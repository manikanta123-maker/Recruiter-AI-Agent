import spacy
import PyPDF2
import docx

# Load NLP model
nlp = spacy.load("en_core_web_sm")

# Master skill list (can expand anytime)
SKILL_KEYWORDS = [
    "python", "java", "react", "sql",
    "machine learning", "flask", "django",
    "docker", "aws", "node", "mongodb",
    "html", "css", "c++"
]


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
# SKILL EXTRACTION FROM RESUME
# -----------------------------

def extract_skills(text):
    text = text.lower()
    found_skills = []

    for skill in SKILL_KEYWORDS:
        if skill in text:
            found_skills.append(skill)

    return list(set(found_skills))


# -----------------------------
# SKILL EXTRACTION FROM JOB DESCRIPTION
# -----------------------------

def extract_skills_from_jd(job_description):
    job_description = job_description.lower()
    extracted = []

    skill_keywords = [
        "python", "java", "react", "sql",
        "machine learning", "flask", "django",
        "docker", "aws", "node", "mongodb",
        "html", "css", "c++"
    ]

    for skill in skill_keywords:
        if skill in job_description:
            extracted.append(skill)

    return list(set(extracted))