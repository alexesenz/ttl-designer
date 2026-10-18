from fastapi import FastAPI

from .api.routes import router

app = FastAPI(title="TTL Designer", version="0.1.0")
app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
