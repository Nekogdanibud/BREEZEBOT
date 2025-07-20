from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from .texts import (
    BUY_SUBSCRIPTION_TEXT, BUY_ANOTHER_TEXT, 
    BACK_TO_LIST_TEXT, REFRESH_TEXT,
    SUBSCRIPTION_DETAIL_CALLBACK, BUY_SUBSCRIPTION_CALLBACK,
    SUBSCRIPTIONS_CALLBACK, SUBSCRIPTION_LINK_TEXT,
    MANAGE_SUBSCRIPTION_TEXT, MANAGE_SUBSCRIPTION_CALLBACK,
    MAIN_MENU_TEXT, MAIN_MENU_CALLBACK
)

def get_subscriptions_list_kb(subscriptions: list) -> InlineKeyboardBuilder:
    """Клавиатура списка подписок (только локальные данные)"""
    builder = InlineKeyboardBuilder()
    
    # Кнопки для каждой подписки
    for sub in subscriptions:
        builder.button(
            text=sub["username"],
            callback_data=f"{SUBSCRIPTION_DETAIL_CALLBACK}{sub['uuid']}"
        )
    
    builder.adjust(1)
    builder.row(
        InlineKeyboardButton(
            text=BUY_ANOTHER_TEXT,
            callback_data=BUY_SUBSCRIPTION_CALLBACK
        ),
        InlineKeyboardButton(
            text=MAIN_MENU_TEXT,
            callback_data=MAIN_MENU_CALLBACK
        )
    )
    
    return builder.as_markup()

# Остальные функции без изменений
def get_no_subscriptions_kb() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=BUY_SUBSCRIPTION_TEXT,
            callback_data=BUY_SUBSCRIPTION_CALLBACK
        ),
        InlineKeyboardButton(
            text=MAIN_MENU_TEXT,
            callback_data=MAIN_MENU_CALLBACK
        )
    )
    return builder.as_markup()

def get_subscription_detail_kb(subscription_uuid: str, subscription_url: str) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=SUBSCRIPTION_LINK_TEXT,
            url=subscription_url
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=MANAGE_SUBSCRIPTION_TEXT,
            callback_data=f"{MANAGE_SUBSCRIPTION_CALLBACK}{subscription_uuid}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=BACK_TO_LIST_TEXT,
            callback_data=SUBSCRIPTIONS_CALLBACK
        )
    )
    return builder.as_markup()
