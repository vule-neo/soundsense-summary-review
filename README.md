# SoundSense — Call Summary QA

Prototype tool for QA reviewers to check AI-generated collections-call summaries against their transcripts and the summary rules.

**Live:** https://soundsense-summary-review.vercel.app

## How it works

1. **Claude audit (offline)**: `scripts/analyze.py` sends each transcript, summary and the summary rules to Claude (`claude-sonnet-5-5`, medium effort) and saves a structured review to `analysis/<CALL-ID>.json`: per-claim verdicts with turn evidence, a fact sheet, and important omissions.
2. **Grounding (server)**: the FastAPI backend locates every claim and key value in the summary and verifies every quoted piece of evidence really occurs in the cited transcript turn.
3. **Rule checks (server)**: deterministic checks run independently of the AI (stated arrears/payment amounts, names, missing mandated phrases, unconfirmed "Payment made" / Authority to Act / consent, etc.).
4. **Review UI (Next.js/React)**: calls ordered by severity; summary claims colour-coded and clickable; amounts, dates and times jump to the transcript turn they came from.

## Layout

```
api/index.py               Vercel entrypoint for the FastAPI app
backend/                   FastAPI app, transcript parsing, rule checks, grounding, Claude analyzer
scripts/analyze.py         Batch Claude analysis → analysis/*.json
analysis/                  Saved analysis results (committed)
src/                       Next.js frontend
soundsense-exercise-data/  Dataset, summary rules and brief
```

## Development

```bash
# backend
python -m venv .venv
.venv/Scripts/pip install -r requirements-dev.txt     # (Windows; use .venv/bin on macOS/Linux)
.venv/Scripts/python -m uvicorn backend.app:app --port 8000

# frontend (proxies /api to :8000 in dev)
npm install
npm run dev     # http://localhost:3000
```

Re-run the AI review (needs `ANTHROPIC_API_KEY` in `.env`, which is git-ignored):

```bash
.venv/Scripts/python scripts/analyze.py CALL-003          # one call
.venv/Scripts/python scripts/analyze.py --all --force     # everything
```

## Deployment

Vercel, connected to GitHub: every push to `main` deploys. `/api/*` is served by the Python function; the rest by Next.js.
