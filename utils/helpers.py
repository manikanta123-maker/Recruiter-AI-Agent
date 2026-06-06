import os
import requests
import email.utils
import smtplib
from email.mime.text import MIMEText

def send_email(to_email: str, subject: str, body: str) -> bool:
    """
    Mock email sender (Emailing disabled). Prints email to console/logs and returns True.
    """
    print(f"\n[MOCK EMAIL - OUTGOING DISABLED]")
    print(f"To: {to_email}")
    print(f"Subject: {subject}")
    print(f"Body:\n{body}")
    print("----------------------------------------\n")
    return True
