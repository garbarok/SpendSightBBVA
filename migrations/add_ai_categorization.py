"""Migration: Add AI categorization support.

This migration adds:
1. AI metadata columns to transactions table
2. category_training_examples table for AI learning
3. transaction_embeddings table for caching
4. Movement type enum migration from free text

Run this migration using:
    python migrations/add_ai_categorization.py
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from sqlalchemy import create_engine, text
from models.database import Base, DatabaseManager
from models.movement_type import MovementType
from utils.logger import setup_logger

logger = setup_logger(__name__)


def migrate_movement_types(engine):
    """
    Migrate existing free-text movement types to enum values.

    Args:
        engine: SQLAlchemy engine
    """
    logger.info("Migrating movement types to enum values...")

    with engine.connect() as conn:
        # Get all unique movement types
        result = conn.execute(text(
            "SELECT DISTINCT movimiento FROM transactions WHERE movimiento IS NOT NULL"
        ))

        movement_mapping = {}
        for row in result:
            original = row[0]
            enum_value = MovementType.from_text(original).value
            movement_mapping[original] = enum_value

        logger.info(f"Found {len(movement_mapping)} unique movement types to migrate")

        # Update each movement type
        for original, enum_value in movement_mapping.items():
            conn.execute(
                text(
                    "UPDATE transactions SET movement_type_enum = :enum_value "
                    "WHERE movimiento = :original"
                ),
                {"enum_value": enum_value, "original": original}
            )
            logger.debug(f"Migrated '{original}' -> '{enum_value}'")

        conn.commit()

    logger.info("✓ Movement type migration complete")


def add_indexes(engine):
    """
    Add performance indexes for AI features.

    Args:
        engine: SQLAlchemy engine
    """
    logger.info("Adding performance indexes...")

    indexes = [
        # Transaction indexes
        "CREATE INDEX IF NOT EXISTS idx_transaction_ai_method ON transactions(categorization_method)",
        "CREATE INDEX IF NOT EXISTS idx_transaction_movement_enum ON transactions(movement_type_enum)",
        "CREATE INDEX IF NOT EXISTS idx_transaction_confidence ON transactions(ai_confidence)",

        # Training example indexes (already defined in model, but ensure they exist)
        "CREATE INDEX IF NOT EXISTS idx_training_project_category ON category_training_examples(project_id, category)",
        "CREATE INDEX IF NOT EXISTS idx_training_project_source ON category_training_examples(project_id, source)",

        # Embedding cache indexes
        "CREATE INDEX IF NOT EXISTS idx_embedding_project_hash ON transaction_embeddings(project_id, text_hash)",
        "CREATE INDEX IF NOT EXISTS idx_embedding_model_version ON transaction_embeddings(model_version)",
    ]

    with engine.connect() as conn:
        for index_sql in indexes:
            try:
                conn.execute(text(index_sql))
                logger.debug(f"Created index: {index_sql[:50]}...")
            except Exception as e:
                logger.warning(f"Index creation failed (may already exist): {e}")

        conn.commit()

    logger.info("✓ Indexes added")


def run_migration():
    """Execute the full migration."""
    logger.info("=" * 60)
    logger.info("Starting AI Categorization Migration")
    logger.info("=" * 60)

    # Initialize database
    db_manager = DatabaseManager()
    engine = db_manager.engine

    # Step 1: Create new tables (handled by Base.metadata.create_all)
    logger.info("\nStep 1: Creating new tables...")
    Base.metadata.create_all(engine)
    logger.info("✓ Tables created/verified")

    # Step 2: Add new columns to existing tables
    logger.info("\nStep 2: Adding new columns to transactions table...")
    with engine.connect() as conn:
        try:
            # Check if columns already exist
            result = conn.execute(text("PRAGMA table_info(transactions)"))
            existing_columns = {row[1] for row in result}

            columns_to_add = []
            if 'ai_confidence' not in existing_columns:
                columns_to_add.append("ALTER TABLE transactions ADD COLUMN ai_confidence FLOAT")
            if 'categorization_method' not in existing_columns:
                columns_to_add.append("ALTER TABLE transactions ADD COLUMN categorization_method VARCHAR(20)")
            if 'movement_type_enum' not in existing_columns:
                columns_to_add.append("ALTER TABLE transactions ADD COLUMN movement_type_enum VARCHAR(50)")

            for sql in columns_to_add:
                conn.execute(text(sql))
                logger.info(f"  Added column: {sql.split('ADD COLUMN')[1].strip()}")

            conn.commit()

            if not columns_to_add:
                logger.info("  All columns already exist")

        except Exception as e:
            logger.error(f"Error adding columns: {e}")
            raise

    logger.info("✓ Columns added")

    # Step 3: Migrate existing movement types
    logger.info("\nStep 3: Migrating movement types...")
    migrate_movement_types(engine)

    # Step 4: Add performance indexes
    logger.info("\nStep 4: Adding performance indexes...")
    add_indexes(engine)

    # Step 5: Initialize categorization_method for existing transactions
    logger.info("\nStep 5: Initializing categorization methods for existing data...")
    with engine.connect() as conn:
        # Set all existing transactions as 'keyword' categorized
        # (they were categorized using the old keyword-based system)
        conn.execute(text(
            "UPDATE transactions SET categorization_method = 'keyword' "
            "WHERE categorization_method IS NULL AND categoria_original IS NULL"
        ))

        # Set manually edited transactions
        conn.execute(text(
            "UPDATE transactions SET categorization_method = 'manual' "
            "WHERE categorization_method IS NULL AND categoria_original IS NOT NULL"
        ))

        conn.commit()

    logger.info("✓ Categorization methods initialized")

    # Migration complete
    logger.info("\n" + "=" * 60)
    logger.info("✅ Migration completed successfully!")
    logger.info("=" * 60)
    logger.info("\nNew features available:")
    logger.info("  • AI-powered categorization with confidence scores")
    logger.info("  • Standardized movement type enums")
    logger.info("  • Training examples for learning from corrections")
    logger.info("  • Embedding cache for performance")
    logger.info("\nNext steps:")
    logger.info("  1. Update requirements.txt with AI dependencies")
    logger.info("  2. Implement AI categorization service")
    logger.info("  3. Download sentence-transformers model")


if __name__ == '__main__':
    try:
        run_migration()
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        sys.exit(1)
