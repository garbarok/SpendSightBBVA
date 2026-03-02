#!/usr/bin/env python3
"""Re-categorize existing transactions using AI."""
import sys
sys.path.insert(0, 'src')

from models.database import DatabaseManager
from models import Transaction
from services.categorization_service import CategorizationService
from utils.logger import setup_logger

logger = setup_logger(__name__)


def recategorize_all_transactions(project_id: int, dry_run: bool = True):
    """
    Re-categorize all transactions in a project using AI.

    Args:
        project_id: Project ID to re-categorize
        dry_run: If True, show what would change without saving
    """
    db = DatabaseManager()
    session = db.get_session()

    try:
        # Get all transactions
        transactions = session.query(Transaction).filter_by(
            project_id=project_id
        ).all()

        print(f"\n{'🔍 DRY RUN - No changes will be saved' if dry_run else '✅ LIVE RUN - Changes will be saved'}")
        print(f"\n📊 Found {len(transactions)} transactions to re-categorize\n")

        # Initialize categorization service
        cat_service = CategorizationService(session, project_id, enable_ai=True)

        # Stats
        stats = {
            'total': len(transactions),
            'changed': 0,
            'unchanged': 0,
            'by_method': {
                'rule': 0,
                'ai': 0,
                'keyword': 0,
                'default': 0
            }
        }

        # Re-categorize each transaction
        for i, transaction in enumerate(transactions, 1):
            old_category = transaction.categoria
            old_method = transaction.categorization_method or 'unknown'

            # Get new categorization
            result = cat_service.categorize_transaction(
                transaction.concepto,
                transaction.movimiento
            )

            new_category = result['category']
            new_method = result['method']
            new_confidence = result['confidence']

            # Track method used
            stats['by_method'][new_method] = stats['by_method'].get(new_method, 0) + 1

            # Check if changed
            if new_category != old_category or new_method != old_method:
                stats['changed'] += 1

                # Show change
                if stats['changed'] <= 10:  # Show first 10 changes
                    print(f"{i:3d}. {transaction.concepto[:50]:50s}")
                    print(f"     OLD: {old_category:30s} [{old_method}]")
                    print(f"     NEW: {new_category:30s} [{new_method}] ({new_confidence:.0%})")
                    print()

                # Update transaction (if not dry run)
                if not dry_run:
                    if new_method == 'ai':
                        transaction.set_ai_categorization(new_category, new_confidence)
                    else:
                        transaction.categoria = new_category
                        transaction.categorization_method = new_method
                        transaction.ai_confidence = new_confidence
            else:
                stats['unchanged'] += 1

            # Progress
            if i % 50 == 0:
                print(f"Progress: {i}/{len(transactions)} ({i/len(transactions)*100:.0f}%)")

        # Commit changes
        if not dry_run:
            session.commit()
            print("\n✅ Changes saved to database")
        else:
            print("\n🔍 Dry run complete - no changes saved")

        # Show summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Total transactions:     {stats['total']}")
        print(f"Changed:                {stats['changed']}")
        print(f"Unchanged:              {stats['unchanged']}")
        print(f"\nCategorization methods:")
        print(f"  • User Rules:         {stats['by_method'].get('rule', 0)}")
        print(f"  • AI:                 {stats['by_method'].get('ai', 0)} 🤖")
        print(f"  • Keywords:           {stats['by_method'].get('keyword', 0)}")
        print(f"  • Default:            {stats['by_method'].get('default', 0)}")
        print("=" * 60)

    except Exception as e:
        logger.error(f"Re-categorization failed: {e}", exc_info=True)
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Re-categorize transactions with AI')
    parser.add_argument('--project-id', type=int, default=1, help='Project ID (default: 1)')
    parser.add_argument('--live', action='store_true', help='Actually save changes (default: dry run)')

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("AI RE-CATEGORIZATION TOOL")
    print("=" * 60)

    if not args.live:
        print("\n⚠️  Running in DRY RUN mode")
        print("   No changes will be saved. Use --live to save changes.\n")

    recategorize_all_transactions(args.project_id, dry_run=not args.live)
