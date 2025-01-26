# django_app/manage.py

import sys
import os

# Добавляем корень проекта в sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_app.config.settings")


def main():
    """Запускает административные команды Django."""
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Не могу импортировать Django. Убедитесь, что оно установлено и доступно."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
