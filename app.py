import streamlit as st
import pandas as pd

from database.db import (
    create_table,
    insert_candidate,
    get_all_candidates,
    update_status,
    update_screening,
    save_feedback,
    update_final_score
)

from modules.resume_parser import (
    extract_text_from_pdf,
    extract_text_from_docx,
    extract_skills,
    extract_skills_from_jd
)

from modules.scorer import ats_score, screening_score
from modules.scheduler import schedule_interview
from modules.templates import generate_email


# -------------------------------
# SETUP
# -------------------------------
create_table()

st.set_page_config(page_title="Recruiter AI Agent", layout="wide")
st.title("🤖 Recruiter AI Agent - Automated Screening Engine")


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

        ats = ats_score(candidate_skills, required_skills, text)

        st.markdown(f"### 📄 {uploaded_file.name}")
        st.write("Extracted Skills:", candidate_skills)

        st.progress(ats / 100)
        st.write(f"ATS Score: **{ats}%**")

        candidate_name = st.text_input(
            f"Enter Candidate Name for {uploaded_file.name}",
            key=uploaded_file.name
        )

        if st.button(f"Save {uploaded_file.name}", key=f"btn_{uploaded_file.name}"):

            insert_candidate(candidate_name, ", ".join(candidate_skills), ats)

            st.success(f"{candidate_name} saved successfully!")
            st.rerun()


# -------------------------------
# CANDIDATE DATA
# -------------------------------
st.subheader("🏆 Candidate Ranking")

candidates = get_all_candidates()

if candidates:

    df = pd.DataFrame(
        candidates,
        columns=["ID", "Name", "Skills", "Score", "Status", "Interview Date"]
    )

    df = df.sort_values(by="Score", ascending=False)

    # -------------------------------
    # LEADERBOARD
    # -------------------------------
    st.subheader("🏆 Leaderboard")

    leaderboard = df[["Name","Score","Status"]]

    leaderboard = leaderboard.rename(columns={
        "Name":"Candidate",
        "Score":"Final Score",
        "Status":"Hiring Status"
    })

    st.dataframe(leaderboard, use_container_width=True)


    # -------------------------------
    # TOP CANDIDATES
    # -------------------------------
    st.subheader("🔥 Top Candidates")
    st.dataframe(df.head(3))


    # -------------------------------
    # ALL CANDIDATES
    # -------------------------------
    st.subheader("📊 All Candidates")
    st.dataframe(df)


    # -------------------------------
    # ANALYTICS DASHBOARD
    # -------------------------------
    st.subheader("📊 Recruitment Dashboard")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Average Score", round(df["Score"].mean(),2))

    with col2:
        st.metric("Total Candidates", len(df))

    st.bar_chart(df.set_index("Name")["Score"])

    st.subheader("Hiring Funnel")
    st.bar_chart(df["Status"].value_counts())


    # -------------------------------
    # SCREENING QUESTIONNAIRE
    # -------------------------------
    st.subheader("📞 Screening Evaluation")

    selected_candidate = st.selectbox(
        "Select Candidate",
        df["ID"]
    )

    experience = st.number_input("Years of Experience", 0, 20)

    notice_period = st.selectbox(
        "Notice Period",
        ["Immediate","15 days","30 days","60 days"]
    )

    expected_salary = st.number_input("Expected Salary (INR)",0)

    if st.button("Evaluate Candidate"):

        ats = df.loc[df["ID"]==selected_candidate,"Score"].values[0]

        screen = screening_score(experience, notice_period)

        final_score = ats + screen

        update_screening(selected_candidate,experience,notice_period,expected_salary)

        update_final_score(selected_candidate,final_score)

        st.success("Candidate evaluation completed!")

        st.write("ATS Score:",ats)
        st.write("Screening Score:",screen)
        st.write("Final Score:",final_score)

        st.rerun()


    # -------------------------------
    # INTERVIEW MANAGEMENT
    # -------------------------------
    st.subheader("📅 Interview Management")

    selected_id = st.selectbox("Select Candidate ID", df["ID"])

    new_status = st.selectbox(
        "Update Status",
        ["Applied","Shortlisted","Scheduled","Rejected"]
    )

    if new_status == "Scheduled":

        interview_date = st.date_input("Interview Date")

        if st.button("Schedule Interview"):

            schedule_interview(selected_id,1,str(interview_date))

            update_status(selected_id,new_status,str(interview_date))

            st.success("Interview Scheduled")

            candidate_row = df[df["ID"]==selected_id].iloc[0]

            email_text = generate_email(
                "interview_invite",
                name=candidate_row["Name"],
                date=str(interview_date),
                position="Software Engineer"
            )

            st.text_area("Generated Email", email_text, height=150)

    elif st.button("Update Status"):

        update_status(selected_id,new_status)

        st.success("Status Updated")


    # -------------------------------
    # FEEDBACK
    # -------------------------------
    st.subheader("📝 Interview Feedback")

    feedback_candidate = st.selectbox(
        "Select Candidate for Feedback",
        df["ID"]
    )

    rating = st.slider("Candidate Rating",1,10)

    feedback = st.text_area("Feedback")

    if st.button("Submit Feedback"):

        save_feedback(feedback_candidate,rating,feedback)

        st.success("Feedback Saved")


else:

    st.write("No candidates saved yet.")