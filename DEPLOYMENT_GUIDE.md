# Инструкция по развёртыванию Punishment API (Swagger)

## Что передать разработчику
- Репозиторий: https://github.com/YergZakon/api_calc
- Файл справочника находится в корне репозитория: `справочник_УК_обновленный_2025_06_07_1.txt`
- Swagger UI: `/docs`
- OpenAPI JSON: `/openapi.json`

## Быстрый локальный запуск (Docker)
```bash
cd api_calc

docker build -t punishment-api .

docker run -p 8000:8000 punishment-api
```
Проверка:
- `http://localhost:8000/health`
- `http://localhost:8000/docs`
- `http://localhost:8000/openapi.json`
ы

## Переменные окружения
- `REFERENCE_FILE_PATH=/app/справочник_УК_обновленный_2025_06_07_1.txt`
  - В Dockerfile уже выставлено по умолчанию.
- `PORT` — Railway выставляет автоматически.

## Эндпойнты
- `GET /health`
- `GET /reference/status`
- `POST /reference/reload`
- `POST /calculate`

## Пример запроса
```bash
curl -X POST https://<domain>/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "lang": "ru",
    "person": {
      "birth_date": "2001-10-24",
      "gender": "1",
      "citizenship": "1"
    },
    "crime": {
      "crime_date": "2025-09-12",
      "article_code": "0990001",
      "article_parts": "01",
      "crime_stage": "3",
      "mitigating": "01",
      "aggravating": "",
      "special_condition": ""
    }
  }'
```

## OpenAPI файл
Можно забрать с сервера:
```bash
curl https://<domain>/openapi.json > openapi.json
```

## Примечания
- Swagger доступен по `/docs` сразу после запуска.
- Сервис автономный, использует локальный справочник.
- Вход/выход только JSON.
