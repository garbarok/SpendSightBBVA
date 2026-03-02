"""User preferences model for application settings."""
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from datetime import datetime
from .database import Base


class UserPreferences(Base):
    """
    Stores user preferences and settings for a project.

    Each project can have its own configuration for AI features,
    display settings, and training preferences.
    """
    __tablename__ = 'user_preferences'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, unique=True)

    # AI Categorization Settings
    enable_ai_categorization = Column(Boolean, default=True, nullable=False)
    ai_confidence_threshold = Column(Float, default=0.80, nullable=False)  # 0.0-1.0
    auto_learn_from_edits = Column(Boolean, default=True, nullable=False)

    # Display Settings
    show_confidence_indicators = Column(Boolean, default=True, nullable=False)
    color_code_amounts = Column(Boolean, default=True, nullable=False)

    # Training Settings
    auto_retrain_enabled = Column(Boolean, default=False, nullable=False)
    min_examples_per_category = Column(Integer, default=5, nullable=False)

    def __repr__(self):
        return f"<UserPreferences(project_id={self.project_id}, ai_enabled={self.enable_ai_categorization})>"

    @classmethod
    def get_or_create(cls, db_session, project_id: int) -> 'UserPreferences':
        """
        Get existing preferences or create default ones.

        Args:
            db_session: SQLAlchemy database session
            project_id: Project ID

        Returns:
            UserPreferences instance
        """
        prefs = db_session.query(cls).filter_by(project_id=project_id).first()

        if not prefs:
            prefs = cls(project_id=project_id)
            db_session.add(prefs)
            db_session.commit()

        return prefs

    def update_from_dict(self, settings: dict) -> None:
        """
        Update preferences from a dictionary.

        Args:
            settings: Dictionary of setting key-value pairs
        """
        for key, value in settings.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def to_dict(self) -> dict:
        """
        Convert preferences to dictionary.

        Returns:
            Dictionary of all settings
        """
        return {
            'enable_ai_categorization': self.enable_ai_categorization,
            'ai_confidence_threshold': self.ai_confidence_threshold,
            'auto_learn_from_edits': self.auto_learn_from_edits,
            'show_confidence_indicators': self.show_confidence_indicators,
            'color_code_amounts': self.color_code_amounts,
            'auto_retrain_enabled': self.auto_retrain_enabled,
            'min_examples_per_category': self.min_examples_per_category,
        }

    @property
    def ai_confidence_threshold_percentage(self) -> int:
        """Get confidence threshold as percentage (0-100)."""
        return int(self.ai_confidence_threshold * 100)

    @ai_confidence_threshold_percentage.setter
    def ai_confidence_threshold_percentage(self, value: int):
        """Set confidence threshold from percentage (0-100)."""
        self.ai_confidence_threshold = value / 100.0
