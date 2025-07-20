from datetime import datetime, timedelta
from aiogram.types import CallbackQuery, Message, Contact
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from core.database import crud
from core.api.remnawave_client import remnawave_service
from core.database.database import async_session
from .keyboards import (
    get_manage_subscription_kb,
    get_device_list_kb,
    get_device_details_kb,
    get_cancel_transfer_kb,
    get_back_to_devices_kb,
    get_back_to_manage_kb,
    DEVICES_PER_PAGE
)
from .texts import (
    MANAGE_SUBSCRIPTION_TEXT,
    NO_SUBSCRIPTION_TEXT,
    INSUFFICIENT_BALANCE_TEXT,
    RENEWAL_PRICE_NOT_SET_TEXT,
    RENEW_SUBSCRIPTION_SUCCESS_TEXT,
    NO_DEVICES_TEXT,
    DEVICES_PAGINATION_TEXT,
    DEVICE_DETAILS_TEXT,
    LAST_DEVICE_TEXT,
    DEVICE_REMOVED_TEXT,
    TRANSFER_COOLDOWN_TEXT,
    TRANSFER_REQUEST_TEXT,
    INVALID_CONTACT_TEXT,
    SELF_TRANSFER_TEXT,
    TRANSFER_SUCCESS_TEXT,
    TRANSFER_RECIPIENT_NOTIFICATION_TEXT,
    TRANSFER_CANCELLED_TEXT,
    DEVICE_REMOVAL_LIMIT_TEXT,
    TRANSFER_LIMIT_WARNING,
    TRANSFER_COOLDOWN_DAYS,
    DEVICE_REMOVAL_LIMIT
)
import logging

logger = logging.getLogger(__name__)

class TransferSubscriptionStates(StatesGroup):
    waiting_for_contact = State()

async def manage_subscription_menu(callback: CallbackQuery) -> None:
    """Меню управления подпиской"""
    try:
        await callback.answer()
        subscription_uuid = callback.data.split(":")[1]
        
        async with async_session() as session:
            local_sub = await crud.get_purchased_subscription_by_uuid(session, subscription_uuid)
            if not local_sub:
                await callback.message.answer(NO_SUBSCRIPTION_TEXT)
                return
            
            if local_sub.telegram_id != callback.from_user.id:
                await callback.message.answer("⚠️ Вы не владелец этой подписки")
                return
            
            sub_info = await remnawave_service.get_subscription_by_uuid(subscription_uuid)
            if "error" in sub_info:
                await callback.message.answer(f"Ошибка: {sub_info['error']}")
                return
            
            await callback.message.edit_text(
                MANAGE_SUBSCRIPTION_TEXT.format(
                    username=sub_info['username'],
                    used_traffic=sub_info['used_traffic_bytes'] / (1024 ** 3),
                    status=sub_info['status'].capitalize(),
                    renewal_price=float(local_sub.renewal_price) if local_sub.renewal_price else 0.0
                ),
                reply_markup=get_manage_subscription_kb(subscription_uuid),
                parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"Ошибка в manage_subscription_menu: {str(e)}", exc_info=True)
        await callback.message.answer("⚠️ Ошибка при загрузке меню")

async def renew_subscription(callback: CallbackQuery) -> None:
    """Продление подписки"""
    try:
        await callback.answer()
        subscription_uuid = callback.data.split(":")[1]
        
        async with async_session() as session:
            local_sub = await crud.get_purchased_subscription_by_uuid(session, subscription_uuid)
            if not local_sub:
                await callback.message.answer(NO_SUBSCRIPTION_TEXT)
                return
                
            if local_sub.telegram_id != callback.from_user.id:
                await callback.message.answer("⚠️ Вы не владелец этой подписки")
                return
                
            user = await crud.get_user_by_telegram_id(session, callback.from_user.id)
            if not user:
                await callback.message.answer("⚠️ Пользователь не найден")
                return
                
            if local_sub.renewal_price is None:
                await callback.message.answer(RENEWAL_PRICE_NOT_SET_TEXT)
                return
                
            if user.balance < local_sub.renewal_price:
                await callback.message.answer(
                    INSUFFICIENT_BALANCE_TEXT.format(
                        required=local_sub.renewal_price,
                        balance=user.balance
                    ),
                    parse_mode="HTML"
                )
                return
                
            user.balance -= local_sub.renewal_price
            new_expiration = datetime.now() + timedelta(days=30)
            local_sub.expired_at = new_expiration
            await session.commit()
            
            await callback.message.answer(
                RENEW_SUBSCRIPTION_SUCCESS_TEXT.format(
                    expiration=new_expiration.strftime("%Y-%m-%d %H:%M:%S"),
                    amount=local_sub.renewal_price
                )
            )
    except Exception as e:
        logger.error(f"Ошибка в renew_subscription: {str(e)}", exc_info=True)
        await callback.message.answer("⚠️ Ошибка при продлении подписки")

async def view_devices(callback: CallbackQuery) -> None:
    """Просмотр подключенных устройств"""
    try:
        await callback.answer()
        data = callback.data.split(":")
        subscription_uuid = data[1]
        page = int(data[2]) if len(data) > 2 else 0
        
        async with async_session() as session:
            local_sub = await crud.get_purchased_subscription_by_uuid(session, subscription_uuid)
            if not local_sub:
                await callback.message.answer(NO_SUBSCRIPTION_TEXT)
                return
                
            if local_sub.telegram_id != callback.from_user.id:
                await callback.message.answer("⚠️ Вы не владелец этой подписки")
                return
                
            devices = await remnawave_service.get_connected_devices(subscription_uuid)
            if not devices:
                await callback.message.answer(NO_DEVICES_TEXT)
                return
                
            sub_info = await remnawave_service.get_subscription_by_uuid(subscription_uuid)
            if "error" in sub_info:
                await callback.message.answer(f"Ошибка: {sub_info['error']}")
                return
                
            total_pages = (len(devices) + DEVICES_PER_PAGE - 1) // DEVICES_PER_PAGE
            paginated_devices = devices[page*DEVICES_PER_PAGE:(page+1)*DEVICES_PER_PAGE]
            
            await callback.message.edit_text(
                DEVICES_PAGINATION_TEXT.format(
                    username=sub_info['username'],
                    current_page=page+1,
                    total_pages=total_pages,
                    total_devices=len(devices)
                ),
                reply_markup=get_device_list_kb(
                    subscription_uuid,
                    paginated_devices,
                    page,
                    total_pages
                ),
                parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"Ошибка в view_devices: {str(e)}", exc_info=True)
        await callback.message.answer("⚠️ Ошибка при загрузке устройств")

async def show_device_details(callback: CallbackQuery) -> None:
    """Детали устройства"""
    try:
        await callback.answer()
        data = callback.data.split(":")
        subscription_uuid, short_hwid = data[1], data[2]
        
        async with async_session() as session:
            local_sub = await crud.get_purchased_subscription_by_uuid(session, subscription_uuid)
            if not local_sub:
                await callback.message.answer(NO_SUBSCRIPTION_TEXT)
                return
                
            if local_sub.telegram_id != callback.from_user.id:
                await callback.message.answer("⚠️ Вы не владелец этой подписки")
                return
                
            devices = await remnawave_service.get_connected_devices(subscription_uuid)
            device = next((d for d in devices if d['hwid'].startswith(short_hwid)), None)
            
            if not device:
                await callback.message.answer(NO_DEVICES_TEXT)
                return
                
            device_name = f"{device['platform']} {device['device_model']}".strip() or "Unknown"
            await callback.message.answer(
                DEVICE_DETAILS_TEXT.format(
                    hwid=device['hwid'],
                    name=device_name,
                    updated_at=device['updated_at']
                ),
                reply_markup=get_device_details_kb(subscription_uuid, device['hwid']),
                parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"Ошибка в show_device_details: {str(e)}", exc_info=True)
        await callback.message.answer("⚠️ Ошибка при загрузке устройства")

async def remove_device_callback(callback: CallbackQuery) -> None:
    """Удаление устройства с обновлением сообщения"""
    try:
        await callback.answer()
        data = callback.data.split(":")
        subscription_uuid, short_hwid = data[1], data[2]
        
        async with async_session() as session:
            local_sub = await crud.get_purchased_subscription_by_uuid(session, subscription_uuid)
            if not local_sub:
                await callback.message.edit_text(NO_SUBSCRIPTION_TEXT)
                return
                
            if local_sub.telegram_id != callback.from_user.id:
                await callback.message.edit_text("⚠️ Вы не владелец этой подписки")
                return
                
            current_time = datetime.now()
            
            if (local_sub.last_removal_reset and 
                (current_time - local_sub.last_removal_reset).days >= 30):
                local_sub.device_removal_count = 0
                local_sub.last_removal_reset = current_time
                
            if local_sub.device_removal_count >= DEVICE_REMOVAL_LIMIT:
                days_left = 30 - (current_time - local_sub.last_removal_reset).days
                await callback.message.edit_text(
                    DEVICE_REMOVAL_LIMIT_TEXT.format(days_left=days_left),
                    reply_markup=get_back_to_devices_kb(subscription_uuid)
                )
                return

            devices = await remnawave_service.get_connected_devices(subscription_uuid)
            if not devices:
                await callback.message.edit_text(
                    NO_DEVICES_TEXT,
                    reply_markup=get_back_to_manage_kb(subscription_uuid)
                )
                return
                
            if len(devices) <= 1:
                await callback.message.edit_text(
                    LAST_DEVICE_TEXT,
                    reply_markup=get_back_to_devices_kb(subscription_uuid)
                )
                return
                
            device = next((d for d in devices if d['hwid'].startswith(short_hwid)), None)
            if not device:
                await callback.message.edit_text(
                    "⚠️ Устройство не найдено",
                    reply_markup=get_back_to_devices_kb(subscription_uuid)
                )
                return
                
            if not await remnawave_service.remove_device(subscription_uuid, device['hwid']):
                await callback.message.edit_text(
                    "⚠️ Ошибка при удалении устройства",
                    reply_markup=get_back_to_devices_kb(subscription_uuid)
                )
                return
                
            local_sub.device_removal_count += 1
            if local_sub.last_removal_reset is None:
                local_sub.last_removal_reset = current_time
            await session.commit()
            
            updated_devices = await remnawave_service.get_connected_devices(subscription_uuid)
            sub_info = await remnawave_service.get_subscription_by_uuid(subscription_uuid)
            
            message_text = (
                f"✅ Устройство {device['hwid'][:8]} успешно удалено\n\n"
                f"📱 Осталось устройств: {len(updated_devices)}"
            )
            
            await callback.message.edit_text(
                text=message_text,
                reply_markup=get_device_list_kb(
                    subscription_uuid=subscription_uuid,
                    devices=updated_devices[:DEVICES_PER_PAGE],
                    page=0,
                    total_pages=max(1, len(updated_devices) // DEVICES_PER_PAGE)
                )
            )
            
    except Exception as e:
        logger.error(f"Ошибка при удалении устройства: {str(e)}", exc_info=True)
        await callback.message.edit_text(
            "⚠️ Произошла ошибка при удалении устройства",
            reply_markup=get_back_to_manage_kb(subscription_uuid)
        )

async def initiate_transfer_subscription(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало передачи подписки"""
    try:
        await callback.answer()
        subscription_uuid = callback.data.split(":")[1]
        
        async with async_session() as session:
            local_sub = await crud.get_purchased_subscription_by_uuid(session, subscription_uuid)
            if not local_sub:
                await callback.message.answer(NO_SUBSCRIPTION_TEXT)
                return
            
            if local_sub.telegram_id != callback.from_user.id:
                await callback.message.answer("⚠️ Вы не владелец этой подписки")
                return
            
            if local_sub.last_transfer_time:
                days_passed = (datetime.now() - local_sub.last_transfer_time).days
                if days_passed < TRANSFER_COOLDOWN_DAYS:
                    remaining_days = TRANSFER_COOLDOWN_DAYS - days_passed
                    await callback.message.answer(
                        TRANSFER_LIMIT_WARNING.format(
                            days_passed=days_passed,
                            remaining_days=remaining_days
                        ),
                        parse_mode="HTML"
                    )
                    return
            
            await state.update_data(subscription_uuid=subscription_uuid)
            await state.set_state(TransferSubscriptionStates.waiting_for_contact)
            await callback.message.answer(
                TRANSFER_REQUEST_TEXT,
                reply_markup=get_cancel_transfer_kb(subscription_uuid)
            )
    except Exception as e:
        logger.error(f"Ошибка в initiate_transfer_subscription: {str(e)}", exc_info=True)
        await callback.message.answer("⚠️ Ошибка при передаче подписки")
        await state.clear()

async def process_transfer_contact(message: Message, state: FSMContext) -> None:
    """Обработка передачи подписки новому владельцу"""
    try:
        if not isinstance(message.contact, Contact):
            await message.answer(INVALID_CONTACT_TEXT)
            return
            
        contact_id = message.contact.user_id
        if not contact_id:
            await message.answer(INVALID_CONTACT_TEXT)
            return
            
        if contact_id == message.from_user.id:
            await message.answer(SELF_TRANSFER_TEXT)
            return
            
        data = await state.get_data()
        subscription_uuid = data.get("subscription_uuid")
        if not subscription_uuid:
            await message.answer("⚠️ Подписка не найдена")
            await state.clear()
            return
            
        async with async_session() as session:
            # Обновляем владельца в локальной БД
            success = await crud.update_subscription_transfer(
                session=session,
                sub_uuid=subscription_uuid,
                new_telegram_id=contact_id
            )
            
            if not success:
                await message.answer(NO_SUBSCRIPTION_TEXT)
                await state.clear()
                return
            
            # Получаем информацию о подписке для уведомлений
            sub_info = await remnawave_service.get_subscription_by_uuid(subscription_uuid)
            if "error" in sub_info:
                await message.answer(f"Ошибка API: {sub_info['error']}")
                await state.clear()
                return
                
            sub_name = sub_info.get('username', subscription_uuid[:8])
            
            await message.answer(
                TRANSFER_SUCCESS_TEXT.format(
                    subscription_name=sub_name,
                    contact_id=contact_id,
                    next_transfer_date=(datetime.now() + timedelta(days=TRANSFER_COOLDOWN_DAYS)).strftime('%d.%m.%Y')
                )
            )
            
            # Уведомляем нового владельца
            await message.bot.send_message(
                contact_id,
                TRANSFER_RECIPIENT_NOTIFICATION_TEXT.format(username=sub_name),
                parse_mode="HTML"
            )
            
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка в process_transfer_contact: {str(e)}", exc_info=True)
        await message.answer("⚠️ Ошибка при передаче подписки")
        await state.clear()

async def cancel_transfer(callback: CallbackQuery, state: FSMContext) -> None:
    """Отмена передачи подписки"""
    try:
        await callback.answer()
        await callback.message.answer(TRANSFER_CANCELLED_TEXT)
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка в cancel_transfer: {str(e)}")
        await callback.message.answer("⚠️ Ошибка при отмене передачи")
