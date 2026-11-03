# Smart Placement Preparation Assistant (Advanced Edition)

A full-stack placement-prep platform: **Python + FastAPI + MySQL + vanilla JavaScript (Fetch API)** with JWT login,
role-based admin tools, timed auto-graded quizzes, topic-based recommendations, a leaderboard and a **rule-based chatbot**
(not generative AI) designed so an LLM can be plugged in later.

## What's new versus the basic guide
| Area | Basic guide | This edition |
|---|---|---|
| Users | seeded demo student | Register/login with **JWT**, salted PBKDF2 password hashes, roles (student / admin) |
| Questions | list + detail | + search, filters, pagination, **MCQ and coding** types |
| Admin | optional | Admin page: add / edit / delete questions, platform stats |
| Quiz | optional | **Timed MCQ quiz**, shuffled options, auto-scoring, auto-submit on timeout |
| Progress | counts | Per-topic stats, rule-based **practice recommendations**, recent attempts, leaderboard |
| DB access | parameterized SQL | **SQLAlchemy ORM** (parameterized by design), indexes, FK constraints |
| Reliability | manual checklist | **Automated pytest suite**, global DB-error handler (503), clear 4xx errors |
| Chatbot | 7 rules | 10 topics, whole-word keyword scoring, `ResponseProvider` interface for a future LLM |

## Project structure
```
smart-placement-assistant/
├── backend/    main.py, database.py, models.py, schemas.py, security.py, chatbot.py, seed.py, tests/
├── frontend/   index, questions, question, quiz, progress, chatbot, admin (.html) + style.css + app.js
├── database/   schema.sql
├── docs/       API.md, REPORT.md (project report template)
├── screenshots/  (add your 4+ screenshots here)
└── README.md
```

## Setup
**Prerequisites:** Python 3.10+, MySQL 8 (or 5.7+ with JSON support).

```bash
# 1. Database
mysql -u root -p < database/schema.sql
#    (recommended) create a least-privilege user - see the comments at the bottom of schema.sql

# 2. Backend
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # Windows: copy .env.example .env  -> edit DB_PASSWORD and JWT_SECRET
python seed.py                     # optional: tables + 22 questions + demo accounts (also runs automatically on startup)
uvicorn main:app --reload
```
Open **http://localhost:8000/app/** for the website and **http://localhost:8000/docs** for the interactive API docs.

Generate a strong secret: `python -c "import secrets; print(secrets.token_urlsafe(48))"`

   **Demo accounts:** on first start the app creates `admin@example.com` and `student@example.com`.
   Their passwords come from SEED_ADMIN_PASSWORD and SEED_STUDENT_PASSWORD in your .env file.

**Quick try without MySQL:** set `DATABASE_URL=sqlite:///./dev.db` in `.env`.

### Run the tests
```bash
cd backend && python -m pytest -q      # uses a temporary SQLite DB, no MySQL needed
```

## Features
- Browse / search / filter questions; view description and sample input/output
- Submit answers: MCQ is auto-graded; coding is self-assessed (code is **never executed** on the server - a deliberate security decision) and the reference solution is revealed after you submit
- Timed quiz with shuffled options and instant feedback
- Progress dashboard: totals, per-topic bars, recommendations, history, leaderboard
- Chatbot: predefined answers via `POST /chat`
- Admin: question CRUD + stats (role-protected on the backend, not just hidden in the UI)

## API summary (full details in `docs/API.md`)
| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | `/` , `/health/db` | - | Health checks |
| POST | `/auth/register`, `/auth/login` | - | Create account / get JWT |
| GET | `/auth/me` | user | Current user |
| GET | `/questions`, `/questions/{id}`, `/questions/meta` | - | List (filters) / detail / filter values |
| POST/PUT/DELETE | `/questions`, `/questions/{id}` | admin | Manage questions |
| POST | `/attempts` | user | Save an attempt (graded) |
| GET | `/students/me/progress`, `/students/{id}/progress` | user (own) / admin | Progress summary |
| GET / POST | `/quiz`, `/quiz/submit` | user | Start / submit a timed quiz |
| GET | `/leaderboard` | user | Top students |
| GET | `/admin/stats`, `/admin/questions` | admin | Admin data |
| POST | `/chat`, GET `/chat/suggestions` | - | Rule-based chatbot |

## Security notes
- Passwords: salted PBKDF2-SHA256 (200k iterations). JWT secret and DB password live only in `.env` (git-ignored).
- All SQL goes through SQLAlchemy bound parameters - no string-built SQL.
- Inputs validated on the backend with Pydantic; the frontend renders server data via `textContent` (no `innerHTML`) to avoid XSS.
- Authorization is enforced server-side (admin routes, own-progress check). Hidden answers are never sent to students before they answer.
- For production also add: HTTPS, rate limiting on `/auth/*`, token refresh/revocation, and restrict `CORS_ORIGINS`.

## Rule-based chatbot vs Generative AI
The chatbot matches whole-word keywords and returns predefined text: deterministic, free, offline, but it cannot answer
unseen questions. An LLM understands free text and generates new answers, but costs money, needs an API key and can be wrong.
To upgrade: implement `LLMProvider.reply()` in `chatbot.py`, call the model **from the backend only**, keep the key in an
environment variable, and set `provider = LLMProvider()`. The endpoint and frontend stay unchanged.

## Known limitations
- Coding answers are self-assessed (no sandboxed code runner).
- No password reset / email verification; no refresh tokens.
- Demo accounts are seeded; remove them for real deployments.

## Team contributions
| Member | Role | Contribution |
|---|---|---|
| | Backend | |
| | Database | |
| | Frontend | |
| | Chatbot & QA | |
