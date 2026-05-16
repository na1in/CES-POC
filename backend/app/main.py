import asyncio
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser, create_access_token, get_current_user
from app.database import AsyncSessionLocal, engine, get_db
from app.models.user import User
from app.routers.analytics import router as analytics_router
from app.routers.annotations import router as annotations_router
from app.routers.approvals import router as approvals_router
from app.routers.config import router as config_router
from app.routers.documents import router as documents_router
from app.routers.governance import router as governance_router
from app.routers.payments import router as payments_router
from app.services.sla import run_sla_monitor


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.connect() as conn:
        await conn.execute(select(1))
    sla_task = asyncio.create_task(run_sla_monitor(AsyncSessionLocal))
    try:
        yield
    finally:
        sla_task.cancel()
        try:
            await sla_task
        except asyncio.CancelledError:
            pass
        await engine.dispose()


app = FastAPI(title="CES — Payment Resolution System", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(payments_router)
app.include_router(approvals_router)
app.include_router(annotations_router)
app.include_router(documents_router)
app.include_router(analytics_router)
app.include_router(governance_router)
app.include_router(config_router)


# ── Exception handlers ────────────────────────────────────────────────────────

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "internal_server_error"},
    )


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.post("/api/auth/token")
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    PoC login: username = user_id (e.g. USR-0001), password is not checked.
    Replace with real credential verification before any production use.
    """
    result = await db.execute(
        select(User).where(User.user_id == form.username, User.is_active == True)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    await db.execute(text("UPDATE users SET last_login = now() WHERE user_id = :uid"), {"uid": user.user_id})
    await db.commit()

    token = create_access_token(user.user_id, user.role)
    return {"access_token": token, "token_type": "bearer", "role": user.role, "name": user.name}


# ── Health + me ───────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/api/me")
async def me(current_user: CurrentUser = Depends(get_current_user)):
    return {"user_id": current_user.user_id, "name": current_user.name, "role": current_user.role}
