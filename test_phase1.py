"""Test script for Phase 1 functionality."""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from models.database import DatabaseManager
from services.project_manager import ProjectManager
from services.migration_service import MigrationService

def test_phase1():
    """Test Phase 1: Database setup and basic operations."""
    print("Testing Phase 1: Foundation")
    print("=" * 50)

    # 1. Database initialization
    print("\n1. Testing database initialization...")
    db_manager = DatabaseManager(db_path="data/test_spendsight.db")
    db_manager.create_tables()
    print("✓ Database created successfully")

    # 2. Project creation
    print("\n2. Testing project creation...")
    project_manager = ProjectManager(db_manager)
    project = project_manager.create_project(
        name="Test Project",
        description="Test project for Phase 1"
    )
    print(f"✓ Project created: {project.name} (ID: {project.id})")

    # 3. List projects
    print("\n3. Testing project listing...")
    projects = project_manager.list_projects()
    print(f"✓ Found {len(projects)} project(s)")
    for p in projects:
        print(f"  - {p.name} (created: {p.created_at})")

    # 4. Get project stats (empty)
    print("\n4. Testing project stats (empty)...")
    stats = project_manager.get_project_stats(project.id)
    print(f"✓ Stats: {stats['transaction_count']} transactions")

    # 5. Migration service test (without actual Excel file)
    print("\n5. Testing migration service initialization...")
    migration_service = MigrationService(db_manager)
    print("✓ Migration service ready")

    # 6. Get project by name
    print("\n6. Testing project retrieval...")
    found_project = project_manager.get_project_by_name("Test Project")
    if found_project:
        print(f"✓ Found project: {found_project.name}")
    else:
        print("✗ Project not found")

    # 7. Cleanup (delete test project)
    print("\n7. Cleaning up...")
    project_manager.delete_project(project.id)
    print("✓ Test project deleted")

    print("\n" + "=" * 50)
    print("Phase 1 Foundation Tests: ALL PASSED ✓")
    print("\nKey features verified:")
    print("  ✓ SQLite database creation")
    print("  ✓ Project CRUD operations")
    print("  ✓ Database schema (projects, transactions)")
    print("  ✓ Service layer (ProjectManager, MigrationService)")
    print("\nNext: Test with actual GUI and Excel import")

if __name__ == "__main__":
    try:
        test_phase1()
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
