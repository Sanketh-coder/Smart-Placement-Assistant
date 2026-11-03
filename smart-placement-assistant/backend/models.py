from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Student(Base):
    __tablename__ = "students"
    student_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(10), nullable=False, default="student")  # student | admin
    branch: Mapped[str | None] = mapped_column(String(60))
    study_year: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.now())


class Question(Base):
    __tablename__ = "questions"
    question_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False, default="Beginner")
    qtype: Mapped[str] = mapped_column(String(10), nullable=False, default="coding")  # coding | mcq
    description: Mapped[str] = mapped_column(Text, nullable=False)
    sample_input: Mapped[str | None] = mapped_column(Text)
    expected_output: Mapped[str | None] = mapped_column(Text)
    options: Mapped[list | None] = mapped_column(JSON)          # MCQ choices
    correct_answer: Mapped[str | None] = mapped_column(Text)    # MCQ only, never sent to students before answering
    solution: Mapped[str | None] = mapped_column(Text)          # coding reference solution (shown after attempt)
    explanation: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.now())


class Attempt(Base):
    __tablename__ = "attempts"
    attempt_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.student_id"), nullable=False, index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.question_id"), nullable=False, index=True)
    submitted_answer: Mapped[str | None] = mapped_column(Text)
    score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    mode: Mapped[str] = mapped_column(String(10), default="practice")  # practice | quiz
    time_taken_sec: Mapped[int | None] = mapped_column(Integer)
    attempted_at: Mapped[object] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))  # stored as UTC

    question = relationship("Question")
