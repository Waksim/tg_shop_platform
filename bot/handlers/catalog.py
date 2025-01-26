# bot/handlers/catalog.py

import os
import django
import logging
from asgiref.sync import sync_to_async

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest

router = Router()

# Настройка логирования
logger = logging.getLogger(__name__)


def register_catalog_handlers(dp):
    """
    Регистрирует маршрутизатор обработчиков каталога в диспетчере.
    """
    dp.include_router(router)
    logger.info("Обработчики каталога зарегистрированы в диспетчере.")


# Инициализация Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_app.config.settings")
django.setup()
logger.info("Django успешно инициализирован для обработчиков каталога.")

from django_app.shop.models import Category, SubCategory, Product

ITEMS_PER_PAGE = 5  # Количество элементов на страницу


# --- Вспомогательные асинхронные функции ---

async def get_categories_page(page=1):
    """
    Получение списка категорий с пагинацией и общее количество категорий.
    """
    logger.debug(f"Получение категорий для страницы {page}.")

    @sync_to_async(thread_sensitive=True)
    def _fetch():
        categories = list(Category.objects.all().order_by("id")[(page - 1) * ITEMS_PER_PAGE: page * ITEMS_PER_PAGE])
        logger.debug(f"Получено {len(categories)} категорий для страницы {page}.")
        return categories

    @sync_to_async(thread_sensitive=True)
    def _count():
        count = Category.objects.count()
        logger.debug(f"Общее количество категорий: {count}.")
        return count

    return await _fetch(), await _count()


async def get_subcategories_page(category_id, page=1):
    """
    Получение списка подкатегорий для заданной категории с пагинацией и общее количество подкатегорий.
    """
    logger.debug(f"Получение подкатегорий для категории ID {category_id}, страница {page}.")

    @sync_to_async(thread_sensitive=True)
    def _fetch():
        subcategories = list(SubCategory.objects.filter(category_id=category_id).order_by("id")[
                             (page - 1) * ITEMS_PER_PAGE: page * ITEMS_PER_PAGE])
        logger.debug(f"Получено {len(subcategories)} подкатегорий для страницы {page}.")
        return subcategories

    @sync_to_async(thread_sensitive=True)
    def _count():
        count = SubCategory.objects.filter(category_id=category_id).count()
        logger.debug(f"Общее количество подкатегорий для категории ID {category_id}: {count}.")
        return count

    return await _fetch(), await _count()


async def get_products_page(subcategory_id, page=1):
    """
    Получение списка товаров для заданной подкатегории с пагинацией и общее количество товаров.
    """
    logger.debug(f"Получение товаров для подкатегории ID {subcategory_id}, страница {page}.")

    @sync_to_async(thread_sensitive=True)
    def _fetch():
        products = list(Product.objects.filter(subcategory_id=subcategory_id).order_by("id")[
                        (page - 1) * ITEMS_PER_PAGE: page * ITEMS_PER_PAGE])
        logger.debug(f"Получено {len(products)} товаров для страницы {page}.")
        return products

    @sync_to_async(thread_sensitive=True)
    def _count():
        count = Product.objects.filter(subcategory_id=subcategory_id).count()
        logger.debug(f"Общее количество товаров для подкатегории ID {subcategory_id}: {count}.")
        return count

    return await _fetch(), await _count()


# --- Генерация клавиатур (inline) ---

def get_categories_keyboard(page, categories, total_count):
    """
    Генерация инлайн-клавиатуры для отображения списка категорий с навигацией.
    """
    logger.debug(f"Генерация клавиатуры категорий для страницы {page}.")
    buttons = [
        [InlineKeyboardButton(text=cat.name, callback_data=f"category_{cat.id}_1")]
        for cat in categories
    ]

    max_page = (total_count - 1) // ITEMS_PER_PAGE + 1
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="←", callback_data=f"cat_page_{page - 1}"))
    if page < max_page:
        nav_buttons.append(InlineKeyboardButton(text="→", callback_data=f"cat_page_{page + 1}"))

    if nav_buttons:
        buttons.append(nav_buttons)
        logger.debug("Добавлены кнопки навигации в клавиатуру категорий.")

    # Кнопка возврата
    buttons.append([
        InlineKeyboardButton(
            text="<-- Назад",
            callback_data="main_menu"
        )
    ])
    logger.debug("Добавлена кнопка 'Назад' в клавиатуру категорий.")

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_subcategories_keyboard(cat_id, page, subcats, total_count):
    """
    Генерация инлайн-клавиатуры для отображения списка подкатегорий с навигацией.
    """
    logger.debug(f"Генерация клавиатуры подкатегорий для категории ID {cat_id}, страницы {page}.")
    buttons = [
        [InlineKeyboardButton(text=sc.name, callback_data=f"subcategory_{sc.id}_1")]
        for sc in subcats
    ]

    max_page = (total_count - 1) // ITEMS_PER_PAGE + 1
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="←", callback_data=f"subcat_page_{cat_id}_{page - 1}"))
    if page < max_page:
        nav_buttons.append(InlineKeyboardButton(text="→", callback_data=f"subcat_page_{cat_id}_{page + 1}"))

    if nav_buttons:
        buttons.append(nav_buttons)
        logger.debug("Добавлены кнопки навигации в клавиатуру подкатегорий.")

    # Кнопка возврата к категориям
    buttons.append([InlineKeyboardButton(text="<-- Назад", callback_data="cat_page_1")])
    logger.debug("Добавлена кнопка 'Назад' в клавиатуру подкатегорий.")

    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def get_products_keyboard(subcat_id, page, products, total_count):
    """
    Генерация инлайн-клавиатуры для отображения списка товаров с навигацией.
    """
    logger.debug(f"Генерация клавиатуры товаров для подкатегории ID {subcat_id}, страницы {page}.")

    @sync_to_async
    def _get_parent_category_id():
        try:
            subcat = SubCategory.objects.get(id=subcat_id)
            logger.debug(f"Родительская категория для подкатегории ID {subcat_id}: {subcat.category.id}.")
            return subcat.category.id
        except SubCategory.DoesNotExist:
            logger.error(f"Подкатегория с ID {subcat_id} не найдена.")
            return None

    category_id = await _get_parent_category_id()

    buttons = [
        [InlineKeyboardButton(text=f"{p.name} — {p.price}₽", callback_data=f"product_{p.id}")]
        for p in products
    ]

    max_page = (total_count - 1) // ITEMS_PER_PAGE + 1
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="←", callback_data=f"prod_page_{subcat_id}_{page - 1}"))
    nav_buttons.append(InlineKeyboardButton(text=f"{page}/{max_page}", callback_data="noop"))
    if page < max_page:
        nav_buttons.append(InlineKeyboardButton(text="→", callback_data=f"prod_page_{subcat_id}_{page + 1}"))

    if nav_buttons:
        buttons.append(nav_buttons)
        logger.debug("Добавлены кнопки навигации в клавиатуру товаров.")

    # Кнопка возврата к подкатегориям или категориям
    buttons.append([
        InlineKeyboardButton(
            text="<-- Назад",
            callback_data=f"category_{category_id}_1" if category_id else "cat_page_1"
        )
    ])
    logger.debug("Добавлена кнопка 'Назад' в клавиатуру товаров.")

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# --- Обработчики с улучшенной обработкой ошибок ---

async def safe_edit_message(callback: CallbackQuery, text: str, reply_markup: InlineKeyboardMarkup):
    """
    Безопасное редактирование сообщения с обработкой возможных ошибок.
    """
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup)
        logger.debug("Сообщение успешно отредактировано.")
    except TelegramBadRequest as e:
        logger.error(f"Ошибка при редактировании сообщения: {e}")
        if "message is not modified" in str(e).lower():
            await callback.answer()
            logger.debug("Сообщение не было изменено, ответ отправлен.")
        else:
            await callback.message.delete()
            await callback.message.answer(text, reply_markup=reply_markup)
            logger.info("Сообщение удалено и отправлено новое из-за ошибки редактирования.")


@router.callback_query(F.data.startswith("prod_page_"))
async def products_pagination(callback: CallbackQuery):
    """
    Обработчик пагинации товаров.
    """
    logger.info("Запрос на пагинацию товаров.")
    try:
        _, _, subcat_id, page = callback.data.split("_")
        subcat_id = int(subcat_id)
        page = int(page)
        logger.debug(f"Пагинация товаров для подкатегории ID {subcat_id}, страницы {page}.")
    except (ValueError, IndexError) as e:
        logger.error(f"Неверный формат данных для пагинации товаров: {callback.data} - {e}")
        await callback.answer("Некорректные данные для пагинации.", show_alert=True)
        return

    products, total_count = await get_products_page(subcat_id, page)

    if not products:
        logger.warning(f"Товары не найдены для подкатегории ID {subcat_id}, страницы {page}.")
        await callback.answer("Товары не найдены.")
        return

    kb = await get_products_keyboard(subcat_id, page, products, total_count)
    await safe_edit_message(callback, "Список товаров:", kb)
    await callback.answer()
    logger.info(f"Пагинация товаров завершена для подкатегории ID {subcat_id}, страницы {page}.")


@router.callback_query(F.data == "noop")
async def noop_handler(callback: CallbackQuery):
    """
    Обработчик для бездействующих кнопок.
    """
    logger.debug("Обработчик noop вызван.")
    await callback.answer()


@router.message(F.text == "/catalog")
async def cmd_catalog(message: Message):
    """
    Обработчик команды /catalog для отображения списка категорий.
    """
    logger.info(f"Пользователь {message.from_user.id} запросил каталог.")
    page = 1
    categories, total_count = await get_categories_page(page)
    if not categories:
        logger.warning("Категорий не найдено.")
        await message.answer("Категорий не найдено.")
        return
    kb = get_categories_keyboard(page, categories, total_count)
    await message.answer("Выберите категорию:", reply_markup=kb)
    logger.debug(f"Каталог категорий отправлен пользователю {message.from_user.id}.")


@router.callback_query(F.data.startswith("cat_page_"))
async def categories_pagination(callback: CallbackQuery):
    """
    Обработчик пагинации категорий.
    """
    logger.info("Запрос на пагинацию категорий.")
    try:
        page = int(callback.data.split("_")[-1])
        logger.debug(f"Пагинация категорий на страницу {page}.")
    except (ValueError, IndexError) as e:
        logger.error(f"Неверный формат данных для пагинации категорий: {callback.data} - {e}")
        await callback.answer("Некорректные данные для пагинации.", show_alert=True)
        return

    categories, total_count = await get_categories_page(page)

    if not categories:
        logger.warning(f"Категории не найдены для страницы {page}.")
        await callback.answer("Категории не найдены.")
        return

    kb = get_categories_keyboard(page, categories, total_count)
    await safe_edit_message(callback, "Выберите категорию:", kb)
    await callback.answer()
    logger.info(f"Пагинация категорий завершена на страницу {page}.")


@router.callback_query(F.data.startswith("category_"))
async def subcategories_show(callback: CallbackQuery):
    """
    Обработчик отображения подкатегорий выбранной категории.
    """
    logger.info("Запрос на отображение подкатегорий.")
    try:
        _, cat_id, page = callback.data.split("_")
        cat_id = int(cat_id)
        page = int(page)
        logger.debug(f"Показ подкатегорий для категории ID {cat_id}, страницы {page}.")
    except (ValueError, IndexError) as e:
        logger.error(f"Неверный формат данных для отображения подкатегорий: {callback.data} - {e}")
        await callback.answer("Некорректные данные для отображения подкатегорий.", show_alert=True)
        return

    subcats, total_count = await get_subcategories_page(cat_id, page)

    if not subcats and total_count == 0:
        logger.warning(f"Подкатегории не найдены для категории ID {cat_id}.")
        await callback.answer("Категория не найдена или в ней нет подкатегорий.", show_alert=True)
        return

    kb = get_subcategories_keyboard(cat_id, page, subcats, total_count)
    await safe_edit_message(callback, "Выберите подкатегорию:", kb)
    await callback.answer()
    logger.info(f"Подкатегории для категории ID {cat_id} отображены.")


@router.callback_query(F.data.startswith("subcat_page_"))
async def subcat_pagination(callback: CallbackQuery):
    """
    Обработчик пагинации подкатегорий.
    """
    logger.info("Запрос на пагинацию подкатегорий.")
    try:
        _, _, cat_id, page = callback.data.split("_")
        cat_id = int(cat_id)
        page = int(page)
        logger.debug(f"Пагинация подкатегорий для категории ID {cat_id}, страницы {page}.")
    except (ValueError, IndexError) as e:
        logger.error(f"Неверный формат данных для пагинации подкатегорий: {callback.data} - {e}")
        await callback.answer("Некорректные данные для пагинации подкатегорий.", show_alert=True)
        return

    subcats, total_count = await get_subcategories_page(cat_id, page)
    if not subcats:
        logger.warning(f"Подкатегории не найдены для категории ID {cat_id}, страницы {page}.")
        await callback.answer("Подкатегории не найдены.", show_alert=True)
        return

    kb = get_subcategories_keyboard(cat_id, page, subcats, total_count)
    await safe_edit_message(callback, "Выберите подкатегорию:", kb)
    await callback.answer()
    logger.info(f"Пагинация подкатегорий завершена для категории ID {cat_id}, страницы {page}.")


@router.callback_query(F.data.startswith("subcategory_"))
async def products_show(callback: CallbackQuery):
    """
    Обработчик отображения товаров выбранной подкатегории.
    """
    logger.info("Запрос на отображение товаров подкатегории.")
    try:
        _, subcat_id, page = callback.data.split("_")
        subcat_id = int(subcat_id)
        page = int(page)
        logger.debug(f"Показ товаров для подкатегории ID {subcat_id}, страницы {page}.")
    except (ValueError, IndexError) as e:
        logger.error(f"Неверный формат данных для отображения товаров: {callback.data} - {e}")
        await callback.answer("Некорректные данные для отображения товаров.", show_alert=True)
        return

    products, total_count = await get_products_page(subcat_id, page)

    if not products and total_count == 0:
        logger.warning(f"Товары не найдены для подкатегории ID {subcat_id}.")
        await callback.answer("Подкатегория не найдена или в ней нет товаров.", show_alert=True)
        return

    kb = await get_products_keyboard(subcat_id, page, products, total_count)
    await safe_edit_message(callback, "Список товаров:", kb)
    await callback.answer()
    logger.info(f"Товары для подкатегории ID {subcat_id} отображены.")
