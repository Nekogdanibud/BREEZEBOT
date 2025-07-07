from aiogram import Router, F
from .handlers import show_subscriptions, show_subscription_detail
from .texts import SUBSCRIPTIONS_CALLBACK, SUBSCRIPTION_DETAIL_CALLBACK

# Создаем роутер модуля подписок
subscriptions_router = Router()

# Регистрируем обработчики
subscriptions_router.callback_query.register(
    show_subscriptions,
    F.data == SUBSCRIPTIONS_CALLBACK
)

subscriptions_router.callback_query.register(
    show_subscription_detail,
    F.data.startswith(SUBSCRIPTION_DETAIL_CALLBACK)
)
