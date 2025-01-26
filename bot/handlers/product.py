# bot/handlers/product.py

import os
from typing import Dict, Optional, Tuple

from .cart import get_cart_total, get_cart_quantity
from .start import get_or_create_user

import django
from asgiref.sync import sync_to_async
from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from aiogram.utils.markdown import hbold

from django_app.shop.models import Cart, CartItem, Product, TelegramUser

# Настройка логирования
import logging

logger = logging.getLogger(__name__)

router = Router()

# Временное хранилище для количества товаров (ключ: (user_id, product_id), значение: quantity)
quantity_storage: Dict[Tuple[int, int], int] = {}


def register_product_handlers(dp):
    """
    Регистрирует маршрутизатор обработчиков продуктов в диспетчере.
    """
    dp.include_router(router)
    logger.info("Обработчики продуктов зарегистрированы в диспетчере.")


# Инициализация Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_app.config.settings")
django.setup()
logger.info("Django успешно инициализирован для обработчиков продуктов.")


# --- Вспомогательные асинхронные функции ---

async def get_cart_items_count(user: TelegramUser) -> int:
    """
    Получение количества товаров в корзине пользователя.
    """
    @sync_to_async(thread_sensitive=True)
    def _get_count():
        count = CartItem.objects.filter(cart__user=user).count()
        logger.debug(f"Количество товаров в корзине пользователя {user.telegram_id}: {count}")
        return count
    return await _get_count()


async def get_product_by_id(product_id: int) -> Product:
    """
    Получение товара по его ID.
    """
    @sync_to_async(thread_sensitive=True)
    def _fetch():
        product = Product.objects.select_related('subcategory').get(id=product_id)
        logger.debug(f"Получен товар: {product.name} (ID: {product_id})")
        return product
    return await _fetch()


async def get_or_create_cart(user: TelegramUser) -> Tuple[Cart, bool]:
    """
    Получение или создание корзины для пользователя.
    """
    @sync_to_async(thread_sensitive=True)
    def _get_or_create():
        cart, created = Cart.objects.get_or_create(user=user)
        if created:
            logger.info(f"Создана новая корзина для пользователя {user.telegram_id}.")
        else:
            logger.debug(f"Корзина пользователя {user.telegram_id} получена.")
        return cart, created
    return await _get_or_create()


async def update_cart_item(cart: Cart, product: Product, quantity: int) -> Optional[CartItem]:
    """
    Обновляет количество товара в корзине. Если количество становится меньше 1, удаляет товар из корзины.

    :param cart: Корзина пользователя
    :param product: Товар для обновления
    :param quantity: Изменение количества (может быть положительным или отрицательным)
    :return: Обновленный объект CartItem или None, если товар удален из корзины
    """
    @sync_to_async(thread_sensitive=True)
    def _update(c: Cart, p: Product, q: int) -> Optional[CartItem]:
        item, created = CartItem.objects.get_or_create(
            cart=c,
            product=p,
            defaults={'quantity': q}
        )
        if created:
            logger.info(f"Добавлен новый товар {p.name} (ID: {p.id}) в корзину пользователя {c.user.telegram_id} с количеством {q}.")
        else:
            item.quantity += q
            if item.quantity < 1:
                item.delete()
                logger.info(f"Товар {p.name} (ID: {p.id}) удален из корзины пользователя {c.user.telegram_id} из-за нулевого количества.")
                return None
            item.save()
            logger.info(f"Количество товара {p.name} (ID: {p.id}) в корзине пользователя {c.user.telegram_id} обновлено до {item.quantity}.")
        return item

    return await _update(cart, product, quantity)


# --- Генерация клавиатур ---

def product_detail_keyboard(
        product_id: int,
        back_callback: str,
        current_quantity: int = 1,
        cart_total: int = 0,
        cart_quantity: int = 0
) -> InlineKeyboardMarkup:
    """
    Генерация инлайн-клавиатуры для деталей продукта с возможностью изменения количества и добавления в корзину.
    """
    logger.debug(f"Генерация клавиатуры для продукта ID {product_id}.")
    buttons = [
        [
            InlineKeyboardButton(text="-", callback_data=f"dec:{product_id}"),
            InlineKeyboardButton(text=str(current_quantity), callback_data="noop"),
            InlineKeyboardButton(text="+", callback_data=f"inc:{product_id}"),
        ],
        [
            InlineKeyboardButton(
                text="Добавить в корзину",
                callback_data=f"add:{product_id}:{current_quantity}"
            )
        ],
    ]

    # Отображение кнопки корзины, если в ней есть товары
    if cart_quantity > 0:
        buttons.append([
            InlineKeyboardButton(
                text=f"🛒 Корзина ({cart_total} ₽) ({cart_quantity} шт.)",
                callback_data="cart"
            )
        ])
        logger.debug("Добавлена кнопка корзины в клавиатуру продукта.")

    buttons.append([
        InlineKeyboardButton(text="<-- Назад", callback_data=back_callback)
    ])
    logger.debug("Добавлена кнопка 'Назад' в клавиатуру продукта.")

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# --- Обработчики ---

@router.callback_query(F.data.startswith("product_"))
async def show_product_detail(callback: CallbackQuery):
    """
    Обработчик отображения деталей выбранного продукта.
    """
    product_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    logger.info(f"Пользователь {user_id} запросил детали продукта ID {product_id}.")

    try:
        product = await get_product_by_id(product_id)
        # Инициализация количества при открытии карточки товара
        quantity_storage[(user_id, product_id)] = 1
        logger.debug(f"Установлено начальное количество для продукта ID {product_id}: 1.")

        back_data = await generate_back_data(product)
        text = generate_product_text(product)

        if product.photo:
            await handle_photo_message(callback, product, text, back_data)
        else:
            await handle_text_message(callback, product, text, back_data, quantity=1)

    except Product.DoesNotExist:
        logger.error(f"Товар с ID {product_id} не найден.")
        await callback.answer("Товар не найден!", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка при отображении продукта ID {product_id}: {e}")
        await callback.answer("Произошла ошибка при отображении товара.", show_alert=True)
    finally:
        await callback.answer()


@router.callback_query(F.data.startswith("inc:"))
async def increase_quantity(callback: CallbackQuery):
    """
    Обработчик увеличения количества выбранного продукта.
    """
    product_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    key = (user_id, product_id)
    current = quantity_storage.get(key, 1)
    quantity_storage[key] = current + 1
    logger.debug(f"Увеличено количество для продукта ID {product_id} пользователя {user_id} до {quantity_storage[key]}.")

    await update_product_message(callback, product_id)


@router.callback_query(F.data.startswith("dec:"))
async def decrease_quantity(callback: CallbackQuery):
    """
    Обработчик уменьшения количества выбранного продукта.
    """
    product_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    key = (user_id, product_id)
    current = quantity_storage.get(key, 1)
    if current > 1:
        quantity_storage[key] = current - 1
        logger.debug(f"Уменьшено количество для продукта ID {product_id} пользователя {user_id} до {quantity_storage[key]}.")
    else:
        logger.debug(f"Количество для продукта ID {product_id} пользователя {user_id} уже минимально: {current}.")

    await update_product_message(callback, product_id)


@router.callback_query(F.data.startswith("add:"))
async def add_to_cart_handler(callback: CallbackQuery):
    """
    Обработчик добавления продукта в корзину.
    """
    _, product_id, quantity = callback.data.split(":")
    product_id = int(product_id)
    quantity = int(quantity)
    user_id = callback.from_user.id
    logger.info(f"Пользователь {user_id} добавляет продукт ID {product_id} в корзину с количеством {quantity}.")

    try:
        product = await get_product_by_id(product_id)
        user = await get_or_create_user(user_id)
        logger.debug(f"Пользователь найден: {user}")

        # Получаем или создаем корзину
        cart, created = await get_or_create_cart(user)
        if created:
            logger.info(f"Создана новая корзина для пользователя {user.telegram_id}.")

        # Добавляем товар в корзину
        item, created_item = await sync_to_async(
            CartItem.objects.get_or_create, thread_sensitive=True
        )(cart=cart, product=product, defaults={'quantity': quantity})
        if not created_item:
            item.quantity += quantity
            await sync_to_async(item.save, thread_sensitive=True)()
            logger.info(f"Обновлено количество товара {product.name} в корзине пользователя {user.telegram_id} до {item.quantity}.")
        else:
            logger.info(f"Добавлен новый товар {product.name} в корзину пользователя {user.telegram_id} с количеством {quantity}.")

        # Сбрасываем количество после добавления
        key = (user_id, product_id)
        if key in quantity_storage:
            del quantity_storage[key]
            logger.debug(f"Сбрасывается количество для продукта ID {product_id} пользователя {user_id}.")

        await callback.answer(f"✅ Добавлено: {product.name} × {quantity}", show_alert=True)
        logger.info(f"Товар {product.name} добавлен в корзину пользователя {user.telegram_id}.")

        # Обновляем данные корзины
        cart_total = await get_cart_total(user)
        cart_quantity = await get_cart_quantity(user)
        logger.debug(f"Корзина пользователя {user.telegram_id}: {cart_total} ₽, {cart_quantity} шт.")

        await update_product_message(
            callback,
            product_id,
            reset_quantity=True,
            cart_total=cart_total,
            cart_quantity=cart_quantity
        )

    except Product.DoesNotExist:
        logger.error(f"Товар с ID {product_id} не найден при попытке добавления в корзину.")
        await callback.answer("Товар не найден!", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка при добавлении товара ID {product_id} в корзину пользователя {user_id}: {e}")
        await callback.answer("Ошибка при добавлении товара", show_alert=True)


# --- Вспомогательные функции ---

async def update_product_message(
    callback: CallbackQuery,
    product_id: int,
    reset_quantity: bool = False,
    cart_total: int = 0,
    cart_quantity: int = 0
):
    """
    Обновляет сообщение с деталями продукта после изменения количества или добавления в корзину.
    """
    user_id = callback.from_user.id
    key = (user_id, product_id)
    logger.debug(f"Обновление сообщения для продукта ID {product_id} пользователя {user_id}.")

    try:
        product = await get_product_by_id(product_id)
        back_data = await generate_back_data(product)

        if reset_quantity:
            quantity = 1
            if key in quantity_storage:
                del quantity_storage[key]
                logger.debug(f"Количество для продукта ID {product_id} пользователя {user_id} сброшено до 1.")
        else:
            quantity = quantity_storage.get(key, 1)

        text = generate_product_text(product)
        markup = product_detail_keyboard(
            product.id,
            back_data,
            quantity,
            cart_total,
            cart_quantity
        )

        if product.photo:
            await callback.message.edit_caption(
                caption=text,
                reply_markup=markup
            )
            logger.debug(f"Сообщение с фото продукта ID {product_id} обновлено.")
        else:
            await callback.message.edit_text(
                text=text,
                reply_markup=markup
            )
            logger.debug(f"Сообщение текста продукта ID {product_id} обновлено.")

    except TelegramBadRequest as e:
        if "message is not modified" not in str(e).lower():
            logger.error(f"Ошибка при обновлении сообщения для продукта ID {product_id}: {e}")
            raise
        else:
            logger.debug(f"Сообщение для продукта ID {product_id} не изменилось.")
    except Exception as e:
        logger.error(f"Не удалось обновить сообщение для продукта ID {product_id}: {e}")


async def generate_back_data(product: Product) -> str:
    """
    Генерирует callback_data для кнопки возврата на основе подкатегории продукта.
    """
    if product.subcategory_id:
        back_data = f"subcategory_{product.subcategory_id}_1"
        logger.debug(f"Генерация callback_data для возврата к подкатегории ID {product.subcategory_id}.")
    else:
        back_data = "cat_page_1"
        logger.debug("Генерация callback_data для возврата к главному меню категорий.")
    return back_data


def generate_product_text(product: Product) -> str:
    """
    Генерирует текстовое описание продукта.
    """
    text = (
        f"{hbold(product.name)}\n"
        f"Цена: {product.price}₽\n\n"
        f"{product.description or 'Описание отсутствует'}"
    )
    logger.debug(f"Сгенерирован текст для продукта {product.name} (ID: {product.id}).")
    return text


async def handle_photo_message(callback: CallbackQuery, product: Product, text: str, back_data: str):
    """
    Обрабатывает сообщение с фотографией продукта.
    """
    try:
        await callback.message.delete()
        logger.debug(f"Исходное сообщение пользователя {callback.from_user.id} удалено для фото продукта ID {product.id}.")
        msg = await callback.message.answer_photo(
            photo=FSInputFile(product.photo.path),
            caption=text,
            reply_markup=product_detail_keyboard(product.id, back_data)
        )
        # Сохраняем начальное количество для продукта
        quantity_storage[(callback.from_user.id, product.id)] = 1
        logger.debug(f"Отправлено новое сообщение с фото продукта ID {product.id} пользователю {callback.from_user.id}.")
    except Exception as e:
        logger.error(f"Ошибка при обработке фото продукта ID {product.id}: {e}")
        await callback.answer("Произошла ошибка при отображении фото товара.", show_alert=True)


async def handle_text_message(callback: CallbackQuery, product: Product, text: str, back_data: str, quantity: int):
    """
    Обрабатывает текстовое сообщение с деталями продукта.
    """
    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=product_detail_keyboard(product.id, back_data, quantity)
        )
        logger.debug(f"Отредактировано текстовое сообщение для продукта ID {product.id} пользователю {callback.from_user.id}.")
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e).lower():
            logger.error(f"Ошибка при редактировании текстового сообщения для продукта ID {product.id}: {e}")
            await callback.answer("Произошла ошибка при обновлении сообщения.", show_alert=True)
        else:
            logger.debug(f"Сообщение для продукта ID {product.id} не изменилось.")


