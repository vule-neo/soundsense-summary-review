# SoundSense — Call Summary Review

QA tool for checking AI-generated collections-call summaries against their transcripts and the summary rules.

## Data

`soundsense-exercise-data/` — 20 synthetic transcript–summary pairs, the summary-generation rules, and the review brief.

## Development

```bash
npm install
npm run dev     # http://localhost:3000
npm run lint
npm run build
```

Secrets live in `.env` (git-ignored). Never commit API keys.

## Deployment

Deployed on Vercel; pushes to `main` deploy to production.
