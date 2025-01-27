import os
import django
import logging
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from asgiref.sync import sync_to_async

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup

# Вместо aiogram.utils.html (устаревшее):
from aiogram.utils.text_decorations import html_decoration as html

from django_app.shop.models import Cart, CartItem, Order, TelegramUser

# Настройка логирования
logger = logging.getLogger(__name__)

router = Router()

class OrderState(StatesGroup):
    waiting_for_address = State()

# Инициализация Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_app.config.settings")
django.setup()

# --- Вспомогательные асинхронные функции ---

@sync_to_async
def get_or_create_user(tg_id: int) -> TelegramUser:
    """
    Получаем пользователя из БД по telegram_id (или создаём, если не существует).
    """
    logger.debug(f"Получение или создание пользователя с ID: {tg_id}")
    return TelegramUser.objects.get(telegram_id=tg_id)

@sync_to_async
def get_cart(user: TelegramUser) -> Cart:
    """
    Получаем корзину пользователя или создаём новую.
    """
    logger.debug(f"Получение корзины для пользователя: {user.telegram_id}")
    cart, created = Cart.objects.get_or_create(user=user)
    if created:
        logger.info(f"Создана новая корзина для пользователя: {user.telegram_id}")
    return cart

@sync_to_async
def get_cart_items(user: TelegramUser) -> list[CartItem]:
    """
    Получаем все товары в корзине у пользователя.
    """
    logger.debug(f"Получение товаров в корзине для пользователя: {user.telegram_id}")
    return list(CartItem.objects.filter(cart__user=user).select_related("product"))

@sync_to_async
def remove_item_from_cart(user: TelegramUser, product_id: int) -> None:
    """
    Удаляем указанный товар из корзины пользователя.
    Если корзина в итоге пуста, удаляем саму корзину.
    """
    logger.info(f"Удаление товара с ID {product_id} из корзины пользователя: {user.telegram_id}")
    cart = Cart.objects.get(user=user)
    CartItem.objects.filter(cart=cart, product_id=product_id).delete()
    if cart.items.count() == 0:
        cart.delete()
        logger.info(f"Корзина пользователя {user.telegram_id} удалена, так как она пуста.")

@sync_to_async
def create_order(user: TelegramUser, address: str) -> Order:
    """
    Создаём заказ на основе корзины пользователя с указанным адресом.
    """
    logger.info(f"Создание заказа для пользователя: {user.telegram_id} по адресу: {address}")
    cart = Cart.objects.get(user=user)
    total = sum(item.product.price * item.quantity for item in cart.items.all())

    order = Order.objects.create(
        user=user,
        address=address,
        total=total
    )

    for cart_item in cart.items.all():
        order.items.create(product=cart_item.product, quantity=cart_item.quantity)

    # После создания Order очищаем корзину
    cart.delete()
    logger.info(f"Заказ {order.id} создан для пользователя {user.telegram_id}")
    return order

@sync_to_async
def get_cart_quantity(user: TelegramUser) -> int:
    """
    Возвращает общее количество всех товаров в корзине пользователя.
    """
    logger.debug(f"Получение количества товаров в корзине для пользователя: {user.telegram_id}")
    total = 0
    cart = Cart.objects.filter(user=user).first()
    if cart:
        total = sum(item.quantity for item in cart.items.all())
    return total

@sync_to_async
def get_cart_total(user: TelegramUser) -> int:
    """
    Возвращает общую стоимость корзины пользователя.
    """
    logger.debug(f"Получение общей стоимости корзины для пользователя: {user.telegram_id}")
    total = 0
    cart = Cart.objects.filter(user=user).first()
    if cart:
        for item in cart.items.all():
            total += item.product.price * item.quantity
    return total

# --- Генерация клавиатур ---

def generate_cart_keyboard(items: list[CartItem]) -> InlineKeyboardMarkup:
    """
    Генерирует inline-клавиатуру для отображения корзины и управления ею.
    """
    logger.debug("Генерация клавиатуры корзины")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"❌ {item.product.name} x{item.quantity}",
                callback_data=f"remove_item_{item.product.id}"
            )
        ]
        for item in items
    ])

    if items:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text="✅ Оформить заказ", callback_data="checkout")
        ])

    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="<-- Назад", callback_data="main_menu")
    ])

    return keyboard

# --- Обработчики ---

async def show_cart(user: TelegramUser, message: Message | CallbackQuery) -> None:
    """
    Выводит пользователю список товаров в корзине, либо сообщение о том, что корзина пуста.
    """
    logger.info(f"Отображение корзины для пользователя: {user.telegram_id}")
    items = await get_cart_items(user)

    if not items:
        text = "🛒 Ваша корзина пуста"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="<-- Назад", callback_data="main_menu")]
        ])

        if isinstance(message, Message):
            await message.answer(text, reply_markup=kb)
        else:
            await message.message.edit_text(text, reply_markup=kb)
        return

    total = sum(item.product.price * item.quantity for item in items)
    text = (
        html.bold("🛒 Ваша корзина:") + "\n\n" +
        "\n".join(
            f"• {html.quote(item.product.name)} - {item.quantity} шт. × {html.quote(str(item.product.price))}₽"
            for item in items
        ) +
        "\n\n" +
        html.bold(f"Итого: {total} ₽")
    )

    kb = generate_cart_keyboard(items)
    parse_mode = ParseMode.HTML

    try:
        if isinstance(message, Message):
            await message.answer(text, reply_markup=kb, parse_mode=parse_mode)
        else:
            if message.message.photo:
                await message.message.edit_caption(
                    caption=text,
                    reply_markup=kb,
                    parse_mode=parse_mode
                )
            else:
                await message.message.edit_text(
                    text,
                    reply_markup=kb,
                    parse_mode=parse_mode
                )
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            logger.error(f"Ошибка редактирования сообщения: {e}")
            await message.answer(text, reply_markup=kb, parse_mode=parse_mode)

@router.callback_query(F.data == "cart")
@router.message(F.text == "/cart")
async def handle_cart(request: Message | CallbackQuery) -> None:
    """
    Обработчик кнопки/команды "Корзина".
    """
    user = await get_or_create_user(request.from_user.id)
    logger.info(f"Обработчик корзины вызван пользователем: {user.telegram_id}")
    await show_cart(user, request)

@router.callback_query(F.data.startswith("remove_item_"))
async def remove_item(callback: CallbackQuery) -> None:
    """
    Обработчик удаления конкретного товара из корзины.
    """
    user = await get_or_create_user(callback.from_user.id)
    product_id = int(callback.data.split("_")[-1])

    logger.info(f"Удаление товара с ID {product_id} из корзины пользователя: {user.telegram_id}")
    await remove_item_from_cart(user, product_id)
    await callback.answer("Товар удалён из корзины")
    await show_cart(user, callback)

@router.callback_query(F.data == "checkout")
async def start_checkout(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Начало оформления заказа: просим пользователя ввести адрес доставки.
    """
    logger.info(f"Начало оформления заказа пользователем: {callback.from_user.id}")
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass

    msg = await callback.message.answer(
        "📦 Введите адрес доставки:\n"
        "(Укажите город, улицу, дом и квартиру)"
    )

    await state.update_data(address_message_id=msg.message_id)
    await state.set_state(OrderState.waiting_for_address)

@router.message(OrderState.waiting_for_address)
async def process_address(message: Message, state: FSMContext) -> None:
    """
    Принимаем адрес, создаём заказ и сразу формируем платёж. Выводим
    сообщение со ссылкой на оплату и кнопкой «Проверить оплату».
    """
    user = await get_or_create_user(message.from_user.id)
    address = message.text.strip()

    logger.info(f"Обработка адреса доставки для пользователя {user.telegram_id}: {address}")
    try:
        order = await create_order(user, address)

        # Создаём платёж сразу
        payment = await sync_to_async(order.create_payment)()
        if not payment:
            await message.answer("❌ Произошла ошибка при создании платежа.")
            await state.clear()
            return

        confirmation_url = payment.confirmation.confirmation_url

        # Формируем клавиатуру из двух кнопок
        payment_kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💳 Оплатить заказ",
                    url=confirmation_url
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Проверить оплату",
                    callback_data=f"check_payment_{order.id}"
                )
            ]
        ])

        await message.answer(
            f"✅ Заказ {html.bold(f'#{order.id}')} оформлен!\n"
            f"Адрес доставки: {html.quote(address)}\n"
            f"Сумма к оплате: {html.bold(f'{order.total} ₽')}\n\n"
            f"Тестовые карты для оплаты:\n"
            f"• MasterCard: <code>5555 5555 5555 4477</code> (<code>08</code>/<code>28</code>) CVC <code>555</code>\n"
            f"• Visa: <code>4793 1281 6164 4804</code> (<code>12</code>/<code>28</code>) CVC <code>111</code>\n"
            f"(в качестве SMS подтверждения введите любое число)",
            reply_markup=payment_kb,
            parse_mode=ParseMode.HTML
        )
    except Cart.DoesNotExist:
        logger.error(f"Попытка оформить заказ без корзины для пользователя {user.telegram_id}")
        await message.answer("❌ Ваша корзина пуста!")

    await state.clear()
