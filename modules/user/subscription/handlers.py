from aiogram.types import CallbackQuery
from core.database.crud import get_purchased_subscriptions
from core.api.remnawave_client import remnawave_service
from . import texts, keyboards
from core.database.database import async_session
import logging
from core.database import crud

logger = logging.getLogger(__name__)

async def show_subscriptions(callback: CallbackQuery) -> None:
    """Обработчик раздела 'Мои подписки' (только локальные данные)"""
    try:
        await callback.answer()
        user_id = callback.from_user.id
        
        async with async_session() as session:
            # Получаем подписки только из локальной БД
            local_subscriptions = await get_purchased_subscriptions(session, user_id)
            
            if not local_subscriptions:
                await callback.message.edit_text(
                    texts.NO_SUBSCRIPTIONS_TEXT,
                    reply_markup=keyboards.get_no_subscriptions_kb()
                )
                return
            
            # Формируем список подписок для клавиатуры
            subscriptions_info = []
            for sub in local_subscriptions:
                subscriptions_info.append({
                    "uuid": sub.sub_uuid,
                    "username": sub.username
                })
            
            await callback.message.edit_text(
                texts.SUBSCRIPTIONS_LIST_TEXT,
                reply_markup=keyboards.get_subscriptions_list_kb(subscriptions_info)
            )
            
    except Exception as e:
        logger.error(f"Ошибка в show_subscriptions: {str(e)}", exc_info=True)
        await callback.answer("⚠️ Ошибка при загрузке подписок", show_alert=True)

async def show_subscription_detail(callback: CallbackQuery) -> None:
    """Детали подписки с запросом в API по UUID"""
    try:
        await callback.answer()
        subscription_uuid = callback.data.split(":")[1]
        
        async with async_session() as session:
            # Проверяем существование подписки в локальной БД
            local_sub = await crud.get_purchased_subscription_by_uuid(session, subscription_uuid)
            if not local_sub:
                await callback.answer("⚠️ Подписка не найдена", show_alert=True)
                return
            
            # Запрос данных подписки в API
            sub_info = await remnawave_service.get_subscription_by_uuid(subscription_uuid)
            
            if "error" in sub_info:
                await callback.message.answer(
                    texts.SUBSCRIPTION_ERROR_TEXT.format(error=sub_info['error'])
                )
                return
            
            # Форматирование данных для отображения
            status_emoji = {
                "active": "🟢",
                "disabled": "🔴",
                "expired": "🟠",
                "limited": "🟡"
            }.get(sub_info["status"].lower(), "⚪️")
            
            message_text = texts.SUBSCRIPTION_DETAIL_TEMPLATE.format(
                status_emoji=status_emoji,
                username=local_sub.username,
                status=sub_info['status'].capitalize(),
                used_traffic=sub_info['used_traffic_bytes'] / (1024 ** 3),
                data_limit=sub_info['data_limit'],
                expire=sub_info['expire'],
                last_connected=sub_info['last_connected_node'],
                purchase_price=float(local_sub.purchase_price) if local_sub.purchase_price else 0.0,
                renewal_price=float(local_sub.renewal_price) if local_sub.renewal_price else 0.0
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
        logger.error(f"Ошибка в show_subscription_detail: {str(e)}", exc_info=True)
        await callback.answer("⚠️ Ошибка при загрузке подписки", show_alert=True)
