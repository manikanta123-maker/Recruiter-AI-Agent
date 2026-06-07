import os
import json
import uuid
import datetime
import requests
from typing import TypedDict, List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()


from database.db_postgres import (
    SessionLocal, User, Job, Candidate, AssessmentQuestion,
    Assessment, AssessmentSubmission, AssessmentResult, CandidateJourney,
    AgentLog, InterviewQuestion, Recommendation
)
from modules.resume_parser import extract_text_from_pdf, extract_text_from_docx, extract_skills
from modules.scheduler import schedule_interview
from modules.templates import generate_email
from utils.helpers import send_email

# LangChain / Gemini imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate

# Initialize the Gemini model
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", 
    temperature=0, 
    google_api_key=os.getenv("GEMINI_API_KEY"),
    max_retries=1
)

# -----------------------------
# AGENT LOGGER HELPER
# -----------------------------
def log_agent_run(agent_name: str, input_data: Any, output_data: Any, status: str = "Success"):
    db = SessionLocal()
    try:
        log_id = str(uuid.uuid4())
        
        # Serialize input/output safely
        input_str = json.dumps(input_data, default=str) if not isinstance(input_data, str) else input_data
        output_str = json.dumps(output_data, default=str) if not isinstance(output_data, str) else output_data
        
        log_entry = AgentLog(
            id=log_id,
            agent_name=agent_name,
            input_data=input_str,
            output_data=output_str,
            status=status,
            timestamp=datetime.datetime.utcnow().isoformat()
        )
        db.add(log_entry)
        db.commit()
        print(f"[AGENT LOG] {agent_name} logged. Status: {status}")
    except Exception as e:
        db.rollback()
        print(f"Error logging agent run: {e}")
    finally:
        db.close()

# -----------------------------
# JOURNEY TRANSITION HELPER
# -----------------------------
def log_journey_stage(candidate_id: str, stage: str, notes: str = None):
    db = SessionLocal()
    try:
        journey_id = str(uuid.uuid4())
        journey = CandidateJourney(
            id=journey_id,
            candidate_id=candidate_id,
            stage=stage,
            timestamp=datetime.datetime.utcnow().isoformat(),
            notes=notes
        )
        db.add(journey)
        
        # Sync the candidate status in PostgreSQL
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if candidate:
            candidate.status = stage
            
        db.commit()
        print(f"[JOURNEY] Candidate {candidate_id} transitioned to: {stage}")
    except Exception as e:
        db.rollback()
        print(f"Error logging candidate journey: {e}")
    finally:
        db.close()

# -----------------------------
# EMAIL / NOTIFICATION SERVICE
# -----------------------------
def send_notification(to_email: str, subject: str, body: str):
    return send_email(to_email, subject, body)

# --------------------------------------------------
# AGENT 1: JD INTELLIGENCE AGENT (Job Creation)
# --------------------------------------------------
def run_jd_intelligence(job_id: str, title: str, description: str) -> dict:
    """Analyzes JD to extract skills, experience, location, salary and structured formats."""
    prompt = PromptTemplate(
        input_variables=["title", "description"],
        template="""
        You are a JD Intelligence AI Agent. Analyze the following Job Opening details:
        Job Title: {title}
        Job Description: {description}
        
        Extract the core requirements in a structured JSON format:
        * skills: Array of technical/soft skills required.
        * experience: Minimum years of experience requested (as number/string).
        * location: Expected job location (Remote, Onsite, hybrid, etc).
        * salary: Expected salary range if mentioned.
        * missing_requirements: Array of key details commonly expected in JDs that are missing here (e.g. benefits, tools, stack specifics).
        
        Return ONLY a valid JSON object. Do not include markdown codeblocks or text formatting.
        """
    )
    chain = prompt | llm
    input_data = {"title": title, "description": description}
    try:
        res = chain.invoke(input_data)
        content = res.content.strip()
        
        # Strip potential markdown formatting
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()
            
        structured_jd = json.loads(content)
        
        # Save structured JD in PostgreSQL database
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.structured_jd = json.dumps(structured_jd)
                db.commit()
        finally:
            db.close()
            
        log_agent_run("JD Intelligence Agent", input_data, structured_jd, "Success")
        return structured_jd
    except Exception as e:
        print(f"JD Agent Error: {e}")
        fallback = {
            "skills": [s.strip() for s in title.split(" ") if len(s.strip()) > 3],
            "experience": "Not specified",
            "location": "Not specified",
            "salary": "Not specified",
            "missing_requirements": ["Detailed role responsibilities", "Company benefits"]
        }
        log_agent_run("JD Intelligence Agent", input_data, fallback, f"Fallback due to: {e}")
        return fallback

# --------------------------------------------------
# AGENT 2: RESUME SCREENING AGENT (Resume Uploaded)
# --------------------------------------------------
def run_resume_screening(candidate_name: str, resume_text: str, required_skills: str) -> dict:
    """Parses resume, extracts skills, compares against JD requirements, and scores."""
    prompt = PromptTemplate(
        input_variables=["name", "resume", "required_skills"],
        template="""
        You are a Resume Screening AI Agent.
        Analyze this resume and evaluate the candidate against the required skills:
        Candidate Name: {name}
        Required Skills: {required_skills}
        Resume Content: {resume}
        
        Provide the evaluation results in a structured JSON format containing:
        * score: Numerical ATS match score (0 to 100) based on skill matching, experience context, and education.
        * summary: A brief 2-3 sentence summary of the candidate's background.
        * strengths: Array of 3-4 key technical strengths or certifications.
        * weaknesses: Array of 2-3 missing skills or gaps relative to the job.
        * match_explanation: A detailed 2-sentence explanation of why they received the score.
        
        Special instructions: Highly value Tier-1 colleges (IIT/NIT/BITS) and technical degrees (B.Tech/M.Tech/MCA) for tech roles.
        Return ONLY valid JSON. No markdown codeblocks or wrapper text.
        """
    )
    chain = prompt | llm
    input_data = {"name": candidate_name, "resume": resume_text[:4000], "required_skills": required_skills}
    
    # Retry up to 3 times with 5s delay — handles Gemini 503 rate limits on rapid uploads
    last_error = None
    for attempt in range(1, 4):
        try:
            res = chain.invoke(input_data)
            content = res.content.strip()
            if content.startswith("```json"):
                content = content[7:-3].strip()
            elif content.startswith("```"):
                content = content[3:-3].strip()
                
            result = json.loads(content)
            log_agent_run("Resume Screening Agent", input_data, result, "Success")
            return result
        except Exception as e:
            last_error = e
            print(f"Resume Screening Agent attempt {attempt}/3 failed: {e}")
            if attempt < 3:
                import time
                time.sleep(5)  # Wait 5s before retrying
    
    # All 3 attempts failed — use rule-based fallback
    e = last_error
    print(f"Resume Screening Agent Error (Falling back after 3 attempts): {e}")
    # Rule based fallback matching
    cand_skills = [s.strip().lower() for s in required_skills.split(",") if s.strip()]
    matches = [s for s in cand_skills if s in resume_text.lower()]
    score = (len(matches) / len(cand_skills) * 100) if cand_skills else 0.0
    fallback = {
        "score": round(score, 1),
        "summary": f"Candidate {candidate_name} evaluated using rule-based fallback.",
        "strengths": matches if matches else ["Basic Technical Knowledge"],
        "weaknesses": [s for s in cand_skills if s not in matches],
        "match_explanation": f"Rule-based match score generated due to Gemini API limit/error: {e}"
    }
    log_agent_run("Resume Screening Agent", input_data, fallback, f"Fallback due to: {e}")
    return fallback

# --------------------------------------------------
# AGENT 3: ASSESSMENT RECOMMENDATION AGENT (ATS -> Test Route)
# --------------------------------------------------
def run_assessment_recommendation(candidate_id: str, ats_score: float) -> str:
    """Decides if candidate proceeds to coding test, goes on Hold, or gets Rejected."""
    input_data = {"candidate_id": candidate_id, "ats_score": ats_score}
    
    if ats_score < 60.0:
        decision = "Rejected"
        notes = f"ATS match score ({ats_score}%) is below the threshold of 60%."
    elif ats_score <= 75.0:
        decision = "Hold"
        notes = f"ATS match score ({ats_score}%) is within review range (60-75%). Placed on Hold."
    else:
        decision = "Assessed"
        notes = f"ATS match score ({ats_score}%) exceeds the threshold of 75%. Triggering coding assessment invitation."
        
    log_journey_stage(candidate_id, decision, notes)
    log_agent_run("Assessment Recommendation Agent", input_data, {"decision": decision, "notes": notes}, "Success")
    return decision

# --------------------------------------------------
# AGENT 4: ASSESSMENT AGENT (Deliver Assessment Link)
# --------------------------------------------------
def run_assessment_delivery(candidate_id: str, job_id: str, candidate_name: str, candidate_email: str, skills_str: str) -> dict:
    """Generates an invitation token, chooses the skill test, and emails the link."""
    db = SessionLocal()
    try:
        # Determine language test based on skills
        skills = [s.strip().lower() for s in skills_str.split(",") if s.strip()]
        language = "python" # default
        
        if any(t in skills for t in ["java", "spring"]):
            language = "java"
        elif any(t in skills for t in ["react", "javascript", "next.js", "node.js"]):
            language = "react"
            
        token = str(uuid.uuid4())
        
        # Save assessment invitation in DB
        invite = Assessment(
            id=token,
            candidate_id=candidate_id,
            job_id=job_id,
            status="Pending",
            created_at=datetime.datetime.utcnow().isoformat()
        )
        db.add(invite)
        db.commit()
        
        # Generate Assessment URL link using FRONTEND_URL from environment if available
        frontend_base = os.getenv("FRONTEND_URL", "http://localhost:3000")
        portal_url = f"{frontend_base.rstrip('/')}/assessment/{token}"
        
        # Fetch job details to parse the actual role/title dynamically
        job_title = "Software Developer"
        if job_id:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job and job.title:
                job_title = job.title

        # Draft email using dynamic job title
        subject = f"Coding Assessment Invitation - {job_title} Role"
        body = f"""Hello {candidate_name},

Thank you for applying for the {job_title} role!

Based on your resume, our AI Recruitment system has shortlisted you for the next step. Please complete this technical coding assessment:

> Start Assessment: {portal_url}

Please write your code solution directly inside the portal and submit it when ready.

Best regards,
Recruitment Team"""
        
        # Send invitation email
        email_sent = send_notification(candidate_email, subject, body)
        
        res = {
            "token": token,
            "language": language,
            "portal_url": portal_url,
            "email_sent": email_sent
        }
        log_agent_run("Assessment Agent", {"candidate_id": candidate_id, "email": candidate_email}, res, "Success")
        return res
    finally:
        db.close()

def wrap_python_code(submitted_code: str, test_cases: list, question_id: str) -> str:
    test_cases_json = json.dumps(test_cases)
    harness = f"""{submitted_code}

# Test cases runner
import json
test_cases = {test_cases_json}
results = []
for tc in test_cases:
    try:
        try:
            inp = json.loads(tc["input"])
        except Exception:
            try:
                inp = eval(tc["input"])
            except Exception:
                inp = tc["input"]
                
        try:
            exp = json.loads(tc["expected"])
        except Exception:
            try:
                exp = eval(tc["expected"])
            except Exception:
                exp = tc["expected"]

        if "{question_id}" == "py_missing_num" or "find_missing" in globals():
            res = find_missing(inp)
        else:
            res = None
            
        if res == exp:
            results.append(True)
        else:
            results.append(False)
    except Exception as e:
        results.append(False)

print("TEST_RESULTS:" + json.dumps(results))
"""
    return harness

def wrap_javascript_code(submitted_code: str, test_cases: list, question_id: str) -> str:
    test_cases_json = json.dumps(test_cases)
    harness = f"""{submitted_code}

// Test cases runner
const test_cases = {test_cases_json};
const results = [];
for (let tc of test_cases) {{
    let inp, exp;
    try {{
        inp = JSON.parse(tc.input);
        exp = JSON.parse(tc.expected);
    }} catch(e) {{
        try {{
            inp = eval(tc.input);
            exp = eval(tc.expected);
        }} catch(e2) {{
            inp = tc.input;
            exp = tc.expected;
        }}
    }}
    
    try {{
        let res;
        if ("{question_id}" === "react_duplicates" || typeof findDuplicates === "function") {{
            res = findDuplicates(inp);
        }} else {{
            res = null;
        }}
        
        if (Array.isArray(res) && Array.isArray(exp)) {{
            res.sort();
            exp.sort();
            if (JSON.stringify(res) === JSON.stringify(exp)) {{
                results.push(true);
            }} else {{
                results.push(false);
            }}
        }} else if (JSON.stringify(res) === JSON.stringify(exp)) {{
            results.push(true);
        }} else {{
            results.push(false);
        }}
    }} catch(e) {{
        results.push(false);
    }}
}}
console.log("TEST_RESULTS:" + JSON.stringify(results));
"""
    return harness

def wrap_java_code(submitted_code: str, test_cases: list, question_id: str) -> str:
    code_clean = submitted_code.replace("public class Solution", "class Solution")
    
    inputs_list = []
    expecteds_list = []
    for tc in test_cases:
        inputs_list.append(json.dumps(tc["input"]))
        expecteds_list.append(json.dumps(tc["expected"]))
        
    inputs_str = ", ".join(inputs_list)
    expecteds_str = ", ".join(expecteds_list)
    
    harness = f"""{code_clean}

import java.util.*;

public class Main {{
    public static void main(String[] args) {{
        List<Boolean> results = new ArrayList<>();
        
        String[] inputs = new String[]{{ {inputs_str} }};
        String[] expecteds = new String[]{{ {expecteds_str} }};
        
        for (int i = 0; i < inputs.length; i++) {{
            try {{
                String inpClean = inputs[i];
                if (inpClean.startsWith("\\\"") && inpClean.endsWith("\\\"")) {{
                    inpClean = inpClean.substring(1, inpClean.length() - 1);
                }}
                
                String expClean = expecteds[i];
                if (expClean.startsWith("\\\"") && expClean.endsWith("\\\"")) {{
                    expClean = expClean.substring(1, expClean.length() - 1);
                }}
                
                String res = Solution.reverseString(inpClean);
                if (res != null && res.equals(expClean)) {{
                    results.add(true);
                }} else {{
                    results.add(false);
                }}
            }} catch (Exception e) {{
                results.add(false);
            }}
        }}
        
        System.out.print("TEST_RESULTS:[");
        for (int i = 0; i < results.size(); i++) {{
            System.out.print(results.get(i) + (i == results.size() - 1 ? "" : ","));
        }}
        System.out.println("]");
    }}
}}
"""
    return harness

def run_assessment_evaluation(token: str, submitted_code: str, language: str) -> dict:
    """Grades submitted candidate code using Judge0 execution against test cases."""
    from fastapi import HTTPException
    import re
    
    input_data = {"token": token, "language": language, "code_length": len(submitted_code)}
    
    # 1. Fetch the assessment details and test cases
    db = SessionLocal()
    candidate_id = None
    job_id = None
    candidate_name = "Candidate"
    candidate_email = None
    test_cases = []
    question_id = "py_missing_num"
    
    try:
        invite = db.query(Assessment).filter(Assessment.id == token).first()
        if not invite:
            return {"success": False, "detail": "Assessment token not found"}
            
        candidate_id = invite.candidate_id
        job_id = invite.job_id
        invite.status = "Completed"
        
        cand = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if cand:
            candidate_name = cand.name or "Candidate"
            candidate_email = cand.email
            
        # Fetch matching question & test cases
        question = db.query(AssessmentQuestion).filter(AssessmentQuestion.language == language.lower().strip()).first()
        if not question:
            question = db.query(AssessmentQuestion).first()
            
        if question:
            question_id = question.id
            if question.test_cases:
                try:
                    test_cases = json.loads(question.test_cases)
                except Exception as e:
                    print(f"Error parsing test cases JSON from DB: {e}")
                    
        db.commit()
    finally:
        db.close()
        
    # 2. Wrap the code with the language-specific test harness
    if language.lower().strip() == "python":
        wrapped_code = wrap_python_code(submitted_code, test_cases, question_id)
        lang_id = 71
    elif language.lower().strip() == "java":
        wrapped_code = wrap_java_code(submitted_code, test_cases, question_id)
        lang_id = 62
    else: # react / javascript
        wrapped_code = wrap_javascript_code(submitted_code, test_cases, question_id)
        lang_id = 63
        
    # 3. Execute code via Judge0 API
    score = 0.0
    report = ""
    
    judge0_key = os.getenv("JUDGE0_API_KEY")
    if not judge0_key:
        raise HTTPException(
            status_code=503,
            detail="Grading service is temporarily unavailable (Judge0 key not configured). Please contact support."
        )
        
    try:
        # Judge0 execution via RapidAPI
        url = "https://judge0-ce.p.rapidapi.com/submissions?base64_encoded=false&wait=true"
        headers = {
            "x-rapidapi-key": judge0_key,
            "x-rapidapi-host": "judge0-ce.p.rapidapi.com",
            "Content-Type": "application/json"
        }
        payload = {
            "source_code": wrapped_code,
            "language_id": lang_id,
            "stdin": ""
        }
        res = requests.post(url, headers=headers, json=payload, timeout=12)
        
        if res.status_code == 200 or res.status_code == 201:
            exec_res = res.json()
            stdout = exec_res.get("stdout") or ""
            stderr = exec_res.get("stderr") or ""
            compile_output = exec_res.get("compile_output") or ""
            status_desc = exec_res.get("status", {}).get("description", "Unknown")
            
            # Parse test results from stdout
            match = re.search(r"TEST_RESULTS:(\[.*?\])", stdout)
            if match:
                try:
                    results_list = json.loads(match.group(1))
                    total = len(results_list)
                    passed = sum(1 for r in results_list if r is True)
                    score = (passed / total) * 100.0 if total > 0 else 0.0
                    report = f"Test Cases: {passed}/{total} passed."
                    if passed == total:
                        report += " All test cases passed successfully."
                    else:
                        report += f" Failed {total - passed} test cases."
                except Exception as e:
                    print(f"Error parsing test results array: {e}")
                    score = 0.0
                    report = f"Grading output format error. Stdout:\n{stdout}"
            else:
                score = 0.0
                if stderr or compile_output:
                    report = f"Compilation/Execution failed. Compiler output:\n{compile_output}\nStderr:\n{stderr}"
                else:
                    report = f"Execution completed with no test case outputs. Status: {status_desc}."
        else:
            raise HTTPException(
                status_code=503,
                detail=f"Grading service returned error status {res.status_code}: {res.text}"
            )
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=503,
            detail=f"Grading service communication error: {str(e)}"
        )
        
    passed = score >= 70.0
    
    # 4. Save optional AI review feedback (Gemini)
    feedback_report = report
    try:
        prompt = PromptTemplate(
            input_variables=["code", "language", "score", "passed"],
            template="""
            You are a Senior Software Engineer conducting a candidate code review.
            Analyze this candidate's submitted code and review their performance:
            Language: {language}
            Execution Score: {score}/100 (Passed: {passed})
            
            Candidate Code:
            {code}
            
            Please provide a professional, constructive code review in a brief paragraph.
            Highlight:
            * Strengths of their implementation.
            * Weaknesses or potential edge case bugs (if any).
            * Suggestions for readability or performance optimizations.
            
            Format your output as standard text (1 paragraph, max 3-4 sentences). Do not mention Gemini or AI.
            """
        )
        chain = prompt | llm
        gemini_res = chain.invoke({"code": submitted_code, "language": language, "score": score, "passed": passed})
        feedback_report = f"{report}\n\n[AI Code Review Feedback]:\n{gemini_res.content.strip()}"
    except Exception as e:
        print(f"Optional Gemini feedback generation failed/bypassed: {e}")
        feedback_report = f"{report}\n\n[AI Code Review Feedback]:\n(AI code review feedback is temporarily unavailable due to demand limits)."
        
    # 5. Store Assessment Result in DB
    db = SessionLocal()
    try:
        res_id = str(uuid.uuid4())
        
        # Find matching question ID in database to satisfy foreign key constraint
        question = db.query(AssessmentQuestion).filter(AssessmentQuestion.language == language.lower().strip()).first()
        if not question:
            question = db.query(AssessmentQuestion).first()
        question_id = question.id if question else "py_missing_num"
        
        # Save Submission
        sub = AssessmentSubmission(
            id=str(uuid.uuid4()),
            assessment_id=token,
            question_id=question_id,
            submitted_code=submitted_code,
            score=score,
            evaluated_at=datetime.datetime.utcnow().isoformat()
        )
        db.add(sub)
        
        # Save Result
        result = AssessmentResult(
            id=res_id,
            assessment_id=token,
            score=score,
            passed=passed,
            report=feedback_report,
            created_at=datetime.datetime.utcnow().isoformat()
        )
        db.add(result)
        
        # Update Candidate overall score & status
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if candidate:
            candidate.assessment_score = score
            # Add scaled points (+10 max) to candidate's overall ATS match score
            candidate.score = round(min(candidate.score + (score / 10.0), 100.0), 1)
            
        db.commit()
    finally:
        db.close()
        
    # Transition candidate journey stage
    # Passed → Scheduled (interview will be autonomously booked below)
    # Failed → Hold (recruiter can review and manually send test or reject)
    next_stage = "Scheduled" if passed else "Hold"
    notes = f"Assessment score: {score}/100. Passed: {passed}. Grader report: {feedback_report}"
    log_journey_stage(candidate_id, next_stage, notes)
    
    # Autonomous scheduling of the interview if passed
    if passed and candidate_email:
        try:
            # Scheduled autonomously for 3 days from now
            scheduled_date = (datetime.datetime.utcnow() + datetime.timedelta(days=3)).strftime("%Y-%m-%d")
            sched_res = schedule_interview(candidate_id, job_id, scheduled_date)
            meet_url = sched_res.get("meet_url")
            
            # Sync candidate status and interview date in DB
            db_conn = SessionLocal()
            try:
                c = db_conn.query(Candidate).filter(Candidate.id == candidate_id).first()
                if c:
                    c.status = "Scheduled"
                    c.interview_date = scheduled_date
                    c.feedback = (c.feedback or "") + f"\n[AUTO-MEET LINK] {meet_url}"
                    db_conn.commit()
            finally:
                db_conn.close()
                
            # Draft and send the interview invitation email
            subject = "Technical Interview Invitation - Recruiter AI Platform"
            body = f"""Hello {candidate_name},

Congratulations! You successfully passed the technical coding assessment with a score of {score}/100.

We would like to invite you for a 1-hour technical interview scheduled autonomously by our AI.

- Date: {scheduled_date}
- Time: 10:00 AM (IST)
- Google Meet Link: {meet_url}

Please join the meeting link at the scheduled time.

Best regards,
Recruiter AI Agent Team"""
            send_notification(candidate_email, subject, body)
            print(f"[AUTO-SCHEDULER] Interview scheduled automatically for candidate {candidate_id}")
            
            # Update candidate journey with Scheduled stage
            log_journey_stage(candidate_id, "Scheduled", f"Interview scheduled autonomously. Meet Link: {meet_url}")
            
        except Exception as es:
            print(f"Error autonomously scheduling interview: {es}")
            
    res_details = {"score": score, "passed": passed, "report": feedback_report}
    log_agent_run("Assessment Evaluation Agent", input_data, res_details, "Success")
    return res_details

# --------------------------------------------------
# AGENT 6: INTERVIEW PREPARATION AGENT (Generates questions)
# --------------------------------------------------
def run_interview_preparation(candidate_id: str, candidate_name: str, skills: str, assessment_report: str) -> list:
    """Generates 5 personalized interview questions for the Hiring Manager."""
    prompt = PromptTemplate(
        input_variables=["name", "skills", "report"],
        template="""
        You are an Interview Preparation AI Agent.
        Review the candidate's details and assessment performance to generate personalized interview questions:
        Candidate Name: {name}
        Skills: {skills}
        Technical Assessment Report: {report}
        
        Generate exactly 5 specialized interview questions.
        * Focus on testing their weaknesses or missing skills highlighted in the report.
        * Include a mix of technical coding logic and real-world system design.
        
        Return ONLY a JSON string array of 5 questions. No markdown format or prefix text.
        """
    )
    chain = prompt | llm
    input_data = {"name": candidate_name, "skills": skills, "report": assessment_report}
    try:
        res = chain.invoke(input_data)
        content = res.content.strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()
            
        questions = json.loads(content)
        
        # Save questions in DB
        db = SessionLocal()
        try:
            iq = InterviewQuestion(
                id=str(uuid.uuid4()),
                candidate_id=candidate_id,
                questions=json.dumps(questions),
                created_at=datetime.datetime.utcnow().isoformat()
            )
            db.add(iq)
            db.commit()
        finally:
            db.close()
            
        log_agent_run("Interview Preparation Agent", input_data, questions, "Success")
        return questions
    except Exception as e:
        print(f"Interview Prep Agent Error: {e}")
        fallback = [
            f"Explain your experience working with NodeJS and Express in your projects.",
            f"How do you handle database connections and query optimizations in PostgreSQL?",
            f"Describe how you would debug a memory leak in a Node.js backend environment.",
            f"How do you design REST APIs to handle high traffic and concurrent client requests?",
            f"Explain your approach to implementing secure JWT authentication in full-stack apps."
        ]
        log_agent_run("Interview Preparation Agent", input_data, fallback, f"Fallback due to: {e}")
        return fallback

# --------------------------------------------------
# AGENT 7: INTERVIEW DECISION AGENT (Final Recommendation)
# --------------------------------------------------
def run_interview_decision(candidate_id: str, ats_score: float, assessment_score: float, rating: int, feedback: str) -> dict:
    """Collects screening metrics and generates final Hire / Reject decision with confidence."""
    prompt = PromptTemplate(
        input_variables=["ats", "assessment", "rating", "feedback"],
        template="""
        You are the Interview Decision AI Agent.
        Analyze the candidate's metrics and hiring manager feedback to make a final recommendation:
        * ATS Match Score: {ats}%
        * Coding Assessment Score: {assessment}%
        * Interview Rating: {rating}/10
        * Interview Feedback: {feedback}
        
        Generate the final decision in JSON format containing:
        * recommendation: "Strong Hire", "Hire", "Hold", "Reject"
        * confidence: Numerical confidence score (0 to 100) representing AI certainty.
        * reasoning: A concise 2-sentence rationale summarizing their fit.
        
        Return ONLY valid JSON.
        """
    )
    chain = prompt | llm
    input_data = {"ats": ats_score, "assessment": assessment_score, "rating": rating, "feedback": feedback}
    try:
        res = chain.invoke(input_data)
        content = res.content.strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()
            
        decision = json.loads(content)
        
        # Save recommendation in DB
        db = SessionLocal()
        try:
            # Clean existing recommendations for candidate
            db.query(Recommendation).filter(Recommendation.candidate_id == candidate_id).delete()
            
            rec = Recommendation(
                id=str(uuid.uuid4()),
                candidate_id=candidate_id,
                recommendation=decision["recommendation"],
                confidence=decision["confidence"],
                reasoning=decision["reasoning"],
                created_at=datetime.datetime.utcnow().isoformat()
            )
            db.add(rec)
            
            # Sync candidate final recommendations
            cand = db.query(Candidate).filter(Candidate.id == candidate_id).first()
            if cand:
                cand.ai_recommendation = f"{decision['recommendation']} ({decision['confidence']}%)"
                
            db.commit()
        finally:
            db.close()
            
        log_agent_run("Interview Decision Agent", input_data, decision, "Success")
        return decision
    except Exception as e:
        print(f"Interview Decision Agent Error: {e}")
        # Rule-based fallback decision
        rec_str = "Hold"
        if rating >= 8 and assessment_score >= 80:
            rec_str = "Strong Hire"
        elif rating >= 6 and assessment_score >= 70:
            rec_str = "Hire"
        elif rating <= 4:
            rec_str = "Reject"
            
        fallback = {
            "recommendation": rec_str,
            "confidence": 75.0,
            "reasoning": f"Rule-based recommendation generated due to Gemini error: {e}"
        }
        log_agent_run("Interview Decision Agent", input_data, fallback, f"Fallback due to: {e}")
        return fallback

# --------------------------------------------------
# LANGGRAPH WORKFLOW ORCHESTRATION
# --------------------------------------------------
class AgentState(TypedDict, total=False):
    candidate_id: Optional[str]
    job_id: Optional[str]
    candidate_name: Optional[str]
    candidate_email: Optional[str]
    resume_text: Optional[str]
    job_title: Optional[str]
    job_description: Optional[str]
    required_skills: Optional[str]
    structured_jd: Optional[Dict[str, Any]]
    screening_result: Optional[Dict[str, Any]]
    recommendation: Optional[str]
    assessment_details: Optional[Dict[str, Any]]
    submitted_code: Optional[str]
    code_language: Optional[str]
    evaluation_result: Optional[Dict[str, Any]]
    interview_questions: Optional[List[str]]
    interview_rating: Optional[int]
    interview_feedback: Optional[str]
    final_decision: Optional[Dict[str, Any]]

# Define Node wrapper functions matching LangGraph state signature
def jd_intelligence_node(state: AgentState) -> dict:
    if state.get("structured_jd"):
        return {}
    if not state.get("job_id") or not state.get("job_title"):
        return {}
    res = run_jd_intelligence(state["job_id"], state["job_title"], state.get("job_description", ""))
    return {"structured_jd": res}

def resume_screening_node(state: AgentState) -> dict:
    if state.get("screening_result"):
        return {}
    if not state.get("resume_text") or not state.get("candidate_name"):
        return {}
    skills = state.get("required_skills") or ""
    if state.get("structured_jd") and "skills" in state["structured_jd"]:
        skills = ", ".join(state["structured_jd"]["skills"])
    res = run_resume_screening(state["candidate_name"], state["resume_text"], skills)
    
    # Extract actual skills from resume text
    extracted = extract_skills(state["resume_text"])
    res["extracted_skills"] = extracted
    
    cand_id = state.get("candidate_id")
    if cand_id:
        db = SessionLocal()
        try:
            cand = db.query(Candidate).filter(Candidate.id == cand_id).first()
            if cand:
                cand.score = res.get("score", 0.0)
                cand.candidate_summary = res.get("summary", "")
                
                # Save extracted skills
                cand.skills = ", ".join(extracted)
                
                strengths_val = res.get("strengths", [])
                cand.strengths = ", ".join(strengths_val) if isinstance(strengths_val, list) else str(strengths_val)
                
                weaknesses_val = res.get("weaknesses", [])
                cand.weaknesses = ", ".join(weaknesses_val) if isinstance(weaknesses_val, list) else str(weaknesses_val)
                
                cand.ats_explanation = res.get("match_explanation", "")
                db.commit()
                print(f"[DB Sync] Resume screening results & skills synced for candidate: {cand_id}")
        except Exception as e:
            print(f"Error syncing screening results to DB: {e}")
            db.rollback()
        finally:
            db.close()
            
    return {"screening_result": res}

def assessment_recommendation_node(state: AgentState) -> dict:
    if state.get("recommendation"):
        return {}
    if not state.get("candidate_id") or not state.get("screening_result"):
        return {}
    ats_score = state["screening_result"].get("score", 0.0)
    decision = run_assessment_recommendation(state["candidate_id"], ats_score)
    return {"recommendation": decision}

def assessment_delivery_node(state: AgentState) -> dict:
    if state.get("assessment_details"):
        return {}
    if not state.get("candidate_id") or not state.get("job_id") or not state.get("candidate_email"):
        return {}
    skills = state.get("required_skills") or ""
    if state.get("structured_jd") and "skills" in state["structured_jd"]:
        skills = ", ".join(state["structured_jd"]["skills"])
    res = run_assessment_delivery(
        state["candidate_id"],
        state["job_id"],
        state["candidate_name"],
        state["candidate_email"],
        skills
    )
    return {"assessment_details": res}

def assessment_evaluation_node(state: AgentState) -> dict:
    if state.get("evaluation_result"):
        return {}
    if not state.get("submitted_code") or not state.get("code_language"):
        return {}
    token = state.get("assessment_details", {}).get("token") or state.get("candidate_id")
    res = run_assessment_evaluation(token, state["submitted_code"], state["code_language"])
    return {"evaluation_result": res}

def interview_preparation_node(state: AgentState) -> dict:
    if state.get("interview_questions"):
        return {}
    if not state.get("candidate_id") or not state.get("candidate_name"):
        return {}
    skills = state.get("required_skills") or ""
    report = state.get("evaluation_result", {}).get("report", "")
    res = run_interview_preparation(state["candidate_id"], state["candidate_name"], skills, report)
    return {"interview_questions": res}

def interview_decision_node(state: AgentState) -> dict:
    if state.get("final_decision"):
        return {}
    if not state.get("candidate_id") or state.get("interview_rating") is None:
        return {}
    ats_score = state.get("screening_result", {}).get("score", 0.0)
    assessment_score = state.get("evaluation_result", {}).get("score", 0.0)
    res = run_interview_decision(
        state["candidate_id"],
        ats_score,
        assessment_score,
        state["interview_rating"],
        state["interview_feedback"] or ""
    )
    return {"final_decision": res}

from langgraph.graph import StateGraph, END

# Define and build the workflow
workflow = StateGraph(AgentState)

workflow.add_node("jd_intelligence", jd_intelligence_node)
workflow.add_node("resume_screening", resume_screening_node)
workflow.add_node("assessment_recommendation", assessment_recommendation_node)
workflow.add_node("assessment_delivery", assessment_delivery_node)
workflow.add_node("assessment_evaluation", assessment_evaluation_node)
workflow.add_node("interview_preparation", interview_preparation_node)
workflow.add_node("interview_decision", interview_decision_node)

# Set edges
workflow.set_entry_point("jd_intelligence")
workflow.add_edge("jd_intelligence", "resume_screening")
workflow.add_edge("resume_screening", "assessment_recommendation")

def route_recommendation(state: AgentState):
    if state.get("recommendation") == "Assessed":
        return "assessment_delivery"
    return END

workflow.add_conditional_edges(
    "assessment_recommendation",
    route_recommendation,
    {
        "assessment_delivery": "assessment_delivery",
        END: END
    }
)

def route_delivery(state: AgentState):
    if state.get("submitted_code") is not None:
        return "assessment_evaluation"
    return END

workflow.add_conditional_edges(
    "assessment_delivery",
    route_delivery,
    {
        "assessment_evaluation": "assessment_evaluation",
        END: END
    }
)

workflow.add_edge("assessment_evaluation", "interview_preparation")

def route_interview_prep(state: AgentState):
    if state.get("interview_feedback") is not None:
        return "interview_decision"
    return END

workflow.add_conditional_edges(
    "interview_preparation",
    route_interview_prep,
    {
        "interview_decision": "interview_decision",
        END: END
    }
)

workflow.add_edge("interview_decision", END)

# Compile the LangGraph agent workflow
recruitment_langgraph_workflow = workflow.compile()

