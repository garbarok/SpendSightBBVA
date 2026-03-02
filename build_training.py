#!/usr/bin/env python3
"""Build initial AI training data from existing transactions."""
import sys
sys.path.insert(0, 'src')

from models.database import DatabaseManager
from services.initial_training_service import InitialTrainingService
from utils.logger import setup_logger

logger = setup_logger(__name__)


def build_training(project_id: int = 1):
    """Build initial training data."""
    db = DatabaseManager()
    session = db.get_session()

    try:
        print("\n" + "=" * 60)
        print("BUILDING INITIAL AI TRAINING DATA")
        print("=" * 60)

        # Initialize service
        training_service = InitialTrainingService(session, project_id)

        # Check readiness
        readiness = training_service.get_training_readiness()
        print(f"\nReadiness: {readiness['readiness']}")
        print(f"Message: {readiness['message']}")
        print(f"\nAvailable data:")
        print(f"  • Manual edits: {readiness['manual_edits_available']}")
        print(f"  • Category rules: {readiness['rules_available']}")
        print(f"  • Current examples: {readiness['current_examples']}")

        # Build training
        print("\n" + "-" * 60)
        print("Building training data...")
        print("-" * 60 + "\n")

        def progress_callback(message, current, total):
            print(f"[{current}/{total}] {message}")

        stats = training_service.build_initial_training(progress_callback)

        # Show results
        print("\n" + "=" * 60)
        print("✅ TRAINING DATA BUILT SUCCESSFULLY!")
        print("=" * 60)
        print(f"\nTotal examples created: {stats['total_examples']}")
        print(f"  • From manual edits: {stats['manual_edits']}")
        print(f"  • From category rules: {stats['category_rules']}")
        print(f"  • Representative samples: {stats['representatives']}")
        print(f"\nCategories covered: {stats['categories_covered']}")

        print("\n💡 Next steps:")
        print("  1. Run: python recategorize_with_ai.py")
        print("     (To see what would change - dry run)")
        print("  2. Run: python recategorize_with_ai.py --live")
        print("     (To actually apply AI categorization)")
        print("  3. Restart the app to see results!")
        print("=" * 60 + "\n")

    except Exception as e:
        logger.error(f"Training build failed: {e}", exc_info=True)
        print(f"\n❌ Error: {e}\n")
        raise
    finally:
        session.close()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Build AI training data')
    parser.add_argument('--project-id', type=int, default=1, help='Project ID (default: 1)')

    args = parser.parse_args()

    build_training(args.project_id)
