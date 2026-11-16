"""Structured output schema the AI reviewer must return for each call.

Every finding carries turn-level evidence (turn ID + verbatim quote) so the UI can
link it back to the transcript and the server can verify the quote really exists.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Severity = Literal["critical", "major", "minor", "none"]

ClaimVerdict = Literal[
    "supported",  # transcript backs the claim and it follows the rules
    "contradicted",  # transcript says something different
    "unsupported",  # nothing in the transcript backs it
    "rule_breach",  # fact may be right but the summary rules forbid how it is written
    "uncertain",  # evidence is ambiguous; reviewer must decide
]

FactField = Literal[
    "call_direction",
    "dpa",
    "third_party_authority",
    "account_status",
    "reason_for_non_payment",
    "hardship_and_vulnerability",
    "consent_to_record_vulnerability",
    "income_and_expenditure",
    "risk_of_further_action",
    "signposting_and_referrals",
    "forbearance_or_hold",
    "payment_during_call",
    "promise_to_pay",
    "next_steps",
]

FactStatus = Literal[
    "match",  # summary states it correctly
    "mismatch",  # summary states it, but wrongly
    "missing_in_summary",  # discussed + required by rules, absent from summary
    "not_in_transcript",  # summary states it, transcript has no basis
    "not_applicable",  # not discussed and not required — correctly absent
]


class Evidence(BaseModel):
    turn_id: str = Field(description='Transcript turn ID, e.g. "T08".')
    quote: str = Field(description="Short VERBATIM excerpt copied character-for-character from that turn.")


class KeyTerm(BaseModel):
    text: str = Field(description='Exact substring of the claim, e.g. "£780", "23 October", "after 3 pm", "fourteen-day".')
    kind: Literal["amount", "date", "time", "duration", "other"]
    turn_ids: list[str] = Field(description="Turns where this value is stated or decided.")


class Claim(BaseModel):
    text: str = Field(description="Exact VERBATIM substring of the summary that makes one checkable claim.")
    verdict: ClaimVerdict
    severity: Severity = Field(description='"none" when verdict is supported.')
    explanation: str = Field(description="One or two sentences. For problems: what is wrong and what the transcript says instead.")
    rule: str = Field(description='Summary rule involved, e.g. "Arrears/Balances", or "" if none.')
    evidence: list[Evidence]
    key_terms: list[KeyTerm]


class FactRow(BaseModel):
    field: FactField
    transcript_value: str = Field(description="What actually happened per the transcript (final position), or \"\".")
    summary_value: str = Field(description="What the summary states, or \"\" if absent.")
    status: FactStatus
    severity: Severity
    evidence: list[Evidence]


class Omission(BaseModel):
    title: str = Field(description="Short label, e.g. \"Risk of further action warning not reported\".")
    detail: str = Field(description="What was said in the call and why the summary must include it.")
    rule: str = Field(description="Summary rule that requires it.")
    severity: Severity
    suggested_wording: str = Field(description="Rule-compliant wording the summary should have contained.")
    evidence: list[Evidence]


class IgnoredTurn(BaseModel):
    turn_id: str
    reason: str = Field(description="Why this turn is excluded, e.g. hold-music ASR hallucination.")


class CallAnalysis(BaseModel):
    overall_verdict: Literal["accurate", "minor_issues", "needs_correction"]
    headline: str = Field(description="One sentence for the reviewer: the single most important finding.")
    claims: list[Claim] = Field(description="The whole summary split into consecutive claims, in order, covering every sentence.")
    facts: list[FactRow] = Field(description="Exactly one row per FactField, in the listed order.")
    omissions: list[Omission] = Field(description="Important, rule-required items discussed in the call but missing from the summary.")
    ignored_turns: list[IgnoredTurn]
