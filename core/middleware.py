from typing import Callable, Dict, Awaitable, Any, Union
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery, Update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from core.database.crud import get_user_by_telegram_id, create_user
from core.database.model import User
import logging

logger = logging.getLogger(__name__)

class RoleMiddleware(BaseMiddleware):
    def __init__(self, session_pool: async_sessionmaker[AsyncSession]):
        super().__init__()
        self.session_pool = session_pool

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        logger.debug(f"RoleMiddleware processing event: {type(event)}")
        data.update({"user": None, "role": "USER"})

        # Extract actual event from Update if needed
        actual_event = event
        if isinstance(event, Update):
            actual_event = event.message or event.callback_query
            if not actual_event:
                logger.debug("Unsupported Update event type")
                return await handler(event, data)

        # Check if we have a supported event with from_user
        if not isinstance(actual_event, (Message, CallbackQuery)) or not actual_event.from_user:
            logger.debug("Event doesn't have from_user, skipping user processing")
            return await handler(event, data)

        user = actual_event.from_user
        telegram_id = user.id
        logger.debug(f"Processing user with telegram_id: {telegram_id}")

        try:
            async with self.session_pool() as session:
                async with session.begin():
                    # Try to get existing user
                    db_user = await get_user_by_telegram_id(session, telegram_id)
                    
                    # Create new user if doesn't exist
                    if not db_user:
                        logger.debug(f"Creating new user for telegram_id: {telegram_id}")
                        db_user = await create_user(
                            session=session,
                            telegram_id=telegram_id,
                            username=user.username
                        )
                        
                        if not db_user:
                            logger.error(f"Failed to create user for telegram_id: {telegram_id}")
                            return await handler(event, data)

                    # Update data for handler
                    data.update({
                        "user": db_user,
                        "role": db_user.role.upper() if db_user else "USER"
                    })
                    logger.debug(f"User data updated: {data['role']}")

        except Exception as e:
            logger.error(f"Error processing user {telegram_id}: {str(e)}", exc_info=True)
            # Continue with default data (user=None, role=USER)
        
        return await handler(event, data)