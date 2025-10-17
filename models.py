from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, UniqueConstraint
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    drive_folder_id = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class OAuthToken(Base):
    __tablename__ = "oauth_tokens"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    provider = Column(String(32), nullable=False)               # 'google'
    scope_key = Column(String(64), nullable=False)              # 'youtube+drive'
    token_json = Column(Text, nullable=False)                   # Credentials.to_json()
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    __table_args__ = (
        UniqueConstraint("user_id", "provider", "scope_key", name="uq_token_user_provider_scope"),
    )

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
