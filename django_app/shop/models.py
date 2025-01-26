# django_app/shop/models.py

import logging
from django.conf import settings
from django.db import models
from yookassa import Payment, Configuration

# Настройка логирования для данного модуля
logger = logging.getLogger(__name__)


class TelegramUser(models.Model):
    """
    Модель пользователя Telegram.

    Хранит информацию о пользователях, взаимодействующих с ботом.
    """
    telegram_id = models.BigIntegerField(unique=True, verbose_name="ID в Telegram")
    first_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Имя")
    last_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Фамилия")
    username = models.CharField(max_length=255, blank=True, null=True, verbose_name="Юзернейм")
    language_code = models.CharField(max_length=10, blank=True, null=True, verbose_name="Язык")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата регистрации")
    last_activity = models.DateTimeField(auto_now=True, verbose_name="Последняя активность")

    def __str__(self):
        return f"{self.first_name} (@{self.username})" if self.username else f"User {self.telegram_id}"


class Category(models.Model):
    """
    Модель категории товаров.

    Категории используются для организации товаров в каталоге.
    """
    name = models.CharField(max_length=100, unique=True, verbose_name="Категория")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    def __str__(self):
        return self.name


class SubCategory(models.Model):
    """
    Модель подкатегории товаров.

    Подкатегории позволяют более детально классифицировать товары внутри категории.
    """
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories',
                                 verbose_name="Категория")
    name = models.CharField(max_length=100, verbose_name="Подкатегория")

    def __str__(self):
        return f"{self.category.name} / {self.name}"


class Product(models.Model):
    """
    Модель товара.

    Представляет отдельный товар в каталоге с описанием, ценой и изображением.
    """
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, related_name='products',
                                    verbose_name="Подкатегория")
    name = models.CharField(max_length=255, verbose_name="Название товара")
    description = models.TextField(verbose_name="Описание товара", blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    photo = models.ImageField(
        upload_to='product_photos/',
        blank=True,
        null=True,
        default='product_photos/placeholder.png',  # Путь к фото-заглушке
        verbose_name="Фото товара"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    def __str__(self):
        return f"{self.name} ({self.subcategory.name})"


class FAQ(models.Model):
    """
    Модель часто задаваемых вопросов.

    Хранит вопросы и ответы для раздела FAQ бота.
    """
    question = models.CharField(max_length=255, verbose_name="Вопрос")
    answer = models.TextField(verbose_name="Ответ")

    def __str__(self):
        return self.question


class Cart(models.Model):
    """
    Модель корзины пользователя.

    Содержит товары, выбранные пользователем для покупки.
    """
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name='carts', verbose_name="Пользователь")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    def __str__(self):
        return f"Корзина пользователя {self.user.username or self.user.telegram_id}"


class CartItem(models.Model):
    """
    Модель товара в корзине.

    Представляет отдельный товар, добавленный в корзину, с указанием количества.
    """
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items', verbose_name="Корзина")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Товар")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Количество")

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"


class Order(models.Model):
    """
    Модель заказа.

    Представляет оформленный заказ пользователя с информацией о доставке и оплате.
    """
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name='orders', verbose_name="Пользователь")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    address = models.CharField(max_length=255, verbose_name="Адрес доставки")
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Итого")
    is_paid = models.BooleanField(default=False, verbose_name="Оплачен")
    payment_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="ID платежа")

    def __str__(self):
        return f"Заказ №{self.id} от {self.user.username or self.user.telegram_id}"

    def create_payment(self):
        """
        Создаёт платеж через Yookassa и сохраняет ID платежа.

        Возвращает объект платежа при успешном создании, иначе None.
        """
        try:
            payment = Payment.create({
                "amount": {
                    "value": f"{float(self.total):.2f}",
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": settings.YOOKASSA_RETURN_URL or "https://example.com/payment-callback/"
                },
                "description": f"Заказ №{self.id}",
                "metadata": {
                    "order_id": self.id,
                    "user_id": self.user.id
                }
            })
            self.payment_id = payment.id
            self.is_paid = True
            self.save()
            logger.info(f'Платеж создан для заказа №{self.id} с payment_id={payment.id}')
            return payment
        except Exception as e:
            logger.error(f"Ошибка при создании платежа для заказа №{self.id}: {e}", exc_info=True)
            self.payment_id = None
            self.save()
            return None


class OrderItem(models.Model):
    """
    Модель товара в заказе.

    Представляет отдельный товар, входящий в заказ, с указанием количества.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name="Заказ")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Товар")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Количество")

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
