"""Excel to SQLite migration service."""
from typing import List
from pathlib import Path
import pandas as pd
from sqlalchemy.orm import Session
from models.database import DatabaseManager
from models.project import Project
from models.transaction import Transaction
from utils.data_processor import DataProcessor

class MigrationService:
    """Handles importing Excel files into SQLite database."""

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize migration service.

        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager

    def import_excel_to_project(
        self,
        project_id: int,
        file_paths: List[str],
        skip_duplicates: bool = True,
        categorization_service = None
    ) -> dict:
        """
        Import Excel files into a project.

        Args:
            project_id: Target project ID
            file_paths: List of Excel file paths to import
            skip_duplicates: If True, skip transactions with same date+concept+amount
            categorization_service: Optional CategorizationService for AI categorization during import

        Returns:
            Dictionary with import statistics (imported, skipped, errors)
        """
        session = self.db_manager.get_session()
        stats = {
            'imported': 0,
            'skipped': 0,
            'errors': []
        }

        try:
            # Verify project exists
            project = session.query(Project).filter_by(id=project_id).first()
            if not project:
                raise ValueError(f"Project with ID {project_id} not found")

            # Get existing transactions for duplicate detection
            existing_hashes = set()
            if skip_duplicates:
                existing = session.query(
                    Transaction.fecha,
                    Transaction.concepto,
                    Transaction.importe
                ).filter_by(project_id=project_id).all()
                existing_hashes = {self._transaction_hash(t.fecha, t.concepto, t.importe) for t in existing}

            # Process each file
            for file_path in file_paths:
                try:
                    # Load and clean data using existing DataProcessor
                    df = DataProcessor.load_and_clean_data(file_path)
                    # Pass categorization_service to enable AI during import
                    df = DataProcessor.analyze_transactions(df, categorization_service=categorization_service)

                    # Import each transaction
                    for _, row in df.iterrows():
                        # Check for duplicates
                        trans_hash = self._transaction_hash(row['Fecha'], row['Concepto'], row['Importe'])
                        if skip_duplicates and trans_hash in existing_hashes:
                            stats['skipped'] += 1
                            continue

                        # Create transaction with AI metadata
                        transaction = Transaction(
                            project_id=project_id,
                            fecha=row['Fecha'],
                            concepto=row['Concepto'],
                            movimiento=row.get('Movimiento', ''),
                            importe=row['Importe'],
                            categoria=row['Categoría'],
                            ai_confidence=row.get('AI_Confidence'),  # Include AI confidence from analysis
                            categorization_method=row.get('Categorization_Method'),  # Include method
                            categoria_original=None,  # First import, no manual edit yet
                            source_file=Path(file_path).name
                        )
                        session.add(transaction)
                        existing_hashes.add(trans_hash)
                        stats['imported'] += 1

                except Exception as e:
                    stats['errors'].append(f"{Path(file_path).name}: {str(e)}")

            # Commit all changes
            session.commit()

            # Update project timestamp
            project.updated_at = pd.Timestamp.now()
            session.commit()

        finally:
            session.close()

        return stats

    def _transaction_hash(self, fecha, concepto: str, importe: float) -> str:
        """
        Generate a hash for duplicate detection.

        Args:
            fecha: Transaction date
            concepto: Transaction description
            importe: Transaction amount

        Returns:
            Hash string
        """
        fecha_str = pd.Timestamp(fecha).strftime('%Y-%m-%d')
        return f"{fecha_str}|{concepto}|{importe:.2f}"

    def export_project_to_excel(self, project_id: int, output_path: str):
        """
        Export project transactions to Excel.

        Args:
            project_id: Project ID to export
            output_path: Output Excel file path
        """
        session = self.db_manager.get_session()
        try:
            # Get all transactions for project
            transactions = session.query(Transaction).filter_by(
                project_id=project_id
            ).order_by(Transaction.fecha.desc()).all()

            # Convert to DataFrame
            data = []
            for t in transactions:
                data.append({
                    'Fecha': t.fecha,
                    'Concepto': t.concepto,
                    'Movimiento': t.movimiento,
                    'Importe': t.importe,
                    'Categoría': t.categoria,
                    'Source': t.source_file
                })

            df = pd.DataFrame(data)
            df.to_excel(output_path, index=False)

        finally:
            session.close()
