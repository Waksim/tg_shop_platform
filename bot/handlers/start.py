# bot/handlers/start.py

import os
import django
import logging
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from asgiref.sync import sync_to_async

from django_app.shop.models import TelegramUser

router = Router()

# Настройка логирования
logger = logging.getLogger(__name__)

CHANNEL_ID = -1002253035978  # ID официального канала
GROUP_ID = -4744061031  # ID группы поддержки


def register_start_handlers(dp):
    """
    Регистрирует маршрутизатор обработчиков стартовых команд в диспетчере.
    """
    dp.include_router(router)
    logger.info("Обработчики стартовых команд зарегистрированы в диспетчере.")


@sync_to_async(thread_sensitive=True)
def get_or_create_user(user_id: int, **kwargs) -> TelegramUser:
    """
    Получение пользователя по его Telegram ID или создание нового, если он не существует.

    :param user_id: Telegram ID пользователя
    :param kwargs: Дополнительные данные пользователя
    :return: Объект TelegramUser
    """
    user, created = TelegramUser.objects.get_or_create(
        telegram_id=user_id,
        defaults={
            'first_name': kwargs.get('first_name'),
            'last_name': kwargs.get('last_name'),
            'username': kwargs.get('username'),
            'language_code': kwargs.get('language_code')
        }
    )
    if created:
        logger.info(f"Создан новый пользователь: {user}")
    else:
        logger.debug(f"Пользователь найден: {user}")
    return user


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Создание основной инлайн-клавиатуры.

    :return: Объект InlineKeyboardMarkup с кнопками меню
    """
    logger.debug("Создание основной клавиатуры меню.")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛍️ Каталог", callback_data="cat_page_1")],
            [InlineKeyboardButton(text="🛒 Корзина", callback_data="cart")],
            [InlineKeyboardButton(text="❓ FAQ", callback_data="faq")]
        ]
    )


def welcome_message(user_name: str) -> str:
    """
    Формирование приветственного сообщения для пользователя.

    :param user_name: Имя пользователя
    :return: Строка приветственного сообщения
    """
    message = (
        f"👋 Добро пожаловать, {user_name}!\n\n"
        "Мы рады видеть вас в нашем магазине! 🛍️\n"
        "Выберите действие в меню ниже:\n\n"
        "🔹 Посмотрите наш Каталог с товарами\n"
        "🔹 Загляните в корзину и оформите покупку\n"
        "🔹 Или найдите ответы на вопросы в разделе FAQ."
    )
    logger.debug(f"Формирование приветственного сообщения для пользователя {user_name}.")
    return message


@router.message(F.text == "/start")
async def start_command(message: Message):
    """
    Обработчик команды /start. Проверяет подписку пользователя и приветствует его.

    :param message: Объект сообщения
    """
    bot = message.bot
    user_id = message.from_user.id
    logger.info(f"Получена команда /start от пользователя {user_id}.")

    try:
        user_data = message.from_user
        user = await get_or_create_user(
            user_id=user_data.id,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            username=user_data.username,
            language_code=user_data.language_code
        )
        logger.debug(f"Пользователь {user_id} обработан.")

        # Проверка подписки на канал и группу
        channel_member = await bot.get_chat_member(CHANNEL_ID, user_id)
        group_member = await bot.get_chat_member(GROUP_ID, user_id)
        logger.debug(
            f"Статусы подписки для пользователя {user_id}: Канал - {channel_member.status}, Группа - {group_member.status}.")

        if channel_member.status in ["left", "kicked"] or group_member.status in ["left", "kicked"]:
            logger.warning(f"Пользователь {user_id} не подписан на необходимые каналы.")
            await message.answer(
                "📢 Для продолжения подпишитесь на наши ресурсы:\n"
                "- [Официальный канал](https://t.me/+S_nrWJVLwQ1jNzIy)\n"
                "- [Чат поддержки](https://t.me/+BQC2N3ks1RdmMzMy)",
                disable_web_page_preview=True,
                parse_mode="Markdown"
            )
        else:
            logger.info(f"Пользователь {user_id} успешно подписан. Отправка приветственного сообщения.")
            await message.answer(
                welcome_message(message.from_user.first_name),
                reply_markup=main_menu_keyboard()
            )

    except TelegramAPIError as e:
        logger.error(f"Ошибка Telegram API при проверке подписки для пользователя {user_id}: {e}")
        await message.answer("⚠️ Не удалось проверить подписку. Попробуйте позже.")


@router.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback: CallbackQuery):
    """
    Обработчик возврата в главное меню из других разделов.

    :param callback: Объект CallbackQuery
    """
    user_first_name = callback.from_user.first_name
    logger.info(f"Пользователь {callback.from_user.id} возвращается в главное меню.")

    try:
        # Пытаемся редактировать сообщение с фотографией
        await callback.message.edit_caption(
            caption=welcome_message(user_first_name),
            reply_markup=main_menu_keyboard()
        )
        logger.debug("Сообщение с фото успешно отредактировано для возврата в главное меню.")
    except TelegramBadRequest:
        logger.warning("Не удалось отредактировать сообщение с фото. Переход к редактированию текста.")
        try:
            # Если сообщение не содержит фото, редактируем текстовое сообщение
            await callback.message.edit_text(
                welcome_message(user_first_name),
                reply_markup=main_menu_keyboard()
            )
            logger.debug("Текстовое сообщение успешно отредактировано для возврата в главное меню.")
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e).lower():
                logger.error(f"Ошибка при редактировании текстового сообщения: {e}. Отправка нового сообщения.")
                await callback.answer()
                await callback.message.answer(
                    welcome_message(user_first_name),
                    reply_markup=main_menu_keyboard()
                )
            else:
                logger.debug("Сообщение не изменилось. Нет необходимости отправлять новое сообщение.")
    except Exception as e:
        logger.error(f"Неизвестная ошибка при возврате в главное меню: {e}")

    await callback.answer()
