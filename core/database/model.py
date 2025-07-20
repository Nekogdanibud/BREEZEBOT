from datetime import datetime
from sqlalchemy import (
    Column, Integer, BigInteger, String, DateTime, 
    Text, Index, func, ForeignKey, CheckConstraint,
    UniqueConstraint, Boolean, Numeric
)
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, relationship

class Base(AsyncAttrs, DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index('idx_user_telegram_id', 'telegram_id'),
        Index('idx_user_username', 'username'),
        CheckConstraint(
            "role IN ('ADMIN', 'SUPPORT', 'USER', 'BANNED')", 
            name="check_user_role"
        ),
    )

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True, index=True)
    role = Column(String(20), nullable=False, server_default="USER")
    balance = Column(Numeric(10, 2), default=0, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_sync_time = Column(DateTime, nullable=True)

    # Relationships
    purchased_subscriptions = relationship("PurchasedSubscription", back_populates="user")
    used_promocodes = relationship("UsedPromocode", back_populates="user")

class PurchasedSubscription(Base):
    __tablename__ = "purchased_subscriptions"
    __table_args__ = (
        Index('idx_purchased_sub_telegram_id', 'telegram_id'),
        Index('idx_purchased_sub_uuid', 'sub_uuid'),
    )

    id = Column(Integer, primary_key=True)
    telegram_id = Column(
        BigInteger, 
        ForeignKey("users.telegram_id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    sub_uuid = Column(String(255), nullable=False)
    username = Column(String(255), nullable=False)  # Новое поле
    purchase_price = Column(Numeric(10, 2), nullable=True)
    renewal_price = Column(Numeric(10, 2), nullable=True)
    expired_at = Column(DateTime, nullable=False)
    last_transfer_time = Column(DateTime, nullable=True)
    device_removal_count = Column(Integer, default=0, nullable=False)
    last_removal_reset = Column(DateTime, nullable=True)
    
    # Relationship
    user = relationship("User", back_populates="purchased_subscriptions")

class SubscriptionPlan(Base):
    __tablename__ = "subscriptions_plan"
    __table_args__ = (
        UniqueConstraint('name', name='uq_subscription_plan_name'),
    )

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    price = Column(Numeric(10, 2), nullable=False)
    end_date = Column(DateTime, nullable=False)

class Promocode(Base):
    __tablename__ = "promocodes"
    __table_args__ = (
        UniqueConstraint('code', name='uq_promocode_code'),
        Index('idx_promocode_is_active', 'is_active'),
    )

    id = Column(Integer, primary_key=True)
    code = Column(String(50), nullable=False, unique=True)
    total_uses = Column(Integer, nullable=False)
    remaining_uses = Column(Integer, nullable=False)
    uses_per_user = Column(Integer, nullable=False)
    discount_value = Column(Numeric(10, 2), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    valid_until = Column(DateTime, nullable=False)

class UsedPromocode(Base):
    __tablename__ = "used_promocodes"
    __table_args__ = (
        Index('idx_used_promo_telegram_id', 'telegram_id'),
        Index('idx_used_promo_promo_id', 'promo_id'),
    )

    id = Column(Integer, primary_key=True)
    telegram_id = Column(
        BigInteger, 
        ForeignKey("users.telegram_id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    promo_id = Column(
        Integer, 
        ForeignKey("promocodes.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    valid_until = Column(DateTime)
    use_status = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="used_promocodes")
    promocode = relationship("Promocode")
