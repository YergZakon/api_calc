FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    REFERENCE_FILE_PATH=/app/reference_uk_2025_06_07.txt

WORKDIR /app

# системные зависимости (если нужны)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY app ./app
COPY tests ./tests
COPY scripts ./scripts
COPY reference_uk_2025_06_07.txt ./

RUN pip install --upgrade pip && pip install .

EXPOSE 9000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9000"]