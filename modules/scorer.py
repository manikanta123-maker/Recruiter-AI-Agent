import os
import re
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from database.redis_cache import get_cached_score, set_cached_score

load_dotenv()
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", 
    temperature=0, 
    google_api_key=os.getenv("GEMINI_API_KEY"),
    max_retries=1
)

def match_score_rule_based(candidate_skills, required_skills):
    match_count = len(set(candidate_skills) & set(required_skills))
    total_required = len(required_skills)
    if total_required == 0:
        return 0
    score = (match_count / total_required) * 100
    return round(score, 2)

# --------------------------------
# TRUE AI ATS Resume Scoring
# --------------------------------
def ats_score(candidate_skills, required_skills, resume_text):
    # Check cache first to avoid repetitive LLM costs
    cached_score = get_cached_score(resume_text, required_skills)
    if cached_score is not None:
        return cached_score

    prompt = PromptTemplate(
        input_variables=["resume", "skills", "candidate_skills"],
        template="""
        You are an elite AI Applicant Tracking System (ATS).
        Evaluate this resume and the extracted skills against the REQUIRED skills for a particular job.
        
        Required Skills for Job: {skills}
        Candidate's Extracted Skills: {candidate_skills}
        Resume Context Snippet: {resume}
        
        Score the overall candidate match from 0 to 100 based on relevant professional experience, education, and context matching.
        *SPECIAL INSTRUCTION*: Explicitly highly value Indian Education Context (B.Tech, M.Tech, Tier-1 colleges like IIT/NIT/BITS) if technical degrees are required.
        Provide ONLY the final numerical score (0-100). Do not provide any justification text.
        """
    )
    chain = prompt | llm
    try:
        # LLM based scoring evaluation
        response = chain.invoke({
            "resume": resume_text[:3000],
            "skills": ", ".join(required_skills),
            "candidate_skills": ", ".join(candidate_skills)
        })
        match = re.search(r'\d+', response.content)
        score = float(match.group()) if match else 0.0
        final_score = min(max(score, 0), 100)
        set_cached_score(resume_text, required_skills, final_score)
        return final_score
    except Exception as e:
        print(f"LLM Error during ATS scoring (falling back to rule-based): {e}")
        fallback_score = match_score_rule_based(candidate_skills, required_skills)
        set_cached_score(resume_text, required_skills, fallback_score)
        return fallback_score

# --------------------------------
# Screening Score (Questionnaire)
# --------------------------------
def screening_score(experience, notice_period):
    exp_score = min(experience * 2, 10)
    notice_score = 0

    if notice_period == "Immediate":
        notice_score = 10
    elif notice_period == "15 days":
        notice_score = 8
    elif notice_period == "30 days":
        notice_score = 5
    else:
        notice_score = 2

    return exp_score + notice_score