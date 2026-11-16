"use client";

import type { Claim, KeyTerm } from "@/lib/types";
import { verdictSpan } from "@/lib/ui";

const kindIcon: Record<KeyTerm["kind"], string> = {
  amount: "£",
  date: "📅",
  time: "🕒",
  duration: "⏱",
  other: "•",
};

function renderClaim(
  summary: string,
  claim: Claim,
  onTerm: (term: KeyTerm, claim: Claim) => void,
): React.ReactNode[] {
  const start = claim.start!;
  const end = claim.end!;
  const terms = claim.key_terms
    .filter((t) => t.start !== null && t.end !== null && t.start >= start && t.end <= end)
    .sort((a, b) => a.start! - b.start!);
  const out: React.ReactNode[] = [];
  let pos = start;
  terms.forEach((t, i) => {
    if (t.start! < pos) return;
    out.push(summary.slice(pos, t.start!));
    out.push(
      <button
        key={i}
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          onTerm(t, claim);
        }}
        title={`${t.kind} — jump to ${t.turn_ids.join(", ") || "transcript"}`}
        className="mx-0.5 inline-flex items-baseline gap-0.5 rounded border border-sky-400 bg-white px-1 font-semibold text-sky-800 underline decoration-sky-400 decoration-2 underline-offset-2 hover:bg-sky-100"
      >
        <span className="text-[10px] no-underline opacity-70">{kindIcon[t.kind]}</span>
        {summary.slice(t.start!, t.end!)}
      </button>,
    );
    pos = t.end!;
  });
  out.push(summary.slice(pos, end));
  return out;
}

export default function SummaryView({
  summary,
  claims,
  selected,
  onSelectClaim,
  onTerm,
}: {
  summary: string;
  claims: Claim[];
  selected: number | null;
  onSelectClaim: (index: number) => void;
  onTerm: (term: KeyTerm, claim: Claim) => void;
}) {
  const located = claims
    .map((c, i) => ({ c, i }))
    .filter(({ c }) => c.start !== null && c.end !== null)
    .sort((a, b) => a.c.start! - b.c.start!);

  const nodes: React.ReactNode[] = [];
  let pos = 0;
  for (const { c, i } of located) {
    if (c.start! < pos) continue;
    if (c.start! > pos) nodes.push(<span key={`gap-${i}`}>{summary.slice(pos, c.start!)}</span>);
    const problem = c.verdict !== "supported";
    nodes.push(
      <span
        key={`claim-${i}`}
        role="button"
        tabIndex={0}
        onClick={() => onSelectClaim(i)}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && onSelectClaim(i)}
        className={[
          "cursor-pointer rounded px-0.5 underline decoration-2 underline-offset-4 transition-colors",
          verdictSpan[c.verdict],
          problem ? "font-medium" : "",
          selected === i ? "outline outline-2 outline-offset-1 outline-slate-900" : "",
        ].join(" ")}
      >
        {renderClaim(summary, c, onTerm)}
      </span>,
    );
    pos = c.end!;
  }
  if (pos < summary.length) nodes.push(<span key="tail">{summary.slice(pos)}</span>);

  return <p className="text-[15px] leading-8 text-slate-900">{nodes}</p>;
}
