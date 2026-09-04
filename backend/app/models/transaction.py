"""Transaction ORM model."""

from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, Text
from sqlalchemy import func
from app.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(String(50), unique=True, nullable=False, index=True)
    customer_id = Column(String(50), nullable=False, index=True)
    merchant_id = Column(String(50), nullable=False, default="MERCHANT_001")
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="INR")
    payment_method = Column(String(30), nullable=False)
    payment_status = Column(String(30), nullable=False, index=True)  # success, failed, recovered, pending
    failure_code = Column(String(50), nullable=True)
    failure_reason = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    device_type = Column(String(20), nullable=True)
    location = Column(String(50), nullable=True)
    merchant_category = Column(String(50), nullable=True)
    checkout_duration = Column(Float, nullable=True)  # seconds
    cart_value = Column(Float, nullable=True)
    is_returning_customer = Column(Boolean, default=False)
    transaction_frequency = Column(Float, nullable=True)  # transactions per month
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String(50), unique=True, nullable=False, index=True)
    previous_transactions = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    previous_failures = Column(Integer, default=0)
    lifetime_value = Column(Float, default=0.0)
    last_transaction_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
