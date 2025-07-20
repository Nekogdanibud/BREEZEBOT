# Тексты для управления подпиской
MANAGE_SUBSCRIPTION_TEXT = (
    "⚙️ Управление подпиской <b>{username}</b>\n\n"
    "📊 Использовано трафика: {used_traffic:.2f} GB\n"
    "🔔 Статус: {status}\n"
    "💰 Цена продления: {renewal_price:.2f} ₽\n\n"
    "Выберите действие:"
)

NO_SUBSCRIPTION_TEXT = "⚠️ Подписка не найдена"
INSUFFICIENT_BALANCE_TEXT = "⚠️ Недостаточно средств. Требуется: {required:.2f} ₽, баланс: {balance:.2f} ₽"
RENEWAL_PRICE_NOT_SET_TEXT = "⚠️ Цена продления не указана"
RENEW_SUBSCRIPTION_SUCCESS_TEXT = "✅ Подписка продлена до {expiration}. Списано {amount:.2f} ₽"

# Тексты для управления устройствами
NO_DEVICES_TEXT = "⚠️ Устройства не найдены"
DEVICES_LIST_TEXT = "📱 Подключённые устройства для подписки <b>{username}</b>:"
DEVICES_PAGINATION_TEXT = (
    "📱 Подключённые устройства для подписки <b>{username}</b>:\n\n"
    "Страница {current_page}/{total_pages} | Всего устройств: {total_devices}"
)
DEVICE_DETAILS_TEXT = (
    "📱 Информация об устройстве:\n\n"
    "HWID: {hwid}\n"
    "Имя: {name}\n"
    "Обновлено: {updated_at}\n\n"
    "Выберите действие:"
)
LAST_DEVICE_TEXT = "⚠️ Нельзя удалить последнее устройство"
DEVICE_REMOVED_TEXT = "✅ Устройство {hwid} удалено"
DEVICE_REMOVAL_LIMIT_TEXT = "⚠️ Достигнут лимит удаления устройств (4 в месяц). Попробуйте снова через {days_left} дней"

# Тексты для передачи подписки
TRANSFER_COOLDOWN_TEXT = "⚠️ Подписку можно передать через {days_left} дней"
TRANSFER_REQUEST_TEXT = "📱 Отправьте контакт пользователя для передачи подписки:"
INVALID_CONTACT_TEXT = "⚠️ Пожалуйста, отправьте действительный контакт"
SELF_TRANSFER_TEXT = "⚠️ Нельзя передать подписку самому себе"
TRANSFER_SUCCESS_TEXT = (
    "✅ Подписка '{subscription_name}' передана пользователю с ID {contact_id}!\n\n"
    "Следующая передача возможна после {next_transfer_date}"
)
TRANSFER_RECIPIENT_NOTIFICATION_TEXT = (
    "🎉 Вам передана подписка <b>{username}</b>!\n\n"
    "Вы можете управлять ей в разделе 'Мои подписки'.\n"
    "Передать эту подписку можно будет через 14 дней."
)
TRANSFER_CANCELLED_TEXT = "❌ Передача подписки отменена"
TRANSFER_LIMIT_WARNING = (
    "⏳ Эту подписку уже передавали {days_passed} дней назад.\n\n"
    "Согласно правилам, передавать подписку можно "
    "только 1 раз в 14 дней.\n\n"
    "Повторить попытку можно будет через {remaining_days} дней."
)

# Константы
TRANSFER_COOLDOWN_DAYS = 14  # Ограничение 14 дней между передачами
DEVICE_REMOVAL_LIMIT = 4     # Максимум 4 удаления устройств в месяц
PAGINATION_PREV_BUTTON = "⬅️ Назад"
PAGINATION_NEXT_BUTTON = "Вперёд ➡️"
BACK_BUTTON = "🔙 Назад"
