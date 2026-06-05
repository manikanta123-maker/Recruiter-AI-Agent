import random
import uuid
from database.db_postgres import SessionLocal, Candidate

def trigger_assessment(candidate_id: str, candidate_name: str, skills_str: str) -> dict:
    """Simulate triggering a HackerEarth technical test for a candidate based on their extracted skills."""
    skills = [s.strip().lower() for s in skills_str.split(",") if s.strip()]
    
    # Select appropriate test based on technical skills
    test_name = "General Aptitude & Problem Solving Test"
    test_id = "general_101"
    
    if any(tech in skills for tech in ["python", "django", "fastapi"]):
        test_name = "Python Advanced Programming Challenge"
        test_id = "py_adv_202"
    elif any(tech in skills for tech in ["javascript", "react", "next.js", "node.js"]):
        test_name = "React & Node Full-Stack Evaluation"
        test_id = "js_fs_303"
    elif any(tech in skills for tech in ["java", "spring"]):
        test_name = "Enterprise Java Backend Assessment"
        test_id = "java_ent_404"
        
    mock_test_token = str(uuid.uuid4())[:8]
    test_url = f"https://hackerearth.com/recruiter-ai-agent/test-{test_id}/{mock_test_token}"
    
    print(f"API Outbox (HackerEarth): Triggered {test_name} for {candidate_name}.")
    
    # We will log the assessment details in candidate database fields
    db = SessionLocal()
    try:
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if candidate:
            # We can save metadata inside candidate feedback or update fields
            # For simplicity, we can store it in the candidate's feedback text for now
            # or dynamically add columns if needed. Let's make sure it's stored in feedback/notes.
            assessment_notes = f"[ASSESSMENT TRIGGERED] Test: {test_name} | URL: {test_url} | Status: Pending"
            candidate.feedback = (candidate.feedback or "") + "\n" + assessment_notes
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error logging assessment in DB: {e}")
    finally:
        db.close()
        
    return {
        "success": True,
        "test_name": test_name,
        "test_url": test_url,
        "status": "Pending"
    }

def simulate_assessment_completion(candidate_id: str) -> dict:
    """Simulate candidate completing the coding assessment and returning a score."""
    # Generate a random score between 60 and 100
    test_score = random.randint(60, 100)
    
    db = SessionLocal()
    try:
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if candidate:
            # Add assessment points to overall score (scaling the score out of 10 to add to final_score)
            assessment_points = round(test_score / 10.0, 1)
            candidate.score = (candidate.score or 0) + assessment_points
            
            assessment_notes = f"\n[ASSESSMENT COMPLETED] Score: {test_score}/100 | Points added: +{assessment_points}"
            candidate.feedback = (candidate.feedback or "") + assessment_notes
            db.commit()
            
            print(f"Webhook Callback received: Candidate {candidate.name} finished assessment with score {test_score}/100.")
            return {"success": True, "score": test_score, "points_added": assessment_points}
    except Exception as e:
        db.rollback()
        print(f"Error completing assessment in DB: {e}")
    finally:
        db.close()
        
    return {"success": False, "detail": "Candidate not found"}
