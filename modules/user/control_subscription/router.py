from aiogram import Router, F  
from aiogram.types import CallbackQuery, Message  
from core.filters import IsNotBanned  
from .handlers import (  
    manage_subscription_menu,  
    renew_subscription,  
    view_devices,  
    show_device_details,  
    remove_device_callback,  
    initiate_transfer_subscription,  
    process_transfer_contact,  
    cancel_transfer,  
    TransferSubscriptionStates  
)  

router = Router()  

# Обработчики управления подпиской  
router.callback_query.register(  
    manage_subscription_menu,  
    F.data.startswith("manage_subscription:"),  
    IsNotBanned  
)  

router.callback_query.register(  
    renew_subscription,  
    F.data.startswith("renew_subscription:"),  
    IsNotBanned  
)  

# Обработчики управления устройствами  
router.callback_query.register(  
    view_devices,  
    F.data.startswith("view_devices:"),  
    IsNotBanned  
)  

router.callback_query.register(  
    show_device_details,  
    F.data.startswith("device_details:"),  
    IsNotBanned  
)  

router.callback_query.register(  
    remove_device_callback,  
    F.data.startswith("remove_device:"),  
    IsNotBanned  
)  

# Обработчики передачи подписки  
router.callback_query.register(  
    initiate_transfer_subscription,  
    F.data.startswith("transfer_subscription:"),  
    IsNotBanned  
)  

router.callback_query.register(  
    cancel_transfer,  
    F.data.startswith("cancel_transfer:"),  
    IsNotBanned  
)  

# Обработчик контакта для передачи  
router.message.register(  
    process_transfer_contact,  
    TransferSubscriptionStates.waiting_for_contact,  
    IsNotBanned  
)
