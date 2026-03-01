import spacy
import PyPDF2
import docx

nlp = spacy.load("en_core_web_sm")

def extract_text_from_pdf(file):
    reader = PyPDF2.PdfReader(file)
    text = ""
    for page in reader.pages:
        if page.extract_text():
            text += page.extract_text()
    return text

def extract_text_from_docx(file):
    doc = docx.Document(file)
    return "\n".join([para.text for para in doc.paragraphs])

def extract_skills(text):
    doc = nlp(text)
    skills = []
    skill_keywords = [
        "python", "java", "react", "sql",
        "machine learning", "flask", "django"
    ]

    for token in doc:
        if token.text.lower() in skill_keywords:
            skills.append(token.text.lower())

    return list(set(skills))