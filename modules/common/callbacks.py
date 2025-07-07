# modules/common/callbacks.py
from aiogram.filters.callback_data import CallbackData

class ProfileActions(CallbackData, prefix="profile"):
    action: str  # refresh, manage_vpn, etc.
