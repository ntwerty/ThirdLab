# Django Recipes Application

Веб-приложение для управления рецептами с поддержкой хранения данных в файлах (XML) и базе данных (PostgreSQL). Приложение полностью докеризировано и готово к развертыванию.

## Возможности

- ✅ Создание, редактирование и удаление рецептов
- ✅ Хранение данных в файлах (XML) или базе данных (PostgreSQL)
- ✅ Проверка на дубликаты рецептов при сохранении в БД
- ✅ AJAX-поиск по рецептам
- ✅ Загрузка рецептов из XML файлов
- ✅ Экспорт рецептов в XML
- ✅ Полная докеризация с Docker и Docker Compose
- ✅ Миграция данных из SQLite в PostgreSQL

## Технологический стек

- **Backend**: Django 5.2.7
- **База данных**: PostgreSQL 15
- **Контейнеризация**: Docker, Docker Compose
- **Python**: 3.11

## Требования

- Docker (версия 20.10 или выше)
- Docker Compose (версия 2.0 или выше)

## Быстрый старт

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd ThirdLab-new-branch
```

### 2. Настройка переменных окружения

Создайте файл `.env` в корне проекта на основе примера:

```bash
# Django Settings
DEBUG=True
DJANGO_SECRET_KEY=your-secret-key-here-change-in-production
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:8000

# Database Configuration (PostgreSQL)
DB_ENGINE=django.db.backends.postgresql
DB_NAME=recipes_db
DB_USER=recipes_user
DB_PASSWORD=recipes_password
DB_HOST=db
DB_PORT=5432

# PostgreSQL Container Settings
POSTGRES_DB=recipes_db
POSTGRES_USER=recipes_user
POSTGRES_PASSWORD=recipes_password
POSTGRES_PORT=5432

# Django Container Settings
DJANGO_PORT=8000
```

**⚠️ ВАЖНО**: В production обязательно измените `DJANGO_SECRET_KEY` и `POSTGRES_PASSWORD` на безопасные значения!

### 3. Запуск приложения

#### Для разработки:

```bash
# Сборка и запуск контейнеров
docker-compose up --build

# Или в фоновом режиме
docker-compose up -d --build
```

Приложение будет доступно по адресу: http://localhost:8000

#### Первый запуск (создание миграций):

При первом запуске Django автоматически выполнит миграции базы данных. Если нужно выполнить миграции вручную:

```bash
docker-compose exec web python manage.py migrate
```

#### Создание суперпользователя:

```bash
docker-compose exec web python manage.py createsuperuser
```

### 4. Остановка приложения

```bash
docker-compose down
```

Для удаления всех данных (включая базу данных):

```bash
docker-compose down -v
```

## Миграция данных из SQLite в PostgreSQL

Если у вас есть существующая SQLite база данных (`recipes/db.sqlite3`), вы можете мигрировать данные в PostgreSQL.

### Способ 1: Автоматическая миграция через скрипт

1. Убедитесь, что контейнеры запущены:
   ```bash
   docker-compose up -d
   ```

2. Скопируйте SQLite базу в контейнер (если она находится локально):
   ```bash
   docker cp recipes/db.sqlite3 recipes_web:/app/db.sqlite3
   ```

3. Запустите скрипт миграции:
   ```bash
   docker-compose exec web python migrate_sqlite_to_postgres.py db.sqlite3
   ```

   Или используйте bash-скрипт (Linux/Mac):
   ```bash
   bash scripts/migrate_data.sh
   ```

### Способ 2: Ручная миграция через Django

1. Экспортируйте данные из SQLite:
   ```bash
   # Временно переключитесь на SQLite
   export DB_ENGINE=django.db.backends.sqlite3
   python manage.py dumpdata main.Recipe --indent 2 > recipes_backup.json
   ```

2. Импортируйте данные в PostgreSQL:
   ```bash
   # Переключитесь обратно на PostgreSQL
   export DB_ENGINE=django.db.backends.postgresql
   python manage.py loaddata recipes_backup.json
   ```

### Способ 3: Использование pgloader (альтернативный метод)

Если у вас установлен `pgloader`:

```bash
# Установите pgloader (Ubuntu/Debian)
sudo apt-get install pgloader

# Выполните миграцию
pgloader sqlite:///path/to/db.sqlite3 postgresql://recipes_user:recipes_password@localhost:5432/recipes_db
```

## Структура проекта

```
ThirdLab-new-branch/
├── Dockerfile                 # Образ для Django приложения
├── docker-compose.yml         # Конфигурация Docker Compose
├── .dockerignore              # Исключения для Docker build
├── .gitignore                 # Исключения для Git
├── requirements.txt           # Python зависимости
├── migrate_sqlite_to_postgres.py  # Скрипт миграции данных
├── README.md                  # Документация
├── scripts/
│   └── migrate_data.sh        # Bash скрипт для миграции
└── recipes/
    ├── manage.py
    ├── db.sqlite3             # SQLite база (опционально)
    ├── recipes/
    │   ├── settings.py        # Настройки Django
    │   ├── urls.py
    │   ├── wsgi.py
    │   └── asgi.py
    ├── main/
    │   ├── models.py          # Модель Recipe
    │   ├── views.py           # Представления
    │   ├── forms.py           # Формы
    │   ├── urls.py
    │   └── templates/
    ├── staticfiles/           # Собранные статические файлы
    ├── media/                 # Загруженные медиа файлы
    └── data/
        ├── uploads/           # Загруженные XML файлы
        └── exports/           # Экспортированные XML файлы
```

## Volumes (постоянное хранение данных)

Docker Compose настроен с следующими volumes для постоянного хранения данных:

- `postgres_data` - данные PostgreSQL базы
- `static_volume` - собранные статические файлы
- `media_volume` - загруженные медиа файлы
- `data_volume` - XML файлы (uploads и exports)

Данные сохраняются между перезапусками контейнеров.

## Разработка

### Локальная разработка без Docker

Если вы хотите разрабатывать без Docker:

1. Создайте виртуальное окружение:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # или
   venv\Scripts\activate  # Windows
   ```

2. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

3. Настройте базу данных (SQLite по умолчанию):
   ```bash
   cd recipes
   python manage.py migrate
   ```

4. Запустите сервер разработки:
   ```bash
   python manage.py runserver
   ```

### Работа с контейнерами

Выполнение команд Django в контейнере:

```bash
# Миграции
docker-compose exec web python manage.py migrate

# Создание суперпользователя
docker-compose exec web python manage.py createsuperuser

# Сборка статических файлов
docker-compose exec web python manage.py collectstatic --noinput

# Открытие shell
docker-compose exec web python manage.py shell

# Просмотр логов
docker-compose logs -f web
docker-compose logs -f db
```

## Production развертывание

### Рекомендации для production:

1. **Безопасность**:
   - Установите `DEBUG=False` в `.env`
   - Используйте сильный `DJANGO_SECRET_KEY`
   - Измените пароли БД на безопасные
   - Настройте `ALLOWED_HOSTS` для вашего домена
   - Настройте `CSRF_TRUSTED_ORIGINS`

2. **Статические файлы**:
   - В production используйте веб-сервер (nginx) для обслуживания статических файлов
   - Или используйте облачное хранилище (AWS S3, etc.)

3. **База данных**:
   - Рассмотрите использование управляемой PostgreSQL (AWS RDS, Google Cloud SQL, etc.)
   - Настройте регулярные бэкапы

4. **Обновление docker-compose.yml для production**:
   ```yaml
   # Добавьте nginx сервис
   # Настройте SSL сертификаты
   # Используйте secrets для паролей
   ```

### Пример production .env:

```env
DEBUG=False
DJANGO_SECRET_KEY=<generate-strong-secret-key>
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

DB_ENGINE=django.db.backends.postgresql
DB_NAME=recipes_prod
DB_USER=recipes_prod_user
DB_PASSWORD=<strong-password>
DB_HOST=db
DB_PORT=5432

POSTGRES_DB=recipes_prod
POSTGRES_USER=recipes_prod_user
POSTGRES_PASSWORD=<strong-password>
```

## Функциональность приложения

### Работа с рецептами

1. **Создание рецепта**:
   - Перейдите на главную страницу
   - Заполните форму рецепта
   - Выберите хранилище (файл или база данных)
   - При сохранении в БД автоматически проверяется наличие дубликатов

2. **Просмотр рецептов из БД**:
   - Перейдите в раздел "База данных"
   - Используйте поиск для фильтрации рецептов
   - AJAX-поиск работает в реальном времени

3. **Редактирование/Удаление**:
   - Откройте детальную страницу рецепта
   - Используйте кнопки редактирования или удаления

4. **Работа с файлами**:
   - Загружайте XML файлы с рецептами
   - Просматривайте список всех файлов
   - Экспортируйте рецепты в XML

### Проверка на дубликаты

При сохранении рецепта в базу данных система автоматически:
- Вычисляет сигнатуру рецепта на основе всех полей
- Проверяет наличие рецепта с такой же сигнатурой
- Предупреждает пользователя, если дубликат найден

## Устранение неполадок

### Проблема: Контейнер не запускается

```bash
# Проверьте логи
docker-compose logs web

# Пересоберите образы
docker-compose build --no-cache
docker-compose up
```

### Проблема: Ошибка подключения к базе данных

1. Убедитесь, что контейнер БД запущен:
   ```bash
   docker-compose ps
   ```

2. Проверьте переменные окружения в `.env`

3. Проверьте логи БД:
   ```bash
   docker-compose logs db
   ```

### Проблема: Миграции не применяются

```bash
# Выполните миграции вручную
docker-compose exec web python manage.py migrate

# Если нужно сбросить БД (⚠️ удалит все данные)
docker-compose down -v
docker-compose up -d
docker-compose exec web python manage.py migrate
```

### Проблема: Статические файлы не загружаются

```bash
# Пересоберите статические файлы
docker-compose exec web python manage.py collectstatic --noinput
```

## Лицензия

Этот проект создан в учебных целях.

## Контакты

Для вопросов и предложений создайте issue в репозитории.
