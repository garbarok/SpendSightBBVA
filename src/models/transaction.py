"""Transaction ORM model."""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import json
from typing import List
from .database import Base

class Transaction(Base):
    """
    Represents a bank transaction.

    Stores all transaction data including manual edits to categories.
    """
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)

    # Transaction data from BBVA Excel
    fecha = Column(DateTime, nullable=False)  # Transaction date
    concepto = Column(Text, nullable=False)   # Transaction description
    movimiento = Column(String(50), nullable=True)  # Transaction type (e.g., "Pago con tarjeta")
    importe = Column(Float, nullable=False)  # Amount (negative for expenses, positive for income)

    # Categorization
    categoria = Column(String(100), nullable=False, index=True)  # Category (manual or auto)
    categoria_original = Column(String(100), nullable=True)  # Original auto-assigned category

    # AI Categorization metadata
    ai_confidence = Column(Float, nullable=True)  # AI confidence score (0.0-1.0)
    categorization_method = Column(String(20), nullable=True)  # 'rule', 'ai', 'keyword', 'manual'
    movement_type_enum = Column(String(50), nullable=True)  # Standardized movement type enum

    # Tags (JSON array stored as TEXT)
    tags = Column(Text, nullable=True)  # JSON array: ["work", "reimbursable", "vacation"]

    # Metadata
    source_file = Column(String(255), nullable=True)  # Original Excel filename
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Indexes for performance
    __table_args__ = (
        Index('idx_project_date', 'project_id', 'fecha'),
        Index('idx_project_category', 'project_id', 'categoria'),
    )

    def __repr__(self):
        return f"<Transaction(id={self.id}, fecha={self.fecha}, importe={self.importe}, categoria='{self.categoria}')>"

    @property
    def is_manually_edited(self):
        """Check if category was manually edited."""
        return self.categoria_original is not None and self.categoria != self.categoria_original

    def get_tags(self) -> List[str]:
        """
        Get transaction tags as a list.

        Returns:
            List of tag strings, or empty list if no tags
        """
        if not self.tags:
            return []
        try:
            return json.loads(self.tags)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_tags(self, tags: List[str]) -> None:
        """
        Set transaction tags from a list.

        Args:
            tags: List of tag strings
        """
        if not tags:
            self.tags = None
        else:
            # Remove duplicates and sort
            unique_tags = sorted(set(tags))
            self.tags = json.dumps(unique_tags)

    def add_tag(self, tag: str) -> None:
        """
        Add a single tag to the transaction.

        Args:
            tag: Tag string to add
        """
        current_tags = self.get_tags()
        if tag not in current_tags:
            current_tags.append(tag)
            self.set_tags(current_tags)

    def remove_tag(self, tag: str) -> None:
        """
        Remove a single tag from the transaction.

        Args:
            tag: Tag string to remove
        """
        current_tags = self.get_tags()
        if tag in current_tags:
            current_tags.remove(tag)
            self.set_tags(current_tags)

    def has_tag(self, tag: str) -> bool:
        """
        Check if transaction has a specific tag.

        Args:
            tag: Tag string to check

        Returns:
            True if tag exists, False otherwise
        """
        return tag in self.get_tags()

    @property
    def confidence_indicator(self) -> str:
        """
        Get visual indicator for AI confidence level.

        Returns:
            Emoji indicator: 🟢 high (>85%), 🟡 medium (70-85%), ⚪ low/manual
        """
        if not self.ai_confidence:
            return "⚪"  # No AI confidence (manual or keyword-based)

        if self.ai_confidence >= 0.85:
            return "🟢"  # High confidence
        elif self.ai_confidence >= 0.70:
            return "🟡"  # Medium confidence
        else:
            return "⚪"  # Low confidence

    @property
    def was_ai_categorized(self) -> bool:
        """Check if transaction was categorized using AI."""
        return self.categorization_method == 'ai'

    def set_ai_categorization(self, category: str, confidence: float) -> None:
        """
        Set category with AI metadata.

        Args:
            category: Category name
            confidence: AI confidence score (0.0-1.0)
        """
        self.categoria = category
        self.ai_confidence = confidence
        self.categorization_method = 'ai'

    def set_manual_categorization(self, category: str) -> None:
        """
        Set category as manually edited.

        Args:
            category: Category name
        """
        if not self.is_manually_edited:
            self.categoria_original = self.categoria
        self.categoria = category
        self.categorization_method = 'manual'
        self.ai_confidence = None
