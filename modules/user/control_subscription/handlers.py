from aiogram.types import CallbackQuery, Message, Contact
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import crud
from core.api.remnawave_client import remnawave_service
from core.database.database import async_session
from datetime import datetime, timedelta
from decimal import Decimal
import logging
from .keyboards import get_manage_subscription_kb, get_device_list_kb, get_device_details_kb, get_cancel_transfer_kb
from .texts import (
    MANAGE_SUBSCRIPTION_TEXT,
    NO_SUBSCRIPTION_TEXT,
    INSUFFICIENT_BALANCE_TEXT,
    RENEWAL_PRICE_NOT_SET_TEXT,
    RENEW_SUBSCRIPTION_SUCCESS_TEXT,
    NO_DEVICES_TEXT,
    DEVICES_LIST_TEXT,
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
)

logger = logging.getLogger(__name__)

class TransferSubscriptionStates(StatesGroup):
    waiting_for_contact = State()

async def manage_subscription_menu(callback: CallbackQuery) -> None:
    try:
        await callback.answer()
        subscription_uuid = callback.data.split(":")[1]
        async with async_session() as session:
            local_sub = await crud.get_purchased_subscription_by_uuid(session, subscription_uuid)
            if not local_sub:
                await callback.message.answer(NO_SUBSCRIPTION_TEXT)
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
                    renewal_price=float(local_sub.renewal_price)
                ),
                reply_markup=get_manage_subscription_kb(subscription_uuid),
                parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"Ошибка в manage_subscription_menu для uuid {subscription_uuid}: {str(e)}", exc_info=True)
        await callback.answer("⚠️ Ошибка", show_alert=True)

async def renew_subscription(callback: CallbackQuery) -> None:
    try:
        await callback.answer()
        subscription_uuid = callback.data.split(":")[1]
        async with async_session() as session:
            local_sub = await crud.get_purchased_subscription_by_uuid(session, subscription_uuid)
            if not local_sub:
                await callback.answer(NO_SUBSCRIPTION_TEXT, show_alert=True)
                return
            user = await crud.get_user_by_telegram_id(session, callback.from_user.id)
            if not user:
                await callback.answer("⚠️ Пользователь не найден", show_alert=True)
                return
            if local_sub.renewal_price is None:
                await callback.answer(RENEWAL_PRICE_NOT_SET_TEXT, show_alert=True)
                return
            renewal_price = Decimal(str(local_sub.renewal_price))
            if user.balance < renewal_price:
                await callback.answer(
                    INSUFFICIENT_BALANCE_TEXT.format(
                        required=renewal_price, balance=user.balance
                    ),
                    show_alert=True
                )
                return
            user.balance -= renewal_price
            new_expiration = datetime.now() + timedelta(days=30)
            await crud.update_subscription_expiration(session, subscription_uuid, new_expiration)
            await session.commit()
            logger.info(f"Подписка {subscription_uuid} продлена для user_id {user.telegram_id}")
            await callback.message.answer(
                RENEW_SUBSCRIPTION_SUCCESS_TEXT.format(
                    expiration=new_expiration.strftime("%Y-%m-%d %H:%M:%S"),
                    amount=renewal_price
                )
            )
    except Exception as e:
        logger.error(f"Ошибка в renew_subscription для uuid {subscription_uuid}: {str(e)}")
        await callback.answer("⚠️ Ошибка", show_alert=True)

async def view_devices(callback: CallbackQuery) -> None:
    try:
        await callback.answer()
        subscription_uuid = callback.data.split(":")[1]
        devices = await remnawave_service.get_connected_devices(subscription_uuid)
        if not devices:
            await callback.message.answer(NO_DEVICES_TEXT)
            return
        if len(devices) > 5:
            logger.warning(f"Подписка {subscription_uuid} имеет более 5 устройств: {len(devices)}")
            devices = devices[:5]
        sub_info = await remnawave_service.get_subscription_by_uuid(subscription_uuid)
        if "error" in sub_info:
            await callback.message.answer(f"Ошибка: {sub_info['error']}")
            return
        await callback.message.answer(
            DEVICES_LIST_TEXT.format(username=sub_info['username']),
            reply_markup=get_device_list_kb(subscription_uuid, devices),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка в view_devices для uuid {subscription_uuid}: {str(e)}")
        await callback.answer("⚠️ Ошибка", show_alert=True)

async def show_device_details(callback: CallbackQuery) -> None:
    try:
        await callback.answer()
        data = callback.data.split(":")
        if len(data) != 3:
            await callback.answer("⚠️ Неверный запрос", show_alert=True)
            return
        subscription_uuid, short_hwid = data[1], data[2]
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
        logger.error(f"Ошибка в show_device_details для uuid {subscription_uuid}: {str(e)}")
        await callback.answer("⚠️ Ошибка", show_alert=True)

async def remove_device_callback(callback: CallbackQuery) -> None:
    try:
        await callback.answer()
        data = callback.data.split(":")
        if len(data) != 3:
            await callback.answer("⚠️ Неверный запрос", show_alert=True)
            return
        subscription_uuid, short_hwid = data[1], data[2]
        
        async with async_session() as session:
            local_sub = await crud.get_purchased_subscription_by_uuid(session, subscription_uuid)
            if not local_sub:
                await callback.message.answer(NO_SUBSCRIPTION_TEXT)
                return
                
            DEVICE_REMOVAL_LIMIT = 4
            current_time = datetime.now()
            
            # Проверяем, нужно ли сбросить счетчик
            if local_sub.last_removal_reset and (current_time - local_sub.last_removal_reset).days >= 30:
                await crud.update_device_removal_count(session, subscription_uuid, increment=False)
                local_sub = await crud.get_purchased_subscription_by_uuid(session, subscription_uuid)
                
            # Проверяем лимит удалений
            if local_sub.device_removal_count >= DEVICE_REMOVAL_LIMIT:
                days_left = 30 - (current_time - local_sub.last_removal_reset).days if local_sub.last_removal_reset else 30
                await callback.message.answer(
                    DEVICE_REMOVAL_LIMIT_TEXT.format(days_left=days_left),
                    parse_mode="HTML"
                )
                logger.info(f"Достигнут лимит удаления устройств для подписки {subscription_uuid}: {local_sub.device_removal_count}")
                return

            devices = await remnawave_service.get_connected_devices(subscription_uuid)
            if not devices:
                await callback.message.answer(NO_DEVICES_TEXT)
                return
            if len(devices) <= 1:
                await callback.message.answer(LAST_DEVICE_TEXT)
                return
                
            device = next((d for d in devices if d['hwid'].startswith(short_hwid)), None)
            if not device:
                await callback.message.answer(NO_DEVICES_TEXT)
                return
                
            success = await remnawave_service.remove_device(subscription_uuid, device['hwid'])
            if not success:
                await callback.message.answer("⚠️ Ошибка при удалении устройства")
                return
                
            # Обновляем счетчик удалений
            await crud.update_device_removal_count(session, subscription_uuid, increment=True)
            if local_sub.last_removal_reset is None:
                local_sub.last_removal_reset = current_time
                await session.commit()
                
            logger.info(f"Устройство {device['hwid']} удалено для подписки {subscription_uuid}")
            await callback.message.answer(DEVICE_REMOVED_TEXT.format(hwid=device['hwid'][:8]))
            await view_devices(callback)
            
    except Exception as e:
        logger.error(f"Ошибка в remove_device_callback для uuid {subscription_uuid}: {str(e)}")
        await callback.answer("⚠️ Ошибка", show_alert=True)

async def initiate_transfer_subscription(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        await callback.answer()
        subscription_uuid = callback.data.split(":")[1]
        async with async_session() as session:
            local_sub = await crud.get_purchased_subscription_by_uuid(session, subscription_uuid)
            if not local_sub:
                await callback.answer(NO_SUBSCRIPTION_TEXT, show_alert=True)
                return
            if local_sub.last_transfer_time and (
                datetime.now() - local_sub.last_transfer_time
            ).days < 30:
                days_left = 30 - (datetime.now() - local_sub.last_transfer_time).days
                await callback.answer(
                    TRANSFER_COOLDOWN_TEXT.format(days_left=days_left),
                    show_alert=True
                )
                return
            await state.update_data(subscription_uuid=subscription_uuid)
            await state.set_state(TransferSubscriptionStates.waiting_for_contact)
            await callback.message.answer(
                TRANSFER_REQUEST_TEXT,
                reply_markup=get_cancel_transfer_kb(subscription_uuid)
            )
    except Exception as e:
        logger.error(f"Ошибка в initiate_transfer_subscription для uuid {subscription_uuid}: {str(e)}")
        await callback.answer("⚠️ Ошибка", show_alert=True)
        await state.clear()

async def process_transfer_contact(message: Message, state: FSMContext) -> None:
    try:
        if not isinstance(message.contact, Contact):
            await message.answer(INVALID_CONTACT_TEXT)
            return
        contact_telegram_id = message.contact.user_id
        if not contact_telegram_id:
            await message.answer(INVALID_CONTACT_TEXT)
            return
        if contact_telegram_id == message.from_user.id:
            await message.answer(SELF_TRANSFER_TEXT)
            return
        data = await state.get_data()
        subscription_uuid = data.get("subscription_uuid")
        if not subscription_uuid:
            await message.answer("⚠️ Ошибка: подписка не найдена")
            await state.clear()
            return
        async with async_session() as session:
            local_sub = await crud.get_purchased_subscription_by_uuid(session, subscription_uuid)
            if not local_sub:
                await message.answer(NO_SUBSCRIPTION_TEXT)
                await state.clear()
                return
            recipient = await crud.get_user_by_telegram_id(session, contact_telegram_id)
            if not recipient:
                recipient = await crud.create_user(session, contact_telegram_id)
                if not recipient:
                    await message.answer("⚠️ Не удалось создать пользователя")
                    await state.clear()
                    return
            sub_info = await remnawave_service.get_subscription_by_uuid(subscription_uuid)
            if "error" in sub_info:
                await message.answer(f"Ошибка: {sub_info['error']}")
                await state.clear()
                return
            local_sub.telegram_id = contact_telegram_id
            local_sub.last_transfer_time = datetime.now()
            await session.commit()
            logger.info(
                f"Подписка {subscription_uuid} передана от {message.from_user.id} к {contact_telegram_id}"
            )
            await message.answer(
                TRANSFER_SUCCESS_TEXT.format(contact_id=contact_telegram_id)
            )
            await message.bot.send_message(
                contact_telegram_id,
                TRANSFER_RECIPIENT_NOTIFICATION_TEXT.format(username=sub_info.get('username', 'Без имени')),
                parse_mode="HTML"
            )
            await state.clear()
    except Exception as e:
        logger.error(f"Ошибка в process_transfer_contact для uuid {subscription_uuid}: {str(e)}")
        await message.answer("⚠️ Ошибка")
        await state.clear()

async def cancel_transfer(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        await callback.answer()
        await callback.message.answer(TRANSFER_CANCELLED_TEXT)
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка в cancel_transfer: {str(e)}")
        await callback.answer("⚠️ Ошибка", show_alert=True)
        await state.clear()