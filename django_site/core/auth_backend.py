"""
Custom authentication backend for the existing preprint_bot users table.

The FastAPI backend stores passwords as:
    pbkdf2$<iterations>$<salt_hex>$<hash_hex>

This backend verifies against that format and stores the authenticated
PBUser instance on the Django session (not Django's built-in User model).
"""

import hashlib
import binascii
import secrets

from .models import PBUser

PBKDF2_ITER = 200_000


def hash_password(password: str) -> str:
    """Hash a password using the same scheme as the FastAPI backend."""
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITER)
    return "pbkdf2$%d$%s$%s" % (
        PBKDF2_ITER,
        binascii.hexlify(salt).decode(),
        binascii.hexlify(dk).decode(),
    )


def verify_password(password: str, stored: str) -> bool:
    """Verify a password against a stored PBKDF2 hash."""
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


class PreprintBotBackend:
    """
    Authenticate against the existing preprint_bot ``users`` table.

    Usage in views::

        from core.auth_backend import authenticate_pbuser
        user = authenticate_pbuser(request, email, password)
    """

    def authenticate(self, request, email=None, password=None):
        """Return a PBUser if credentials are valid, else None."""
        if email is None or password is None:
            return None
        try:
            pb_user = PBUser.objects.get(email__iexact=email)
        except PBUser.DoesNotExist:
            return None

        if verify_password(password, pb_user.password_hash):
            return pb_user
        return None

    def get_user(self, user_id):
        """Retrieve PBUser by pk – called by session middleware."""
        try:
            return PBUser.objects.get(pk=user_id)
        except PBUser.DoesNotExist:
            return None


# ── Convenience helpers for views ──────────────────────────────────────────

def authenticate_pbuser(request, email: str, password: str):
    """Thin wrapper so views don't import the backend directly."""
    backend = PreprintBotBackend()
    return backend.authenticate(request, email=email, password=password)


def login_pbuser(request, pb_user: PBUser):
    """Store the PBUser id on the Django session."""
    request.session["pbuser_id"] = pb_user.pk
    request.session["pbuser_email"] = pb_user.email
    request.session["pbuser_name"] = pb_user.name or ""


def logout_pbuser(request):
    """Clear PBUser data from the session."""
    request.session.flush()


def get_current_pbuser(request) -> PBUser | None:
    """Return the logged-in PBUser from the session, or None."""
    uid = request.session.get("pbuser_id")
    if uid is None:
        return None
    try:
        return PBUser.objects.get(pk=uid)
    except PBUser.DoesNotExist:
        request.session.flush()
        return None
