# Используем официальный Python образ
FROM python:3.11-slim

# Устанавливаем переменные окружения
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        gcc \
        python3-dev \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements и устанавливаем зависимости
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Копируем проект
COPY recipes/ /app/

# Создаем директории для статических файлов и медиа
RUN mkdir -p /app/staticfiles /app/media /app/data/uploads /app/data/exports

# Собираем статические файлы (будет выполнено при сборке)
# RUN python manage.py collectstatic --noinput

# Открываем порт
EXPOSE 8000

# Команда запуска (будет переопределена в docker-compose для ожидания БД)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

