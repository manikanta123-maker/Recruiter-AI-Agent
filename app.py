import streamlit as st
import pandas as pd
from modules.resume_parser import (
    extract_text_from_pdf,
    extract_text_from_docx,
    extract_skills,
    extract_skills_from_jd
)
from modules.scorer import calculate_score
from modules.matcher import match_candidate_to_job
from modules.scheduler import schedule_interview
from modules.templates import generate_email
from database.db import create_table, insert_candidate, get_all_candidates, update_status

# -------------------------------
# SETUP
# -------------------------------
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
        # Extract text
        if uploaded_file.name.endswith(".pdf"):
            text = extract_text_from_pdf(uploaded_file)
        else:
            text = extract_text_from_docx(uploaded_file)

        # Extract candidate skills
        candidate_skills = extract_skills(text)

        # Match candidate to job
        match_score = match_candidate_to_job(candidate_skills, required_skills)

        # Display candidate info
        st.markdown(f"### 📄 {uploaded_file.name}")
        st.write("Extracted Skills:", candidate_skills)
        st.progress(match_score / 100)
        st.write(f"Match Score: **{match_score}%**")

        # Candidate name input
        candidate_name = st.text_input(
            f"Enter Candidate Name for {uploaded_file.name}",
            key=uploaded_file.name
        )

        if st.button(f"Save {uploaded_file.name}", key=f"btn_{uploaded_file.name}"):
            insert_candidate(candidate_name, ", ".join(candidate_skills), match_score)
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
    ).sort_values(by="Score", ascending=False)

    # Recommendation based on score
    def recommend(score):
        if score >= 75:
            return "🔥 Strong Fit"
        elif score >= 50:
            return "👍 Moderate Fit"
        else:
            return "❌ Weak Fit"
    df["Recommendation"] = df["Score"].apply(recommend)

    # Top 3
    st.subheader("🔥 Top 3 Candidates")
    st.dataframe(df.head(3))

    # Full Table
    st.subheader("📊 All Candidates")
    st.dataframe(df)

    # Analytics
    st.subheader("📊 Analytics Dashboard")
    st.markdown("### 📈 Candidate Score Comparison")
    st.bar_chart(df.set_index("Name")["Score"])
    st.markdown("### 📌 Status Distribution")
    st.bar_chart(df["Status"].value_counts())

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Average Candidate Score", f"{round(df['Score'].mean(), 2)}%")
    with col2:
        st.metric("Total Candidates", len(df))

    # CSV Download
    st.subheader("⬇️ Download Candidates Data")
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download Candidates as CSV",
        data=csv,
        file_name="candidates_data.csv",
        mime="text/csv"
    )

    # -------------------------------
    # STATUS UPDATE & INTERVIEW SCHEDULING
    # -------------------------------
    st.subheader("✏️ Update Candidate Status / Schedule Interview")
    selected_id = st.selectbox("Select Candidate ID", df["ID"])
    new_status = st.selectbox("Change Status", ["Applied", "Shortlisted", "Scheduled", "Rejected"])

    interview_date = None
    if new_status == "Scheduled":
        interview_date = st.date_input("Select Interview Date")
        # Schedule interview in DB
        if st.button("Schedule Interview"):
            schedule_interview(selected_id, 1, str(interview_date))  # Job ID = 1 for demo
            update_status(selected_id, new_status, str(interview_date))
            st.success(f"Interview scheduled for {interview_date}!")

            # Generate email
            candidate_row = df[df["ID"] == selected_id].iloc[0]
            email_text = generate_email(
                "interview_invite",
                name=candidate_row["Name"],
                date=str(interview_date),
                position="Software Engineer"
            )
            st.text_area("📧 Generated Email", email_text, height=150)

    elif st.button("Update Status Only"):
        update_status(selected_id, new_status)
        st.success("Status Updated Successfully!")

else:
    st.write("No candidates saved yet.")