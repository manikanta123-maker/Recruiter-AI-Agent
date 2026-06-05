import os
from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate

from modules.resume_parser import extract_skills
from modules.scorer import ats_score

# Define State Schema for the Recruitment Agent
class AgentState(TypedDict):
    candidate_name: str
    resume_text: str
    required_skills: List[str]
    candidate_skills: List[str]
    ats_score: float
    compliance_notes: str
    error: Optional[str]

# Node 1: Extract candidate skills from resume
def node_extract_skills(state: AgentState) -> dict:
    try:
        skills = extract_skills(state["resume_text"])
        return {"candidate_skills": skills, "error": None}
    except Exception as e:
        return {"error": f"Failed during skill extraction: {str(e)}"}

# Node 2: Calculate ATS Match Score
def node_calculate_ats(state: AgentState) -> dict:
    if state.get("error"):
        return {}
    try:
        score = ats_score(state["candidate_skills"], state["required_skills"], state["resume_text"])
        return {"ats_score": score, "error": None}
    except Exception as e:
        return {"error": f"Failed during ATS scoring: {str(e)}"}

# Node 3: Compliance & Bias Auditing Node
def node_audit_compliance(state: AgentState) -> dict:
    if state.get("error"):
        return {}
    
    # Check for potential demographic indicators to enforce data privacy and compliance
    prompt = PromptTemplate(
        input_variables=["resume"],
        template="""
        You are an HR Compliance & Bias Auditing AI.
        Analyze this resume snippet and determine if it contains highly sensitive personal information that should be masked or flagged (e.g., specific age, religion, marital status, gender indicators, or physical addresses).
        Also, check if the formatting exhibits signs of automated spam generation.
        Provide a concise, 1-2 sentence audit report.
        
        Resume text: {resume}
        """
    )
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0, google_api_key=os.getenv("GEMINI_API_KEY"))
    chain = prompt | llm
    
    try:
        response = chain.invoke({"resume": state["resume_text"][:2000]})
        return {"compliance_notes": response.content.strip(), "error": None}
    except Exception as e:
        return {"compliance_notes": f"Compliance check bypassed due to API error: {e}"}

# -----------------------------
# COMPILE LANGGRAPH STATE MACHINE
# -----------------------------
workflow = StateGraph(AgentState)

# Define Graph Nodes
workflow.add_node("extract_skills", node_extract_skills)
workflow.add_node("calculate_ats", node_calculate_ats)
workflow.add_node("audit_compliance", node_audit_compliance)

# Set Entry Point
workflow.set_entry_point("extract_skills")

# Define Graph Transitions
workflow.add_edge("extract_skills", "calculate_ats")
workflow.add_edge("calculate_ats", "audit_compliance")
workflow.add_edge("audit_compliance", END)

# Compile the graph
recruitment_agent_pipeline = workflow.compile()

def run_recruitment_pipeline(candidate_name: str, resume_text: str, required_skills: List[str]) -> AgentState:
    """Wrapper function to invoke the state graph."""
    initial_state = {
        "candidate_name": candidate_name,
        "resume_text": resume_text,
        "required_skills": required_skills,
        "candidate_skills": [],
        "ats_score": 0.0,
        "compliance_notes": "",
        "error": None
    }
    return recruitment_agent_pipeline.invoke(initial_state)
