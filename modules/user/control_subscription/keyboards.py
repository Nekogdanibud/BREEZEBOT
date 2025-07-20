from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Dict, Optional

# Константы для кнопок
BACK_BUTTON = "⬅️ Назад"
MANAGE_BUTTON = "⚙️ Управление"
DEVICES_BUTTON = "📱 Устройства"
RENEW_BUTTON = "🔄 Продлить"
TRANSFER_BUTTON = "👤 Передать"
REMOVE_BUTTON = "🗑 Удалить"
CANCEL_BUTTON = "❌ Отмена"
PREV_PAGE_BUTTON = "◀️"
NEXT_PAGE_BUTTON = "▶️"
HELP_BUTTON = "❓ Помощь"

# Количество устройств на странице
DEVICES_PER_PAGE = 5

def get_main_menu_kb(role: str = "USER") -> InlineKeyboardMarkup:
    """Главное меню с учетом роли пользователя"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="👤 Профиль", callback_data="menu:profile")
    builder.button(text="💎 Подписки", callback_data="menu:subscriptions")
    
    if role in ["ADMIN", "SUPPORT"]:
        builder.button(text="🛎 Поддержка", callback_data="menu:support")
    if role == "ADMIN":
        builder.button(text="👑 Админ-панель", callback_data="menu:admin")
    
    builder.button(text=HELP_BUTTON, callback_data="menu:help")
    
    # Распределение кнопок (2 в первом ряду, остальные по 1)
    builder.adjust(2, 1)
    return builder.as_markup()

def get_subscriptions_list_kb(subscriptions: List[Dict]) -> InlineKeyboardMarkup:
    """Список подписок пользователя"""
    builder = InlineKeyboardBuilder()
    
    for sub in subscriptions:
        builder.button(
            text=sub['username'],
            callback_data=f"subscription_detail:{sub['uuid']}"
        )
    
    builder.button(text="🛒 Купить подписку", callback_data="buy_subscription")
    builder.button(text=BACK_BUTTON, callback_data="menu:main")
    
    builder.adjust(1, 2)
    return builder.as_markup()

def get_subscription_detail_kb(subscription_uuid: str, subscription_url: str) -> InlineKeyboardMarkup:
    """Детали подписки"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="🔗 Ссылка подключения", url=subscription_url)
    builder.button(text=MANAGE_BUTTON, callback_data=f"manage_subscription:{subscription_uuid}")
    builder.button(text=BACK_BUTTON, callback_data="menu:subscriptions")
    
    builder.adjust(1, 1, 1)
    return builder.as_markup()

def get_manage_subscription_kb(subscription_uuid: str) -> InlineKeyboardMarkup:
    """Меню управления подпиской"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text=RENEW_BUTTON, callback_data=f"renew_subscription:{subscription_uuid}")
    builder.button(text=DEVICES_BUTTON, callback_data=f"view_devices:{subscription_uuid}:0")
    builder.button(text=TRANSFER_BUTTON, callback_data=f"transfer_subscription:{subscription_uuid}")
    builder.button(text=BACK_BUTTON, callback_data=f"subscription_detail:{subscription_uuid}")
    
    builder.adjust(1, 2, 1)
    return builder.as_markup()

def get_device_list_kb(
    subscription_uuid: str,
    devices: List[Dict],
    page: int,
    total_pages: int
) -> InlineKeyboardMarkup:
    """Список устройств с пагинацией"""
    builder = InlineKeyboardBuilder()
    
    # Кнопки устройств
    for device in devices:
        device_name = f"{device['platform']} {device['device_model']}".strip() or device['hwid'][:8]
        builder.button(
            text=device_name,
            callback_data=f"device_details:{subscription_uuid}:{device['hwid'][:8]}"
        )
    
    # Пагинация
    pagination_row = []
    if page > 0:
        pagination_row.append(
            InlineKeyboardButton(
                text=PREV_PAGE_BUTTON,
                callback_data=f"view_devices:{subscription_uuid}:{page-1}"
            )
        )
    if page < total_pages - 1:
        pagination_row.append(
            InlineKeyboardButton(
                text=NEXT_PAGE_BUTTON,
                callback_data=f"view_devices:{subscription_uuid}:{page+1}"
            )
        )
    
    # Навигация
    builder.row(*pagination_row)
    builder.button(text=BACK_BUTTON, callback_data=f"manage_subscription:{subscription_uuid}")
    
    builder.adjust(1, *[1]*len(devices), len(pagination_row), 1)
    return builder.as_markup()

def get_device_details_kb(subscription_uuid: str, hwid: str) -> InlineKeyboardMarkup:
    """Детали устройства"""
    builder = InlineKeyboardBuilder()
    
    builder.button(
        text=REMOVE_BUTTON,
        callback_data=f"remove_device:{subscription_uuid}:{hwid[:8]}"
    )
    builder.button(
        text=BACK_BUTTON,
        callback_data=f"view_devices:{subscription_uuid}:0"
    )
    
    builder.adjust(1, 1)
    return builder.as_markup()

def get_cancel_transfer_kb(subscription_uuid: str) -> InlineKeyboardMarkup:
    """Клавиатура отмены передачи"""
    builder = InlineKeyboardBuilder()
    builder.button(
        text=CANCEL_BUTTON,
        callback_data=f"cancel_transfer:{subscription_uuid}"
    )
    return builder.as_markup()

def get_back_to_devices_kb(subscription_uuid: str) -> InlineKeyboardMarkup:
    """Кнопка возврата к списку устройств"""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="⬅️ К устройствам",
        callback_data=f"view_devices:{subscription_uuid}:0"
    )
    return builder.as_markup()

def get_back_to_manage_kb(subscription_uuid: str) -> InlineKeyboardMarkup:
    """Кнопка возврата к управлению подпиской"""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="⬅️ К управлению",
        callback_data=f"manage_subscription:{subscription_uuid}"
    )
    return builder.as_markup()

def get_no_subscriptions_kb() -> InlineKeyboardMarkup:
    """Клавиатура при отсутствии подписок"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🛒 Купить подписку", callback_data="buy_subscription")
    builder.button(text=BACK_BUTTON, callback_data="menu:main")
    builder.adjust(1, 1)
    return builder.as_markup()