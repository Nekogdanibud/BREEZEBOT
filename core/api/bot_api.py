from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from core.database.database import async_session
from core.database.crud import (
    get_user_by_telegram_id,
    get_purchased_subscriptions,
    get_purchased_subscription_by_uuid
)
from core.api.remnawave_client import remnawave_service
import os
import logging
from dotenv import load_dotenv
# Настройка логгера
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

router = APIRouter()

# Аутентификация
API_KEY = os.getenv("API_KEY")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def validate_api_key(api_key: str = Depends(api_key_header)):
    if api_key != API_KEY:
        logger.warning(f"Invalid API Key attempt: {api_key}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
            headers={"WWW-Authenticate": "API-Key"}
        )
    return True

# Dependency для БД
async def get_db():
    async with async_session() as session:
        yield session

@router.get("/health")
async def health_check():
    return {"status": "ok"}

@router.get("/users/{telegram_id}")
async def get_user(
    telegram_id: int,
    _: bool = Depends(validate_api_key),
    db=Depends(get_db)
):
    try:
        user = await get_user_by_telegram_id(db, telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "telegram_id": user.telegram_id,
            "username": user.username,
            "role": user.role,
            "balance": float(user.balance) if user.balance else 0.0
        }
    except Exception as e:
        logger.error(f"Error fetching user {telegram_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/users/{telegram_id}/subscriptions")
async def get_user_subscriptions(
    telegram_id: int,
    _: bool = Depends(validate_api_key),
    db=Depends(get_db)
):
    try:
        # Локальные подписки из БД
        local_subs = await get_purchased_subscriptions(db, telegram_id)
        
        # Данные из Remnawave API
        remote_subs = await remnawave_service.get_user_by_telegram_id(telegram_id)
        
        return {
            "telegram_id": telegram_id,
            "local_subscriptions": [
                {
                    "sub_uuid": sub.sub_uuid,
                    "username": sub.username,
                    "expired_at": sub.expired_at.isoformat(),
                    "renewal_price": float(sub.renewal_price) if sub.renewal_price else None
                } for sub in local_subs
            ],
            "remote_subscriptions": remote_subs
        }
    except Exception as e:
        logger.error(f"Error fetching subscriptions for {telegram_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/subscriptions/{sub_uuid}/devices")
async def get_subscription_devices(
    sub_uuid: str,
    _: bool = Depends(validate_api_key),
    db=Depends(get_db)
):
    try:
        sub = await get_purchased_subscription_by_uuid(db, sub_uuid)
        if not sub:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        devices = await remnawave_service.get_connected_devices(sub_uuid)
        return {
            "sub_uuid": sub_uuid,
            "owner_telegram_id": sub.telegram_id,
            "devices": devices
        }
    except Exception as e:
        logger.error(f"Error fetching devices for {sub_uuid}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
