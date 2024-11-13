FROM python:3.11-slim

WORKDIR /app

# Сначала устанавливаем shared зависимости
COPY shared/requirements.txt shared-requirements.txt
RUN pip install --no-cache-dir -r shared-requirements.txt

# Затем устанавливаем зависимости бота
COPY telegram_bot/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY telegram_bot/src/ /app/src/
COPY shared/ /app/shared/
COPY .env /app/.env

ENV PYTHONPATH=/app

CMD ["python", "src/main.py"] 