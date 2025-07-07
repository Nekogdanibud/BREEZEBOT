from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, exc
from sqlalchemy.orm import selectinload
from core.database.model import User, PurchasedSubscription, SubscriptionPlan, Promocode, UsedPromocode
from typing import Optional, List, Tuple, Union, Dict, Any
import logging
from decimal import Decimal
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

async def create_user(
    session: AsyncSession,
    telegram_id: int,
    username: Optional[str] = None,
    balance: Union[Decimal, float, int] = 0
) -> Optional[User]:
    """Создание пользователя с автоматическим назначением роли 'USER'"""
    try:
        # Конвертируем balance в Decimal если это не так
        if not isinstance(balance, Decimal):
            balance = Decimal(str(balance))
            
        user = User(
            telegram_id=telegram_id,
            username=username,
            balance=balance
        )
        session.add(user)
        await session.flush()
        await session.refresh(user)
        logger.info(f"Создан пользователь: {user.telegram_id}")
        return user
    except exc.IntegrityError as e:
        logger.warning(f"IntegrityError при создании пользователя {telegram_id}: {str(e)}")
        await session.rollback()
        return await get_user_by_telegram_id(session, telegram_id)
    except Exception as e:
        logger.error(f"Ошибка при создании пользователя {telegram_id}: {str(e)}", exc_info=True)
        await session.rollback()
        return None

async def get_user_by_telegram_id(
    session: AsyncSession,
    telegram_id: int
) -> Optional[User]:
    """Получение пользователя по telegram_id (базовая информация)"""
    try:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalars().first()
    except Exception as e:
        logger.error(f"Ошибка при получении пользователя {telegram_id}: {str(e)}", exc_info=True)
        return None

async def get_user_full_data(
    session: AsyncSession,
    telegram_id: int
) -> Optional[Tuple[User, List[PurchasedSubscription], List[UsedPromocode]]]:
    """
    Получение полной информации о пользователе:
    - Возвращает кортеж (User, List[PurchasedSubscription], List[UsedPromocode])
    - Автоматически обрабатывает пустые коллекции
    """
    try:
        result = await session.execute(
            select(User)
            .options(
                selectinload(User.purchased_subscriptions),
                selectinload(User.used_promocodes)
            )
            .where(User.telegram_id == telegram_id)
        )
        user = result.scalars().first()

        if not user:
            logger.debug(f"Пользователь {telegram_id} не найден")
            return None

        # Обработка пустых коллекций
        subscriptions = user.purchased_subscriptions if user.purchased_subscriptions else []
        promocodes = user.used_promocodes if user.used_promocodes else []

        return (user, subscriptions, promocodes)

    except Exception as e:
        logger.error(
            f"Ошибка при получении полных данных пользователя {telegram_id}: {str(e)}",
            exc_info=True
        )
        return None

async def get_purchased_subscriptions(
    session: AsyncSession, 
    telegram_id: int
) -> List[PurchasedSubscription]:
    """
    Получение всех объектов PurchasedSubscription для пользователя
    :param session: Асинхронная сессия БД
    :param telegram_id: Telegram ID пользователя
    :return: Список объектов PurchasedSubscription или пустой список
    """
    try:
        result = await session.execute(
            select(PurchasedSubscription)
            .where(PurchasedSubscription.telegram_id == telegram_id)
            .order_by(PurchasedSubscription.expired_at.desc())
        )
        return list(result.scalars().all())
    except Exception as e:
        logger.error(f"Ошибка при получении подписок пользователя {telegram_id}: {str(e)}", exc_info=True)
        return []

async def get_purchased_subscription_uuids(
    session: AsyncSession, 
    telegram_id: int
) -> List[str]:
    """
    Получение всех UUID подписок пользователя
    :param session: Асинхронная сессия БД
    :param telegram_id: Telegram ID пользователя
    :return: Список UUID подписок
    """
    try:
        result = await session.execute(
            select(PurchasedSubscription.sub_uuid)
            .where(PurchasedSubscription.telegram_id == telegram_id)
        )
        return [row[0] for row in result.all()]
    except Exception as e:
        logger.error(f"Ошибка при получении UUID подписок пользователя {telegram_id}: {str(e)}", exc_info=True)
        return []

async def get_active_purchased_subscriptions(
    session: AsyncSession, 
    telegram_id: int
) -> List[Dict[str, Any]]:
    """
    Получение активных подписок пользователя (не истекших)
    :param session: Асинхронная сессия БД
    :param telegram_id: Telegram ID пользователя
    :return: Список словарей с данными подписок
    """
    try:
        result = await session.execute(
            select(PurchasedSubscription)
            .where(PurchasedSubscription.telegram_id == telegram_id)
            .where(PurchasedSubscription.expired_at > datetime.now())
            .order_by(PurchasedSubscription.expired_at.desc())
        )
        
        subscriptions = []
        for sub in result.scalars().all():
            subscriptions.append({
                "id": sub.id,
                "sub_uuid": sub.sub_uuid,
                "purchase_price": float(sub.purchase_price),
                "renewal_price": float(sub.renewal_price),
                "expired_at": sub.expired_at,
                "is_active": sub.expired_at > datetime.now(),
                "device_removal_count": sub.device_removal_count,
                "last_removal_reset": sub.last_removal_reset
            })
            
        return subscriptions
    except Exception as e:
        logger.error(f"Ошибка при получении активных подписок пользователя {telegram_id}: {str(e)}", exc_info=True)
        return []

async def get_purchased_subscription_by_uuid(
    session: AsyncSession, 
    sub_uuid: str
) -> Optional[PurchasedSubscription]:
    """
    Получение объекта подписки по UUID
    :param session: Асинхронная сессия БД
    :param sub_uuid: UUID подписки
    :return: Объект PurchasedSubscription или None
    """
    try:
        result = await session.execute(
            select(PurchasedSubscription)
            .where(PurchasedSubscription.sub_uuid == sub_uuid)
        )
        return result.scalars().first()
    except Exception as e:
        logger.error(f"Ошибка при получении подписки по UUID {sub_uuid}: {str(e)}", exc_info=True)
        return None

async def update_subscription_expiration(
    session: AsyncSession, 
    sub_uuid: str, 
    new_expiration: datetime
) -> bool:
    """
    Обновление даты истечения подписки
    :param session: Асинхронная сессия БД
    :param sub_uuid: UUID подписки
    :param new_expiration: Новая дата истечения
    :return: True при успехе, False при ошибке
    """
    try:
        result = await session.execute(
            select(PurchasedSubscription)
            .where(PurchasedSubscription.sub_uuid == sub_uuid)
        )
        subscription = result.scalars().first()
        
        if not subscription:
            logger.warning(f"Подписка с UUID {sub_uuid} не найдена")
            return False
            
        subscription.expired_at = new_expiration
        await session.commit()
        logger.info(f"Обновлена дата истечения подписки {sub_uuid}: {new_expiration}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при обновлении подписки {sub_uuid}: {str(e)}", exc_info=True)
        await session.rollback()
        return False

async def create_or_update_purchased_subscription(
    session: AsyncSession,
    telegram_id: int,
    sub_uuid: str,
    purchase_price: Union[Decimal, float, int, None] = None,
    renewal_price: Union[Decimal, float, int, None] = None,
    expired_at: datetime = None
) -> Optional[PurchasedSubscription]:
    """
    Создание или обновление подписки пользователя
    :param session: Асинхронная сессия БД
    :param telegram_id: Telegram ID пользователя
    :param sub_uuid: UUID подписки
    :param purchase_price: Цена покупки (не обновляется, если None)
    :param renewal_price: Цена продления (не обновляется, если None)
    :param expired_at: Дата истечения (не обновляется, если None)
    :return: Объект PurchasedSubscription или None
    """
    try:
        # Проверяем существование подписки
        subscription = await get_purchased_subscription_by_uuid(session, sub_uuid)
        
        if subscription:
            # Обновляем существующую подписку
            subscription.telegram_id = telegram_id
            if purchase_price is not None:
                new_purchase_price = Decimal(str(purchase_price))
                logger.info(f"Обновление purchase_price для {sub_uuid}: {subscription.purchase_price} -> {new_purchase_price}")
                subscription.purchase_price = new_purchase_price
            if renewal_price is not None:
                new_renewal_price = Decimal(str(renewal_price))
                logger.info(f"Обновление renewal_price для {sub_uuid}: {subscription.renewal_price} -> {new_renewal_price}")
                subscription.renewal_price = new_renewal_price
            if expired_at is not None:
                subscription.expired_at = expired_at
            logger.debug(f"Обновлена подписка {sub_uuid} для пользователя {telegram_id}")
        else:
            # Создаем новую подписку
            subscription = PurchasedSubscription(
                telegram_id=telegram_id,
                sub_uuid=sub_uuid,
                purchase_price=Decimal(str(purchase_price)) if purchase_price is not None else Decimal('0'),
                renewal_price=Decimal(str(renewal_price)) if renewal_price is not None else Decimal('0'),
                expired_at=expired_at,
                device_removal_count=0,
                last_removal_reset=None
            )
            session.add(subscription)
            logger.info(f"Создана подписка {sub_uuid} для пользователя {telegram_id}")
        
        await session.commit()
        await session.refresh(subscription)
        return subscription
        
    except Exception as e:
        logger.error(f"Ошибка при создании/обновлении подписки {sub_uuid}: {str(e)}", exc_info=True)
        await session.rollback()
        return None

async def create_purchased_subscription(
    session: AsyncSession,
    telegram_id: int,
    sub_uuid: str,
    purchase_price: Union[Decimal, float, int],
    renewal_price: Union[Decimal, float, int],
    expired_at: datetime
) -> Optional[PurchasedSubscription]:
    """Создание записи о купленной подписке (альтернатива create_or_update)"""
    return await create_or_update_purchased_subscription(
        session,
        telegram_id,
        sub_uuid,
        purchase_price,
        renewal_price,
        expired_at
    )

async def get_subscription_plan_by_id(
    session: AsyncSession,
    plan_id: int
) -> Optional[SubscriptionPlan]:
    """Получение плана подписки по ID"""
    try:
        result = await session.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
        )
        return result.scalars().first()
    except Exception as e:
        logger.error(f"Ошибка при получении плана подписки {plan_id}: {str(e)}")
        return None

async def get_active_promocode(
    session: AsyncSession,
    code: str
) -> Optional[Promocode]:
    """Получение активного промокода"""
    try:
        result = await session.execute(
            select(Promocode)
            .where(Promocode.code == code)
            .where(Promocode.is_active == True)
            .where(Promocode.valid_until >= datetime.now())
        )
        return result.scalars().first()
    except Exception as e:
        logger.error(f"Ошибка при получении промокода {code}: {str(e)}")
        return None

async def create_used_promocode(
    session: AsyncSession,
    telegram_id: int,
    promo_id: int,
    valid_until: Optional[datetime] = None
) -> Optional[UsedPromocode]:
    """Создание записи об использованном промокоде"""
    try:
        used_promo = UsedPromocode(
            telegram_id=telegram_id,
            promo_id=promo_id,
            valid_until=valid_until,
            use_status=True
        )
        session.add(used_promo)
        await session.flush()
        await session.refresh(used_promo)
        logger.info(f"Создана запись об использовании промокода {promo_id} пользователем {telegram_id}")
        return used_promo
    except Exception as e:
        logger.error(f"Ошибка при создании записи об использованном промокоде: {str(e)}")
        await session.rollback()
        return None

async def get_last_sync_time(
    session: AsyncSession,
    telegram_id: int
) -> datetime | None:
    """
    Получает время последней синхронизации для пользователя.
    
    Args:
        session: Асинхронная сессия БД.
        telegram_id: Telegram ID пользователя.
    
    Returns:
        datetime | None: Время последней синхронизации или None.
    """
    try:
        user = await session.get(User, telegram_id)
        return user.last_sync_time if user else None
    except Exception as e:
        logger.error(f"Ошибка при получении времени последней синхронизации для {telegram_id}: {str(e)}")
        return None

async def update_last_sync_time(
    session: AsyncSession,
    telegram_id: int,
    sync_time: datetime
) -> None:
    """
    Обновляет время последней синхронизации для пользователя.
    
    Args:
        session: Асинхронная сессия БД.
        telegram_id: Telegram ID пользователя.
        sync_time: Время синхронизации.
    """
    try:
        user = await session.get(User, telegram_id)
        if user:
            user.last_sync_time = sync_time
        else:
            user = User(telegram_id=telegram_id, last_sync_time=sync_time)
            session.add(user)
        await session.commit()
        logger.debug(f"Обновлено время синхронизации для {telegram_id}: {sync_time}")
    except Exception as e:
        logger.error(f"Ошибка при обновлении времени синхронизации для {telegram_id}: {str(e)}")
        await session.rollback()

async def update_device_removal_count(
    session: AsyncSession,
    sub_uuid: str,
    increment: bool = True
) -> bool:
    """
    Обновление счетчика удаления устройств и времени последнего сброса
    :param session: Асинхронная сессия БД
    :param sub_uuid: UUID подписки
    :param increment: Увеличить счетчик (True) или сбросить (False)
    :return: True при успехе, False при ошибке
    """
    try:
        result = await session.execute(
            select(PurchasedSubscription)
            .where(PurchasedSubscription.sub_uuid == sub_uuid)
        )
        subscription = result.scalars().first()
        
        if not subscription:
            logger.warning(f"Подписка с UUID {sub_uuid} не найдена")
            return False
            
        if increment:
            subscription.device_removal_count += 1
        else:
            subscription.device_removal_count = 0
            subscription.last_removal_reset = datetime.now()
            
        await session.commit()
        logger.info(f"Обновлен счетчик удаления устройств для подписки {sub_uuid}: {subscription.device_removal_count}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при обновлении счетчика удаления устройств для подписки {sub_uuid}: {str(e)}", exc_info=True)
        await session.rollback()
        return False