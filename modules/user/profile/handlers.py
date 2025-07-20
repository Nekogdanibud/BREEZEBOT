from aiogram import F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from core.database.crud import get_user_full_data
from .texts import PROFILE_TEXT
from .keyboards import get_profile_kb
from core.database.database import async_session
import logging
from datetime import datetime
from core.database.model import User

logger = logging.getLogger(__name__)

async def show_profile(callback: CallbackQuery):
    """Обработчик показа профиля пользователя с данными только из локальной БД"""
    try:
        await callback.answer()

        async with async_session() as session:
            # Получаем данные пользователя из локальной БД
            user_data = await get_user_full_data(session, callback.from_user.id)
            
            if not user_data or not isinstance(user_data.get("user"), User):
                return await callback.answer("❌ Ошибка загрузки профиля", show_alert=True)
            
            user = user_data["user"]
            
            # Формируем текст профиля
            profile_text = PROFILE_TEXT.format(
                username=f"@{user.username}" if user.username else "Не установлен",
                balance=float(user.balance) if user.balance else 0.0,
                subscriptions_count=user_data.get("subscriptions_count", 0)
            )
            
            try:
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
