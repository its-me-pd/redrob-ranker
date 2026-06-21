#!/usr/bin/env python3
"""
scoring.py v4 — Full-spec implementation.
Aligned with submission_spec (NDCG@10=50%), JD explicit disqualifiers,
redrob_signals_doc (all 23 signals), honeypot spec section 7.
"""

import re
from datetime import date
from config import (
    TIER1_NORMALIZED, TIER2_NORMALIZED, TITLE_MODIFIERS,
    HONEYPOT_TITLES, SERVICE_COMPANIES,
    JD_CONCEPT_FAMILIES, JD_CORE_SKILLS,
    WEAK_TRAP_TERMS, WRONG_DOMAIN_TERMS,
    PREFERRED_CITIES, ACCEPTABLE_CITIES, INDIA_IDENTIFIERS,
    SALARY_OFFER_LPA, SALARY_MAX_FIT, SALARY_MIN_FIT, W,
)

TODAY = date(2026, 6, 15)


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


def _career_text(candidate: dict) -> str:
    parts = []
    for job in candidate.get("career_history", []):
        parts.append(job.get("title", ""))
        parts.append(job.get("description", ""))
    return " ".join(parts).lower()


def _word_match(text: str, term: str) -> bool:
    return bool(re.search(r"\b" + re.escape(term) + r"\b", text))


def _career_families(career_text: str) -> tuple:
    hits = []
    for family, terms in JD_CONCEPT_FAMILIES.items():
        if any(_word_match(career_text, t) for t in terms):
            hits.append(family)
    return len(hits), hits


def _skill_depth(candidate: dict) -> tuple:
    score = 0.0
    expert_count = 0
    for sk in candidate.get("skills", []):
        name = sk.get("name", "").lower().strip()
        is_jd = any(jd in name or name in jd for jd in JD_CORE_SKILLS)
        if not is_jd:
            continue
        prof = sk.get("proficiency", "").lower()
        dur = min(sk.get("duration_months", 0) or 0, W["skill_dur_cap"])
        if prof == "expert":
            score += W["skill_expert"] + dur * W["skill_dur_bonus"]
            expert_count += 1
        elif prof == "advanced":
            score += W["skill_advanced"] + dur * W["skill_dur_bonus"] * 0.5
        elif prof == "intermediate":
            score += W["skill_intermediate"]
    return score, expert_count


def _is_all_service(candidate: dict) -> bool:
    career = candidate.get("career_history", [])
    if not career:
        return False
    return all(
        any(s in job.get("company", "").lower() for s in SERVICE_COMPANIES)
        for job in career
    )


def _has_product_company(candidate: dict) -> bool:
    for job in candidate.get("career_history", []):
        co = job.get("company", "").lower()
        if not any(s in co for s in SERVICE_COMPANIES):
            return True
    return False


def _career_progression(candidate: dict) -> float:
    career = candidate.get("career_history", [])
    if len(career) < 2:
        return 0.0
    try:
        sorted_c = sorted(career, key=lambda j: j.get("start_date", ""))
    except Exception:
        return 0.0
    def tier(title):
        n = normalize_title(title)
        if n in TIER1_NORMALIZED or any(t in n for t in TIER1_NORMALIZED):
            return 2
        if n in TIER2_NORMALIZED or any(t in n for t in TIER2_NORMALIZED):
            return 1
        return 0
    tiers = [tier(j.get("title", "")) for j in sorted_c]
    if tiers[-1] > tiers[0]:
        return W["career_progression"]
    return 0.0


def _title_chaser(candidate: dict) -> float:
    career = candidate.get("career_history", [])
    if len(career) < 3:
        return 0.0
    short_stints = sum(1 for j in career if (j.get("duration_months") or 0) < 14)
    if short_stints >= len(career) - 1:
        return W["title_chaser"]
    return 0.0


def _description_richness(candidate: dict) -> float:
    total = sum(len(j.get("description", "")) for j in candidate.get("career_history", []))
    if total > 1500:
        return W["desc_richness"]
    if total > 700:
        return W["desc_richness"] * 0.5
    return 0.0


def _education_bonus(candidate: dict) -> float:
    best = 0.0
    for edu in candidate.get("education", []):
        tier = edu.get("tier", "").lower()
        if tier == "tier_1":
            best = max(best, W["edu_tier1"])
        elif tier == "tier_2":
            best = max(best, W["edu_tier2"])
    return best


def _honeypot_profile(candidate: dict) -> bool:
    """Spec section 7: expert skill with 0 duration = impossible profile."""
    yoe = candidate.get("profile", {}).get("years_of_experience", 0)
    for sk in candidate.get("skills", []):
        if sk.get("proficiency", "").lower() == "expert":
            if (sk.get("duration_months") or 0) == 0:
                return True
        dur = sk.get("duration_months") or 0
        if dur > (yoe * 12) + 6:
            return True
    return False


def _location_score(candidate: dict) -> float:
    profile = candidate.get("profile", {})
    signals = candidate.get("redrob_signals", {})
    location = profile.get("location", "").lower()
    country = profile.get("country", "").lower().strip()
    willing = signals.get("willing_to_relocate", False)
    work_mode = signals.get("preferred_work_mode", "").lower()

    if "remote" in work_mode:
        return 0.0

    is_india = country in INDIA_IDENTIFIERS or "india" in location
    if not is_india and not willing:
        return W["loc_penalty"]

    if any(c in location for c in PREFERRED_CITIES):
        return W["loc_preferred"]
    if any(c in location for c in ACCEPTABLE_CITIES):
        return W["loc_acceptable"]
    return 0.0


def _salary_fit(candidate: dict) -> float:
    sal = candidate.get("redrob_signals", {}).get("expected_salary_range_inr_lpa", {})
    if not sal:
        return 0.0
    sal_min = sal.get("min", 0) or 0
    sal_max = sal.get("max", 0) or 0
    midpoint = (sal_min + sal_max) / 2 if sal_max > 0 else sal_min
    if midpoint == 0:
        return 0.0
    if midpoint > SALARY_MAX_FIT:
        excess = min((midpoint - SALARY_MAX_FIT) / 20, 1.0)
        return -(excess * W["high_salary"])
    if midpoint < SALARY_MIN_FIT:
        return -3.0
    return 0.0


def _behavioral_score(candidate: dict) -> tuple:
    signals = candidate.get("redrob_signals", {})
    score = 0.0
    bd = {}

    days_inactive = _days_since(signals.get("last_active_date", "2020-01-01"))
    if days_inactive <= 30:
        score += W["recency_30d"]; bd["recency"] = W["recency_30d"]
    elif days_inactive <= 90:
        score += W["recency_90d"]; bd["recency"] = W["recency_90d"]

    rr = signals.get("recruiter_response_rate", 0)
    rr_pts = rr * W["rr_weight"]
    score += rr_pts; bd["rr"] = round(rr_pts, 2)

    icr = signals.get("interview_completion_rate", 0)
    score += icr * W["icr_weight"]; bd["icr"] = round(icr * W["icr_weight"], 2)

    if signals.get("open_to_work_flag", False):
        score += W["open_to_work"]; bd["otw"] = W["open_to_work"]

    if signals.get("willing_to_relocate", False):
        score += W["willing_relocate"]; bd["relocate"] = W["willing_relocate"]

    notice = signals.get("notice_period_days", 90)
    if notice <= 30:
        score += W["notice_30d"]; bd["notice"] = W["notice_30d"]
    elif notice <= 60:
        score += W["notice_60d"]; bd["notice"] = W["notice_60d"]
    elif notice > 90:
        score += W["notice_90plus"]; bd["notice"] = W["notice_90plus"]

    art = signals.get("avg_response_time_hours", 9999)
    if 0 < art < 24:
        score += W["fast_response"]; bd["fast_response"] = W["fast_response"]

    oar = signals.get("offer_acceptance_rate", -1)
    if oar >= 0.7:
        score += W["offer_accept_high"]; bd["offer_accept"] = W["offer_accept_high"]

    if signals.get("applications_submitted_30d", 0) > 0:
        score += W["active_applications"]; bd["apps"] = W["active_applications"]

    if signals.get("verified_email", False) and signals.get("verified_phone", False):
        score += W["verified_contact"]; bd["verified"] = W["verified_contact"]

    if signals.get("linkedin_connected", False):
        score += W["linkedin_connected"]; bd["linkedin"] = W["linkedin_connected"]

    if signals.get("endorsements_received", 0) >= 50:
        score += W["endorsements_bonus"]; bd["endorsements"] = W["endorsements_bonus"]

    saved = min(signals.get("saved_by_recruiters_30d", 0), W["saved_cap"])
    score += saved * W["saved_recruiter"]; bd["saved"] = round(saved * W["saved_recruiter"], 2)

    gh = signals.get("github_activity_score", -1)
    score += max(gh, 0) * W["github_per_pt"]; bd["github"] = round(max(gh, 0) * W["github_per_pt"], 2)

    assessments = signals.get("skill_assessment_scores", {})
    if assessments:
        avg_a = sum(assessments.values()) / len(assessments)
        a_pts = (avg_a / 100) * W["assessment_avg"]
        score += a_pts; bd["assessments"] = round(a_pts, 2)

    return score, bd


def score_candidate(candidate: dict) -> tuple:
    """Returns (raw_score, breakdown). Negative = disqualified."""
    profile = candidate.get("profile", {})
    signals = candidate.get("redrob_signals", {})
    raw_title = profile.get("current_title", "").lower().strip()
    norm_title = normalize_title(raw_title)
    yoe = profile.get("years_of_experience", 0)
    bd = {}

    # Gate 1: Honeypot title
    if any(ht in raw_title for ht in HONEYPOT_TITLES):
        return -999.0, {"gate": "honeypot_title"}

    # Gate 2: Honeypot profile (spec section 7)
    if _honeypot_profile(candidate):
        return -998.0, {"gate": "honeypot_profile"}

    # Gate 3: Title must be in scope
    in_t1_exact   = norm_title in TIER1_NORMALIZED
    in_t1_partial  = not in_t1_exact and any(t in norm_title for t in TIER1_NORMALIZED)
    in_t2          = not (in_t1_exact or in_t1_partial) and (
        norm_title in TIER2_NORMALIZED or any(t in norm_title for t in TIER2_NORMALIZED)
    )
    if not (in_t1_exact or in_t1_partial or in_t2):
        return -1.0, {"gate": "irrelevant_title"}

    score = 0.0

    # 1. Title
    t_pts = W["tier1_exact"] if in_t1_exact else (W["tier1_partial"] if in_t1_partial else W["tier2"])
    score += t_pts; bd["title"] = t_pts

    # 2. Experience
    if 5 <= yoe <= 9:    e_pts = W["exp_peak"]
    elif 3 <= yoe < 5 or 9 < yoe <= 12: e_pts = W["exp_good"]
    elif yoe > 12:       e_pts = W["exp_overqual"]
    else:                e_pts = W["exp_junior"]
    score += e_pts; bd["experience"] = e_pts

    # 3. Career families
    ct = _career_text(candidate)
    n_fam, fam_hit = _career_families(ct)
    capped = min(n_fam, W["career_family_cap"])
    career_pts = capped * W["career_family"]
    if _is_all_service(candidate):
        career_pts = max(0.0, career_pts - W["service_only"])
    score += career_pts; bd["career_depth"] = round(career_pts, 2); bd["career_families"] = n_fam

    # 4. Skill depth
    sk_pts, expert_ct = _skill_depth(candidate)
    score += sk_pts; bd["skill_depth"] = round(sk_pts, 2); bd["expert_skills"] = expert_ct

    # 5. Stuffer penalty
    skill_text = " ".join(sk.get("name", "").lower() for sk in candidate.get("skills", []))
    skill_hits = sum(1 for terms in JD_CONCEPT_FAMILIES.values() for t in terms if t in skill_text)
    if skill_hits >= 5 and n_fam == 0:
        score -= W["stuffer_penalty"]; bd["stuffer_penalty"] = -W["stuffer_penalty"]

    # 6. Weak/trap terms
    full_text = ct + " " + skill_text + " " + profile.get("summary", "").lower()
    weak_pen = min(sum(1 for t in WEAK_TRAP_TERMS if t in full_text) * W["weak_term"], W["weak_term_cap"])
    score -= weak_pen; bd["weak_penalty"] = -round(weak_pen, 2)

    # 7. Wrong domain
    wrong_pen = min(sum(1 for t in WRONG_DOMAIN_TERMS if t in full_text) * W["wrong_domain"], W["wrong_domain_cap"])
    score -= wrong_pen
    if wrong_pen > 0: bd["wrong_domain"] = -round(wrong_pen, 2)

    # 8. Career bonuses
    score += _career_progression(candidate); bd["progression"] = _career_progression(candidate)
    score += _description_richness(candidate); bd["desc_richness"] = _description_richness(candidate)
    if _has_product_company(candidate):
        score += W["product_company_bonus"]; bd["product_co"] = W["product_company_bonus"]

    # 9. Title-chaser penalty
    tc = _title_chaser(candidate)
    if tc > 0: score -= tc; bd["title_chaser"] = -tc

    # 10. Education
    edu = _education_bonus(candidate)
    score += edu; bd["education"] = edu

    # 11. Behavioral (all 23 signals)
    beh_pts, beh_bd = _behavioral_score(candidate)
    score += beh_pts; bd.update(beh_bd)

    # 12. Location
    loc = _location_score(candidate)
    score += loc; bd["location"] = loc

    # 13. Salary fit
    sal = _salary_fit(candidate)
    if sal != 0: score += sal; bd["salary_fit"] = round(sal, 2)

    # 14. Hireability multiplier
    rr = signals.get("recruiter_response_rate", 0)
    otw = signals.get("open_to_work_flag", False)
    days_inactive = _days_since(signals.get("last_active_date", "2020-01-01"))
    if rr < 0.15 and not otw and days_inactive > 90:
        score *= W["unhireable_mult"]; bd["hireability_mult"] = W["unhireable_mult"]
    elif rr < 0.25 and days_inactive > 60:
        score *= W["low_avail_mult"]; bd["hireability_mult"] = W["low_avail_mult"]

    bd["raw_total"] = round(score, 4)
    return round(score, 4), bd
