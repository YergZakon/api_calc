"""Загрузка и кеширование справочника УК из TXT-файла."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from threading import Lock
from typing import Optional


@dataclass(frozen=True)
class ArticleRecord:
    """Запись санкции по статье/части с полями, эквивалентными колонкам справочника."""
    article_code: str
    hard: str
    prest: str
    fs1r64: str
    fs1r64_nn: str
    fs1r64_05n: str
    fs1r64_05x: str
    fs1r64_06n: str
    fs1r64_06x: str
    fs1r64_09n: str
    fs1r64_09x: str
    fs1r64_12n: str
    fs1r64_12x: str
    fs1r64_11n: str
    fs1r64_11x: str
    fs1r64_01n: str
    fs1r64_01x: str
    fs1r65_o: str
    fs1r65_n: str
    fs1r65_02n: str
    fs1r65_02x: str
    fl1u: str
    d_izm: Optional[date]


class ReferenceService:
    """Сервис доступа к справочнику: чтение, декодирование, выбор записи по дате."""
    ENCODING_FIXES = {
        "8A:;NG5=0": "Исключена",
        "8A:;NG5=": "Исключен",
        "(8A:;NG5=0)": "(Исключена)",
        "(8A:;NG5=)": "(Исключен)",
    }

    def __init__(self, file_path: Optional[str] = None):
        """Инициализирует сервис и лениво подготавливает внутренний кеш записей."""
        self._lock = Lock()
        self._file_path = Path(file_path) if file_path else None
        self._records: dict[str, list[ArticleRecord]] = {}
        self._loaded = False
        self._source = "unknown"
        self._ensure_loaded()

    def _ensure_loaded(self) -> None:
        """Гарантирует однократную загрузку справочника в память."""
        with self._lock:
            if self._loaded:
                return
            self._load_from_file()
            self._loaded = True
            self._source = "file"

    def reload(self) -> None:
        """Сбрасывает кеш и повторно загружает справочник из файла."""
        with self._lock:
            self._records = {}
            self._loaded = False
            self._ensure_loaded()

    @property
    def source(self) -> str:
        """Источник данных справочника (например, `file`)."""
        return self._source

    @property
    def file_path(self) -> str:
        """Путь к файлу справочника, используемому сервисом."""
        if self._file_path:
            return str(self._file_path)
        return "(default)"

    @property
    def count(self) -> int:
        """Количество загруженных записей справочника."""
        self._ensure_loaded()
        return sum(len(v) for v in self._records.values())

    def get_by_code(self, code: str, crime_date: date) -> Optional[ArticleRecord]:
        """Возвращает запись статьи, актуальную на дату преступления."""
        self._ensure_loaded()
        records = self._records.get(code or "")
        if not records:
            return None
        # Choose record with max d_izm <= crime_date, falling back to earliest
        best = None
        best_date = None
        for rec in records:
            rec_date = rec.d_izm or date.min
            if rec_date <= crime_date:
                if best is None or rec_date > best_date:
                    best = rec
                    best_date = rec_date
        if best is not None:
            return best
        return records[0]

    def _get_file_path(self) -> Path:
        """Возвращает явный путь к справочнику или путь по умолчанию."""
        if self._file_path:
            return self._file_path
        # Default: repo root file
        return Path(__file__).resolve().parents[2] / "справочник_УК_обновленный_2025_06_07_1.txt"

    def _load_from_file(self) -> None:
        """Читает и парсит справочник из TXT-файла."""
        file_path = self._get_file_path()
        if not file_path.exists():
            return
        content = self._read_file(file_path)
        self._parse_content(content)

    def _read_file(self, file_path: Path) -> str:
        """Читает бинарный файл и декодирует строки/поля в текст UTF-8."""
        with open(file_path, "rb") as f:
            raw_data = f.read()

        lines = raw_data.split(b"\n")
        decoded_lines: list[str] = []
        for line_idx, line in enumerate(lines):
            line = line.rstrip(b"\r")
            fields = line.split(b"\t")
            decoded_fields = []
            for field_idx, field in enumerate(fields):
                if line_idx == 0:
                    decoded_fields.append(field.decode("ascii", errors="replace"))
                else:
                    decoded_fields.append(self._decode_field(field, field_idx))
            decoded_lines.append("\t".join(decoded_fields))

        content = "\n".join(decoded_lines)
        for broken, fixed in self.ENCODING_FIXES.items():
            content = content.replace(broken, fixed)
        return content

    def _decode_field(self, field: bytes, field_idx: int) -> str:
        """Декодирует поле строки с учётом типа колонки."""
        if not field:
            return ""
        if field_idx == 0:
            return self._decode_stat_field(field)
        if field_idx in {7, 8}:
            return self._decode_text_field(field)
        try:
            return field.decode("ascii")
        except UnicodeDecodeError:
            return field.decode("latin-1", errors="replace")

    def _decode_stat_field(self, field: bytes) -> str:
        """Восстанавливает кодировку поля `stat` с артикулом статьи."""
        restored = bytearray()
        for byte in field:
            if byte == 0x20 or byte == 0x2E or 0x30 <= byte <= 0x39:
                restored.append(byte)
            elif 0x21 <= byte <= 0x7E:
                new_byte = (byte + 0xB0) % 256
                if 0xC0 <= new_byte <= 0xFF or new_byte in (0xA8, 0xB8):
                    restored.append(new_byte)
                else:
                    restored.append(byte)
            else:
                restored.append(byte)
        try:
            return bytes(restored).decode("cp1251")
        except UnicodeDecodeError:
            return bytes(restored).decode("cp1251", errors="replace")

    def _decode_text_field(self, field: bytes) -> str:
        """Декодирует текстовые поля, сохранённые в сдвинутой кодировке."""
        restored = bytearray()
        for byte in field:
            if byte in (0x20, 0x09, 0x0A, 0x0D):
                restored.append(byte)
            else:
                restored.append((byte + 0xB0) % 256)
        try:
            return bytes(restored).decode("cp1251")
        except UnicodeDecodeError:
            return bytes(restored).decode("cp1251", errors="replace")

    def _parse_content(self, content: str) -> None:
        """Разбирает весь текст справочника на строки и записи."""
        lines = content.splitlines()
        if not lines:
            return
        header = [h.strip().lower() for h in lines[0].split("\t")]
        for line in lines[1:]:
            if not line.strip():
                continue
            self._parse_row(line, header)

    def _parse_row(self, line: str, header: list[str]) -> None:
        """Преобразует строку табличного справочника в `ArticleRecord`."""
        fields = line.split("\t")
        row = {col: (fields[i].strip() if i < len(fields) else "") for i, col in enumerate(header)}

        code = row.get("p2", "").strip()
        if not code:
            return

        record = ArticleRecord(
            article_code=code,
            hard=row.get("hard", "").strip(),
            prest=row.get("prest", "").strip(),
            fs1r64=row.get("fs1r64", "").strip(),
            fs1r64_nn=row.get("fs1r64_nn", "").strip(),
            fs1r64_05n=row.get("fs1r64_05n", "").strip(),
            fs1r64_05x=row.get("fs1r64_05x", "").strip(),
            fs1r64_06n=row.get("fs1r64_06n", "").strip(),
            fs1r64_06x=row.get("fs1r64_06x", "").strip(),
            fs1r64_09n=row.get("fs1r64_09n", "").strip(),
            fs1r64_09x=row.get("fs1r64_09x", "").strip(),
            fs1r64_12n=row.get("fs1r64_12n", "").strip(),
            fs1r64_12x=row.get("fs1r64_12x", "").strip(),
            fs1r64_11n=row.get("fs1r64_11n", "").strip(),
            fs1r64_11x=row.get("fs1r64_11x", "").strip(),
            fs1r64_01n=row.get("fs1r64_01n", "").strip(),
            fs1r64_01x=row.get("fs1r64_01x", "").strip(),
            fs1r65_o=row.get("fs1r65_o", "").strip(),
            fs1r65_n=row.get("fs1r65_n", "").strip(),
            fs1r65_02n=row.get("fs1r65_02n", "").strip(),
            fs1r65_02x=row.get("fs1r65_02x", "").strip(),
            fl1u=row.get("fl1u", "").strip(),
            d_izm=_parse_date(row.get("d_izm", "").strip()),
        )

        self._records.setdefault(code, []).append(record)


def _parse_date(value: str) -> Optional[date]:
    """Парсит дату формата `dd.mm.yyyy` из справочника."""
    if not value or value == "-" or value == "--":
        return None
    try:
        day, month, year = value.split(".")
        return date(int(year), int(month), int(day))
    except Exception:
        return None


_SERVICE: Optional[ReferenceService] = None


def get_reference_service() -> ReferenceService:
    """Возвращает singleton-экземпляр `ReferenceService` для приложения."""
    global _SERVICE
    if _SERVICE is None:
        ref_path = os.environ.get("REFERENCE_FILE_PATH")
        _SERVICE = ReferenceService(ref_path)
    return _SERVICE
