from fastapi import FastAPI, HTTPException

from backend.calls import load_calls

app = FastAPI(title="SoundSense Summary Review API", docs_url="/api/docs", openapi_url="/api/openapi.json")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/calls")
def list_calls() -> list[dict]:
    return [
        {"id": c["id"], "call_date": c["call_date"], "estimated_duration": c["estimated_duration"]}
        for c in load_calls().values()
    ]


@app.get("/api/calls/{call_id}")
def get_call(call_id: str) -> dict:
    call = load_calls().get(call_id.upper())
    if call is None:
        raise HTTPException(status_code=404, detail=f"Unknown call {call_id}")
    return {k: v for k, v in call.items() if k != "transcript"}
