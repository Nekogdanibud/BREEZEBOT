# Основные тексты
NO_SUBSCRIPTIONS_TEXT = (
    "📭 У вас пока нет активных подписок.\n\n"
    "Приобретите подписку, чтобы получить доступ к нашим услугам! 🛒"
)

SUBSCRIPTIONS_LIST_TEXT = "📋 Ваши активные подписки:"

SUBSCRIPTION_DETAIL_TEMPLATE = (
    "{status_emoji} <b>{username}</b> ✨\n"
    "📈 Статус: {status}\n"
    "🌐 Трафик: {used_traffic:.2f} GB / {data_limit:.2f} GB\n"
    "⏳ Срок действия: {expire}\n"
    "📍 Последнее подключение: {last_connected}\n"
    "💰 Цена покупки: {purchase_price:.2f} ₽\n"
    "🔄 Цена продления: {renewal_price:.2f} ₽\n"
)

SUBSCRIPTION_ERROR_TEXT = "⚠️ Ошибка при получении данных подписки:\n{error}"

# Тексты кнопок
BUY_SUBSCRIPTION_TEXT = "🛒 Купить"
BUY_ANOTHER_TEXT = "🛒 Купить"
BACK_TO_LIST_TEXT = "⬅️ Назад к списку"
REFRESH_TEXT = "🔄 Обновить"
MANAGE_SUBSCRIPTION_TEXT = "⚙️ Управление подпиской"
SUBSCRIPTION_LINK_TEXT = "🔗 Ссылка для подключения"
MAIN_MENU_TEXT = "🏠 Меню"

# Callback data
SUBSCRIPTIONS_CALLBACK = "subscriptions"
SUBSCRIPTION_DETAIL_CALLBACK = "subscription_detail:"
BUY_SUBSCRIPTION_CALLBACK = "buy_subscription"
MANAGE_SUBSCRIPTION_CALLBACK = "manage_subscription:"
MAIN_MENU_CALLBACK = "menu:main"