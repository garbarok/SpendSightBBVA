"""Script to run migration 002 for Phase 2 intelligence features."""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from models.database import DatabaseManager
from services.migration_002_phase2_intelligence import upgrade

def main():
    """Run the migration."""
    print("Running migration 002: Phase 2 Intelligence features")
    print("=" * 60)

    # Initialize database manager
    db_manager = DatabaseManager()

    # Run migration
    try:
        upgrade(db_manager)
        print("\n✅ Migration completed successfully!")
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
