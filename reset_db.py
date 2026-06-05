import os
import sys
from dotenv import load_dotenv

# Load env variables
load_dotenv()

# Add current directory to path
sys.path.append(os.getcwd())

from database.db_postgres import Base, engine, create_table
from main import seed_assessment_questions

print("==================================================")
print("RESETTING DATABASE TO A FRESH AND CLEAN STATE")
print("==================================================")

try:
    # Drop all tables
    print("Dropping all existing database tables...")
    Base.metadata.drop_all(bind=engine)
    print("All tables dropped successfully.")
    
    # Recreate all tables
    print("Recreating database tables...")
    create_table()
    print("All tables recreated successfully.")
    
    # Seed coding questions
    print("Seeding default coding questions...")
    seed_assessment_questions()
    print("Seeding completed successfully.")
    
    print("\nDatabase is now 100% clean and fresh!")
    print("==================================================")
except Exception as e:
    print(f"Error resetting database: {e}")
    sys.exit(1)
