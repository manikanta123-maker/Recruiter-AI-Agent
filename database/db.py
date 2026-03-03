import sqlite3
import os

DB_PATH = "data/candidates.db"

def create_connection():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    return conn

# ---------------------------------
# CREATE TABLE
# ---------------------------------
def create_table():
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            skills TEXT,
            score REAL,
            status TEXT DEFAULT 'Applied',
            interview_date TEXT
        )
    """)

    conn.commit()
    conn.close()

# ---------------------------------
# INSERT CANDIDATE
# ---------------------------------
def insert_candidate(name, skills, score):
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO candidates (name, skills, score, status)
        VALUES (?, ?, ?, 'Applied')
    """, (name, skills, score))

    conn.commit()
    conn.close()

# ---------------------------------
# GET ALL CANDIDATES
# ---------------------------------
def get_all_candidates():
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, skills, score, status, interview_date
        FROM candidates
        ORDER BY score DESC
    """)

    data = cursor.fetchall()
    conn.close()
    return data

# ---------------------------------
# UPDATE STATUS + INTERVIEW DATE
# ---------------------------------
def update_status(candidate_id, status, interview_date):
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE candidates
        SET status = ?, interview_date = ?
        WHERE id = ?
    """, (status, str(interview_date), candidate_id))

    conn.commit()
    conn.close()