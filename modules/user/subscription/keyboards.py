from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import types
from typing import List, Dict, Any
from .texts import (
    BUY_SUBSCRIPTION_TEXT, BUY_ANOTHER_TEXT, 
    BACK_TO_LIST_TEXT, REFRESH_TEXT,
    SUBSCRIPTION_DETAIL_CALLBACK, BUY_SUBSCRIPTION_CALLBACK,
    SUBSCRIPTIONS_CALLBACK, SUBSCRIPTION_LINK_TEXT,
    MANAGE_SUBSCRIPTION_TEXT, MANAGE_SUBSCRIPTION_CALLBACK,
    MAIN_MENU_TEXT, MAIN_MENU_CALLBACK
)

def _create_subscription_button(sub_info: Dict[str, Any]) -> types.InlineKeyboardButton:
    """
    Создает кнопку для подписки.
    
    Args:
        sub_info: Данные подписки.
    
    Returns:
        InlineKeyboardButton: Кнопка для подписки.
    """
    button_text = sub_info.get("username") or f"Подписка {sub_info.get('uuid', 'N/A')[:8]}"
    callback_data = f"{SUBSCRIPTION_DETAIL_CALLBACK}{sub_info.get('uuid', '')}"
    return types.InlineKeyboardButton(text=button_text, callback_data=callback_data)

def get_subscriptions_list_kb(subscriptions_info: List[Dict[str, Any]]) -> types.InlineKeyboardMarkup:
    """
    Создает клавиатуру для списка подписок.
    
    Args:
        subscriptions_info: Список данных подписок.
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками.
    """
    builder = InlineKeyboardBuilder()
    
    for sub_info in subscriptions_info:
        builder.add(_create_subscription_button(sub_info))
    
    builder.adjust(1)
    builder.row(
        types.InlineKeyboardButton(
            text=BUY_ANOTHER_TEXT,
            callback_data=BUY_SUBSCRIPTION_CALLBACK
        ),
        types.InlineKeyboardButton(
            text=MAIN_MENU_TEXT,
            callback_data=MAIN_MENU_CALLBACK
        )
    )
    
    return builder.as_markup()

def get_no_subscriptions_kb() -> types.InlineKeyboardMarkup:
    """Создает клавиатуру для случая отсутствия подписок."""
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text=BUY_SUBSCRIPTION_TEXT,
            callback_data=BUY_SUBSCRIPTION_CALLBACK
        ),
        types.InlineKeyboardButton(
            text=MAIN_MENU_TEXT,
            callback_data=MAIN_MENU_CALLBACK
        )
    )
    return builder.as_markup()

def get_subscription_detail_kb(subscription_uuid: str, subscription_url: str) -> types.InlineKeyboardMarkup:
    """
    Создает клавиатуру для деталей подписки.
    
    Args:
        subscription_uuid: UUID подписки.
        subscription_url: URL подписки.
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками.
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text=SUBSCRIPTION_LINK_TEXT,
            url=subscription_url
        )
    )
    builder.row(
        types.InlineKeyboardButton(
            text=MANAGE_SUBSCRIPTION_TEXT,
            callback_data=f"{MANAGE_SUBSCRIPTION_CALLBACK}{subscription_uuid}"
        )
    )
    builder.row(
        types.InlineKeyboardButton(
            text=BACK_TO_LIST_TEXT,
            callback_data=SUBSCRIPTIONS_CALLBACK
        )
    )
    return builder.as_markup()