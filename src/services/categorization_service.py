"""Smart categorization service with rule learning and AI integration."""
from typing import List, Optional, Tuple, Dict
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models import CategoryRule, Transaction
from utils.categories import get_default_category, CATEGORIES
from utils.logger import setup_logger

logger = setup_logger(__name__)


class CategorizationService:
    """
    Handles intelligent transaction categorization using hybrid approach.

    Priority system (Hybrid Intelligence Pattern):
    - 100: User-created rules (learned from manual edits)
    - 50-90: AI semantic matching with confidence
    - 25-50: Hardcoded keyword rules
    - 0: Default fallback category
    """

    def __init__(self, db_session: Session, project_id: int, enable_ai: bool = True):
        """
        Initialize categorization service.

        Args:
            db_session: SQLAlchemy database session
            project_id: Current project ID
            enable_ai: Enable AI categorization (default: True)
        """
        self.db_session = db_session
        self.project_id = project_id
        self.enable_ai = enable_ai
        self._rules_cache = None
        self._ai_service = None

    def _load_rules(self) -> List[CategoryRule]:
        """
        Load all categorization rules for the current project.

        Returns:
            List of CategoryRule objects sorted by priority (highest first)
        """
        if self._rules_cache is None:
            self._rules_cache = (
                self.db_session.query(CategoryRule)
                .filter(CategoryRule.project_id == self.project_id)
                .order_by(CategoryRule.priority.desc(), CategoryRule.created_at.asc())
                .all()
            )
        return self._rules_cache

    def invalidate_cache(self):
        """Invalidate the rules cache, forcing a reload on next use."""
        self._rules_cache = None

    def _get_ai_service(self):
        """
        Lazy-load AI categorization service.

        Returns:
            AICategorizationService instance or None if disabled/unavailable
        """
        if not self.enable_ai:
            return None

        if self._ai_service is None:
            try:
                from services.ai_categorization_service import AICategorizationService
                self._ai_service = AICategorizationService(self.db_session, self.project_id)
            except ImportError as e:
                logger.warning(f"AI categorization unavailable: {e}")
                self.enable_ai = False
                return None
            except Exception as e:
                logger.error(f"Failed to initialize AI service: {e}")
                self.enable_ai = False
                return None

        return self._ai_service

    def categorize_transaction(
        self,
        concepto: str,
        movimiento: str = None
    ) -> Dict[str, any]:
        """
        Categorize a transaction using hybrid intelligence approach.

        Priority flow:
        1. User-created rules (priority 100)
        2. AI semantic matching (priority 50-90 based on confidence)
        3. Hardcoded keyword rules (priority 25-50)
        4. Default fallback (priority 0)

        Args:
            concepto: Transaction description/concept
            movimiento: Movement type (optional, enhances AI accuracy)

        Returns:
            Dictionary with:
            - category (str): Category name
            - confidence (float): AI confidence or 1.0 for rule-based
            - method (str): 'rule', 'ai', 'keyword', or 'default'
            - priority (int): Priority score
            - alternatives (list): Alternative categories (for AI)
        """
        if not concepto:
            return {
                'category': "❓ Otros",
                'confidence': 0.0,
                'method': 'default',
                'priority': 0,
                'alternatives': []
            }

        concepto_lower = concepto.lower()

        # STEP 1: Check user-created rules (priority 100)
        user_rules = self._load_rules()
        for rule in user_rules:
            if rule.match(concepto):
                logger.debug(f"Matched user rule: {rule.pattern} -> {rule.category}")
                return {
                    'category': rule.category,
                    'confidence': 1.0,
                    'method': 'rule',
                    'priority': rule.priority,
                    'alternatives': []
                }

        # STEP 2: Try AI semantic matching (priority 50-90)
        ai_service = self._get_ai_service()
        if ai_service:
            try:
                ai_category, ai_confidence, alternatives = ai_service.categorize_with_confidence(
                    concepto,
                    movimiento
                )

                # Use AI if confidence is above medium threshold
                if ai_category and ai_confidence >= ai_service.MEDIUM_CONFIDENCE:
                    # Map confidence to priority (70-100% -> priority 50-90)
                    priority = int(50 + (ai_confidence - 0.70) * 133)  # Scale to 50-90

                    logger.debug(
                        f"AI categorization: {concepto[:30]}... -> {ai_category} "
                        f"(confidence: {ai_confidence:.2%})"
                    )

                    return {
                        'category': ai_category,
                        'confidence': ai_confidence,
                        'method': 'ai',
                        'priority': priority,
                        'alternatives': alternatives
                    }
                elif ai_category:
                    logger.debug(
                        f"AI confidence too low ({ai_confidence:.2%}), "
                        "falling back to keywords"
                    )

            except Exception as e:
                logger.error(f"AI categorization error: {e}", exc_info=True)

        # STEP 3: Fall back to hardcoded keyword rules (priority 25-50)
        category = get_default_category(concepto)

        if category != "❓ Otros":
            # Determine priority based on match quality
            priority = 25  # Default fuzzy match

            for cat_name, keywords in CATEGORIES.items():
                if cat_name == category:
                    # If any keyword is an exact match, priority 50
                    if any(keyword == concepto_lower for keyword in keywords):
                        priority = 50
                        break

            logger.debug(f"Keyword match: {concepto[:30]}... -> {category}")

            return {
                'category': category,
                'confidence': 1.0,
                'method': 'keyword',
                'priority': priority,
                'alternatives': []
            }

        # STEP 4: Default fallback
        return {
            'category': "❓ Otros",
            'confidence': 0.0,
            'method': 'default',
            'priority': 0,
            'alternatives': []
        }

    def create_rule_from_edit(self, transaction: Transaction, new_category: str) -> Optional[CategoryRule]:
        """
        Create a categorization rule based on a manual category edit.

        This is called when a user manually changes a transaction's category
        and chooses to create a rule for future auto-categorization.

        Args:
            transaction: The transaction that was edited
            new_category: The new category assigned by the user

        Returns:
            CategoryRule object if created, None if rule already exists
        """
        # Extract a pattern from the transaction concept
        # For now, use the first significant word (>3 chars)
        pattern = self._extract_pattern(transaction.concepto)

        if not pattern:
            return None

        # Check if a similar rule already exists
        existing_rule = (
            self.db_session.query(CategoryRule)
            .filter(
                CategoryRule.project_id == self.project_id,
                CategoryRule.pattern == pattern,
                CategoryRule.category == new_category
            )
            .first()
        )

        if existing_rule:
            return None  # Rule already exists

        # Create new rule
        new_rule = CategoryRule(
            project_id=self.project_id,
            pattern=pattern,
            category=new_category,
            priority=100  # User rules always have highest priority
        )

        self.db_session.add(new_rule)

        try:
            self.db_session.commit()
        except IntegrityError:
            # Rule already exists (race condition)
            self.db_session.rollback()
            logger.debug(f"Rule already exists for pattern '{pattern}'")
            return None

        self.invalidate_cache()

        return new_rule

    def _extract_pattern(self, concepto: str) -> Optional[str]:
        """
        Extract a meaningful pattern from a transaction concept.

        Strategy:
        1. Split into words
        2. Find the first significant word (>3 characters, not a number)
        3. Return that word as the pattern

        Args:
            concepto: Transaction description

        Returns:
            Pattern string or None if no suitable pattern found
        """
        if not concepto:
            return None

        # Remove common prefixes and clean
        concepto_clean = concepto.strip()

        # Split into words and find first significant one
        words = concepto_clean.split()
        for word in words:
            # Remove punctuation
            word_clean = ''.join(c for c in word if c.isalnum())

            # Check if it's a significant word
            if len(word_clean) > 3 and not word_clean.isdigit():
                return word_clean.lower()

        # If no significant word found, use the whole concept (truncated)
        if len(concepto_clean) > 3:
            return concepto_clean[:50].lower()

        return None

    def apply_rules_to_transactions(self, transactions: List[Transaction]) -> Dict[str, int]:
        """
        Apply categorization rules to a list of transactions.

        This is used during import to auto-categorize new transactions.

        Args:
            transactions: List of Transaction objects to categorize

        Returns:
            Dictionary with categorization statistics:
            - total: Total transactions processed
            - rule: Categorized by user rules
            - ai: Categorized by AI
            - keyword: Categorized by keywords
            - default: Default category
        """
        stats = {
            'total': len(transactions),
            'rule': 0,
            'ai': 0,
            'keyword': 0,
            'default': 0
        }

        for transaction in transactions:
            # Skip if already manually categorized
            if transaction.is_manually_edited:
                continue

            # Categorize using hybrid approach
            result = self.categorize_transaction(
                transaction.concepto,
                transaction.movimiento
            )

            # Apply categorization
            transaction.categoria = result['category']
            transaction.ai_confidence = result['confidence']
            transaction.categorization_method = result['method']

            # Update stats
            method = result['method']
            if method in stats:
                stats[method] += 1

        return stats

    def get_all_rules(self) -> List[CategoryRule]:
        """
        Get all categorization rules for the current project.

        Returns:
            List of CategoryRule objects
        """
        return self._load_rules()

    def delete_rule(self, rule_id: int) -> bool:
        """
        Delete a categorization rule.

        Args:
            rule_id: ID of the rule to delete

        Returns:
            True if deleted, False if not found
        """
        rule = (
            self.db_session.query(CategoryRule)
            .filter(
                CategoryRule.id == rule_id,
                CategoryRule.project_id == self.project_id
            )
            .first()
        )

        if not rule:
            return False

        self.db_session.delete(rule)

        try:
            self.db_session.commit()
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Failed to delete rule: {e}")
            raise

        self.invalidate_cache()

        return True

    def update_rule(self, rule_id: int, pattern: str = None, category: str = None) -> bool:
        """
        Update an existing categorization rule.

        Args:
            rule_id: ID of the rule to update
            pattern: New pattern (optional)
            category: New category (optional)

        Returns:
            True if updated, False if not found
        """
        rule = (
            self.db_session.query(CategoryRule)
            .filter(
                CategoryRule.id == rule_id,
                CategoryRule.project_id == self.project_id
            )
            .first()
        )

        if not rule:
            return False

        if pattern is not None:
            rule.pattern = pattern
        if category is not None:
            rule.category = category

        try:
            self.db_session.commit()
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Failed to update rule: {e}")
            raise

        self.invalidate_cache()

        return True
