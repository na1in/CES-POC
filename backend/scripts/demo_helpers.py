"""
Shared helpers for CES demo scripts.
Usage: imported by demo_*.py scripts.
"""
import sys
import httpx

BASE_URL = "http://localhost:8000"

# Seed user IDs
USR_ANALYST      = "USR-0001"   # Priya Sharma
USR_INVESTIGATOR = "USR-0002"   # Damien Torres
USR_DIRECTOR     = "USR-0003"   # Lorraine Chen
USR_ADMIN        = "USR-0004"   # Marcus Webb


def get_token(user_id: str) -> str:
    """PoC login: username = user_id, password is not checked."""
    resp = httpx.post(
        f"{BASE_URL}/api/auth/token",
        data={"username": user_id, "password": "demo"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if resp.status_code != 200:
        print(f"  [ERROR] Login failed for {user_id}: {resp.text}")
        sys.exit(1)
    return resp.json()["access_token"]


def api(
    method: str,
    path: str,
    token: str,
    json: dict | None = None,
    expected: int = 200,
) -> dict | None:
    """Make an authenticated API call. Exits on unexpected status."""
    resp = httpx.request(
        method.upper(),
        f"{BASE_URL}{path}",
        headers={"Authorization": f"Bearer {token}"},
        json=json,
        timeout=30.0,
    )
    if resp.status_code != expected:
        print(f"  [ERROR] {method.upper()} {path} → {resp.status_code}: {resp.text}")
        sys.exit(1)
    try:
        return resp.json()
    except Exception:
        return None


def section(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


def ok(msg: str) -> None:
    print(f"  ✓  {msg}")


def info(msg: str) -> None:
    print(f"     {msg}")
