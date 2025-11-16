#!/usr/bin/env python
"""
Скрипт для миграции данных из SQLite в PostgreSQL.

Использование:
    python migrate_sqlite_to_postgres.py [path_to_sqlite_db]

Если путь не указан, используется db.sqlite3 в директории recipes/
"""

import os
import sys
import django
from pathlib import Path

# Настройка Django окружения
# Скрипт может быть запущен из корня проекта или из директории recipes
BASE_DIR = Path(__file__).resolve().parent
if (BASE_DIR / 'recipes').exists():
    # Скрипт в корне проекта
    sys.path.insert(0, str(BASE_DIR / 'recipes'))
    SQLITE_DEFAULT_PATH = BASE_DIR / 'recipes' / 'db.sqlite3'
else:
    # Скрипт в директории recipes
    sys.path.insert(0, str(BASE_DIR))
    SQLITE_DEFAULT_PATH = BASE_DIR / 'db.sqlite3'

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'recipes.settings')

# Временно используем SQLite для чтения данных
os.environ['DB_ENGINE'] = 'django.db.backends.sqlite3'
django.setup()

from django.db import connections
from main.models import Recipe


def migrate_data(sqlite_path=None):
    """
    Мигрирует данные из SQLite в PostgreSQL.
    
    Args:
        sqlite_path: Путь к SQLite файлу. Если None, используется db.sqlite3
    """
    if sqlite_path is None:
        sqlite_path = SQLITE_DEFAULT_PATH
    else:
        sqlite_path = Path(sqlite_path)
    
    if not sqlite_path.exists():
        print(f"Ошибка: Файл {sqlite_path} не найден!")
        return False
    
    print(f"Чтение данных из SQLite: {sqlite_path}")
    
    # Подключаемся к SQLite базе
    sqlite_db = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': str(sqlite_path),
    }
    
    # Временно заменяем конфигурацию БД
    from django.conf import settings
    original_db = settings.DATABASES['default'].copy()
    settings.DATABASES['default'] = sqlite_db
    connections.databases['default'] = sqlite_db
    
    # Читаем все рецепты из SQLite
    try:
        recipes = Recipe.objects.all()
        recipes_count = recipes.count()
        print(f"Найдено рецептов в SQLite: {recipes_count}")
        
        if recipes_count == 0:
            print("Нет данных для миграции.")
            return True
        
        # Восстанавливаем конфигурацию PostgreSQL
        settings.DATABASES['default'] = original_db
        connections.databases['default'] = original_db
        connections['default'].close()
        
        # Переключаемся на PostgreSQL
        os.environ['DB_ENGINE'] = 'django.db.backends.postgresql'
        django.setup()
        
        print("\nПодключение к PostgreSQL...")
        print("Убедитесь, что PostgreSQL запущен и доступен!")
        
        # Проверяем подключение к PostgreSQL
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        print("Подключение к PostgreSQL успешно!\n")
        
        # Мигрируем данные
        migrated = 0
        skipped = 0
        errors = 0
        
        # Временно снова подключаемся к SQLite для чтения
        settings.DATABASES['sqlite'] = sqlite_db
        connections.databases['sqlite'] = sqlite_db
        
        from django.db import router
        for recipe in Recipe.objects.using('sqlite').all():
            try:
                # Проверяем, существует ли рецепт с такой же сигнатурой
                existing = Recipe.objects.filter(signature=recipe.signature).first()
                if existing:
                    print(f"  Пропущен (дубликат): {recipe.title}")
                    skipped += 1
                    continue
                
                # Создаем новый рецепт в PostgreSQL
                new_recipe = Recipe(
                    title=recipe.title,
                    ingredients=recipe.ingredients,
                    instructions=recipe.instructions,
                    servings=recipe.servings,
                    cook_minutes=recipe.cook_minutes,
                    signature=recipe.signature,
                    created_at=recipe.created_at,
                    updated_at=recipe.updated_at,
                )
                new_recipe.save()
                print(f"  Мигрирован: {recipe.title}")
                migrated += 1
                
            except Exception as e:
                print(f"  Ошибка при миграции '{recipe.title}': {e}")
                errors += 1
        
        print(f"\n{'='*50}")
        print(f"Миграция завершена!")
        print(f"  Успешно мигрировано: {migrated}")
        print(f"  Пропущено (дубликаты): {skipped}")
        print(f"  Ошибок: {errors}")
        print(f"{'='*50}")
        
        return errors == 0
        
    except Exception as e:
        print(f"Ошибка при чтении данных из SQLite: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    sqlite_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    print("="*50)
    print("Миграция данных из SQLite в PostgreSQL")
    print("="*50)
    print()
    
    success = migrate_data(sqlite_path)
    
    if success:
        print("\nМиграция успешно завершена!")
        sys.exit(0)
    else:
        print("\nМиграция завершилась с ошибками!")
        sys.exit(1)

