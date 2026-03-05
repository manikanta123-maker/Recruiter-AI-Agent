EMPLATES = {
    "interview_invite": "Hello {name},\nYou are invited for an interview on {date} for the position {position}.\nBest regards,\nHR Team",
    "rejection": "Hello {name},\nThank you for applying to {position}. We regret to inform you that you were not selected.\nBest regards,\nHR Team",
    "shortlist": "Hello {name},\nCongratulations! You have been shortlisted for the next round of interviews for {position}.\nBest regards,\nHR Team"
}

def generate_email(template_name, **kwargs):
    template = TEMPLATES.get(template_name)
    if not template:
        return "Template not found"
    return template.format(**kwargs)