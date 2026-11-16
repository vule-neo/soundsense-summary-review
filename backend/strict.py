"""Strict gate for green ("supported") claims.

The AI's "supported" verdict is only kept if independent, mechanical checks agree.
Otherwise the claim is downgraded to "uncertain" (shown as "Needs check") with the
reasons listed, so a hurried reviewer never skips an unproven claim.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

UNITS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19,
}
TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
ORDINALS = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9,
    "tenth": 10, "eleventh": 11, "twelfth": 12, "thirteenth": 13, "fourteenth": 14, "fifteenth": 15,
    "sixteenth": 16, "seventeenth": 17, "eighteenth": 18, "nineteenth": 19, "twentieth": 20, "thirtieth": 30,
}
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def spoken_numbers(text: str) -> set[int]:
    """All numbers in text, from digits ("£220", "1,760") and words ("seventeen hundred and sixty")."""
    nums = {int(n.replace(",", "")) for n in re.findall(r"\d[\d,]*", text)}
    # Punctuation ends a number phrase ("a hundred. two hundred" is two numbers).
    tokens = re.findall(r"[a-z]+|[.,;:!?]", text.lower().replace("-", " "))
    current, active = 0, False
    for tok in tokens + ["<end>"]:
        if tok in UNITS:
            current += UNITS[tok]; active = True
        elif tok in TENS:
            current += TENS[tok]; active = True
        elif tok == "hundred":
            current = (current or 1) * 100; active = True
        elif tok == "thousand":
            current = (current or 1) * 1000; active = True
        elif tok == "a" or (tok == "and" and active):
            continue
        else:
            if active:
                nums.add(current)
            current, active = 0, False
    return nums


def spoken_days(text: str, call_date: date) -> set[int]:
    """Day-of-month numbers referred to in text: '23rd', 'twenty-third', 'Friday', 'tomorrow'."""
    low = text.lower().replace("-", " ")
    days = {int(d) for d in re.findall(r"\b(\d{1,2})(?:st|nd|rd|th)?\b", low) if 1 <= int(d) <= 31}
    words = re.findall(r"[a-z]+", low)
    for i, w in enumerate(words):
        if w in ORDINALS:
            prev = words[i - 1] if i else ""
            days.add(ORDINALS[w] + (TENS.get(prev, 0) if prev in ("twenty", "thirty") else 0))
    for i, wd in enumerate(WEEKDAYS):
        if wd in words:
            ahead = (i - call_date.weekday()) % 7 or 7
            days.add((call_date + timedelta(days=ahead)).day)
            days.add((call_date + timedelta(days=ahead + 7)).day)  # "the Friday after"
    if "tomorrow" in words:
        days.add((call_date + timedelta(days=1)).day)
    if "today" in words:
        days.add(call_date.day)
    return days


def _claim_amounts(text: str) -> list[int]:
    return [int(float(m.replace(",", ""))) for m in re.findall(r"£\s?([\d,]+(?:\.\d+)?)", text)]


def _claim_days(text: str) -> list[int]:
    rx = r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:" + "|".join(MONTHS) + r")\b"
    return [int(d) for d in re.findall(rx, text, re.I)]


def _claim_times(text: str) -> list[tuple[str, str]]:
    """(phrase, hour) pairs like ('after 3 pm', '3') or ('at 2 pm', '2')."""
    return [(m.group(0), m.group(2)) for m in re.finditer(r"(after |at |by |before |from )?(\d{1,2})(?:[.:]\d{2})?\s?(?:am|pm)\b", text, re.I)]


def strict_reasons(claim: dict, turns_by_id: dict[str, dict], call_date: date, flagged_spans: list[tuple[int, int, str]]) -> list[str]:
    """Reasons a 'supported' claim must not be shown as green."""
    reasons: list[str] = []
    ev = claim["evidence"]

    if claim.get("start") is None:
        reasons.append("Claim text could not be located in the summary.")
    if not ev:
        reasons.append("No transcript evidence cited.")
    bad = [e["turn_id"] for e in ev if e["status"] != "verified"]
    if bad:
        reasons.append(f"Cited quote could not be verified in {', '.join(bad)}.")
    noise = [e["turn_id"] for e in ev if e.get("ignored_turn")]
    if noise:
        reasons.append(f"Relies on {', '.join(noise)}, which is marked as transcription noise.")

    cited_ids = {e["turn_id"] for e in ev} | {t for k in claim["key_terms"] for t in k["turn_ids"]}
    cited_text = " ".join(turns_by_id[t]["text"] for t in cited_ids if t in turns_by_id)

    numbers = spoken_numbers(cited_text)
    for amt in _claim_amounts(claim["text"]):
        if amt not in numbers:
            reasons.append(f"£{amt} does not appear in the cited turns.")

    days = spoken_days(cited_text, call_date)
    for d in _claim_days(claim["text"]):
        if d not in days:
            reasons.append(f"Date '{d}' is not stated in the cited turns.")

    low_cited = cited_text.lower()
    for phrase, hour in _claim_times(claim["text"]):
        hour_words = {hour, next((w for w, n in UNITS.items() if str(n) == hour), hour)}
        if not any(re.search(rf"\b{re.escape(h)}\b", low_cited) for h in hour_words):
            reasons.append(f"Time '{phrase.strip()}' is not stated in the cited turns.")
        elif not phrase.lower().startswith("after") and re.search(r"\bafter\b", low_cited):
            reasons.append(f"Summary says '{phrase.strip()}' but the call only agreed a time window ('after …').")

    for k in claim["key_terms"]:
        if not k["turn_ids"]:
            reasons.append(f"Key value '{k['text']}' has no linked transcript turn.")

    if claim.get("start") is not None:
        for s, e, title in flagged_spans:
            if s < claim["end"] and e > claim["start"]:
                reasons.append(f"Rule check flagged this text: {title}.")
    return reasons


def apply_strict_gate(call: dict, analysis: dict, rule_checks: list[dict]) -> None:
    turns_by_id = {t["id"]: t for t in call["turns"]}
    call_date = date.fromisoformat(call["call_date"])
    flagged = [(c["start"], c["end"], c["title"]) for c in rule_checks if c.get("start") is not None]
    for claim in analysis["claims"]:
        claim["ai_verdict"] = claim["verdict"]
        claim["check_reasons"] = []
        if claim["verdict"] != "supported":
            continue
        reasons = strict_reasons(claim, turns_by_id, call_date, flagged)
        if reasons:
            claim["verdict"] = "uncertain"
            claim["severity"] = "minor"
            claim["check_reasons"] = reasons
