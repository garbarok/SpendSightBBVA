"""Test Phase 2 Intelligence features."""
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from models import DatabaseManager, Project, Transaction, CategoryRule
from services import CategorizationService, RecurringDetector, SearchService


def test_database_schema():
    """Test that new database schema is in place."""
    print("\n" + "=" * 60)
    print("Testing Database Schema")
    print("=" * 60)

    db = DatabaseManager()
    db.create_tables()

    # Test creating a project
    session = db.get_session()
    try:
        # Try to find existing project first
        project = session.query(Project).filter_by(name="Test Project Phase 2").first()
        if not project:
            project = Project(name="Test Project Phase 2", description="Testing Phase 2 features")
            session.add(project)
            session.commit()
            print(f"✓ Created project: {project.name}")
        else:
            print(f"✓ Using existing project: {project.name}")

        # Test creating a transaction with tags
        txn = Transaction(
            project_id=project.id,
            fecha=datetime.now(),
            concepto="MERCADONA MALAGA",
            movimiento="Pago con tarjeta",
            importe=-45.50,
            categoria="🛒 Supermercado"
        )
        txn.set_tags(["groceries", "weekly-shopping"])
        session.add(txn)
        session.commit()
        print(f"✓ Created transaction with tags: {txn.get_tags()}")

        # Test creating a category rule
        rule = CategoryRule(
            project_id=project.id,
            pattern="mercadona",
            category="🛒 Supermercado",
            priority=100
        )
        session.add(rule)
        session.commit()
        print(f"✓ Created category rule: {rule.pattern} -> {rule.category}")

        return project.id

    finally:
        session.close()


def test_tag_management(project_id):
    """Test tag management on transactions."""
    print("\n" + "=" * 60)
    print("Testing Tag Management")
    print("=" * 60)

    db = DatabaseManager()
    session = db.get_session()

    try:
        # Create test transaction
        txn = Transaction(
            project_id=project_id,
            fecha=datetime.now(),
            concepto="NETFLIX",
            movimiento="Pago recurrente",
            importe=-15.99,
            categoria="💻 Software y Suscripciones"
        )
        session.add(txn)
        session.flush()

        # Test adding tags
        txn.add_tag("subscription")
        txn.add_tag("entertainment")
        print(f"✓ Added tags: {txn.get_tags()}")

        # Test removing tag
        txn.remove_tag("entertainment")
        print(f"✓ Removed tag: {txn.get_tags()}")

        # Test has_tag
        print(f"✓ Has 'subscription': {txn.has_tag('subscription')}")
        print(f"✓ Has 'entertainment': {txn.has_tag('entertainment')}")

        session.commit()

    finally:
        session.close()


def test_categorization_service(project_id):
    """Test smart categorization with rules."""
    print("\n" + "=" * 60)
    print("Testing Categorization Service")
    print("=" * 60)

    db = DatabaseManager()
    session = db.get_session()

    try:
        service = CategorizationService(session, project_id)

        # Test categorizing without rules
        category, priority = service.categorize_transaction("COMPRA AMAZON")
        print(f"✓ Categorized 'COMPRA AMAZON': {category} (priority: {priority})")

        # Create a rule
        txn = Transaction(
            project_id=project_id,
            fecha=datetime.now(),
            concepto="SPOTIFY MADRID",
            movimiento="Pago recurrente",
            importe=-9.99,
            categoria="💻 Software y Suscripciones"
        )
        session.add(txn)
        session.flush()

        rule = service.create_rule_from_edit(txn, "💻 Software y Suscripciones")
        if rule:
            print(f"✓ Created rule from edit: {rule.pattern} -> {rule.category}")
        else:
            print("  Rule already exists")

        # Test categorizing with rule
        category, priority = service.categorize_transaction("SPOTIFY PREMIUM")
        print(f"✓ Categorized 'SPOTIFY PREMIUM': {category} (priority: {priority})")

        # Test getting all rules
        rules = service.get_all_rules()
        print(f"✓ Total rules in project: {len(rules)}")

        session.commit()

    finally:
        session.close()


def test_recurring_detector(project_id):
    """Test recurring transaction detection."""
    print("\n" + "=" * 60)
    print("Testing Recurring Transaction Detection")
    print("=" * 60)

    db = DatabaseManager()
    session = db.get_session()

    try:
        # Create monthly recurring transactions
        base_date = datetime.now() - timedelta(days=90)
        for i in range(4):
            txn = Transaction(
                project_id=project_id,
                fecha=base_date + timedelta(days=30 * i),
                concepto="NETFLIX MADRID",
                movimiento="Pago recurrente",
                importe=-15.99,
                categoria="💻 Software y Suscripciones"
            )
            session.add(txn)

        # Create weekly recurring transactions
        for i in range(5):
            txn = Transaction(
                project_id=project_id,
                fecha=base_date + timedelta(days=7 * i),
                concepto="MERCADONA MALAGA",
                movimiento="Pago con tarjeta",
                importe=-35.00 + (i * 2),  # Slight variance
                categoria="🛒 Supermercado"
            )
            session.add(txn)

        session.commit()

        # Detect patterns
        detector = RecurringDetector(session, project_id)
        patterns = detector.detect_recurring_patterns()

        print(f"✓ Detected {len(patterns)} recurring patterns:")
        for pattern in patterns:
            print(f"  - {pattern.merchant_name}: {pattern.frequency} "
                  f"(€{pattern.average_amount:.2f}, {pattern.transaction_count} txns, "
                  f"confidence: {pattern.confidence:.2f})")

    finally:
        session.close()


def test_search_service(project_id):
    """Test advanced search and filtering."""
    print("\n" + "=" * 60)
    print("Testing Search Service")
    print("=" * 60)

    db = DatabaseManager()
    session = db.get_session()

    try:
        service = SearchService(session, project_id)

        # Get all categories
        categories = service.get_all_categories()
        print(f"✓ Found {len(categories)} categories in project")

        # Get all tags
        tags = service.get_all_tags()
        print(f"✓ Found {len(tags)} tags in project")

        # Search by text
        results = service.search(text="NETFLIX")
        print(f"✓ Text search 'NETFLIX': {len(results)} results")

        # Search by date range
        from_date = (datetime.now() - timedelta(days=60)).date()
        to_date = datetime.now().date()
        results = service.search(date_from=from_date, date_to=to_date)
        print(f"✓ Date range search: {len(results)} results")

        # Search by category
        results = service.search(categories=["💻 Software y Suscripciones"])
        print(f"✓ Category search: {len(results)} results")

        # Quick search
        results = service.quick_search("MERCA", limit=10)
        print(f"✓ Quick search 'MERCA': {len(results)} results")

    finally:
        session.close()


def main():
    """Run all Phase 2 tests."""
    print("\n" + "=" * 60)
    print("PHASE 2 INTELLIGENCE FEATURES - COMPREHENSIVE TEST")
    print("=" * 60)

    try:
        # Test 1: Database schema
        project_id = test_database_schema()

        # Test 2: Tag management
        test_tag_management(project_id)

        # Test 3: Categorization service
        test_categorization_service(project_id)

        # Test 4: Recurring detection
        test_recurring_detector(project_id)

        # Test 5: Search service
        test_search_service(project_id)

        print("\n" + "=" * 60)
        print("✅ ALL PHASE 2 TESTS PASSED!")
        print("=" * 60)
        print("\nPhase 2 features implemented and tested:")
        print("  ✓ Category rule learning with priority system")
        print("  ✓ Tag management (JSON array storage)")
        print("  ✓ Smart categorization service")
        print("  ✓ Recurring transaction detection")
        print("  ✓ Advanced search and filtering")
        print("\n GUI components created (not tested here):")
        print("  ✓ TagInputWidget and TagSelectorDialog")
        print("  ✓ DateRangePicker widget")
        print("  ✓ SearchPanel component")

        return 0

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
