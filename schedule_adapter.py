"""Compatibilidad con la entrada Streamlit y fuentes de planificacion."""
from __future__ import annotations

from workforce_validator.config import SETTINGS
from workforce_validator.dataframes import result_dataframes
from workforce_validator.excel import build_excel_bytes
from workforce_validator.input_sources import (
    combine_planning_inputs as combine_planning_documents,
    detect_input_schedule_sources as detect_schedule_sources,
    run_input_validation as run_validation,
)
from workforce_validator.io import load_json_bytes
from workforce_validator.schedule_sources import MANUAL_EDIT_FILTERS, SCHEDULE_SOURCES

MAX_CONSECUTIVE_DAYS = int(SETTINGS.max_consecutive_days.limit)
MAX_SHIFT_HOURS = SETTINGS.max_shift_hours.limit
MIN_REST_HOURS = SETTINGS.min_rest_hours.limit
MIN_SHIFT_HOURS = SETTINGS.min_shift_hours.limit

__all__ = [
    "MAX_CONSECUTIVE_DAYS", "MAX_SHIFT_HOURS", "MIN_REST_HOURS",
    "MIN_SHIFT_HOURS", "SCHEDULE_SOURCES", "MANUAL_EDIT_FILTERS",
    "load_json_bytes", "combine_planning_documents", "result_dataframes",
    "build_excel_bytes", "detect_schedule_sources", "run_validation",
]
