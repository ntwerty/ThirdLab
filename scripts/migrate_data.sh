#!/bin/bash
# Скрипт для миграции данных из SQLite в PostgreSQL через Docker

echo "=========================================="
echo "Миграция данных из SQLite в PostgreSQL"
echo "=========================================="
echo ""

# Проверяем, что контейнеры запущены
if ! docker-compose ps | grep -q "recipes_web.*Up"; then
    echo "Ошибка: Контейнеры не запущены!"
    echo "Запустите сначала: docker-compose up -d"
    exit 1
fi

# Копируем SQLite базу в контейнер (если она существует)
if [ -f "recipes/db.sqlite3" ]; then
    echo "Копирование SQLite базы в контейнер..."
    docker cp recipes/db.sqlite3 recipes_web:/app/db.sqlite3
fi

# Запускаем скрипт миграции
echo "Запуск скрипта миграции..."
docker-compose exec web python migrate_sqlite_to_postgres.py db.sqlite3

echo ""
echo "Миграция завершена!"

