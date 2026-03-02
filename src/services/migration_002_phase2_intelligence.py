"""Database migration 002: Phase 2 Intelligence features.

Adds:
- category_rules table for learning categorization
- tags column to transactions table
"""
from sqlalchemy import text

def upgrade(db_manager):
    """
    Apply migration to add Phase 2 intelligence features.

    Args:
        db_manager: DatabaseManager instance
    """
    with db_manager.engine.begin() as connection:
        # Add tags column to transactions table (if not exists)
        try:
            connection.execute(text("""
                ALTER TABLE transactions
                ADD COLUMN tags TEXT NULL
            """))
            print("✓ Added tags column to transactions table")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("  Tags column already exists, skipping")
            else:
                raise

        # Create category_rules table (if not exists)
        try:
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS category_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    pattern VARCHAR(255) NOT NULL,
                    category VARCHAR(100) NOT NULL,
                    priority INTEGER NOT NULL DEFAULT 100,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            """))
            print("✓ Created category_rules table")
        except Exception as e:
            print(f"  Category rules table may already exist: {e}")

        # Create index on category_rules
        try:
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_project_priority
                ON category_rules(project_id, priority)
            """))
            print("✓ Created index on category_rules")
        except Exception as e:
            print(f"  Index may already exist: {e}")

    print("✅ Migration 002 completed successfully")

def downgrade(db_manager):
    """
    Rollback migration 002.

    Args:
        db_manager: DatabaseManager instance
    """
    with db_manager.engine.begin() as connection:
        # Note: SQLite doesn't support DROP COLUMN directly
        # For now, we'll just drop the table
        connection.execute(text("DROP TABLE IF EXISTS category_rules"))
        print("✓ Dropped category_rules table")

        # Cannot easily drop tags column in SQLite without recreating table
        print("⚠ Warning: tags column left in transactions table (SQLite limitation)")

    print("✅ Migration 002 rollback completed")
