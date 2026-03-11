from fastapi import FastAPI

from app.config import settings

app = FastAPI(title="CES - Payment Resolution System")


@app.get("/health")
async def health_check():
    return {"status": "ok"}
