from database.db import insert_interview
from datetime import datetime

def schedule_interview(candidate_id, job_id, interview_datetime):
    """
    Schedule an interview for a candidate using MongoDB wrapper.
    """
    insert_interview(candidate_id, job_id, interview_datetime)
    return f"Interview scheduled for candidate {candidate_id} on {interview_datetime}"