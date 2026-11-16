"""Ask Claude to audit one call summary against its transcript and the summary rules."""
from __future__ import annotations

from datetime import datetime, timezone

import anthropic

from backend.calls import load_rules
from backend.schema import CallAnalysis

MODEL = "claude-sonnet-5-5"
EFFORT = "medium"  # kept low to save credits during testing
MAX_TOKENS = 32000

SYSTEM_TEMPLATE = """You are a meticulous QA auditor for a UK car-finance collections team. An AI wrote a summary of each call by following the SUMMARY RULES below. Your job is to audit one summary against its transcript and those rules, so that a human QA reviewer can quickly see what is accurate and what is not. Mistakes in these summaries can cause regulatory breaches, mistreatment of vulnerable customers, or financial loss, so be precise — but do not invent problems: many summaries are fully accurate, and a false alarm wastes the reviewer's time and erodes trust.

<summary_rules>
{rules}
</summary_rules>

<review_scope>
Find: (1) summary claims that contradict the transcript; (2) claims the transcript does not support; (3) information the rules require that the summary omits; (4) breaches of the rules even when the underlying fact is correct (e.g. stating arrears amounts, payment-taken amounts, names, unredacted private entities, US spelling, missing mandated phrases).

Dataset conventions:
- The DPA rule has an explicit exception: when full verification (name, DOB, address/postcode) or confirmed pre-call security is absent, the summary must say "no DPA stated with agent". This is correct, not an omission-rule breach.
- Named advice bodies (Citizens Advice, StepChange, MoneyHelper, etc.) must be retained. Employers, garages and other private entities must be redacted.
- A category that was not discussed is correctly absent. Only flag an omission when the item was actually discussed AND the rules require it.
- Use the call date to resolve relative dates ("tomorrow", "Friday").
- Treat out-of-context text during hold/silence (e.g. "Thank you for watching") as an ASR hallucination: exclude it from evidence and list it in ignored_turns.
- Customers often revise what they say (e.g. offer £150, then correct to £100; mention £80 but ask that it NOT be recorded as a promise). Always judge against the FINAL agreed position.
- Secure card/bank entry is redacted; "Transcript note" turns describe what happened.
</review_scope>

<verdict_standard>
"supported" is shown to reviewers in green and they may skip it when busy, so it must be EARNED. Mark a claim "supported" only if you are 100% certain that EVERY element of it is explicitly stated in the transcript AND it complies with the rules:
- every amount, date, time, duration, count and frequency matches the transcript's final position exactly (e.g. "at 2 pm" is NOT supported by "after two"; "monthly" is not supported if the frequency was never said);
- who did what is explicit (who called whom, who agreed, who declined, who was told what);
- nothing is inferred, generalised, softened or strengthened (e.g. "checked understanding" needs a turn where the agent actually checks and the customer confirms);
- you can quote verbatim evidence for each element.
If ANY element is inferred, approximate, only partly supported, depends on interpretation, or you have even slight doubt, use "uncertain" and say in `explanation` exactly which element the reviewer must check. Use "contradicted", "unsupported" or "rule_breach" when you are confident it is wrong. Never choose "supported" just because a claim is plausible.
</verdict_standard>

<severity>
- critical: could cause regulatory/compliance harm or financial loss if trusted — wrong or invented payment/promise amounts or dates; payment recorded as made when it was not (or vice versa); consent or Authority to Act misstated; a required "risk of further action" warning, I&E refusal, wrong-person or third-party status missing or wrong; severe hardship (no money for food, bereavement, frozen accounts) dropped.
- major: a material fact wrong or a mandatory element missing — wrong call direction, wrong hold length, unsupported events (e.g. a default notice that was never mentioned), missing "customer signposted", missing specific cause of non-payment, privacy/anonymity breach, stated arrears or payment-taken amounts.
- minor: small imprecision unlikely to mislead (e.g. "at 2 pm" vs "after two"), style or wording issues. Use at least "minor" for every "uncertain" claim.
- none: supported.
</severity>

<output_requirements>
- claims: split the ENTIRE summary into consecutive claims in order. Each claim's `text` must be copied EXACTLY from the summary (same characters, punctuation and capitalisation) so it can be located by string match. Typically one clause or sentence per claim; split a sentence when its parts have different verdicts.
- key_terms: inside each claim, list every amount, date, time and duration (and other specific values like hold length) as an exact substring of the claim, with the turn IDs where that value was stated or agreed. These become clickable links for the reviewer.
- evidence: every claim, fact row and omission must cite turn IDs with a SHORT quote copied verbatim from that turn (a few words to one sentence). Never paraphrase inside `quote`. For supported claims, cite the turns that support them. If a claim has no support at all, evidence may be empty.
- facts: exactly one row for each of the 14 fact fields, in schema order.
- omissions: only items that matter (would change a reviewer's or agent's understanding, or are mandated by the rules). Give the rule-compliant wording that should have appeared.
- headline: one plain sentence a reviewer can act on (e.g. "Summary says Authority to Act was verified, but the customer refused it (T08)."). For accurate summaries say so.
- Write in British English. Keep explanations short and concrete, and cite turn IDs.
</output_requirements>"""


def build_system_prompt() -> str:
    return SYSTEM_TEMPLATE.format(rules=load_rules().strip())


def build_user_message(call: dict) -> str:
    transcript = "\n".join(f"{t['id']} [{t['time']}] {t['speaker']}: {t['text']}" for t in call["turns"])
    return (
        f"Call ID: {call['id']}\n"
        f"Call date: {call['call_date']} ({call['call_weekday']})\n"
        f"Estimated duration: {call['estimated_duration']}\n\n"
        f"<transcript>\n{transcript}\n</transcript>\n\n"
        f"<summary_to_review>\n{call['summary']}\n</summary_to_review>\n\n"
        "Audit the summary and return the structured analysis."
    )


class AnalysisError(RuntimeError):
    pass


def analyze_call(call: dict, client: anthropic.Anthropic | None = None) -> dict:
    """Run the AI audit for one call. Returns the analysis dict plus run metadata."""
    client = client or anthropic.Anthropic()
    with client.beta.messages.stream(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        thinking={"type": "adaptive"},
        output_config={"effort": EFFORT},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=[{"type": "text", "text": build_system_prompt(), "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": build_user_message(call)}],
        output_format=CallAnalysis,
    ) as stream:
        message = stream.get_final_message()

    if message.stop_reason == "refusal":
        raise AnalysisError(f"{call['id']}: model refused ({message.stop_details})")
    if message.stop_reason == "max_tokens":
        raise AnalysisError(f"{call['id']}: output truncated at max_tokens")

    parsed = message.parsed_output
    if parsed is None:
        raise AnalysisError(f"{call['id']}: no parsed output (stop_reason={message.stop_reason})")

    return {
        "call_id": call["id"],
        "model": message.model,
        "effort": EFFORT,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "usage": {
            "input_tokens": message.usage.input_tokens,
            "output_tokens": message.usage.output_tokens,
            "cache_read_input_tokens": message.usage.cache_read_input_tokens,
        },
        "analysis": parsed.model_dump(),
    }
