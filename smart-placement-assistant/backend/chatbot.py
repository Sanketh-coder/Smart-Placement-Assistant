"""Rule-based chatbot (NOT generative AI).

`get_reply` picks a predefined answer by keyword matching. The `ResponseProvider`
interface lets a team later plug in an LLM-backed provider without touching the API
or the frontend (see LLMProvider at the bottom; it is intentionally not enabled).
"""
import re
from typing import Protocol

ENGINE = "rule-based"
SUGGESTIONS = ["hello", "python", "REST API", "FastAPI", "MySQL", "interview", "help"]

# (topic, keywords, answer). More specific rules are listed first.
RULES: list[tuple[str, list[str], str]] = [
    ("help", ["help", "topics", "what can you do"],
     "I can answer basic questions about: Python, REST APIs, FastAPI, MySQL/databases, SQL injection, "
     "Pydantic, JWT/login and interview preparation. Try: 'What is FastAPI?' or 'How do I prepare for an interview?'"),
    ("greeting", ["hello", "hi", "hey"],
     "Hello! I'm the placement assistant. I use predefined rules, not generative AI. Ask about Python, REST APIs, "
     "FastAPI, MySQL or interviews, or type 'help' for the full list."),
    ("sql_injection", ["sql injection", "injection", "parameterized", "parameterised"],
     "SQL injection happens when user input is concatenated into SQL text. Prevent it with parameterized queries "
     "(placeholders) or an ORM, and validate inputs on the backend."),
    ("pydantic", ["pydantic", "validation", "validate"],
     "Pydantic defines data models with types and constraints. FastAPI uses it to validate request bodies and shape "
     "responses, returning HTTP 422 automatically when input is invalid."),
    ("jwt", ["jwt", "token", "login", "authentication", "auth"],
     "JWT (JSON Web Token) is a signed token the server issues after login. The browser sends it in the "
     "'Authorization: Bearer <token>' header; the server verifies the signature instead of storing sessions. "
     "Passwords must be stored as salted hashes, never as plain text."),
    ("fastapi", ["fastapi", "uvicorn"],
     "FastAPI is a modern Python framework for building APIs. It uses type hints and Pydantic for validation and "
     "generates interactive documentation at /docs automatically. Run it with Uvicorn."),
    ("rest_api", ["rest api", "rest", "api", "http", "endpoint"],
     "A REST API lets clients talk to a server over HTTP using JSON. Common methods: GET (read), POST (create), "
     "PUT/PATCH (update), DELETE (remove). Status codes: 200 OK, 201 Created, 400/422 bad input, 401/403 auth, 404 not found."),
    ("mysql", ["mysql", "database", "sql", "table", "join", "primary key"],
     "MySQL is a relational database that stores data in tables (rows and columns). Primary keys identify rows, "
     "foreign keys link tables, and JOIN combines related rows. Use SELECT/INSERT/UPDATE/DELETE for CRUD."),
    ("python", ["python", "list", "dictionary", "tuple"],
     "Python is a readable, general-purpose language used for web backends, automation, data science and scripting. "
     "Interviews focus on strings, lists, dictionaries, functions and basic algorithms."),
    ("interview", ["interview", "placement", "prepare", "preparation"],
     "Practise daily: solve a few questions per topic, explain your approach aloud, then check edge cases (empty "
     "input, duplicates, large values). Review weak topics on your Progress page. Treat this advice as a "
     "suggestion, not guaranteed interview guidance."),
]

FALLBACK = ("I don't have a predefined answer for that. I currently support: Python, REST APIs, FastAPI, "
            "MySQL, Pydantic, JWT/login, SQL injection and interview preparation. Type 'help' to see examples.")


class ResponseProvider(Protocol):
    def reply(self, message: str) -> tuple[str, str | None]: ...


class RuleBasedProvider:
    def reply(self, message: str) -> tuple[str, str | None]:
        text = message.lower()
        best: tuple[int, str, str] | None = None
        for order, (topic, keywords, answer) in enumerate(RULES):
            for kw in keywords:
                if re.search(rf"(?<![a-z0-9]){re.escape(kw)}(?![a-z0-9])", text):
                    score = len(kw) * 10 - order  # longer keyword wins; earlier rule breaks ties
                    if best is None or score > best[0]:
                        best = (score, topic, answer)
        return (best[2], best[1]) if best else (FALLBACK, None)


class LLMProvider:  # pragma: no cover - placeholder for a future extension
    """Example hook: call a hosted LLM from the BACKEND only (keep API keys in env vars; usage may be billed)."""
    engine = "llm"

    def reply(self, message: str) -> tuple[str, str | None]:
        raise NotImplementedError("Connect your LLM SDK here and return (text, topic).")


provider: ResponseProvider = RuleBasedProvider()


def get_reply(message: str) -> tuple[str, str | None]:
    return provider.reply(message)
