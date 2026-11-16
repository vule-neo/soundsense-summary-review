"""Deterministic rule checks that run independently of the AI review.

These are cheap, predictable pattern checks against the summary rules. They are a
second, independent signal: if the AI misses something mechanical (an arrears
amount, a missing mandated phrase) these still catch it.
"""
from __future__ import annotations

import re

US_SPELLINGS = {
    "authorized": "authorised",
    "authorize": "authorise",
    "center": "centre",
    "program": "programme",
    "color": "colour",
    "behavior": "behaviour",
    "organization": "organisation",
    "recognize": "recognise",
    "apologize": "apologise",
    "favor": "favour",
    "canceled": "cancelled",
    "license": "licence",
    "analyze": "analyse",
}

PLACEHOLDERS = ["N/A", "not discussed", "not completed", "not applicable"]

NOT_NAMES = {"Yes", "Yeah", "Hi", "Hello", "The", "That's", "It's", "Okay", "Right", "Sorry"}


def _span(summary: str, m: re.Match | None) -> dict:
    if m is None:
        return {"summary_text": "", "start": None, "end": None}
    return {"summary_text": m.group(0), "start": m.start(), "end": m.end()}


def _check(cid: str, title: str, detail: str, severity: str, turn_ids: list[str] | None = None, span: dict | None = None) -> dict:
    return {
        "id": cid,
        "title": title,
        "detail": detail,
        "severity": severity,
        "turn_ids": turn_ids or [],
        **(span or {"summary_text": "", "start": None, "end": None}),
    }


def _agent_turns(turns: list[dict], pattern: str) -> list[str]:
    rx = re.compile(pattern, re.I)
    return [t["id"] for t in turns if t["role"] == "agent" and rx.search(t["text"])]


def _person_names(turns: list[dict]) -> set[str]:
    """Collect customer / agent name tokens mentioned in the transcript."""
    names: set[str] = set()
    for i, t in enumerate(turns):
        text = t["text"]
        for m in re.finditer(r"speak to ([A-Z][a-z]+(?: [A-Z][a-z]+)+)", text):
            names.update(m.group(1).split())
        for m in re.finditer(r"(?:my name's|my name is|speaking with) ([A-Z][a-z]+)", text):
            names.add(m.group(1))
        # Customer's answer to the identity question starts "Firstname Surname, <dob>..."
        asks_name = re.search(r"(?:confirm|take|give me) your (?:full )?name", text, re.I)
        if t["role"] == "agent" and asks_name and i + 1 < len(turns):
            for word in turns[i + 1]["text"].split():
                bare = word.strip(".,")
                if not re.fullmatch(r"[A-Z][a-z]+", bare) or bare in NOT_NAMES:
                    break
                names.add(bare)
                if word[-1] in ".,":
                    break
    return {n for n in names if len(n) >= 3}


def run_checks(call: dict) -> list[dict]:
    summary: str = call["summary"]
    turns: list[dict] = call["turns"]
    out: list[dict] = []

    # --- Banned content -------------------------------------------------------
    m = re.search(r"arrears[^.;]{0,40}£\s?[\d,]+|£\s?[\d,]+[^.;]{0,30}\b(?:arrears|balance)\b", summary, re.I)
    if m:
        out.append(_check("arrears-amount", "Arrears or balance amount stated",
                          "Rules: never include numerical values for current arrears or total balance.", "major", span=_span(summary, m)))

    m = re.search(r"payment of £[\d,.]+ (?:was )?(?:made|taken)|£[\d,.]+ (?:was )?(?:paid|taken) (?:today|during)", summary, re.I)
    if m:
        out.append(_check("payment-amount", "Amount of payment taken during the call stated",
                          'Rules: never include amounts for payments taken during the call — use "Payment made."', "major", span=_span(summary, m)))

    for name in sorted(_person_names(turns)):
        m = re.search(rf"\b{re.escape(name)}\b", summary)
        if m:
            out.append(_check(f"name-{name.lower()}", f'Personal name "{name}" appears in summary',
                              "Rules: never include customer or agent names.", "major", span=_span(summary, m)))

    m = re.search(r"(?:\+44|\b0)\d[\d ]{8,12}\d\b", summary)
    if m:
        out.append(_check("phone-number", "Telephone number in summary", "Rules: never include telephone numbers.", "major", span=_span(summary, m)))

    for us, uk in US_SPELLINGS.items():
        m = re.search(rf"\b{us}\b", summary, re.I)
        if m:
            out.append(_check(f"spelling-{us}", f'US spelling "{m.group(0)}"', f'Use British English: "{uk}".', "minor", span=_span(summary, m)))

    for ph in PLACEHOLDERS:
        m = re.search(re.escape(ph), summary, re.I)
        if m:
            out.append(_check(f"placeholder-{ph.lower().replace(' ', '-').replace('/', '')}", f'Placeholder "{ph}" used',
                              "Critical Omission Rule: omit undiscussed categories entirely.", "minor", span=_span(summary, m)))

    if re.search(r"^\s*[-•*]\s", summary, re.M):
        out.append(_check("bullets", "Bullet points used", "Rules: complete sentences, no bullet points.", "minor"))

    sentences = [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z])", summary.strip()) if s]
    if len(sentences) > 5:
        out.append(_check("length", f"Summary has {len(sentences)} sentences", "Rules: concise, 2–5 sentences.", "minor"))

    m = re.search(r"(?<!risk of )further action", summary, re.I)
    if m:
        out.append(_check("further-action-wording", '"further action" used outside "risk of further action"',
                          'Rules: do not use "further action" to describe the plan.', "minor", span=_span(summary, m)))

    # --- Mandatory phrases ----------------------------------------------------
    if not re.match(r"\s*(DPA completed|no DPA stated with agent)", summary, re.I):
        out.append(_check("dpa-missing", "Summary does not open with the DPA status",
                          'Rules: start with "DPA completed" or "no DPA stated with agent".', "major"))

    warned = _agent_turns(turns, r"risk of further action")
    if warned and "risk of further action" not in summary.lower():
        out.append(_check("risk-warning-missing", "Risk of further action warning not reported",
                          'Agent explicitly warned the customer; the summary MUST include "risk of further action".', "critical", warned))

    website = _agent_turns(turns, r"website|signpost")
    if website and "customer signposted" not in summary.lower():
        out.append(_check("signposting-missing", '"customer signposted" missing',
                          'Agent pointed the customer to the company website / signposted; the rules require the phrase "customer signposted".',
                          "major", website))

    # --- Claims that need a confirming turn -----------------------------------
    m = re.search(r"payment made", summary, re.I)
    if m and not _agent_turns(turns, r"payment (?:has been|was) successful|(?:has|have) gone through successfully|payment has gone through|(?:payment|it)[^.]{0,30}successful"):
        out.append(_check("payment-made-unconfirmed", '"Payment made" but no successful payment in transcript',
                          "No agent turn confirms a successful payment during the call.", "critical", span=_span(summary, m)))

    m = re.search(r"default notice", summary, re.I)
    if m and not any(re.search(r"default", t["text"], re.I) for t in turns):
        out.append(_check("default-notice-unsupported", "Default notice mentioned but never discussed",
                          'The transcript never mentions a default or default notice.', "major", span=_span(summary, m)))

    m = re.search(r"authority to act[^.;]{0,30}verified|verified[^.;]{0,30}authority to act", summary, re.I)
    if m and not _agent_turns(turns, r"authority to act (?:is|has been) verified"):
        out.append(_check("ata-unconfirmed", "Authority to Act stated as verified but not confirmed",
                          "No agent turn confirms Authority to Act was verified.", "critical",
                          _agent_turns(turns, r"authority"), _span(summary, m)))

    m = re.search(r"consent gained to record vulnerability", summary, re.I)
    consent_turns = _agent_turns(turns, r"record|note .*(?:so we|so you)")
    if m and consent_turns:
        refused = [t["id"] for t in turns if t["role"] == "customer" and re.search(r"rather you didn't|don't want that|don't write", t["text"], re.I)]
        if refused:
            out.append(_check("consent-refused", "Consent stated but customer appears to have refused",
                              "A customer turn declines having the information recorded.", "critical", refused, _span(summary, m)))

    order = {"critical": 0, "major": 1, "minor": 2}
    return sorted(out, key=lambda c: order.get(c["severity"], 3))
