# django_app/shop/apps.py

import logging
from django.apps import AppConfig


class ShopConfig(AppConfig):
    """
    Конфигурация приложения 'Магазин'.

    Настраивает параметры приложения и инициализирует логирование при запуске.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'django_app.shop'
    verbose_name = "Магазин"

    def ready(self):
        """
        Метод, вызываемый при готовности приложения.

        Здесь настраивается логирование, которое сообщает об успешной инициализации приложения.
        """
        # Создание логгера для данного модуля
        logger = logging.getLogger(__name__)

        # Логирование сообщения об инициализации приложения
        logger.info(f'Приложение "{self.verbose_name}" успешно инициализировано.')
