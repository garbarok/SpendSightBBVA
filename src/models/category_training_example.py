"""Category training example model for AI learning."""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, LargeBinary, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import numpy as np
from .database import Base


class CategoryTrainingExample(Base):
    """
    Stores training examples for AI-powered categorization.

    Each example represents a learned pattern linking transaction text
    (concepto + movimiento) to a category, along with its embedding vector.
    """
    __tablename__ = 'category_training_examples'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)

    # Training data
    concepto = Column(String(500), nullable=False)  # Transaction concept
    movimiento = Column(String(100), nullable=True)  # Movement type
    category = Column(String(100), nullable=False, index=True)  # Target category

    # Embedding vector (stored as binary blob)
    # For all-MiniLM-L6-v2: 384-dimensional float32 vector
    embedding = Column(LargeBinary, nullable=False)  # numpy array serialized

    # Learning metadata
    source = Column(String(50), nullable=False, default='manual')  # 'manual', 'rule', 'initial'
    confidence = Column(Float, nullable=True)  # Optional confidence score
    times_used = Column(Integer, default=0, nullable=False)  # Track usage frequency
    last_used = Column(DateTime, nullable=True)  # Last time this example was matched

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Indexes for performance
    __table_args__ = (
        Index('idx_project_category', 'project_id', 'category'),
        Index('idx_project_source', 'project_id', 'source'),
    )

    def __repr__(self):
        return f"<CategoryTrainingExample(id={self.id}, category='{self.category}', source='{self.source}')>"

    def set_embedding(self, embedding_vector: np.ndarray) -> None:
        """
        Store embedding vector as binary data.

        Args:
            embedding_vector: numpy array of shape (384,) for all-MiniLM-L6-v2
        """
        if not isinstance(embedding_vector, np.ndarray):
            raise ValueError("Embedding must be a numpy array")

        # Ensure float32 type for consistency
        embedding_float32 = embedding_vector.astype(np.float32)
        self.embedding = embedding_float32.tobytes()

    def get_embedding(self) -> np.ndarray:
        """
        Retrieve embedding vector from binary storage.

        Returns:
            numpy array of shape (384,)
        """
        if not self.embedding:
            raise ValueError("No embedding stored")

        # Reconstruct numpy array from bytes
        # For all-MiniLM-L6-v2: 384 dimensions * 4 bytes (float32) = 1536 bytes
        embedding_array = np.frombuffer(self.embedding, dtype=np.float32)
        return embedding_array

    def increment_usage(self) -> None:
        """Increment usage counter and update last_used timestamp."""
        self.times_used += 1
        self.last_used = datetime.utcnow()

    @property
    def text(self) -> str:
        """Get combined text representation (concepto + movimiento)."""
        if self.movimiento:
            return f"{self.concepto} {self.movimiento}"
        return self.concepto
