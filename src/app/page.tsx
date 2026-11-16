"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import CallList, { sortCalls } from "@/components/CallList";
import { ClaimCard, FactSheet, IssuesList, OmissionsList } from "@/components/Findings";
import SummaryView from "@/components/SummaryView";
import Transcript from "@/components/Transcript";
import { fetchCall, fetchCalls } from "@/lib/api";
import type { CallDetail, CallListItem, Claim, Focus, KeyTerm } from "@/lib/types";
import { verdictChip, verdictLabel, verdictOverall } from "@/lib/ui";

function Section({ title, count, tone, children }: { title: string; count?: number; tone?: string; children: React.ReactNode }) {
  return (
    <section className="mt-6">
      <h2 className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-500">
        {title}
        {count !== undefined && <span className={`rounded-full px-2 py-0.5 text-[11px] ${tone ?? "bg-slate-200 text-slate-700"}`}>{count}</span>}
      </h2>
      {children}
    </section>
  );
}

export default function Home() {
  const [calls, setCalls] = useState<CallListItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [call, setCall] = useState<CallDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedClaim, setSelectedClaim] = useState<number | null>(null);
  const [focus, setFocus] = useState<Focus | null>(null);

  const selectCall = useCallback((id: string) => {
    setSelectedId(id);
    setCall(null);
    setSelectedClaim(null);
    setFocus(null);
    if (typeof window !== "undefined") window.history.replaceState(null, "", `#${id}`);
  }, []);

  useEffect(() => {
    fetchCalls()
      .then((list) => {
        setCalls(list);
        const fromHash = window.location.hash.slice(1).toUpperCase();
        selectCall(list.some((c) => c.id === fromHash) ? fromHash : sortCalls(list)[0]?.id);
      })
      .catch((e) => setError(String(e)));
  }, [selectCall]);

  useEffect(() => {
    if (!selectedId) return;
    fetchCall(selectedId)
      .then(setCall)
      .catch((e) => setError(String(e)));
  }, [selectedId]);

  const analysis = call?.analysis ?? null;
  const ignoredTurns = useMemo(
    () => new Map((analysis?.ignored_turns ?? []).map((t) => [t.turn_id.toUpperCase(), t.reason])),
    [analysis],
  );

  const onSelectClaim = (i: number) => {
    setSelectedClaim(i);
    const c = analysis!.claims[i];
    setFocus({ turnIds: [...new Set(c.evidence.map((e) => e.turn_id))], quotes: c.evidence.map((e) => e.quote), source: `claim-${i}-${Date.now()}` });
  };

  const onTerm = (term: KeyTerm, claim: Claim) => {
    setSelectedClaim(analysis!.claims.indexOf(claim));
    const turnIds = term.turn_ids.length ? term.turn_ids : [...new Set(claim.evidence.map((e) => e.turn_id))];
    const quotes = claim.evidence.filter((e) => turnIds.includes(e.turn_id)).map((e) => e.quote);
    setFocus({ turnIds, quotes, source: `term-${term.text}-${Date.now()}` });
  };

  const onFocus = (f: Focus) => setFocus({ ...f, source: `${f.source}-${Date.now()}` });

  const problemCount = analysis ? analysis.claims.filter((c) => c.verdict !== "supported").length + (call?.rule_checks.length ?? 0) : 0;

  return (
    <div className="flex h-screen flex-col">
      <header className="flex items-center gap-3 border-b border-slate-200 bg-white px-4 py-2.5">
        <span className="text-base font-bold text-slate-900">SoundSense</span>
        <span className="text-sm text-slate-500">Call summary QA</span>
        <span className="ml-auto hidden flex-wrap items-center gap-1.5 text-[11px] md:flex">
          {(Object.keys(verdictLabel) as (keyof typeof verdictLabel)[]).map((v) => (
            <span key={v} className={`rounded px-1.5 py-0.5 font-semibold ${verdictChip[v]}`}>
              {verdictLabel[v]}
            </span>
          ))}
          <span className="rounded border border-sky-400 px-1.5 py-0.5 font-semibold text-sky-800">£ / date → click to jump</span>
        </span>
      </header>

      {error && <div className="bg-red-50 px-4 py-2 text-sm text-red-700">Could not load data: {error}</div>}

      {/* Mobile call picker */}
      <div className="border-b border-slate-200 bg-white px-4 py-2 lg:hidden">
        <select
          className="w-full rounded border border-slate-300 p-2 text-sm"
          value={selectedId ?? ""}
          onChange={(e) => selectCall(e.target.value)}
        >
          {sortCalls(calls).map((c) => (
            <option key={c.id} value={c.id}>
              {c.id} — {c.counts.critical} critical, {c.counts.major} major, {c.counts.minor} minor
            </option>
          ))}
        </select>
      </div>

      <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
        <aside className="hidden w-72 shrink-0 overflow-y-auto border-r border-slate-200 p-3 lg:block">
          <h2 className="mb-2 px-1 text-xs font-bold uppercase tracking-wider text-slate-500">Calls · most severe first</h2>
          <CallList calls={calls} selectedId={selectedId} onSelect={selectCall} />
        </aside>

        <main className="min-h-0 flex-1 overflow-y-auto p-4 lg:p-6">
          {!call && !error && <p className="text-sm text-slate-500">Loading…</p>}
          {call && (
            <>
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="font-mono text-xl font-bold text-slate-900">{call.id}</h1>
                {analysis && (
                  <span className={`rounded px-2 py-0.5 text-xs font-bold ${verdictOverall[analysis.overall_verdict].cls}`}>
                    {verdictOverall[analysis.overall_verdict].label}
                  </span>
                )}
                <span className="text-sm text-slate-500">
                  {call.call_weekday} {call.call_date} · {call.estimated_duration}
                </span>
              </div>
              {analysis && <p className="mt-2 text-[15px] font-medium text-slate-800">{analysis.headline}</p>}

              <Section title="Summary under review">
                <div className="rounded-lg border border-slate-200 bg-white p-4">
                  {analysis ? (
                    <SummaryView summary={call.summary} claims={analysis.claims} selected={selectedClaim} onSelectClaim={onSelectClaim} onTerm={onTerm} />
                  ) : (
                    <p className="text-[15px] leading-8">{call.summary}</p>
                  )}
                  <p className="mt-3 text-xs text-slate-500">
                    Click any highlighted part to see its evidence. Click a boxed amount, date or time to jump straight to where it was said.
                  </p>
                </div>
                {analysis && selectedClaim !== null && (
                  <div className="mt-3">
                    <ClaimCard claim={analysis.claims[selectedClaim]} onFocus={onFocus} active />
                  </div>
                )}
              </Section>

              {analysis ? (
                <>
                  <Section title="Problems in the summary" count={problemCount} tone={problemCount ? "bg-red-100 text-red-800" : "bg-emerald-100 text-emerald-800"}>
                    <IssuesList claims={analysis.claims} checks={call.rule_checks} onFocus={onFocus} onSelectClaim={onSelectClaim} selected={selectedClaim} />
                  </Section>

                  <Section
                    title="Important in the call, missing from the summary"
                    count={analysis.omissions.length}
                    tone={analysis.omissions.length ? "bg-orange-100 text-orange-800" : "bg-emerald-100 text-emerald-800"}
                  >
                    <OmissionsList omissions={analysis.omissions} onFocus={onFocus} />
                  </Section>

                  <Section title="Fact sheet · transcript vs summary">
                    <FactSheet facts={analysis.facts} onFocus={onFocus} />
                  </Section>

                  <Section title="All claims" count={analysis.claims.length}>
                    <div className="space-y-2">
                      {analysis.claims.map((c, i) => (
                        <ClaimCard key={i} claim={c} onFocus={onFocus} active={selectedClaim === i} onClick={() => onSelectClaim(i)} />
                      ))}
                    </div>
                  </Section>

                  <p className="mt-6 text-xs text-slate-400">
                    AI review: {call.analysis_meta?.model} ({call.analysis_meta?.effort} effort) · {analysis.evidence_stats.verified}/
                    {analysis.evidence_stats.total} quotes verified against the transcript · AI findings can be wrong — always check the
                    cited turns.
                  </p>
                </>
              ) : (
                <Section title="Rule checks" count={call.rule_checks.length}>
                  <IssuesList claims={[]} checks={call.rule_checks} onFocus={onFocus} onSelectClaim={() => {}} selected={null} />
                </Section>
              )}
            </>
          )}
        </main>

        <aside className="min-h-0 border-t border-slate-200 bg-slate-50 lg:w-[40%] lg:shrink-0 lg:border-l lg:border-t-0">
          <div className="flex h-full flex-col">
            <div className="flex items-center gap-2 border-b border-slate-200 bg-white px-4 py-2 text-xs">
              <span className="font-bold uppercase tracking-wider text-slate-500">Transcript</span>
              <span className="ml-auto flex gap-2">
                <span className="text-sky-700">■ Agent</span>
                <span className="text-slate-700">■ Customer</span>
                <span className="text-fuchsia-700">■ Third party</span>
              </span>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto p-3">
              {call && <Transcript turns={call.turns} focus={focus} ignoredTurns={ignoredTurns} />}
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
