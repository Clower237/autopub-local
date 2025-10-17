# database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

# Si DATABASE_URL est fourni (ex: Render -> postgresql://...), on l'utilise.
# Sinon, fallback local en SQLite.
if DATABASE_URL:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
else:
    engine = create_engine("sqlite:///./autopub_local.db", connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    # Import ici pour éviter les imports circulaires
    from models import User, Job, OAuthToken  # noqa: F401
    Base.metadata.create_all(bind=engine)