import os
import sys
import json
from dotenv import load_dotenv
from sqlalchemy import text

# Load env variables
load_dotenv()

# Add current directory to path
sys.path.append(os.getcwd())

from database.db_postgres import SessionLocal, create_table, AssessmentQuestion

print("==================================================")
print("CLEARING ALL DATA FROM DATABASE TABLES")
print("==================================================")

db = SessionLocal()
try:
    # We will delete rows from all tables in correct order of foreign keys
    tables = [
        "recommendations",
        "interview_questions",
        "agent_logs",
        "candidate_journey",
        "assessment_results",
        "assessment_submissions",
        "assessments",
        "assessment_questions",
        "interviews",
        "candidates",
        "jobs",
        "users"
    ]
    
    print("Clearing tables...")
    for table in tables:
        try:
            print(f"Attempting to clear table: {table}...")
            db.execute(text(f"DELETE FROM {table}"))
            db.commit() # Commit after each delete to release locks
            print(f"Successfully cleared table: {table}")
        except Exception as e:
            db.rollback()
            print(f"Could not clear table {table}: {e}")
            
    print("All tables cleared successfully.")
    
    # Re-seed questions
    print("Re-seeding assessment questions...")
    if db.query(AssessmentQuestion).count() == 0:
        questions = [
            AssessmentQuestion(
                id="py_missing_num",
                language="python",
                title="Find the Missing Number in an Array",
                description="Write a function `find_missing(arr)` that takes an array of integers from 1 to N (where N is the length of the array + 1) with one missing number, and returns the missing number.\n\nSample Input: `[1, 2, 4, 5]`\nSample Output: `3`",
                template_code="def find_missing(arr):\n    # Write your code here\n    pass",
                test_cases=json.dumps([{"input": "[1, 2, 4, 5]", "expected": "3"}])
            ),
            AssessmentQuestion(
                id="java_reverse",
                language="java",
                title="Reverse a String",
                description="Write a method `reverseString(String str)` that reverses a given string.\n\nSample Input: `\"hello\"`\nSample Output: `\"olleh\"`",
                template_code="public class Solution {\n    public static String reverseString(String str) {\n        // Write your code here\n        return \"\";\n    }\n}",
                test_cases=json.dumps([{"input": "\"hello\"", "expected": "\"olleh\""}])
            ),
            AssessmentQuestion(
                id="react_duplicates",
                language="react",
                title="Find Duplicate Elements",
                description="Write a JavaScript function `findDuplicates(arr)` that returns a sorted array of duplicate numbers found in the input array.\n\nSample Input: `[1, 2, 3, 2, 4, 3]`\nSample Output: `[2, 3]`",
                template_code="function findDuplicates(arr) {\n    // Write your code here\n    return [];\n}",
                test_cases=json.dumps([{"input": "[1, 2, 3, 2, 4, 3]", "expected": "[2, 3]"}])
            )
        ]
        db.add_all(questions)
        db.commit()
        print("Database: Pre-populated 3 standard assessment coding questions.")
    
    print("\nDatabase is now 100% clean and fresh!")
    print("==================================================")
except Exception as e:
    db.rollback()
    print(f"Error clearing database: {e}")
    sys.exit(1)
finally:
    db.close()
