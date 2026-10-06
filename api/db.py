from sqlalchemy import create_engine, Column, String, Float, JSON, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from config.settings import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class MeetingRecord(Base):
    __tablename__ = "meetings"
    meeting_id   = Column(String, primary_key=True)
    source_file  = Column(String)
    probability  = Column(Float)
    verdict      = Column(String)
    summary      = Column(String)
    transcript   = Column(JSON)
    prediction   = Column(JSON)
    created_at   = Column(DateTime, default=datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
