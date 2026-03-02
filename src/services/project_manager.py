"""Project lifecycle management service."""
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from models.database import DatabaseManager
from models.project import Project
from models.transaction import Transaction

class ProjectManager:
    """Manages project lifecycle operations (CRUD, activation, etc.)."""

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize project manager.

        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager

    def create_project(self, name: str, description: str = None) -> Project:
        """
        Create a new project.

        Args:
            name: Project name (must be unique)
            description: Optional project description

        Returns:
            Created project instance

        Raises:
            ValueError: If project with same name already exists
        """
        session = self.db_manager.get_session()
        try:
            # Check if project already exists
            existing = session.query(Project).filter_by(name=name).first()
            if existing:
                raise ValueError(f"Project with name '{name}' already exists")

            # Create new project
            project = Project(name=name, description=description)
            session.add(project)
            session.commit()
            session.refresh(project)
            return project
        finally:
            session.close()

    def get_project_by_id(self, project_id: int) -> Optional[Project]:
        """
        Get project by ID.

        Args:
            project_id: Project ID

        Returns:
            Project instance or None if not found
        """
        session = self.db_manager.get_session()
        try:
            return session.query(Project).filter_by(id=project_id).first()
        finally:
            session.close()

    def get_project_by_name(self, name: str) -> Optional[Project]:
        """
        Get project by name.

        Args:
            name: Project name

        Returns:
            Project instance or None if not found
        """
        session = self.db_manager.get_session()
        try:
            return session.query(Project).filter_by(name=name).first()
        finally:
            session.close()

    def list_projects(self) -> List[Project]:
        """
        List all projects ordered by most recently updated.

        Returns:
            List of project instances
        """
        session = self.db_manager.get_session()
        try:
            return session.query(Project).order_by(Project.updated_at.desc()).all()
        finally:
            session.close()

    def delete_project(self, project_id: int) -> bool:
        """
        Delete a project and all its associated data.

        Args:
            project_id: Project ID

        Returns:
            True if deleted, False if not found
        """
        session = self.db_manager.get_session()
        try:
            project = session.query(Project).filter_by(id=project_id).first()
            if not project:
                return False

            session.delete(project)
            session.commit()
            return True
        finally:
            session.close()

    def get_project_stats(self, project_id: int) -> dict:
        """
        Get statistics for a project.

        Args:
            project_id: Project ID

        Returns:
            Dictionary with stats (transaction_count, date_range, etc.)
        """
        session = self.db_manager.get_session()
        try:
            transactions = session.query(Transaction).filter_by(project_id=project_id).all()

            if not transactions:
                return {
                    'transaction_count': 0,
                    'earliest_date': None,
                    'latest_date': None,
                    'total_income': 0.0,
                    'total_expenses': 0.0,
                }

            dates = [t.fecha for t in transactions]
            amounts = [t.importe for t in transactions]

            return {
                'transaction_count': len(transactions),
                'earliest_date': min(dates),
                'latest_date': max(dates),
                'total_income': sum(a for a in amounts if a > 0),
                'total_expenses': sum(a for a in amounts if a < 0),
            }
        finally:
            session.close()
