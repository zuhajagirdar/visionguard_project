import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Determine absolute path to the SQLite database file in a 'data' folder at the project root.
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# Use separate database file for tests to avoid schema conflicts
if os.getenv('PYTEST_CURRENT_TEST'):
    db_filename = 'test_reimbursement.db'
    # Remove existing test DB to ensure a fresh schema
    test_db_path = os.path.join(DATA_DIR, db_filename)
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
else:
    db_filename = 'reimbursement.db'
DB_PATH = os.path.join(DATA_DIR, db_filename)
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# Create engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Declarative base
Base = declarative_base()

# Import models to ensure tables are registered
import models as _models  # noqa: F401

# Ensure all tables are created (especially for fresh test DB)
Base.metadata.create_all(bind=engine)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
