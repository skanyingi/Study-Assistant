# Pydantic schemas for validating structured LLM output (quiz questions, etc).
from pydantic import BaseModel, field_validator


class QuizQuestion(BaseModel):
    question: str
    choices: list[str]  # exactly 4 answer options
    correct_answer: str  # must exactly match one of the choices
    explanation: str

    @field_validator("choices")
    @classmethod
    def must_have_four_choices(cls, choices: list[str]) -> list[str]:
        if len(choices) != 4:
            raise ValueError(f"expected exactly 4 choices, got {len(choices)}")
        return choices

    @field_validator("correct_answer")
    @classmethod
    def answer_must_be_in_choices(cls, answer: str, info) -> str:
        choices = info.data.get("choices")
        if choices is not None and answer not in choices:
            raise ValueError("correct_answer must exactly match one of the choices")
        return answer


class Quiz(BaseModel):
    questions: list[QuizQuestion]
