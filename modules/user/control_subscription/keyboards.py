from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_manage_subscription_kb(subscription_uuid: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Продлить подписку", callback_data=f"renew_subscription:{subscription_uuid}")
    kb.button(text="📱 Просмотр устройств", callback_data=f"view_devices:{subscription_uuid}")
    kb.button(text="👤 Передать подписку", callback_data=f"transfer_subscription:{subscription_uuid}")
    kb.button(text="⬅️ Назад", callback_data=f"subscription_detail:{subscription_uuid}")
    kb.adjust(1)
    return kb.as_markup()

def get_device_list_kb(subscription_uuid: str, devices: list):
    kb = InlineKeyboardBuilder()
    for device in devices:
        device_name = f"{device['platform']} {device['device_model']}".strip() or device['hwid'][:8]
        # Ограничиваем hwid до 8 символов для callback_data
        short_hwid = device['hwid'][:8]
        callback_data = f"device_details:{subscription_uuid}:{short_hwid}"
        # Логируем длину callback_data для диагностики
        if len(callback_data.encode('utf-8')) > 64:
            print(f"Warning: callback_data too long ({len(callback_data.encode('utf-8'))} bytes): {callback_data}")
        kb.button(
            text=device_name,
            callback_data=callback_data
        )
    kb.button(text="⬅️ Назад", callback_data=f"manage_subscription:{subscription_uuid}")
    kb.adjust(1)
    return kb.as_markup()

def get_device_details_kb(subscription_uuid: str, hwid: str):
    kb = InlineKeyboardBuilder()
    # Используем ту же длину hwid, что в get_device_list_kb
    short_hwid = hwid[:8]
    kb.button(text="🗑 Удалить устройство", callback_data=f"remove_device:{subscription_uuid}:{short_hwid}")
    kb.button(text="⬅️ Назад", callback_data=f"view_devices:{subscription_uuid}")
    kb.adjust(1)
    return kb.as_markup()

def get_cancel_transfer_kb(subscription_uuid: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="❌ Отмена", callback_data=f"cancel_transfer:{subscription_uuid}")
    kb.adjust(1)
    return kb.as_markup()