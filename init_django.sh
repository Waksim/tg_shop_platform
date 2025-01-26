#!/bin/sh

# Применение миграций базы данных
python django_app/manage.py migrate

# Загрузка тестовых данных
python django_app/load_data.py

# Создание суперпользователя, если он не существует
echo "Проверка и создание суперпользователя, если он не существует..."

python django_app/manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
username = "$DJANGO_SUPERUSER_USERNAME"
email = "$DJANGO_SUPERUSER_EMAIL"
password = "$DJANGO_SUPERUSER_PASSWORD"

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print("Суперпользователь создан.")
else:
    print("Суперпользователь уже существует.")
EOF

# Запуск сервера Django
python django_app/manage.py runserver 0.0.0.0:8000
