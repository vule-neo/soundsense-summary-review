"""Run the Claude audit over calls and save results to analysis/<CALL-ID>.json.

Usage:
    python scripts/analyze.py CALL-003 CALL-018   # specific calls
    python scripts/analyze.py --all               # every call missing a result
    python scripts/analyze.py --all --force       # re-run everything
Requires ANTHROPIC_API_KEY (read from .env).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import anthropic  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

from backend.analyzer import analyze_call  # noqa: E402
from backend.calls import load_calls  # noqa: E402

OUT_DIR = ROOT / "analysis"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("call_ids", nargs="*")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    calls = load_calls()
    ids = list(calls) if args.all else [c.upper() for c in args.call_ids]
    if not ids:
        parser.error("give call IDs or --all")
    unknown = [i for i in ids if i not in calls]
    if unknown:
        parser.error(f"unknown call IDs: {unknown}")
    if not args.force:
        ids = [i for i in ids if not (OUT_DIR / f"{i}.json").exists()]

    OUT_DIR.mkdir(exist_ok=True)
    client = anthropic.Anthropic()
    failures = 0

    def run(call_id: str) -> tuple[str, dict]:
        return call_id, analyze_call(calls[call_id], client)

    started = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(run, i): i for i in ids}
        for fut in as_completed(futures):
            call_id = futures[fut]
            try:
                _, result = fut.result()
            except Exception as exc:  # report and continue with the other calls
                failures += 1
                print(f"FAIL {call_id}: {type(exc).__name__}: {exc}", flush=True)
                continue
            path = OUT_DIR / f"{call_id}.json"
            path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            a = result["analysis"]
            print(
                f"OK   {call_id}: {a['overall_verdict']:<16} claims={len(a['claims'])} "
                f"omissions={len(a['omissions'])} out_tokens={result['usage']['output_tokens']}",
                flush=True,
            )
    print(f"done: {len(ids) - failures} ok, {failures} failed in {time.time() - started:.0f}s")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
