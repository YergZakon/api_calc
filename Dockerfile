FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY services/punishment_api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

ENV REFERENCE_FILE_PATH=/app/справочник_УК_обновленный_2025_06_07_1.txt

CMD ["sh", "-c", "uvicorn services.punishment_api.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
