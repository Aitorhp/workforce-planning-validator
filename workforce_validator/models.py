from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any


@dataclass(frozen=True)
class ShiftRow:
    store_id: Any
    person_id: Any
    applicable_working_hours: Any
    work_day: date
    shift_start: datetime
    shift_end: datetime
    worked_hours: float
    break_hours: float


@dataclass(frozen=True)
class AbsenceDay:
    store_id: Any
    person_id: Any
    absence_day: date
    absence_type: str
    absence_status: str


@dataclass(frozen=True)
class Incident:
    store_id: Any
    person_id: Any
    month: str
    incident_type: str
    start_date: date
    end_date: date
    observed_value: float
    limit_text: str
    detail: str


@dataclass
class CanonicalDataset:
    shifts: list[ShiftRow]
    absences: list[AbsenceDay]
    employee_months: dict[tuple[Any, Any, str], Any]
    employee_presence_dates: dict[tuple[Any, Any], set[date]]
    data_dates: set[date]
    schedule_source: str
    manual_edit_filter: str = "all"


@dataclass
class ValidationResult:
    source_data: dict[str, Any]
    schedule_source: str
    shifts: list[ShiftRow]
    employee_months: dict[tuple[Any, Any, str], Any]
    absences: list[AbsenceDay]
    employee_presence_dates: dict[tuple[Any, Any], set[date]]
    summaries: list[dict[str, Any]]
    incidents: list[Incident]
    weekly_rows: list[dict[str, Any]]
    data_dates: set[date]
    manual_edit_filter: str = "all"
