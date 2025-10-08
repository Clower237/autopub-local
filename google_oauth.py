import os
from typing import List
from google_auth_oauthlib.flow import Flow
from sqlalchemy.orm import Session
from models import OAuthToken

GOOGLE_CLIENT_ID = os.environ["GOOGLE_OAUTH_CLIENT_ID"]
GOOGLE_CLIENT_SECRET = os.environ["GOOGLE_OAUTH_CLIENT_SECRET"]
REDIRECT_BASE = os.environ["OAUTH_REDIRECT_BASE"].rstrip("/")
DRIVE_SCOPES: List[str] = ["https://www.googleapis.com/auth/drive.file"]

_CLIENT_CONFIG = {
    "web": {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": [f"{REDIRECT_BASE}/auth/drive/callback"],
    }
}

def _new_flow() -> Flow:
    return Flow.from_client_config(
        _CLIENT_CONFIG, scopes=DRIVE_SCOPES, redirect_uri=f"{REDIRECT_BASE}/auth/drive/callback",
    )

def drive_start_url(user_id: int) -> str:
    flow = _new_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline", include_granted_scopes="true", prompt="consent", state=str(user_id),
    )
    return auth_url

def finish_drive_oauth(db: Session, code: str, state: str) -> None:
    uid = int(state)
    flow = _new_flow()
    flow.fetch_token(code=code)
    creds = flow.credentials

    tok = db.query(OAuthToken).filter_by(user_id=uid, provider="drive").first()
    if not tok:
        tok = OAuthToken(user_id=uid, provider="drive")
        db.add(tok)

    tok.access_token = creds.token
    tok.refresh_token = getattr(creds, "refresh_token", None) or tok.refresh_token
    tok.scopes = " ".join(creds.scopes or DRIVE_SCOPES)
    tok.expiry = getattr(creds, "expiry", None)
    db.commit()
