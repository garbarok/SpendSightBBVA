"""Transaction embedding cache for faster AI categorization."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, LargeBinary, Index
from datetime import datetime
import numpy as np
from .database import Base


class TransactionEmbedding(Base):
    """
    Caches embedding vectors for transaction text to avoid recomputation.

    Each embedding is tied to specific transaction text (concepto + movimiento hash).
    This significantly speeds up categorization by avoiding model re-inference.
    """
    __tablename__ = 'transaction_embeddings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)

    # Text hash for lookup (MD5 of concepto + movimiento)
    text_hash = Column(String(32), nullable=False, index=True, unique=True)

    # Original text (for debugging/verification)
    concepto = Column(String(500), nullable=False)
    movimiento = Column(String(100), nullable=True)

    # Embedding vector (stored as binary blob)
    # For all-MiniLM-L6-v2: 384-dimensional float32 vector
    embedding = Column(LargeBinary, nullable=False)

    # Cache metadata
    model_version = Column(String(50), nullable=False, default='all-MiniLM-L6-v2')
    times_used = Column(Integer, default=0, nullable=False)
    last_used = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Indexes for performance
    __table_args__ = (
        Index('idx_project_hash', 'project_id', 'text_hash'),
        Index('idx_model_version', 'model_version'),
    )

    def __repr__(self):
        return f"<TransactionEmbedding(id={self.id}, hash='{self.text_hash[:8]}...', times_used={self.times_used})>"

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
        embedding_array = np.frombuffer(self.embedding, dtype=np.float32)
        return embedding_array

    def increment_usage(self) -> None:
        """Increment usage counter and update last_used timestamp."""
        self.times_used += 1
        self.last_used = datetime.utcnow()

    @staticmethod
    def compute_text_hash(concepto: str, movimiento: str = None) -> str:
        """
        Compute MD5 hash of transaction text for cache lookup.

        Args:
            concepto: Transaction concept
            movimiento: Movement type (optional)

        Returns:
            32-character hex string (MD5 hash)
        """
        import hashlib

        text = concepto
        if movimiento:
            text = f"{concepto} {movimiento}"

        # Create MD5 hash
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    @property
    def text(self) -> str:
        """Get combined text representation (concepto + movimiento)."""
        if self.movimiento:
            return f"{self.concepto} {self.movimiento}"
        return self.concepto
