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

## Slice 5 — app.py UI
- Built upload -> summary -> quiz -> answer-checking flow in `app.py`, using
  st.session_state to avoid re-extracting on every rerun, and st.form so quiz
  answers are graded all at once.
- Bug found and fixed: running `streamlit run app.py` directly bound to `::`
  (dual-stack) and failed silently on Windows with repeated
  `OSError: [WinError 64]` accept failures - the log claimed the app was up,
  but it was unreachable. Fixed by binding explicitly with
  `--server.address 127.0.0.1`; confirmed via the `/_stcore/health` endpoint.
- Verified the real upload -> summary -> quiz flow using Streamlit's AppTest
  utility against the actual sample PDF and the real Gemini API.
- Hit the Gemini free tier's daily quota while testing: 20 requests/day on
  gemini-2.5-flash-lite, shared across summary and quiz calls. Worth
  remembering for demo day and when deciding how to handle this error
  message in Slice 7 (friendly "try again later" vs. a raw exception).
- To keep testing the UI logic without more quota usage, mocked
  `generate_summary`/`generate_quiz` and re-ran the full flow. Diagnosed a
  false bug in my own test script (AppTest form widgets need `set_value()`
  chained directly with the submit click, not run separately) - the app
  logic itself was correct once the test was fixed. Verified: all 5
  questions scored correctly end-to-end.

## Provider swap: Gemini -> OpenRouter
- Owner's choice: fully replace Gemini with OpenRouter (free tier), since
  Gemini's free-tier daily quota (20 req/day) was exhausted mid-build. This is
  exactly the swap the spec designed `llm.py` to isolate for.
- Checked OpenRouter's public /models endpoint for free models that support
  `structured_outputs` (needed for the quiz JSON schema). Picked
  `nvidia/nemotron-3.5-super-vl:free` - one of OpenRouter's most-used free
  models, 1M context, explicit structured-output support.
- Rewrote `llm.py` to use the OpenAI-compatible client against OpenRouter's
  base URL, reading `OPENROUTER_API_KEY` from `.env`. Updated
  `requirements.txt` (dropped `google-genai`, added `openai`) and
  `.env.example`.
- Bug found and fixed: first quiz generation attempt duplicated the answer
  choices and "Correct Answer: X" inside the `question` text field itself,
  on top of the separate `choices`/`correct_answer` fields - would have
  shown doubled choices in the UI. Fixed by being explicit in the prompt
  about what belongs only in the `question` field. Re-verified clean output.
- Verified end-to-end against the real PDF and the real app.py (via AppTest)
  using the new provider: summary generation, quiz generation, and the full
  upload -> summary -> quiz -> answer -> score flow all passed with zero
  exceptions and a correct 5/5 score.
- Found and removed a stray `.env.txt` that reappeared with both API keys in
  plaintext (git-ignored, never tracked - no exposure risk, just redundant).

## Slice 6 — schedule.py + study schedule UI
- `generate_schedule(exam_date, today=None)`: spaced-repetition review dates
  at 30/14/7/4/2/1 days before the exam, filtering out any that have already
  passed. Raises ValueError if exam_date isn't in the future.
- Caught a dead-code bug before even running it: an initial "exam is very
  close" fallback branch could never actually trigger, since the 1-day-before
  interval is always >= today whenever exam_date > today. Removed it and
  added a real test for the edge case that matters (exam date in the past).
- Added the Study Schedule section to app.py: a date input (min value =
  tomorrow, so past dates aren't even selectable) and a button that displays
  the generated review dates with days-from-now counts.
- Verified: generate_schedule() directly for a 6-week exam, a 3-day exam, an
  exam tomorrow, and a past exam date (correctly raises); and the full UI
  flow via AppTest (date input -> Generate Schedule -> correct list
  rendered, zero exceptions).

## Slice 7 — Error handling, spinners, caching
- Added a 1s backoff before `generate_quiz`'s retry (it previously retried
  instantly with no delay, unlike `_generate_text`'s backoff).
- Wrapped `generate_summary`/`generate_quiz` with `st.cache_data` in app.py
  so clicking buttons or unrelated reruns don't re-call the API for the same
  input text. Verified: calling the same button twice only triggered one
  underlying call (mocked test, call counted directly).
- Wrapped both LLM calls in try/except RuntimeError in app.py, showing a
  friendly "please try again" message instead of a raw traceback, with
  technical details available in a small caption for debugging. Verified
  with a simulated failure: zero unhandled exceptions.
- Final regression check: ran the complete app against the real OpenRouter
  API - upload -> summary -> quiz -> answer -> score -> schedule - all
  passed with zero exceptions.
- This completes the spec's must-ship scope (summary, quiz, schedule). The
  weak-topics report remains a stretch goal, not built unless requested.

## Stretch goal — Weak Topics report
- Refactored `generate_quiz`'s JSON-schema retry logic into a shared
  `_generate_quiz_json()` helper to avoid duplicating it for the new
  function.
- Added `generate_weak_topics_quiz(text_chunk, missed_questions)` to
  llm.py: takes the questions a student got wrong and generates new
  questions testing the same concepts, phrased differently from the
  originals (not just repeating the same question).
- app.py: tracks wrong answers in session_state after grading the main
  quiz; shows a "Weak Topics" section (only when there are wrong answers)
  with its own "Review Weak Topics" button, cached generation, form,
  scoring, and friendly error handling, matching the rest of the app's
  patterns. Generating a new main quiz clears stale weak-topic state.
- Verified with a mocked test (confirmed the exact wrong question is
  passed through, section visibility logic, and scoring) and a real
  end-to-end run: got 2 real questions wrong (scalability, block storage),
  and the generated weak-topics quiz asked genuinely rephrased versions of
  those same two concepts - not verbatim repeats.

## Calendar integration (.ics download)
- Added `generate_ics(review_dates, exam_date)` to schedule.py: hand-built
  iCalendar text (no new dependency), one all-day VEVENT per review date
  plus one for "EXAM DAY", with correct exclusive DTEND per the spec.
- Added a "Add to Calendar" download button in app.py's Study Schedule
  section, with a caption explaining the manual import step (download then
  open the file in your calendar app - not fully automatic; a true one-click
  auto-add would need OAuth, which was deliberately scoped out as too heavy
  for this project).
- Verified the .ics structure by temporarily installing the real `icalendar`
  library (not added to requirements.txt) and parsing the generated file
  with it: parsed cleanly, correct dates and titles, 7 events total.
- Verified the full UI flow via AppTest: upload -> set exam date -> generate
  schedule -> download button appears with correct underlying data.

## Slice 4 — Summary generation
- Added `_generate_text()` to `llm.py`: plain-text Gemini call with exponential
  backoff (1s/2s/4s) on API errors, so rate limits don't immediately fail.
- Added `generate_summary(chunks)`: summarizes each chunk individually, then
  (if more than one chunk) combines the partial summaries into one organized,
  deduplicated final summary. Handles long PDFs without extra files, per spec.
- Verified on the real 2-chunk sample PDF: produced an accurate, well-organized
  bulleted summary covering cloud storage types, database types, migration
  strategies, and cloud security practices, correctly merged from both chunks.
