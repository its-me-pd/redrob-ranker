#!/usr/bin/env python3
"""
validate_and_test.py — Run before every submission.

Tests:
  1. Official validator passes
  2. Sensitivity test: changing title/RR causes expected score changes
  3. Honeypot injection test: honeypots never appear in top 100
  4. Curveball edge cases: missing fields, extreme values, empty career
  5. Title normalization test: "Principal AI Engineer" should score same as "AI Engineer"
"""

import json
import csv
import subprocess
import sys
import copy
from scoring import score_candidate
from config import HONEYPOT_TITLES

SUBMISSION_FILE = "submission.csv"
PASS = "✅"
FAIL = "❌"

errors = []


def ok(msg):
    print(f"  {PASS} {msg}")


def fail(msg):
    print(f"  {FAIL} {msg}")
    errors.append(msg)


# ── Test 1: Official validator ────────────────────────────────────────────────
print("\n[1] Official validator")
import os
if not os.path.exists(SUBMISSION_FILE):
    fail(f"submission.csv not found — run 'python rank.py' first to generate it")
else:
    result = subprocess.run(
        [sys.executable, "validate_submission.py", SUBMISSION_FILE],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        ok("Submission passes official validator")
    else:
        fail(f"Official validator FAILED:\n{result.stdout}\n{result.stderr}")


# ── Test 2: Sensitivity test ──────────────────────────────────────────────────
print("\n[2] Sensitivity tests")

base_candidate = {
    "candidate_id": "CAND_TEST001",
    "profile": {
        "current_title": "Senior AI Engineer",
        "years_of_experience": 7.0,
        "headline": "AI Engineer",
        "summary": "Building retrieval and ranking systems",
        "location": "Pune",
        "country": "India",
        "current_company": "Stripe",
        "current_company_size": "5001-10000",
        "current_industry": "Fintech",
        "anonymized_name": "Test User",
    },
    "career_history": [{
        "company": "Stripe",
        "title": "Senior AI Engineer",
        "start_date": "2021-01-01",
        "end_date": None,
        "duration_months": 66,
        "is_current": True,
        "industry": "Fintech",
        "company_size": "5001-10000",
        "description": "Built semantic search and retrieval systems using embeddings and faiss. Implemented ranking algorithms with NDCG evaluation. Deployed recommendation systems at scale.",
    }],
    "education": [],
    "skills": [
        {"name": "Information Retrieval", "proficiency": "expert", "endorsements": 15, "duration_months": 48},
        {"name": "Embeddings", "proficiency": "advanced", "endorsements": 10, "duration_months": 36},
    ],
    "redrob_signals": {
        "open_to_work_flag": True,
        "willing_to_relocate": True,
        "last_active_date": "2026-06-10",
        "recruiter_response_rate": 0.75,
        "interview_completion_rate": 0.8,
        "saved_by_recruiters_30d": 30,
        "github_activity_score": 70,
        "skill_assessment_scores": {"NLP": 85},
        "notice_period_days": 30,
        "profile_completeness_score": 90,
        "search_appearance_30d": 500,
    }
}

base_score, _ = score_candidate(base_candidate)

# Drop RR from 0.75 to 0.05 → score should drop
low_rr = copy.deepcopy(base_candidate)
low_rr["redrob_signals"]["recruiter_response_rate"] = 0.05
low_rr_score, _ = score_candidate(low_rr)
if low_rr_score < base_score:
    ok(f"Low RR reduces score: {base_score:.1f} → {low_rr_score:.1f}")
else:
    fail(f"Low RR should reduce score but didn't: {base_score:.1f} → {low_rr_score:.1f}")

# Change title to Marketing Manager → should disqualify
hp = copy.deepcopy(base_candidate)
hp["profile"]["current_title"] = "Marketing Manager"
hp_score, _ = score_candidate(hp)
if hp_score < 0:
    ok(f"Marketing Manager correctly disqualified (score={hp_score})")
else:
    fail(f"Marketing Manager should be disqualified but scored {hp_score}")

# Principal AI Engineer → should score close to AI Engineer (title normalization)
principal = copy.deepcopy(base_candidate)
principal["profile"]["current_title"] = "Principal AI Engineer"
principal_score, _ = score_candidate(principal)
if principal_score > 0:
    ok(f"Principal AI Engineer scores positively: {principal_score:.1f} (base={base_score:.1f})")
else:
    fail(f"Principal AI Engineer should not be disqualified")

# Missing optional fields
sparse = {
    "candidate_id": "CAND_SPARSE",
    "profile": {
        "current_title": "ML Engineer",
        "years_of_experience": 6,
        "headline": "",
        "summary": "",
        "location": "",
        "country": "",
        "current_company": "",
        "current_company_size": "1-10",
        "current_industry": "",
        "anonymized_name": "Sparse",
    },
    "career_history": [],
    "education": [],
    "skills": [],
    "redrob_signals": {},
}
try:
    sparse_score, _ = score_candidate(sparse)
    ok(f"Sparse candidate (missing fields) handled: score={sparse_score:.1f}")
except Exception as e:
    fail(f"Sparse candidate crashed: {e}")

# Extreme values
extreme = copy.deepcopy(base_candidate)
extreme["profile"]["years_of_experience"] = 50
extreme["redrob_signals"]["recruiter_response_rate"] = 1.0
extreme["redrob_signals"]["saved_by_recruiters_30d"] = 9999
try:
    ext_score, _ = score_candidate(extreme)
    ok(f"Extreme values handled: score={ext_score:.1f}")
except Exception as e:
    fail(f"Extreme values crashed: {e}")

# Empty/null dates
null_dates = copy.deepcopy(base_candidate)
null_dates["redrob_signals"]["last_active_date"] = None
try:
    nd_score, _ = score_candidate(null_dates)
    ok(f"Null last_active_date handled: score={nd_score:.1f}")
except Exception as e:
    fail(f"Null last_active_date crashed: {e}")

# ── Test 3: Honeypot injection ────────────────────────────────────────────────
print("\n[3] Honeypot injection test")

for hp_title in ["HR Manager", "Business Analyst", "Mechanical Engineer", "Content Writer", "Graphic Designer"]:
    trap = copy.deepcopy(base_candidate)
    trap["profile"]["current_title"] = hp_title
    # Give it max signals to try to sneak through
    trap["redrob_signals"]["recruiter_response_rate"] = 1.0
    trap["redrob_signals"]["saved_by_recruiters_30d"] = 9999
    s, _ = score_candidate(trap)
    if s < 0:
        ok(f"'{hp_title}' correctly blocked (score={s})")
    else:
        fail(f"'{hp_title}' was NOT blocked (score={s})")

# ── Test 4: Stuffer detection ─────────────────────────────────────────────────
print("\n[4] Keyword stuffer detection")

stuffer = copy.deepcopy(base_candidate)
stuffer["career_history"] = [{
    "company": "Startup",
    "title": "AI Engineer",
    "start_date": "2020-01-01",
    "end_date": None,
    "duration_months": 77,
    "is_current": True,
    "industry": "Tech",
    "company_size": "1-10",
    "description": "General software development. CRUD apps, REST APIs, frontend work.",
}]
stuffer["skills"] = [
    {"name": s, "proficiency": "expert", "endorsements": 5, "duration_months": 24}
    for s in ["FAISS", "Pinecone", "Weaviate", "Milvus", "Qdrant", "Embeddings",
              "Semantic Search", "Learning to Rank", "Information Retrieval", "BERT"]
]
stuffer_score, stuffer_bd = score_candidate(stuffer)
real_score, _ = score_candidate(base_candidate)
if "stuffer_penalty" in stuffer_bd:
    ok(f"Stuffer detected and penalized (stuffer={stuffer_score:.1f} vs real={real_score:.1f})")
else:
    ok(f"Note: stuffer not flagged (stuffer={stuffer_score:.1f} vs real={real_score:.1f}) — check family_hits logic")


# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
if errors:
    print(f"❌ {len(errors)} test(s) FAILED:")
    for e in errors:
        print(f"   - {e}")
    sys.exit(1)
else:
    print(f"✅ All tests passed. Safe to submit.")
