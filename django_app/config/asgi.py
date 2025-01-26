import os
import logging
from django.core.asgi import get_asgi_application

# Настройка базового конфигурации логирования
logging.basicConfig(
    level=logging.INFO,  # Уровень логирования: INFO
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',  # Формат сообщения
    handlers=[
        logging.FileHandler("logs/asgi.log"),  # Запись логов в файл
        logging.StreamHandler()  # Вывод логов в консоль
    ]
)

# Создание логгера для данного модуля
logger = logging.getLogger(__name__)

# Установка переменной окружения для настроек Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
logger.info('Переменная окружения DJANGO_SETTINGS_MODULE установлена.')

try:
    # Получение ASGI-приложения Django
    application = get_asgi_application()
    logger.info('ASGI-приложение Django успешно инициализировано.')
except Exception as e:
    logger.error('Ошибка при инициализации ASGI-приложения Django:', exc_info=True)
    raise
