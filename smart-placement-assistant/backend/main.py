"""Smart Placement Preparation Assistant (Advanced) - FastAPI backend."""
import logging
import os
import random
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

import models
import schemas as s
from chatbot import ENGINE, SUGGESTIONS, get_reply
from database import Base, SessionLocal, engine, get_db
from security import create_token, get_current_user, hash_password, require_admin, verify_password
from seed import seed

log = logging.getLogger("placement")
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    if os.getenv("AUTO_SEED", "true").lower() == "true":
        with SessionLocal() as db:
            seed(db)
    yield


app = FastAPI(title="Smart Placement Preparation Assistant", version="2.0.0", lifespan=lifespan)
origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5500,http://127.0.0.1:5500").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(SQLAlchemyError)
async def db_error_handler(request: Request, exc: SQLAlchemyError):
    log.exception("Database error")
    return JSONResponse(status_code=503, content={"detail": "Database is unavailable. Please try again shortly."})


def _get_question_or_404(db: Session, qid: int) -> models.Question:
    q = db.get(models.Question, qid)
    if q is None:
        raise HTTPException(404, f"Question {qid} was not found.")
    return q


def _norm(x: str | None) -> str:
    return " ".join((x or "").split()).lower()


def _feedback(q: models.Question) -> s.Feedback:
    return s.Feedback(correct_answer=q.correct_answer, solution=q.solution, explanation=q.explanation)


# ---------------------------------------------------------------- health
@app.get("/", tags=["Health"])
def health():
    return {"status": "ok", "service": "Smart Placement Preparation Assistant", "docs": "/docs", "app": "/app/"}


@app.get("/health/db", tags=["Health"])
def health_db(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {"database": "ok"}


# ---------------------------------------------------------------- auth
@app.post("/auth/register", response_model=s.TokenOut, status_code=201, tags=["Auth"])
def register(body: s.RegisterIn, db: Session = Depends(get_db)):
    user = models.Student(full_name=body.full_name, email=body.email.lower(), password_hash=hash_password(body.password),
                          branch=body.branch, study_year=body.study_year, role="student")
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "An account with this email already exists.")
    return s.TokenOut(access_token=create_token(user), user=user)


@app.post("/auth/login", response_model=s.TokenOut, tags=["Auth"])
def login(body: s.LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(models.Student).where(models.Student.email == body.email.lower()))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Incorrect email or password.")
    return s.TokenOut(access_token=create_token(user), user=user)


@app.get("/auth/me", response_model=s.UserOut, tags=["Auth"])
def me(user: models.Student = Depends(get_current_user)):
    return user


# ---------------------------------------------------------------- questions
@app.get("/questions/meta", tags=["Questions"])
def questions_meta(db: Session = Depends(get_db)):
    cats = [r[0] for r in db.execute(select(models.Question.category).distinct().order_by(models.Question.category))]
    return {"categories": cats, "difficulties": ["Beginner", "Intermediate", "Advanced"], "types": ["coding", "mcq"]}


@app.get("/questions", response_model=list[s.QuestionOut], tags=["Questions"])
def list_questions(
    category: str | None = None, difficulty: str | None = None, qtype: str | None = None,
    search: str | None = Query(default=None, max_length=100),
    skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), db: Session = Depends(get_db),
):
    stmt = select(models.Question)
    if category:
        stmt = stmt.where(models.Question.category == category)
    if difficulty:
        stmt = stmt.where(models.Question.difficulty == difficulty)
    if qtype:
        stmt = stmt.where(models.Question.qtype == qtype)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(or_(models.Question.title.like(like), models.Question.description.like(like)))
    return db.scalars(stmt.order_by(models.Question.question_id).offset(skip).limit(limit)).all()


@app.get("/questions/{question_id}", response_model=s.QuestionOut, tags=["Questions"])
def get_question(question_id: int, db: Session = Depends(get_db)):
    return _get_question_or_404(db, question_id)


@app.post("/questions", response_model=s.QuestionAdminOut, status_code=201, tags=["Admin"])
def create_question(body: s.QuestionIn, db: Session = Depends(get_db), _: models.Student = Depends(require_admin)):
    q = models.Question(**body.model_dump())
    db.add(q)
    db.commit()
    return q


@app.put("/questions/{question_id}", response_model=s.QuestionAdminOut, tags=["Admin"])
def update_question(question_id: int, body: s.QuestionIn, db: Session = Depends(get_db), _: models.Student = Depends(require_admin)):
    q = _get_question_or_404(db, question_id)
    for k, v in body.model_dump().items():
        setattr(q, k, v)
    db.commit()
    return q


@app.delete("/questions/{question_id}", status_code=204, tags=["Admin"])
def delete_question(question_id: int, db: Session = Depends(get_db), _: models.Student = Depends(require_admin)):
    q = _get_question_or_404(db, question_id)
    db.query(models.Attempt).filter(models.Attempt.question_id == question_id).delete()
    db.delete(q)
    db.commit()


@app.get("/admin/questions", response_model=list[s.QuestionAdminOut], tags=["Admin"])
def admin_questions(db: Session = Depends(get_db), _: models.Student = Depends(require_admin)):
    return db.scalars(select(models.Question).order_by(models.Question.question_id)).all()


@app.get("/admin/stats", tags=["Admin"])
def admin_stats(db: Session = Depends(get_db), _: models.Student = Depends(require_admin)):
    avg = db.scalar(select(func.avg(models.Attempt.score))) or 0
    return {
        "students": db.scalar(select(func.count()).select_from(models.Student).where(models.Student.role == "student")),
        "questions": db.scalar(select(func.count()).select_from(models.Question)),
        "attempts": db.scalar(select(func.count()).select_from(models.Attempt)),
        "average_score": round(float(avg), 2),
    }


# ---------------------------------------------------------------- attempts
@app.post("/attempts", response_model=s.AttemptOut, status_code=201, tags=["Attempts"])
def create_attempt(body: s.AttemptIn, db: Session = Depends(get_db), user: models.Student = Depends(get_current_user)):
    q = _get_question_or_404(db, body.question_id)
    if q.qtype == "mcq":
        if not (body.submitted_answer or "").strip():
            raise HTTPException(422, "Please choose an answer before submitting.")
        ok = _norm(body.submitted_answer) == _norm(q.correct_answer)
        score, completed, graded_by = (100.0 if ok else 0.0), ok, "auto"
    else:
        # Code is never executed on the server (security). Coding attempts are self-assessed.
        if not (body.submitted_answer or "").strip() and not body.completed:
            raise HTTPException(422, "Write your solution or mark the question as completed.")
        score, completed, graded_by = (100.0 if body.completed else 0.0), body.completed, "self"
    a = models.Attempt(student_id=user.student_id, question_id=q.question_id, submitted_answer=body.submitted_answer,
                       score=score, completed=completed, mode="practice")
    db.add(a)
    db.commit()
    return s.AttemptOut(attempt_id=a.attempt_id, question_id=q.question_id, score=score, completed=completed,
                        graded_by=graded_by, feedback=_feedback(q))


# ---------------------------------------------------------------- quiz
@app.get("/quiz", response_model=list[s.QuestionOut], tags=["Quiz"])
def start_quiz(count: int = Query(5, ge=1, le=20), category: str | None = None, difficulty: str | None = None,
               db: Session = Depends(get_db), _: models.Student = Depends(get_current_user)):
    stmt = select(models.Question).where(models.Question.qtype == "mcq")
    if category:
        stmt = stmt.where(models.Question.category == category)
    if difficulty:
        stmt = stmt.where(models.Question.difficulty == difficulty)
    pool = db.scalars(stmt).all()
    if not pool:
        raise HTTPException(404, "No quiz questions match those filters.")
    picked = random.sample(pool, min(count, len(pool)))
    for q in picked:  # shuffle a copy of the options so answer position isn't predictable
        q.options = random.sample(q.options or [], len(q.options or []))
    db.expunge_all()  # never persist the shuffle
    return picked


@app.post("/quiz/submit", response_model=s.QuizResultOut, tags=["Quiz"])
def submit_quiz(body: s.QuizSubmitIn, db: Session = Depends(get_db), user: models.Student = Depends(get_current_user)):
    seen, results, correct = set(), [], 0
    for ans in body.answers:
        if ans.question_id in seen:
            continue
        seen.add(ans.question_id)
        q = db.get(models.Question, ans.question_id)
        if q is None or q.qtype != "mcq":
            raise HTTPException(404, f"Quiz question {ans.question_id} was not found.")
        ok = bool(ans.answer) and _norm(ans.answer) == _norm(q.correct_answer)
        correct += ok
        db.add(models.Attempt(student_id=user.student_id, question_id=q.question_id, submitted_answer=ans.answer,
                              score=100.0 if ok else 0.0, completed=ok, mode="quiz", time_taken_sec=body.time_taken_sec))
        results.append(s.QuizResultItem(question_id=q.question_id, title=q.title, your_answer=ans.answer, correct=ok, feedback=_feedback(q)))
    db.commit()
    total = len(results)
    return s.QuizResultOut(total=total, correct=correct, score_percent=round(100 * correct / total, 2) if total else 0,
                           time_taken_sec=body.time_taken_sec, results=results)


# ---------------------------------------------------------------- progress
def build_progress(db: Session, student: models.Student) -> s.ProgressOut:
    rows = (db.query(models.Attempt, models.Question.title, models.Question.category)
            .join(models.Question, models.Attempt.question_id == models.Question.question_id)
            .filter(models.Attempt.student_id == student.student_id)
            .order_by(models.Attempt.attempted_at.desc(), models.Attempt.attempt_id.desc()).all())
    best: dict[int, float] = {}
    cat_of: dict[int, str] = {}
    completed_ids: set[int] = set()
    for a, _t, cat in rows:
        best[a.question_id] = max(best.get(a.question_id, 0.0), float(a.score or 0))
        cat_of[a.question_id] = cat
        if a.completed:
            completed_ids.add(a.question_id)
    totals = dict(db.query(models.Question.category, func.count()).group_by(models.Question.category).all())
    categories, recs = [], []
    for cat, total in sorted(totals.items()):
        scores = [v for qid, v in best.items() if cat_of[qid] == cat]
        avg = round(sum(scores) / len(scores), 2) if scores else 0.0
        categories.append(s.CategoryStat(category=cat, total_questions=total, attempted=len(scores), average_best_score=avg))
        if not scores:
            recs.append(f"Start with {cat}: you haven't attempted any questions yet.")
        elif avg < 60:
            recs.append(f"Revise {cat}: your average best score is {avg:.0f}%. Retry the missed questions.")
        elif len(scores) < total:
            recs.append(f"Keep going in {cat}: {total - len(scores)} question(s) left.")
    if not recs:
        recs.append("Great work! Try a timed quiz to test your speed.")
    all_scores = [float(r[0].score or 0) for r in rows]
    return s.ProgressOut(
        student_id=student.student_id, full_name=student.full_name, total_attempts=len(rows),
        questions_attempted=len(best), questions_completed=len(completed_ids), total_questions=sum(totals.values()),
        average_score=round(sum(all_scores) / len(all_scores), 2) if all_scores else 0.0,
        categories=categories, recommendations=recs[:5],
        recent=[s.AttemptRow(attempt_id=a.attempt_id, question_id=a.question_id, title=t, category=c, score=float(a.score or 0),
                             completed=bool(a.completed), mode=a.mode, attempted_at=a.attempted_at) for a, t, c in rows[:10]])


@app.get("/students/me/progress", response_model=s.ProgressOut, tags=["Progress"])
def my_progress(db: Session = Depends(get_db), user: models.Student = Depends(get_current_user)):
    return build_progress(db, user)


@app.get("/students/{student_id}/progress", response_model=s.ProgressOut, tags=["Progress"])
def student_progress(student_id: int, db: Session = Depends(get_db), user: models.Student = Depends(get_current_user)):
    if user.role != "admin" and user.student_id != student_id:
        raise HTTPException(403, "You can only view your own progress.")
    student = db.get(models.Student, student_id)
    if student is None:
        raise HTTPException(404, f"Student {student_id} was not found.")
    return build_progress(db, student)


@app.get("/leaderboard", response_model=list[s.LeaderRow], tags=["Progress"])
def leaderboard(limit: int = Query(10, ge=1, le=50), db: Session = Depends(get_db), _: models.Student = Depends(get_current_user)):
    best = (db.query(models.Attempt.student_id, models.Attempt.question_id, func.max(models.Attempt.score).label("b"))
            .group_by(models.Attempt.student_id, models.Attempt.question_id).subquery())
    rows = (db.query(models.Student.full_name, func.sum(best.c.b), func.count(best.c.question_id))
            .join(best, best.c.student_id == models.Student.student_id)
            .filter(models.Student.role == "student").group_by(models.Student.student_id, models.Student.full_name)
            .order_by(func.sum(best.c.b).desc()).limit(limit).all())
    return [s.LeaderRow(rank=i + 1, full_name=n, points=float(p or 0), questions_attempted=c) for i, (n, p, c) in enumerate(rows)]


# ---------------------------------------------------------------- chatbot
@app.post("/chat", response_model=s.ChatOut, tags=["Chatbot"])
def chat(body: s.ChatIn):
    reply, topic = get_reply(body.message)
    return s.ChatOut(reply=reply, topic=topic, engine=ENGINE)


@app.get("/chat/suggestions", tags=["Chatbot"])
def chat_suggestions():
    return {"suggestions": SUGGESTIONS}


# ---------------------------------------------------------------- frontend
if FRONTEND_DIR.exists():
    app.mount("/app", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
