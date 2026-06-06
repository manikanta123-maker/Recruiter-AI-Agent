import os
import requests
import email.utils
import smtplib
from email.mime.text import MIMEText

def send_email(to_email: str, subject: str, body: str) -> bool:
    """
    Sends an email using Brevo (highest priority), Resend (medium priority), 
    or SMTP/Gmail (fallback). If none are configured, prints to console (mock).
    """
    # 1. Try Brevo API
    brevo_key = os.getenv("BREVO_API_KEY")
    if brevo_key:
        sender_name = "Recruiter AI Agent"
        sender_email = "recruiterjobgiver@gmail.com"  # fallback default
        
        env_sender_email = os.getenv("BREVO_SENDER_EMAIL")
        env_sender_name = os.getenv("BREVO_SENDER_NAME")
        if env_sender_email:
            sender_email = env_sender_email
            if env_sender_name:
                sender_name = env_sender_name
        else:
            email_sender = os.getenv("EMAIL_SENDER")
            if email_sender:
                parsed_name, parsed_email = email.utils.parseaddr(email_sender)
                if parsed_email:
                    sender_email = parsed_email
                    if parsed_name:
                        sender_name = parsed_name
                else:
                    sender_email = email_sender
                    
        url = "https://api.brevo.com/v3/smtp/email"
        headers = {
            "accept": "application/json",
            "api-key": brevo_key,
            "content-type": "application/json"
        }
        payload = {
            "sender": {
                "name": sender_name,
                "email": sender_email
            },
            "to": [
                {
                    "email": to_email
                }
            ],
            "subject": subject,
            "htmlContent": body.replace("\n", "<br>")
        }
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=15)
            if res.status_code in (200, 201):
                print(f"Brevo: Email successfully sent to {to_email}")
                return True
            else:
                print(f"Brevo API failed (status {res.status_code}): {res.text}. Trying fallbacks.")
        except Exception as e:
            print(f"Brevo API error: {e}. Trying fallbacks.")

    # 2. Try Resend API
    resend_key = os.getenv("RESEND_API_KEY")
    if resend_key:
        try:
            url = "https://api.resend.com/emails"
            headers = {
                "Authorization": f"Bearer {resend_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "from": "Recruiter AI <onboarding@resend.dev>",
                "to": [to_email],
                "subject": subject,
                "html": body.replace("\n", "<br>")
            }
            res = requests.post(url, headers=headers, json=payload, timeout=15)
            if res.status_code in (200, 201):
                print(f"Resend: Email successfully sent to {to_email}")
                return True
            else:
                print(f"Resend API failed (status {res.status_code}): {res.text}. Trying fallbacks.")
        except Exception as e:
            print(f"Resend API error: {e}. Trying fallbacks.")

    # 3. Try standard SMTP/Gmail
    sender_email = os.getenv("EMAIL_SENDER")
    app_password = os.getenv("EMAIL_APP_PASSWORD")
    if sender_email and app_password:
        _, clean_sender = email.utils.parseaddr(sender_email)
        if not clean_sender:
            clean_sender = sender_email
            
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = to_email
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
                server.login(clean_sender, app_password)
                server.send_message(msg)
            print(f"SMTP: Email successfully sent to {to_email}")
            return True
        except Exception as e:
            print(f"SMTP failed to send: {e}")
            
    # Mock send fallback
    print(f"[MOCK EMAIL] To: {to_email} | Subject: {subject} | Body:\n{body}")
    return True
