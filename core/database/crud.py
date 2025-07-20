from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_
from sqlalchemy.orm import selectinload
from core.database.model import User, PurchasedSubscription, SubscriptionPlan, Promocode, UsedPromocode
from typing import Optional, List, Union, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

# ==================== USER OPERATIONS ====================

async def create_user(
    session: AsyncSession,
    telegram_id: int,
    username: Optional[str] = None,
    balance: Decimal = Decimal('0'),
    role: str = "USER"
) -> Optional[User]:
    """Create new user in database"""
    try:
        user = User(
            telegram_id=telegram_id,
            username=username,
            balance=balance,
            role=role
        )
        session.add(user)
        await session.flush()
        await session.refresh(user)
        logger.debug(f"Created user: {user.telegram_id}")
        return user
    except Exception as e:
        logger.error(f"Error creating user {telegram_id}: {str(e)}", exc_info=True)
        await session.rollback()
        return None

async def get_user_by_telegram_id(
    session: AsyncSession,
    telegram_id: int
) -> Optional[User]:
    """Get user by Telegram ID"""
    try:
        result = await session.execute(
            select(User)
            .where(User.telegram_id == telegram_id)
        )
        return result.scalars().first()
    except Exception as e:
        logger.error(f"Error getting user {telegram_id}: {str(e)}", exc_info=True)
        return None

async def update_user_balance(
    session: AsyncSession,
    telegram_id: int,
    amount: Decimal
) -> bool:
    """Update user balance"""
    try:
        user = await get_user_by_telegram_id(session, telegram_id)
        if not user:
            return False
            
        user.balance += amount
        await session.flush()
        return True
    except Exception as e:
        logger.error(f"Error updating balance for {telegram_id}: {str(e)}", exc_info=True)
        await session.rollback()
        return False

# ==================== SUBSCRIPTION OPERATIONS ====================

async def update_subscription_transfer(
    session: AsyncSession,
    sub_uuid: str,
    new_telegram_id: int
) -> bool:
    """Обновление владельца подписки при передаче"""
    try:
        result = await session.execute(
            update(PurchasedSubscription)
            .where(PurchasedSubscription.sub_uuid == sub_uuid)
            .values(
                telegram_id=new_telegram_id,
                last_transfer_time=datetime.now()
            )
        )
        await session.commit()
        return result.rowcount > 0
    except Exception as e:
        logger.error(f"Error transferring subscription {sub_uuid}: {str(e)}", exc_info=True)
        await session.rollback()
        return False

async def create_or_update_subscription(
    session: AsyncSession,
    telegram_id: int,
    sub_uuid: str,
    username: str,
    expired_at: datetime,
    purchase_price: Optional[Decimal] = None,
    renewal_price: Optional[Decimal] = None
) -> Optional[PurchasedSubscription]:
    """Create or update subscription"""
    try:
        subscription = await get_purchased_subscription_by_uuid(session, sub_uuid)
        
        if subscription:
            # Update existing subscription
            subscription.telegram_id = telegram_id
            subscription.username = username
            subscription.expired_at = expired_at
            if purchase_price is not None:
                subscription.purchase_price = purchase_price
            if renewal_price is not None:
                subscription.renewal_price = renewal_price
        else:
            # Create new subscription
            subscription = PurchasedSubscription(
                telegram_id=telegram_id,
                sub_uuid=sub_uuid,
                username=username,
                purchase_price=purchase_price,
                renewal_price=renewal_price,
                expired_at=expired_at
            )
            session.add(subscription)
        
        await session.flush()
        await session.refresh(subscription)
        return subscription
    except Exception as e:
        logger.error(f"Error with subscription {sub_uuid}: {str(e)}", exc_info=True)
        await session.rollback()
        return None

async def get_purchased_subscription_by_uuid(
    session: AsyncSession, 
    sub_uuid: str
) -> Optional[PurchasedSubscription]:
    """Get subscription by UUID"""
    try:
        result = await session.execute(
            select(PurchasedSubscription)
            .where(PurchasedSubscription.sub_uuid == sub_uuid)
        )
        return result.scalars().first()
    except Exception as e:
        logger.error(f"Error getting subscription {sub_uuid}: {str(e)}", exc_info=True)
        return None

async def get_purchased_subscriptions(
    session: AsyncSession, 
    telegram_id: int
) -> List[PurchasedSubscription]:
    """Get all user subscriptions"""
    try:
        result = await session.execute(
            select(PurchasedSubscription)
            .where(PurchasedSubscription.telegram_id == telegram_id)
            .order_by(PurchasedSubscription.expired_at.desc())
        )
        return list(result.scalars().all())
    except Exception as e:
        logger.error(f"Error getting subscriptions for {telegram_id}: {str(e)}", exc_info=True)
        return []

async def transfer_subscription_ownership(
    session: AsyncSession,
    sub_uuid: str,
    new_telegram_id: int
) -> bool:
    """Transfer subscription to new owner"""
    try:
        result = await session.execute(
            update(PurchasedSubscription)
            .where(PurchasedSubscription.sub_uuid == sub_uuid)
            .values(
                telegram_id=new_telegram_id,
                last_transfer_time=datetime.now()
            )
        )
        await session.flush()
        return result.rowcount > 0
    except Exception as e:
        logger.error(f"Error transferring subscription {sub_uuid}: {str(e)}", exc_info=True)
        await session.rollback()
        return False

async def update_subscription_expiration(
    session: AsyncSession,
    sub_uuid: str,
    new_expiration: datetime
) -> bool:
    """Update subscription expiration date"""
    try:
        result = await session.execute(
            update(PurchasedSubscription)
            .where(PurchasedSubscription.sub_uuid == sub_uuid)
            .values(expired_at=new_expiration)
        )
        await session.flush()
        return result.rowcount > 0
    except Exception as e:
        logger.error(f"Error updating expiration for {sub_uuid}: {str(e)}", exc_info=True)
        await session.rollback()
        return False

async def update_device_removal_count(
    session: AsyncSession,
    sub_uuid: str,
    increment: bool = True
) -> bool:
    """Update device removal counter"""
    try:
        subscription = await get_purchased_subscription_by_uuid(session, sub_uuid)
        if not subscription:
            return False
            
        if increment:
            subscription.device_removal_count += 1
        else:
            subscription.device_removal_count = 0
            subscription.last_removal_reset = datetime.now()
            
        await session.flush()
        return True
    except Exception as e:
        logger.error(f"Error updating device removal for {sub_uuid}: {str(e)}", exc_info=True)
        await session.rollback()
        return False

# ==================== PROMOCODE OPERATIONS ====================

async def get_active_promocode(
    session: AsyncSession,
    code: str
) -> Optional[Promocode]:
    """Get active promocode"""
    try:
        result = await session.execute(
            select(Promocode)
            .where(Promocode.code == code)
            .where(Promocode.is_active == True)
            .where(Promocode.valid_until >= datetime.now())
        )
        return result.scalars().first()
    except Exception as e:
        logger.error(f"Error getting promocode {code}: {str(e)}", exc_info=True)
        return None

async def create_used_promocode(
    session: AsyncSession,
    telegram_id: int,
    promo_id: int,
    valid_until: Optional[datetime] = None
) -> Optional[UsedPromocode]:
    """Create used promocode record"""
    try:
        used_promo = UsedPromocode(
            telegram_id=telegram_id,
            promo_id=promo_id,
            valid_until=valid_until
        )
        session.add(used_promo)
        await session.flush()
        await session.refresh(used_promo)
        return used_promo
    except Exception as e:
        logger.error(f"Error creating used promocode: {str(e)}", exc_info=True)
        await session.rollback()
        return None

# ==================== UTILITY FUNCTIONS ====================

async def get_user_full_data(
    session: AsyncSession,
    telegram_id: int
) -> Optional[Dict[str, Any]]:
    """Get complete user data"""
    try:
        user = await get_user_by_telegram_id(session, telegram_id)
        if not user:
            return None
            
        subscriptions = await get_purchased_subscriptions(session, telegram_id)
        active_subscriptions = [s for s in subscriptions if s.expired_at > datetime.now()]
        
        return {
            "user": user,
            "subscriptions": active_subscriptions,
            "subscriptions_count": len(active_subscriptions)
        }
    except Exception as e:
        logger.error(f"Error getting full data for {telegram_id}: {str(e)}", exc_info=True)
        return None
