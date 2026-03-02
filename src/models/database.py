"""SQLAlchemy database setup and configuration."""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from pathlib import Path

Base = declarative_base()

class DatabaseManager:
    """Manages database connections and sessions."""

    def __init__(self, db_path: str = None):
        """
        Initialize database manager.

        Args:
            db_path: Path to SQLite database file. If None, uses default location.
        """
        if db_path is None:
            # Default to data/spendsight.db
            db_path = Path(__file__).parent.parent.parent / "data" / "spendsight.db"
        else:
            db_path = Path(db_path)

        # Ensure parent directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self.db_path = db_path
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)

    def create_tables(self):
        """Create all tables in the database."""
        Base.metadata.create_all(bind=self.engine)

    def get_session(self):
        """Get a new database session."""
        return self.SessionLocal()

    def close(self):
        """Close the database engine."""
        self.engine.dispose()
