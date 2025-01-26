# django_app/config/wsgi.py

import os
import logging
from django.core.wsgi import get_wsgi_application

# Создание логгера для данного модуля
logger = logging.getLogger(__name__)

# Установка переменной окружения для настроек Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_app.config.settings')
logger.info('Переменная окружения DJANGO_SETTINGS_MODULE установлена.')

try:
    # Получение WSGI-приложения Django
    application = get_wsgi_application()
    logger.info('WSGI-приложение Django успешно инициализировано.')
except Exception as e:
    logger.error('Ошибка при инициализации WSGI-приложения Django:', exc_info=True)
    raise
