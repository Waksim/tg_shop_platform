# tg_shop_platform

Telegram-бот для интернет-магазина с интеграцией Django и PostgreSQL. Проект разработан с использованием современных технологий, таких как Docker и асинхронная обработка данных.

## Основные возможности

- **Telegram-бот**: Каталог товаров с категориями, подкатегориями, корзиной и системой оплаты.
- **Админ-панель Django**: Управление заказами, клиентами и товарами.
- **База данных PostgreSQL**: Надёжное и масштабируемое хранилище данных.
- **Docker**: Простое развертывание через контейнеризацию.
- **Асинхронность**: Эффективное взаимодействие с базой данных.
- **Логирование**: Сохранение логов для анализа и отладки.

## Структура проекта

- `bot/` — исходный код Telegram-бота на Aiogram 3.
- `django_app/` — исходный код Django-приложения.
- `logs/` — директория для логов.
- `requirements.txt` — зависимости проекта.
- `docker-compose.yml` — конфигурация Docker Compose для сборки проекта.
- `Dockerfile.django` и `Dockerfile.bot` — Dockerfile для соответствующих сервисов.

## Установка и запуск

### Предварительные требования
- Docker и Docker Compose установлены на вашем устройстве.
- Создайте файл `.env` в корне проекта с необходимыми переменными окружения.

### Шаги для запуска

1. Склонируйте репозиторий:
   ```bash
   git clone https://github.com/Waksim/tg_shop_platform.git
   cd tg_shop_platform
   ```

2. Постройте и запустите контейнеры:
   ```bash
   docker-compose up --build
   ```

3. Бот и Django-приложение будут запущены. Логи работы доступны в директории `logs/`.

### Переменные окружения
Пример содержимого `.env`:
```env
# База данных PostgreSQL
POSTGRES_DB=your_postgres_db_name  # Имя базы данных
POSTGRES_USER=your_postgres_user  # Имя пользователя базы данных
POSTGRES_PASSWORD=your_postgres_password  # Пароль пользователя базы данных
POSTGRES_HOST=db  # Хост базы данных (имя сервиса в Docker Compose)
POSTGRES_PORT=5432  # Порт базы данных

# Настройки Django
DJANGO_SETTINGS_MODULE=django_app.config.settings  # Модуль настроек Django
DJANGO_SECRET_KEY=your_django_secret_key  # Секретный ключ Django
DJANGO_DEBUG=True  # Включение режима отладки Django

# Суперпользователь Django
DJANGO_SUPERUSER_USERNAME=your_superuser_username  # Имя суперпользователя
DJANGO_SUPERUSER_PASSWORD=your_superuser_password  # Пароль суперпользователя
DJANGO_SUPERUSER_EMAIL=your_superuser_email  # Email суперпользователя

# Настройки Telegram бота
TELEGRAM_BOT_TOKEN=your_telegram_bot_token  # Токен Telegram бота

# Настройки YooKassa
YOOKASSA_SHOP_ID=your_yookassa_shop_id  # ID магазина в YooKassa
YOOKASSA_API_KEY=your_yookassa_api_key  # API-ключ для YooKassa
# YOOKASSA_RETURN_URL=your_return_url  # URL для возврата после оплаты (для продакшена)
```

## Как использовать

1. Запустите проект с помощью Docker.
2. В Telegram найдите бота, используя токен, и начните с команды `/start`.
3. Используйте каталог для выбора товаров, добавляйте их в корзину и совершайте покупки.
4. Администраторы могут управлять данными через Django-панель.

