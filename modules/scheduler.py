from database.db import create_connection
from datetime import datetime

def schedule_interview(candidate_id, job_id, interview_datetime):
    """
    Schedule an interview for a candidate.
    """
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO interviews (candidate_id, job_id, interview_datetime) 
        VALUES (?, ?, ?)
    """, (candidate_id, job_id, interview_datetime))
    conn.commit()
    conn.close()
    return f"Interview scheduled for candidate {candidate_id} on {interview_datetime}"