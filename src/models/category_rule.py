"""CategoryRule ORM model for learning user categorization preferences."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from datetime import datetime
from .database import Base

class CategoryRule(Base):
    """
    Represents a user-created rule for automatic categorization.

    Rules are learned from manual category edits. When a user changes
    a transaction's category, they can create a rule to auto-categorize
    similar transactions in the future.

    Priority system:
    - 100: User-created rules (highest priority)
    - 50: Exact match hardcoded rules
    - 25: Fuzzy match hardcoded rules
    - 0: Default fallback
    """
    __tablename__ = 'category_rules'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)

    # Rule definition
    pattern = Column(String(255), nullable=False)  # Text pattern to match (case-insensitive)
    category = Column(String(100), nullable=False)  # Category to assign
    priority = Column(Integer, nullable=False, default=100)  # User rules always priority 100

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Indexes for performance
    __table_args__ = (
        Index('idx_project_priority', 'project_id', 'priority'),
    )

    def __repr__(self):
        return f"<CategoryRule(id={self.id}, pattern='{self.pattern}', category='{self.category}', priority={self.priority})>"

    def match(self, text: str) -> bool:
        """
        Check if this rule matches the given text.

        Args:
            text: Transaction concept/description to match against

        Returns:
            True if pattern is found in text (case-insensitive), False otherwise
        """
        if not text or not self.pattern:
            return False

        return self.pattern.lower() in text.lower()

    def apply_to_transaction(self, transaction):
        """
        Apply this rule's category to a transaction if it matches.

        Args:
            transaction: Transaction object to potentially categorize

        Returns:
            True if rule was applied, False if no match
        """
        if self.match(transaction.concepto):
            transaction.categoria = self.category
            return True
        return False
