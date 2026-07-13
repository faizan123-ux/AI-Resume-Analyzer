import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Render-ലെ DATABASE_URL ഉണ്ടെങ്കിൽ അത് എടുക്കും, ഇല്ലെങ്കിൽ ലോക്കൽ ടെസ്റ്റിംഗിനായി SQLite ഉപയോഗിക്കും
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./sql_app.db"

# PostgreSQL ആണെങ്കിൽ connect_args ആവശ്യമില്ല, SQLite-ന് മാത്രം മതി
if "sqlite" in DATABASE_URL:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()