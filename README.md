# Meetup BOT

__Здесь будет красивое и подробное описание этого проекта__

## Техническая информация

### Установка
1. Установить зависимости
    ```
    pip install -r requirements.txt
    ```
1. Создать файл `.env`, в него положить токен бота и токен для приема оплат
    ```
    TG_TOKEN=<ваш токен>
    TG_PAY_TOKEN=<другой ваш токен>
    ```
    Как получать токен оплат: https://core.telegram.org/bots/payments#getting-a-token
1. Создать БД 
    ```
    python manage.py migrate
    ```
1. Создать администратора
    ```
    python manage.py createsuperuser
    ```
1. Бота запускать командой
    ```
    python bot_backend.py
    ```
1. Админку запускать командой
    ```
    python manage.py runserver
    ```
    Доступ по адресу http://127.0.0.1:8000/admin