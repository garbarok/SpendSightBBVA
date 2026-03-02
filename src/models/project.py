"""Project ORM model."""
from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime
from .database import Base

class Project(Base):
    """
    Represents a project workspace for organizing transactions.

    A project is a collection of transactions, rules, and budgets.
    Users can create multiple projects to separate different accounts or time periods.
    """
    __tablename__ = 'projects'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Project(id={self.id}, name='{self.name}')>"
