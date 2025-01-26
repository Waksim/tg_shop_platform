# django_app/shop/admin.py

import logging
from django.contrib import admin
from .models import Category, SubCategory, Product, FAQ, Cart, CartItem, Order, TelegramUser

# Настройка логирования для данного модуля
logger = logging.getLogger(__name__)
logger.info('Инициализация admin.py для приложения shop.')

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """
    Админ-интерфейс для модели Category.
    Позволяет просматривать, искать и фильтровать категории товаров.
    """
    list_display = ('id', 'name', 'created_at')  # Поля, отображаемые в списке
    search_fields = ('name',)  # Поля для поиска

    def save_model(self, request, obj, form, change):
        """
        Переопределение метода сохранения модели для логирования.
        """
        if change:
            logger.info(f'Категория изменена: {obj}')
        else:
            logger.info(f'Создана новая категория: {obj}')
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        """
        Переопределение метода удаления модели для логирования.
        """
        logger.info(f'Категория удалена: {obj}')
        super().delete_model(request, obj)

@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    """
    Админ-интерфейс для модели SubCategory.
    Позволяет просматривать, искать и фильтровать подкатегории товаров.
    """
    list_display = ('id', 'name', 'category')  # Поля, отображаемые в списке
    search_fields = ('name',)  # Поля для поиска
    list_filter = ('category',)  # Поля для фильтрации

    def save_model(self, request, obj, form, change):
        """
        Переопределение метода сохранения модели для логирования.
        """
        if change:
            logger.info(f'Подкатегория изменена: {obj}')
        else:
            logger.info(f'Создана новая подкатегория: {obj}')
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        """
        Переопределение метода удаления модели для логирования.
        """
        logger.info(f'Подкатегория удалена: {obj}')
        super().delete_model(request, obj)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Админ-интерфейс для модели Product.
    Позволяет просматривать, искать и фильтровать товары.
    """
    list_display = ('id', 'name', 'subcategory', 'price', 'created_at')  # Поля, отображаемые в списке
    search_fields = ('name', 'description')  # Поля для поиска

    def save_model(self, request, obj, form, change):
        """
        Переопределение метода сохранения модели для логирования.
        """
        if change:
            logger.info(f'Товар изменён: {obj}')
        else:
            logger.info(f'Создан новый товар: {obj}')
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        """
        Переопределение метода удаления модели для логирования.
        """
        logger.info(f'Товар удалён: {obj}')
        super().delete_model(request, obj)

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    """
    Админ-интерфейс для модели FAQ.
    Позволяет просматривать и управлять часто задаваемыми вопросами.
    """
    list_display = ('id', 'question')  # Поля, отображаемые в списке

    def save_model(self, request, obj, form, change):
        """
        Переопределение метода сохранения модели для логирования.
        """
        if change:
            logger.info(f'FAQ изменён: {obj}')
        else:
            logger.info(f'Создан новый FAQ: {obj}')
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        """
        Переопределение метода удаления модели для логирования.
        """
        logger.info(f'FAQ удалён: {obj}')
        super().delete_model(request, obj)

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    """
    Админ-интерфейс для модели Cart.
    Позволяет просматривать и управлять корзинами пользователей.
    """
    list_display = ('id', 'user', 'created_at')  # Поля, отображаемые в списке

    def save_model(self, request, obj, form, change):
        """
        Переопределение метода сохранения модели для логирования.
        """
        if change:
            logger.info(f'Корзина изменена: {obj}')
        else:
            logger.info(f'Создана новая корзина: {obj}')
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        """
        Переопределение метода удаления модели для логирования.
        """
        logger.info(f'Корзина удалена: {obj}')
        super().delete_model(request, obj)

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    """
    Админ-интерфейс для модели CartItem.
    Позволяет просматривать и управлять товарами в корзинах.
    """
    list_display = ('id', 'cart', 'product', 'quantity')  # Поля, отображаемые в списке

    def save_model(self, request, obj, form, change):
        """
        Переопределение метода сохранения модели для логирования.
        """
        if change:
            logger.info(f'Товар в корзине изменён: {obj}')
        else:
            logger.info(f'Добавлен новый товар в корзину: {obj}')
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        """
        Переопределение метода удаления модели для логирования.
        """
        logger.info(f'Товар в корзине удалён: {obj}')
        super().delete_model(request, obj)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    Админ-интерфейс для модели Order.
    Позволяет просматривать и управлять заказами пользователей.
    """
    list_display = ('id', 'user', 'created_at', 'is_paid')  # Поля, отображаемые в списке
    search_fields = ('user__username',)  # Поля для поиска

    def save_model(self, request, obj, form, change):
        """
        Переопределение метода сохранения модели для логирования.
        """
        if change:
            logger.info(f'Заказ изменён: {obj}')
        else:
            logger.info(f'Создан новый заказ: {obj}')
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        """
        Переопределение метода удаления модели для логирования.
        """
        logger.info(f'Заказ удалён: {obj}')
        super().delete_model(request, obj)

@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    """
    Админ-интерфейс для модели TelegramUser.
    Позволяет просматривать и управлять пользователями Telegram.
    """
    list_display = ('telegram_id', 'first_name', 'username', 'created_at')  # Поля, отображаемые в списке
    search_fields = ('telegram_id', 'username')  # Поля для поиска
    readonly_fields = ('created_at', 'last_activity')  # Поля только для чтения

    def save_model(self, request, obj, form, change):
        """
        Переопределение метода сохранения модели для логирования.
        """
        if change:
            logger.info(f'Пользователь Telegram изменён: {obj}')
        else:
            logger.info(f'Создан новый пользователь Telegram: {obj}')
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        """
        Переопределение метода удаления модели для логирования.
        """
        logger.info(f'Пользователь Telegram удалён: {obj}')
        super().delete_model(request, obj)
