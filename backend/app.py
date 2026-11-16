import json
from functools import lru_cache

from fastapi import FastAPI, HTTPException

from backend.calls import ROOT, load_calls
from backend.checks import run_checks
from backend.verify import enrich_analysis

ANALYSIS_DIR = ROOT / "analysis"
SEVERITIES = ("critical", "major", "minor")

app = FastAPI(title="SoundSense Summary Review API", docs_url="/api/docs", openapi_url="/api/openapi.json")


@lru_cache(maxsize=64)
def load_analysis(call_id: str) -> dict | None:
    path = ANALYSIS_DIR / f"{call_id}.json"
    if not path.exists():
        return None
    result = json.loads(path.read_text(encoding="utf-8"))
    result["analysis"] = enrich_analysis(load_calls()[call_id], result["analysis"])
    return result


def severity_counts(call_id: str) -> dict:
    """Count issues across AI claims, omissions and rule checks."""
    counts = {s: 0 for s in SEVERITIES}
    result = load_analysis(call_id)
    if result:
        a = result["analysis"]
        for c in a["claims"]:
            if c["verdict"] != "supported" and c["severity"] in counts:
                counts[c["severity"]] += 1
        for o in a["omissions"]:
            if o["severity"] in counts:
                counts[o["severity"]] += 1
    for chk in run_checks(load_calls()[call_id]):
        counts[chk["severity"]] += 1
    return counts


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/calls")
def list_calls() -> list[dict]:
    out = []
    for cid, c in load_calls().items():
        result = load_analysis(cid)
        out.append(
            {
                "id": cid,
                "call_date": c["call_date"],
                "estimated_duration": c["estimated_duration"],
                "analysed": result is not None,
                "overall_verdict": result["analysis"]["overall_verdict"] if result else None,
                "headline": result["analysis"]["headline"] if result else None,
                "counts": severity_counts(cid),
            }
        )
    return out


@app.get("/api/calls/{call_id}")
def get_call(call_id: str) -> dict:
    call_id = call_id.upper()
    call = load_calls().get(call_id)
    if call is None:
        raise HTTPException(status_code=404, detail=f"Unknown call {call_id}")
    result = load_analysis(call_id)
    return {
        **{k: v for k, v in call.items() if k != "transcript"},
        "rule_checks": run_checks(call),
        "analysis": result["analysis"] if result else None,
        "analysis_meta": {k: v for k, v in result.items() if k != "analysis"} if result else None,
        "counts": severity_counts(call_id),
    }
