from aiogram import F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from core.database.crud import get_user_full_data
from .texts import PROFILE_TEXT
from .keyboards import get_profile_kb
from core.database.database import async_session
from core.api.remnawave_client import remnawave_service
import logging

logger = logging.getLogger(__name__)

async def show_profile(callback: CallbackQuery):
    """Обработчик показа профиля пользователя"""
    try:
        # Убираем индикатор загрузки сразу
        await callback.answer()

        async with async_session() as session:
            user_data = await get_user_full_data(session, callback.from_user.id)
            
            if not user_data:
                return await callback.answer("❌ Ошибка загрузки профиля", show_alert=True)
            
            user, _, _ = user_data  # Игнорируем локальные подписки
            
            # Получаем подписки из Remnawave API
            remote_subscriptions = await remnawave_service.get_user_by_telegram_id(callback.from_user.id)
            
            # Считаем только активные подписки
            active_subscriptions_count = sum(
                1 for sub in remote_subscriptions 
                if not sub.get("error") and sub.get("status") == 'ACTIVE'
            )
            
            profile_text = PROFILE_TEXT.format(
                username=f"@{user.username}" if user.username else "Не установлен",
                balance=getattr(user, 'balance', 0),
                subscriptions_count=active_subscriptions_count  # Только это поле изменено
            )
            
            try:
                # Редактируем сообщение
                await callback.message.edit_text(
                    text=profile_text,
                    reply_markup=get_profile_kb()
                )
            except TelegramBadRequest:
                # Если сообщение не изменилось, игнорируем
                pass
                
    except Exception as e:
        logger.error(f"Ошибка в show_profile: {str(e)}", exc_info=True)
        await callback.answer("⚠️ Произошла ошибка при загрузке профиля", show_alert=True)
