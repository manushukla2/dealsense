import os
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Float, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config.settings import settings

_url = settings.database_url
if _url.startswith("postgresql") and os.getenv("APP_ENV", "development") == "development":
    _db_path = str(__import__("pathlib").Path(__file__).resolve().parent.parent / "data" / "dealsense.db")
    _url = f"sqlite:///{_db_path}"

engine = create_engine(_url, connect_args={"check_same_thread": False} if "sqlite" in _url else {})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


class MeetingRecord(Base):
    __tablename__ = "meetings"
    meeting_id  = Column(String, primary_key=True)
    source_file = Column(String)
    probability = Column(Float)
    verdict     = Column(String)
    summary     = Column(String)
    transcript  = Column(JSON)
    prediction  = Column(JSON)
    created_at  = Column(DateTime, default=datetime.utcnow)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
