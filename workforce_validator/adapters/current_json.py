from __future__ import annotations

from typing import Any

from workforce_validator.config import SETTINGS, ValidatorSettings
from workforce_validator.dates import collect_data_dates
from workforce_validator.extraction import extract_data
from workforce_validator.models import CanonicalDataset
from workforce_validator.schedule_sources import filter_schedule_data


class CurrentJsonAdapter:
    """Translate the current storeDayTimes JSON into the canonical contract.

    This adapter intentionally delegates to the existing source filtering and
    extraction functions so it can be used as a Golden Master bridge without
    changing any current parsing semantics.
    """

    def __init__(self, data: dict[str, Any], settings: ValidatorSettings = SETTINGS):
        self.data = data
        self.settings = settings

    def build_canonical_dataset(
        self,
        schedule_source: str,
        manual_edit_filter: str = "all",
    ) -> CanonicalDataset:
        filtered, effective_filter = filter_schedule_data(
            self.data, schedule_source, manual_edit_filter
        )
        shifts, employee_months, absences, presence = extract_data(
            filtered, schedule_source, self.settings
        )
        return CanonicalDataset(
            shifts=shifts,
            absences=absences,
            employee_months=employee_months,
            employee_presence_dates=dict(presence),
            data_dates=collect_data_dates(filtered),
            schedule_source=schedule_source,
            manual_edit_filter=effective_filter,
        )
