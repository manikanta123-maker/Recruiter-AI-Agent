import streamlit as st
import pandas as pd
from modules.resume_parser import (
    extract_text_from_pdf,
    extract_text_from_docx,
    extract_skills,
    extract_skills_from_jd
)
from modules.scorer import calculate_score
from database.db import create_table, insert_candidate, get_all_candidates, update_status

# Create DB table
create_table()

st.set_page_config(page_title="Recruiter AI Agent", layout="wide")

st.title("🤖 Recruiter AI Agent - Mini ATS System")

# -------------------------------
# JOB DESCRIPTION INPUT
# -------------------------------

st.subheader("📄 Job Description")
job_description = st.text_area("Paste Full Job Description")

required_skills = []
if job_description:
    required_skills = extract_skills_from_jd(job_description)
    st.write("🔍 Extracted Required Skills:", required_skills)

# -------------------------------
# FILE UPLOAD
# -------------------------------

st.subheader("📂 Upload Resumes")

uploaded_files = st.file_uploader(
    "Upload Multiple Resumes (PDF or DOCX)",
    type=["pdf", "docx"],
    accept_multiple_files=True
)

if uploaded_files and required_skills:

    for uploaded_file in uploaded_files:

        if uploaded_file.name.endswith(".pdf"):
            text = extract_text_from_pdf(uploaded_file)
        else:
            text = extract_text_from_docx(uploaded_file)

        candidate_skills = extract_skills(text)
        score = calculate_score(candidate_skills, required_skills)

        st.markdown(f"### 📄 {uploaded_file.name}")
        st.write("Extracted Skills:", candidate_skills)
        st.progress(score / 100)
        st.write(f"Match Score: **{score}%**")

        candidate_name = st.text_input(
            f"Enter Candidate Name for {uploaded_file.name}",
            key=uploaded_file.name
        )

        if st.button(f"Save {uploaded_file.name}", key=f"btn_{uploaded_file.name}"):
            insert_candidate(candidate_name, ", ".join(candidate_skills), score)
            st.success(f"{candidate_name} saved successfully!")
            st.rerun()

# -------------------------------
# DISPLAY & RANKING SECTION
# -------------------------------

st.subheader("🏆 Candidate Ranking")

candidates = get_all_candidates()

if candidates:
    df = pd.DataFrame(
        candidates,
        columns=["ID", "Name", "Skills", "Score", "Status", "Interview Date"]
    )

    df = df.sort_values(by="Score", ascending=False)

    # Highlight Top 3
    st.subheader("🔥 Top 3 Candidates")
    st.dataframe(df.head(3))

    st.subheader("📊 All Candidates")
    st.dataframe(df)

    # -------------------------------
    # STATUS UPDATE SECTION
    # -------------------------------

    st.subheader("✏️ Update Candidate Status")

    selected_id = st.selectbox("Select Candidate ID", df["ID"])

    new_status = st.selectbox(
        "Change Status",
        ["Applied", "Shortlisted", "Scheduled", "Rejected"]
    )

    interview_date = None
    if new_status == "Scheduled":
        interview_date = st.date_input("Select Interview Date")

    if st.button("Update Status"):
        update_status(selected_id, new_status, interview_date)
        st.success("Status Updated Successfully!")
        st.rerun()

else:
    st.write("No candidates saved yet.")