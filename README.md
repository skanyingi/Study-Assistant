# Notes to Exam-Ready

Turn a lecture-notes PDF into a summary, a quiz, a weak-topics review, and a
spaced-repetition study schedule you can import into your calendar.

## Key features

- **Summaries** — chunked so long PDFs still work; partial summaries merged and de-duplicated.
- **Quizzes** — 5 multiple-choice questions grounded in your notes, with an explanation each.
  Responses are JSON-validated against a pydantic schema, with one retry on malformed output.
- **Weak topics** — miss a question and the app generates *new* questions on that same
  concept, rephrased rather than repeated.
- **Study schedule** — spaced-repetition review dates counting back from your exam
  (30/14/7/4/2/1 days), downloadable as an `.ics` file for Google Calendar, Outlook,
  or Apple Calendar.
- **Robust by default** — scanned/empty PDF detection, cached results so repeat clicks
  don't re-call the API, and friendly errors instead of tracebacks on rate limits.

## Setup

Requires **Python 3.11+**.

1. `pip install -r requirements.txt`
2. `cp .env.example .env`, then add your OpenRouter key:
   `OPENROUTER_API_KEY=sk-or-v1-...`
   (Get one free at openrouter.ai/keys.)
3. `python -m streamlit run app.py --server.address 127.0.0.1`
4. Open http://127.0.0.1:8501 and upload a lecture PDF.

> **Windows note:** the `--server.address 127.0.0.1` flag matters. Without it Streamlit
> binds to `::` and fails silently with `OSError: [WinError 64]` — it prints a URL that
> doesn't respond.

## How I built this

See `DEVLOG.md` for a slice-by-slice build log, and `ABOUT.md` for the full project story.
