# ============================================================
# config.py v4 — Built from full spec + JD + signals doc
# Scoring optimised for NDCG@10 (50% weight) > NDCG@50 (30%)
# ============================================================

# --------------- TITLE TIERS ---------------
TIER1_NORMALIZED = {
    "ai engineer", "machine learning engineer", "ml engineer",
    "nlp engineer", "applied scientist", "applied ml engineer",
    "ai research engineer", "recommendation systems engineer",
    "search engineer", "staff machine learning engineer",
    "computer vision engineer", "ml research engineer",
    "research scientist",
}

# Seniority/level modifiers that don't change the base role
TITLE_MODIFIERS = {
    "senior", "sr", "lead", "principal", "staff", "head of", "head",
    "associate", "jr", "junior", "ii", "iii", "iv", "i",
    "founding", "chief", "distinguished", "fellow", "executive",
}

# Tier 2: adjacent but relevant
TIER2_NORMALIZED = {
    "data scientist",
    "ml researcher",
    "ai specialist",
    "junior ml engineer",
}

# Hard disqualifiers — never rank these
HONEYPOT_TITLES = {
    "business analyst", "hr manager", "human resources",
    "mechanical engineer", "accountant", "project manager",
    "customer support", "operations manager", "content writer",
    "sales executive", "civil engineer", "graphic designer",
    "marketing manager", "product manager", "financial analyst",
    "lawyer", "teacher", "professor", "doctor", "nurse",
    "backend engineer", "frontend engineer", "full stack engineer",
    "fullstack engineer", "devops engineer",
}

# Service companies (JD explicitly names these)
SERVICE_COMPANIES = {
    "tcs", "tata consultancy", "infosys", "wipro", "accenture",
    "cognizant", "capgemini", "mindtree", "hexaware", "mphasis",
    "tech mahindra", "hcl", "l&t infotech", "ltimindtree",
}

# --------------- JD CONCEPT FAMILIES ---------------
# Grouped so one description can't inflate by repeating synonyms.
# Each family = max 1 career hit.
JD_CONCEPT_FAMILIES = {
    "retrieval":       ["retrieval", "information retrieval", "dense retrieval",
                        "hybrid retrieval", "candidate retrieval"],
    "ranking":         ["ranking", "learning to rank", "lambdamart",
                        "candidate ranking", "ranking layer", "ranking systems",
                        "relevance ranking", "reranking", "re-ranking",
                        "cross encoder", "cross-encoder"],
    "recommendation":  ["recommendation", "recommendation systems",
                        "job matching", "candidate matching", "matching pipeline"],
    "semantic_search": ["semantic search", "vector search", "hybrid search",
                        "search backend", "search relevance"],
    "embeddings":      ["embedding", "embeddings", "sentence-transformers",
                        "sentence transformers", "vector representations",
                        "dense embeddings", "bi-encoder"],
    "vector_db":       ["faiss", "pinecone", "weaviate", "milvus", "qdrant",
                        "pgvector", "opensearch", "elasticsearch", "bm25"],
    "evaluation":      ["ndcg", "mrr", "map", "a/b test", "a/b testing",
                        "ab test", "offline evaluation", "ranking quality",
                        "relevance evaluation", "eval framework",
                        "embedding drift", "index refresh"],
    "models":          ["bert", "transformers", "fine-tuning", "fine tuning",
                        "lora", "qlora", "peft", "xgboost", "lightgbm",
                        "learning-to-rank", "neural ranker"],
    "scale":           ["query latency", "at scale", "million queries",
                        "large scale", "production ml", "inference optimization",
                        "distributed", "high throughput"],
    "rag":             ["rag", "retrieval augmented", "retrieval-augmented"],
}

# JD-relevant skill names for skill depth scoring
JD_CORE_SKILLS = {
    "information retrieval", "semantic search", "vector search", "dense retrieval",
    "embeddings", "sentence transformers", "recommendation systems", "learning to rank",
    "faiss", "pinecone", "weaviate", "milvus", "qdrant", "elasticsearch", "opensearch",
    "pgvector", "bm25", "hybrid search", "bert", "transformers", "fine-tuning",
    "fine tuning", "lora", "qlora", "ndcg", "mrr", "ranking", "retrieval",
    "reranking", "cross encoder", "rag", "llm", "nlp", "xgboost", "lightgbm",
    "search", "search relevance", "bi-encoder",
}

# Terms that signal GenAI tourist, not production ML (JD explicitly warns about these)
WEAK_TRAP_TERMS = [
    "langchain", "llamaindex", "haystack",
    "prompt engineering", "chatgpt", "openai api",
    "ai enthusiast", "genai", "ai tools", "openai",
]

# JD explicitly says CV/speech/robotics = wrong background
WRONG_DOMAIN_TERMS = [
    "computer vision", "image classification", "object detection",
    "speech recognition", "automatic speech recognition", "asr",
    "robotics", "autonomous vehicles", "self-driving",
]

# --------------- LOCATION ---------------
PREFERRED_CITIES = ["pune", "noida"]
ACCEPTABLE_CITIES = [
    "hyderabad", "mumbai", "delhi", "ncr", "bangalore",
    "bengaluru", "gurugram", "gurgaon",
]
INDIA_IDENTIFIERS = ["india", "in"]

# --------------- SALARY FIT ---------------
# JD: 36 LPA + 1L/month stipend ≈ 48 LPA total comp
# Candidates expecting much more are unlikely to accept
# Candidates expecting much less are probably too junior
SALARY_OFFER_LPA = 36
SALARY_MAX_FIT = 55      # above this = overpriced, score starts dropping
SALARY_MIN_FIT = 18      # below this = probably too junior for the role

# --------------- SCORING WEIGHTS v4 ---------------
# Tuned for NDCG@10 (50%) — top 10 matter most.
# Be decisive at the top; don't let marginal signals swap rank 1 and rank 2.
W = {
    # Title (most decisive signal)
    "tier1_exact":          42,
    "tier1_partial":        30,   # modifier-only variant
    "tier2":                14,
    "tier3":                 5,

    # Experience (JD: 5-9 yrs ideal, explicit)
    "exp_peak":             20,   # 5-9 yrs
    "exp_good":             12,   # 3-5 or 9-12 yrs
    "exp_overqual":          5,   # >12 yrs (JD says still fine)
    "exp_junior":            2,   # <3 yrs

    # Career concept families (up to 10 families, each scores once)
    "career_family":         8,   # per family
    "career_family_cap":    10,

    # Skill depth
    "skill_expert":          4,
    "skill_advanced":        2,
    "skill_intermediate":    1,
    "skill_dur_bonus":       0.02,
    "skill_dur_cap":        60,

    # JD extras
    "career_progression":    8,   # upward title trajectory
    "desc_richness":         5,   # detailed descriptions = real work
    "product_company_bonus": 6,   # ever worked at non-service product company

    # Education bonus (JD doesn't emphasise but IIT/IISc = strong signal)
    "edu_tier1":             6,   # IIT, IISc, BITS
    "edu_tier2":             3,   # NIT, IIIT, top private

    # Penalties
    "stuffer_penalty":      15,
    "weak_term":             2,   # per term, capped
    "weak_term_cap":        10,
    "wrong_domain":          5,   # per term, capped
    "wrong_domain_cap":     10,
    "service_only":         10,   # all career at service cos
    "title_chaser":          8,   # many short stints (<12 months each)
    "anomaly":              12,   # impossible profile
    "high_salary":           8,   # salary expectation >> offer

    # Behavioral signals (all 23 from signals doc)
    "rr_weight":            18,   # recruiter_response_rate × this
    "icr_weight":           10,   # interview_completion_rate × this
    "open_to_work":          6,
    "willing_relocate":      5,
    "recency_30d":          12,
    "recency_90d":           6,
    "notice_30d":            5,
    "notice_60d":            2,
    "notice_90plus":        -3,   # JD: "bar gets higher" for 90+ day notice
    "fast_response":         3,   # avg_response_time_hours < 24
    "offer_accept_high":     4,   # offer_acceptance_rate > 0.7
    "active_applications":   3,   # applications_submitted_30d > 0
    "verified_contact":      2,   # verified email + phone
    "linkedin_connected":    2,

    # Platform engagement
    "saved_recruiter":       0.4,
    "saved_cap":            80,
    "github_per_pt":         0.15,
    "assessment_avg":        8,
    "endorsements_bonus":    3,   # high endorsements = external validation

    # Location
    "loc_preferred":         5,   # Pune/Noida
    "loc_acceptable":        2,   # other Tier-1 cities
    "loc_penalty":         -10,   # outside India, no relocation

    # Hireability multiplier
    "unhireable_mult":      0.50,
    "low_avail_mult":       0.78,
}
