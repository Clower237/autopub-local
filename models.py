
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.sql import func
from database import Base
# --- OAuth tokens (à coller en bas de models.py) ---
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base

class OAuthToken(Base):
    __tablename__ = "oauth_tokens"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    provider = Column(String(32), nullable=False)  # "drive" ou "youtube"
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    scopes = Column(Text, nullable=True)  # scopes séparés par espaces
    expiry = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    tags = Column(Text, default="")
    script_text = Column(Text, nullable=False)
    voice = Column(String(128), default="fr-FR-DeniseNeural")
    speed = Column(Float, default=1.3)
    publish_iso = Column(String(64), nullable=True)
    thumbnail_path = Column(String(512), nullable=False)
    audio_path = Column(String(512), nullable=True)
    video_path = Column(String(512), nullable=True)
    youtube_video_id = Column(String(64), nullable=True)
    status = Column(String(32), default="READY")
    progress_msg = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class OAuthToken(Base):
    __tablename__ = "oauth_tokens"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    provider = Column(String(32), nullable=False)  # "drive" ou "youtube"
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    scopes = Column(Text, nullable=True)
    expiry = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
