"""Ground the AI output in the actual text.

- Locates every claim and key term in the summary (character offsets) so the UI
  can render clickable spans.
- Checks every evidence quote really occurs in the turn it cites. Quotes that
  don't are marked unverified, so the reviewer never trusts invented evidence.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher

_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-"})


def normalise(text: str) -> str:
    text = text.translate(_QUOTES).lower()
    text = re.sub(r"[^\w£'\s-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _find(haystack: str, needle: str, start: int = 0) -> tuple[int, int] | None:
    """Exact, then case/quote-insensitive, then fuzzy location of needle in haystack."""
    if not needle:
        return None
    i = haystack.find(needle, start)
    if i == -1:
        i = haystack.find(needle, 0)
    if i != -1:
        return i, i + len(needle)

    hay = haystack.translate(_QUOTES).lower()
    ndl = needle.translate(_QUOTES).lower().strip()
    i = hay.find(ndl)
    if i != -1:
        return i, i + len(ndl)

    # Fuzzy: best window of the same length, accepted only if very similar.
    best, best_ratio = None, 0.0
    n = len(ndl)
    step = max(1, n // 20)
    for s in range(0, max(1, len(hay) - n + 1), step):
        r = SequenceMatcher(None, hay[s : s + n], ndl).ratio()
        if r > best_ratio:
            best, best_ratio = (s, s + n), r
    return best if best_ratio >= 0.85 else None


def verify_quote(turns_by_id: dict[str, dict], turn_id: str, quote: str) -> str:
    """Return 'verified', 'partial', 'wrong_turn' or 'not_found'."""
    q = normalise(quote).strip(" .")
    if not q:
        return "not_found"
    turn = turns_by_id.get(turn_id)
    if turn and q in normalise(turn["text"]):
        return "verified"
    if any(q in normalise(t["text"]) for t in turns_by_id.values()):
        return "wrong_turn"
    if turn:
        words = [w for w in q.split() if len(w) > 2]
        if words:
            hits = sum(1 for w in words if w in normalise(turn["text"]))
            if hits / len(words) >= 0.7:
                return "partial"
    return "not_found"


def _verify_evidence(items: list[dict], turns_by_id: dict[str, dict], ignored: set[str]) -> None:
    for ev in items:
        tid = ev["turn_id"].strip().upper()
        ev["turn_id"] = tid
        ev["status"] = verify_quote(turns_by_id, tid, ev["quote"])
        ev["ignored_turn"] = tid in ignored


def enrich_analysis(call: dict, analysis: dict) -> dict:
    """Mutates and returns the analysis with offsets and evidence verification."""
    summary = call["summary"]
    turns_by_id = {t["id"]: t for t in call["turns"]}
    ignored = {t["turn_id"].strip().upper() for t in analysis.get("ignored_turns", [])}

    cursor = 0
    for claim in analysis["claims"]:
        loc = _find(summary, claim["text"], cursor)
        claim["start"], claim["end"] = loc if loc else (None, None)
        if loc:
            cursor = loc[1]
        _verify_evidence(claim["evidence"], turns_by_id, ignored)
        for term in claim["key_terms"]:
            term["turn_ids"] = [t.strip().upper() for t in term["turn_ids"] if t.strip().upper() in turns_by_id]
            base = claim["start"] if claim["start"] is not None else 0
            region = summary[base : claim["end"]] if claim["end"] is not None else summary
            tloc = _find(region, term["text"])
            term["start"], term["end"] = (base + tloc[0], base + tloc[1]) if tloc else (None, None)

    for row in analysis["facts"]:
        _verify_evidence(row["evidence"], turns_by_id, ignored)
    for om in analysis["omissions"]:
        _verify_evidence(om["evidence"], turns_by_id, ignored)

    all_ev = [e for c in analysis["claims"] for e in c["evidence"]] + [
        e for group in ("facts", "omissions") for item in analysis[group] for e in item["evidence"]
    ]
    analysis["evidence_stats"] = {
        "total": len(all_ev),
        "verified": sum(e["status"] == "verified" for e in all_ev),
        "unverified": sum(e["status"] != "verified" for e in all_ev),
    }
    analysis["unlocated_claims"] = sum(c["start"] is None for c in analysis["claims"])
    return analysis
