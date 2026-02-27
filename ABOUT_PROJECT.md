# Punishment API (Standalone)

## What it is
Standalone FastAPI service for punishment calculation with JSON input/output and Swagger.

## Run locally
```bash
export REFERENCE_FILE_PATH="/path/to/справочник_УК_обновленный_2025_06_07_1.txt"
uvicorn app.main:app --reload
```

## Endpoints
- `POST /calculate`
- `GET /reference/status`
- `POST /reference/reload`
- `GET /health`

## Notes
- RU only for now.
- `aNakaz` is returned as 15x13 strict array plus structured JSON.
- Full FoxPro parity is implemented based on `count_srk.prg`, `ddtomy.prg`, and `slvst.prg`.

## Input fields (FoxPro parity)
Provide these fields for accurate results (strings as in FoxPro forms):
- `crime.crime_date` (FS1R51P2)
- `crime.article_code` (FS1R54P1)
- `crime.article_parts` (FS1R54P2, comma-separated)
- `crime.crime_stage` or `crime.fs1r56p1` (FS1R56P1)
- `crime.mitigating` or `crime.fs1r571p1` (FS1R571P1)
- `crime.aggravating` or `crime.fs1r572p1` (FS1R572P1)
- `crime.special_condition` or `crime.fs1r573p1` (FS1R573P1)
- `crime.fs1r041p1`, `crime.fs1r042p1` (special procedure flags)
- `crime.fs1r23p1`, `crime.fs1r26p1`
- `person.birth_date` (FS1R13P1)
- `person.gender` (FS1R15P1)
- `person.citizenship` (FS1R17P1)
- `person.dependents` (FS1R21P1)
- `person.additional_marks` (FS1R231P1)
- Optional: `calc_date` to override server date used in month/day conversions
