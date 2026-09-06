import os
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client
import httpx

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

security = HTTPBearer(auto_error=False)


def sign_up(email: str, password: str):
    response = supabase.auth.sign_up({"email": email, "password": password})
    return response


def sign_in(email: str, password: str):
    response = supabase.auth.sign_in_with_password({"email": email, "password": password})
    return response


def get_user(token: str):
    try:
        response = supabase.auth.get_user(token)
        return response.user
    except Exception:
        return None


def sign_out(token: str):
    try:
        # Supabase Python client sign_out works on the client's current session.
        # For a stateless server, we verify the token first, then acknowledge logout.
        user = get_user(token)
        if user is None:
            return False
        supabase.auth.sign_out()
        return True
    except Exception:
        return False


def confirm_user(user_id: str) -> bool:
    """Dev-only: auto-confirm a user via Supabase Admin API (requires service role key)."""
    if not SUPABASE_SERVICE_KEY:
        return False
    try:
        url = f"{SUPABASE_URL}/auth/v1/admin/users/{user_id}"
        headers = {
            "apikey": SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            "Content-Type": "application/json",
        }
        response = httpx.put(url, headers=headers, json={"email_confirm": True})
        return response.status_code == 200
    except Exception:
        return False


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    user = get_user(token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
