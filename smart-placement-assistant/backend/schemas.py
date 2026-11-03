from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

EMAIL_RE = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
Difficulty = Literal["Beginner", "Intermediate", "Advanced"]


class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: str = Field(pattern=EMAIL_RE, max_length=150)
    password: str = Field(min_length=8, max_length=72)
    branch: str | None = Field(default=None, max_length=60)
    study_year: int | None = Field(default=None, ge=1, le=6)

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Name must have at least 2 characters")
        return v


class LoginIn(BaseModel):
    email: str = Field(pattern=EMAIL_RE)
    password: str = Field(min_length=1, max_length=72)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    student_id: int
    full_name: str
    email: str
    role: str
    branch: str | None = None
    study_year: int | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class QuestionIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    category: str = Field(min_length=2, max_length=60)
    difficulty: Difficulty = "Beginner"
    qtype: Literal["coding", "mcq"] = "coding"
    description: str = Field(min_length=5)
    sample_input: str | None = None
    expected_output: str | None = None
    options: list[str] | None = None
    correct_answer: str | None = None
    solution: str | None = None
    explanation: str | None = None

    @model_validator(mode="after")
    def check_mcq(self):
        if self.qtype == "mcq":
            opts = [o.strip() for o in (self.options or []) if o.strip()]
            if len(opts) < 2:
                raise ValueError("MCQ questions need at least 2 options")
            if not self.correct_answer or self.correct_answer.strip() not in opts:
                raise ValueError("correct_answer must match one of the options")
            self.options = opts
            self.correct_answer = self.correct_answer.strip()
        else:
            self.options = None
            self.correct_answer = None
        return self


class QuestionOut(BaseModel):
    """What students see: no answers."""
    model_config = ConfigDict(from_attributes=True)
    question_id: int
    title: str
    category: str
    difficulty: str
    qtype: str
    description: str
    sample_input: str | None = None
    expected_output: str | None = None
    options: list[str] | None = None


class QuestionAdminOut(QuestionOut):
    correct_answer: str | None = None
    solution: str | None = None
    explanation: str | None = None


class AttemptIn(BaseModel):
    question_id: int = Field(gt=0)
    submitted_answer: str | None = Field(default=None, max_length=10000)
    completed: bool = False


class Feedback(BaseModel):
    correct_answer: str | None = None
    solution: str | None = None
    explanation: str | None = None


class AttemptOut(BaseModel):
    attempt_id: int
    question_id: int
    score: float
    completed: bool
    graded_by: Literal["auto", "self"]
    feedback: Feedback


class QuizAnswer(BaseModel):
    question_id: int = Field(gt=0)
    answer: str | None = None


class QuizSubmitIn(BaseModel):
    answers: list[QuizAnswer] = Field(min_length=1, max_length=50)
    time_taken_sec: int | None = Field(default=None, ge=0, le=86400)


class QuizResultItem(BaseModel):
    question_id: int
    title: str
    your_answer: str | None
    correct: bool
    feedback: Feedback


class QuizResultOut(BaseModel):
    total: int
    correct: int
    score_percent: float
    time_taken_sec: int | None
    results: list[QuizResultItem]


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=500)

    @field_validator("message")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Message cannot be empty")
        return v


class ChatOut(BaseModel):
    reply: str
    topic: str | None
    engine: str


class AttemptRow(BaseModel):
    attempt_id: int
    question_id: int
    title: str
    category: str
    score: float
    completed: bool
    mode: str
    attempted_at: datetime | None


class CategoryStat(BaseModel):
    category: str
    total_questions: int
    attempted: int
    average_best_score: float


class ProgressOut(BaseModel):
    student_id: int
    full_name: str
    total_attempts: int
    questions_attempted: int
    questions_completed: int
    total_questions: int
    average_score: float
    categories: list[CategoryStat]
    recommendations: list[str]
    recent: list[AttemptRow]


class LeaderRow(BaseModel):
    rank: int
    full_name: str
    points: float
    questions_attempted: int
