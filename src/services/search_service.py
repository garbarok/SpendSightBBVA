"""Advanced search and filtering service for transactions."""
from typing import List, Optional
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from models import Transaction


class SearchService:
    """
    Provides advanced search and filtering capabilities for transactions.

    Supports filtering by:
    - Text (concept/description)
    - Date range
    - Amount range
    - Categories (multiple selection)
    - Tags (multiple selection)
    """

    def __init__(self, db_session: Session, project_id: int):
        """
        Initialize search service.

        Args:
            db_session: SQLAlchemy database session
            project_id: Current project ID
        """
        self.db_session = db_session
        self.project_id = project_id

    def search(
        self,
        text: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        amount_min: Optional[float] = None,
        amount_max: Optional[float] = None,
        categories: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        sort_by: str = "fecha",
        sort_desc: bool = True
    ) -> List[Transaction]:
        """
        Search transactions with multiple filters.

        Args:
            text: Text to search in concept/description (case-insensitive)
            date_from: Start date (inclusive)
            date_to: End date (inclusive)
            amount_min: Minimum amount (inclusive, absolute value)
            amount_max: Maximum amount (inclusive, absolute value)
            categories: List of categories to include
            tags: List of tags to include (any match)
            sort_by: Field to sort by ('fecha', 'importe', 'categoria')
            sort_desc: Sort descending if True, ascending if False

        Returns:
            List of matching Transaction objects
        """
        # Start with base query
        query = self.db_session.query(Transaction).filter(
            Transaction.project_id == self.project_id
        )

        # Apply text filter
        if text:
            text_pattern = f"%{text}%"
            query = query.filter(
                or_(
                    Transaction.concepto.ilike(text_pattern),
                    Transaction.movimiento.ilike(text_pattern)
                )
            )

        # Apply date range filter
        if date_from:
            query = query.filter(Transaction.fecha >= datetime.combine(date_from, datetime.min.time()))
        if date_to:
            query = query.filter(Transaction.fecha <= datetime.combine(date_to, datetime.max.time()))

        # Apply amount range filter (use absolute values)
        if amount_min is not None:
            query = query.filter(
                or_(
                    Transaction.importe >= amount_min,
                    Transaction.importe <= -amount_min
                )
            )
        if amount_max is not None:
            query = query.filter(
                and_(
                    Transaction.importe <= amount_max,
                    Transaction.importe >= -amount_max
                )
            )

        # Apply category filter
        if categories:
            query = query.filter(Transaction.categoria.in_(categories))

        # Execute query
        results = query.all()

        # Apply tag filter (post-query since tags are JSON)
        if tags:
            results = [
                txn for txn in results
                if any(tag in txn.get_tags() for tag in tags)
            ]

        # Sort results
        if sort_by == "fecha":
            results.sort(key=lambda t: t.fecha, reverse=sort_desc)
        elif sort_by == "importe":
            results.sort(key=lambda t: abs(t.importe), reverse=sort_desc)
        elif sort_by == "categoria":
            results.sort(key=lambda t: t.categoria, reverse=sort_desc)

        return results

    def get_all_categories(self) -> List[str]:
        """
        Get list of all unique categories in the project.

        Returns:
            Sorted list of category names
        """
        categories = (
            self.db_session.query(Transaction.categoria)
            .filter(Transaction.project_id == self.project_id)
            .distinct()
            .all()
        )

        return sorted([cat[0] for cat in categories if cat[0]])

    def get_all_tags(self) -> List[str]:
        """
        Get list of all unique tags used in the project.

        Returns:
            Sorted list of tag names
        """
        transactions = (
            self.db_session.query(Transaction)
            .filter(Transaction.project_id == self.project_id)
            .all()
        )

        # Extract all tags
        all_tags = set()
        for txn in transactions:
            all_tags.update(txn.get_tags())

        return sorted(all_tags)

    def quick_search(self, text: str, limit: int = 50) -> List[Transaction]:
        """
        Quick text search across all transactions.

        Args:
            text: Text to search for
            limit: Maximum number of results

        Returns:
            List of matching transactions (most recent first)
        """
        if not text:
            return []

        text_pattern = f"%{text}%"

        results = (
            self.db_session.query(Transaction)
            .filter(
                Transaction.project_id == self.project_id,
                or_(
                    Transaction.concepto.ilike(text_pattern),
                    Transaction.movimiento.ilike(text_pattern),
                    Transaction.categoria.ilike(text_pattern)
                )
            )
            .order_by(Transaction.fecha.desc())
            .limit(limit)
            .all()
        )

        return results

    def search_by_amount(self, target_amount: float, tolerance: float = 1.0) -> List[Transaction]:
        """
        Find transactions with amounts close to a target value.

        Args:
            target_amount: Target amount to search for
            tolerance: Acceptable difference (default ±1.0)

        Returns:
            List of matching transactions
        """
        min_amount = target_amount - tolerance
        max_amount = target_amount + tolerance

        results = (
            self.db_session.query(Transaction)
            .filter(
                Transaction.project_id == self.project_id,
                and_(
                    Transaction.importe >= min_amount,
                    Transaction.importe <= max_amount
                )
            )
            .order_by(Transaction.fecha.desc())
            .all()
        )

        return results

    def get_transactions_by_date_range(
        self,
        start_date: date,
        end_date: date
    ) -> List[Transaction]:
        """
        Get all transactions within a date range.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            List of transactions sorted by date
        """
        results = (
            self.db_session.query(Transaction)
            .filter(
                Transaction.project_id == self.project_id,
                Transaction.fecha >= datetime.combine(start_date, datetime.min.time()),
                Transaction.fecha <= datetime.combine(end_date, datetime.max.time())
            )
            .order_by(Transaction.fecha.asc())
            .all()
        )

        return results

    def get_transactions_by_category(self, category: str) -> List[Transaction]:
        """
        Get all transactions in a specific category.

        Args:
            category: Category name

        Returns:
            List of transactions sorted by date (newest first)
        """
        results = (
            self.db_session.query(Transaction)
            .filter(
                Transaction.project_id == self.project_id,
                Transaction.categoria == category
            )
            .order_by(Transaction.fecha.desc())
            .all()
        )

        return results

    def get_transactions_by_tag(self, tag: str) -> List[Transaction]:
        """
        Get all transactions with a specific tag.

        Args:
            tag: Tag name

        Returns:
            List of transactions sorted by date (newest first)
        """
        # Have to load all and filter in Python since tags are JSON
        transactions = (
            self.db_session.query(Transaction)
            .filter(Transaction.project_id == self.project_id)
            .order_by(Transaction.fecha.desc())
            .all()
        )

        return [txn for txn in transactions if txn.has_tag(tag)]
