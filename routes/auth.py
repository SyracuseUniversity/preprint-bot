from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr
from typing import Optional
import hashlib
import secrets
import binascii
from datetime import datetime, timedelta, timezone
from database import get_db_pool

router = APIRouter(prefix="/auth", tags=["auth"])

PBKDF2_ITER = 200_000
TOKEN_EXPIRY_HOURS = 24

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

async def _create_token(conn, user_id: int) -> str:
    token = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires_at = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS)
    await conn.execute(
        "INSERT INTO auth_tokens (user_id, token_hash, expires_at) VALUES ($1, $2, $3)",
        user_id, token_hash, expires_at
    )
    return token

async def _get_user_from_token(request: Request) -> dict:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    
    token = auth_header.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Empty token")
    
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT u.id, u.email, u.name
            FROM auth_tokens t
            JOIN users u ON u.id = t.user_id
            WHERE t.token_hash = $1 AND t.expires_at > NOW()
            """,
            token_hash
        )
    
    if not row:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return {"user_id": row["id"], "email": row["email"], "name": row["name"]}

@router.get("/me")
async def me(request: Request):
    """Return the authenticated user based on their token"""
    return await _get_user_from_token(request)

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
        
        token = await _create_token(conn, row['id'])
        
        return {
            "user_id": row['id'],
            "email": row['email'],
            "name": row['name'],
            "access_token": token
        }

@router.post("/register")
async def register(user: UserCreate):
    """Register a new user"""
    pool = await get_db_pool()
    
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT id FROM users WHERE lower(email) = lower($1)",
            user.email
        )
        
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        password_hash = _hash_password(user.password)
        row = await conn.fetchrow(
            "INSERT INTO users (email, name, password_hash) VALUES ($1, $2, $3) RETURNING id, email, name",
            user.email, user.name, password_hash
        )
        
        token = await _create_token(conn, row['id'])
        
        return {
            "user_id": row['id'],
            "email": row['email'],
            "name": row['name'],
            "access_token": token
        }

@router.post("/request-reset")
async def request_password_reset(request: PasswordResetRequest):
    """Request a password reset token"""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from config import get_settings
    settings = get_settings()

    pool = await get_db_pool()

    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT id, email FROM users WHERE lower(email) = lower($1)",
            request.email
        )

        if not user:
            return {"message": "If the email exists, a reset token has been sent"}

        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=1)

        await conn.execute(
            """
            INSERT INTO password_resets (user_id, token, expires_at)
            VALUES ($1, $2, $3)
            """,
            user['id'], token, expires_at
        )

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Preprint Bot — Password Reset"
        msg["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM_ADDRESS}>"
        msg["To"] = user['email']
        body = (
            f"Hello,\n\n"
            f"You requested a password reset for your Preprint Bot account.\n\n"
            f"Your reset token is:\n\n"
            f"{token}\n\n"
            f"Enter this token on the Reset Password page. It expires in 1 hour.\n\n"
            f"If you did not request this, you can ignore this email.\n\n"
            f"— Preprint Bot"
        )
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)
            smtp.sendmail(settings.EMAIL_FROM_ADDRESS, user['email'], msg.as_string())

    except Exception as e:
        # Log but don't expose SMTP errors to the caller
        import logging
        logging.getLogger(__name__).error(f"Password reset email failed: {e}")

    return {"message": "If the email exists, a reset token has been sent"}

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
async def verify_session(user_id: int, request: Request):
    """Verify a user session — requires a valid auth token matching the user_id"""
    # Enforce token auth so this can't be used for user enumeration (IDOR)
    authenticated = await _get_user_from_token(request)
    
    if authenticated["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Token does not match user_id")
    
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