"""AI-powered categorization service using sentence-transformers."""
from typing import List, Tuple, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import numpy as np
from datetime import datetime
import os

from models import CategoryTrainingExample, TransactionEmbedding, Transaction
from utils.logger import setup_logger

logger = setup_logger(__name__)


class AICategorizationService:
    """
    Semantic categorization using sentence-transformers.

    Model: all-MiniLM-L6-v2 (~80MB, 384-dim embeddings)
    Strategy: Cosine similarity against training examples
    """

    # Confidence thresholds
    HIGH_CONFIDENCE = 0.85  # Auto-apply with 🟢 indicator
    MEDIUM_CONFIDENCE = 0.70  # Apply but mark uncertain with 🟡 indicator

    # Model configuration
    MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2'
    EMBEDDING_DIM = 384

    def __init__(self, db_session: Session, project_id: int):
        """
        Initialize AI categorization service.

        Args:
            db_session: SQLAlchemy database session
            project_id: Current project ID
        """
        self.db_session = db_session
        self.project_id = project_id
        self._model = None
        self._training_cache = None

    def _load_model(self):
        """
        Lazy-load the sentence-transformers model.

        Returns:
            SentenceTransformer model instance
        """
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                model_path = self._get_model_path()

                # Check if model exists locally
                if os.path.exists(model_path):
                    logger.info(f"Loading model from {model_path}")
                    self._model = SentenceTransformer(model_path)
                else:
                    logger.info(f"Downloading model {self.MODEL_NAME}...")
                    self._model = SentenceTransformer(self.MODEL_NAME)
                    # Save for future use
                    self._model.save(model_path)
                    logger.info(f"Model saved to {model_path}")

            except ImportError:
                logger.error(
                    "sentence-transformers not installed. "
                    "Install with: pip install sentence-transformers"
                )
                raise
            except Exception as e:
                logger.error(f"Failed to load AI model: {e}", exc_info=True)
                raise

        return self._model

    def _get_model_path(self) -> str:
        """
        Get local path for storing the model.

        Returns:
            Path to model directory
        """
        from pathlib import Path

        # Store in data/models directory
        model_dir = Path(__file__).parent.parent.parent / 'data' / 'models' / 'sentence-transformers'
        model_dir.mkdir(parents=True, exist_ok=True)

        return str(model_dir / 'all-MiniLM-L6-v2')

    def _load_training_examples(self) -> List[CategoryTrainingExample]:
        """
        Load training examples from database with caching.

        Returns:
            List of CategoryTrainingExample objects
        """
        if self._training_cache is None:
            self._training_cache = (
                self.db_session.query(CategoryTrainingExample)
                .filter(CategoryTrainingExample.project_id == self.project_id)
                .all()
            )
            logger.info(f"Loaded {len(self._training_cache)} training examples")

        return self._training_cache

    def invalidate_cache(self):
        """Invalidate training example cache, forcing reload on next use."""
        self._training_cache = None

    def generate_embedding(self, concepto: str, movimiento: str = None) -> np.ndarray:
        """
        Generate embedding vector for transaction text.

        Args:
            concepto: Transaction concept/description
            movimiento: Movement type (optional)

        Returns:
            numpy array of shape (384,) - embedding vector
        """
        # Combine text
        text = concepto
        if movimiento:
            text = f"{concepto} {movimiento}"

        # Compute hash for caching
        text_hash = TransactionEmbedding.compute_text_hash(concepto, movimiento)

        # Try to get cached embedding (with retry on session errors)
        max_retries = 2
        for attempt in range(max_retries):
            try:
                cached = (
                    self.db_session.query(TransactionEmbedding)
                    .filter(
                        TransactionEmbedding.project_id == self.project_id,
                        TransactionEmbedding.text_hash == text_hash
                    )
                    .first()
                )

                if cached:
                    # Update usage stats (best effort, ignore errors)
                    try:
                        cached.increment_usage()
                        self.db_session.commit()
                    except Exception:
                        self.db_session.rollback()
                    return cached.get_embedding()

                # Not cached, generate new embedding
                break

            except Exception as e:
                self.db_session.rollback()
                if attempt == max_retries - 1:
                    logger.warning(f"Failed to query cache after {max_retries} attempts: {e}")
                    # Continue to generate embedding without cache
                    break

        # Generate new embedding
        model = self._load_model()
        embedding = model.encode(text, convert_to_numpy=True)

        # Try to cache it (best effort, don't fail if can't cache)
        try:
            cache_entry = TransactionEmbedding(
                project_id=self.project_id,
                text_hash=text_hash,
                concepto=concepto,
                movimiento=movimiento,
                model_version=self.MODEL_NAME
            )
            cache_entry.set_embedding(embedding)

            self.db_session.add(cache_entry)
            self.db_session.commit()
            logger.debug(f"Cached embedding for '{concepto[:30]}...'")

        except IntegrityError:
            # Already cached by another process - that's OK
            self.db_session.rollback()
            logger.debug(f"Embedding '{text_hash[:8]}...' already cached concurrently")

        except Exception as e:
            # Other error - log but don't fail
            self.db_session.rollback()
            logger.debug(f"Could not cache embedding: {e}")

        return embedding

    def categorize_with_confidence(
        self,
        concepto: str,
        movimiento: str = None
    ) -> Tuple[Optional[str], float, List[Dict[str, any]]]:
        """
        Categorize transaction using AI with confidence score.

        Args:
            concepto: Transaction concept/description
            movimiento: Movement type (optional)

        Returns:
            Tuple of:
            - category (str or None if no match)
            - confidence (float 0.0-1.0)
            - alternatives (list of dicts with 'category' and 'confidence')
        """
        try:
            # Load training examples
            training_examples = self._load_training_examples()

            if not training_examples:
                logger.debug("No training examples available for AI categorization")
                return (None, 0.0, [])

            # Generate embedding for transaction
            transaction_embedding = self.generate_embedding(concepto, movimiento)

            # Calculate similarities
            similarities = []
            for example in training_examples:
                example_embedding = example.get_embedding()

                # Cosine similarity
                similarity = self._cosine_similarity(
                    transaction_embedding,
                    example_embedding
                )

                similarities.append({
                    'category': example.category,
                    'confidence': float(similarity),
                    'example_id': example.id,
                    'times_used': example.times_used,
                    'created_at': example.created_at
                })

            # Sort by confidence (descending)
            similarities.sort(key=lambda x: x['confidence'], reverse=True)

            # Aggregate by category (take top-3 matches per category)
            category_scores = {}
            for sim in similarities:
                cat = sim['category']
                if cat not in category_scores:
                    category_scores[cat] = []

                # Keep top-3 matches per category
                if len(category_scores[cat]) < 3:
                    category_scores[cat].append(sim['confidence'])

            # Calculate weighted average per category
            category_confidences = {}
            for cat, scores in category_scores.items():
                # Weight: 0.5 for best, 0.3 for second, 0.2 for third
                weights = [0.5, 0.3, 0.2][:len(scores)]
                weighted_score = sum(s * w for s, w in zip(scores, weights))
                category_confidences[cat] = weighted_score

            # Get best category
            if not category_confidences:
                return (None, 0.0, [])

            best_category = max(category_confidences.items(), key=lambda x: x[1])
            category, confidence = best_category

            # Build alternatives (top 3 categories)
            alternatives = [
                {'category': cat, 'confidence': conf}
                for cat, conf in sorted(
                    category_confidences.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:3]
            ]

            # Update usage stats for matched examples
            if confidence >= self.MEDIUM_CONFIDENCE:
                self._update_example_usage(similarities[0]['example_id'])

            return (category, confidence, alternatives)

        except Exception as e:
            logger.error(f"AI categorization failed: {e}", exc_info=True)
            return (None, 0.0, [])

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Similarity score (0.0-1.0)
        """
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    def _update_example_usage(self, example_id: int):
        """
        Update usage statistics for a training example.

        Args:
            example_id: ID of the training example
        """
        try:
            example = self.db_session.query(CategoryTrainingExample).get(example_id)
            if example:
                example.increment_usage()
                self.db_session.commit()
        except IntegrityError:
            # Ignore concurrent usage updates
            self.db_session.rollback()
            logger.debug(f"Concurrent update ignored for example {example_id}")

    def learn_from_correction(
        self,
        transaction: Transaction,
        new_category: str,
        source: str = 'manual'
    ) -> Optional[CategoryTrainingExample]:
        """
        Learn from a manual category correction.

        Creates a training example from the corrected transaction.

        Args:
            transaction: Transaction that was corrected
            new_category: New category assigned by user
            source: Learning source ('manual', 'rule', 'initial')

        Returns:
            CategoryTrainingExample if created, None if error
        """
        try:
            # Check if similar example already exists
            existing = (
                self.db_session.query(CategoryTrainingExample)
                .filter(
                    CategoryTrainingExample.project_id == self.project_id,
                    CategoryTrainingExample.concepto == transaction.concepto,
                    CategoryTrainingExample.category == new_category
                )
                .first()
            )

            if existing:
                logger.debug(f"Training example already exists for '{transaction.concepto}'")
                return None

            # Generate embedding
            embedding = self.generate_embedding(
                transaction.concepto,
                transaction.movimiento
            )

            # Create training example
            example = CategoryTrainingExample(
                project_id=self.project_id,
                concepto=transaction.concepto,
                movimiento=transaction.movimiento,
                category=new_category,
                source=source,
                confidence=1.0  # Manual corrections are 100% confident
            )
            example.set_embedding(embedding)

            self.db_session.add(example)

            try:
                self.db_session.commit()
            except IntegrityError:
                # Example already created by concurrent process
                self.db_session.rollback()
                logger.debug(f"Training example already created concurrently for '{transaction.concepto}'")
                return None

            # Invalidate cache
            self.invalidate_cache()

            logger.info(
                f"✓ Learned from correction: '{transaction.concepto}' → '{new_category}'"
            )

            return example

        except Exception as e:
            logger.error(f"Failed to learn from correction: {e}", exc_info=True)
            self.db_session.rollback()
            return None

    def retrain_from_transactions(
        self,
        transactions: List[Transaction],
        source: str = 'initial'
    ) -> int:
        """
        Batch training from multiple transactions.

        Args:
            transactions: List of transactions to learn from
            source: Learning source ('initial', 'manual', 'rule')

        Returns:
            Number of training examples created
        """
        created_count = 0

        logger.info(f"Starting batch training from {len(transactions)} transactions...")

        for transaction in transactions:
            example = self.learn_from_correction(
                transaction,
                transaction.categoria,
                source=source
            )
            if example:
                created_count += 1

        logger.info(f"✓ Batch training complete: {created_count} examples created")

        return created_count

    def get_training_stats(self) -> Dict[str, any]:
        """
        Get statistics about training data.

        Returns:
            Dictionary with training statistics
        """
        examples = self._load_training_examples()

        if not examples:
            return {
                'total_examples': 0,
                'categories': {},
                'sources': {},
                'avg_usage': 0
            }

        # Count by category
        categories = {}
        for ex in examples:
            categories[ex.category] = categories.get(ex.category, 0) + 1

        # Count by source
        sources = {}
        for ex in examples:
            sources[ex.source] = sources.get(ex.source, 0) + 1

        # Average usage
        avg_usage = sum(ex.times_used for ex in examples) / len(examples)

        return {
            'total_examples': len(examples),
            'categories': categories,
            'sources': sources,
            'avg_usage': avg_usage,
            'most_used_category': max(categories.items(), key=lambda x: x[1])[0] if categories else None
        }
