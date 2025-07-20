import asyncio
import logging
import os
import signal
from dotenv import load_dotenv
from fastapi import FastAPI
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from contextlib import asynccontextmanager

# Импорт компонентов
from core.api.bot_api import router as api_router
from core.middleware import RoleMiddleware
from core.database.model import Base
from core.database.database import engine

load_dotenv()

# Конфигурация
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_PORT = int(os.getenv("API_PORT", 8899))
SSL_CERT_PATH = os.getenv("SSL_CERT_PATH")

# Настройка логгера
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class Application:
    def __init__(self):
        self.bot = None
        self.dp = None
        self.server = None
        self._shutdown = False

    async def startup(self):
        """Инициализация приложения"""
        self.bot = Bot(token=BOT_TOKEN)
        self.dp = Dispatcher(storage=MemoryStorage())
        
        session_pool = async_sessionmaker(
            bind=engine,
            expire_on_commit=False,
            class_=AsyncSession
        )

        self.dp.update.outer_middleware(RoleMiddleware(session_pool=session_pool))

        from modules.common.router import main_menu_router
        self.dp.include_router(main_menu_router)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def run_bot(self):
        """Запуск бота с обработкой остановки"""
        try:
            logger.info("Starting Telegram bot polling...")
            await self.dp.start_polling(self.bot)
        except asyncio.CancelledError:
            logger.info("Bot polling cancelled")
            await self.dp.stop_polling()
        except Exception as e:
            logger.error(f"Bot error: {str(e)}")
        finally:
            logger.info("Bot fully stopped")

    async def shutdown(self):
        """Корректное завершение работы"""
        if self._shutdown:
            return
        self._shutdown = True
        
        logger.info("Starting graceful shutdown...")
        
        # 1. Останавливаем сервер
        if self.server:
            self.server.should_exit = True
            logger.info("Uvicorn server shutdown initiated")
        
        # 2. Останавливаем бота
        if hasattr(self.dp, '_polling'):
            await self.dp.stop_polling()
            logger.info("Bot polling stopped")
        
        # 3. Закрываем соединения
        if self.bot:
            await self.bot.session.close()
            logger.info("Bot session closed")
        
        if engine:
            await engine.dispose()
            logger.info("Database connections closed")

def create_app():
    """Фабрика приложения"""
    app = FastAPI()
    app.state.application = Application()
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await app.state.application.startup()
        
        # Запускаем бота в фоне
        bot_task = asyncio.create_task(app.state.application.run_bot())
        
        yield
        
        # Завершаем работу
        bot_task.cancel()
        try:
            await bot_task
        except asyncio.CancelledError:
            pass
        
        await app.state.application.shutdown()

    app.router.lifespan_context = lifespan
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.include_router(api_router, prefix="/api")
    
    @app.get("/health")
    async def health_check():
        return {"status": "ok", "services": ["bot", "api"]}
    
    return app

async def run_server():
    """Запуск сервера"""
    app = create_app()
    
    # Настройка SSL
    ssl_params = {}
    if SSL_CERT_PATH:
        key = os.path.join(SSL_CERT_PATH, "privkey.pem")
        cert = os.path.join(SSL_CERT_PATH, "fullchain.pem")
        if os.path.exists(key) and os.path.exists(cert):
            ssl_params = {
                "ssl_keyfile": key,
                "ssl_certfile": cert
            }
            logger.info("SSL certificates loaded")
        else:
            logger.warning(f"SSL files not found at {SSL_CERT_PATH}, using HTTP")
    else:
        logger.warning("SSL_CERT_PATH not set, using HTTP")

    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=API_PORT,
        reload=True,
        **ssl_params
    )
    
    server = uvicorn.Server(config)
    app.state.application.server = server
    
    # Обработка сигналов
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(app.state.application.shutdown()))
    
    await server.serve()

if __name__ == "__main__":
    # Очистка порта перед запуском
    os.system(f"fuser -k {API_PORT}/tcp >/dev/null 2>&1")
    
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        logger.info("Application stopped by keyboard interrupt")
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
    finally:
        logger.info("Application fully stopped")
