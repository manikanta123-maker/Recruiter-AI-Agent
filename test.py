import os
import sys

# Change stderr so we see everything
sys.stderr = sys.stdout

from modules.resume_parser import extract_skills_from_jd

try:
    print("Testing LangChain invoke...")
    res = extract_skills_from_jd("We want a React and Python Developer with FastAPI skills.")
    print(f"Extraction Output: {res}")
except Exception as e:
    print(f"FAILED: {e}")
