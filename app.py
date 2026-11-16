# Streamlit UI: PDF upload, summary, quiz, and study schedule.
from datetime import date, timedelta

import streamlit as st

from llm import generate_quiz, generate_summary, generate_weak_topics_quiz
from pdf_utils import chunk_text, clean_text, extract_text, is_empty_or_scanned
from schedule import generate_ics, generate_schedule

st.set_page_config(page_title="Notes to Exam-Ready", page_icon="📚", layout="centered")

st.title("📚 Notes to Exam-Ready")
st.subheader("Turn your lecture notes into a summary, a practice quiz, and a study plan — in minutes.")

how_it_works = st.columns(3)
with how_it_works[0]:
    st.markdown("**📄 1. Upload**")
    st.caption("Drop in your lecture-notes PDF")
with how_it_works[1]:
    st.markdown("**🧠 2. Learn**")
    st.caption("Get a summary and a practice quiz")
with how_it_works[2]:
    st.markdown("**📅 3. Review**")
    st.caption("Follow a spaced-repetition schedule")

st.divider()

# Cached so that unrelated reruns (e.g. clicking other buttons) don't burn
# API quota re-generating the same summary/quiz for the same text.
cached_generate_summary = st.cache_data(show_spinner=False)(generate_summary)
cached_generate_quiz = st.cache_data(show_spinner=False)(generate_quiz)
cached_generate_weak_topics_quiz = st.cache_data(show_spinner=False)(
    generate_weak_topics_quiz
)

FRIENDLY_LLM_ERROR = (
    "We couldn't reach the AI service right now. This is usually temporary "
    "(rate limits or a busy model) - please wait a moment and try again."
)

uploaded_file = st.file_uploader("📄 Upload a PDF", type="pdf")

if uploaded_file is not None:
    # Only re-extract/chunk when a new file is uploaded.
    if st.session_state.get("uploaded_name") != uploaded_file.name:
        raw_text = extract_text(uploaded_file)
        cleaned_text = clean_text(raw_text)

        st.session_state["uploaded_name"] = uploaded_file.name
        st.session_state["chunks"] = chunk_text(cleaned_text)
        st.session_state["is_empty"] = is_empty_or_scanned(cleaned_text)
        st.session_state.pop("summary", None)
        st.session_state.pop("quiz", None)

    if st.session_state["is_empty"]:
        st.error(
            "We couldn't find readable text in this PDF. It may be empty or "
            "made of scanned images. Try a different file."
        )
    else:
        chunks = st.session_state["chunks"]

        st.subheader("🧠 Summary")
        if st.button("Generate Summary"):
            with st.spinner("Summarizing..."):
                try:
                    st.session_state["summary"] = cached_generate_summary(tuple(chunks))
                except RuntimeError as e:
                    st.error(FRIENDLY_LLM_ERROR)
                    st.caption(f"Technical details: {e}")

        if "summary" in st.session_state:
            st.write(st.session_state["summary"])

        st.divider()
        st.subheader("📝 Quiz")
        if st.button("Generate Quiz"):
            with st.spinner("Writing quiz questions..."):
                try:
                    st.session_state["quiz"] = cached_generate_quiz(chunks[0])
                    st.session_state.pop("wrong_questions", None)
                    st.session_state.pop("weak_quiz", None)
                except RuntimeError as e:
                    st.error(FRIENDLY_LLM_ERROR)
                    st.caption(f"Technical details: {e}")

        if "quiz" in st.session_state:
            quiz = st.session_state["quiz"]

            with st.form("quiz_form"):
                selected_answers = []
                for i, q in enumerate(quiz.questions):
                    answer = st.radio(
                        f"{i + 1}. {q.question}", q.choices, key=f"q{i}", index=None
                    )
                    selected_answers.append(answer)

                submitted = st.form_submit_button("Check Answers")

            if submitted:
                score = 0
                wrong_questions = []
                for i, q in enumerate(quiz.questions):
                    answer = selected_answers[i]
                    correct = answer == q.correct_answer
                    score += correct
                    if not correct:
                        wrong_questions.append(q.question)

                    if answer is None:
                        st.warning(f"Q{i + 1}: No answer selected.")
                    elif correct:
                        st.success(f"Q{i + 1}: Correct!")
                    else:
                        st.error(f"Q{i + 1}: Incorrect. Correct answer: {q.correct_answer}")
                    st.caption(q.explanation)

                st.info(f"Score: {score} / {len(quiz.questions)}")
                st.session_state["wrong_questions"] = wrong_questions

        if st.session_state.get("wrong_questions"):
            st.divider()
            st.subheader("🎯 Weak Topics")
            st.write(
                f"You missed {len(st.session_state['wrong_questions'])} "
                f"question(s). Practice those concepts again:"
            )
            if st.button("Review Weak Topics"):
                with st.spinner("Writing practice questions..."):
                    try:
                        st.session_state["weak_quiz"] = cached_generate_weak_topics_quiz(
                            chunks[0], tuple(st.session_state["wrong_questions"])
                        )
                    except RuntimeError as e:
                        st.error(FRIENDLY_LLM_ERROR)
                        st.caption(f"Technical details: {e}")

            if "weak_quiz" in st.session_state:
                weak_quiz = st.session_state["weak_quiz"]

                with st.form("weak_quiz_form"):
                    weak_answers = []
                    for i, q in enumerate(weak_quiz.questions):
                        answer = st.radio(
                            f"{i + 1}. {q.question}", q.choices, key=f"wq{i}", index=None
                        )
                        weak_answers.append(answer)

                    weak_submitted = st.form_submit_button("Check Weak-Topic Answers")

                if weak_submitted:
                    weak_score = 0
                    for i, q in enumerate(weak_quiz.questions):
                        answer = weak_answers[i]
                        correct = answer == q.correct_answer
                        weak_score += correct

                        if answer is None:
                            st.warning(f"Q{i + 1}: No answer selected.")
                        elif correct:
                            st.success(f"Q{i + 1}: Correct!")
                        else:
                            st.error(f"Q{i + 1}: Incorrect. Correct answer: {q.correct_answer}")
                        st.caption(q.explanation)

                    st.info(f"Score: {weak_score} / {len(weak_quiz.questions)}")

        st.divider()
        st.subheader("📅 Study Schedule")
        exam_date = st.date_input(
            "When is your exam?", min_value=date.today() + timedelta(days=1)
        )
        if st.button("Generate Schedule"):
            try:
                st.session_state["schedule"] = generate_schedule(exam_date)
                st.session_state["schedule_exam_date"] = exam_date
            except ValueError as e:
                st.error(str(e))

        if "schedule" in st.session_state:
            st.write("Review your notes on these dates, leading up to the exam:")
            for review_date in st.session_state["schedule"]:
                days_away = (review_date - date.today()).days
                st.write(f"- **{review_date}** ({days_away} day(s) from now)")

            ics_text = generate_ics(
                st.session_state["schedule"], st.session_state["schedule_exam_date"]
            )
            st.download_button(
                "📅 Add to Calendar",
                data=ics_text,
                file_name="study_schedule.ics",
                mime="text/calendar",
            )
            st.caption(
                "Downloads a calendar file. Open it to import these dates into "
                "Google Calendar, Outlook, Apple Calendar, or any other calendar app."
            )
