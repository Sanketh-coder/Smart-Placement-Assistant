/* Smart Placement Assistant - shared frontend logic. All data comes from FastAPI via fetch(). */
const API = window.API_BASE ?? (["8000", ""].includes(location.port) && location.protocol.startsWith("http") ? "" : "http://127.0.0.1:8000");
const $ = (sel, root = document) => root.querySelector(sel);
const store = {
  get token() { return localStorage.getItem("token"); },
  get user() { try { return JSON.parse(localStorage.getItem("user")); } catch { return null; } },
  save(t, u) { localStorage.setItem("token", t); localStorage.setItem("user", JSON.stringify(u)); },
  clear() { localStorage.removeItem("token"); localStorage.removeItem("user"); },
};

// Build DOM safely (textContent only - no innerHTML with server data => no XSS).
function h(tag, attrs = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === "class") e.className = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else if (v !== false && v != null) e.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat()) if (kid != null && kid !== false) e.append(kid.nodeType ? kid : document.createTextNode(kid));
  return e;
}
const clear = (e) => { e.replaceChildren(); return e; };
// replaceChildren() would print "null"/"false" as text, so drop empty children first.
const fill = (box, ...kids) => box.replaceChildren(...kids.flat(Infinity).filter((k) => k != null && k !== false));
const note = (text, kind = "info") => h("div", { class: `msg ${kind}`, role: kind === "error" ? "alert" : "status" }, text);

async function api(path, { method = "GET", body } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (store.token) headers.Authorization = `Bearer ${store.token}`;
  let res;
  try { res = await fetch(API + path, { method, headers, body: body ? JSON.stringify(body) : undefined }); }
  catch { throw new Error("Cannot reach the server. Check that the backend is running and try again."); }
  if (res.status === 204) return null;
  let data = null;
  try { data = await res.json(); } catch { /* non-JSON body */ }
  if (res.status === 401 && store.token) { store.clear(); location.href = "index.html?expired=1"; }
  if (!res.ok) {
    const d = data && data.detail;
    throw new Error(typeof d === "string" ? d : Array.isArray(d) ? d.map((x) => `${(x.loc || []).slice(-1)[0]}: ${x.msg}`).join("; ") : `Request failed (${res.status})`);
  }
  return data;
}

const PAGES = [["questions.html", "Questions"], ["quiz.html", "Quiz"], ["progress.html", "Progress"], ["chatbot.html", "Chatbot"]];
function renderNav(page) {
  const user = store.user, links = [...PAGES];
  if (user && user.role === "admin") links.push(["admin.html", "Admin"]);
  const nav = h("div", { class: "in" }, h("a", { class: "brand", href: "questions.html" }, "Placement Assistant"),
    ...(user ? links.map(([href, label]) => h("a", { class: "link" + (href.startsWith(page) ? " on" : ""), href }, label)) : []),
    user ? h("span", { class: "badge" }, user.full_name) : null,
    user ? h("button", { class: "ghost", onclick: () => { store.clear(); location.href = "index.html"; } }, "Log out") : null);
  clear($("#nav")).append(nav);
}
const pct = (n) => `${Math.round(n)}%`;
const mmss = (s) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
const qid = () => Number(new URLSearchParams(location.search).get("id"));
function guard(box, fn) { return fn().catch((e) => box.replaceChildren(note(e.message, "error"))); }

/* ---------- Login / register ---------- */
function pageLogin() {
  if (store.token) { location.href = "questions.html"; return; }
  const box = $("#box");
  if (new URLSearchParams(location.search).has("expired")) box.before(note("Your session expired. Please log in again.", "info"));
  let mode = "login";
  const render = () => {
    const f = h("form", { novalidate: true, onsubmit: async (ev) => {
      ev.preventDefault();
      const d = Object.fromEntries(new FormData(ev.target));
      if (!d.email.trim() || !d.password) return show(note("Email and password are required.", "error"));
      if (mode === "register") { d.study_year = d.study_year ? Number(d.study_year) : null; if (!d.branch) d.branch = null; }
      try {
        const r = await api(mode === "login" ? "/auth/login" : "/auth/register", { method: "POST", body: d });
        store.save(r.access_token, r.user); location.href = "questions.html";
      } catch (e) { show(note(e.message, "error")); }
    } },
      mode === "register" ? h("div", {}, h("label", { for: "fn" }, "Full name"), h("input", { id: "fn", name: "full_name", required: true, autocomplete: "name" })) : null,
      h("label", { for: "em" }, "Email"), h("input", { id: "em", name: "email", type: "email", autocomplete: "email", required: true }),
      h("label", { for: "pw" }, "Password" + (mode === "register" ? " (min 8 characters)" : "")), h("input", { id: "pw", name: "password", type: "password", autocomplete: mode === "login" ? "current-password" : "new-password", required: true }),
      mode === "register" ? h("div", { class: "row" }, h("div", {}, h("label", { for: "br" }, "Branch (optional)"), h("input", { id: "br", name: "branch" })),
        h("div", {}, h("label", { for: "yr" }, "Year (optional)"), h("input", { id: "yr", name: "study_year", type: "number", min: 1, max: 6 }))) : null,
      h("p", {}, h("button", { type: "submit" }, mode === "login" ? "Log in" : "Create account")), h("div", { id: "fmsg" }));
    const show = (n) => clear($("#fmsg", f)).append(n);
    box.replaceChildren(h("div", { class: "tabs" },
      h("button", { class: mode === "login" ? "on" : "", onclick: () => { mode = "login"; render(); } }, "Log in"),
      h("button", { class: mode === "register" ? "on" : "", onclick: () => { mode = "register"; render(); } }, "Register")), f,
      h("p", { class: "msg info" }, "Demo accounts: student@example.com / Student@12345, admin@example.com / Admin@12345 (change these after first use)."));
  };
  render();
}

/* ---------- Question list ---------- */
async function pageQuestions() {
  const list = $("#list"), cat = $("#cat"), diff = $("#diff"), search = $("#search"), typ = $("#typ");
  const meta = await api("/questions/meta");
  meta.categories.forEach((c) => cat.append(h("option", { value: c }, c)));
  meta.difficulties.forEach((c) => diff.append(h("option", { value: c }, c)));
  const load = () => guard(list, async () => {
    list.replaceChildren(note("Loading questions...", "info"));
    const p = new URLSearchParams();
    if (cat.value) p.set("category", cat.value); if (diff.value) p.set("difficulty", diff.value);
    if (typ.value) p.set("qtype", typ.value); if (search.value.trim()) p.set("search", search.value.trim());
    const qs = await api("/questions?" + p);
    if (!qs.length) return list.replaceChildren(note("No questions match these filters. Clear a filter to see more.", "info"));
    list.replaceChildren(...qs.map((q) => h("div", { class: "q" },
      h("div", {}, h("a", { href: `question.html?id=${q.question_id}` }, q.title), h("div", {}, h("span", { class: "badge" }, q.category), h("span", { class: `badge ${q.difficulty}` }, q.difficulty), h("span", { class: "badge" }, q.qtype === "mcq" ? "Multiple choice" : "Coding"))),
      h("a", { class: "btn ghost", href: `question.html?id=${q.question_id}` }, "Open"))));
  });
  let t; [cat, diff, typ].forEach((e) => e.addEventListener("change", load));
  search.addEventListener("input", () => { clearTimeout(t); t = setTimeout(load, 300); });
  load();
}

/* ---------- Question detail + attempt ---------- */
async function pageQuestion() {
  const box = $("#box"); const id = qid();
  if (!id) return box.replaceChildren(note("No question selected. Go back to the question list.", "error"));
  await guard(box, async () => {
    const q = await api(`/questions/${id}`);
    const result = h("div", { id: "result" });
    const form = h("form", { novalidate: true, onsubmit: async (ev) => {
      ev.preventDefault(); const fd = new FormData(form);
      const body = { question_id: id, submitted_answer: (fd.get("answer") || "").toString().trim() || null, completed: fd.get("done") === "on" };
      if (q.qtype === "mcq" && !body.submitted_answer) return result.replaceChildren(note("Choose an answer first.", "error"));
      if (q.qtype === "coding" && !body.submitted_answer && !body.completed) return result.replaceChildren(note("Write your solution or tick 'I solved it'.", "error"));
      try {
        const r = await api("/attempts", { method: "POST", body });
        const f = r.feedback, out = [note(q.qtype === "mcq" ? (r.completed ? "Correct! Attempt saved (100%)." : "Not quite. Attempt saved (0%).") : (r.completed ? "Attempt saved as completed." : "Attempt saved. Compare with the reference solution and retry."), r.completed ? "ok" : "info")];
        if (f.correct_answer) out.push(h("p", {}, h("b", {}, "Correct answer: "), f.correct_answer));
        if (f.solution) out.push(h("h3", {}, "Reference solution"), h("pre", {}, f.solution));
        if (f.explanation) out.push(h("p", {}, h("b", {}, "Why: "), f.explanation));
        result.replaceChildren(...out); $("#go", form).disabled = true;
      } catch (e) { result.replaceChildren(note(e.message, "error")); }
    } },
      q.qtype === "mcq"
        ? (q.options || []).map((o, i) => h("label", { class: "opt", for: `o${i}` }, h("input", { type: "radio", name: "answer", id: `o${i}`, value: o }), o))
        : [h("label", { for: "ans" }, "Your solution"), h("textarea", { id: "ans", name: "answer", placeholder: "Write your Python code here..." }),
          h("label", { class: "opt" }, h("input", { type: "checkbox", name: "done" }), "I solved it (self-assessed; code is never executed on the server)")],
      h("p", {}, h("button", { id: "go", type: "submit" }, "Submit attempt")));
    fill(box, h("a", { href: "questions.html" }, "Back to questions"), h("h1", {}, q.title),
      h("p", {}, h("span", { class: "badge" }, q.category), h("span", { class: `badge ${q.difficulty}` }, q.difficulty)),
      h("p", {}, q.description),
      q.sample_input ? [h("h3", {}, "Sample input"), h("pre", {}, q.sample_input)] : null,
      q.expected_output ? [h("h3", {}, "Sample output"), h("pre", {}, q.expected_output)] : null, form, result);
  });
}

/* ---------- Timed quiz ---------- */
async function pageQuiz() {
  const box = $("#box"); const meta = await api("/questions/meta").catch(() => ({ categories: [] }));
  const setup = () => {
    const cat = h("select", { id: "qc" }, h("option", { value: "" }, "All topics"), meta.categories.map((c) => h("option", { value: c }, c)));
    const n = h("input", { id: "qn", type: "number", min: 1, max: 20, value: 5 });
    box.replaceChildren(h("h1", {}, "Timed quiz"), h("p", { class: "msg info" }, "You get 1 minute per question. The quiz auto-submits when time runs out."),
      h("div", { class: "row" }, h("div", {}, h("label", { for: "qc" }, "Topic"), cat), h("div", {}, h("label", { for: "qn" }, "Questions"), n),
        h("div", {}, h("button", { onclick: () => start(cat.value, Number(n.value) || 5) }, "Start quiz"))), h("div", { id: "qerr" }));
  };
  const start = async (category, count) => {
    let qs;
    try { qs = await api(`/quiz?count=${count}${category ? "&category=" + encodeURIComponent(category) : ""}`); }
    catch (e) { return $("#qerr").replaceChildren(note(e.message, "error")); }
    let left = qs.length * 60; const total = left; let finished = false;
    const timer = h("span", { class: "timer", role: "timer" }, mmss(left));
    const submit = async () => {
      if (finished) return; finished = true; clearInterval(tick);
      const answers = qs.map((q) => ({ question_id: q.question_id, answer: (document.querySelector(`input[name="q${q.question_id}"]:checked`) || {}).value || null }));
      try { showResult(await api("/quiz/submit", { method: "POST", body: { answers, time_taken_sec: total - left } })); }
      catch (e) { finished = false; box.prepend(note(e.message, "error")); }
    };
    const tick = setInterval(() => { left--; timer.textContent = mmss(left); timer.classList.toggle("low", left <= 15); if (left <= 0) submit(); }, 1000);
    box.replaceChildren(h("div", { class: "row" }, h("h1", {}, "Quiz"), h("div", {}, "Time left: ", timer)),
      ...qs.map((q, i) => h("div", { class: "panel" }, h("h3", {}, `${i + 1}. ${q.title}`), h("p", {}, q.description),
        q.options.map((o, j) => h("label", { class: "opt", for: `q${q.question_id}_${j}` }, h("input", { type: "radio", id: `q${q.question_id}_${j}`, name: `q${q.question_id}`, value: o }), o)))),
      h("button", { onclick: submit }, "Submit quiz"));
  };
  const showResult = (r) => box.replaceChildren(h("h1", {}, "Quiz result"),
    h("div", { class: "stats" }, h("div", { class: "stat" }, h("b", {}, `${r.correct}/${r.total}`), h("span", {}, "Correct")), h("div", { class: "stat" }, h("b", {}, pct(r.score_percent)), h("span", {}, "Score")), h("div", { class: "stat" }, h("b", {}, mmss(r.time_taken_sec || 0)), h("span", {}, "Time"))),
    ...r.results.map((x) => h("div", { class: "panel" }, h("b", {}, x.title), note(x.correct ? "Correct" : `Incorrect. Your answer: ${x.your_answer ?? "(none)"}`, x.correct ? "ok" : "error"),
      h("p", {}, h("b", {}, "Answer: "), x.feedback.correct_answer), x.feedback.explanation ? h("p", {}, x.feedback.explanation) : null)),
    h("button", { onclick: setup }, "New quiz"), " ", h("a", { class: "btn ghost", href: "progress.html" }, "View progress"));
  setup();
}

/* ---------- Progress ---------- */
async function pageProgress() {
  const box = $("#box");
  await guard(box, async () => {
    box.replaceChildren(note("Loading progress...", "info"));
    const [p, lb] = await Promise.all([api("/students/me/progress"), api("/leaderboard?limit=5").catch(() => [])]);
    const stat = (v, l) => h("div", { class: "stat" }, h("b", {}, v), h("span", {}, l));
    fill(box, h("h1", {}, `Progress for ${p.full_name}`),
      p.total_attempts === 0 ? note("No attempts yet. Open a question or take a quiz to start tracking progress.", "info") : null,
      h("div", { class: "stats" }, stat(p.total_attempts, "Attempts"), stat(`${p.questions_attempted}/${p.total_questions}`, "Questions attempted"), stat(p.questions_completed, "Completed"), stat(pct(p.average_score), "Average score")),
      h("div", { class: "panel" }, h("h2", {}, "By topic"), ...p.categories.map((c) => h("div", { style: "margin:.6rem 0" }, h("div", { class: "row" }, h("span", {}, c.category), h("span", { style: "text-align:right;color:var(--muted)" }, `${c.attempted}/${c.total_questions} tried, ${pct(c.average_best_score)}`)),
        h("div", { class: "bar", role: "img", "aria-label": `${c.category} ${pct(c.average_best_score)}` }, h("i", { style: `width:${c.average_best_score}%` }))))),
      h("div", { class: "panel" }, h("h2", {}, "Suggested practice"), h("ul", {}, p.recommendations.map((r) => h("li", {}, r)))),
      h("div", { class: "panel" }, h("h2", {}, "Recent attempts"), p.recent.length ? h("div", { style: "overflow:auto" }, h("table", {}, h("thead", {}, h("tr", {}, ["Question", "Topic", "Mode", "Score", "When"].map((x) => h("th", {}, x)))),
        h("tbody", {}, p.recent.map((a) => h("tr", {}, h("td", {}, h("a", { href: `question.html?id=${a.question_id}` }, a.title)), h("td", {}, a.category), h("td", {}, a.mode), h("td", {}, pct(a.score)), h("td", {}, a.attempted_at ? new Date(a.attempted_at + "Z").toLocaleString() : "")))))) : "Nothing yet."),
      lb.length ? h("div", { class: "panel" }, h("h2", {}, "Leaderboard"), h("table", {}, h("tbody", {}, lb.map((r) => h("tr", {}, h("td", {}, `#${r.rank}`), h("td", {}, r.full_name), h("td", {}, `${r.points} pts`), h("td", {}, `${r.questions_attempted} questions`)))))) : null);
  });
}

/* ---------- Chatbot ---------- */
async function pageChat() {
  const log = $("#log"), input = $("#msg"), chips = $("#chips");
  const add = (text, me) => { log.append(h("div", { class: "bubble " + (me ? "me" : "bot") }, text)); log.scrollTop = log.scrollHeight; };
  add("Hi! I'm a rule-based assistant (not generative AI). Ask about Python, REST APIs, FastAPI, MySQL or interviews.", false);
  const send = async (text) => {
    text = text.trim();
    if (!text) return log.append(note("Type a question first.", "error"));
    add(text, true); input.value = "";
    try { const r = await api("/chat", { method: "POST", body: { message: text } }); add(r.reply, false); }
    catch (e) { add("Error: " + e.message, false); }
  };
  $("#chatform").addEventListener("submit", (e) => { e.preventDefault(); send(input.value); });
  api("/chat/suggestions").then((r) => r.suggestions.forEach((s) => chips.append(h("button", { class: "ghost", type: "button", onclick: () => send(s) }, s)))).catch(() => {});
}

/* ---------- Admin ---------- */
async function pageAdmin() {
  const box = $("#box");
  if (!store.user || store.user.role !== "admin") return box.replaceChildren(note("Administrator access required.", "error"));
  let editing = null;
  const F = (id, label, el) => h("div", {}, h("label", { for: id }, label), el);
  const load = () => guard(box, async () => {
    const [stats, qs] = await Promise.all([api("/admin/stats"), api("/admin/questions")]);
    const f = {
      title: h("input", { id: "t", required: true }), category: h("input", { id: "c", required: true }),
      difficulty: h("select", { id: "d" }, ["Beginner", "Intermediate", "Advanced"].map((x) => h("option", {}, x))),
      qtype: h("select", { id: "y" }, h("option", { value: "coding" }, "Coding"), h("option", { value: "mcq" }, "Multiple choice")),
      description: h("textarea", { id: "ds" }), sample_input: h("input", { id: "si" }), expected_output: h("input", { id: "eo" }),
      options: h("textarea", { id: "op", placeholder: "One option per line (MCQ only)" }), correct_answer: h("input", { id: "ca" }),
      solution: h("textarea", { id: "so" }), explanation: h("input", { id: "ex" }),
    };
    const msg = h("div", {});
    if (editing) for (const k of Object.keys(f)) f[k].value = k === "options" ? (editing.options || []).join("\n") : (editing[k] ?? "");
    const form = h("form", { novalidate: true, onsubmit: async (ev) => {
      ev.preventDefault();
      const body = {}; for (const k of Object.keys(f)) body[k] = f[k].value.trim() || null;
      body.options = f.options.value.split("\n").map((x) => x.trim()).filter(Boolean);
      try { await api(editing ? `/questions/${editing.question_id}` : "/questions", { method: editing ? "PUT" : "POST", body }); editing = null; load(); }
      catch (e) { msg.replaceChildren(note(e.message, "error")); }
    } }, h("div", { class: "row" }, F("t", "Title", f.title), F("c", "Category", f.category), F("d", "Difficulty", f.difficulty), F("y", "Type", f.qtype)),
      F("ds", "Description", f.description), h("div", { class: "row" }, F("si", "Sample input", f.sample_input), F("eo", "Sample output", f.expected_output)),
      F("op", "MCQ options", f.options), F("ca", "MCQ correct answer (must match an option)", f.correct_answer), F("so", "Reference solution (coding)", f.solution), F("ex", "Explanation", f.explanation),
      h("p", {}, h("button", { type: "submit" }, editing ? "Save changes" : "Add question"), editing ? [" ", h("button", { type: "button", class: "ghost", onclick: () => { editing = null; load(); } }, "Cancel")] : null), msg);
    box.replaceChildren(h("h1", {}, "Administration"),
      h("div", { class: "stats" }, ...Object.entries(stats).map(([k, v]) => h("div", { class: "stat" }, h("b", {}, v), h("span", {}, k.replace("_", " "))))),
      h("div", { class: "panel" }, h("h2", {}, editing ? `Edit question #${editing.question_id}` : "Add question"), form),
      h("div", { class: "panel" }, h("h2", {}, "All questions"), ...qs.map((q) => h("div", { class: "q" }, h("span", {}, `#${q.question_id} ${q.title} `, h("span", { class: "badge" }, q.qtype)),
        h("span", {}, h("button", { class: "ghost", onclick: () => { editing = q; load(); scrollTo(0, 0); } }, "Edit"), " ",
          h("button", { class: "danger", onclick: async () => { if (confirm(`Delete "${q.title}" and its attempts?`)) { try { await api(`/questions/${q.question_id}`, { method: "DELETE" }); load(); } catch (e) { alert(e.message); } } } }, "Delete"))))));
  });
  load();
}

document.addEventListener("DOMContentLoaded", () => {
  const page = document.body.dataset.page;
  if (page !== "login" && !store.token) { location.href = "index.html"; return; }
  renderNav(page);
  ({ login: pageLogin, questions: pageQuestions, question: pageQuestion, quiz: pageQuiz, progress: pageProgress, chat: pageChat, admin: pageAdmin })[page]?.();
});
