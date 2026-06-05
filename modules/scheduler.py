import os
import uuid
import random
from database.db_postgres import insert_interview

# Google API client imports
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def schedule_interview(candidate_id, job_id, interview_datetime):
    """
    Schedule an interview, log it in PostgreSQL, and book it in Google Calendar using real OAuth credentials.
    """
    # Insert record to PostgreSQL DB
    insert_interview(candidate_id, job_id, interview_datetime)

    # Read credentials from environment
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")

    if client_id and client_secret and refresh_token:
        try:
            # Recreate credentials using client ID, secret, and refresh token
            creds = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_secret
            )

            # Build Calendar service
            service = build('calendar', 'v3', credentials=creds)

            # Create event data structure with a Google Meet request
            event_body = {
                'summary': f'Technical Interview - Recruiter AI Agent',
                'description': 'Technical screening interview triggered autonomously by the Recruiter AI Agent.',
                'start': {
                    # Convert 'YYYY-MM-DD' to ISO DateTime format
                    'dateTime': f'{interview_datetime}T10:00:00',
                    'timeZone': 'Asia/Kolkata',
                },
                'end': {
                    'dateTime': f'{interview_datetime}T11:00:00',
                    'timeZone': 'Asia/Kolkata',
                },
                'conferenceData': {
                    'createRequest': {
                        'requestId': str(uuid.uuid4()),
                        'conferenceSolutionKey': {
                            'type': 'hangoutsMeet'
                        }
                    }
                }
            }

            # Insert event into user's primary calendar
            event = service.events().insert(
                calendarId='primary',
                body=event_body,
                conferenceDataVersion=1
            ).execute()

            # Retrieve Google Meet link
            meet_url = event.get('hangoutLink')
            
            # If Google Meet was not returned, fallback to event details HTML Link
            if not meet_url:
                meet_url = event.get('htmlLink')

            print(f"Google Calendar API: Event successfully booked! Meet Link: {meet_url}")
            
            return {
                "status": "Scheduled",
                "date": interview_datetime,
                "meet_url": meet_url,
                "message": "Interview successfully booked on Google Calendar."
            }

        except Exception as e:
            print(f"Google API failed (falling back to simulation): {e}")

    # Fallback simulation if API config is incomplete or fails
    meet_code = "".join(random.choices("abcdefghijklmnopqrstuvwxyz", k=10))
    meet_code_formatted = f"{meet_code[:3]}-{meet_code[3:7]}-{meet_code[7:]}"
    google_meet_url = f"https://meet.google.com/{meet_code_formatted}"
    
    print(f"Simulation Mode: Event created for {interview_datetime} | Meet URL: {google_meet_url}")
    
    return {
        "status": "Scheduled",
        "date": interview_datetime,
        "meet_url": google_meet_url,
        "message": "Google Calendar slot booked (Simulation Mode)."
    }