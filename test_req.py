from modules.resume_parser import extract_skills_from_jd
import sys

print("Testing JD extraction...")
try:
    print(extract_skills_from_jd("Python developer with Fastapi experience"))
except Exception as e:
    print(f"Exception caught: {type(e).__name__}: {e}")
