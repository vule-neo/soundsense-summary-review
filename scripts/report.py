"""Print review statistics for the saved analysis (the numbers quoted in the README).

Usage:
    python scripts/report.py                      # per-call counts + totals
    python scripts/report.py --compare 1eb8ae0    # also compare with an earlier analysis commit
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.app import get_call, list_calls  # noqa: E402
from backend.calls import load_calls  # noqa: E402
from backend.verify import enrich_analysis  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--compare", help="git commit holding an earlier analysis/ to compare against")
    args = parser.parse_args()

    totals = {"claims": 0, "verified": 0, "to_check": 0, "problems": 0, "evidence": 0, "evidence_ok": 0}
    print(f"{'call':<9} {'crit':>4} {'major':>5} {'minor':>5} {'check':>5} {'green':>5}  headline")
    for item in list_calls():
        d = get_call(item["id"])
        a, k = d["analysis"], d["counts"]
        totals["claims"] += len(a["claims"])
        totals["verified"] += k["verified"]
        totals["to_check"] += k["to_check"]
        totals["problems"] += sum(c["verdict"] not in ("supported", "uncertain") for c in a["claims"])
        totals["evidence"] += a["evidence_stats"]["total"]
        totals["evidence_ok"] += a["evidence_stats"]["verified"]
        print(f"{item['id']:<9} {k['critical']:>4} {k['major']:>5} {k['minor']:>5} {k['to_check']:>5} {k['verified']:>5}  {a['headline'][:90]}")
    print("\nTotals:", json.dumps(totals))

    if args.compare:
        calls = load_calls()
        old_claims = old_green = to_yellow = to_red = 0
        for cid in calls:
            raw = subprocess.check_output(["git", "show", f"{args.compare}:analysis/{cid}.json"], cwd=ROOT)
            old = enrich_analysis(calls[cid], json.loads(raw.decode("utf-8"))["analysis"])
            old_claims += len(old["claims"])
            old_green += sum(c["verdict"] == "supported" for c in old["claims"])
            for nc in get_call(cid)["analysis"]["claims"]:
                if nc["verdict"] == "supported" or nc["start"] is None:
                    continue
                overlap = [oc for oc in old["claims"] if oc["start"] is not None and oc["start"] < nc["end"] and oc["end"] > nc["start"]]
                if overlap and all(oc["verdict"] == "supported" for oc in overlap):
                    if nc["verdict"] == "uncertain":
                        to_yellow += 1
                    else:
                        to_red += 1
        print(
            f"\nCompared with {args.compare}: {old_green}/{old_claims} claims were green then. "
            f"Parts of summaries that were green then and are not green now: {to_yellow + to_red} "
            f"({to_yellow} now 'Needs check', {to_red} now a definite problem)."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
