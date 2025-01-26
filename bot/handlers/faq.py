# bot/handlers/faq.py

import os
import django
import logging
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from asgiref.sync import sync_to_async
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.markdown import hbold, hunderline
from aiogram.filters import StateFilter
from aiogram.exceptions import TelegramBadRequest

from django_app.shop.models import FAQ

router = Router()

# Настройка логирования
logger = logging.getLogger(__name__)

ITEMS_PER_PAGE = 5  # Количество элементов на страницу
SEARCH_RESULTS_PER_PAGE = 5  # Количество результатов на страницу поиска


class FAQStates(StatesGroup):
    browsing = State()
    waiting_question = State()
    viewing_item = State()
    searching = State()  # Состояние для поиска


# Инициализация Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_app.config.settings")
django.setup()
logger.info("Django успешно инициализирован для обработчиков FAQ.")


@sync_to_async
def get_faq_page(page: int = 1):
    """
    Получение списка FAQ с пагинацией.
    """
    faq_page = list(FAQ.objects.all()[(page - 1) * ITEMS_PER_PAGE: page * ITEMS_PER_PAGE])
    logger.debug(f"Получено {len(faq_page)} FAQ для страницы {page}.")
    return faq_page


@sync_to_async
def get_faq_count():
    """
    Получение общего количества FAQ.
    """
    count = FAQ.objects.count()
    logger.debug(f"Общее количество FAQ: {count}.")
    return count


@sync_to_async
def get_faq_item(item_id: int):
    """
    Получение отдельного FAQ по его ID.
    """
    try:
        faq_item = FAQ.objects.get(id=item_id)
        logger.debug(f"Получен FAQ с ID {item_id}: {faq_item.question}")
        return faq_item
    except FAQ.DoesNotExist:
        logger.warning(f"FAQ с ID {item_id} не найден.")
        return None


@sync_to_async
def search_faq(query: str, page: int = 1):
    """
    Поиск FAQ по запросу с учетом регистра.
    """
    logger.debug(f"Поиск FAQ по запросу: '{query}', страница {page}.")
    start = (page - 1) * SEARCH_RESULTS_PER_PAGE
    end = start + SEARCH_RESULTS_PER_PAGE

    q_lower = query.lower()
    q_capital = q_lower.capitalize()

    qs_lower = FAQ.objects.filter(question__icontains=q_lower)
    qs_capital = FAQ.objects.filter(question__icontains=q_capital)

    combined = (qs_lower | qs_capital).distinct()
    results = list(combined[start:end])
    logger.debug(f"Найдено {len(results)} результатов для запроса '{query}' на странице {page}.")
    return results


@sync_to_async
def get_search_count(query: str):
    """
    Получение общего количества результатов поиска по запросу.
    """
    logger.debug(f"Получение количества результатов поиска для запроса: '{query}'.")
    q_lower = query.lower()
    q_capital = q_lower.capitalize()

    qs_lower = FAQ.objects.filter(question__icontains=q_lower)
    qs_capital = FAQ.objects.filter(question__icontains=q_capital)

    combined = (qs_lower | qs_capital).distinct()
    count = combined.count()
    logger.debug(f"Общее количество результатов поиска для '{query}': {count}.")
    return count


def build_faq_keyboard(faq_items, page: int, total_pages: int):
    """
    Построение инлайн-клавиатуры для списка FAQ с пагинацией.
    """
    logger.debug(f"Построение клавиатуры для FAQ страницы {page} из {total_pages}.")
    buttons = []

    # Кнопки номеров вопросов
    number_buttons = [
        InlineKeyboardButton(text=str(i + 1), callback_data=f"faq_item_{item.id}")
        for i, item in enumerate(faq_items)
    ]
    if number_buttons:
        buttons.append(number_buttons)
        logger.debug("Добавлены кнопки номеров FAQ.")

    # Пагинация
    pagination_buttons = []
    if total_pages > 1:
        if page > 1:
            pagination_buttons.append(InlineKeyboardButton(text="←", callback_data=f"faq_page_{page - 1}"))
        pagination_buttons.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop"))
        if page < total_pages:
            pagination_buttons.append(InlineKeyboardButton(text="→", callback_data=f"faq_page_{page + 1}"))
        buttons.append(pagination_buttons)
        logger.debug("Добавлены кнопки пагинации FAQ.")

    # Управление
    buttons.append([InlineKeyboardButton(text="🔍 Задать вопрос", callback_data="ask_question")])
    buttons.append([InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_search_keyboard(results, page: int, total_pages: int, query: str):
    """
    Построение инлайн-клавиатуры для результатов поиска FAQ с пагинацией.
    """
    logger.debug(f"Построение клавиатуры для поиска FAQ по запросу '{query}', страница {page} из {total_pages}.")
    buttons = []

    # Кнопки номеров вопросов в один ряд
    number_buttons = [
        InlineKeyboardButton(text=str(i + 1), callback_data=f"faq_item_{item.id}")
        for i, item in enumerate(results)
    ]
    if number_buttons:
        buttons.append(number_buttons)
        logger.debug("Добавлены кнопки номеров найденных FAQ.")

    # Кодируем запрос для безопасной передачи в callback_data
    encoded_query = query.replace("_", "##")

    # Пагинация
    pagination_buttons = []
    if total_pages > 1:
        if page > 1:
            pagination_buttons.append(
                InlineKeyboardButton(
                    text="←",
                    callback_data=f"search_page_{page - 1}_{encoded_query}"
                )
            )
        pagination_buttons.append(
            InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop")
        )
        if page < total_pages:
            pagination_buttons.append(
                InlineKeyboardButton(
                    text="→",
                    callback_data=f"search_page_{page + 1}_{encoded_query}"
                )
            )
        buttons.append(pagination_buttons)
        logger.debug("Добавлены кнопки пагинации для поиска FAQ.")

    buttons.append([InlineKeyboardButton(text="🔙 Назад к FAQ", callback_data="faq")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_to_list_keyboard(page: int):
    """
    Клавиатура для возврата к списку FAQ.
    """
    logger.debug(f"Построение клавиатуры для возврата к списку FAQ, страница {page}.")
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад к списку", callback_data=f"faq_page_{page}")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
    ])


async def edit_or_resend_message(callback: CallbackQuery, text: str, markup: InlineKeyboardMarkup):
    """
    Безопасное редактирование сообщения или отправка нового в случае ошибки.
    """
    try:
        await callback.message.edit_caption(caption=text, reply_markup=markup)
        logger.debug("Сообщение успешно отредактировано с новым текстом и клавиатурой.")
    except TelegramBadRequest as e:
        logger.error(f"Ошибка при редактировании сообщения с подписью: {e}")
        try:
            await callback.message.edit_text(text=text, reply_markup=markup)
            logger.debug("Сообщение успешно отредактировано с новым текстом.")
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e).lower():
                logger.error(f"Не удалось отредактировать сообщение, отправляется новое: {e}")
                await callback.message.delete()
                await callback.message.answer(text=text, reply_markup=markup)
                logger.info("Новое сообщение отправлено после удаления старого.")


@router.callback_query(F.data == "faq")
async def show_faq(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик для отображения списка FAQ.
    """
    logger.info(f"Пользователь {callback.from_user.id} запросил FAQ.")
    await state.set_state(FAQStates.browsing)
    await state.update_data(current_page=1)
    await show_faq_page(callback, 1)


async def show_faq_page(callback: CallbackQuery, page: int):
    """
    Отображение определенной страницы FAQ.
    """
    logger.debug(f"Отображение страницы FAQ {page}.")
    faq_items = await get_faq_page(page)
    total_count = await get_faq_count()
    total_pages = max(1, (total_count - 1) // ITEMS_PER_PAGE + 1)
    page = max(1, min(page, total_pages))

    text = "❓ Часто задаваемые вопросы:\n\n"
    if faq_items:
        text += "\n".join(
            f"{i + 1}. {item.question}"
            for i, item in enumerate(faq_items)
        )
    else:
        text = "❌ В базе пока нет вопросов\n"

    if faq_items:
        markup = build_faq_keyboard(faq_items, page, total_pages)
    else:
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
        ])
        logger.debug("FAQ пуст, добавлена кнопка возврата в главное меню.")

    await edit_or_resend_message(callback, text, markup)
    await callback.answer()
    logger.info(f"Страница FAQ {page} отображена.")


@router.callback_query(F.data.startswith("faq_page_"))
async def faq_pagination(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик пагинации списка FAQ.
    """
    try:
        page = int(callback.data.split("_")[-1])
        logger.debug(f"Пагинация FAQ на страницу {page}.")
    except (ValueError, IndexError) as e:
        logger.error(f"Неверный формат данных для пагинации FAQ: {callback.data} - {e}")
        await callback.answer("Некорректные данные для пагинации.", show_alert=True)
        return

    await state.update_data(current_page=page)
    await show_faq_page(callback, page)


@router.callback_query(F.data.startswith("faq_item_"))
async def show_faq_item(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик отображения отдельного FAQ.
    """
    try:
        item_id = int(callback.data.split("_")[-1])
        logger.debug(f"Запрос на отображение FAQ с ID {item_id}.")
    except (ValueError, IndexError) as e:
        logger.error(f"Неверный формат данных для отображения FAQ: {callback.data} - {e}")
        await callback.answer("Некорректные данные для отображения FAQ.", show_alert=True)
        return

    faq_item = await get_faq_item(item_id)

    if not faq_item:
        logger.warning(f"FAQ с ID {item_id} не найден.")
        await callback.answer("⚠️ Вопрос не найден!", show_alert=True)
        return

    data = await state.get_data()
    current_page = data.get('current_page', 1)

    text = (
        f"{hunderline('Вопрос:')}\n{faq_item.question}\n\n"
        f"{hunderline('Ответ:')}\n{faq_item.answer}"
    )

    await edit_or_resend_message(callback, text, back_to_list_keyboard(current_page))
    await callback.answer()
    logger.info(f"FAQ с ID {item_id} отображен пользователю {callback.from_user.id}.")


@router.callback_query(F.data == "ask_question")
async def ask_question_handler(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик запроса пользователя на задачу нового вопроса.
    """
    logger.info(f"Пользователь {callback.from_user.id} инициировал задачу вопроса.")
    await state.set_state(FAQStates.waiting_question)
    await edit_or_resend_message(
        callback,
        "✍️ Введите ваш вопрос текстом:",
        InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="faq")]
        ])
    )
    await callback.answer()


@router.message(F.text, StateFilter(FAQStates.waiting_question))
async def process_question(message: Message, state: FSMContext):
    """
    Обработка введенного пользователем вопроса и переход к поиску.
    """
    query = message.text.strip()
    logger.info(f"Пользователь {message.from_user.id} задал вопрос: '{query}'.")
    await state.set_state(FAQStates.searching)
    await state.update_data(search_query=query, search_page=1)
    await show_search_results(message, state, query, 1)


async def show_search_results(message: Message, state: FSMContext, query: str, page: int):
    """
    Отображение результатов поиска FAQ по запросу пользователя.
    """
    logger.debug(f"Отображение результатов поиска для запроса '{query}', страница {page}.")
    await state.update_data(search_query=query, search_page=page)

    decoded_query = query.replace("##", "_")
    results = await search_faq(decoded_query, page)
    total_count = await get_search_count(decoded_query)
    total_pages = max(1, (total_count - 1) // SEARCH_RESULTS_PER_PAGE + 1)
    page = max(1, min(page, total_pages))

    text = f"🔍 Результаты поиска по запросу '{decoded_query}':\n\n"
    if results:
        text += "\n".join(f"{i + 1}. {item.question}" for i, item in enumerate(results))
        markup = build_search_keyboard(results, page, total_pages, decoded_query)
    else:
        text += "❌ Ничего не найдено\nВы можете задать вопрос напрямую @maksenro"
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад к FAQ", callback_data="faq")]
        ])
        logger.debug("Поиск не дал результатов, добавлена кнопка возврата к FAQ.")

    try:
        # Редактируем исходное сообщение с вопросом
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=message.message_id - 1,
            text=text,
            reply_markup=markup
        )
        await message.delete()
        logger.debug("Сообщение с результатами поиска успешно отредактировано.")
    except TelegramBadRequest as e:
        logger.error(f"Ошибка при редактировании сообщения с результатами поиска: {e}")
        if "message to edit not found" in str(e).lower():
            new_msg = await message.answer(text, reply_markup=markup)
            await state.update_data(search_message_id=new_msg.message_id)
            logger.info("Новое сообщение с результатами поиска отправлено.")
        else:
            await message.answer(text, reply_markup=markup)
            logger.info("Сообщение с результатами поиска отправлено заново из-за ошибки редактирования.")


@router.callback_query(F.data.startswith("search_page_"))
async def search_pagination(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик пагинации результатов поиска FAQ.
    """
    logger.info(f"Пользователь {callback.from_user.id} запросил пагинацию поиска.")
    try:
        parts = callback.data.split("_")
        if len(parts) < 4:
            raise ValueError("Invalid callback data format")

        page = int(parts[2])
        query = "_".join(parts[3:]).replace("##", "_")
        logger.debug(f"Пагинация поиска FAQ на страницу {page} для запроса '{query}'.")
    except (ValueError, IndexError) as e:
        logger.error(f"Неверный формат данных для пагинации поиска FAQ: {callback.data} - {e}")
        await callback.answer("❌ Некорректные данные для пагинации поиска.", show_alert=True)
        return

    await show_search_results(callback.message, state, query, page)
    await callback.answer()
    logger.info(f"Пагинация поиска FAQ на страницу {page} завершена.")
