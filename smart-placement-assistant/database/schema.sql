-- Smart Placement Preparation Assistant (Advanced) - MySQL 8.x schema
-- Run:  mysql -u root -p < database/schema.sql
-- Sample data (questions + demo accounts with hashed passwords) is inserted by:  python backend/seed.py

CREATE DATABASE IF NOT EXISTS placement_assistant CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE placement_assistant;

CREATE TABLE IF NOT EXISTS students (
  student_id    INT AUTO_INCREMENT PRIMARY KEY,
  full_name     VARCHAR(100) NOT NULL,
  email         VARCHAR(150) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,              -- salted PBKDF2-SHA256, never plain text
  role          VARCHAR(10)  NOT NULL DEFAULT 'student',   -- student | admin
  branch        VARCHAR(60),
  study_year    INT,
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS questions (
  question_id     INT AUTO_INCREMENT PRIMARY KEY,
  title           VARCHAR(200) NOT NULL,
  category        VARCHAR(60)  NOT NULL,
  difficulty      VARCHAR(20)  NOT NULL DEFAULT 'Beginner',
  qtype           VARCHAR(10)  NOT NULL DEFAULT 'coding',  -- coding | mcq
  description     TEXT NOT NULL,
  sample_input    TEXT,
  expected_output TEXT,
  options         JSON,          -- MCQ choices
  correct_answer  TEXT,          -- MCQ answer (hidden from students until they answer)
  solution        TEXT,          -- coding reference solution
  explanation     TEXT,
  created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_questions_category (category)
);

CREATE TABLE IF NOT EXISTS attempts (
  attempt_id       INT AUTO_INCREMENT PRIMARY KEY,
  student_id       INT NOT NULL,
  question_id      INT NOT NULL,
  submitted_answer TEXT,
  score            DECIMAL(5,2) DEFAULT 0,
  completed        BOOLEAN DEFAULT FALSE,
  mode             VARCHAR(10) DEFAULT 'practice',   -- practice | quiz
  time_taken_sec   INT,
  attempted_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (student_id)  REFERENCES students(student_id),
  FOREIGN KEY (question_id) REFERENCES questions(question_id),
  INDEX idx_attempts_student (student_id),
  INDEX idx_attempts_question (question_id)
);

-- Handy verification queries
-- SELECT category, COUNT(*) FROM questions GROUP BY category;
-- SELECT s.full_name, COUNT(*) AS attempts, ROUND(AVG(a.score),1) AS avg_score
--   FROM attempts a JOIN students s ON s.student_id = a.student_id GROUP BY s.student_id;

-- Recommended: a least-privilege application user instead of root
-- CREATE USER 'placement_user'@'localhost' IDENTIFIED BY 'choose-a-strong-password';
-- GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, INDEX ON placement_assistant.* TO 'placement_user'@'localhost';
