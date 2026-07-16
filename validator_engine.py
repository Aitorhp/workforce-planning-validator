"""Fachada de compatibilidad para la aplicacion existente.

La logica productiva vive en el paquete ``workforce_validator``. Este modulo
mantiene los imports publicos utilizados por app.py y por integraciones previas.
"""
from __future__ import annotations

from datetime import timedelta

from workforce_validator.config import SETTINGS, ValidatorSettings, load_settings
from workforce_validator.dataframes import result_dataframes
from workforce_validator.dates import (
    collect_data_dates,
    daterange,
    find_consecutive_streaks,
    month_key,
    week_start,
    weekend_counts,
)
from workforce_validator.engine import run_validation
from workforce_validator.excel import build_excel_bytes
from workforce_validator.extraction import extract_data
from workforce_validator.io import load_json_bytes, load_json_path, parse_iso_datetime
from workforce_validator.models import AbsenceDay, Incident, ShiftRow, ValidationResult
from workforce_validator.schedule_sources import (
    MANUAL_EDIT_FILTERS,
    SCHEDULE_SOURCES,
    detect_schedule_sources,
    validate_schedule_source,
)
from workforce_validator.summary import analyze_shifts
from workforce_validator.weekly_hours import analyze_weekly_hours

MAX_INTERNAL_BREAK = timedelta(hours=SETTINGS.calculation.max_internal_break_hours)
MAX_CONSECUTIVE_DAYS = int(SETTINGS.max_consecutive_days.limit)
MAX_SHIFT_HOURS = SETTINGS.max_shift_hours.limit
MIN_SHIFT_HOURS = SETTINGS.min_shift_hours.limit
MIN_REST_HOURS = SETTINGS.min_rest_hours.limit
WEEKLY_HOURS_TOLERANCE = SETTINGS.calculation.weekly_hours_tolerance

__all__ = [
    "AbsenceDay", "Incident", "ShiftRow", "ValidationResult",
    "ValidatorSettings", "SETTINGS", "MAX_INTERNAL_BREAK",
    "MAX_CONSECUTIVE_DAYS", "MAX_SHIFT_HOURS", "MIN_SHIFT_HOURS",
    "MIN_REST_HOURS", "WEEKLY_HOURS_TOLERANCE", "SCHEDULE_SOURCES",
    "MANUAL_EDIT_FILTERS", "load_settings", "parse_iso_datetime",
    "load_json_bytes", "load_json_path", "detect_schedule_sources",
    "validate_schedule_source", "month_key", "extract_data", "daterange",
    "find_consecutive_streaks", "weekend_counts", "week_start",
    "analyze_weekly_hours", "analyze_shifts", "collect_data_dates",
    "run_validation", "result_dataframes", "build_excel_bytes",
]
