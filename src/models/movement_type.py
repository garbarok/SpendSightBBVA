"""Movement type enumeration for standardizing transaction types."""
from enum import Enum


class MovementType(str, Enum):
    """
    Standardized movement types for BBVA transactions.

    Supports both Spanish and English to normalize free-text movement descriptions
    from Excel exports into consistent database values.
    """

    # Income movements
    TRANSFER_RECEIVED = "Transferencia recibida"
    BIZUM_RECEIVED = "Bizum recibido"

    # Expense movements
    CARD_PAYMENT = "Pago con tarjeta"
    DIRECT_DEBIT = "Adeudo/domiciliación"
    CASH_WITHDRAWAL = "Retirada de efectivo"
    BIZUM_SENT = "Bizum enviado"
    TRANSFER_SENT = "Transferencia enviada"
    CARD_CHARGE = "Cargo tarjeta"
    FEE = "Comisión"

    # Neutral movements
    INTEREST = "Intereses"
    OTHER = "Otro movimiento"
    UNKNOWN = "Desconocido"

    @classmethod
    def from_text(cls, text: str) -> "MovementType":
        """
        Convert free-text movement description to enum value.

        Args:
            text: Movement description from BBVA Excel file

        Returns:
            MovementType enum value

        Examples:
            >>> MovementType.from_text("Pago con tarjeta")
            MovementType.CARD_PAYMENT
            >>> MovementType.from_text("Card payment")
            MovementType.CARD_PAYMENT
            >>> MovementType.from_text("Transferencia recibida")
            MovementType.TRANSFER_RECEIVED
        """
        if not text:
            return cls.UNKNOWN

        text_lower = str(text).lower().strip()

        # Mapping rules - ordered by specificity
        mappings = {
            # Transfers
            ("transfer received", "transferencia recibida"): cls.TRANSFER_RECEIVED,
            ("transfer", "transferencia", "traspaso", "transfer sent"): cls.TRANSFER_SENT,

            # Bizum
            ("bizum recibido", "bizum received"): cls.BIZUM_RECEIVED,
            ("bizum"): cls.BIZUM_SENT,

            # Card payments
            ("pago con tarjeta", "card payment", "pago tarjeta"): cls.CARD_PAYMENT,
            ("cargo tarjeta", "card charge", "cargo de tarjeta"): cls.CARD_CHARGE,

            # Direct debits
            ("adeudo", "domiciliación", "domiciliacion", "direct debit", "adeudo mensual"): cls.DIRECT_DEBIT,

            # Cash
            ("retirada", "cajero", "cash withdrawal", "atm"): cls.CASH_WITHDRAWAL,

            # Fees
            ("comisión", "comision", "fee", "commission"): cls.FEE,

            # Interest
            ("intereses", "interest"): cls.INTEREST,
        }

        # Find matching pattern
        for patterns, movement_type in mappings.items():
            if isinstance(patterns, str):
                patterns = (patterns,)
            if any(pattern in text_lower for pattern in patterns):
                return movement_type

        # Check if it contains "other" keyword
        if "otro" in text_lower or "other" in text_lower:
            return cls.OTHER

        # Default to unknown
        return cls.UNKNOWN

    @property
    def is_income(self) -> bool:
        """Check if this movement type typically represents income."""
        return self in (
            self.TRANSFER_RECEIVED,
            self.BIZUM_RECEIVED,
        )

    @property
    def is_expense(self) -> bool:
        """Check if this movement type typically represents an expense."""
        return self in (
            self.CARD_PAYMENT,
            self.DIRECT_DEBIT,
            self.CASH_WITHDRAWAL,
            self.BIZUM_SENT,
            self.TRANSFER_SENT,
            self.CARD_CHARGE,
            self.FEE,
        )

    @property
    def is_neutral(self) -> bool:
        """Check if this movement type is neutral (neither income nor expense)."""
        return not (self.is_income or self.is_expense)
