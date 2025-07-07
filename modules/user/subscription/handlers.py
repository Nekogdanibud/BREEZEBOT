from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import crud
from core.api.remnawave_client import remnawave_service
from . import texts, keyboards
from core.database.database import async_session
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

async def sync_subscriptions(session: AsyncSession, telegram_id: int, force: bool = False) -> bool:
    """
    Синхронизация подписок между локальной базой данных и API Remnawave.
    (Временно не используется, будет реализована в админ-панели.)
    
    Args:
        session: Асинхронная сессия БД.
        telegram_id: Telegram ID пользователя.
        force: Принудительно выполнить синхронизацию.
    
    Returns:
        bool: True если синхронизация успешна или не требуется, False в случае ошибки.
    """
    try:
        # Проверяем, нужна ли синхронизация (раз в час)
        last_sync = await crud.get_last_sync_time(session, telegram_id)
        if not force and last_sync and (datetime.now() - last_sync).total_seconds() < 3600:
            logger.info(f"Синхронизация для {telegram_id} не требуется")
            return True
        
        remote_subscriptions = await remnawave_service.get_user_by_telegram_id(telegram_id)
        remote_uuids = {sub["uuid"] for sub in remote_subscriptions if not sub.get("error")}
        
        local_subscriptions = await crud.get_purchased_subscriptions(session, telegram_id)
        local_uuids = {sub.sub_uuid for sub in local_subscriptions}
        
        for sub in local_subscriptions:
            if sub.sub_uuid not in remote_uuids:
                logger.warning(f"Подписка {sub.sub_uuid} отсутствует в API, удаляем из локальной БД")
                await session.delete(sub)
        
        for sub in remote_subscriptions:
            if not sub.get("error"):
                existing_sub = await crud.get_purchased_subscription_by_uuid(session, sub["uuid"])
                if existing_sub:
                    logger.debug(f"Подписка {sub['uuid']} существует, текущие цены: purchase={existing_sub.purchase_price}, renewal={existing_sub.renewal_price}")
                
                await crud.create_or_update_purchased_subscription(
                    session=session,
                    telegram_id=telegram_id,
                    sub_uuid=sub["uuid"],
                    purchase_price=None if existing_sub else 0,
                    renewal_price=None if existing_sub else 0,
                    expired_at=datetime.strptime(sub["expire"], "%Y-%m-%d %H:%M:%S")
                    if sub["expire"] != "N/A" else datetime.now()
                )
        
        # Сохраняем время синхронизации
        await crud.update_last_sync_time(session, telegram_id, datetime.now())
        await session.commit()
        logger.info(f"Синхронизация подписок завершена для {telegram_id}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка синхронизации подписок для {telegram_id}: {str(e)}", exc_info=True)
        await session.rollback()
        return False

async def show_subscriptions(callback: CallbackQuery) -> None:
    """
    Обработчик раздела 'Мои подписки'. Редактирует текущее сообщение, если возможно, иначе отправляет новое.
    
    Args:
        callback: CallbackQuery от Telegram.
    """
    try:
        await callback.answer()
        
        async with async_session() as session:
            user_id = callback.from_user.id
            
            local_subscriptions = await crud.get_purchased_subscriptions(session, user_id)
            if not local_subscriptions:
                try:
                    await callback.message.edit_text(
                        texts.NO_SUBSCRIPTIONS_TEXT,
                        reply_markup=keyboards.get_no_subscriptions_kb()
                    )
                except Exception as edit_error:
                    logger.warning(f"Не удалось отредактировать сообщение для user_id {user_id}: {str(edit_error)}")
                    await callback.message.answer(
                        texts.NO_SUBSCRIPTIONS_TEXT,
                        reply_markup=keyboards.get_no_subscriptions_kb()
                    )
                return
            
            remote_subscriptions = await remnawave_service.get_user_by_telegram_id(user_id)
            remote_sub_map = {sub["uuid"]: sub for sub in remote_subscriptions if not sub.get("error")}
            
            subscriptions_info = []
            for sub in local_subscriptions:
                remote_sub = remote_sub_map.get(sub.sub_uuid)
                subscriptions_info.append({
                    "uuid": sub.sub_uuid,
                    "username": remote_sub.get("username") if remote_sub else f"Подписка {sub.sub_uuid[:8]}",
                    "status": remote_sub.get("status", "unknown") if remote_sub else "unknown",
                    "used_traffic_bytes": remote_sub.get("used_traffic_bytes", 0) if remote_sub else 0,
                    "data_limit": remote_sub.get("data_limit", 0) if remote_sub else 0,
                    "expire": remote_sub.get("expire", sub.expired_at.isoformat() if sub.expired_at else "N/A") if remote_sub else (sub.expired_at.isoformat() if sub.expired_at else "N/A"),
                    "last_connected_node": remote_sub.get("last_connected_node", "N/A") if remote_sub else "N/A",
                    "inbounds": remote_sub.get("inbounds", ["N/A"]) if remote_sub else ["N/A"],
                    "subscription_url": remote_sub.get("subscription_url", "N/A") if remote_sub else "N/A",
                    "purchase_price": float(sub.purchase_price) if sub.purchase_price is not None else 0.0,
                    "renewal_price": float(sub.renewal_price) if sub.renewal_price is not None else 0.0,
                    "expired_at": sub.expired_at.isoformat() if sub.expired_at else "N/A"
                })
            
            if not subscriptions_info:
                try:
                    await callback.message.edit_text(
                        texts.NO_SUBSCRIPTIONS_TEXT,
                        reply_markup=keyboards.get_no_subscriptions_kb()
                    )
                except Exception as edit_error:
                    logger.warning(f"Не удалось отредактировать сообщение для user_id {user_id}: {str(edit_error)}")
                    await callback.message.answer(
                        texts.NO_SUBSCRIPTIONS_TEXT,
                        reply_markup=keyboards.get_no_subscriptions_kb()
                    )
                return
            
            try:
                await callback.message.edit_text(
                    texts.SUBSCRIPTIONS_LIST_TEXT,
                    reply_markup=keyboards.get_subscriptions_list_kb(subscriptions_info)
                )
            except Exception as edit_error:
                logger.warning(f"Не удалось отредактировать сообщение для user_id {user_id}: {str(edit_error)}")
                await callback.message.answer(
                    texts.SUBSCRIPTIONS_LIST_TEXT,
                    reply_markup=keyboards.get_subscriptions_list_kb(subscriptions_info)
                )
            
    except Exception as e:
        logger.error(f"Ошибка в show_subscriptions для user_id {callback.from_user.id}: {str(e)}", exc_info=True)
        await callback.answer("⚠️ Произошла ошибка при загрузке подписок", show_alert=True)

async def show_subscription_detail(callback: CallbackQuery) -> None:
    """
    Отображение деталей подписки.
    
    Args:
        callback: CallbackQuery от Telegram.
    """
    try:
        await callback.answer()
        
        subscription_uuid = callback.data.split(":")[1]
        if not subscription_uuid or not isinstance(subscription_uuid, str):
            logger.warning(f"Некорректный subscription_uuid: {subscription_uuid}")
            await callback.answer("⚠️ Неверный идентификатор подписки", show_alert=True)
            return
        
        async with async_session() as session:
            local_sub = await crud.get_purchased_subscription_by_uuid(session, subscription_uuid)
            if not local_sub:
                logger.warning(f"Локальная подписка {subscription_uuid} не найдена")
                await callback.answer("⚠️ Подписка не найдена", show_alert=True)
                return
            
            sub_info = await remnawave_service.get_subscription_by_uuid(subscription_uuid)
            
            if "error" in sub_info:
                await callback.message.answer(
                    texts.SUBSCRIPTION_ERROR_TEXT.format(error=sub_info['error'])
                )
                return
            
            status_emoji = {
                "active": "🟢",
                "disabled": "🔴",
                "expired": "🟠",
                "limited": "🟡"
            }.get(sub_info["status"].lower(), "⚪️")
            
            message_text = texts.SUBSCRIPTION_DETAIL_TEMPLATE.format(
                status_emoji=status_emoji,
                username=sub_info['username'],
                status=sub_info['status'].capitalize(),
                used_traffic=sub_info['used_traffic_bytes'] / (1024 ** 3),
                data_limit=sub_info['data_limit'],
                expire=sub_info['expire'],
                last_connected=sub_info['last_connected_node'],
                purchase_price=float(local_sub.purchase_price) if local_sub.purchase_price is not None else 0.0,
                renewal_price=float(local_sub.renewal_price) if local_sub.renewal_price is not None else 0.0
            )
            
            await callback.message.edit_text(
                text=message_text,
                reply_markup=keyboards.get_subscription_detail_kb(
                    subscription_uuid=subscription_uuid,
                    subscription_url=sub_info['subscription_url']
                ),
                parse_mode="HTML"
            )
            
    except Exception as e:
        logger.error(f"Ошибка в show_subscription_detail для uuid {subscription_uuid}: {str(e)}", exc_info=True)
        await callback.answer("⚠️ Произошла ошибка при загрузке подписки", show_alert=True)