from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ശ്രദ്ധിക്കുക: 'your_password' എന്ന ഭാഗത്ത് pgAdmin തുറക്കാൻ ഉപയോഗിച്ച പാസ്‌വേഡ് കൊടുക്കുക.
DATABASE_URL = "postgresql://postgres:faizan%40123@localhost:5432/resume_builder"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()