"""
ORCID OAuth2 helpers.

ORCID uses standard OAuth2.  The token exchange response includes the
ORCID iD and display name directly.  After authentication we attempt to
fetch the user's email via the ORCID public API — this only returns
emails the user has marked as public on their ORCID record.

Sandbox (development):  https://sandbox.orcid.org
Production:             https://orcid.org

Register an app at https://orcid.org/developer-tools to get a client ID
and secret.  Set the redirect URI to:
    https://your-domain/auth/orcid/callback/
"""

import logging

from django.conf import settings as django_settings

logger = logging.getLogger(__name__)

# ── URLs ──────────────────────────────────────────────────────────────────

ORCID_SANDBOX_BASE = "https://sandbox.orcid.org"
ORCID_PRODUCTION_BASE = "https://orcid.org"

# The public API is used to read user records after authentication
ORCID_SANDBOX_API = "https://pub.sandbox.orcid.org/v3.0"
ORCID_PRODUCTION_API = "https://pub.orcid.org/v3.0"


def _base_url():
    if getattr(django_settings, "ORCID_SANDBOX", False):
        return ORCID_SANDBOX_BASE
    return ORCID_PRODUCTION_BASE


def _api_url():
    if getattr(django_settings, "ORCID_SANDBOX", False):
        return ORCID_SANDBOX_API
    return ORCID_PRODUCTION_API


def is_configured():
    """Return True if ORCID client credentials are present in settings."""
    return bool(getattr(django_settings, "ORCID_CLIENT_ID", ""))


def get_authorize_url(redirect_uri, state=None):
    """Build the ORCID OAuth2 authorization URL."""
    base = _base_url()
    url = (
        f"{base}/oauth/authorize"
        f"?client_id={django_settings.ORCID_CLIENT_ID}"
        f"&response_type=code"
        f"&scope=/authenticate"
        f"&redirect_uri={redirect_uri}"
    )
    if state:
        url += f"&state={state}"
    return url


def exchange_code(code, redirect_uri):
    """Exchange an authorization code for an access token.

    Returns a dict with keys: orcid, name, access_token
    (or None on failure).

    The ORCID token endpoint returns the iD and name in the response
    body itself.
    """
    import requests as http_requests

    base = _base_url()
    try:
        resp = http_requests.post(
            f"{base}/oauth/token",
            data={
                "client_id": django_settings.ORCID_CLIENT_ID,
                "client_secret": django_settings.ORCID_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
            },
            headers={"Accept": "application/json"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "orcid": data.get("orcid", ""),
            "name": data.get("name", ""),
            "access_token": data.get("access_token", ""),
        }
    except Exception:
        logger.exception("ORCID token exchange failed")
        return None


def fetch_email(orcid_id, access_token):
    """Fetch the user's email from the ORCID public API.

    Only returns emails the user has marked as public on their ORCID
    record.  Returns the first verified email, or the first available
    email, or None if no public emails exist.
    """
    import requests as http_requests

    api = _api_url()
    try:
        resp = http_requests.get(
            f"{api}/{orcid_id}/email",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        emails = data.get("email", [])
        if not emails:
            return None

        # Prefer a verified email
        for entry in emails:
            if entry.get("verified") and entry.get("email"):
                return entry["email"].strip().lower()

        # Fall back to first available email
        first = emails[0].get("email", "")
        return first.strip().lower() if first else None

    except Exception:
        logger.exception("Failed to fetch email from ORCID for %s", orcid_id)
        return None
