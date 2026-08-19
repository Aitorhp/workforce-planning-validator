from __future__ import annotations

from typing import Any
from workforce_validator.config import SETTINGS, ValidatorSettings
from workforce_validator.dates import collect_data_dates
from workforce_validator.extraction import extract_data
from workforce_validator.models import CanonicalDataset, ValidationResult
from workforce_validator.schedule_sources import filter_schedule_data
from workforce_validator.summary import analyze_shifts
from workforce_validator.weekly_hours import analyze_weekly_hours


def run_canonical_validation(
    dataset: CanonicalDataset,
    source_data: dict[str, Any] | None = None,
    settings: ValidatorSettings = SETTINGS,
) -> ValidationResult:
    """Run the unchanged business engine over an already-normalized dataset."""
    summaries, incidents = analyze_shifts(dataset.shifts, dataset.employee_months, settings)
    weekly = analyze_weekly_hours(
        dataset.shifts,
        dataset.employee_months,
        dataset.data_dates,
        dataset.absences,
        dataset.employee_presence_dates,
        settings,
    )
    return ValidationResult(
        source_data or {},
        dataset.schedule_source,
        dataset.shifts,
        dataset.employee_months,
        dataset.absences,
        dataset.employee_presence_dates,
        summaries,
        incidents,
        weekly,
        dataset.data_dates,
        dataset.manual_edit_filter,
    )


def run_validation(
    data: dict[str, Any],
    schedule_source: str = "plannedDraft",
    manual_edit_filter: str = "all",
    settings: ValidatorSettings = SETTINGS,
) -> ValidationResult:
    filtered, effective_filter = filter_schedule_data(data, schedule_source, manual_edit_filter)
    shifts, employee_months, absences, presence = extract_data(filtered, schedule_source, settings)
    summaries, incidents = analyze_shifts(shifts, employee_months, settings)
    dates = collect_data_dates(filtered)
    weekly = analyze_weekly_hours(shifts, employee_months, dates, absences, presence, settings)
    return ValidationResult(
        filtered, schedule_source, shifts, employee_months, absences, presence,
        summaries, incidents, weekly, dates, effective_filter,
    )
