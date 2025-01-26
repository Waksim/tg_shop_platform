# django_app/shop/utils.py

import os
import django
import logging
import asyncio
from dotenv import load_dotenv
from aiogram import Bot
from django.core.exceptions import ImproperlyConfigured

# Настройка Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

# Загрузка переменных окружения из .env
load_dotenv()

# Настройка логирования для данного модуля
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Создание обработчика для вывода логов в консоль
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Создание форматтера и добавление его к обработчику
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
console_handler.setFormatter(formatter)

# Добавление обработчика к логгеру
if not logger.handlers:
    logger.addHandler(console_handler)

# Получение токена бота из переменных окружения
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def send_mass_message_to_users(user_ids, message_text):
    """
    Отправляет сообщения указанным пользователям Telegram.

    :param user_ids: Список ID пользователей Telegram.
    :param message_text: Текст сообщения для отправки.
    """
    logger.info('Начало процесса массовой рассылки сообщений.')

    # Проверка наличия токена бота
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не найден в окружении.")
        raise ImproperlyConfigured("TELEGRAM_BOT_TOKEN не найден в окружении.")

    # Инициализация экземпляра бота
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    logger.debug('Инициализирован экземпляр бота Aiogram.')

    async def _send_messages():
        """
        Асинхронная функция для отправки сообщений пользователям.
        """
        for uid in user_ids:
            try:
                await bot.send_message(chat_id=uid, text=message_text)
                logger.info(f'Сообщение успешно отправлено пользователю с ID {uid}.')
            except Exception as e:
                logger.error(f"Ошибка отправки сообщения пользователю с ID {uid}: {e}", exc_info=True)

    try:
        # Запуск асинхронной функции отправки сообщений
        asyncio.run(_send_messages())
        logger.info('Массовая рассылка сообщений завершена успешно.')
    except Exception as e:
        logger.error(f"Не удалось завершить массовую рассылку сообщений: {e}", exc_info=True)
    finally:
        # Закрытие сессии бота
        asyncio.run(bot.session.close())
        logger.debug('Сессия бота Aiogram закрыта.')
