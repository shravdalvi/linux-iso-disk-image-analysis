from sqlalchemy import create_engine, Column, Integer, String, Float, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///../data/iso_analysis.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class ISOAnalysisResult(Base):
    __tablename__ = "iso_analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    checksum = Column(String, index=True)
    status = Column(String)  # TRUSTED, SUSPICIOUS, etc.
    risk_score = Column(Float)
    details = Column(JSON)   # Detailed results from agents

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
