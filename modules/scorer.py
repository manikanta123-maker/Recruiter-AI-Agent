def calculate_score(candidate_skills, required_skills):
    match_count = len(set(candidate_skills) & set(required_skills))
    total_required = len(required_skills)

    if total_required == 0:
        return 0

    score = (match_count / total_required) * 100
    return round(score, 2)