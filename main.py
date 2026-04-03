from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import uvicorn

import smtplib
from email.mime.text import MIMEText

from database.db import (
    create_table, insert_candidate, get_all_candidates, 
    update_screening, update_final_score, update_status, 
    save_feedback, insert_interview, rename_candidate
)

from modules.resume_parser import (
    extract_text_from_pdf, extract_text_from_docx, 
    extract_skills, extract_skills_from_jd
)
from modules.scorer import ats_score, screening_score
from modules.scheduler import schedule_interview
from modules.templates import generate_email

# Ensure DB table exists
create_table()

app = FastAPI(title="Recruiter AI Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class JDRequest(BaseModel):
    job_description: str

@app.post("/api/extract-jd")
def extract_jd_skills(req: JDRequest):
    skills = extract_skills_from_jd(req.job_description)
    return {"required_skills": skills}

@app.post("/api/upload-resume")
def upload_resumes(
    candidate_name: str = Form(...),
    required_skills: str = Form(...),
    file: UploadFile = File(...)
):
    req_skills_list = [s.strip() for s in required_skills.split(",")]
    
    if file.filename.endswith(".pdf"):
        text = extract_text_from_pdf(file.file)
    elif file.filename.endswith(".docx"):
        text = extract_text_from_docx(file.file)
    else:
        raise HTTPException(status_code=400, detail="Invalid file type")

    candidate_skills = extract_skills(text)
    ats = ats_score(candidate_skills, req_skills_list, text)
    
    insert_candidate(candidate_name, ", ".join(candidate_skills), ats)
    
    return {
        "candidate_name": candidate_name,
        "extracted_skills": candidate_skills,
        "ats_score": ats
    }

@app.get("/api/candidates")
def get_candidates():
    records = get_all_candidates()
    # map records to dictionary
    keys = ["id", "name", "skills", "score", "status", "interview_date"]
    return [dict(zip(keys, r)) for r in records]

class EvaluateRequest(BaseModel):
    candidate_id: str
    experience: int
    notice_period: str
    expected_salary: int

@app.post("/api/evaluate")
def evaluate_candidate(req: EvaluateRequest):
    screen = screening_score(req.experience, req.notice_period)
    
    # fetch current ats
    cands = get_all_candidates()
    cand = next((c for c in cands if c[0] == req.candidate_id), None)
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    ats = cand[3]
    final_score = ats + screen
    
    update_screening(req.candidate_id, req.experience, req.notice_period, req.expected_salary)
    update_final_score(req.candidate_id, final_score)
    
    return {
        "ats_score": ats,
        "screening_score": screen,
        "final_score": final_score
    }

class RenameRequest(BaseModel):
    candidate_id: str
    new_name: str

@app.post("/api/candidate/rename")
def rename_cand(req: RenameRequest):
    rename_candidate(req.candidate_id, req.new_name)
    return {"message": "Candidate renamed successfully"}

class ScheduleRequest(BaseModel):
    candidate_id: str
    job_id: int
    interview_date: str
    email: str

@app.post("/api/interview/schedule")
def schedule_int(req: ScheduleRequest):
    schedule_interview(req.candidate_id, req.job_id, req.interview_date)
    update_status(req.candidate_id, "Scheduled", req.interview_date)
    
    cands = get_all_candidates()
    cand = next((c for c in cands if c[0] == req.candidate_id), None)
    cand_name = cand[1] if cand else "Candidate"
    
    email_text = generate_email(
        "interview_invite",
        name=cand_name,
        date=req.interview_date,
        position="the position"
    )
    
    sender_email = os.getenv("EMAIL_SENDER")
    app_password = os.getenv("EMAIL_APP_PASSWORD")
    
    email_sent = False
    warning_msg = ""
    
    if sender_email and app_password and req.email:
        try:
            msg = MIMEText(email_text)
            msg['Subject'] = "Interview Scheduled"
            msg['From'] = sender_email
            msg['To'] = req.email
            
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(sender_email, app_password)
                server.send_message(msg)
            email_sent = True
        except Exception as e:
            warning_msg = f"Failed to send email: {str(e)}"
    else:
        warning_msg = "Real email not sent: EMAIL_SENDER or EMAIL_APP_PASSWORD not in .env"

    return {
        "message": "Interview Scheduled", 
        "email_text": email_text, 
        "email_sent": email_sent, 
        "warning": warning_msg
    }

class UpdateStatusRequest(BaseModel):
    candidate_id: str
    status: str

@app.post("/api/interview/status")
def update_stat(req: UpdateStatusRequest):
    update_status(req.candidate_id, req.status)
    return {"message": f"Status updated to {req.status}"}

class FeedbackRequest(BaseModel):
    candidate_id: str
    rating: int
    feedback: str

@app.post("/api/interview/feedback")
def submit_feedback(req: FeedbackRequest):
    save_feedback(req.candidate_id, req.rating, req.feedback)
    return {"message": "Feedback Saved"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
