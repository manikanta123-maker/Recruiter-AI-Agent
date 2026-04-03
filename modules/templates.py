TEMPLATES = {
    "interview_invite": """
Dear {name},

We are pleased to invite you for an interview for the {position} position.

Interview Date: {date}

Please confirm your availability.

Best regards,
Recruitment Team
""",

    "rejection": """
Dear {name},

Thank you for your interest in the {position} position.

After careful review, we regret to inform you that we will not be moving forward with your application.

We wish you success in your future endeavors.

Best regards,
Recruitment Team
"""
}


def generate_email(template_name, **kwargs):
    template = TEMPLATES.get(template_name)

    if not template:
        return "Template not found."

    return template.format(**kwargs)