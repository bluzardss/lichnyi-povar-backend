import ssl
import socket
from aiohttp import TCPConnector
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from src.бот.handlers.start import router as start_router
from src.бот.handlers.text import router as text_router
from src.бот.handlers.photo import router as photo_router
from src.бот.middleware.auth import AuthMiddleware
from src.config import config
import logging

logger = logging.getLogger(__name__)

if not config.TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не установлен в .env файле")

# DEBUG: print full token
print(f"DEBUG: Using token: {config.TELEGRAM_BOT_TOKEN}")

# Use SOCKS5 proxy via aiohttp-socks (Xray runs at 127.0.0.1:10808)
from aiohttp_socks import ProxyConnector

# Custom session that uses SOCKS5 proxy
class ProxySession(AiohttpSession):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Override connector type and init to use SOCKS5 proxy
        self._connector_type = ProxyConnector
        self._connector_init = {
            "host": "127.0.0.1",
            "port": 10808,
            "ssl": False,  # Let proxy handle TLS
            "limit": 100,
            "ttl_dns_cache": 3600,
        }
        print(f"DEBUG: ProxySession._connector_init = {self._connector_init}")

session = ProxySession()

print(f"DEBUG: Created SOCKS5 proxy session")

bot = Bot(
    token=config.TELEGRAM_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    session=session
)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Регистрация middleware
dp.message.middleware(AuthMiddleware())
dp.callback_query.middleware(AuthMiddleware())

# Регистрация роутеров
dp.include_router(start_router)
dp.include_router(text_router)
dp.include_router(photo_router)

logger.info("Бот успешно инициализирован")

async def create_bot() -> Dispatcher:
    """Инициализирует бота и диспетчер, регистрает роутеры и middleware."""
    return dp
