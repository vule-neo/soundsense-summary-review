from fastapi import FastAPI

app = FastAPI(title="SoundSense Summary Review API", docs_url="/api/docs", openapi_url="/api/openapi.json")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
