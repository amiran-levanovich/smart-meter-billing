from fastapi import FastAPI

app = FastAPI(title="WattWunder Billing")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
