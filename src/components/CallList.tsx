"use client";

import type { CallListItem } from "@/lib/types";
import { verdictOverall } from "@/lib/ui";

export function sortCalls(calls: CallListItem[]) {
  return [...calls].sort(
    (a, b) =>
      b.counts.critical - a.counts.critical ||
      b.counts.major - a.counts.major ||
      b.counts.minor - a.counts.minor ||
      a.id.localeCompare(b.id),
  );
}

function Count({ n, cls, label }: { n: number; cls: string; label: string }) {
  if (!n) return null;
  return (
    <span title={`${n} ${label}`} className={`rounded px-1.5 text-[11px] font-bold ${cls}`}>
      {n} {label[0].toUpperCase()}
    </span>
  );
}

export default function CallList({
  calls,
  selectedId,
  onSelect,
}: {
  calls: CallListItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <ul className="space-y-1">
      {sortCalls(calls).map((c) => {
        const v = c.overall_verdict ? verdictOverall[c.overall_verdict] : null;
        const clean = !c.counts.critical && !c.counts.major && !c.counts.minor;
        return (
          <li key={c.id}>
            <button
              type="button"
              onClick={() => onSelect(c.id)}
              className={`w-full rounded-lg border px-3 py-2 text-left transition-colors ${
                selectedId === c.id ? "border-slate-900 bg-white shadow-sm" : "border-transparent hover:bg-white/70"
              }`}
            >
              <div className="flex items-center gap-1.5">
                <span className="font-mono text-sm font-semibold text-slate-900">{c.id}</span>
                <span className="ml-auto flex gap-1">
                  <Count n={c.counts.critical} cls="bg-red-600 text-white" label="critical" />
                  <Count n={c.counts.major} cls="bg-orange-500 text-white" label="major" />
                  <Count n={c.counts.minor} cls="bg-amber-200 text-amber-900" label="minor" />
                  {c.counts.to_check > 0 && (
                    <span title={`${c.counts.to_check} claims to check`} className="rounded bg-yellow-200 px-1.5 text-[11px] font-bold text-yellow-900">
                      {c.counts.to_check} ?
                    </span>
                  )}
                  {clean && v && !c.counts.to_check && <span className="rounded bg-emerald-100 px-1.5 text-[11px] font-bold text-emerald-800">✓ OK</span>}
                </span>
              </div>
              {c.headline && <p className="mt-1 line-clamp-2 text-xs text-slate-500">{c.headline}</p>}
              {!c.analysed && <p className="mt-1 text-xs italic text-slate-400">Not analysed yet</p>}
            </button>
          </li>
        );
      })}
    </ul>
  );
}
