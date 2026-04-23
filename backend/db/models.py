from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from datetime import datetime, timezone
from db.database import Base  # The parent class for all the models


class Import(Base):
    __tablename__ = "imports"

    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String, nullable=False)
    file_hash = Column(String, nullable=False, unique=True)
    imported_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    import_id = Column(Integer, ForeignKey("imports.id"), nullable=False)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    transaction_date = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, nullable=False)
    description_raw = Column(String, nullable=False)
