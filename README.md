# SoundSense — Call Summary QA

A prototype that helps a QA reviewer check, quickly and safely, whether an AI-written summary of a debt-collection call is accurate against the call transcript and the company's summary rules.

**Live app:** https://soundsense-summary-review.vercel.app  
**Repository:** https://github.com/vule-neo/soundsense-summary-review

> All 20 calls in this repo are synthetic (from the exercise pack). No real customer data is used.

---

## At a glance

| | |
|---|---|
| Calls reviewed | 20 transcript–summary pairs |
| Summary claims checked | 158, each linked to transcript evidence |
| Evidence quotes verified against the transcript | **467 / 467** |
| Claims shown green (fully proven) | 127 |
| Claims shown yellow (“Needs check”) | 14 |
| Claims shown as definite problems | 17, plus 9 independent rule-check findings |
| Calls with at least one critical or major problem | 15 of 20 (matches a manual review of all 20 calls) |
| Green claims removed by the “strict green” fix | **16 of 134 (12%)**, 4 of which were real errors (see [Fixes](#fixes-and-iterations)) |

Reproduce these numbers with `python scripts/report.py --compare 1eb8ae0`.

---

## How to use the app

```
┌──────────────┬─────────────────────────────────────────┬──────────────────────────┐
│ CALL QUEUE   │ REVIEW                                  │ TRANSCRIPT               │
│ most severe  │ Headline: the one thing to know         │ T01 Agent  …             │
│ first        │ Tally: 2 problems · 1 to check · 6 ✓    │ T02 Customer …           │
│              │ ┌ Summary (colour-coded, clickable) ┐  │ T08 Customer  ◀ jumps    │
│ CALL-018 4C  │ └───────────────────────────────────┘  │     here, quote in yellow│
│ CALL-003 4C… │ Problems in the summary                 │ …                        │
│ …            │ Needs a quick check                     │                          │
│ CALL-001 ✓   │ Missing from the summary                │                          │
│              │ Fact sheet · All claims                 │                          │
└──────────────┴─────────────────────────────────────────┴──────────────────────────┘
```

1. **Pick a call from the queue (left).** Calls are sorted with the most severe first. The badges count `C` critical, `M` major, `m` minor and `?` claims to check. **✓ OK** appears only when there is nothing to fix and nothing left to check.
2. **Read the headline.** One sentence naming the most important finding and the turns that prove it.
3. **Read the summary under review.** Each claim is highlighted by verdict:

   | Colour | Label | Meaning | Reviewer action |
   |---|---|---|---|
   | 🟢 green | **Verified** | Every detail is proven by quoted transcript turns and passed the automatic checks | Safe to skim |
   | 🟡 yellow (dashed) | **Needs check** | Probably right but not fully proven. The card says exactly what to check | Look at the cited turn |
   | 🔴 red | **Contradicted** | The transcript says something different | Correct the summary |
   | 🟠 orange | **Unsupported** | Nothing in the transcript backs it | Correct the summary |
   | 🟣 purple | **Rule breach** | The fact may be right, but the summary rules forbid how it is written | Correct the summary |

4. **Click to verify.**
   - Click any highlighted claim to see why it got its verdict, with evidence chips (`T08 "No, not the details."`).
   - Amounts, dates and times inside the summary (e.g. `£75`, `26 October`, `after 3 pm`) are boxed. **Click one to jump straight to the turn where it was said**, with the exact words highlighted.
   - Click any `T..` chip anywhere to jump to that turn. Only the transcript panel scrolls, so you keep your place.
5. **Work down the sections:**
   - **Problems in the summary**: definite errors from the AI review, plus **Rule check** cards from the independent code checks.
   - **Needs a quick check**: yellow claims, each with a “Not green because…” list.
   - **Important in the call, missing from the summary**: items the rules require that were discussed but left out, with the wording that should have been used.
   - **Fact sheet**: 14 rule-driven items (call direction, DPA, Authority to Act, consent, I&E, risk of further action, promises, etc.) showing *transcript says* vs *summary says*. Click a row to see its evidence.
   - **All claims**: the full claim-by-claim breakdown.

A chip with a red ⚠ means the AI's quote could not be found in that turn. Don't rely on it. So far all 467 quotes have verified.

**Good calls to try:** CALL-018 (Authority to Act said verified, actually refused), CALL-002 (£150 promise, actually £100), CALL-003 (consent the customer refused), CALL-017 (30-day hold, actually 14-day), CALL-020 (an £80 "promise" the customer said not to record).

---

## What we prioritised, and why

The goal is that a busy QA reviewer **cannot easily miss a costly mistake** and **never has to take the AI's word for anything**.

1. **Every claim must be backed by the transcript.** The AI must cite turn IDs with verbatim quotes for every claim, fact and omission. The server then checks each quote really occurs in the cited turn. Unverifiable evidence is flagged, never hidden.
2. **One click from a number to its source.** Amounts, dates and times are where the costliest errors hide (£150 vs £100, 30 vs 14 days). They're clickable and jump to the exact turn.
3. **Green must be earned (“strict green”).** A hurried reviewer will skip green claims, so green means *100% proven*. Any doubt makes the claim yellow, with the reason shown.
4. **Show what's missing, not just what's wrong.** About half the real problems in this dataset are omissions (risk-of-further-action warnings, I&E refusals, severe hardship, mandatory phrases), which you can't spot by reading the summary alone. The "missing" section and the fact sheet make them visible.
5. **Two independent signals.** Plain-code rule checks run alongside the AI, so a mechanical breach is caught even if the AI misses it.
6. **Severity first.** The queue and every list are sorted critical → major → minor, so the worst calls and issues come first.
7. **Keep the prototype simple.** No logins, users or database. The AI review is computed in advance and saved as JSON, so the app opens instantly and costs nothing to view.

### Severity scale

- **Critical**: could cause compliance harm or financial loss if trusted: wrong or invented payment amounts or dates, "Payment made" when nothing was paid, consent or Authority to Act misstated, missing risk-of-further-action warning or I&E refusal, severe hardship dropped.
- **Major**: a material fact wrong or a mandatory element missing: wrong call direction, wrong hold length, invented events, missing "customer signposted", missing specific cause, privacy breach, arrears or payment amounts stated.
- **Minor**: small imprecision unlikely to mislead.

---

## How a summary is checked

```
transcript + summary + summary rules
        │
        ▼
1. Claude review (offline, scripts/analyze.py)
   claim-by-claim verdicts · fact sheet · omissions · turn IDs + verbatim quotes
        │
        ▼
2. Grounding (backend/verify.py)
   locate each claim and value in the summary · verify every quote is in its cited turn
        │
        ▼
3. Strict-green gate (backend/strict.py)
   AI "supported" is kept only if: evidence exists and is verified · every £ amount, date
   and time in the claim appears in the cited turns (spoken forms understood, e.g.
   "seventeen hundred and sixty", "twenty-third", "Friday") · no time window narrowed
   ("after two" ≠ "at 2 pm") · no rule check flags the text. Otherwise → "Needs check".
        │
        ▼
4. Independent rule checks (backend/checks.py), no AI
   arrears/balance amounts · amount of payment taken · names · phone numbers · US spelling
   · placeholders ("N/A") · bullets/length · missing DPA status · missing "risk of further
   action" when the agent warned · missing "customer signposted" when the website was
   mentioned · "Payment made" with no successful payment · default notice never discussed
   · Authority to Act claimed but not confirmed · consent claimed but refused
        │
        ▼
5. Review UI (Next.js)
```

---

## Results on the 20 calls

| Call | What the app shows |
|---|---|
| CALL-001 | No errors; one minor wording issue ("confirmed understanding" when the customer asked for the confirmation) |
| CALL-002 | **Critical**: promise recorded as £150, final agreed amount £100 (T14–T16) |
| CALL-003 | **Critical**: "Consent gained" but the customer refused (T10). Arrears amount stated; "no money for food" dropped |
| CALL-004 | Accurate; one claim to check (the £60 surplus was the customer's own estimate) |
| CALL-005 | Accurate; one claim to check ("checked understanding") |
| CALL-006 | Accurate; two claims to check |
| CALL-007 | Accurate; one claim to check ("checked understanding") |
| CALL-008 | **Major**: invents a default notice. Only an arrears letter was mentioned (T06) |
| CALL-009 | **Critical**: says I&E refused, but it was postponed and booked (T12–T15) |
| CALL-010 | **Major**: omits the specific cause (husband cancelled the Direct Debit during the divorce) |
| CALL-011 | **Major**: missing "customer signposted" (website support page, T15) |
| CALL-012 | **Critical**: Authority to Act called "ongoing", but it was for this call only (T08–T09) |
| CALL-013 | **Critical**: "Payment made", but no payment was taken (T22–T23) |
| CALL-014 | **Major**: employer name not redacted. "no DPA stated with agent" correctly accepted |
| CALL-015 | **Critical**: risk of further action warning omitted (T13, T15) |
| CALL-016 | **Major**: amount of payment taken (£230) stated |
| CALL-017 | **Critical**: 30-day hold, actually 14-day (T13, T19). Bereavement and frozen account omitted |
| CALL-018 | **Critical**: Authority to Act "verified", but the customer refused it (T08, T10, T22). I&E refusal omitted |
| CALL-019 | **Critical/major**: wrong call direction (outbound, T01). Consent phrase missing. "at 2 pm" vs "after two" |
| CALL-020 | **Critical**: records an £80 promise the customer said not to record (T16–T17). Risk-of-further-action warning omitted |

Before building the app we reviewed all 20 calls by hand. The app flags every problem from that manual review, on the same 15 calls. It also raises a few extra points: CALL-020's missing £210 childcare cost, which the Situational Costs rule requires, plus smaller wording points in CALL-001 and CALL-015 that a reviewer should judge.

---

## Fixes and iterations

| Commit | Change | Why |
|---|---|---|
| `1f35e1b` | Next.js 16.4.6 instead of the scaffold's 15.5.4 | The scaffold version had critical security advisories |
| `36a3df9` | Analysis model switched from Claude Opus 5.5 (high effort) to **Claude Sonnet 5.5 (medium effort)** | Lower cost while testing. Tested on CALL-018, Sonnet found the same issues with about 1/3 fewer output tokens |
| `df9c55a` | Name detection in rule checks tightened | The first version flagged words like "The", "Debit", "September" as personal names |
| `6841718` | **Evidence chips jumped to the wrong turn** | Clicking `T22` inside a claim card also triggered the card, which re-focused the claim's first turn (`T08`). Fixed, and only the transcript panel scrolls now |
| `3ad897d` `a02fc15` `5da8ebd` | **Strict green** | See below |

### The strict-green fix

**Problem.** In the first version, 134 of 149 claims were green. A reviewer in a hurry skips green claims, so any green claim that wasn't fully proven could let a wrong summary through.

**Fix.**
- **Stricter standard for the AI.** Green only when every element (amounts, dates, times, who did what, "checked understanding") is explicitly in the transcript; any doubt → "Needs check".
- **A code check that re-verifies every green claim.** Evidence verified, amounts, dates and times present in the cited turns, time windows not narrowed, no rule-check hit.
- **UI.** Green relabelled "Verified", yellow "Needs check" with the reasons, its own section, and a `?` count in the queue.

**Result:** **16 of the 134 previously green claims (12%) are no longer green.**
- **12** are now yellow. Mostly "agent checked understanding" where the customer actually did the recap, an I&E surplus that was only the customer's estimate, and "at 2 pm" where the call said "after two".
- **4** are now marked as definite problems. These were real errors hidden under green:
  - CALL-003: "no money for food" hardship dropped (critical);
  - CALL-019: mandatory "Consent gained to record vulnerability" phrase missing (critical);
  - CALL-020: £210 childcare cost omitted, which the Situational Costs rule requires (major);
  - CALL-001: "agent confirmed understanding" when the customer asked (minor).

In the first run the code check on its own caught 1 of these: CALL-019's "at 2 pm". It's a safety net in case the AI marks something green it shouldn't.

---

## Assumptions

- **Summary rules:** `summary-rules.txt` is the standard. Where the exercise readme adds clarifications, we follow them:
  - "no DPA stated with agent" is correct when name + DOB + address isn't fully verified;
  - named advice bodies (StepChange, Citizens Advice, MoneyHelper) are kept;
  - employers, garages and other private businesses must be redacted.
- **Omissions:** a category that wasn't discussed is correctly absent. An omission is flagged only when the item was discussed *and* the rules require it.
- **Final position counts:** when a customer revises (offers £150, then corrects to £100), the summary is judged against the final agreed position.
- **Relative dates:** resolved from the call date (Tue 20 Oct 2026): "Friday" = 23 Oct, "tomorrow" = 21 Oct.
- **Transcription noise:** out-of-context text during hold music (CALL-003 T15, "Thank you for watching") is treated as a transcription error. It's shown struck through and never used as evidence.
- **Reviewers only judge, never edit:** the app doesn't change summaries. It shows what's wrong and suggests compliant wording for omissions.
- **One verdict per claim:** the summary is split into claims at clause level, so different parts of one sentence can get different verdicts.

## Known limitations

- **AI output varies between runs.** Re-running can split claims differently or move a borderline claim between green and yellow. The strict gate and rule checks reduce the risk, and every finding links to evidence so a reviewer can confirm it.
- **The deployed app shows saved results.** The API key isn't on Vercel, so the live site can't re-analyse new calls yet. Analysis runs locally with `scripts/analyze.py`.
- **Reviewer decisions aren't saved** (no database, by design for this prototype).
- **Rule checks use pattern matching.** They are tuned to this dataset's wording, and there may be phrasings they don't recognise.
- **The benchmark is one person's review,** not a labelled gold standard.

---

## Run it locally and check the results

Requirements: Python 3.10+, Node 20+.

```bash
# 1. Backend (FastAPI on :8000)
python -m venv .venv
.venv/Scripts/pip install -r requirements-dev.txt        # macOS/Linux: .venv/bin/pip
.venv/Scripts/python -m uvicorn backend.app:app --port 8000

# 2. Frontend (Next.js on :3000, proxies /api to :8000)
npm install
npm run dev
# open http://localhost:3000
```

**Check the results and numbers**

```bash
.venv/Scripts/python scripts/report.py                     # per-call counts and totals
.venv/Scripts/python scripts/report.py --compare 1eb8ae0   # before/after strict green
```

The API docs are at `/api/docs` (e.g. https://soundsense-summary-review.vercel.app/api/docs). `GET /api/calls` lists calls with severity counts. `GET /api/calls/{id}` returns the call with turns, analysis, verified evidence and rule checks.

**Re-run the AI review** (needs `ANTHROPIC_API_KEY` in a local `.env` file, which git ignores):

```bash
.venv/Scripts/python scripts/analyze.py CALL-003           # one call
.venv/Scripts/python scripts/analyze.py --all --force      # all 20 (≈1 minute, well under $1 on Sonnet 5.5)
```

**Quality checks:** `npm run lint`, `npx tsc --noEmit`, `npm run build`.

## Project structure

```
api/index.py               Vercel entrypoint for the FastAPI app
backend/
  app.py                   API: /api/calls, /api/calls/{id}
  calls.py                 Load dataset, split transcripts into turns, speaker roles
  analyzer.py              Claude prompt + structured-output call
  schema.py                Output schema (claims, fact sheet, omissions, evidence)
  verify.py                Locate claims/values in the summary, verify quotes
  strict.py                Strict-green gate (amounts, dates, times, evidence)
  checks.py                Independent rule checks (no AI)
scripts/analyze.py         Run the Claude review → analysis/*.json
scripts/report.py          Statistics quoted in this README
analysis/                  Saved Claude review per call (committed)
src/                       Next.js + React UI (app/page.tsx, components/)
soundsense-exercise-data/  Dataset, summary rules and exercise brief
```

## Tech

FastAPI (Python) · Next.js 16 / React 19 / Tailwind · Claude Sonnet 5.5 via the Anthropic SDK with structured outputs · Vercel (pushes to `main` deploy automatically).
