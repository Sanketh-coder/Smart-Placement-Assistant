"""Seed data: demo admin, demo student and 22 questions. Idempotent (only runs on an empty table)."""
import os

from sqlalchemy.orm import Session

import models
from security import hash_password


def C(title, cat, diff, desc, sin, sout, sol, expl=None):
    return dict(title=title, category=cat, difficulty=diff, qtype="coding", description=desc,
                sample_input=sin, expected_output=sout, solution=sol, explanation=expl)


def M(title, cat, diff, desc, opts, ans, expl):
    return dict(title=title, category=cat, difficulty=diff, qtype="mcq", description=desc,
                options=opts, correct_answer=ans, explanation=expl)


QUESTIONS = [
    C("Reverse a String", "Strings", "Beginner", "Write a function that returns the reverse of a string.", "hello", "olleh",
      "def reverse(s):\n    return s[::-1]", "Slicing with a step of -1 walks the string backwards."),
    C("Palindrome Check", "Strings", "Beginner", "Return True if a string reads the same forwards and backwards (ignore case).",
      "Madam", "True", "def is_pal(s):\n    s = s.lower()\n    return s == s[::-1]"),
    C("Count Vowels", "Strings", "Beginner", "Count the vowels (a, e, i, o, u) in a string.", "interview", "4",
      "def count_vowels(s):\n    return sum(ch in 'aeiou' for ch in s.lower())"),
    C("Anagram Check", "Strings", "Intermediate", "Check whether two strings are anagrams of each other.", "listen silent", "True",
      "def anagram(a, b):\n    return sorted(a.lower()) == sorted(b.lower())", "Sorting both strings makes equal letter multisets identical."),
    C("Largest Number in a List", "Lists", "Beginner", "Find the largest number without using max().", "[3, 9, 2, 7]", "9",
      "def largest(nums):\n    best = nums[0]\n    for n in nums:\n        if n > best:\n            best = n\n    return best"),
    C("Remove Duplicates (Keep Order)", "Lists", "Intermediate", "Remove duplicates from a list while keeping the first occurrence order.",
      "[1, 2, 2, 3, 1]", "[1, 2, 3]",
      "def dedupe(items):\n    seen, out = set(), []\n    for x in items:\n        if x not in seen:\n            seen.add(x)\n            out.append(x)\n    return out",
      "A set gives O(1) membership checks."),
    C("Two Sum", "Lists", "Intermediate", "Return indices of two numbers that add up to a target.", "nums=[2,7,11,15], target=9", "[0, 1]",
      "def two_sum(nums, target):\n    seen = {}\n    for i, n in enumerate(nums):\n        if target - n in seen:\n            return [seen[target - n], i]\n        seen[n] = i",
      "One pass with a dictionary gives O(n) time."),
    C("Word Frequency", "Dictionaries", "Intermediate", "Count how many times each word appears in a sentence.", "to be or not to be",
      "{'to': 2, 'be': 2, 'or': 1, 'not': 1}",
      "def freq(text):\n    counts = {}\n    for w in text.lower().split():\n        counts[w] = counts.get(w, 0) + 1\n    return counts"),
    C("Factorial Function", "Functions", "Beginner", "Write a function that returns n! for n >= 0.", "5", "120",
      "def fact(n):\n    return 1 if n <= 1 else n * fact(n - 1)"),
    C("Fibonacci Series", "Functions", "Intermediate", "Return the first n Fibonacci numbers.", "6", "[0, 1, 1, 2, 3, 5]",
      "def fib(n):\n    a, b, out = 0, 1, []\n    for _ in range(n):\n        out.append(a)\n        a, b = b, a + b\n    return out"),
    C("FizzBuzz", "Numbers", "Beginner", "For 1..n print Fizz (multiples of 3), Buzz (5), FizzBuzz (both), else the number.", "5", "1 2 Fizz 4 Buzz",
      "def fizzbuzz(n):\n    for i in range(1, n + 1):\n        print('Fizz' * (i % 3 == 0) + 'Buzz' * (i % 5 == 0) or i)"),
    C("Prime Number Check", "Numbers", "Intermediate", "Check whether a number is prime efficiently.", "29", "True",
      "def is_prime(n):\n    if n < 2:\n        return False\n    i = 2\n    while i * i <= n:\n        if n % i == 0:\n            return False\n        i += 1\n    return True",
      "Only test divisors up to sqrt(n)."),
    M("List vs Tuple", "Python Basics", "Beginner", "Which statement about Python lists and tuples is correct?",
      ["Lists are mutable; tuples are immutable", "Tuples are mutable; lists are immutable", "Both are immutable", "Neither can hold mixed types"],
      "Lists are mutable; tuples are immutable", "Lists can be changed in place; tuples cannot."),
    M("Set Length", "Python Basics", "Beginner", "What does len({1, 2, 2, 3}) return?", ["4", "3", "2", "Error"], "3",
      "Sets drop duplicates, leaving {1, 2, 3}."),
    M("is vs ==", "Python Basics", "Intermediate", "What does the `is` operator compare?",
      ["Value equality", "Object identity", "Type only", "String length"], "Object identity", "`==` compares values; `is` checks whether both names refer to the same object."),
    M("Creating a Resource", "REST APIs", "Beginner", "Which HTTP method is normally used to create a new resource?", ["GET", "POST", "DELETE", "HEAD"], "POST",
      "POST submits data to create a resource; GET only reads."),
    M("Not Found Status", "REST APIs", "Beginner", "Which status code means the requested resource does not exist?", ["200", "201", "404", "500"], "404",
      "404 Not Found; 500 is a server error."),
    M("Pydantic Purpose", "FastAPI", "Intermediate", "What is Pydantic mainly used for in FastAPI?",
      ["Drawing the UI", "Validating and parsing data models", "Running SQL", "Hosting static files"], "Validating and parsing data models",
      "FastAPI uses Pydantic to validate request/response data from type hints."),
    M("Docs URL", "FastAPI", "Beginner", "Where does FastAPI serve interactive API documentation by default?", ["/docs", "/help", "/swagger.txt", "/admin"], "/docs",
      "Swagger UI is at /docs and ReDoc at /redoc."),
    M("Primary Key", "MySQL", "Beginner", "What does a PRIMARY KEY guarantee?",
      ["Rows are sorted alphabetically", "Each row is uniquely identified and non-NULL", "Columns are encrypted", "Tables load faster always"],
      "Each row is uniquely identified and non-NULL", "A primary key uniquely identifies each row."),
    M("Preventing SQL Injection", "MySQL", "Intermediate", "Which practice best prevents SQL injection?",
      ["Concatenating user input into queries", "Hiding the database name", "Using parameterized queries", "Using longer table names"],
      "Using parameterized queries", "Placeholders keep user input as data, never as SQL code."),
    M("JOIN Purpose", "MySQL", "Intermediate", "What does an INNER JOIN return?",
      ["All rows from both tables", "Only rows with matching values in both tables", "Only unmatched rows", "Table structure only"],
      "Only rows with matching values in both tables", "INNER JOIN keeps rows where the join condition matches in both tables."),
]


def seed(db: Session) -> None:
      if db.query(models.Student).count() == 0:
        admin_pw = os.getenv("SEED_ADMIN_PASSWORD")
        student_pw = os.getenv("SEED_STUDENT_PASSWORD")
        if admin_pw and student_pw:
            db.add(models.Student(full_name="Demo Admin", email="admin@example.com", role="admin",
                                  password_hash=hash_password(admin_pw)))
            db.add(models.Student(full_name="Demo Student", email="student@example.com", role="student", branch="CSE", study_year=3,
                                  password_hash=hash_password(student_pw)))
        else:
            print("SEED_ADMIN_PASSWORD / SEED_STUDENT_PASSWORD not set: demo users were not created.")
      db.commit()


if __name__ == "__main__":
    from database import Base, SessionLocal, engine
    Base.metadata.create_all(engine)
    with SessionLocal() as s:
        seed(s)
    print("Seeded.")
