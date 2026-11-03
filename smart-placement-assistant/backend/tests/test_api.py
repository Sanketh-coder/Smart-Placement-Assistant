def test_health(client):
    assert client.get("/").json()["status"] == "ok"
    assert client.get("/health/db").json() == {"database": "ok"}


def test_questions_list_filter_and_404(client):
    allq = client.get("/questions").json()
    assert len(allq) >= 20
    assert all("correct_answer" not in q and "solution" not in q for q in allq)
    assert all(q["category"] == "Strings" for q in client.get("/questions?category=Strings").json())
    assert client.get("/questions?search=palindrome").json()
    assert client.get("/questions/99999").status_code == 404
    assert client.get("/questions/abc").status_code == 422


def test_auth_register_login_and_errors(client):
    body = {"full_name": "Test User", "email": "t@example.com", "password": "Passw0rd!!"}
    assert client.post("/auth/register", json=body).status_code == 201
    assert client.post("/auth/register", json=body).status_code == 409
    assert client.post("/auth/login", json={"email": "t@example.com", "password": "wrong"}).status_code == 401
    assert client.post("/auth/register", json={**body, "email": "bad", "password": "x"}).status_code == 422
    assert client.get("/auth/me").status_code == 401


def test_attempt_and_progress(client, student):
    mcq = next(q for q in client.get("/questions?qtype=mcq").json())
    assert client.post("/attempts", json={"question_id": mcq["question_id"]}).status_code == 401
    assert client.post("/attempts", json={"question_id": mcq["question_id"]}, headers=student).status_code == 422
    wrong = client.post("/attempts", json={"question_id": mcq["question_id"], "submitted_answer": "zzz"}, headers=student).json()
    assert wrong["score"] == 0 and wrong["feedback"]["correct_answer"]
    ok = client.post("/attempts", json={"question_id": mcq["question_id"], "submitted_answer": wrong["feedback"]["correct_answer"]}, headers=student).json()
    assert ok["score"] == 100 and ok["graded_by"] == "auto"
    coding = client.get("/questions?qtype=coding").json()[0]
    r = client.post("/attempts", json={"question_id": coding["question_id"], "submitted_answer": "x", "completed": True}, headers=student)
    assert r.status_code == 201 and r.json()["graded_by"] == "self"
    assert client.post("/attempts", json={"question_id": 99999, "completed": True}, headers=student).status_code == 404
    p = client.get("/students/me/progress", headers=student).json()
    assert p["total_attempts"] >= 3 and p["questions_completed"] >= 2 and p["recommendations"]
    assert client.get("/students/1/progress", headers=student).status_code == 403


def test_quiz_flow(client, student):
    quiz = client.get("/quiz?count=3", headers=student).json()
    assert len(quiz) == 3 and all("correct_answer" not in q for q in quiz)
    res = client.post("/quiz/submit", json={"answers": [{"question_id": q["question_id"], "answer": None} for q in quiz], "time_taken_sec": 30}, headers=student).json()
    assert res["total"] == 3 and res["correct"] == 0 and res["time_taken_sec"] == 30
    assert client.get("/leaderboard", headers=student).status_code == 200


def test_admin_crud_and_permissions(client, admin, student):
    new = {"title": "Sum of List", "category": "Lists", "difficulty": "Beginner", "qtype": "coding", "description": "Sum all numbers."}
    assert client.post("/questions", json=new, headers=student).status_code == 403
    assert client.post("/questions", json=new).status_code == 401
    qid = client.post("/questions", json=new, headers=admin).json()["question_id"]
    assert client.put(f"/questions/{qid}", json={**new, "title": "Sum List v2"}, headers=admin).json()["title"] == "Sum List v2"
    bad_mcq = {**new, "qtype": "mcq", "options": ["a", "b"], "correct_answer": "c"}
    assert client.post("/questions", json=bad_mcq, headers=admin).status_code == 422
    assert client.delete(f"/questions/{qid}", headers=admin).status_code == 204
    assert client.get(f"/questions/{qid}").status_code == 404
    assert client.get("/admin/stats", headers=admin).json()["questions"] >= 20


def test_chatbot(client):
    for msg, topic in [("hello", "greeting"), ("What is FastAPI?", "fastapi"), ("explain REST API", "rest_api"),
                       ("mysql tables", "mysql"), ("how to prepare for interview", "interview"), ("help", "help"),
                       ("how to stop sql injection", "sql_injection")]:
        r = client.post("/chat", json={"message": msg}).json()
        assert r["topic"] == topic, (msg, r)
        assert r["engine"] == "rule-based"
    unknown = client.post("/chat", json={"message": "what is the weather"}).json()
    assert unknown["topic"] is None and "predefined answer" in unknown["reply"]
    assert client.post("/chat", json={"message": "   "}).status_code == 422
    assert client.post("/chat", json={}).status_code == 422
