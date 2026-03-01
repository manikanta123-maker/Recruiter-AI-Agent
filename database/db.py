import sqlite3
import os

DB_PATH = "data/candidates.db"

def create_connection():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    return conn

def create_table():
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            skills TEXT,
            score REAL
        )
    """)

    conn.commit()
    conn.close()

def insert_candidate(skills, score):
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO candidates (skills, score)
        VALUES (?, ?)
    """, (", ".join(skills), score))

    conn.commit()
    conn.close()

def get_all_candidates():
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM candidates")
    data = cursor.fetchall()

    conn.close()
    return data