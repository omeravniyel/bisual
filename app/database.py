from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import os

SQLALCHEMY_DATABASE_URL = "sqlite:///./bisual.db"

# Check for DATABASE_URL (Vercel/Supabase)
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Fix for SQLAlchemy requiring 'postgresql://' instead of 'postgres://'
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    # Supabase requires SSL
    engine = create_engine(DATABASE_URL, connect_args={"sslmode": "require"})
else:
    # Vercel Read-Only File System Fix (Fallback to SQLite)
    if os.environ.get("VERCEL"):
        SQLALCHEMY_DATABASE_URL = "sqlite:////tmp/bisual.db"
    
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
