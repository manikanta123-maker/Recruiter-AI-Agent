from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import uvicorn
from dotenv import load_dotenv

load_dotenv()


import smtplib
from email.mime.text import MIMEText

import json
from database.db_postgres import (
    create_table, insert_candidate, get_all_candidates, 
    update_screening, update_final_score, update_status, 
    save_feedback, insert_interview, rename_candidate,
    SessionLocal, Candidate, User, Job,
    get_user_by_email, verify_password, insert_user, insert_job, get_all_jobs,
    AssessmentQuestion, Assessment, AssessmentSubmission, AssessmentResult,
    CandidateJourney, AgentLog, InterviewQuestion, Recommendation
)

from database.auth import create_access_token, get_current_user, RoleChecker

from modules.resume_parser import (
    extract_text_from_pdf, extract_text_from_docx, 
    extract_skills_from_jd
)
from modules.scorer import screening_score
from modules.scheduler import schedule_interview
from modules.templates import generate_email
from utils.helpers import send_email

# Import V3 Agentic pipeline functions
from modules.pipeline_v3 import (
    run_jd_intelligence, run_resume_screening, run_assessment_recommendation,
    run_assessment_delivery, run_assessment_evaluation, run_interview_preparation,
    run_interview_decision, log_journey_stage, recruitment_langgraph_workflow
)

# Ensure PostgreSQL tables exist
create_table()

def seed_assessment_questions():
    db = SessionLocal()
    try:
        if db.query(AssessmentQuestion).count() == 0:
            questions = [
                AssessmentQuestion(
                    id="py_missing_num",
                    language="python",
                    title="Find the Missing Number in an Array",
                    description="Write a function `find_missing(arr)` that takes an array of integers from 1 to N (where N is the length of the array + 1) with one missing number, and returns the missing number.\n\nSample Input: `[1, 2, 4, 5]`\nSample Output: `3`",
                    template_code="def find_missing(arr):\n    # Write your code here\n    pass",
                    test_cases=json.dumps([{"input": "[1, 2, 4, 5]", "expected": "3"}])
                ),
                AssessmentQuestion(
                    id="java_reverse",
                    language="java",
                    title="Reverse a String",
                    description="Write a method `reverseString(String str)` that reverses a given string.\n\nSample Input: `\"hello\"`\nSample Output: `\"olleh\"`",
                    template_code="public class Solution {\n    public static String reverseString(String str) {\n        // Write your code here\n        return \"\";\n    }\n}",
                    test_cases=json.dumps([{"input": "\"hello\"", "expected": "\"olleh\""}])
                ),
                AssessmentQuestion(
                    id="react_duplicates",
                    language="react",
                    title="Find Duplicate Elements",
                    description="Write a JavaScript function `findDuplicates(arr)` that returns a sorted array of duplicate numbers found in the input array.\n\nSample Input: `[1, 2, 3, 2, 4, 3]`\nSample Output: `[2, 3]`",
                    template_code="function findDuplicates(arr) {\n    // Write your code here\n    return [];\n}",
                    test_cases=json.dumps([{"input": "[1, 2, 3, 2, 4, 3]", "expected": "[2, 3]"}])
                )
            ]
            db.add_all(questions)
            db.commit()
            print("Database: Pre-populated 3 standard assessment coding questions.")
    except Exception as e:
        print(f"Error seeding questions: {e}")
    finally:
        db.close()

seed_assessment_questions()

app = FastAPI(title="Recruiter AI Agent API (Track B)")

# Build allowed origins dynamically — supports local dev + any deployed Vercel frontend
_frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")
_allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    _frontend_url,
]
# Also allow all *.vercel.app preview deployments
_allowed_origins = list(set(_allowed_origins))  # deduplicate

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",  # covers all Vercel preview URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# DATA SCHEMAS
# -----------------------------
class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    password: str
    role: str
    name: str

class JDRequest(BaseModel):
    job_description: str

class JobCreateRequest(BaseModel):
    title: str
    description: str
    required_skills: str
    hiring_manager_name: str
    hiring_manager_email: str

class EvaluateRequest(BaseModel):
    candidate_id: str
    experience: int
    notice_period: str
    expected_salary: int

class RenameRequest(BaseModel):
    candidate_id: str
    new_name: str

class ScheduleRequest(BaseModel):
    candidate_id: str
    job_id: str
    interview_date: str
    email: str

class UpdateStatusRequest(BaseModel):
    candidate_id: str
    status: str

class FeedbackRequest(BaseModel):
    candidate_id: str
    rating: int
    feedback: str

class AssessmentRequest(BaseModel):
    candidate_id: str
    skills: str

class MockCompleteRequest(BaseModel):
    candidate_id: str

class VerifyOTPRequest(BaseModel):
    email: str
    code: str

# -----------------------------
# AUTH ENDPOINTS
# -----------------------------
@app.post("/api/login")
def login(req: LoginRequest):
    email_clean = req.email.lower().strip()
    user = get_user_by_email(email_clean)
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not user.is_verified:
        raise HTTPException(status_code=400, detail="Please verify your email address before logging in")
        
    token = create_access_token({"sub": email_clean, "role": user.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "email": email_clean
    }

def send_verification_otp(to_email: str, code: str):
    print(f"[OTP VERIFICATION CODE - EMAIL DISABLED] To: {to_email} | Code: {code}")

@app.post("/api/register")
def register(req: RegisterRequest):
    import re
    import random
    email_clean = req.email.lower().strip()
    if not re.match(r"^[a-zA-Z0-9._%+-]+@gmail\.com$", email_clean):
        raise HTTPException(status_code=400, detail="Only @gmail.com email addresses are allowed")
    
    existing = get_user_by_email(email_clean)
    if existing:
        raise HTTPException(status_code=400, detail="Email is already registered")
    
    if req.role not in ["Recruiter", "HiringManager", "Admin"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be Recruiter, HiringManager, or Admin")
        
    try:
        # Create verified account immediately (emailing bypassed)
        user_id = insert_user(email_clean, req.password, req.role, req.name, is_verified=True, verification_code=None)
        return {"message": "Account created successfully. You can now log in.", "email": email_clean, "requires_verification": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/verify-otp")
def verify_otp(req: VerifyOTPRequest):
    email_clean = req.email.lower().strip()
    user = get_user_by_email(email_clean)
    if not user:
        raise HTTPException(status_code=404, detail="User record not found")
    
    if user.is_verified:
        return {"message": "Email is already verified"}
        
    if user.verification_code == req.code:
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.id == user.id).first()
            if db_user:
                db_user.is_verified = True
                db_user.verification_code = None
                db.commit()
            return {"message": "Verification successful! You can now log in."}
        finally:
            db.close()
    else:
        raise HTTPException(status_code=400, detail="Invalid verification code")

# -----------------------------
# JOBS ENDPOINTS
# -----------------------------
@app.post("/api/jobs")
def create_new_job(req: JobCreateRequest, current_user: dict = Depends(RoleChecker(["Recruiter"]))):
    import re
    if not re.match(r"^[a-zA-Z0-9._%+-]+@gmail\.com$", req.hiring_manager_email):
        raise HTTPException(status_code=400, detail="Hiring Manager email must be a @gmail.com address")
    
    # Verify hiring manager exists
    manager = get_user_by_email(req.hiring_manager_email)
    if not manager:
        raise HTTPException(
            status_code=400, 
            detail=f"Hiring Manager with email {req.hiring_manager_email} does not exist. Please have them register first."
        )
    
    if manager.role != "HiringManager":
        raise HTTPException(
            status_code=400,
            detail=f"The account with email {req.hiring_manager_email} is not registered as a Hiring Manager."
        )
        
    manager_id = manager.id

        
    recruiter = get_user_by_email(current_user["email"])
    recruiter_id = recruiter.id if recruiter else "default_recruiter"
    
    try:
        job_id = insert_job(req.title, req.description, req.required_skills, recruiter_id, manager_id)
        # Execute JD Intelligence Agent to analyze raw JD
        run_jd_intelligence(job_id, req.title, req.description)
        return {"message": "Job created successfully", "job_id": job_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/jobs")
def get_jobs(current_user: dict = Depends(get_current_user)):
    user = get_user_by_email(current_user["email"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db = SessionLocal()
    try:
        if user.role == "Admin":
            jobs = db.query(Job).all()
        elif user.role == "Recruiter":
            # Each Recruiter sees ONLY jobs they personally created
            jobs = db.query(Job).filter(Job.recruiter_id == user.id).all()
        elif user.role == "HiringManager":
            jobs = db.query(Job).filter(Job.hiring_manager_id == user.id).all()
        else:
            jobs = []
            
        res_list = []
        for j in jobs:
            mgr = db.query(User).filter(User.id == j.hiring_manager_id).first()
            rec = db.query(User).filter(User.id == j.recruiter_id).first()
            res_list.append({
                "id": j.id,
                "title": j.title,
                "description": j.description,
                "required_skills": j.required_skills,
                "recruiter_id": j.recruiter_id,
                "recruiter_email": rec.email if rec else "",
                "hiring_manager_id": j.hiring_manager_id,
                "hiring_manager_email": mgr.email if mgr else ""
            })
        return res_list
    finally:
        db.close()

# -----------------------------
# RECRUITMENT ENDPOINTS
# -----------------------------
@app.post("/api/extract-jd")
def extract_jd_skills(req: JDRequest, current_user: dict = Depends(RoleChecker(["Recruiter"]))):
    skills = extract_skills_from_jd(req.job_description)
    return {"required_skills": skills}

@app.post("/api/upload-resume")
def upload_resumes(
    candidate_name: str = Form(...),
    required_skills: str = Form(...),
    file: UploadFile = File(...),
    job_id: str = Form(...),
    current_user: dict = Depends(RoleChecker(["Recruiter"]))
):
    filename_lower = file.filename.lower()
    if filename_lower.endswith(".pdf"):
        text = extract_text_from_pdf(file.file)
    elif filename_lower.endswith(".docx"):
        text = extract_text_from_docx(file.file)
    elif filename_lower.endswith(".txt"):
        text = file.file.read().decode("utf-8")
    else:
        raise HTTPException(status_code=400, detail="Invalid file type")

    # 1. Fetch Job info and structured_jd
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job opening not found")
        job_title = job.title
        job_description = job.description
        structured_jd_str = job.structured_jd
        structured_jd = json.loads(structured_jd_str) if structured_jd_str else None
    finally:
        db.close()
        
    # 2. Extract or generate candidate email — accept ANY valid email domain
    import re
    any_emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    if any_emails:
        # Use the first real email found directly without forcing @gmail.com
        cand_email = any_emails[0].lower().strip()
    else:
        # Fallback: synthesize a placeholder email from the candidate's name
        cand_email = f"{re.sub(r'[^a-zA-Z0-9]', '.', candidate_name).lower()}@candidate.placeholder"
            
    # 3. Block duplicate uploads — same candidate name for same job
    db_check = SessionLocal()
    try:
        existing_candidate = db_check.query(Candidate).filter(
            Candidate.job_id == job_id,
            Candidate.name == candidate_name
        ).first()
        if existing_candidate:
            raise HTTPException(
                status_code=400,
                detail=f"A resume for '{candidate_name}' has already been uploaded for this job. Duplicate uploads are not allowed."
            )
    finally:
        db_check.close()

    # 4. Create candidate entry in Database
    cand_id = insert_candidate(candidate_name, "", 0.0, job_id=job_id, email=cand_email)
    
    # 4. Initialize LangGraph workflow state
    initial_state = {
        "candidate_id": cand_id,
        "job_id": job_id,
        "candidate_name": candidate_name,
        "candidate_email": cand_email,
        "resume_text": text,
        "job_title": job_title,
        "job_description": job_description,
        "required_skills": required_skills,
        "structured_jd": structured_jd
    }
    
    # 5. Run the LangGraph workflow
    try:
        result_state = recruitment_langgraph_workflow.invoke(initial_state)
    except Exception as e:
        print(f"LangGraph execution error: {e}")
        raise HTTPException(status_code=500, detail=f"Pipeline execution crashed: {e}")
        
    # 6. Fetch updated candidate fields from DB to return
    db = SessionLocal()
    try:
        cand = db.query(Candidate).filter(Candidate.id == cand_id).first()
        score = cand.score if cand else 0.0
        skills_str = cand.skills if cand else ""
        compliance_notes = cand.ats_explanation if cand else ""
    finally:
        db.close()
        
    return {
        "candidate_id": cand_id,
        "candidate_name": candidate_name,
        "extracted_skills": [s.strip() for s in skills_str.split(",") if s.strip()] if skills_str else [],
        "ats_score": score,
        "compliance_notes": compliance_notes
    }

@app.get("/api/candidates")
def get_candidates(current_user: dict = Depends(get_current_user)):
    user = get_user_by_email(current_user["email"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    db = SessionLocal()
    try:
        if user.role == "Admin":
            candidates = db.query(Candidate).order_by(Candidate.score.desc()).all()
        elif user.role == "Recruiter":
            # Each Recruiter sees ONLY candidates from their own jobs
            my_jobs = db.query(Job).filter(Job.recruiter_id == user.id).all()
            my_job_ids = {j.id for j in my_jobs}
            if my_job_ids:
                candidates = db.query(Candidate).filter(Candidate.job_id.in_(my_job_ids)).order_by(Candidate.score.desc()).all()
            else:
                candidates = []
        elif user.role == "HiringManager":
            assigned_jobs = db.query(Job).filter(Job.hiring_manager_id == user.id).all()
            assigned_job_ids = {j.id for j in assigned_jobs}
            candidates = db.query(Candidate).filter(Candidate.job_id.in_(assigned_job_ids)).order_by(Candidate.score.desc()).all()
        else:
            candidates = []
            
        res_list = []
        for c in candidates:
            iq = db.query(InterviewQuestion).filter(InterviewQuestion.candidate_id == c.id).first()
            questions = json.loads(iq.questions) if iq else []
            
            # Query assessment token if exists
            assess = db.query(Assessment).filter(Assessment.candidate_id == c.id).first()
            assessment_token = assess.id if assess else ""
            
            res_list.append({
                "id": c.id,
                "name": c.name,
                "email": c.email or "",
                "skills": c.skills or "",
                "score": c.score,
                "status": c.status,
                "interview_date": c.interview_date or "",
                "job_id": c.job_id,
                "experience": c.experience or 0,
                "notice_period": c.notice_period or "",
                "expected_salary": c.expected_salary or 0,
                "rating": c.rating or 0,
                "feedback": c.feedback or "",
                "ats_explanation": c.ats_explanation or "",
                "strengths": c.strengths or "",
                "weaknesses": c.weaknesses or "",
                "candidate_summary": c.candidate_summary or "",
                "assessment_score": c.assessment_score or 0.0,
                "ai_recommendation": c.ai_recommendation or "",
                "interview_questions": questions,
                "assessment_token": assessment_token
            })
        return res_list
    finally:
        db.close()

@app.post("/api/evaluate")
def evaluate_candidate(req: EvaluateRequest, current_user: dict = Depends(RoleChecker(["Recruiter"]))):
    screen = screening_score(req.experience, req.notice_period)
    
    # Fetch candidate from DB to get their current score
    db = SessionLocal()
    try:
        cand = db.query(Candidate).filter(Candidate.id == req.candidate_id).first()
        if not cand:
            raise HTTPException(status_code=404, detail="Candidate not found")
        ats = cand.score
        final_score = ats + screen
        
        update_screening(req.candidate_id, req.experience, req.notice_period, req.expected_salary)
        update_final_score(req.candidate_id, final_score)
        
        return {
            "ats_score": ats,
            "screening_score": screen,
            "final_score": final_score
        }
    finally:
        db.close()

@app.post("/api/candidate/rename")
def rename_cand(req: RenameRequest, current_user: dict = Depends(RoleChecker(["Recruiter"]))):
    rename_candidate(req.candidate_id, req.new_name)
    return {"message": "Candidate renamed successfully"}

@app.post("/api/interview/schedule")
def schedule_int(req: ScheduleRequest, current_user: dict = Depends(RoleChecker(["Recruiter"]))):
    import re
    # Accept any valid email — candidates may use Gmail, Outlook, Yahoo, company email, etc.
    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", req.email):
        raise HTTPException(status_code=400, detail="Please enter a valid candidate email address")
        
    # Schedule event (updates database + generates Google Meet link)
    res = schedule_interview(req.candidate_id, req.job_id, req.interview_date)
    update_status(req.candidate_id, "Scheduled", req.interview_date)
    
    # Update candidate feedback with Meet URL
    db = SessionLocal()
    try:
        cand = db.query(Candidate).filter(Candidate.id == req.candidate_id).first()
        cand_name = cand.name if cand else "Candidate"
        if cand:
            cand.feedback = (cand.feedback or "") + f"\n[MEET LINK] {res['meet_url']}"
            db.commit()
    finally:
        db.close()
        
    email_text = generate_email(
        "interview_invite",
        name=cand_name,
        date=req.interview_date,
        position="Software Engineer"
    )
    # Include Meet URL in invite body
    email_text += f"\n\nGoogle Meet Link: {res['meet_url']}"
    
    email_sent = send_email(req.email, "Interview Scheduled (Meet Link Included)", email_text)
    warning_msg = "" if email_sent else "Failed to send email"

    return {
        "message": "Interview Scheduled", 
        "email_text": email_text, 
        "email_sent": email_sent, 
        "meet_url": res["meet_url"],
        "warning": warning_msg
    }

@app.post("/api/interview/status")
def update_stat(req: UpdateStatusRequest, current_user: dict = Depends(RoleChecker(["Recruiter", "HiringManager"]))):
    update_status(req.candidate_id, req.status)
    
    # Auto-trigger assessment delivery when recruiter manually promotes a candidate to Assessed
    if req.status == "Assessed":
        db = SessionLocal()
        try:
            cand = db.query(Candidate).filter(Candidate.id == req.candidate_id).first()
            if cand and cand.job_id and cand.email:
                # Only send if no assessment token already exists for this candidate
                existing = db.query(Assessment).filter(Assessment.candidate_id == req.candidate_id).first()
                if not existing:
                    from modules.pipeline_v3 import run_assessment_delivery
                    skills_str = cand.skills or ""
                    run_assessment_delivery(cand.id, cand.job_id, cand.name, cand.email, skills_str)
                    print(f"[AUTO-ASSESS] Assessment invitation triggered for candidate {req.candidate_id}")
        except Exception as e:
            print(f"[AUTO-ASSESS ERROR] {e}")
        finally:
            db.close()
    
    return {"message": f"Status updated to {req.status}"}

@app.post("/api/interview/feedback")
def submit_feedback(req: FeedbackRequest, current_user: dict = Depends(get_current_user)):
    user = get_user_by_email(current_user["email"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
        
    db = SessionLocal()
    try:
        cand = db.query(Candidate).filter(Candidate.id == req.candidate_id).first()
        if not cand:
            raise HTTPException(status_code=404, detail="Candidate not found")
        
        is_authorized = False
        if user.role == "Admin":
            is_authorized = True
        elif cand.job_id:
            job = db.query(Job).filter(Job.id == cand.job_id).first()
            if job and (job.hiring_manager_id == user.id or job.recruiter_id == user.id):
                is_authorized = True
        else:
            if user.role in ["HiringManager", "Recruiter"]:
                is_authorized = True
                
        if not is_authorized:
            raise HTTPException(status_code=403, detail="You are not authorized to submit feedback for this candidate.")
            
        save_feedback(req.candidate_id, req.rating, req.feedback)
        
        # Execute Interview Decision Agent (Agent 7) statefully
        ats_score = cand.score
        assessment_score = cand.assessment_score or 0.0
        
        decision = run_interview_decision(req.candidate_id, ats_score, assessment_score, req.rating, req.feedback)
        
        # Automatically update candidate journey stage based on Agent 7 decision
        rec = decision.get("recommendation", "Hold")
        reasoning = decision.get("reasoning", "")
        confidence = decision.get("confidence", 0.0)
        
        if rec in ["Strong Hire", "Hire"]:
            new_stage = "Recommended"
        elif rec == "Reject":
            new_stage = "Rejected"
        else:
            new_stage = "Hold"
            
        log_journey_stage(req.candidate_id, new_stage, notes=f"Auto-transitioned by Agent 7 (Recommendation: {rec}, Confidence: {confidence}%, Reasoning: {reasoning})")
        
        return {"message": "Feedback Saved & AI Decision Generated"}
    finally:
        db.close()

# -----------------------------
# ASSESSMENT PORTAL ENDPOINTS
# -----------------------------
class SubmissionRequest(BaseModel):
    token: str
    submitted_code: str
    code_language: str

@app.get("/api/assessment/{token}")
def get_assessment_details(token: str):
    db = SessionLocal()
    try:
        invite = db.query(Assessment).filter(Assessment.id == token).first()
        if not invite:
            raise HTTPException(status_code=404, detail="Assessment link is invalid or expired.")
            
        candidate = db.query(Candidate).filter(Candidate.id == invite.candidate_id).first()
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found.")
            
        job = db.query(Job).filter(Job.id == invite.job_id).first()
        job_title = job.title if job else "Software Engineer"
        
        skills_str = candidate.skills or ""
        skills = [s.strip().lower() for s in skills_str.split(",") if s.strip()]
        language = "python"
        
        if any(t in skills for t in ["java", "spring"]):
            language = "java"
        elif any(t in skills for t in ["react", "javascript", "next.js", "node.js"]):
            language = "react"
            
        question = db.query(AssessmentQuestion).filter(AssessmentQuestion.language == language).first()
        if not question:
            question = db.query(AssessmentQuestion).first()
            
        return {
            "token": token,
            "candidate_name": candidate.name,
            "job_title": job_title,
            "language": question.language if question else "python",
            "question_title": question.title if question else "Code Submission Challenge",
            "question_description": question.description if question else "Write a clean implementation of the requested coding task.",
            "template_code": question.template_code if question else ""
        }
    finally:
        db.close()

@app.post("/api/assessment/submit")
def submit_assessment(req: SubmissionRequest):
    db = SessionLocal()
    try:
        invite = db.query(Assessment).filter(Assessment.id == req.token).first()
        if not invite:
            raise HTTPException(status_code=404, detail="Assessment token not found")
            
        candidate = db.query(Candidate).filter(Candidate.id == invite.candidate_id).first()
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")
            
        job = db.query(Job).filter(Job.id == invite.job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
            
        candidate_email = candidate.email
        candidate_id = candidate.id
        candidate_name = candidate.name
        candidate_score = candidate.score
        job_id = job.id
        job_skills = job.required_skills
    finally:
        db.close()
        
    # Run the stateful LangGraph workflow for evaluation & interview prep
    initial_state = {
        "candidate_id": candidate_id,
        "job_id": job_id,
        "candidate_name": candidate_name,
        "candidate_email": candidate_email,
        "required_skills": job_skills,
        "screening_result": {"score": candidate_score},
        "recommendation": "Assessed",
        "assessment_details": {"token": req.token},
        "submitted_code": req.submitted_code,
        "code_language": req.code_language
    }
    
    try:
        # Runs A5 (Assessment Evaluation) -> A6 (Interview Prep) -> END
        result_state = recruitment_langgraph_workflow.invoke(initial_state)
    except Exception as e:
        print(f"Evaluation pipeline crash: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    eval_res = result_state.get("evaluation_result", {})
    return {
        "success": True,
        "score": eval_res.get("score", 0.0),
        "passed": eval_res.get("passed", False),
        "report": eval_res.get("report", "")
    }

# -----------------------------
# SYSTEM ANALYTICS & LOGGING ENDPOINTS
# -----------------------------
@app.get("/api/agent-logs")
def get_agent_logs(current_user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        logs = db.query(AgentLog).order_by(AgentLog.timestamp.desc()).limit(100).all()
        return [
            {
                "id": l.id,
                "agent_name": l.agent_name,
                "input_data": l.input_data,
                "output_data": l.output_data,
                "status": l.status,
                "timestamp": l.timestamp
            }
            for l in logs
        ]
    finally:
        db.close()

@app.get("/api/journey/{candidate_id}")
def get_candidate_journey(candidate_id: str, current_user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        journey = db.query(CandidateJourney).filter(CandidateJourney.candidate_id == candidate_id).order_by(CandidateJourney.timestamp.asc()).all()
        return [
            {
                "id": j.id,
                "candidate_id": j.candidate_id,
                "stage": j.stage,
                "timestamp": j.timestamp,
                "notes": j.notes
            }
            for j in journey
        ]
    finally:
        db.close()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
