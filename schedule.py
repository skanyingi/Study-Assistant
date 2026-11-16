# Spaced-repetition review date calculation working backward from the exam date.
import uuid
from datetime import date, timedelta

# Days before the exam to schedule a review, in spaced-repetition order
# (longest gap first, tightening up as the exam approaches).
REVIEW_INTERVALS_DAYS = [30, 14, 7, 4, 2, 1]


def generate_schedule(exam_date: date, today: date | None = None) -> list[date]:
    """Build a spaced-repetition review schedule counting back from the
    exam date, skipping any review date that's already in the past.

    The day-before-exam interval always falls on or after today (since
    exam_date must be in the future), so at least one review date is
    always returned.
    """
    if today is None:
        today = date.today()

    if exam_date <= today:
        raise ValueError("Exam date must be in the future.")

    return sorted(
        d for d in (exam_date - timedelta(days=n) for n in REVIEW_INTERVALS_DAYS)
        if d >= today
    )


def _ics_event(event_date: date, summary: str) -> str:
    """Build one all-day VEVENT block. Per the iCalendar spec, an all-day
    event's DTEND is exclusive, so it's set to the day after."""
    start = event_date.strftime("%Y%m%d")
    end = (event_date + timedelta(days=1)).strftime("%Y%m%d")
    stamp = date.today().strftime("%Y%m%dT000000Z")
    return (
        "BEGIN:VEVENT\r\n"
        f"UID:{uuid.uuid4()}@notes-to-exam-ready\r\n"
        f"DTSTAMP:{stamp}\r\n"
        f"DTSTART;VALUE=DATE:{start}\r\n"
        f"DTEND;VALUE=DATE:{end}\r\n"
        f"SUMMARY:{summary}\r\n"
        "END:VEVENT\r\n"
    )


def generate_ics(review_dates: list[date], exam_date: date) -> str:
    """Build a downloadable .ics calendar file: one all-day event per review
    date, plus one for the exam itself."""
    events = "".join(
        _ics_event(d, "Review your notes (exam countdown)") for d in review_dates
    )
    events += _ics_event(exam_date, "EXAM DAY")

    return (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//Notes to Exam-Ready//Study Schedule//EN\r\n"
        f"{events}"
        "END:VCALENDAR\r\n"
    )


if __name__ == "__main__":
    today = date(2026, 11, 16)

    print("Exam in 6 weeks:")
    for d in generate_schedule(today + timedelta(days=42), today=today):
        print(" ", d, f"({(d - today).days} days from now)")

    print("\nExam in 3 days:")
    for d in generate_schedule(today + timedelta(days=3), today=today):
        print(" ", d, f"({(d - today).days} days from now)")

    print("\nExam tomorrow:")
    for d in generate_schedule(today + timedelta(days=1), today=today):
        print(" ", d, f"({(d - today).days} days from now)")

    print("\nExam date in the past (should raise ValueError):")
    try:
        generate_schedule(today - timedelta(days=1), today=today)
        print("  ERROR: no exception raised!")
    except ValueError as e:
        print(" ", e)

    print("\nGenerated .ics file:")
    exam = today + timedelta(days=42)
    reviews = generate_schedule(exam, today=today)
    print(generate_ics(reviews, exam))
