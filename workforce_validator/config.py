from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "rules.json"
CONFIG_ENV_VAR = "WORKFORCE_VALIDATOR_CONFIG"

@dataclass(frozen=True)
class CalculationSettings:
    max_internal_break_hours: float
    weekly_hours_tolerance: float

@dataclass(frozen=True)
class RuleSettings:
    enabled: bool
    limit: float
    incident_type: str

@dataclass(frozen=True)
class ValidatorSettings:
    calculation: CalculationSettings
    max_consecutive_days: RuleSettings
    max_shift_hours: RuleSettings
    min_shift_hours: RuleSettings
    min_rest_hours: RuleSettings

def _number(value: Any, field: str, *, minimum: float = 0.0) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field} debe ser numerico, no booleano.")
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} debe ser numerico.") from exc
    if parsed < minimum:
        raise ValueError(f"{field} debe ser >= {minimum}.")
    return parsed

def _rule(data: dict[str, Any], name: str, *, integer_limit: bool = False) -> RuleSettings:
    raw = data.get(name)
    if not isinstance(raw, dict):
        raise ValueError(f"Falta la configuracion de la regla '{name}'.")
    enabled = raw.get("enabled")
    if not isinstance(enabled, bool):
        raise ValueError(f"rules.{name}.enabled debe ser true o false.")
    limit = _number(raw.get("limit"), f"rules.{name}.limit")
    if integer_limit and not limit.is_integer():
        raise ValueError(f"rules.{name}.limit debe ser un numero entero.")
    incident_type = raw.get("incident_type")
    if not isinstance(incident_type, str) or not incident_type.strip():
        raise ValueError(f"rules.{name}.incident_type debe ser texto no vacio.")
    return RuleSettings(enabled=enabled, limit=limit, incident_type=incident_type.strip())

def load_settings(path: str | Path | None = None) -> ValidatorSettings:
    resolved = Path(path or os.getenv(CONFIG_ENV_VAR) or DEFAULT_CONFIG_PATH)
    try:
        raw = json.loads(resolved.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"No se encontro la configuracion: {resolved}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Configuracion JSON no valida. Linea {exc.lineno}, columna {exc.colno}: {exc.msg}") from exc
    if not isinstance(raw, dict):
        raise ValueError("La configuracion debe tener un objeto JSON en la raiz.")
    calculation = raw.get("calculation")
    rules = raw.get("rules")
    if not isinstance(calculation, dict) or not isinstance(rules, dict):
        raise ValueError("La configuracion debe incluir 'calculation' y 'rules'.")
    return ValidatorSettings(
        calculation=CalculationSettings(
            max_internal_break_hours=_number(calculation.get("max_internal_break_hours"), "calculation.max_internal_break_hours"),
            weekly_hours_tolerance=_number(calculation.get("weekly_hours_tolerance"), "calculation.weekly_hours_tolerance"),
        ),
        max_consecutive_days=_rule(rules, "max_consecutive_days", integer_limit=True),
        max_shift_hours=_rule(rules, "max_shift_hours"),
        min_shift_hours=_rule(rules, "min_shift_hours"),
        min_rest_hours=_rule(rules, "min_rest_hours"),
    )

SETTINGS = load_settings()
