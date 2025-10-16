<<<<<<< HEAD
=======
# database.py
>>>>>>> db514c543433a21066a87daabdbd4b4cbeaa9a76
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

<<<<<<< HEAD
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./autopub_local.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
=======
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

# Render fournit un URL postgresql:// ; SQLAlchemy accepte aussi postgresql+psycopg
if DATABASE_URL:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
else:
    engine = create_engine("sqlite:///./autopub_local.db", connect_args={"check_same_thread": False})
>>>>>>> db514c543433a21066a87daabdbd4b4cbeaa9a76

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from models import User, Job, OAuthToken  # noqa
    Base.metadata.create_all(bind=engine)
