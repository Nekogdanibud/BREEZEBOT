MANAGE_SUBSCRIPTION_TEXT = (
    "⚙️ Управление подпиской <b>{username}</b>\n\n"
    "📊 Использовано трафика: {used_traffic:.2f} GB\n"
    "🔔 Статус: {status}\n"
    "💰 Цена продления: {renewal_price:.2f} ₽\n\n"
    "Выберите действие:"
)
NO_SUBSCRIPTION_TEXT = "⚠️ Подписка не найдена"
INSUFFICIENT_BALANCE_TEXT = (
    "⚠️ Недостаточно средств. Требуется: {required:.2f} ₽, баланс: {balance:.2f} ₽"
)
RENEWAL_PRICE_NOT_SET_TEXT = "⚠️ Цена продления не указана"
RENEW_SUBSCRIPTION_SUCCESS_TEXT = (
    "✅ Подписка продлена до {expiration}. Списано {amount:.2f} ₽"
)
NO_DEVICES_TEXT = "⚠️ Устройства не найдены или их нет"
DEVICES_LIST_TEXT = "📱 Подключённые устройства для подписки <b>{username}</b>:\n\nВыберите устройство для просмотра деталей:"
DEVICE_DETAILS_TEXT = (
    "📱 Информация об устройстве:\n\n"
    "HWID: {hwid}\n"
    "Имя: {name}\n"
    "Обновлено: {updated_at}\n\n"
    "Выберите действие:"
)
LAST_DEVICE_TEXT = "⚠️ Нельзя удалить последнее устройство"
DEVICE_REMOVED_TEXT = "✅ Устройство {hwid} удалено"
TRANSFER_COOLDOWN_TEXT = "⚠️ Подписку можно передать через {days_left} дней"
TRANSFER_REQUEST_TEXT = "📱 Отправьте контакт пользователя для передачи подписки:"
INVALID_CONTACT_TEXT = "⚠️ Пожалуйста, отправьте действительный контакт"
SELF_TRANSFER_TEXT = "⚠️ Нельзя передать подписку самому себе"
TRANSFER_SUCCESS_TEXT = "✅ Подписка передана пользователю с ID {contact_id}"
TRANSFER_RECIPIENT_NOTIFICATION_TEXT = "🎉 Вам передана подписка <b>{username}</b>!"
TRANSFER_CANCELLED_TEXT = "❌ Передача подписки отменена"
DEVICE_REMOVAL_LIMIT_TEXT = "⚠️ Достигнут лимит удаления устройств (4 в месяц). Попробуйте снова через {days_left} дней"