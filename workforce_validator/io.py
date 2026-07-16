from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def parse_iso_datetime(value: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Fecha no valida: {value!r}")
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    return datetime.fromisoformat(normalized).replace(tzinfo=None)


def load_json_bytes(file_bytes: bytes) -> dict[str, Any]:
    try:
        text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("El fichero no esta codificado en UTF-8.") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"JSON no valido. Linea {exc.lineno}, columna {exc.colno}: {exc.msg}"
        ) from exc
    if not isinstance(data, dict):
        raise ValueError("La raiz del JSON debe ser un objeto.")
    return data


def load_json_path(path: Path) -> dict[str, Any]:
    return load_json_bytes(path.read_bytes())
