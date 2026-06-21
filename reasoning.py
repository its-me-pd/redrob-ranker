#!/usr/bin/env python3
"""
reasoning.py v4 — Spec-compliant reasoning.

Stage 4 checks (from submission_spec.docx):
1. Specific facts (years, title, named skills, signal values)
2. JD connection (not generic praise)
3. Honest concerns (gaps acknowledged)
4. No hallucination (only claims from actual profile)
5. Variation (not templated)
6. Rank consistency (tone matches rank position)
"""

import re
from datetime import date
from config import TIER1_NORMALIZED, TITLE_MODIFIERS, JD_CONCEPT_FAMILIES

TODAY = date(2026, 6, 15)

TIER2_NORMALIZED = {"data scientist", "ml researcher", "ai specialist", "junior ml engineer"}


def _days_since(date_str) -> int:
    try:
        return (TODAY - date.fromisoformat(str(date_str))).days
    except Exception:
        return 9999


def normalize_title(title: str) -> str:
    t = title.lower().strip()
    t = re.sub(r"[,\-/.()&+]", " ", t)
    t = re.sub(r"\s+", " ", t)
    words = t.split()
    cleaned = [w for w in words if w not in TITLE_MODIFIERS]
    return " ".join(cleaned).strip()


def _career_families_hit(candidate: dict) -> list:
    parts = []
    for job in candidate.get("career_history", []):
        parts.append(job.get("title", ""))
        parts.append(job.get("description", ""))
    text = " ".join(parts).lower()

    labels = {
        "retrieval":      "information retrieval",
        "ranking":        "ranking/L2R",
        "recommendation": "recommendation systems",
        "semantic_search":"semantic/vector search",
        "embeddings":     "embeddings",
        "vector_db":      "vector DB (FAISS/Pinecone/ES)",
        "evaluation":     "NDCG/A-B eval frameworks",
        "models":         "BERT/fine-tuning",
        "scale":          "large-scale ML infra",
        "rag":            "RAG pipelines",
    }
    hits = []
    for family, terms in JD_CONCEPT_FAMILIES.items():
        for t in terms:
            if re.search(r"\b" + re.escape(t) + r"\b", text):
                hits.append(labels.get(family, family))
                break
    return hits[:3]


def _top_skills(candidate: dict) -> list:
    jd_skills = {
        "faiss", "pinecone", "weaviate", "elasticsearch", "opensearch",
        "milvus", "qdrant", "pgvector", "bert", "embeddings",
        "information retrieval", "semantic search", "learning to rank",
        "recommendation systems", "ndcg", "bm25", "rag", "nlp",
        "sentence transformers", "lora", "qlora",
    }
    expert_skills = []
    for sk in candidate.get("skills", []):
        name = sk.get("name", "").lower()
        prof = sk.get("proficiency", "").lower()
        if prof in ("expert", "advanced") and any(j in name or name in j for j in jd_skills):
            expert_skills.append(sk.get("name", ""))
    return expert_skills[:3]


def generate_reasoning(candidate: dict, breakdown: dict) -> str:
    profile = candidate.get("profile", {})
    signals = candidate.get("redrob_signals", {})

    title = profile.get("current_title", "Unknown")
    norm = normalize_title(title)
    yoe = profile.get("years_of_experience", 0)
    location = profile.get("location", "")
    country = profile.get("country", "")

    rr = signals.get("recruiter_response_rate", 0)
    saved = signals.get("saved_by_recruiters_30d", 0)
    otw = signals.get("open_to_work_flag", False)
    notice = signals.get("notice_period_days", 90)
    gh = signals.get("github_activity_score", -1)
    days_inactive = _days_since(signals.get("last_active_date", "2020-01-01"))
    icr = signals.get("interview_completion_rate", 0)
    art = signals.get("avg_response_time_hours", 9999)
    oar = signals.get("offer_acceptance_rate", -1)
    salary = signals.get("expected_salary_range_inr_lpa", {})

    career_fams = _career_families_hit(candidate)
    top_skills = _top_skills(candidate)
    raw_score = breakdown.get("raw_total", 0)

    parts = []

    # Sentence 1: Role alignment + career evidence (specific, no generic praise)
    if norm in TIER1_NORMALIZED:
        fit = "Direct profile match"
    elif any(t in norm for t in TIER1_NORMALIZED):
        fit = "Strong title match"
    elif norm in TIER2_NORMALIZED or any(t in norm for t in TIER2_NORMALIZED):
        fit = "Adjacent match"
    else:
        fit = "Partial match"

    career_str = ""
    if career_fams:
        career_str = f" with career evidence in {', '.join(career_fams)}"
    skill_str = ""
    if top_skills and not career_fams:
        skill_str = f"; listed skills include {', '.join(top_skills)}"

    loc_str = f"; based in {location}" if location else ""

    parts.append(f"{fit}: {title} ({yoe:.1f} yrs){career_str}{skill_str}{loc_str}.")

    # Sentence 2: Signals + honest concerns (rank-consistent tone)
    signals_list = []
    concerns_list = []

    if otw and notice <= 30:
        signals_list.append(f"immediately available ({notice}d notice)")
    elif otw:
        signals_list.append(f"open to work ({notice}d notice)")
    elif notice > 90:
        concerns_list.append(f"long notice period ({notice}d)")

    if days_inactive <= 14:
        signals_list.append(f"active {days_inactive}d ago")
    elif days_inactive > 180:
        concerns_list.append(f"inactive {days_inactive}d")

    if rr >= 0.7:
        signals_list.append(f"{rr:.0%} recruiter response rate")
    elif rr < 0.2:
        concerns_list.append(f"low response rate ({rr:.0%})")

    if icr >= 0.8:
        signals_list.append(f"{icr:.0%} interview completion")

    if 0 < art < 12:
        signals_list.append(f"responds within {art:.0f}h")

    if oar >= 0.7:
        signals_list.append(f"{oar:.0%} offer acceptance")

    if saved >= 20:
        signals_list.append(f"saved by {saved} recruiters")

    if gh >= 70:
        signals_list.append(f"GitHub {gh:.0f}/100")

    # Salary concern
    if salary:
        sal_max = salary.get("max", 0) or 0
        if sal_max > 60:
            concerns_list.append(f"expects up to {sal_max:.0f} LPA (above offer range)")

    # Assemble sentence 2
    if signals_list or concerns_list:
        parts2 = []
        if signals_list:
            parts2.append("Signals: " + "; ".join(signals_list))
        if concerns_list:
            parts2.append("Concerns: " + "; ".join(concerns_list))
        parts.append(" ".join(parts2) + ".")

    return " ".join(parts)
