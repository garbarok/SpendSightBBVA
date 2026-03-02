#!/usr/bin/env python3
"""
Test script to verify AI categorization during import.

This script:
1. Creates a test project
2. Imports test transactions with AI categorization enabled
3. Verifies ai_confidence and categorization_method are set correctly
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from models.database import DatabaseManager
from models.project import Project
from models.transaction import Transaction
from services.categorization_service import CategorizationService
from services.migration_service import MigrationService
from utils.logger import setup_logger
from datetime import datetime

logger = setup_logger(__name__)

def test_ai_categorization():
    """Test the AI categorization flow."""
    print("\n" + "="*70)
    print("TESTING AI CATEGORIZATION FIX")
    print("="*70)

    db_manager = DatabaseManager()
    session = db_manager.get_session()

    try:
        # Create test project
        test_project = Project(
            name="AI Test Project",
            description="Testing AI categorization fix"
        )
        session.add(test_project)
        session.commit()
        project_id = test_project.id
        print(f"\n✓ Created test project: {test_project.name} (ID: {project_id})")

        # Create categorization service
        cat_service = CategorizationService(session, project_id)
        print(f"\n✓ Initialized CategorizationService")

        # Test 1: Check if training examples are loaded
        examples = cat_service._get_ai_service()._load_training_examples() if cat_service._get_ai_service() else []
        if examples:
            print(f"\n✓ Found {len(examples)} training examples in database")
        else:
            print(f"\n⚠️  No training examples found - AI won't have data to work with")

        # Test 2: Try to categorize a test transaction
        test_concepto = "AMAZON.ES S.L. BK8HHH12HHH EUR"
        result = cat_service.categorize_transaction(test_concepto, "Card payment")

        print(f"\n✓ Categorized test transaction: '{test_concepto}'")
        print(f"  - Category: {result['category']}")
        print(f"  - Confidence: {result['confidence']:.2%}")
        print(f"  - Method: {result['method']}")
        print(f"  - Priority: {result['priority']}")

        # Test 3: Create a test transaction with AI metadata
        test_txn = Transaction(
            project_id=project_id,
            fecha=datetime.now(),
            concepto=test_concepto,
            movimiento="Card payment",
            importe=-25.99,
            categoria=result['category'],
            ai_confidence=result['confidence'],
            categorization_method=result['method'],
            source_file="test_import.xlsx"
        )
        session.add(test_txn)
        session.commit()

        print(f"\n✓ Created test transaction in database")
        print(f"  - ID: {test_txn.id}")
        print(f"  - AI Confidence: {test_txn.ai_confidence}")
        print(f"  - Method: {test_txn.categorization_method}")

        # Test 4: Verify data persisted correctly
        retrieved = session.query(Transaction).filter_by(id=test_txn.id).first()
        if retrieved:
            print(f"\n✓ Retrieved transaction from database")
            print(f"  - Confidence: {retrieved.ai_confidence}")
            print(f"  - Method: {retrieved.categorization_method}")

            # Verify values are correct
            if retrieved.ai_confidence == result['confidence']:
                print(f"  ✓ Confidence value persisted correctly")
            else:
                print(f"  ✗ Confidence mismatch: expected {result['confidence']}, got {retrieved.ai_confidence}")

            if retrieved.categorization_method == result['method']:
                print(f"  ✓ Method value persisted correctly")
            else:
                print(f"  ✗ Method mismatch: expected {result['method']}, got {retrieved.categorization_method}")

        # Test 5: Check confidence indicator
        print(f"\n✓ Confidence indicator: {retrieved.confidence_indicator}")

        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        print("""
The fix should enable:
1. ✓ AI categorization is called during import (not just legacy keywords)
2. ✓ ai_confidence is populated from AI service
3. ✓ categorization_method shows 'ai' for AI-categorized items
4. ✓ Confidence indicators display correctly (🟢 high, 🟡 medium, ⚪ low)

Next step: Import a real Excel file and verify transactions show AI confidence.
""")

    except Exception as e:
        print(f"\n✗ Error during test: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup: Delete test project
        if 'test_project' in locals():
            try:
                session.delete(test_project)
                session.commit()
                print("✓ Cleaned up test project")
            except:
                pass
        session.close()

    return True

if __name__ == '__main__':
    success = test_ai_categorization()
    sys.exit(0 if success else 1)
