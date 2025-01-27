import os
import django
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
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
    """
    Обработка проверки платежа:
    - Если платеж успешен, помечаем заказ как оплаченный.
    - Иначе (не оплачено) просто показываем alert (всплывающее окно) с ошибкой
      и формируем новую ссылку на оплату, обновляя inline-клавиатуру
      но НЕ трогая текст сообщения (там остались тестовые карты).
    """
    order_id = int(callback.data.split("_")[-1])

    try:
        user = await sync_to_async(TelegramUser.objects.get)(telegram_id=callback.from_user.id)
        order = await sync_to_async(Order.objects.get)(id=order_id, user=user)

        if not order.payment_id:
            await callback.answer(
                "Платёж ещё не был создан. Попробуйте заново оформить заказ.",
                show_alert=True
            )
            return

        payment = await sync_to_async(Payment.find_one)(order.payment_id)

        if payment.status == "succeeded":
            order.is_paid = True
            await sync_to_async(order.save)()

            return_keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🛍️ Вернуться в каталог", callback_data="cat_page_1")]
                ]
            )

            await callback.message.edit_text(
                "✅ Оплата подтверждена! Спасибо за покупку!\n"
                "Мы уже начали собирать ваш заказ!",
                reply_markup=return_keyboard
            )

        else:
            # Оплата не прошла -> формируем новую ссылку,
            # но выводим ошибку во всплывающем alert,
            # а текст сообщения НЕ трогаем, чтобы не потерять данные об оплате.
            new_payment = await sync_to_async(order.create_payment)()
            if not new_payment:
                await callback.answer("❌ Не удалось создать новый платёж", show_alert=True)
                return

            confirmation_url = new_payment.confirmation.confirmation_url

            pay_keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="💳 Оплатить снова",
                            url=confirmation_url
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="✅ Проверить оплату",
                            callback_data=f"check_payment_{order.id}"
                        )
                    ]
                ]
            )

            # Сообщаем пользователю во всплывающем окне
            await callback.answer(
                "❌ Оплата не была подтверждена. Ссылка на новый платёж сформирована.\n"
                "Пожалуйста, попробуйте оплатить ещё раз.",
                show_alert=True
            )

            # Обновляем ТОЛЬКО inline-клавиатуру, сохраняя текст сообщения
            await callback.message.edit_reply_markup(pay_keyboard)

    except Exception as e:
        await callback.answer("❌ Произошла ошибка при проверке оплаты", show_alert=True)
        logger.error(f"Payment check error: {str(e)}", exc_info=True)

    await callback.answer()
