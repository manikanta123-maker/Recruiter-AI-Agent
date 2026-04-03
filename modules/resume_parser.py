import os
import PyPDF2
import docx
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate

# Load environment variables
load_dotenv()

# Initialize the LLM via LangChain using Google Gemini
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0, google_api_key=os.getenv("GEMINI_API_KEY"))

# -----------------------------
# TEXT EXTRACTION FUNCTIONS
# -----------------------------
def extract_text_from_pdf(file):
    reader = PyPDF2.PdfReader(file)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text
    return text.lower()

def extract_text_from_docx(file):
    doc = docx.Document(file)
    return "\n".join([para.text for para in doc.paragraphs]).lower()

# -----------------------------
# TRUE AI SKILL EXTRACTION FROM RESUME
# -----------------------------
def extract_skills(text):
    prompt = PromptTemplate(
        input_variables=["text"],
        template="You are an expert technical recruiter AI. Extract the candidate's core technical and soft skills from this resume text as a clean, comma-separated list. No bullet points, just the comma-separated skills. Resume Text: {text}"
    )
    chain = prompt | llm
    try:
        response = chain.invoke({"text": text[:5000]}) # limit text size
        skills = [s.strip().lower() for s in response.content.split(',')]
        return list(set(skills))
    except Exception as e:
        print(f"Error inside LangChain extracting skills: {e}")
        return []

# -----------------------------
# TRUE AI SKILL EXTRACTION FROM JOB DESCRIPTION
# -----------------------------
def extract_skills_from_jd(job_description):
    prompt = PromptTemplate(
        input_variables=["jd"],
        template="You are an expert technical recruiter AI. Extract the core technical and soft skills required from this job description as a clean, comma-separated list. No bullet points, just the comma-separated skills. Job Description: {jd}"
    )
    chain = prompt | llm
    try:
        response = chain.invoke({"jd": job_description[:5000]})
        skills = [s.strip().lower() for s in response.content.split(',')]
        return list(set(skills))
    except Exception as e:
        print(f"Error inside LangChain extracting JD skills: {e}")
        raise e