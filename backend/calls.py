"""Load the call dataset and split transcripts into addressable turns."""
from __future__ import annotations

import json
import re
from datetime import date
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "soundsense-exercise-data"
CALLS_FILE = DATA_DIR / "candidate-calls.json"
RULES_FILE = DATA_DIR / "summary-rules.txt"

TURN_RE = re.compile(r"^(T\d+)\s+\[(\d{2}:\d{2})\]\s+([^:]+):\s*(.*)$")

THIRD_PARTY_SPEAKERS = {"Mother", "Father", "Partner", "Spouse", "Husband", "Wife", "Representative"}


def speaker_role(speaker: str) -> str:
    """Classify a speaker label so the UI can colour-code it."""
    if speaker == "Agent":
        return "agent"
    if speaker == "Customer":
        return "customer"
    if speaker == "Transcript note":
        return "note"
    if speaker.lower().startswith("unclear"):
        return "unclear"
    if speaker in THIRD_PARTY_SPEAKERS:
        return "third_party"
    return "other"


def parse_transcript(transcript: str) -> list[dict]:
    turns: list[dict] = []
    for line in transcript.splitlines():
        line = line.strip()
        if not line:
            continue
        m = TURN_RE.match(line)
        if m:
            turn_id, ts, speaker, text = m.groups()
            speaker = speaker.strip()
            turns.append(
                {"id": turn_id, "time": ts, "speaker": speaker, "role": speaker_role(speaker), "text": text.strip()}
            )
        elif turns:  # continuation line: attach to previous turn
            turns[-1]["text"] += " " + line
    return turns


@lru_cache(maxsize=1)
def load_calls() -> dict[str, dict]:
    raw = json.loads(CALLS_FILE.read_text(encoding="utf-8"))
    calls: dict[str, dict] = {}
    for rec in raw:
        call_date = date.fromisoformat(rec["call_date"])
        calls[rec["id"]] = {
            "id": rec["id"],
            "call_date": rec["call_date"],
            "call_weekday": call_date.strftime("%A"),
            "estimated_duration": rec["estimated_duration"],
            "summary": rec["summary"],
            "transcript": rec["transcript"],
            "turns": parse_transcript(rec["transcript"]),
        }
    return dict(sorted(calls.items()))


@lru_cache(maxsize=1)
def load_rules() -> str:
    return RULES_FILE.read_text(encoding="utf-8")
