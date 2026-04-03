import os
import re
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

load_dotenv()
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

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
        return min(max(score, 0), 100)
    except Exception as e:
        print(f"LLM Error during ATS scoring (falling back to rule-based): {e}")
        return match_score_rule_based(candidate_skills, required_skills)

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