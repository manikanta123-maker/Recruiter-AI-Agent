import os
from pymongo import MongoClient
from bson.objectid import ObjectId

# Using generic fallback to local testing if MONGO_URI missing, but it is in .env 
uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = MongoClient(uri)
db = client.get_database("recruiter_ai")
candidates_col = db["candidates"]
interviews_col = db["interviews"]

def create_table():
    pass

def insert_candidate(name, skills, score):
    doc = {
        "name": name,
        "skills": skills,
        "score": score,
        "status": "Applied",
        "interview_date": None,
        "experience": None,
        "notice_period": None,
        "expected_salary": None,
        "rating": None,
        "feedback": None
    }
    candidates_col.insert_one(doc)

def get_all_candidates():
    # Return as standard 6-tuple array to keep main.py clean
    docs = candidates_col.find().sort("score", -1)
    data = []
    for doc in docs:
        data.append((
            str(doc["_id"]),
            doc.get("name"),
            doc.get("skills"),
            doc.get("score"),
            doc.get("status"),
            doc.get("interview_date")
        ))
    return data

def update_final_score(candidate_id, final_score):
    candidates_col.update_one(
        {"_id": ObjectId(candidate_id)},
        {"$set": {"score": final_score}}
    )

def update_screening(candidate_id, experience, notice_period, expected_salary):
    candidates_col.update_one(
        {"_id": ObjectId(candidate_id)},
        {"$set": {
            "experience": experience, 
            "notice_period": notice_period, 
            "expected_salary": expected_salary
        }}
    )

def update_status(candidate_id, status, interview_date=None):
    update_data = {"status": status}
    if interview_date:
        update_data["interview_date"] = str(interview_date)
    candidates_col.update_one(
        {"_id": ObjectId(candidate_id)},
        {"$set": update_data}
    )

def save_feedback(candidate_id, rating, feedback):
    candidates_col.update_one(
        {"_id": ObjectId(candidate_id)},
        {"$set": {"rating": rating, "feedback": feedback}}
    )

def insert_interview(candidate_id, job_id, interview_datetime):
    doc = {
        "candidate_id": str(candidate_id),
        "job_id": str(job_id),
        "interview_datetime": str(interview_datetime),
        "status": "Scheduled"
    }
    interviews_col.insert_one(doc)

def rename_candidate(candidate_id, new_name):
    candidates_col.update_one(
        {"_id": ObjectId(candidate_id)},
        {"$set": {"name": new_name}}
    )