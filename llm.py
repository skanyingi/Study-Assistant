# All Gemini-specific code lives here so the provider can be swapped by
# editing only this file.
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import ValidationError

from models import Quiz

load_dotenv()

# Swap this one string to change models (e.g. a newer free-tier Flash release).
MODEL_NAME = "gemini-2.5-flash-lite"

_client = None


def _get_client() -> genai.Client:
    """Lazily create the Gemini client so importing this module never fails
    just because the API key isn't set yet (useful for tests)."""
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add it to your .env file."
            )
        _client = genai.Client(api_key=api_key)
    return _client


def generate_quiz(text_chunk: str, num_questions: int = 5) -> Quiz:
    """Generate a multiple-choice quiz from a chunk of lecture-notes text.

    Returns a validated Quiz. Retries the generation once if the model's
    output fails pydantic validation, then raises so the caller can show a
    friendly error.
    """
    prompt = (
        f"You are a study assistant. Based only on the lecture notes below, "
        f"write exactly {num_questions} multiple-choice quiz questions. "
        f"Each question must have exactly 4 answer choices, one correct "
        f"answer that matches one of the choices exactly, and a short "
        f"explanation of why that answer is correct.\n\n"
        f"Lecture notes:\n{text_chunk}"
    )

    last_error: Exception | None = None
    for attempt in range(2):  # one try + one retry
        try:
            response = _get_client().models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=Quiz,
                ),
            )
            return Quiz.model_validate_json(response.text)
        except ValidationError as e:
            last_error = e
        except Exception as e:  # API errors, rate limits, etc.
            last_error = e

    raise RuntimeError(
        f"Could not generate a valid quiz after 2 attempts: {last_error}"
    )
