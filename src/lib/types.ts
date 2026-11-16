export type Severity = "critical" | "major" | "minor" | "none";
export type ClaimVerdict = "supported" | "contradicted" | "unsupported" | "rule_breach" | "uncertain";
export type EvidenceStatus = "verified" | "partial" | "wrong_turn" | "not_found";
export type FactStatus = "match" | "mismatch" | "missing_in_summary" | "not_in_transcript" | "not_applicable";

export interface Turn {
  id: string;
  time: string;
  speaker: string;
  role: "agent" | "customer" | "third_party" | "note" | "unclear" | "other";
  text: string;
}

export interface Evidence {
  turn_id: string;
  quote: string;
  status: EvidenceStatus;
  ignored_turn: boolean;
}

export interface KeyTerm {
  text: string;
  kind: "amount" | "date" | "time" | "duration" | "other";
  turn_ids: string[];
  start: number | null;
  end: number | null;
}

export interface Claim {
  text: string;
  verdict: ClaimVerdict;
  severity: Severity;
  explanation: string;
  rule: string;
  evidence: Evidence[];
  key_terms: KeyTerm[];
  start: number | null;
  end: number | null;
}

export interface FactRow {
  field: string;
  transcript_value: string;
  summary_value: string;
  status: FactStatus;
  severity: Severity;
  evidence: Evidence[];
}

export interface Omission {
  title: string;
  detail: string;
  rule: string;
  severity: Severity;
  suggested_wording: string;
  evidence: Evidence[];
}

export interface RuleCheck {
  id: string;
  title: string;
  detail: string;
  severity: Exclude<Severity, "none">;
  turn_ids: string[];
  summary_text: string;
  start: number | null;
  end: number | null;
}

export interface Analysis {
  overall_verdict: "accurate" | "minor_issues" | "needs_correction";
  headline: string;
  claims: Claim[];
  facts: FactRow[];
  omissions: Omission[];
  ignored_turns: { turn_id: string; reason: string }[];
  evidence_stats: { total: number; verified: number; unverified: number };
  unlocated_claims: number;
}

export interface Counts {
  critical: number;
  major: number;
  minor: number;
}

export interface CallListItem {
  id: string;
  call_date: string;
  estimated_duration: string;
  analysed: boolean;
  overall_verdict: Analysis["overall_verdict"] | null;
  headline: string | null;
  counts: Counts;
}

export interface CallDetail {
  id: string;
  call_date: string;
  call_weekday: string;
  estimated_duration: string;
  summary: string;
  turns: Turn[];
  rule_checks: RuleCheck[];
  analysis: Analysis | null;
  analysis_meta: { model: string; effort: string; generated_at: string } | null;
  counts: Counts;
}

/** What the transcript should spotlight after a click. */
export interface Focus {
  turnIds: string[];
  quotes: string[];
  source: string;
}
