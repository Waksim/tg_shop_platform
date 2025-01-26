# bot/handlers/payments.py
import os
import django
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from yookassa import Payment
from asgiref.sync import sync_to_async
import logging

logger = logging.getLogger(__name__)

router = Router()

# Инициализация Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_app.config.settings")
django.setup()

from django_app.shop.models import Order, TelegramUser


@router.callback_query(F.data.startswith("check_payment_"))
async def check_payment(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[-1])

    try:
        user = await sync_to_async(TelegramUser.objects.get)(telegram_id=callback.from_user.id)
        order = await sync_to_async(Order.objects.get)(id=order_id, user=user)

        payment = await sync_to_async(Payment.find_one)(order.payment_id)

        if payment.status == "succeeded":
            order.is_paid = True
            await sync_to_async(order.save)()

            await callback.message.edit_text(
                "✅ Оплата подтверждена! Спасибо за покупку!\n"
                "Мы уже начали собирать ваш заказ!"
            )
        else:
            await callback.answer(
                "⚠️ Оплата еще не прошла\n"
                "Попробуйте проверить позже или обратитесь в поддержку",
                show_alert=True
            )

    except Exception as e:
        await callback.answer("❌ Произошла ошибка при проверке оплаты", show_alert=True)
        logger.error(f"Payment check error: {str(e)}")

    await callback.answer()


@router.callback_query(F.data.startswith("test_payment_"))
async def handle_test_payment(callback: CallbackQuery):
    try:
        order_id = int(callback.data.split("_")[-1])
        user = await sync_to_async(TelegramUser.objects.get)(telegram_id=callback.from_user.id)
        order = await sync_to_async(Order.objects.get)(id=order_id, user=user)

        # Помечаем заказ как оплаченный
        order.is_paid = True
        await sync_to_async(order.save)()

        # Создаем клавиатуру с кнопкой возврата
        return_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🛍️ Вернуться в каталог", callback_data="cat_page_1")]
            ]
        )

        # Обновляем сообщение с новой клавиатурой
        await callback.message.edit_text(
            "✅ Заказ оплачен в тестовом режиме! Спасибо за покупку!\n"
            "Мы уже начали собирать ваш заказ!",
            reply_markup=return_keyboard
        )

    except Exception as e:
        logger.error(f"Test payment error: {str(e)}")
        await callback.answer("❌ Ошибка при тестовой оплате", show_alert=True)

    await callback.answer()


@router.callback_query(F.data == "payment_not_available")
async def show_payment_alert(callback: CallbackQuery):
    await callback.answer(
        text="В данный момент оплата не доступна, извините 😢",
        show_alert=True
    )