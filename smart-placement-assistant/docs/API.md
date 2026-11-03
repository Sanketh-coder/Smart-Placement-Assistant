# API Reference

Base URL `http://localhost:8000`. Interactive docs: `/docs`. Protected routes need `Authorization: Bearer <token>`.
Errors use `{"detail": "message"}`; validation errors (422) return a list of field problems.

## Auth
**POST /auth/register** (201) body `{"full_name":"Asha Rao","email":"asha@example.com","password":"Passw0rd!!","branch":"CSE","study_year":3}`
-> `{"access_token":"...","token_type":"bearer","user":{...}}`. Errors: 409 email exists, 422 invalid.

**POST /auth/login** body `{"email":"student@example.com","password":"your-password"}` -> same as above. Errors: 401 wrong credentials.

**GET /auth/me** -> current user. Errors: 401.

## Questions
**GET /questions?category=&difficulty=&qtype=&search=&skip=0&limit=50** -> list of
`{"question_id":1,"title":"Reverse a String","category":"Strings","difficulty":"Beginner","qtype":"coding","description":"...","sample_input":"hello","expected_output":"olleh","options":null}`

**GET /questions/{id}** -> one question. Errors: 404 unknown id, 422 non-integer id.
**GET /questions/meta** -> `{"categories":[...],"difficulties":[...],"types":[...]}`

**POST /questions** (admin, 201) / **PUT /questions/{id}** (admin) / **DELETE /questions/{id}** (admin, 204)
body `{"title":"Sum of List","category":"Lists","difficulty":"Beginner","qtype":"coding","description":"Sum all numbers."}`
MCQ additionally needs `options` (>=2) and `correct_answer` equal to one option. Errors: 401, 403, 404, 422.

## Attempts
**POST /attempts** (user, 201) body `{"question_id":13,"submitted_answer":"Lists are mutable; tuples are immutable"}`
-> `{"attempt_id":7,"question_id":13,"score":100.0,"completed":true,"graded_by":"auto","feedback":{"correct_answer":"...","solution":null,"explanation":"..."}}`
Coding: `{"question_id":1,"submitted_answer":"def reverse(s): ...","completed":true}` -> `graded_by:"self"`.
Errors: 401, 404 unknown question, 422 empty answer.

## Progress
**GET /students/me/progress** and **GET /students/{id}/progress** (own id, or admin) ->
`{"student_id":2,"full_name":"Demo Student","total_attempts":5,"questions_attempted":4,"questions_completed":3,"total_questions":22,"average_score":60.0,"categories":[{"category":"Strings","total_questions":4,"attempted":2,"average_best_score":50.0}],"recommendations":["Revise Strings: ..."],"recent":[...]}`
Errors: 401, 403 (other student), 404.

**GET /leaderboard?limit=10** -> `[{"rank":1,"full_name":"...","points":300.0,"questions_attempted":4}]`

## Quiz
**GET /quiz?count=5&category=&difficulty=** -> shuffled MCQ questions without answers. 404 if none match.
**POST /quiz/submit** body `{"answers":[{"question_id":13,"answer":"..."}],"time_taken_sec":95}`
-> `{"total":5,"correct":4,"score_percent":80.0,"time_taken_sec":95,"results":[{"question_id":13,"title":"...","your_answer":"...","correct":true,"feedback":{...}}]}`

## Admin
**GET /admin/stats** -> `{"students":1,"questions":22,"attempts":10,"average_score":55.0}`; **GET /admin/questions** -> questions including answers.

## Chatbot
**POST /chat** body `{"message":"What is FastAPI?"}` -> `{"reply":"FastAPI is ...","topic":"fastapi","engine":"rule-based"}`.
Unknown input -> `topic:null` and a message saying there is no predefined answer. Empty message -> 422.
**GET /chat/suggestions** -> `{"suggestions":["hello","python",...]}`
