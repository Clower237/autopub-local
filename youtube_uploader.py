# youtube_uploader.py — par utilisateur + compat Render
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Union

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# Emplacement des tokens (persistant si APP_DATA_DIR défini)
DATA_DIR = Path(os.getenv("APP_DATA_DIR", ".")).resolve()
TOKENS_DIR = (DATA_DIR / "tokens").resolve()
TOKENS_DIR.mkdir(parents=True, exist_ok=True)

def _user_tokens_dir(user_id: int) -> Path:
    p = TOKENS_DIR / str(user_id)
    p.mkdir(parents=True, exist_ok=True)
    return p

def _credentials_for_user(user_id: int) -> Credentials:
    tdir = _user_tokens_dir(user_id)
    client_secret = tdir / "client_secret.json"
    token_path = tdir / "youtube_token.json"

    if not client_secret.exists():
        raise FileNotFoundError("client_secret.json manquant pour ce compte")

    creds: Optional[Credentials] = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secret), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as f:
            f.write(creds.to_json())

    return creds

def get_youtube_for_user(user_id: int):
    creds = _credentials_for_user(user_id)
    return build("youtube", "v3", credentials=creds)

def set_thumbnail(youtube, video_id: str, thumb_path: str):
    media = MediaFileUpload(thumb_path)
    youtube.thumbnails().set(videoId=video_id, media_body=media).execute()

def upload_to_youtube(
    user_id: int,
    video_path: str,
    title: str,
    description: str = "",
    tags: Optional[List[str]] = None,
    publish_time: Optional[Union[datetime, str]] = None,
    categoryId: str = "22",
    made_for_kids: bool = False,
    thumbnail_path: Optional[str] = None,
) -> str:
    youtube = get_youtube_for_user(user_id)
    if not title:
        title = "Sans titre"

    body = {
        "snippet": {
            "title": title[:100],
            "description": (description or "")[:4900],  # garde large mais < 5000
            "tags": tags or [],
            "categoryId": categoryId,
        },
        "status": {
            "selfDeclaredMadeForKids": made_for_kids,
        },
    }

    if publish_time is None:
        body["status"]["privacyStatus"] = "public"
    else:
        if isinstance(publish_time, datetime):
            pt = publish_time.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        else:
            pt = str(publish_time)
        body["status"]["privacyStatus"] = "private"
        body["status"]["publishAt"] = pt  # RFC3339 UTC

    media = MediaFileUpload(video_path, mimetype="video/*", chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    try:
        while response is None:
            status, response = request.next_chunk()
        video_id = response.get("id")

        if thumbnail_path and os.path.exists(thumbnail_path):
            try:
                set_thumbnail(youtube, video_id, thumbnail_path)
            except Exception:
                pass

        return video_id

    except HttpError:
        raise
