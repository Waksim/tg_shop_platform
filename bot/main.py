# bot/main.py

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from dotenv import load_dotenv

import django

# Установка переменной окружения для Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_app.config.settings")
django.setup()

# Импорты обработчиков
from bot.handlers.start import router as start_router
from bot.handlers.catalog import router as catalog_router
from bot.handlers.product import router as product_router
from bot.handlers.cart import router as cart_router
from bot.handlers.faq import router as faq_router
from bot.handlers.payments import router as payments_router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("logs/bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def set_bot_commands(bot: Bot):
    """
    Устанавливает доступные команды для бота.

    :param bot: Экземпляр бота Aiogram
    """
    commands = [
        BotCommand(command="/start", description="Запустить бота"),
        BotCommand(command="/catalog", description="Открыть каталог"),
        BotCommand(command="/cart", description="Корзина"),
        BotCommand(command="/faq", description="Частые вопросы")
    ]
    await bot.set_my_commands(commands)
    logger.info("Команды бота установлены.")


async def on_startup(bot: Bot):
    """
    Действия, выполняемые при запуске бота.

    :param bot: Экземпляр бота Aiogram
    """
    await set_bot_commands(bot)
    logger.info("Бот успешно запущен и готов к работе.")


def main():
    """
    Основная функция для запуска бота.
    """
    load_dotenv()
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not bot_token:
        logger.critical("TELEGRAM_BOT_TOKEN не найден в .env")
        raise ValueError("TELEGRAM_BOT_TOKEN не найден в .env")

    bot = Bot(
        token=bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    dp.startup.register(on_startup)

    # Регистрация роутеров
    dp.include_router(start_router)
    dp.include_router(catalog_router)
    dp.include_router(product_router)
    dp.include_router(cart_router)
    dp.include_router(faq_router)
    dp.include_router(payments_router)
    logger.info("Все роутеры успешно зарегистрированы.")

    try:
        logger.info("Запуск polling для бота.")
        asyncio.run(dp.start_polling(bot))
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен вручную.")
    except Exception as e:
        logger.exception(f"Неожиданная ошибка при запуске бота: {e}")
    finally:
        asyncio.run(bot.session.close())
        logger.info("Сессия бота закрыта.")


if __name__ == "__main__":
    main()
