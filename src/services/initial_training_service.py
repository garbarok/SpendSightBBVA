"""Initial training service for bootstrapping AI from existing data."""
from typing import List, Dict, Callable, Optional
from sqlalchemy.orm import Session
from collections import defaultdict

from models import Transaction, CategoryRule
from services.ai_categorization_service import AICategorizationService
from utils.logger import setup_logger

logger = setup_logger(__name__)


class InitialTrainingService:
    """
    Builds initial AI training dataset from existing project data.

    Strategies:
    1. Learn from manually edited transactions
    2. Extract patterns from category rules
    3. Sample representative transactions from each category
    """

    def __init__(self, db_session: Session, project_id: int):
        """
        Initialize initial training service.

        Args:
            db_session: SQLAlchemy database session
            project_id: Current project ID
        """
        self.db_session = db_session
        self.project_id = project_id
        self.ai_service = AICategorizationService(db_session, project_id)

    def build_initial_training(
        self,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> Dict[str, any]:
        """
        Build initial training dataset from existing project data.

        Args:
            progress_callback: Optional callback(message, current, total)

        Returns:
            Dictionary with training statistics
        """
        logger.info("Starting initial training dataset build...")

        stats = {
            'manual_edits': 0,
            'category_rules': 0,
            'representatives': 0,
            'total_examples': 0,
            'categories_covered': 0
        }

        # STEP 1: Learn from manually edited transactions
        if progress_callback:
            progress_callback("Learning from manual edits...", 0, 3)

        manual_count = self._learn_from_manual_edits()
        stats['manual_edits'] = manual_count
        logger.info(f"Learned from {manual_count} manual edits")

        # STEP 2: Extract patterns from category rules
        if progress_callback:
            progress_callback("Extracting patterns from rules...", 1, 3)

        rules_count = self._learn_from_category_rules()
        stats['category_rules'] = rules_count
        logger.info(f"Learned from {rules_count} category rules")

        # STEP 3: Sample representative transactions
        if progress_callback:
            progress_callback("Sampling representative transactions...", 2, 3)

        representatives_count = self._sample_representatives()
        stats['representatives'] = representatives_count
        logger.info(f"Sampled {representatives_count} representative transactions")

        # Calculate totals
        stats['total_examples'] = (
            stats['manual_edits'] +
            stats['category_rules'] +
            stats['representatives']
        )

        # Get unique categories covered
        training_stats = self.ai_service.get_training_stats()
        stats['categories_covered'] = len(training_stats.get('categories', {}))

        if progress_callback:
            progress_callback("Training complete!", 3, 3)

        logger.info(f"Initial training complete: {stats}")
        return stats

    def _learn_from_manual_edits(self) -> int:
        """
        Learn from transactions that were manually edited.

        Returns:
            Number of training examples created
        """
        # Get all manually edited transactions
        manual_transactions = (
            self.db_session.query(Transaction)
            .filter(
                Transaction.project_id == self.project_id,
                Transaction.categoria_original.isnot(None)
            )
            .all()
        )

        logger.info(f"Found {len(manual_transactions)} manually edited transactions")

        # Learn from each manual edit
        count = self.ai_service.retrain_from_transactions(
            manual_transactions,
            source='manual'
        )

        return count

    def _learn_from_category_rules(self) -> int:
        """
        Extract patterns from existing category rules.

        For each rule, find matching transactions and create training examples.

        Returns:
            Number of training examples created
        """
        # Get all category rules
        rules = (
            self.db_session.query(CategoryRule)
            .filter(CategoryRule.project_id == self.project_id)
            .all()
        )

        logger.info(f"Found {len(rules)} category rules")

        count = 0

        for rule in rules:
            # Find transactions matching this rule
            matching_transactions = (
                self.db_session.query(Transaction)
                .filter(
                    Transaction.project_id == self.project_id,
                    Transaction.concepto.contains(rule.pattern)
                )
                .limit(5)  # Max 5 examples per rule
                .all()
            )

            # Create training examples
            for transaction in matching_transactions:
                example = self.ai_service.learn_from_correction(
                    transaction,
                    rule.category,
                    source='rule'
                )
                if example:
                    count += 1

        logger.info(f"Created {count} training examples from rules")
        return count

    def _sample_representatives(self, samples_per_category: int = 10) -> int:
        """
        Sample representative transactions from each category.

        For categories with many transactions but few training examples,
        create additional training data by sampling diverse transactions.

        Args:
            samples_per_category: Max samples per category

        Returns:
            Number of training examples created
        """
        # Get transaction counts by category
        category_counts = defaultdict(int)
        transactions_by_category = defaultdict(list)

        all_transactions = (
            self.db_session.query(Transaction)
            .filter(Transaction.project_id == self.project_id)
            .all()
        )

        for transaction in all_transactions:
            category = transaction.categoria
            category_counts[category] += 1
            transactions_by_category[category].append(transaction)

        # Get current training example counts
        training_stats = self.ai_service.get_training_stats()
        training_by_category = training_stats.get('categories', {})

        count = 0

        # For each category, check if we need more examples
        for category, transactions in transactions_by_category.items():
            current_examples = training_by_category.get(category, 0)
            total_transactions = len(transactions)

            # Skip if enough examples or too few transactions
            if current_examples >= samples_per_category or total_transactions < 5:
                continue

            # How many more do we need?
            needed = min(
                samples_per_category - current_examples,
                total_transactions
            )

            # Sample diverse transactions (spread across time)
            step = max(1, total_transactions // needed)
            sampled = transactions[::step][:needed]

            # Create training examples
            for transaction in sampled:
                # Skip if already manually edited (already learned)
                if transaction.is_manually_edited:
                    continue

                example = self.ai_service.learn_from_correction(
                    transaction,
                    category,
                    source='initial'
                )
                if example:
                    count += 1

        logger.info(f"Sampled {count} representative transactions")
        return count

    def get_training_readiness(self) -> Dict[str, any]:
        """
        Assess readiness for AI categorization.

        Returns:
            Dictionary with readiness assessment
        """
        # Count manually edited transactions
        manual_count = (
            self.db_session.query(Transaction)
            .filter(
                Transaction.project_id == self.project_id,
                Transaction.categoria_original.isnot(None)
            )
            .count()
        )

        # Count category rules
        rules_count = (
            self.db_session.query(CategoryRule)
            .filter(CategoryRule.project_id == self.project_id)
            .count()
        )

        # Get current training stats
        training_stats = self.ai_service.get_training_stats()
        total_examples = training_stats.get('total_examples', 0)

        # Determine readiness level
        if total_examples >= 50:
            readiness = 'excellent'
            message = "AI is ready with excellent training data"
        elif total_examples >= 20:
            readiness = 'good'
            message = "AI is ready with good training data"
        elif total_examples >= 10:
            readiness = 'fair'
            message = "AI is ready but could benefit from more examples"
        elif manual_count > 0 or rules_count > 0:
            readiness = 'potential'
            message = "Ready to build initial training from existing data"
        else:
            readiness = 'none'
            message = "No training data available - start by categorizing transactions"

        return {
            'readiness': readiness,
            'message': message,
            'manual_edits_available': manual_count,
            'rules_available': rules_count,
            'current_examples': total_examples,
            'categories_covered': len(training_stats.get('categories', {}))
        }
