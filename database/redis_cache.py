import os
import redis
import hashlib
import json

# Read Redis connection URI from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
except Exception as e:
    print(f"Failed to connect to Redis at {REDIS_URL}. Falling back to no-op cache: {e}")
    redis_client = None

def get_cache_key(resume_text: str, required_skills: list) -> str:
    """Generate a unique key based on the resume text and required skills."""
    # Hash resume text and sorted required skills to form a unique key
    skills_serialized = "".join(sorted(required_skills))
    content = f"{resume_text.strip()}:{skills_serialized}"
    sha256_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
    return f"ats_score:{sha256_hash}"

def get_cached_score(resume_text: str, required_skills: list) -> float:
    """Retrieve score from cache if it exists, otherwise return None."""
    if not redis_client:
        return None
    try:
        key = get_cache_key(resume_text, required_skills)
        cached_val = redis_client.get(key)
        if cached_val is not None:
            print("Redis Cache Hit! Retrieved ATS score.")
            return float(cached_val)
    except Exception as e:
        print(f"Error reading from Redis cache: {e}")
    return None

def set_cached_score(resume_text: str, required_skills: list, score: float, expiry: int = 3600):
    """Cache the calculated score with an expiration timer (default 1 hour)."""
    if not redis_client:
        return
    try:
        key = get_cache_key(resume_text, required_skills)
        redis_client.setex(key, expiry, str(score))
        print("Score cached in Redis.")
    except Exception as e:
        print(f"Error writing to Redis cache: {e}")
