"use client";

import { useEffect, useRef } from "react";
import type { Focus, Turn } from "@/lib/types";

const roleStyle: Record<Turn["role"], { label: string; cls: string }> = {
  agent: { label: "text-sky-700", cls: "border-l-sky-400" },
  customer: { label: "text-slate-800", cls: "border-l-slate-400" },
  third_party: { label: "text-fuchsia-700", cls: "border-l-fuchsia-500" },
  note: { label: "text-slate-500", cls: "border-l-slate-200" },
  unclear: { label: "text-slate-400", cls: "border-l-slate-200" },
  other: { label: "text-slate-700", cls: "border-l-slate-300" },
};

/** Wrap occurrences of any quote inside text with <mark>. Case/quote-insensitive. */
function highlight(text: string, quotes: string[]) {
  const norm = (s: string) => s.replace(/[‘’]/g, "'").toLowerCase();
  const hay = norm(text);
  const ranges: [number, number][] = [];
  for (const q of quotes) {
    const needle = norm(q).trim().replace(/[.\s]+$/, "");
    if (needle.length < 2) continue;
    const i = hay.indexOf(needle);
    if (i >= 0) ranges.push([i, i + needle.length]);
  }
  if (!ranges.length) return text;
  ranges.sort((a, b) => a[0] - b[0]);
  const parts: React.ReactNode[] = [];
  let pos = 0;
  ranges.forEach(([s, e], k) => {
    if (s < pos) return;
    parts.push(text.slice(pos, s));
    parts.push(
      <mark key={k} className="rounded bg-yellow-300 px-0.5 text-slate-900">
        {text.slice(s, e)}
      </mark>,
    );
    pos = e;
  });
  parts.push(text.slice(pos));
  return parts;
}

export default function Transcript({
  turns,
  focus,
  ignoredTurns,
}: {
  turns: Turn[];
  focus: Focus | null;
  ignoredTurns: Map<string, string>;
}) {
  const refs = useRef<Record<string, HTMLDivElement | null>>({});

  useEffect(() => {
    const first = focus?.turnIds[0];
    if (first) refs.current[first]?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [focus]);

  const focused = new Set(focus?.turnIds ?? []);

  return (
    <div className="space-y-1.5">
      {turns.map((t) => {
        const isFocused = focused.has(t.id);
        const ignoredReason = ignoredTurns.get(t.id);
        const style = roleStyle[t.role];
        return (
          <div
            key={`${t.id}-${focus?.source ?? ""}`}
            id={`turn-${t.id}`}
            ref={(el) => {
              refs.current[t.id] = el;
            }}
            className={[
              "rounded-md border-l-4 px-3 py-2 text-sm transition-colors",
              style.cls,
              isFocused ? "turn-flash bg-yellow-50 ring-2 ring-yellow-400" : "bg-white",
              ignoredReason || t.role === "note" ? "opacity-60" : "",
            ].join(" ")}
          >
            <div className="mb-0.5 flex items-center gap-2 text-xs">
              <span className="font-mono font-semibold text-slate-500">{t.id}</span>
              <span className="text-slate-400">{t.time}</span>
              <span className={`font-semibold ${style.label}`}>{t.speaker}</span>
              {t.role === "third_party" && (
                <span className="rounded bg-fuchsia-100 px-1.5 text-[10px] font-semibold uppercase text-fuchsia-700">
                  third party
                </span>
              )}
              {ignoredReason && (
                <span
                  className="rounded bg-slate-200 px-1.5 text-[10px] font-semibold uppercase text-slate-600"
                  title={ignoredReason}
                >
                  ignored · ASR noise
                </span>
              )}
            </div>
            <p className={`leading-relaxed ${t.role === "note" ? "italic text-slate-500" : "text-slate-800"} ${ignoredReason ? "line-through" : ""}`}>
              {isFocused ? highlight(t.text, focus?.quotes ?? []) : t.text}
            </p>
          </div>
        );
      })}
    </div>
  );
}
