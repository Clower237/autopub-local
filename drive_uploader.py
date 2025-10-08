import os, mimetypes
from typing import Optional
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from sqlalchemy.orm import Session
from database import SessionLocal
from models import OAuthToken, User

def _creds_from_db(db: Session, user_id: int) -> Optional[Credentials]:
    tok = db.query(OAuthToken).filter_by(user_id=user_id, provider="drive").first()
    if not tok:
        return None
    scopes = (tok.scopes or "https://www.googleapis.com/auth/drive.file").split()
    return Credentials(
        token=tok.access_token,
        refresh_token=tok.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["GOOGLE_OAUTH_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_OAUTH_CLIENT_SECRET"],
        scopes=scopes,
    )

def _get_or_create_folder(service, name: str, parent_id: Optional[str] = None) -> str:
    q = f"mimeType='application/vnd.google-apps.folder' and name='{name.replace(\"'\",\"\\'\")}' and trashed=false"
    if parent_id:
        q += f" and '{parent_id}' in parents"
    res = service.files().list(q=q, fields="files(id,name)").execute()
    files = res.get("files", [])
    if files:
        return files[0]["id"]
    body = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        body["parents"] = [parent_id]
    folder = service.files().create(body=body, fields="id").execute()
    return folder["id"]

def upload_for_user(user_id: int, local_path: str) -> Optional[str]:
    db = SessionLocal()
    try:
        creds = _creds_from_db(db, user_id)
        if not creds:
            return None
        service = build("drive", "v3", credentials=creds, cache_discovery=False)
        user = db.query(User).get(user_id)
        root = _get_or_create_folder(service, "autopub-videos")
        user_name = (user.email if user else f"user-{user_id}").replace("/", "_")
        user_folder = _get_or_create_folder(service, user_name, root)

        fname = os.path.basename(local_path)
        mime = mimetypes.guess_type(fname)[0] or "video/mp4"
        media = MediaFileUpload(local_path, mimetype=mime, resumable=True)
        meta = {"name": fname, "parents": [user_folder]}

        file = service.files().create(body=meta, media_body=media, fields="id,webViewLink,webContentLink").execute()
        return file.get("webViewLink") or file.get("webContentLink")
    finally:
        db.close()
