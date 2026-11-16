import type { ClaimVerdict, FactStatus, Severity } from "./types";

export const SEVERITY_RANK: Record<Severity, number> = { critical: 0, major: 1, minor: 2, none: 3 };

export const severityBadge: Record<Severity, string> = {
  critical: "bg-red-600 text-white",
  major: "bg-orange-500 text-white",
  minor: "bg-amber-200 text-amber-900",
  none: "bg-emerald-100 text-emerald-800",
};

export const verdictLabel: Record<ClaimVerdict, string> = {
  supported: "Verified",
  contradicted: "Contradicted",
  unsupported: "Unsupported",
  rule_breach: "Rule breach",
  uncertain: "Needs check",
};

/** Highlight style for a claim span inside the summary text. */
export const verdictSpan: Record<ClaimVerdict, string> = {
  supported: "decoration-emerald-500 bg-emerald-50 hover:bg-emerald-100",
  contradicted: "decoration-red-600 bg-red-100 hover:bg-red-200",
  unsupported: "decoration-orange-500 bg-orange-100 hover:bg-orange-200",
  rule_breach: "decoration-purple-600 bg-purple-100 hover:bg-purple-200",
  uncertain: "decoration-amber-500 decoration-dashed bg-yellow-200 hover:bg-yellow-300",
};

export const verdictChip: Record<ClaimVerdict, string> = {
  supported: "bg-emerald-100 text-emerald-800",
  contradicted: "bg-red-100 text-red-800",
  unsupported: "bg-orange-100 text-orange-800",
  rule_breach: "bg-purple-100 text-purple-800",
  uncertain: "bg-yellow-200 text-yellow-900",
};

export const factStatusStyle: Record<FactStatus, { label: string; cls: string }> = {
  match: { label: "Match", cls: "bg-emerald-100 text-emerald-800" },
  mismatch: { label: "Mismatch", cls: "bg-red-100 text-red-800" },
  missing_in_summary: { label: "Missing", cls: "bg-orange-100 text-orange-800" },
  not_in_transcript: { label: "Not in transcript", cls: "bg-purple-100 text-purple-800" },
  not_applicable: { label: "Not discussed", cls: "bg-slate-100 text-slate-500" },
};

export const FACT_LABELS: Record<string, string> = {
  call_direction: "Call direction",
  dpa: "DPA / security",
  third_party_authority: "Third party & Authority to Act",
  account_status: "Account status",
  reason_for_non_payment: "Reason for non-payment",
  hardship_and_vulnerability: "Hardship & vulnerability",
  consent_to_record_vulnerability: "Consent to record vulnerability",
  income_and_expenditure: "Income & expenditure",
  risk_of_further_action: "Risk of further action",
  signposting_and_referrals: "Signposting & referrals",
  forbearance_or_hold: "Forbearance / hold",
  payment_during_call: "Payment during call",
  promise_to_pay: "Promise to pay",
  next_steps: "Next steps",
};

export const verdictOverall = {
  accurate: { label: "Accurate", cls: "bg-emerald-600 text-white" },
  minor_issues: { label: "Minor issues", cls: "bg-amber-500 text-white" },
  needs_correction: { label: "Needs correction", cls: "bg-red-600 text-white" },
} as const;
