# Redrob Hackathon — Intelligent Candidate Ranking

Rule-based ML candidate ranker for the India Runs Data & AI Challenge.

## Files to submit

| File | Purpose |
|------|---------|
| `submission.csv` | **The actual submission** — 100 ranked candidates |
| `rank.py` | Main entry point — run this to regenerate submission |
| `scoring.py` | Core scoring logic (v3) |
| `config.py` | All weights and term lists |
| `reasoning.py` | Reasoning column generator |
| `validate_and_test.py` | Local test suite |

## How to run

```bash
pip install -r requirements.txt
python rank.py
```

Output: `submission.csv`

## Verify before submitting

```bash
python validate_submission.py submission.csv
python validate_and_test.py
```

Both must pass.

## Architecture

**5 scoring components, in priority order:**

1. **Title gate** — honeypots hard-blocked; titles normalized to strip seniority modifiers (handles Principal/Staff/Lead variants)
2. **Career concept families** — 10 JD concept families (retrieval, ranking, recommendation, embeddings, vector DB, evaluation, fine-tuning, scale, RAG) — each family scores once, preventing keyword inflation
3. **Skill depth** — proficiency × duration weighting for JD-relevant skills
4. **Behavioral availability** — recruiter response rate (highest weight), platform recency, notice period
5. **Platform engagement** — recruiter saves, GitHub score, assessment scores

**Key protections:**
- Stuffer penalty: 5+ JD skill keywords + 0 career evidence = penalized
- Anomaly detection: impossible skill durations vs years of experience
- Career progression bonus: upward title trajectory rewarded
- Hireability multiplier: near-zero availability candidates scored down regardless of qualifications
