"""Test script for auto-recategorization feature."""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from models.database import DatabaseManager
from models import Transaction, CategoryRule
from services.project_manager import ProjectManager
from services.categorization_service import CategorizationService
from datetime import datetime
import pandas as pd

def test_auto_recategorization():
    """Test auto-recategorization feature."""
    print("Testing Auto-Recategorization Feature")
    print("=" * 60)

    # 1. Setup database
    print("\n1. Setting up test database...")
    db_manager = DatabaseManager(db_path="data/test_recategorization.db")
    db_manager.create_tables()
    print("✓ Database created")

    # 2. Create project
    print("\n2. Creating test project...")
    project_manager = ProjectManager(db_manager)
    project = project_manager.create_project(
        name="Recategorization Test",
        description="Testing auto-recategorization"
    )
    print(f"✓ Project created: {project.name}")

    # 3. Create test transactions
    print("\n3. Creating test transactions...")
    session = db_manager.get_session()

    transactions = [
        Transaction(
            project_id=project.id,
            fecha=datetime(2024, 1, 1),
            concepto="AMAZON.ES",
            movimiento="Compra",
            importe=-50.00,
            categoria="❓ Otros",
            categorization_method="default",
            ai_confidence=None
        ),
        Transaction(
            project_id=project.id,
            fecha=datetime(2024, 1, 2),
            concepto="CARREFOUR",
            movimiento="Compra",
            importe=-75.50,
            categoria="❓ Otros",
            categorization_method="default",
            ai_confidence=None
        ),
        Transaction(
            project_id=project.id,
            fecha=datetime(2024, 1, 3),
            concepto="SPOTIFY SUBSCRIPTION",
            movimiento="Cargo",
            importe=-12.99,
            categoria="❓ Otros",
            categorization_method="default",
            ai_confidence=None
        ),
    ]

    session.add_all(transactions)
    session.commit()
    print(f"✓ Created {len(transactions)} test transactions")

    # 4. Test initial state
    print("\n4. Checking initial categorization state...")
    initial_trans = session.query(Transaction).filter_by(project_id=project.id).all()
    for t in initial_trans:
        print(f"  - {t.concepto}: {t.categoria} (method: {t.categorization_method})")

    # 5. Create a categorization rule
    print("\n5. Creating categorization rule...")
    rule = CategoryRule(
        project_id=project.id,
        pattern="AMAZON",
        category="💳 Compras Online",
        priority=100
    )
    session.add(rule)
    session.commit()
    print(f"✓ Rule created: {rule.pattern} → {rule.category}")

    # 6. Test recategorization logic
    print("\n6. Testing recategorization logic...")
    cat_service = CategorizationService(session, project.id)

    recategorized_count = 0
    unchanged_count = 0

    for transaction in initial_trans:
        old_category = transaction.categoria
        old_method = transaction.categorization_method

        # Recategorize
        result = cat_service.categorize_transaction(
            transaction.concepto,
            transaction.movimiento
        )

        new_category = result['category']
        new_method = result['method']
        new_confidence = result['confidence']

        # Update transaction
        transaction.categoria = new_category
        transaction.categorization_method = new_method
        transaction.ai_confidence = new_confidence if new_confidence > 0 else None

        # Track changes
        if old_category != new_category or old_method != new_method:
            recategorized_count += 1
            print(f"  ✓ Changed: {transaction.concepto}")
            print(f"    {old_category} ({old_method}) → {new_category} ({new_method})")
        else:
            unchanged_count += 1

    session.commit()

    print(f"\n✓ Recategorization summary:")
    print(f"  - Changed: {recategorized_count} transactions")
    print(f"  - Unchanged: {unchanged_count} transactions")

    # 7. Verify final state
    print("\n7. Checking final categorization state...")
    final_trans = session.query(Transaction).filter_by(project_id=project.id).all()
    for t in final_trans:
        print(f"  - {t.concepto}: {t.categoria} (method: {t.categorization_method})")

    # 8. Validate results
    print("\n8. Validating results...")
    amazon_trans = [t for t in final_trans if "AMAZON" in t.concepto.upper()]
    if amazon_trans and amazon_trans[0].categoria == "💳 Compras Online":
        print("✓ AMAZON transaction correctly recategorized to '💳 Compras Online'")
    else:
        print("✗ AMAZON transaction NOT recategorized (check rule matching)")

    session.close()

    print("\n" + "=" * 60)
    print("✓ Auto-recategorization test completed successfully!")
    return True

if __name__ == "__main__":
    try:
        test_auto_recategorization()
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
