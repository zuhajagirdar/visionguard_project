import os
import shutil
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

IS_VERCEL = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
DATABASE_URL_ENV = os.environ.get("DATABASE_URL")

if DATABASE_URL_ENV:
    # Support external PostgreSQL / Supabase / Neon / Turso databases
    if DATABASE_URL_ENV.startswith("postgres://"):
        DATABASE_URL_ENV = DATABASE_URL_ENV.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URL = DATABASE_URL_ENV
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
else:
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if IS_VERCEL:
        DATA_DIR = "/tmp/data"
        os.makedirs(DATA_DIR, exist_ok=True)
        db_filename = 'reimbursement.db'
        dest_db_path = os.path.join(DATA_DIR, db_filename)
        # Copy repo db if available and destination does not exist yet
        repo_db_path = os.path.join(BASE_DIR, 'data', 'reimbursement.db')
        if not os.path.exists(dest_db_path) and os.path.exists(repo_db_path):
            try:
                shutil.copyfile(repo_db_path, dest_db_path)
            except Exception as e:
                print("Notice: could not copy repo DB to /tmp:", e)
        DB_PATH = dest_db_path
    else:
        DATA_DIR = os.path.join(BASE_DIR, 'data')
        os.makedirs(DATA_DIR, exist_ok=True)
        if os.getenv('PYTEST_CURRENT_TEST'):
            db_filename = 'test_reimbursement.db'
            test_db_path = os.path.join(DATA_DIR, db_filename)
            if os.path.exists(test_db_path):
                try:
                    os.remove(test_db_path)
                except Exception:
                    pass
        else:
            db_filename = 'reimbursement.db'
        DB_PATH = os.path.join(DATA_DIR, db_filename)

    SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )

# Declarative base
Base = declarative_base()

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
