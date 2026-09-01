import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

logger = logging.getLogger("assetvault.db")

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False, "timeout": 30.0}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def init_db(target_engine=None):
    """Initializes schema and runs automatic SQLite column migrations."""
    db_engine = target_engine or engine
    Base.metadata.create_all(bind=db_engine)
    
    # Auto-migration and concurrency optimization for SQLite tables
    try:
        with db_engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL;"))
            conn.execute(text("PRAGMA busy_timeout=30000;"))
            conn.commit()
    except Exception as e:
        logger.debug(f"SQLite PRAGMA setup note: {e}")

    try:
        with db_engine.connect() as conn:
            # Check files table columns
            cursor = conn.execute(text("PRAGMA table_info(files)"))
            existing_columns = {row[1] for row in cursor.fetchall()}
            
            if existing_columns:
                if "folder_id" not in existing_columns:
                    conn.execute(text("ALTER TABLE files ADD COLUMN folder_id VARCHAR(36)"))
                    logger.info("Migrated schema: Added files.folder_id column.")
                if "file_modified_at" not in existing_columns:
                    conn.execute(text("ALTER TABLE files ADD COLUMN file_modified_at DATETIME"))
                    logger.info("Migrated schema: Added files.file_modified_at column.")
                if "file_hash" not in existing_columns:
                    conn.execute(text("ALTER TABLE files ADD COLUMN file_hash VARCHAR"))
                    logger.info("Migrated schema: Added files.file_hash column.")
                if "thumbnail_path" not in existing_columns:
                    conn.execute(text("ALTER TABLE files ADD COLUMN thumbnail_path VARCHAR"))
                    logger.info("Migrated schema: Added files.thumbnail_path column.")

            # Auto-cleanup orphaned asset references if folders were removed
            cursor = conn.execute(text("SELECT COUNT(*) FROM library_folders"))
            folder_count = cursor.fetchone()[0]
            if folder_count == 0:
                conn.execute(text("DELETE FROM files"))
            else:
                conn.execute(text("DELETE FROM files WHERE folder_id IS NOT NULL AND folder_id NOT IN (SELECT id FROM library_folders)"))
            conn.commit()
    except Exception as e:
        logger.debug(f"Schema migration / cleanup note: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
