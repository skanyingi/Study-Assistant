# Dev Log

## Slice 1 — Project skeleton
- Created `.gitignore` (ignores `.env`, `.env.txt`, caches, venvs).
- Created `.env.example` with the `GEMINI_API_KEY` placeholder.
- Created `requirements.txt`, pinned to versions already installed and verified on
  this machine: streamlit 1.65.0, pypdf 6.13.2, pydantic 2.13.5, google-genai 1.75.0,
  python-dotenv 1.0.1.
- Confirmed the current official Gemini SDK is `google-genai` (`from google import genai`),
  not the older `google-generativeai` package.
- Added placeholder files for the planned structure: `app.py`, `pdf_utils.py`, `llm.py`,
  `schedule.py`, `models.py`, each with a one-line comment describing its future role.
- Found an exposed API key committed as plaintext `.env.txt`. Key was rotated by the
  project owner; old key is dead. `.env.txt` is gitignored now and will be removed from
  the working directory.
- Wrote a minimal `README.md` placeholder.

## Slice 2 — pdf_utils.py
- Implemented `extract_text`, `clean_text`, `is_empty_or_scanned`, `chunk_text`.
- Tested against the real sample PDF ("Lectures 5 &6..."): 12145 raw chars,
  12080 after cleaning, not flagged empty/scanned, split into 2 chunks at the
  8000-char default.
- Bug found and fixed: pypdf extracted custom bullet-icon glyphs from the PDF's
  embedded font as Unicode Private Use Area characters (e.g. U+F076), which
  crashed printing on Windows' default console encoding. Fixed by stripping
  U+E000-U+F8FF in `clean_text` rather than papering over it at the print site.
- Chunking breaks on paragraph (`\n\n`) boundaries, with a hard-split fallback
  for any single paragraph longer than the max chunk size.

## Slice 3 — llm.py + models.py
- Confirmed the API key in `.env` is not a freshly rotated key (it matches the
  one that was exposed in the old `.env.txt`). Owner reviewed and chose to
  proceed with it as-is.
- `models.py`: `QuizQuestion` (question, 4 choices, correct_answer, explanation)
  with validators enforcing exactly 4 choices and that correct_answer matches
  one of them; `Quiz` wraps a list of questions.
- `llm.py`: Gemini client via `google-genai`, `generate_quiz()` using
  `response_mime_type="application/json"` + `response_schema=Quiz` for
  structured output, with one retry on validation/API failure.
- Bug found and fixed: first command-line test failed with `503 UNAVAILABLE`
  on the `gemini-flash-latest` model alias (server-side overload, not an auth
  or network issue - confirmed by testing the raw HTTPS endpoint and
  `client.models.list()` separately, both of which worked fine). Switched
  `MODEL_NAME` to `gemini-2.5-flash-lite`, which responded immediately.
- Verified end-to-end on the real sample PDF: extracted text -> chunked ->
  generated 5 valid quiz questions grounded in the actual lecture content
  (object storage, NoSQL database types, shared responsibility model, etc.),
  all passing pydantic validation.
