# Punishment API (Standalone)

## What it is
Standalone FastAPI service for punishment calculation with JSON input/output and Swagger.

## Run locally
```bash
# Optional: override reference file and data dir
export REFERENCE_FILE_PATH="/path/to/справочник_УК_обновленный_2025_06_07_1.txt"
export DATA_DIR="/tmp/punishment_api_data"

# New structure entrypoint
uvicorn services.punishment_api.app.main:app --reload

# Legacy alias still works
# uvicorn services.punishment_api.app:app --reload
```

## Endpoints
Полный список см. в Swagger (`/docs`) или `openapi_punishment_api.json`.

Ключевые:
- `POST /calculate`
- `GET /api/article/`
- `POST /api/case/{erdr}/analyze-materials/`
- `POST /api/vectorize/`
- `POST /api/case/{uuid}/verdicts/similar/`
- `POST /api/case/{erdr}/norms/`
- `POST /api/case/{erdr}/risks/analyze/`
- `POST /api/generate/async/`
- `POST /api/case/{uuid}/verdict/analyze/`

## Notes
- RU only for now.
- `aNakaz` is returned as 15x13 strict array plus structured JSON.
- Full FoxPro parity is implemented based on `count_srk.prg`, `ddtomy.prg`, and `slvst.prg`.

## OpenAPI
Generate fresh schema:
```bash
python3 - <<'PY'
import json
from pathlib import Path
import sys
root = Path("../../../..").resolve()
if str(root) not in sys.path:
    sys.path.insert(0, str(root))
from services.punishment_api.app.main import app
schema = app.openapi()
Path(root / "openapi_punishment_api.json").write_text(
    json.dumps(schema, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print("done")
PY
```

## Input fields (FoxPro parity)
Provide these fields for accurate results (strings as in FoxPro forms):
- Date format for API input: `YYYY-MM-DD`
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
