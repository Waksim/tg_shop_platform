# django_app/shop/tasks.py

import logging
import openpyxl
from django.core.files.storage import default_storage
from .models import Order, CartItem

# Настройка логирования для данного модуля
logger = logging.getLogger(__name__)


def export_orders_to_excel():
    """
    Экспорт всех заказов в Excel-файл.

    Создаёт Excel-файл с информацией о заказах, включая ID заказа, пользователя,
    адрес доставки, статус оплаты и список товаров.

    Возвращает путь к сохранённому Excel-файлу.
    """
    logger.info('Начало экспорта заказов в Excel.')

    try:
        # Создание новой рабочей книги и настройка листа
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = "Заказы"
        logger.debug('Создана новая рабочая книга Excel.')

        # Установка заголовков столбцов
        headers = ["ID заказа", "Пользователь", "Адрес доставки", "Оплачен?", "Товары"]
        sheet.append(headers)
        logger.debug('Установлены заголовки столбцов в Excel.')

        # Инициализация номера строки для заполнения данных
        row_number = 2

        # Получение всех заказов из базы данных
        orders = Order.objects.all()
        logger.info(f'Получено {orders.count()} заказов для экспорта.')

        for order in orders:
            cart_items = []
            # Получение товаров из корзины пользователя, связанной с заказом
            items = CartItem.objects.filter(cart__user=order.user)
            logger.debug(f'Получено {items.count()} товаров для заказа №{order.id}.')

            for ci in items:
                cart_items.append(f"{ci.product.name} x {ci.quantity}")

            # Заполнение строки данными заказа
            sheet.cell(row=row_number, column=1, value=order.id)
            sheet.cell(row=row_number, column=2, value=order.user.username or f"User {order.user.telegram_id}")
            sheet.cell(row=row_number, column=3, value=order.address)
            sheet.cell(row=row_number, column=4, value="Да" if order.is_paid else "Нет")
            sheet.cell(row=row_number, column=5, value=", ".join(cart_items))

            logger.debug(f'Заполнена строка для заказа №{order.id}.')
            row_number += 1

        # Определение имени файла и сохранение рабочей книги
        excel_filename = "orders_export.xlsx"
        workbook_path = default_storage.save(excel_filename, None)
        workbook.save(workbook_path)
        logger.info(f'Экспорт заказов завершён. Файл сохранён по пути: {workbook_path}')

        return workbook_path

    except Exception as e:
        logger.error(f"Ошибка при экспорте заказов в Excel: {e}", exc_info=True)
        return None
