def match_candidate_to_job(candidate_skills, job_skills):
    """
    Returns a match percentage between candidate skills and job requirements.
    """
    candidate_set = set([skill.lower() for skill in candidate_skills])
    job_set = set([skill.lower() for skill in job_skills])
    
    matched_skills = candidate_set.intersection(job_set)
    if not job_set:
        return 0
    match_percentage = (len(matched_skills) / len(job_set)) * 100
    return round(match_percentage, 2)