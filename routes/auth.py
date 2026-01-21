from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional
import hashlib
import secrets
import binascii
from datetime import datetime, timedelta
from database import get_db_pool

router = APIRouter(prefix="/auth", tags=["auth"])

PBKDF2_ITER = 200_000

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None

class PasswordReset(BaseModel):
    token: str
    new_password: str

class PasswordResetRequest(BaseModel):
    email: EmailStr

def _hash_password(password: str) -> str:
    """Hash password using PBKDF2"""
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITER)
    return "pbkdf2$%d$%s$%s" % (PBKDF2_ITER, binascii.hexlify(salt).decode(), binascii.hexlify(dk).decode())

def _verify_password(password: str, stored: str) -> bool:
    """Verify password against stored hash"""
    try:
        if not stored:
            return False
        scheme, iters, salt_hex, hash_hex = stored.split("$", 3)
        if scheme != "pbkdf2":
            return False
        iters = int(iters)
        salt = binascii.unhexlify(salt_hex)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iters)
        return binascii.hexlify(dk).decode() == hash_hex
    except Exception:
        return False

@router.post("/login")
async def login(credentials: UserLogin):
    """Authenticate user and return user info"""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, email, name, password_hash FROM users WHERE lower(email) = lower($1)",
            credentials.email
        )
        
        if not row:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        if not row['password_hash']:
            raise HTTPException(status_code=401, detail="Password not set. Please use password reset.")
        
        if not _verify_password(credentials.password, row['password_hash']):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        return {
            "user_id": row['id'],
            "email": row['email'],
            "name": row['name']
        }

@router.post("/register")
async def register(user: UserCreate):
    """Register a new user"""
    pool = await get_db_pool()
    
    async with pool.acquire() as conn:
        # Check if user exists
        existing = await conn.fetchrow(
            "SELECT id FROM users WHERE lower(email) = lower($1)",
            user.email
        )
        
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create user with hashed password
        password_hash = _hash_password(user.password)
        row = await conn.fetchrow(
            "INSERT INTO users (email, name, password_hash) VALUES ($1, $2, $3) RETURNING id, email, name",
            user.email, user.name, password_hash
        )
        
        return {
            "user_id": row['id'],
            "email": row['email'],
            "name": row['name']
        }

@router.post("/request-reset")
async def request_password_reset(request: PasswordResetRequest):
    """Request a password reset token"""
    pool = await get_db_pool()
    
    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT id, email FROM users WHERE lower(email) = lower($1)",
            request.email
        )
        
        if not user:
            # Don't reveal if user exists
            return {"message": "If the email exists, a reset token has been sent"}
        
        # Create reset token
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=1)
        
        await conn.execute(
            """
            INSERT INTO password_resets (user_id, token, expires_at)
            VALUES ($1, $2, $3)
            """,
            user['id'], token, expires_at
        )
        
        # TODO: Send email with token
        # For now, return it for testing (REMOVE in production!)
        return {
            "message": "Reset token created",
            "token": token,
            "email": user['email']
        }

@router.post("/reset-password")
async def reset_password(reset: PasswordReset):
    """Reset password using a valid token"""
    pool = await get_db_pool()
    
    async with pool.acquire() as conn:
        # Find valid token
        row = await conn.fetchrow(
            """
            SELECT pr.id, pr.user_id, pr.expires_at, pr.used_at
            FROM password_resets pr
            WHERE pr.token = $1
            """,
            reset.token
        )
        
        if not row:
            raise HTTPException(status_code=400, detail="Invalid or expired token")
        
        if row['used_at']:
            raise HTTPException(status_code=400, detail="Token already used")
        
        if row['expires_at'] < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Token expired")
        
        # Update password
        new_hash = _hash_password(reset.new_password)
        await conn.execute(
            "UPDATE users SET password_hash = $1 WHERE id = $2",
            new_hash, row['user_id']
        )
        
        # Mark token as used
        await conn.execute(
            "UPDATE password_resets SET used_at = CURRENT_TIMESTAMP WHERE id = $1",
            row['id']
        )
        
        return {"message": "Password updated successfully"}

@router.get("/verify/{user_id}")
async def verify_session(user_id: int):
    """Verify a user session by ID"""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, email, name FROM users WHERE id = $1",
            user_id
        )
        
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "user_id": row['id'],
            "email": row['email'],
            "name": row['name']
        }