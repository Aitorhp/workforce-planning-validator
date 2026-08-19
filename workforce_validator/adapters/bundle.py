from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from workforce_validator.config import SETTINGS, ValidatorSettings
from workforce_validator.dates import month_key
from workforce_validator.io import parse_iso_datetime
from workforce_validator.models import AbsenceDay, CanonicalDataset, ShiftRow
from workforce_validator.schedule_sources import (
    validate_manual_filter,
    validate_schedule_source,
)


class BundleAdapter:
    """Adapter for the consolidated workforce-planning bundle payload."""

    def __init__(self, data: dict[str, Any], settings: ValidatorSettings = SETTINGS):
        self.data = data
        self.settings = settings
        self.store_id = self._store_id()
        self.people_by_id = self._people_index()

    def build_canonical_dataset(
        self,
        schedule_source: str,
        manual_edit_filter: str = "all",
    ) -> CanonicalDataset:
        schedule_source = validate_schedule_source(schedule_source)
        manual_edit_filter = validate_manual_filter(manual_edit_filter)
        if schedule_source != "plannedDraft":
            manual_edit_filter = "all"

        shifts: list[ShiftRow] = []
        absences: list[AbsenceDay] = []
        employee_months: dict[tuple[Any, Any, str], Any] = {}
        employee_presence_dates: dict[tuple[Any, Any], set[date]] = defaultdict(set)
        data_dates: set[date] = set()
        max_internal_break = timedelta(
            hours=self.settings.calculation.max_internal_break_hours
        )

        for store_day in self._store_day_times():
            operating_value = store_day.get("operatingDate")
            if not operating_value:
                continue
            operating_day = date.fromisoformat(str(operating_value)[:10])
            data_dates.add(operating_day)

            for person_day in store_day.get("people") or []:
                if not isinstance(person_day, dict):
                    continue
                person_id = person_day.get("personId")
                applicable_hours = self._applicable_hours(person_id, operating_day)
                employee_presence_dates[(self.store_id, person_id)].add(operating_day)
                employee_months[(self.store_id, person_id, month_key(operating_day))] = (
                    applicable_hours
                )

                day_times = person_day.get("dayTimes") or {}
                if not isinstance(day_times, dict):
                    day_times = {}
                self._append_absences(
                    absences, person_id, operating_day, day_times.get("absences") or []
                )

                selected_schedule = day_times.get(schedule_source) or []
                if not isinstance(selected_schedule, list):
                    selected_schedule = []
                if schedule_source == "plannedDraft" and not self._manual_matches(
                    day_times, manual_edit_filter
                ):
                    selected_schedule = []

                segments = []
                for segment in selected_schedule:
                    if (
                        not isinstance(segment, dict)
                        or str(segment.get("hourType", "")).upper() != "WORK"
                    ):
                        continue
                    start_value = segment.get("startDateTime")
                    end_value = segment.get("endDateTime")
                    if not start_value or not end_value:
                        continue
                    start_dt = parse_iso_datetime(start_value)
                    end_dt = parse_iso_datetime(end_value)
                    if end_dt <= start_dt:
                        raise ValueError(
                            "Segmento invalido en "
                            f"{schedule_source}: personId={person_id}, "
                            f"inicio={start_value}, fin={end_value}"
                        )
                    segments.append((start_dt, end_dt))

                if not segments:
                    continue
                segments.sort(key=lambda item: item[0])
                shift_start = segments[0][0]
                shift_end = max(end for _, end in segments)
                net_work = sum((end - start for start, end in segments), timedelta())
                break_duration = timedelta()
                previous_end = segments[0][1]
                for current_start, current_end in segments[1:]:
                    gap = current_start - previous_end
                    if timedelta(0) < gap <= max_internal_break:
                        break_duration += gap
                    if current_end > previous_end:
                        previous_end = current_end
                shifts.append(
                    ShiftRow(
                        self.store_id,
                        person_id,
                        applicable_hours,
                        operating_day,
                        shift_start,
                        shift_end,
                        round(net_work.total_seconds() / 3600, 4),
                        round(break_duration.total_seconds() / 3600, 4),
                    )
                )

        shifts.sort(key=lambda row: (str(row.store_id), str(row.person_id), row.work_day))
        absences.sort(
            key=lambda row: (str(row.store_id), str(row.person_id), row.absence_day)
        )
        return CanonicalDataset(
            shifts=shifts,
            absences=absences,
            employee_months=employee_months,
            employee_presence_dates=dict(employee_presence_dates),
            data_dates=data_dates,
            schedule_source=schedule_source,
            manual_edit_filter=manual_edit_filter,
        )

    def _store_id(self) -> Any:
        config = self.data.get("config") or {}
        store = config.get("store") or {}
        store_id = store.get("id")
        if store_id in (None, ""):
            raise ValueError("El bundle no contiene config.store.id.")
        return store_id

    def _store_day_times(self) -> list[dict[str, Any]]:
        times = self.data.get("times") or {}
        store_day_times = times.get("storeDayTimes") or []
        if not isinstance(store_day_times, list):
            raise ValueError("El bundle debe contener times.storeDayTimes como lista.")
        return store_day_times

    def _people_index(self) -> dict[Any, dict[str, Any]]:
        people_section = self.data.get("people") or {}
        people = people_section.get("data") or []
        if not isinstance(people, list):
            raise ValueError("El bundle debe contener people.data como lista.")
        result = {}
        for person in people:
            if not isinstance(person, dict):
                continue
            person_id = person.get("personId")
            if person_id not in (None, ""):
                result[person_id] = person
        return result

    def _applicable_hours(self, person_id: Any, operating_day: date) -> Any:
        person = self.people_by_id.get(person_id)
        if person is None:
            raise ValueError(
                f"personId={person_id!r} aparece en times pero no en people.data."
            )
        matching = []
        for period in person.get("employmentPeriods") or []:
            if not isinstance(period, dict):
                continue
            from_value = period.get("validFromDate")
            to_value = period.get("validToDate")
            valid_from = date.min if not from_value else date.fromisoformat(str(from_value)[:10])
            valid_to = date.max if not to_value else date.fromisoformat(str(to_value)[:10])
            if valid_from <= operating_day <= valid_to:
                matching.append(period)
        if len(matching) > 1:
            raise ValueError(
                f"personId={person_id!r} tiene varios employmentPeriods aplicables "
                f"en {operating_day.isoformat()}."
            )
        if not matching:
            return None
        return matching[0].get("applicableWorkingHours")

    @staticmethod
    def _manual_matches(day_times: dict[str, Any], manual_filter: str) -> bool:
        flag = day_times.get("plannedDraftManuallyEdited")
        if manual_filter == "edited":
            return flag is True
        if manual_filter == "not_edited":
            return flag is False
        return True

    def _append_absences(
        self,
        target: list[AbsenceDay],
        person_id: Any,
        operating_day: date,
        raw_absences: list[Any],
    ) -> None:
        seen_absences = set()
        for absence in raw_absences:
            if not isinstance(absence, dict):
                continue
            status = str(absence.get("status") or "").upper()
            if status not in {"VALIDATED", "APPROVED"}:
                continue
            type_data = absence.get("type") or {}
            absence_type = str(
                type_data.get("name")
                or type_data.get("description")
                or absence.get("id")
                or "AUSENCIA"
            )
            key = (absence_type, status)
            if key in seen_absences:
                continue
            seen_absences.add(key)
            target.append(
                AbsenceDay(
                    self.store_id,
                    person_id,
                    operating_day,
                    absence_type,
                    status,
                )
            )
