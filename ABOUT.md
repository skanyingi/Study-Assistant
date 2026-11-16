# About the project

## Inspiration

Every student knows the ritual: open a twelve-page lecture PDF, reread it twice, highlight
half of it, and still walk into the exam unsure whether anything actually stuck.

The problem isn't access to information — it's that rereading is a terribly weak way to
learn. You get a feeling of familiarity ("I've seen this before") that masks the truth
("I can't recall this"). Real learning needs retrieval practice: being asked questions,
getting things wrong, and finding out *why*. That's the part lecture notes never provide
on their own.

So I wanted to build the smallest possible tool that closes that loop end-to-end: **upload
the notes, get a summary, get quizzed, find your weak spots, and get a review plan that
respects how memory actually decays.** Not another PDF-chatbot — a study *workflow*.

## What it does

Upload a lecture-notes PDF and the app:

1. **Extracts and cleans the text**, detects empty or scanned (image-only) PDFs, and chunks
   long documents on paragraph boundaries.
2. **Summarizes** the material into a beginner-friendly bulleted overview — chunk by chunk,
   then merges the partial summaries so nothing is lost or duplicated.
3. **Generates a 5-question multiple-choice quiz** grounded strictly in *your* notes, with
   one correct answer and an explanation for each.
4. **Grades it** and, for anything you missed, generates a *new* set of questions targeting
   those same concepts — rephrased, not repeated.
5. **Builds a spaced-repetition schedule** counting backward from your exam date, and
   exports it as a downloadable `.ics` calendar file you can import into Google Calendar,
   Outlook, or Apple Calendar.

## How we built it

I built it as a **series of small vertical slices**, each one run against real data before
moving on: skeleton → PDF utilities → quiz generation → summary → UI → schedule → error
handling → weak topics → calendar export. Every slice ended with real output, not an
assumption. `DEVLOG.md` in the repo is the actual working log from that process.

The stack is deliberately boring and free: **Streamlit**, **pypdf**, **pydantic**, and
**OpenRouter** for the LLM. No database, no auth, no framework sprawl.

Three decisions mattered most:

- **Structured output over parsing.** Quizzes are requested as strict JSON and validated
  with pydantic models (`QuizQuestion` enforces exactly four choices, and that
  `correct_answer` is actually one of them). One retry with a 1-second backoff, then a
  friendly error. The UI never has to trust a text blob.
- **A hard provider boundary.** All LLM code lives in `llm.py`. That wasn't stylistic —
  it's what made the mid-build provider swap survivable (see below).
- **Caching and graceful failure.** `st.cache_data` means repeated clicks don't burn API
  calls, and rate limits or outages surface as a plain "please try again" instead of a
  traceback.

### The math behind the schedule

The review dates aren't arbitrary. Memory retention is well-modelled by exponential decay,

$$R(t) = R_0 \, e^{-t/S}$$

where $R(t)$ is the probability of recall at time $t$ and $S$ is the stability of the
memory. Each successful retrieval increases $S$, which means the *next* review can safely
be further away — intervals should expand, not stay fixed.

Rather than guess absolute intervals, the app anchors them relative to the deadline:
reviews at 30, 14, 7, 4, 2, and 1 days before the exam, dropping any date already in the
past. As the exam approaches, reviews naturally tighten — the same expanding-then-compressing
shape the forgetting curve implies, but guaranteed to fit inside the time a student actually
has left.

## Challenges we ran into

**The provider swap, mid-build.** I started on Gemini and hit its free-tier ceiling
(20 requests/day) partway through. Because `llm.py` was already isolated, I rewrote it to
use the OpenAI-compatible client against OpenRouter in a single file, swapped
`google-genai` for `openai` in requirements, and re-verified the whole flow against the
real API the same day. Designing for a swap *before* needing one is the single best
decision I made.

**PDFs are messier than they look.** `pypdf` extracted the sample lecture's custom bullet
icons as Unicode Private Use Area characters (e.g. `U+F076`), which crashed on Windows'
default console encoding. The tempting fix was to sanitize at the print site; the right fix
was stripping the private-use range inside `clean_text`, so every downstream consumer gets
clean text.

**LLMs confidently duplicate themselves.** The first OpenRouter quiz put the answer choices
*and* a "Correct Answer: X" line inside the `question` field, on top of the separate
`choices` array — the UI would have shown every option twice. Fixed by being explicit in
the prompt about what belongs in each field, then re-verified.

**A silent platform failure.** `streamlit run app.py` bound to `::` on Windows and failed
with repeated `OSError: [WinError 64]` — while the log cheerfully claimed the app was
running. It was unreachable. Fixed by binding explicitly to `127.0.0.1` and confirming via
the `/_stcore/health` endpoint instead of trusting the startup message.

**Spec details that bite.** Calendar all-day events use an *exclusive* `DTEND`, so a
single-day event needs `DTSTART` and `DTEND` one day apart. I validated the generated `.ics`
by temporarily installing a real iCalendar parser (then removing it — it never entered
`requirements.txt`) to confirm it parsed cleanly with all seven events.

## Accomplishments that we're proud of

- **The whole loop actually works, on real data.** The final regression ran the full path
  against the real API — upload → summary → quiz → grade → weak topics → schedule → `.ics`
  export — with zero exceptions and correct scores. Nothing in the demo is mocked.
- **The provider swap took one file.** A mid-build outage of the original provider became a
  single-file rewrite instead of a rewrite of the app, which is exactly what that boundary
  was for.
- **Validation held the line.** After pydantic plus the retry, no malformed quiz ever reached
  the UI — including the run where the model tried to duplicate the answer choices.
- **Weak Topics genuinely re-teaches.** In a real run I missed two questions (scalability and
  block storage); the follow-up quiz asked rephrased questions on those same two concepts,
  not verbatim repeats.
- **The calendar file survives a real parser.** Temporary validation with an RFC 5545
  library confirmed all seven events parsed with correct dates and titles, while
  `requirements.txt` stayed untouched.
- **Zero cost and zero setup for the student.** No account, no key, no install — just a PDF
  and an exam date.

## What we learned

- **Validate at the boundary, not in the UI.** pydantic plus a retry meant the interface
  could stay dumb and readable.
- **"It ran" is not "it works."** Half my bugs were found by checking the actual output —
  the doubled choices, the invisible PUA glyphs, the unreachable server that logged success.
- **Constraints are design tools.** Free tier, minimal dependencies, no new files. These
  forced simpler answers: hand-written `.ics` instead of a library, chunk-and-merge instead
  of a vector database, `.ics` import instead of an OAuth dance.
- **Separate the model from the product.** The LLM is one function call behind a clean
  boundary; everything interesting — validation, caching, error handling, scheduling — is
  deterministic code I control.

## What's next for Notes to Exam-Ready

- **Persistence.** Keep a student's summary, quiz results, and schedule across refreshes
  instead of holding them in session state.
- **Adaptive difficulty.** Track rolling accuracy per topic and let question difficulty and
  review frequency respond to it, rather than using one fixed set of intervals.
- **True two-way calendar sync.** An OAuth integration so the schedule lands in a calendar
  in one click and stays in sync when the exam date changes — the step beyond the current
  download-and-import `.ics` file.
- **Summary and schedule export.** Let students take the summary out as a PDF for offline
  revision, not just the calendar dates.
- **Multi-document study sets.** Combine several lectures into one quiz so a final exam
  isn't limited to a single PDF.
