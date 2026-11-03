# Project Report (template - complete with your team's details)

**Team / Members / IDs / College:**  ...

## 1. Objective
Help engineering students practise Python/placement questions, track progress and get basic technical help from a chatbot.

## 2. Architecture
Browser (HTML/CSS/JS) --Fetch API + JSON--> FastAPI (Pydantic validation, JWT auth, grading, rule-based chatbot) --SQLAlchemy--> MySQL.
Responsibilities: frontend displays; FastAPI validates and applies logic; chatbot function selects a response; MySQL persists data.

## 3. Database design
Tables `students`, `questions`, `attempts` (see `database/schema.sql`). `attempts` references both via foreign keys; indexes on
`category`, `student_id`, `question_id`. Design decisions: `qtype` + JSON `options` allow MCQ and coding in one table;
`role` enables admin features; passwords stored as salted hashes. Explain any fields your team added.

## 4. Key design decisions
- JWT instead of server sessions (stateless API). - Coding questions self-assessed; code never executed (security).
- Hidden answers returned only after an attempt. - ORM for parameterized queries.

## 5. Rule-based chatbot vs LLM
Describe how keyword matching works, why it is NOT generative AI, and how `LLMProvider` could replace `RuleBasedProvider`
(backend-only key, cost, hallucination risk, need to treat answers as suggestions).

## 6. Testing
Automated: `python -m pytest -q` (7 tests: health, listing/filter/404, auth, attempts/progress, quiz, admin permissions/CRUD, chatbot).
Manual checklist: tick each item from Section 11 of the guide and attach screenshots (question list, detail, progress, chatbot).
Include results for: empty input, unknown ID, backend stopped (frontend shows "Cannot reach the server"), invalid token.

## 7. Limitations and future work
Sandboxed code runner, password reset, rate limiting, refresh tokens, optional LLM integration, deployment with HTTPS.

## 8. Individual contributions
Table of members and tasks.
