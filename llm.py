# All LLM-provider-specific code lives here so the provider can be swapped by
# editing only this file. Currently using OpenRouter (free tier) via its
# OpenAI-compatible API.
import os
import time

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import ValidationError

from models import Quiz

load_dotenv()

# Swap this one string to change models. Must support structured JSON output
# (OpenRouter's "structured_outputs" parameter) for generate_quiz to work.
MODEL_NAME = "nvidia/nemotron-3.5-super-vl:free"

_client = None


def _get_client() -> OpenAI:
    """Lazily create the OpenRouter client so importing this module never
    fails just because the API key isn't set yet (useful for tests)."""
    global _client
    if _client is None:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set. Add it to your .env file."
            )
        _client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    return _client


QUIZ_FORMAT_INSTRUCTIONS = (
    "Each question must have exactly 4 answer choices, one correct answer "
    "that matches one of the choices exactly, and a short explanation of "
    "why that answer is correct.\n\n"
    "Important: the 'question' field must contain ONLY the question text "
    "itself. Do not include the answer choices, option letters (A/B/C/D), "
    "or the correct answer inside the 'question' field - those belong only "
    "in the separate 'choices' and 'correct_answer' fields."
)


def _generate_quiz_json(prompt: str) -> Quiz:
    """Shared retry logic for any prompt that asks the LLM for a Quiz as
    structured JSON. Retries once if the output fails pydantic validation
    or the request errors out, then raises so the caller can show a
    friendly error."""
    last_error: Exception | None = None
    for attempt in range(2):  # one try + one retry
        try:
            response = _get_client().chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "quiz",
                        "strict": True,
                        "schema": Quiz.model_json_schema(),
                    },
                },
            )
            return Quiz.model_validate_json(response.choices[0].message.content)
        except ValidationError as e:
            last_error = e
        except Exception as e:  # API errors, rate limits, etc.
            last_error = e

        if attempt == 0:
            time.sleep(1)

    raise RuntimeError(
        f"Could not generate a valid quiz after 2 attempts: {last_error}"
    )


def generate_quiz(text_chunk: str, num_questions: int = 5) -> Quiz:
    """Generate a multiple-choice quiz from a chunk of lecture-notes text."""
    prompt = (
        f"You are a study assistant. Based only on the lecture notes below, "
        f"write exactly {num_questions} multiple-choice quiz questions.\n\n"
        f"{QUIZ_FORMAT_INSTRUCTIONS}\n\n"
        f"Lecture notes:\n{text_chunk}"
    )
    return _generate_quiz_json(prompt)


def generate_weak_topics_quiz(text_chunk: str, missed_questions: list[str]) -> Quiz:
    """Generate a fresh quiz re-testing the concepts behind questions the
    student previously got wrong, phrased differently from the originals."""
    missed_list = "\n".join(f"- {q}" for q in missed_questions)
    prompt = (
        f"A student got the following quiz questions wrong:\n{missed_list}\n\n"
        f"Based only on the lecture notes below, write one NEW multiple-choice "
        f"question for each concept above, testing the same underlying idea "
        f"but phrased differently from the original question.\n\n"
        f"{QUIZ_FORMAT_INSTRUCTIONS}\n\n"
        f"Lecture notes:\n{text_chunk}"
    )
    return _generate_quiz_json(prompt)


def _generate_text(prompt: str, retries: int = 3) -> str:
    """Call the LLM for a plain-text response, retrying with backoff on
    transient API errors (e.g. rate limits, temporary overload)."""
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            response = _get_client().chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            last_error = e
            if attempt < retries - 1:
                time.sleep(2**attempt)  # 1s, 2s, 4s

    raise RuntimeError(f"LLM request failed after {retries} attempts: {last_error}")


def generate_summary(chunks: list[str]) -> str:
    """Summarize lecture notes into a concise list of key concepts.

    Handles long documents by summarizing each chunk separately, then
    combining those partial summaries into one cohesive final summary.
    """
    summary_prompt = (
        "Summarize the key concepts in these lecture notes as a concise, "
        "beginner-friendly bulleted list. Focus on definitions and the most "
        "important ideas only.\n\nLecture notes:\n{}"
    )

    partial_summaries = [_generate_text(summary_prompt.format(c)) for c in chunks]

    if len(partial_summaries) == 1:
        return partial_summaries[0]

    combine_prompt = (
        "These are partial summaries of different sections of the same "
        "lecture notes. Combine them into one concise, well-organized "
        "summary of key concepts, removing repetition.\n\n"
        + "\n\n".join(partial_summaries)
    )
    return _generate_text(combine_prompt)
