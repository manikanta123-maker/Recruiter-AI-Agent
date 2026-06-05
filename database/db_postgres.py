import os
import uuid
import hashlib
import secrets
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, String, Float, Integer, ForeignKey, Text, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()

# Read PostgreSQL connection URI from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/recruiter_ai")

# Handle potential Heroku/Render postgres:// to postgresql:// change
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Initialize SQLAlchemy engine
try:
    if "postgresql" in DATABASE_URL:
        engine = create_engine(
            DATABASE_URL, 
            connect_args={"connect_timeout": 10}, 
            pool_pre_ping=True, 
            pool_recycle=300
        )
    elif "sqlite" in DATABASE_URL:
        engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    else:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=300)
except Exception:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# -----------------------------
# PASSWORD HASHING HELPERS
# -----------------------------
def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return f"{salt}:{key.hex()}"

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify password against PBKDF2-HMAC-SHA256 hash."""
    try:
        salt, key_hex = hashed_password.split(':')
        new_key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
        return new_key.hex() == key_hex
    except Exception:
        return False

# -----------------------------
# DATABASE MODELS
# -----------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False) # Admin, Recruiter, HiringManager
    name = Column(String, nullable=True)
    is_verified = Column(Boolean, default=False)
    verification_code = Column(String, nullable=True)

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    required_skills = Column(String, nullable=True)
    recruiter_id = Column(String, ForeignKey("users.id"), nullable=False)
    hiring_manager_id = Column(String, ForeignKey("users.id"), nullable=False)
    structured_jd = Column(Text, nullable=True) # Structured JSON JD

class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=True)
    skills = Column(String, nullable=True) # Stored as comma-separated string
    score = Column(Float, default=0.0)
    status = Column(String, default="Applied")
    interview_date = Column(String, nullable=True)
    experience = Column(Integer, nullable=True)
    notice_period = Column(String, nullable=True)
    expected_salary = Column(Integer, nullable=True)
    rating = Column(Integer, nullable=True)
    feedback = Column(Text, nullable=True)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=True)
    
    # Track B extended candidate fields
    email = Column(String, nullable=True)
    ats_explanation = Column(Text, nullable=True)
    strengths = Column(Text, nullable=True) # Comma-separated or JSON list
    weaknesses = Column(Text, nullable=True) # Comma-separated or JSON list
    candidate_summary = Column(Text, nullable=True)
    assessment_score = Column(Float, default=0.0)
    ai_recommendation = Column(String, nullable=True)

class Interview(Base):
    __tablename__ = "interviews"

    id = Column(String, primary_key=True, index=True)
    candidate_id = Column(String, ForeignKey("candidates.id"), nullable=False)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False)
    interview_datetime = Column(String, nullable=False)
    status = Column(String, default="Scheduled")

class AssessmentQuestion(Base):
    __tablename__ = "assessment_questions"
    
    id = Column(String, primary_key=True, index=True)
    language = Column(String, nullable=False) # java, python, react
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    template_code = Column(Text, nullable=True)
    test_cases = Column(Text, nullable=True) # JSON test cases: [{"input": "...", "expected": "..."}]

class Assessment(Base):
    __tablename__ = "assessments"
    
    id = Column(String, primary_key=True, index=True) # Token
    candidate_id = Column(String, ForeignKey("candidates.id"), nullable=False)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False)
    status = Column(String, default="Pending") # Pending, Completed
    created_at = Column(String, nullable=True)

class AssessmentSubmission(Base):
    __tablename__ = "assessment_submissions"
    
    id = Column(String, primary_key=True, index=True)
    assessment_id = Column(String, ForeignKey("assessments.id"), nullable=False)
    question_id = Column(String, ForeignKey("assessment_questions.id"), nullable=False)
    submitted_code = Column(Text, nullable=False)
    score = Column(Float, default=0.0)
    evaluated_at = Column(String, nullable=True)

class AssessmentResult(Base):
    __tablename__ = "assessment_results"
    
    id = Column(String, primary_key=True, index=True)
    assessment_id = Column(String, ForeignKey("assessments.id"), nullable=False)
    score = Column(Float, default=0.0)
    passed = Column(Boolean, default=False)
    report = Column(Text, nullable=True)
    created_at = Column(String, nullable=True)

class CandidateJourney(Base):
    __tablename__ = "candidate_journey"
    
    id = Column(String, primary_key=True, index=True)
    candidate_id = Column(String, ForeignKey("candidates.id"), nullable=False)
    stage = Column(String, nullable=False) # Applied, Screened, Assessed, Interviewed, Recommended, Selected, Hired, Rejected
    timestamp = Column(String, nullable=False)
    notes = Column(Text, nullable=True)

class AgentLog(Base):
    __tablename__ = "agent_logs"
    
    id = Column(String, primary_key=True, index=True)
    agent_name = Column(String, nullable=False)
    input_data = Column(Text, nullable=True)
    output_data = Column(Text, nullable=True)
    status = Column(String, nullable=False)
    timestamp = Column(String, nullable=False)

class InterviewQuestion(Base):
    __tablename__ = "interview_questions"
    
    id = Column(String, primary_key=True, index=True)
    candidate_id = Column(String, ForeignKey("candidates.id"), nullable=False)
    questions = Column(Text, nullable=False) # JSON array of questions
    created_at = Column(String, nullable=True)

class Recommendation(Base):
    __tablename__ = "recommendations"
    
    id = Column(String, primary_key=True, index=True)
    candidate_id = Column(String, ForeignKey("candidates.id"), nullable=False)
    recommendation = Column(String, nullable=False) # Hire, Strong Hire, Hold, Reject
    confidence = Column(Float, default=0.0)
    reasoning = Column(Text, nullable=True)
    created_at = Column(String, nullable=True)

# -----------------------------
# DATABASE HELPER FUNCTIONS
# -----------------------------
def create_table():
    global engine
    try:
        Base.metadata.create_all(bind=engine)
        print("Database tables initialized successfully.")
        
        from sqlalchemy import text
        with engine.connect() as conn:
            try:
                if "postgresql" in str(engine.url):
                    conn.execute(text("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS email VARCHAR"))
                    conn.commit()
                else:
                    conn.execute(text("ALTER TABLE candidates ADD COLUMN email VARCHAR"))
                    conn.commit()
                print("Database schema verified: candidate email column ensured.")
            except Exception:
                pass
    except Exception as e:
        print(f"Warning: Could not connect to PostgreSQL. Falling back to local SQLite database. Error: {e}")
        # Fallback to local SQLite database
        sqlite_url = "sqlite:///./recruiter_ai.db"
        engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
        SessionLocal.configure(bind=engine)
        Base.metadata.create_all(bind=engine)
        print("SQLite database tables initialized successfully.")
        
        from sqlalchemy import text
        with engine.connect() as conn:
            try:
                conn.execute(text("ALTER TABLE candidates ADD COLUMN email VARCHAR"))
                conn.commit()
            except Exception:
                pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Users Helpers
def get_user_by_email(email: str):
    db = SessionLocal()
    try:
        return db.query(User).filter(User.email == email.lower().strip()).first()
    finally:
        db.close()

def insert_user(email: str, password_raw: str, role: str, name: str, is_verified: bool = False, verification_code: str = None) -> str:
    db = SessionLocal()
    try:
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            email=email.lower().strip(),
            password_hash=hash_password(password_raw),
            role=role,
            name=name,
            is_verified=is_verified,
            verification_code=verification_code
        )
        db.add(user)
        db.commit()
        return user_id
    except Exception as e:
        db.rollback()
        print(f"Error inserting user: {e}")
        raise e
    finally:
        db.close()

# Jobs Helpers
def insert_job(title: str, description: str, required_skills: str, recruiter_id: str, hiring_manager_id: str) -> str:
    db = SessionLocal()
    try:
        job_id = str(uuid.uuid4())
        job = Job(
            id=job_id,
            title=title,
            description=description,
            required_skills=required_skills,
            recruiter_id=recruiter_id,
            hiring_manager_id=hiring_manager_id
        )
        db.add(job)
        db.commit()
        return job_id
    except Exception as e:
        db.rollback()
        print(f"Error inserting job: {e}")
        raise e
    finally:
        db.close()

def get_all_jobs():
    db = SessionLocal()
    try:
        return db.query(Job).all()
    finally:
        db.close()

# Candidates Helpers
def insert_candidate(name: str, skills: str, score: float, job_id: str = None, email: str = None) -> str:
    db = SessionLocal()
    try:
        cand_id = str(uuid.uuid4())
        candidate = Candidate(
            id=cand_id,
            name=name,
            skills=skills,
            score=score,
            status="Applied",
            job_id=job_id,
            email=email
        )
        db.add(candidate)
        db.commit()
        return cand_id
    except Exception as e:
        db.rollback()
        print(f"Error inserting candidate into PostgreSQL: {e}")
        raise e
    finally:
        db.close()

def get_all_candidates():
    db = SessionLocal()
    try:
        candidates = db.query(Candidate).order_by(Candidate.score.desc()).all()
        # Return tuples for backend controller compatibility
        # (id, name, skills, score, status, interview_date, job_id)
        return [
            (c.id, c.name, c.skills, c.score, c.status, c.interview_date, c.job_id)
            for c in candidates
        ]
    except Exception as e:
        print(f"Error querying candidate records: {e}")
        return []
    finally:
        db.close()

def update_final_score(candidate_id: str, final_score: float):
    db = SessionLocal()
    try:
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if candidate:
            candidate.score = final_score
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error updating score: {e}")
    finally:
        db.close()

def update_screening(candidate_id: str, experience: int, notice_period: str, expected_salary: int):
    db = SessionLocal()
    try:
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if candidate:
            candidate.experience = experience
            candidate.notice_period = notice_period
            candidate.expected_salary = expected_salary
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error updating screening parameters: {e}")
    finally:
        db.close()

def update_status(candidate_id: str, status: str, interview_date: str = None):
    db = SessionLocal()
    try:
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if candidate:
            candidate.status = status
            if interview_date:
                candidate.interview_date = interview_date
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error updating status: {e}")
    finally:
        db.close()

def save_feedback(candidate_id: str, rating: int, feedback: str):
    db = SessionLocal()
    try:
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if candidate:
            candidate.rating = rating
            candidate.feedback = feedback
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error saving feedback: {e}")
    finally:
        db.close()

def insert_interview(candidate_id: str, job_id: str, interview_datetime: str):
    db = SessionLocal()
    try:
        int_id = str(uuid.uuid4())
        interview = Interview(
            id=int_id,
            candidate_id=candidate_id,
            job_id=job_id,
            interview_datetime=interview_datetime,
            status="Scheduled"
        )
        db.add(interview)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error scheduling interview: {e}")
    finally:
        db.close()

def rename_candidate(candidate_id: str, new_name: str):
    db = SessionLocal()
    try:
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if candidate:
            candidate.name = new_name
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error renaming candidate: {e}")
    finally:
        db.close()

