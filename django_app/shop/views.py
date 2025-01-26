# django_app/shop/views.py

import logging
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseForbidden
from django.contrib.auth.decorators import user_passes_test
from .models import Order

# Настройка логирования для данного модуля
logger = logging.getLogger(__name__)


def index(request):
    """
    Представление для главной страницы магазина.

    Возвращает простое сообщение как заглушку.

    :param request: HTTP-запрос.
    :return: HTTP-ответ с текстом.
    """
    logger.info(f'Запрос к главной странице от пользователя {request.user}')
    return HttpResponse("Главная страница магазина (заглушка)")


@user_passes_test(lambda u: u.is_superuser, login_url='/', redirect_field_name=None)
def order_list(request):
    """
    Представление для отображения списка всех заказов.

    Доступно только суперпользователям.

    :param request: HTTP-запрос.
    :return: Отрендеренный шаблон с списком заказов или сообщение о запрете доступа.
    """
    logger.info(f'Суперпользователь {request.user} запросил список заказов.')
    orders = Order.objects.all()
    return render(request, 'shop/order_list.html', {'orders': orders})


def payment_callback(request):
    """
    Обработчик обратного вызова платежа от платёжного шлюза Yookassa.

    Логирует полученные данные и возвращает статус 200 OK.

    :param request: HTTP-запрос с данными платежа.
    :return: HTTP-ответ с текстом "OK".
    """
    logger.info(f'Получен callback платежа: {request.POST}')

    # Здесь можно добавить логику обработки данных платежа, например, обновление статуса заказа

    return HttpResponse("OK")
