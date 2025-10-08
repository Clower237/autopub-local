import os, io, csv, zipfile, uuid, re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import User, Job
from auth import get_password_hash, verify_password, create_access_token, get_current_user
from worker import ensure_worker_running, poke_worker
from schemas import JobOut
from fastapi import Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from database import init_db, get_db
from auth import get_current_user
import google_oauth
from worker import ensure_worker_running

# ---------------------------------------------------------------------
# Boot & Dossiers (compat Render)
# ---------------------------------------------------------------------
load_dotenv()

# Base de données
Base.metadata.create_all(bind=engine)

# Répertoire de données (persistant sur Render si APP_DATA_DIR=/data)
DATA_DIR = Path(os.getenv("APP_DATA_DIR", ".")).resolve()

STATIC_DIR = Path("static").resolve()               # assets UI
STORAGE_DIR = (DATA_DIR / "storage").resolve()      # audio / video / thumbs
TOKENS_DIR  = (DATA_DIR / "tokens").resolve()       # OAuth Google par utilisateur

# Création des dossiers
STATIC_DIR.mkdir(exist_ok=True)
(STORAGE_DIR / "thumbs").mkdir(parents=True, exist_ok=True)
(STORAGE_DIR / "audio").mkdir(parents=True, exist_ok=True)
(STORAGE_DIR / "video").mkdir(parents=True, exist_ok=True)
TOKENS_DIR.mkdir(exist_ok=True)

app = FastAPI(title="AutoPub Local (gratuit)")

# Servir l'UI et les fichiers
app.mount("/ui", StaticFiles(directory=str(STATIC_DIR), html=True), name="ui")
app.mount("/storage", StaticFiles(directory=str(STORAGE_DIR)), name="storage")

# Page d'accueil -> index.html (unique)
@app.get("/", response_class=HTMLResponse)
def root():
    return FileResponse(str(STATIC_DIR / "index.html"))

# Favicon (pour que les navigateurs qui appellent /favicon.ico le trouvent)
@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    ico = STATIC_DIR / "favicon.ico"
    png = STATIC_DIR / "favicon.png"
    if ico.exists():
        return FileResponse(str(ico))
    if png.exists():
        return FileResponse(str(png))
    return Response(status_code=204)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# Lancer le worker (thread)
ensure_worker_running()

# ---------------------------------------------------------------------
# Schemas Auth
# ---------------------------------------------------------------------
class TokenOut(BaseModel):
    access_token: str
    token_type: str

class RegisterIn(BaseModel):
    email: EmailStr
    password: str

class LoginIn(BaseModel):
    email: EmailStr
    password: str

# ---------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------
def pick_voice(category: str, explicit: Optional[str] = None) -> str:
    if explicit and explicit.strip():
        return explicit.strip()
    mapping = {
        "femme": "fr-FR-DeniseNeural",
        "homme": "fr-FR-HenriNeural",
        "enfant-fille": "en-GB-MaisieNeural",
        "enfant-garcon": "en-US-AndrewMultilingualNeural",
    }
    return mapping.get((category or "").strip().lower(), "fr-FR-DeniseNeural")

def safe_filename(name: str) -> str:
    base = re.sub(r"[^A-Za-z0-9._-]", "_", (name or "").strip())
    return base or f"file_{uuid.uuid4().hex[:8]}"

# ---------------------------------------------------------------------
# Profil / YouTube creds (par utilisateur)
# ---------------------------------------------------------------------
@app.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email}

@app.get("/me/youtube/credentials")
def youtube_credentials_status(user: User = Depends(get_current_user)):
    user_dir = TOKENS_DIR / str(user.id)
    client_secret = (user_dir / "client_secret.json").exists()
    token_file   = (user_dir / "youtube_token.json").exists()
    return {"client_secret": client_secret, "token_present": token_file}

@app.post("/me/youtube/credentials")
async def upload_youtube_client_secret(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    if not file.filename.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="Fichier attendu: .json")
    user_dir = TOKENS_DIR / str(user.id)
    user_dir.mkdir(parents=True, exist_ok=True)
    dest = user_dir / "client_secret.json"
    with open(dest, "wb") as f:
        f.write(await file.read())
    # on supprime l'ancien token pour forcer un nouveau consentement propre
    old_token = user_dir / "youtube_token.json"
    if old_token.exists():
        old_token.unlink()
    return {"ok": True}

# ---------------------------------------------------------------------
# Bulk (CSV + ZIP)
# Colonnes: title,description,tags,script_text,voice_category,speed,publish_iso,thumbnail
# ---------------------------------------------------------------------
STORAGE_THUMBS = str(STORAGE_DIR / "thumbs")

@app.post("/bulk")
def bulk_create_jobs(
    csv_file: UploadFile = File(...),
    thumbs_zip: UploadFile | None = File(None),
    default_speed: float = Form(1.3),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    thumb_dir = STORAGE_THUMBS
    if thumbs_zip:
        tmp_sub = f"bulk_{uuid.uuid4().hex[:8]}"
        thumb_dir = os.path.join(STORAGE_THUMBS, tmp_sub)
        os.makedirs(thumb_dir, exist_ok=True)
        data = thumbs_zip.file.read()
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            z.extractall(thumb_dir)

    raw = csv_file.file.read()
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    required = {"title","description","tags","script_text","voice_category","speed","publish_iso","thumbnail"}
    if set(map(str.strip, reader.fieldnames or [])) != required:
        return JSONResponse(
            status_code=400,
            content={"detail": f"En-têtes CSV invalides. Attendu: {','.join(sorted(required))}"}
        )

    created = []
    for row in reader:
        title = (row["title"] or "").strip()
        if not title:
            continue
        description = (row["description"] or "").strip()
        tags = (row["tags"] or "").strip()
        script_text = (row["script_text"] or "").strip()
        voice_category = (row["voice_category"] or "femme").strip()
        try:
            speed = float(row["speed"] or default_speed)
        except:
            speed = default_speed
        publish_iso = (row["publish_iso"] or "").strip()
        thumb_name = (row["thumbnail"] or "").strip()

        thumb_path = ""
        if thumb_name:
            src = os.path.join(thumb_dir, thumb_name)
            if os.path.exists(src):
                base, ext = os.path.splitext(safe_filename(thumb_name))
                unique = f"{uuid.uuid4().hex[:8]}_{base}{ext}"
                dst = os.path.join(STORAGE_THUMBS, unique)
                with open(src, "rb") as fi, open(dst, "wb") as fo:
                    fo.write(fi.read())
                thumb_path = str(Path(dst)).replace("\\", "/")

        job = Job(
            user_id=user.id,
            title=title,
            description=description,
            tags=tags,
            script_text=script_text,
            voice=pick_voice(voice_category, None),
            speed=speed,
            publish_iso=publish_iso,
            thumbnail_path=thumb_path,
            status="READY",
            progress_msg="",
        )
        db.add(job)
        created.append(title)

    db.commit()
    return {"created_count": len(created), "created_titles": created[:10]}

# ---------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------
class _TokenOutModel(TokenOut): pass

@app.post("/auth/register", response_model=_TokenOutModel)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email deja utilise")
    user = User(email=payload.email, password_hash=get_password_hash(payload.password))
    db.add(user); db.commit(); db.refresh(user)
    token = create_access_token({"sub": str(user.id)})
    return _TokenOutModel(access_token=token, token_type="bearer")

@app.post("/auth/login", response_model=_TokenOutModel)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Identifiants invalides")
    token = create_access_token({"sub": str(user.id)})
    return _TokenOutModel(access_token=token, token_type="bearer")

# ---------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------
@app.post("/jobs", response_model=JobOut)
async def create_job(
    title: str = Form(...),
    description: str = Form(""),
    tags: str = Form(""),
    script_text: str = Form(...),
    voice_category: str = Form("femme"),
    voice: str = Form(""),
    speed: float = Form(1.1),
    publish_iso: Optional[str] = Form(None),
    thumbnail: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not thumbnail or not thumbnail.filename:
        raise HTTPException(status_code=400, detail="Miniature requise")

    chosen_voice = voice.strip() or pick_voice(voice_category, None)

    # nom sûr + unique
    original = thumbnail.filename or "thumb.jpg"
    base, ext = os.path.splitext(safe_filename(original))
    unique = f"{uuid.uuid4().hex[:8]}_{base}{ext}"
    thumb_path = STORAGE_DIR / "thumbs" / unique
    with open(thumb_path, "wb") as f:
        f.write(await thumbnail.read())
    thumb_path_str = str(thumb_path).replace("\\", "/")

    job = Job(
        user_id=user.id,
        title=title, description=description, tags=tags,
        script_text=script_text, voice=chosen_voice, speed=speed,
        publish_iso=(publish_iso or "").strip() or "",  # "" = publication immédiate
        thumbnail_path=thumb_path_str,
        status="READY",
        progress_msg="",
    )
    db.add(job); db.commit(); db.refresh(job)
    poke_worker()
    return job

@app.get("/jobs", response_model=List[JobOut])
def list_jobs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(Job).filter(Job.user_id == user.id)
    if status:
        q = q.filter(Job.status == status)
    jobs = q.order_by(Job.created_at.desc()).offset(offset).limit(limit).all()
    return jobs

@app.get("/jobs/{job_id}", response_model=JobOut)
def job_detail(job_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job introuvable")
    return job

# ---------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------
@app.get("/stats")
def stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = datetime(now.year, now.month, 1)

    base = db.query(Job).filter(Job.user_id == user.id)

    def count_since(start_dt): return base.filter(Job.created_at >= start_dt).count()
    def count_status(start_dt, st): return base.filter(Job.created_at >= start_dt, Job.status == st).count()

    return {
        "created_today": count_since(today_start),
        "created_week": count_since(week_start),
        "created_month": count_since(month_start),
        "published_today": count_status(today_start, "PUBLISHED"),
        "scheduled_today": count_status(today_start, "SCHEDULED"),
        "failed_today": count_status(today_start, "FAILED"),
        "totals": {
            "ready": base.filter(Job.status=="READY").count(),
            "rendering": base.filter(Job.status=="RENDERING").count(),
            "done": base.filter(Job.status=="DONE").count(),
            "uploading": base.filter(Job.status=="UPLOADING").count(),
            "scheduled": base.filter(Job.status=="SCHEDULED").count(),
            "published": base.filter(Job.status=="PUBLISHED").count(),
            "failed": base.filter(Job.status=="FAILED").count(),
        }
    }

# ---------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------
@app.get("/health")
def health():
    return {"ok": True}

# ---------------------------------------------------------------------
# Main (local)
# ---------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)


@app.on_event("startup")
def _startup():
    init_db()
    try: ensure_worker_running()
    except: pass

@app.get("/auth/drive/start")
def drive_start(current_user=Depends(get_current_user)):
    return RedirectResponse(google_oauth.drive_start_url(current_user.id))

@app.get("/auth/drive/callback")
def drive_callback(code: str, state: str, db: Session = Depends(get_db)):
    google_oauth.finish_drive_oauth(db, code, state)
    return HTMLResponse("<h3>Google Drive connecté ✅</h3><p>Tu peux revenir à l’app.</p>")
