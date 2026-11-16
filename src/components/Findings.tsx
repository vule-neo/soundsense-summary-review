"use client";

import type { Claim, Evidence, FactRow, Focus, Omission, RuleCheck, Severity } from "@/lib/types";
import { FACT_LABELS, SEVERITY_RANK, factStatusStyle, severityBadge, verdictChip, verdictLabel } from "@/lib/ui";

type FocusFn = (f: Focus) => void;

export function SeverityBadge({ severity }: { severity: Severity }) {
  if (severity === "none") return null;
  return (
    <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide ${severityBadge[severity]}`}>
      {severity}
    </span>
  );
}

const evidenceTitle: Record<Evidence["status"], string> = {
  verified: "Quote verified in this turn",
  partial: "Quote only partly matches this turn — check it",
  wrong_turn: "Quote exists, but in a different turn — check it",
  not_found: "Quote NOT found in transcript — do not rely on it",
};

export function EvidenceChips({ evidence, onFocus, source }: { evidence: Evidence[]; onFocus: FocusFn; source: string }) {
  if (!evidence.length) return <span className="text-xs italic text-slate-400">no transcript evidence</span>;
  return (
    <div className="flex flex-wrap gap-1.5">
      {evidence.map((e, i) => {
        const ok = e.status === "verified" && !e.ignored_turn;
        return (
          <button
            key={i}
            type="button"
            onClick={(ev) => {
              // Chips live inside clickable claim cards: don't let the card re-focus the claim's first turn.
              ev.stopPropagation();
              onFocus({ turnIds: [e.turn_id], quotes: [e.quote], source: `${source}-${i}` });
            }}
            title={`${evidenceTitle[e.status]}${e.ignored_turn ? " (turn marked as ASR noise)" : ""}\n“${e.quote}”`}
            className={`group inline-flex max-w-full items-center gap-1 rounded-full border px-2 py-0.5 text-xs hover:bg-sky-50 ${
              ok ? "border-slate-300 text-slate-700" : "border-red-400 bg-red-50 text-red-700"
            }`}
          >
            <span className="font-mono font-semibold">{e.turn_id}</span>
            <span className="truncate italic text-slate-500 group-hover:text-slate-700">“{e.quote}”</span>
            {!ok && <span className="font-bold">⚠</span>}
          </button>
        );
      })}
    </div>
  );
}

function allQuotes(ev: Evidence[]) {
  return { turnIds: [...new Set(ev.map((e) => e.turn_id))], quotes: ev.map((e) => e.quote) };
}

export function ClaimCard({ claim, onFocus, active, onClick }: { claim: Claim; onFocus: FocusFn; active?: boolean; onClick?: () => void }) {
  return (
    <div
      onClick={onClick}
      className={`rounded-lg border bg-white p-3 ${active ? "border-slate-900 ring-1 ring-slate-900" : "border-slate-200"} ${onClick ? "cursor-pointer hover:border-slate-400" : ""}`}
    >
      <div className="mb-1.5 flex flex-wrap items-center gap-2">
        <span className={`rounded px-1.5 py-0.5 text-[11px] font-semibold ${verdictChip[claim.verdict]}`}>{verdictLabel[claim.verdict]}</span>
        <SeverityBadge severity={claim.severity} />
        {claim.rule && <span className="text-[11px] text-slate-500">Rule: {claim.rule}</span>}
        {claim.start === null && <span className="text-[11px] font-semibold text-red-600">⚠ text not found in summary</span>}
      </div>
      <p className="mb-1.5 text-sm font-medium text-slate-900">“{claim.text}”</p>
      <p className="mb-2 text-sm text-slate-600">{claim.explanation}</p>
      <EvidenceChips evidence={claim.evidence} onFocus={onFocus} source={`claim-${claim.text.slice(0, 20)}`} />
    </div>
  );
}

export function IssuesList({
  claims,
  checks,
  onFocus,
  onSelectClaim,
  selected,
}: {
  claims: Claim[];
  checks: RuleCheck[];
  onFocus: FocusFn;
  onSelectClaim: (i: number) => void;
  selected: number | null;
}) {
  const problems = claims
    .map((c, i) => ({ c, i }))
    .filter(({ c }) => c.verdict !== "supported")
    .sort((a, b) => SEVERITY_RANK[a.c.severity] - SEVERITY_RANK[b.c.severity]);

  if (!problems.length && !checks.length)
    return <p className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800">No problems found in the summary text. Still confirm the fact sheet and transcript before approving.</p>;

  return (
    <div className="space-y-2">
      {problems.map(({ c, i }) => (
        <ClaimCard
          key={`c${i}`}
          claim={c}
          active={selected === i}
          onClick={() => onSelectClaim(i)}
          onFocus={onFocus}
        />
      ))}
      {checks.map((chk) => (
        <div key={chk.id} className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-3">
          <div className="mb-1 flex flex-wrap items-center gap-2">
            <span className="rounded bg-slate-700 px-1.5 py-0.5 text-[11px] font-semibold text-white">Rule check</span>
            <SeverityBadge severity={chk.severity} />
            <span className="text-sm font-semibold text-slate-900">{chk.title}</span>
          </div>
          <p className="text-sm text-slate-600">{chk.detail}</p>
          <div className="mt-1.5 flex flex-wrap gap-1.5 text-xs">
            {chk.summary_text && <span className="rounded bg-white px-1.5 py-0.5 font-mono text-slate-700 ring-1 ring-slate-300">“{chk.summary_text}”</span>}
            {chk.turn_ids.map((t) => (
              <button
                key={t}
                type="button"
                onClick={(ev) => {
                  ev.stopPropagation();
                  onFocus({ turnIds: [t], quotes: [], source: `chk-${chk.id}-${t}` });
                }}
                className="rounded-full border border-slate-300 bg-white px-2 py-0.5 font-mono font-semibold text-slate-700 hover:bg-sky-50"
              >
                {t}
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export function OmissionsList({ omissions, onFocus }: { omissions: Omission[]; onFocus: FocusFn }) {
  const sorted = [...omissions].sort((a, b) => SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity]);
  if (!sorted.length) return <p className="text-sm text-slate-500">Nothing important from the call is missing from the summary.</p>;
  return (
    <div className="space-y-2">
      {sorted.map((o, i) => (
        <div key={i} className="rounded-lg border border-orange-200 bg-orange-50/60 p-3">
          <div className="mb-1 flex flex-wrap items-center gap-2">
            <SeverityBadge severity={o.severity} />
            <span className="text-sm font-semibold text-slate-900">{o.title}</span>
            {o.rule && <span className="text-[11px] text-slate-500">Rule: {o.rule}</span>}
          </div>
          <p className="mb-1.5 text-sm text-slate-700">{o.detail}</p>
          {o.suggested_wording && (
            <p className="mb-2 text-sm text-slate-600">
              <span className="font-semibold text-slate-700">Should have said: </span>
              <span className="italic">“{o.suggested_wording}”</span>
            </p>
          )}
          <EvidenceChips evidence={o.evidence} onFocus={onFocus} source={`om-${i}`} />
        </div>
      ))}
    </div>
  );
}

export function FactSheet({ facts, onFocus }: { facts: FactRow[]; onFocus: FocusFn }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
      <table className="w-full min-w-[640px] text-sm">
        <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
          <tr>
            <th className="px-3 py-2">Item</th>
            <th className="px-3 py-2">Transcript says</th>
            <th className="px-3 py-2">Summary says</th>
            <th className="px-3 py-2">Status</th>
          </tr>
        </thead>
        <tbody>
          {facts.map((f) => {
            const st = factStatusStyle[f.status];
            const quiet = f.status === "not_applicable";
            const { turnIds, quotes } = allQuotes(f.evidence);
            return (
              <tr
                key={f.field}
                onClick={() => turnIds.length && onFocus({ turnIds, quotes, source: `fact-${f.field}` })}
                className={`border-t border-slate-100 align-top ${quiet ? "text-slate-400" : "text-slate-800"} ${turnIds.length ? "cursor-pointer hover:bg-sky-50" : ""}`}
              >
                <td className="px-3 py-2 font-medium">
                  {FACT_LABELS[f.field] ?? f.field}
                  {turnIds.length > 0 && <div className="mt-0.5 font-mono text-[11px] text-sky-700">{turnIds.join(" · ")}</div>}
                </td>
                <td className="px-3 py-2">{f.transcript_value || "—"}</td>
                <td className="px-3 py-2">{f.summary_value || "—"}</td>
                <td className="px-3 py-2 whitespace-nowrap">
                  <span className={`rounded px-1.5 py-0.5 text-[11px] font-semibold ${st.cls}`}>{st.label}</span>{" "}
                  <SeverityBadge severity={f.status === "match" || quiet ? "none" : f.severity} />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
