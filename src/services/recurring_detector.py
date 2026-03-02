"""Recurring transaction detection service."""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass
from sqlalchemy.orm import Session
from models import Transaction


@dataclass
class RecurringPattern:
    """Represents a detected recurring transaction pattern."""

    merchant_name: str  # Common merchant identifier
    category: str  # Transaction category
    frequency: str  # "weekly", "monthly", or "yearly"
    interval_days: int  # Average days between transactions
    average_amount: float  # Average transaction amount
    amount_variance: float  # Variance in amounts (percentage)
    transaction_count: int  # Number of transactions in pattern
    last_date: datetime  # Most recent transaction date
    next_expected_date: Optional[datetime]  # Predicted next transaction date
    confidence: float  # Confidence score 0-1
    transaction_ids: List[int]  # List of transaction IDs in this pattern
    is_active: bool  # True if likely still active (recent transaction)


class RecurringDetector:
    """
    Detects recurring transaction patterns (subscriptions, bills, etc).

    Algorithm:
    1. Group transactions by merchant name (fuzzy matching)
    2. For each group, check if transactions occur at regular intervals
    3. Verify amounts are similar (within ±10%)
    4. Require minimum 3 occurrences to establish pattern
    5. Calculate confidence based on regularity and amount consistency
    """

    # Thresholds
    MIN_OCCURRENCES = 3  # Minimum transactions to establish pattern
    AMOUNT_TOLERANCE = 0.10  # ±10% variance in amounts
    INTERVAL_TOLERANCE = 0.20  # ±20% variance in intervals
    ACTIVE_THRESHOLD_DAYS = 60  # Pattern is "active" if transaction within 60 days

    # Frequency detection (in days)
    WEEKLY_RANGE = (5, 9)  # 7 days ± 2
    MONTHLY_RANGE = (25, 35)  # 30 days ± 5
    YEARLY_RANGE = (350, 380)  # 365 days ± 15

    def __init__(self, db_session: Session, project_id: int):
        """
        Initialize recurring detector.

        Args:
            db_session: SQLAlchemy database session
            project_id: Current project ID
        """
        self.db_session = db_session
        self.project_id = project_id

    def detect_recurring_patterns(self) -> List[RecurringPattern]:
        """
        Detect all recurring transaction patterns in the project.

        Returns:
            List of RecurringPattern objects sorted by confidence
        """
        # Load all transactions, sorted by date
        transactions = (
            self.db_session.query(Transaction)
            .filter(Transaction.project_id == self.project_id)
            .order_by(Transaction.fecha.asc())
            .all()
        )

        # Group by merchant
        merchant_groups = self._group_by_merchant(transactions)

        # Detect patterns in each group
        patterns = []
        for merchant_name, txns in merchant_groups.items():
            if len(txns) >= self.MIN_OCCURRENCES:
                pattern = self._analyze_pattern(merchant_name, txns)
                if pattern and pattern.confidence >= 0.5:  # Only return confident patterns
                    patterns.append(pattern)

        # Sort by confidence (descending)
        patterns.sort(key=lambda p: p.confidence, reverse=True)

        return patterns

    def _group_by_merchant(self, transactions: List[Transaction]) -> Dict[str, List[Transaction]]:
        """
        Group transactions by merchant name.

        Uses fuzzy matching to group similar merchant names together.

        Args:
            transactions: List of all transactions

        Returns:
            Dictionary mapping merchant name to list of transactions
        """
        groups = defaultdict(list)

        for txn in transactions:
            # Extract merchant name from concept
            merchant = self._extract_merchant_name(txn.concepto)
            if merchant:
                groups[merchant].append(txn)

        return groups

    def _extract_merchant_name(self, concepto: str) -> Optional[str]:
        """
        Extract a normalized merchant name from transaction concept.

        Strategy:
        1. Find the first significant word (>3 chars)
        2. Remove common prefixes (PAGO, COMPRA, etc)
        3. Normalize case

        Args:
            concepto: Transaction description

        Returns:
            Normalized merchant name or None
        """
        if not concepto:
            return None

        # Remove common prefixes
        prefixes_to_remove = ['PAGO', 'COMPRA', 'RECIBO', 'CARGO', 'TRANSFERENCIA']
        words = concepto.upper().split()

        # Filter out prefixes and short words
        significant_words = [
            w for w in words
            if len(w) > 3 and w not in prefixes_to_remove and not w.isdigit()
        ]

        if significant_words:
            # Use first significant word as merchant name
            return significant_words[0]

        return None

    def _analyze_pattern(self, merchant_name: str, transactions: List[Transaction]) -> Optional[RecurringPattern]:
        """
        Analyze a group of transactions to detect recurring pattern.

        Args:
            merchant_name: Merchant identifier
            transactions: List of transactions for this merchant

        Returns:
            RecurringPattern if pattern detected, None otherwise
        """
        if len(transactions) < self.MIN_OCCURRENCES:
            return None

        # Sort by date
        transactions = sorted(transactions, key=lambda t: t.fecha)

        # Calculate intervals between transactions
        intervals = []
        for i in range(1, len(transactions)):
            delta = (transactions[i].fecha - transactions[i-1].fecha).days
            if delta > 0:  # Ignore same-day duplicates
                intervals.append(delta)

        if not intervals:
            return None

        # Calculate average interval
        avg_interval = sum(intervals) / len(intervals)

        # Detect frequency
        frequency, expected_interval = self._detect_frequency(avg_interval)

        if not frequency:
            return None  # No recognizable pattern

        # Check interval consistency
        interval_variance = self._calculate_variance(intervals, expected_interval)
        if interval_variance > self.INTERVAL_TOLERANCE:
            return None  # Too much variance in timing

        # Check amount consistency
        amounts = [abs(txn.importe) for txn in transactions]
        avg_amount = sum(amounts) / len(amounts)
        amount_variance = self._calculate_variance(amounts, avg_amount)

        if amount_variance > self.AMOUNT_TOLERANCE:
            # Amounts too inconsistent, lower confidence but don't reject
            confidence = 0.5
        else:
            # Calculate confidence based on consistency
            confidence = self._calculate_confidence(interval_variance, amount_variance, len(transactions))

        # Predict next transaction date
        last_date = transactions[-1].fecha
        next_expected = last_date + timedelta(days=expected_interval)

        # Check if pattern is still active
        days_since_last = (datetime.now() - last_date).days
        is_active = days_since_last < self.ACTIVE_THRESHOLD_DAYS

        # Get category (use most common category)
        categories = [txn.categoria for txn in transactions]
        most_common_category = max(set(categories), key=categories.count)

        return RecurringPattern(
            merchant_name=merchant_name,
            category=most_common_category,
            frequency=frequency,
            interval_days=expected_interval,
            average_amount=avg_amount,
            amount_variance=amount_variance,
            transaction_count=len(transactions),
            last_date=last_date,
            next_expected_date=next_expected if is_active else None,
            confidence=confidence,
            transaction_ids=[txn.id for txn in transactions],
            is_active=is_active
        )

    def _detect_frequency(self, avg_interval: float) -> tuple[Optional[str], Optional[int]]:
        """
        Detect frequency pattern from average interval.

        Args:
            avg_interval: Average days between transactions

        Returns:
            Tuple of (frequency_name, expected_interval_days) or (None, None)
        """
        if self.WEEKLY_RANGE[0] <= avg_interval <= self.WEEKLY_RANGE[1]:
            return ("weekly", 7)
        elif self.MONTHLY_RANGE[0] <= avg_interval <= self.MONTHLY_RANGE[1]:
            return ("monthly", 30)
        elif self.YEARLY_RANGE[0] <= avg_interval <= self.YEARLY_RANGE[1]:
            return ("yearly", 365)
        else:
            return (None, None)

    def _calculate_variance(self, values: List[float], expected: float) -> float:
        """
        Calculate variance as a percentage.

        Args:
            values: List of actual values
            expected: Expected value

        Returns:
            Variance as a decimal (0.1 = 10% variance)
        """
        if not values or expected == 0:
            return 1.0

        deviations = [abs(v - expected) / expected for v in values]
        return sum(deviations) / len(deviations)

    def _calculate_confidence(self, interval_variance: float, amount_variance: float, count: int) -> float:
        """
        Calculate confidence score for a recurring pattern.

        Args:
            interval_variance: Variance in intervals (0-1)
            amount_variance: Variance in amounts (0-1)
            count: Number of transactions

        Returns:
            Confidence score 0-1
        """
        # Base confidence from consistency
        interval_score = max(0, 1 - (interval_variance / self.INTERVAL_TOLERANCE))
        amount_score = max(0, 1 - (amount_variance / self.AMOUNT_TOLERANCE))

        # Bonus for more data points (up to 10 transactions)
        count_bonus = min(count / 10, 1.0) * 0.2

        # Weighted average
        confidence = (interval_score * 0.5 + amount_score * 0.3 + count_bonus)

        return min(confidence, 1.0)

    def get_pattern_by_merchant(self, merchant_name: str) -> Optional[RecurringPattern]:
        """
        Get recurring pattern for a specific merchant.

        Args:
            merchant_name: Merchant identifier

        Returns:
            RecurringPattern or None if not found
        """
        patterns = self.detect_recurring_patterns()
        for pattern in patterns:
            if pattern.merchant_name.lower() == merchant_name.lower():
                return pattern
        return None

    def mark_as_ignored(self, pattern: RecurringPattern) -> None:
        """
        Mark a pattern as ignored (not really recurring).

        This could be implemented by adding a flag to transactions or a separate ignore list.
        For now, this is a placeholder for future implementation.

        Args:
            pattern: RecurringPattern to ignore
        """
        # TODO: Implement ignore functionality
        # Could add a 'recurring_ignore' tag to all transactions in the pattern
        pass
