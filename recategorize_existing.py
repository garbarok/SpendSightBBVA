#!/usr/bin/env python3
"""
Recategorize existing transactions with AI metadata.

This script updates all transactions in a project to include:
- ai_confidence
- categorization_method

It re-runs the categorization pipeline on existing transactions.
"""
import sys
sys.path.insert(0, 'src')

from models.database import DatabaseManager
from models.project import Project
from models.transaction import Transaction
from services.categorization_service import CategorizationService
from utils.logger import setup_logger

logger = setup_logger(__name__)


def recategorize_project(project_id: int):
    """
    Recategorize all transactions in a project.

    Args:
        project_id: ID of the project to recategorize
    """
    db_manager = DatabaseManager('data/spendsight.db')
    session = db_manager.get_session()

    try:
        # Get project
        project = session.query(Project).get(project_id)
        if not project:
            print(f"❌ Project {project_id} not found")
            return

        print(f"\n{'='*60}")
        print(f"Recategorizing project: {project.name}")
        print(f"{'='*60}\n")

        # Get all transactions
        transactions = session.query(Transaction).filter_by(
            project_id=project_id
        ).all()

        print(f"Found {len(transactions)} transactions to recategorize\n")

        # Create categorization service
        cat_service = CategorizationService(session, project_id, enable_ai=True)

        # Recategorize each transaction
        stats = {
            'ai': 0,
            'rule': 0,
            'keyword': 0,
            'manual': 0,
            'default': 0,
            'skipped': 0
        }

        for i, txn in enumerate(transactions, 1):
            # Skip manually edited transactions
            if txn.is_manually_edited:
                stats['manual'] += 1
                stats['skipped'] += 1
                if i % 50 == 0:
                    print(f"  Progress: {i}/{len(transactions)} ({i*100//len(transactions)}%)")
                continue

            # Get categorization
            result = cat_service.categorize_transaction(
                txn.concepto,
                txn.movimiento
            )

            category = result['category']
            method = result['method']
            confidence = result.get('confidence')

            # Update transaction
            if method == 'ai' and confidence:
                txn.categoria = category
                txn.ai_confidence = confidence
                txn.categorization_method = 'ai'
                stats['ai'] += 1
            elif method == 'rule':
                txn.categoria = category
                txn.categorization_method = 'rule'
                txn.ai_confidence = None
                stats['rule'] += 1
            elif method == 'keyword':
                txn.categoria = category
                txn.categorization_method = 'keyword'
                txn.ai_confidence = None
                stats['keyword'] += 1
            else:
                txn.categoria = category
                txn.categorization_method = 'default'
                txn.ai_confidence = None
                stats['default'] += 1

            # Commit every 50 transactions
            if i % 50 == 0:
                session.commit()
                print(f"  Progress: {i}/{len(transactions)} ({i*100//len(transactions)}%)")

        # Final commit
        session.commit()

        # Print results
        print(f"\n{'='*60}")
        print("Recategorization Complete!")
        print(f"{'='*60}")
        print(f"  🤖 AI categorized:     {stats['ai']:>4} transactions")
        print(f"  📋 Rule categorized:   {stats['rule']:>4} transactions")
        print(f"  🔑 Keyword matched:    {stats['keyword']:>4} transactions")
        print(f"  ⚙️  Default category:   {stats['default']:>4} transactions")
        print(f"  ✋ Manual (skipped):   {stats['manual']:>4} transactions")
        print(f"  {'='*60}")
        print(f"  Total processed:       {len(transactions) - stats['skipped']:>4} transactions")
        print(f"  {'='*60}\n")

    except Exception as e:
        logger.error(f"Error recategorizing project: {e}", exc_info=True)
        session.rollback()
        print(f"❌ Error: {e}")
    finally:
        session.close()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("\nUsage: python recategorize_existing.py <project_id>")
        print("\nExample: python recategorize_existing.py 3")

        # List available projects
        db_manager = DatabaseManager('data/spendsight.db')
        session = db_manager.get_session()
        projects = session.query(Project).all()

        if projects:
            print("\nAvailable projects:")
            for p in projects:
                txn_count = session.query(Transaction).filter_by(project_id=p.id).count()
                print(f"  ID {p.id}: {p.name} ({txn_count} transactions)")

        session.close()
        sys.exit(1)

    project_id = int(sys.argv[1])
    recategorize_project(project_id)
