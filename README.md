# Сервис расчёта наказаний

## Описание сервиса
- **name:** gp-sentence-calc-service
- **port:** 9000
- **context-path:** /calc
- **actuator:** http://gp-sentence-calc-service.gosobvin.kz:31056/api/gp/v1/calc/health
- **swagger:** http://gp-sentence-calc-service.gosobvin.kz:31056/docs

## Дополнительную информация по проекту смотри в файлах:
- ABOUT_PROJECT.md
- MIGRATE_PROJECT.md
- API_FIELDS_DOCS.md

## Запуск локально контейнера 
- Сборка: 
```docker build -t api_calc_fork .```
- Запуск:
``` docker run -p 9000:9000 api_calc_fork```
- Пересборка:
``` docker build -t api_calc_fork .```
- Остановить контейнер:
```
docker ps
docker stop <container_id>
```
- Проверка в браузере (swagger): http://localhost:9000/docs