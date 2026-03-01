import streamlit as st
import pandas as pd
from modules.resume_parser import extract_text_from_pdf, extract_text_from_docx, extract_skills
from modules.scorer import calculate_score
from database.db import create_table, insert_candidate, get_all_candidates

# Create table when app starts
create_table()

st.title("Recruiter AI Agent - Resume Screener")

# Job input
job_input = st.text_area("Enter Required Skills (comma separated)")

# File upload (PDF + DOCX support)
uploaded_file = st.file_uploader("Upload Resume (PDF or DOCX)", type=["pdf", "docx"])

if uploaded_file and job_input:
    
    # Extract text based on file type
    if uploaded_file.name.endswith(".pdf"):
        text = extract_text_from_pdf(uploaded_file)
    else:
        text = extract_text_from_docx(uploaded_file)

    candidate_skills = extract_skills(text)
    required_skills = [skill.strip().lower() for skill in job_input.split(",")]

    score = calculate_score(candidate_skills, required_skills)

    st.subheader("Extracted Skills")
    st.write(candidate_skills)

    st.subheader("Match Score")
    st.write(f"{score}%")

    # Save button
    if st.button("Save Candidate"):
        insert_candidate(candidate_skills, score)
        st.success("Candidate saved successfully!")

# Display saved candidates
st.subheader("Saved Candidates")

candidates = get_all_candidates()

if candidates:
    df = pd.DataFrame(candidates, columns=["ID", "Skills", "Score"])
    st.dataframe(df)
else:
    st.write("No candidates saved yet.")