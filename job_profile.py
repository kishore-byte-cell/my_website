from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

PROFILE_PATH = Path(__file__).parent / "candidate_profile.json"

DEFAULT_PROFILE: Dict[str, Any] = {
    "candidate_profile": {
        "full_name": "Kishore",
        "contact_email": "kishore@example.com",
        "age": 21,
        "location": "India / Remote",
        "present_degree": "B.Tech Computer Science (Final Year)",
        "educational_qualifications": [
            "B.Tech in Computer Science & Engineering (2022 - 2026)",
            "Higher Secondary Education (Physics & Mathematics specialization)"
        ],
        "interested_fields": [
            "Artificial Intelligence & Machine Learning",
            "Interactive 3D Web Development",
            "Robotics & Computer Vision",
            "Data Analytics & Quantitative Research"
        ],
        "target_roles": [
            "Python Developer",
            "AI Engineer",
            "3D Web Developer",
            "Data Analyst",
            "Physics / Robotics Researcher"
        ],
        "employment_type": [
            "Internship",
            "Entry-Level Job",
            "Remote / Work From Home",
            "Full-Time"
        ],
        "projects": [
            {
                "name": "Daily Intelligence Pipeline & News Dispatcher",
                "description": "Python, Streamlit, Ollama LLM, SQLite automated market research and news executive briefing engine."
            },
            {
                "name": "3D Web & MediaPipe Vision Control System",
                "description": "Interactive Three.js WebGL application integrated with MediaPipe gesture recognition and Blender models."
            }
        ],
        "core_skills": {
            "programming": ["Python", "JavaScript", "Three.js", "C++"],
            "tools_frameworks": ["VS Code", "Git/GitHub", "Ollama", "Blender", "MediaPipe", "Streamlit"],
            "domain_knowledge": ["3D Modeling", "Machine Learning", "Data Structures", "Physics", "Robotics"]
        },
        "experience_level": "Fresher / 0-1 Years / Student",
        "portfolio_urls": {
            "github": "https://github.com/kishore",
            "linkedin": "https://linkedin.com/in/kishore",
            "portfolio": "https://kishore.dev"
        },
        "preferred_platforms_and_locations": {
            "preferred_locations": ["India", "Remote", "Hybrid"],
            "excluded_keywords": ["Unpaid (unless high value)", "Senior", "Lead", "5+ years experience"]
        }
    }
}


def load_candidate_profile() -> Dict[str, Any]:
    """Load candidate profile from candidate_profile.json or return default profile."""
    if PROFILE_PATH.exists():
        try:
            with open(PROFILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "candidate_profile" in data:
                    return data
        except Exception as e:
            print(f"Error reading {PROFILE_PATH}: {e}")
    
    # Save default if not present or invalid
    save_candidate_profile(DEFAULT_PROFILE)
    return DEFAULT_PROFILE


def save_candidate_profile(profile_data: Dict[str, Any]) -> bool:
    """Save candidate profile payload to JSON file."""
    try:
        with open(PROFILE_PATH, "w", encoding="utf-8") as f:
            json.dump(profile_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error writing candidate profile: {e}")
        return False


def get_all_skills_list(profile_data: Dict[str, Any]) -> list[str]:
    """Flatten all core skills into a single list of strings."""
    spec = profile_data.get("candidate_profile", {})
    skills_dict = spec.get("core_skills", {})
    flat_skills = []
    for cat, skills in skills_dict.items():
        if isinstance(skills, list):
            flat_skills.extend(skills)
        elif isinstance(skills, str):
            flat_skills.append(skills)
    return list(dict.fromkeys(flat_skills))
