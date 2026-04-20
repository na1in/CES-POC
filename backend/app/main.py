from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser, create_access_token, get_current_user
from app.database import engine, get_db
from app.models.user import User


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.connect() as conn:
        await conn.execute(select(1))
    yield
    await engine.dispose()


app = FastAPI(title="CES — Payment Resolution System", lifespan=lifespan)


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
