from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List

import requests

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")


def is_ollama_active() -> bool:
    """Check if local Ollama service is up and responding."""
    try:
        resp = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=1.5)
        return resp.status_code == 200
    except Exception:
        return False


def heuristic_match_job(candidate_spec: Dict[str, Any], job_listing: Dict[str, Any]) -> Dict[str, Any]:
    """Fast, accurate fallback evaluation using keyword skill matching & scoring logic."""
    profile = candidate_spec.get("candidate_profile", {})
    skills_dict = profile.get("core_skills", {})
    all_candidate_skills = []
    for cat_skills in skills_dict.values():
        if isinstance(cat_skills, list):
            all_candidate_skills.extend(cat_skills)
        elif isinstance(cat_skills, str):
            all_candidate_skills.append(cat_skills)

    target_roles = profile.get("target_roles", [])
    title = job_listing.get("title", "")
    desc = job_listing.get("description", "")
    company = job_listing.get("company", "")
    url = job_listing.get("url", "")

    combined_text = (title + " " + desc + " " + " ".join(job_listing.get("key_skills_found", []))).lower()

    # Find matched skills
    matched = []
    for skill in all_candidate_skills:
        # Match word boundaries or substring
        pattern = r"\b" + re.escape(skill.lower()) + r"\b"
        if re.search(pattern, combined_text) or skill.lower() in combined_text:
            matched.append(skill)
    matched = list(dict.fromkeys(matched))

    # Common technology requirements for missing skill detection
    tech_pool = ["Docker", "Kubernetes", "AWS", "SQL", "React", "PyTorch", "ROS2", "TypeScript", "FastAPI"]
    missing = []
    for tech in tech_pool:
        if tech.lower() in combined_text and tech not in matched:
            missing.append(tech)

    # Base score calculation
    score = 50
    # Role match bonus
    if any(r.lower() in title.lower() for r in target_roles):
        score += 15

    # Interested fields bonus
    interested_fields = profile.get("interested_fields", [])
    if any(f.lower() in combined_text for f in interested_fields):
        score += 10

    # Projects overlap bonus
    projects = profile.get("projects", [])
    for proj in projects:
        p_desc = (proj.get("name", "") + " " + proj.get("description", "")).lower()
        if any(w in p_desc for w in title.lower().split()):
            score += 5
            break

    # Skill match bonus
    score += min(25, len(matched) * 6)

    # Excluded keywords check
    excluded = profile.get("preferred_platforms_and_locations", {}).get("excluded_keywords", [])
    for ex in excluded:
        if ex.lower() in combined_text:
            score -= 15

    # Location Eligibility Validation
    job_loc = job_listing.get("location", "").lower()
    pref_locs = profile.get("preferred_platforms_and_locations", {}).get("preferred_locations", ["India", "Remote"])
    pref_loc_lowers = [l.lower() for l in pref_locs]

    is_us_onsite = any(u in job_loc for u in ["united states", "usa", "san francisco", "new york", "austin", "ca, us", "ny, us"]) and not any(r in job_loc for r in ["remote", "india", "worldwide", "anywhere"])
    is_location_match = any(p in job_loc for p in pref_loc_lowers) or any(k in job_loc for k in ["india", "remote", "worldwide", "work from home", "hybrid"])

    base_dict = {
        "id": job_listing.get("id", f"job_{hash(title + company) & 0xffffff}"),
        "job_id": job_listing.get("id", f"job_{hash(title + company) & 0xffffff}"),
        "source": job_listing.get("source", "Web Search"),
        "title": title,
        "job_title": title,
        "company": company,
        "location": job_listing.get("location", "Remote"),
        "description": desc,
        "url": url,
        "posted_date": job_listing.get("posted_date", "Today"),
        "stipend_salary": job_listing.get("stipend_salary", "Not Disclosed"),
    }

    if is_us_onsite:
        score = 25
        tier = "LOW MATCH"
        rec = f"Ineligible Region: Role is on-site in {job_listing.get('location')}. Candidate is located in India / Remote."
        return {
            **base_dict,
            "suitability_score": score,
            "match_tier": tier,
            "matched_skills": matched if matched else ["Python"],
            "missing_skills": ["US Work Authorization"],
            "recommendation": rec
        }

    if is_location_match:
        score += 15

    score = max(35, min(98, score))

    if score >= 75:
        tier = "HIGH MATCH"
    elif score >= 50:
        tier = "MEDIUM MATCH"
    else:
        tier = "LOW MATCH"

    if matched:
        rec = f"Strong fit for your background in {', '.join(matched[:3])}. Role is located in {job_listing.get('location')}, matching candidate preferences."
    else:
        rec = f"Relevant entry-level opportunity at {company} in {job_listing.get('location')}. Review key skill requirements."

    return {
        **base_dict,
        "suitability_score": score,
        "match_tier": tier,
        "matched_skills": matched if matched else ["Python", "Git"],
        "missing_skills": missing[:3],
        "recommendation": rec
    }


def match_job_with_ollama(candidate_spec: Dict[str, Any], job_listing: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate job listing using Ollama local LLM with fallback to heuristic logic."""
    if not is_ollama_active():
        return heuristic_match_job(candidate_spec, job_listing)

    prompt = f"""
    You are an expert AI Technical Recruiter. Evaluate the fit between the candidate and the job listing.

    CANDIDATE SPECIFICATION:
    {json.dumps(candidate_spec, indent=2)}

    JOB LISTING:
    Title: {job_listing.get('title')}
    Company: {job_listing.get('company')}
    Location: {job_listing.get('location')}
    Description: {job_listing.get('description')}
    URL: {job_listing.get('url')}

    INSTRUCTIONS:
    1. CRITICAL LOCATION CHECK: Candidate is based in India and prefers India / Remote positions. If the job is on-site in the US/America and not remote, assign suitability_score < 40 and match_tier "LOW MATCH".
    2. Calculate a Suitability Score from 0 to 100 based on skill overlap, location match, and experience level.
    3. Identify key matching skills and missing/gap skills.
    4. State clearly if this is a "HIGH MATCH" (>= 75), "MEDIUM MATCH" (50-74), or "LOW MATCH" (< 50).
    5. Provide a 2-sentence rationale on why the candidate should or should not apply.

    Return JSON strictly in this format:
    {{
        "job_title": "{job_listing.get('title')}",
        "company": "{job_listing.get('company')}",
        "url": "{job_listing.get('url')}",
        "suitability_score": 85,
        "match_tier": "HIGH MATCH",
        "matched_skills": ["Python", "Git"],
        "missing_skills": ["Docker"],
        "recommendation": "Strong match based on Python and web framework background..."
    }}
    """

    try:
        endpoint = f"{OLLAMA_HOST}/api/generate"
        resp = requests.post(
            endpoint,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json"
            },
            timeout=2.5
        )
        if resp.status_code == 200:
            raw_text = resp.json().get("response", "")
            parsed = json.loads(raw_text)
            # Ensure required keys exist
            parsed["suitability_score"] = int(parsed.get("suitability_score", 70))
            parsed["match_tier"] = parsed.get("match_tier", "HIGH MATCH" if parsed["suitability_score"] >= 75 else "MEDIUM MATCH")
            return parsed
    except Exception as e:
        print(f"[Ollama Evaluator Exception]: {e}")

    return heuristic_match_job(candidate_spec, job_listing)
