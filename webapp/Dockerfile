FROM python:3.11-slim

WORKDIR /app

# Сначала устанавливаем shared зависимости
COPY shared/requirements.txt shared-requirements.txt
RUN pip install --no-cache-dir -r shared-requirements.txt

# Затем устанавливаем зависимости webapp
COPY webapp/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY webapp/src/ /app/src/
COPY webapp/static/ /app/static/
COPY shared/ /app/shared/
COPY .env /app/.env

ENV PYTHONPATH=/app

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"] 