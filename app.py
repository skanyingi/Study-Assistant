# Streamlit UI: PDF upload, summary, and quiz with answer checking.
import streamlit as st

from llm import generate_quiz, generate_summary
from pdf_utils import chunk_text, clean_text, extract_text, is_empty_or_scanned

st.set_page_config(page_title="Notes to Exam-Ready", page_icon="📚")
st.title("📚 Notes to Exam-Ready")
st.caption("Upload a lecture-notes PDF to get a summary and a practice quiz.")

uploaded_file = st.file_uploader("Upload a PDF", type="pdf")

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

        st.subheader("Summary")
        if st.button("Generate Summary"):
            with st.spinner("Summarizing..."):
                st.session_state["summary"] = generate_summary(chunks)

        if "summary" in st.session_state:
            st.write(st.session_state["summary"])

        st.subheader("Quiz")
        if st.button("Generate Quiz"):
            with st.spinner("Writing quiz questions..."):
                st.session_state["quiz"] = generate_quiz(chunks[0])

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
                for i, q in enumerate(quiz.questions):
                    answer = selected_answers[i]
                    correct = answer == q.correct_answer
                    score += correct

                    if answer is None:
                        st.warning(f"Q{i + 1}: No answer selected.")
                    elif correct:
                        st.success(f"Q{i + 1}: Correct!")
                    else:
                        st.error(f"Q{i + 1}: Incorrect. Correct answer: {q.correct_answer}")
                    st.caption(q.explanation)

                st.info(f"Score: {score} / {len(quiz.questions)}")
