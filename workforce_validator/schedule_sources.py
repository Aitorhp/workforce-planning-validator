from __future__ import annotations

from copy import deepcopy
from datetime import date
from typing import Any

SCHEDULE_SOURCES = {"planned": "Plan publicado", "plannedDraft": "Borrador del planificador"}
MANUAL_EDIT_FILTERS = {"all": "Todos los borradores", "edited": "Solo borradores editados manualmente", "not_edited": "Solo borradores no editados manualmente"}


class SourceDetection(dict):
    """Resultado rico compatible con la interfaz Streamlit anterior.

    El acceso por clave expone ``sources`` y ``manual_edit``, mientras que
    ``items()`` itera directamente por los origenes para mantener la
    compatibilidad con ``app.py``.

    Streamlit serializa los resultados de ``st.cache_data``. Durante la
    reconstruccion de un ``dict`` personalizado, Python puede invocar
    ``items()`` antes de haber restaurado la clave ``sources``. En ese estado
    transitorio se delega en la implementacion nativa de ``dict``.

    ``__reduce__`` fuerza ademas que la serializacion conserve las claves reales
    del objeto (``sources`` y ``manual_edit``), en lugar de la vista aplanada que
    ofrece ``items()`` a la interfaz.
    """

    def items(self):
        sources = dict.get(self, "sources")
        if sources is None:
            return dict.items(self)
        return sources.items()

    def __reduce__(self):
        return (type(self), (), None, None, iter(dict.items(self)))


def validate_schedule_source(schedule_source: str) -> str:
    if schedule_source not in SCHEDULE_SOURCES:
        raise ValueError(f"Origen de horarios no valido: {schedule_source!r}. Valores: {', '.join(SCHEDULE_SOURCES)}")
    return schedule_source


def validate_manual_filter(manual_filter: str) -> str:
    if manual_filter not in MANUAL_EDIT_FILTERS:
        raise ValueError(f"Filtro manual no valido: {manual_filter!r}. Valores: {', '.join(MANUAL_EDIT_FILTERS)}")
    return manual_filter


def _is_work(segment: Any) -> bool:
    return isinstance(segment, dict) and str(segment.get("hourType", "")).upper() == "WORK"


def _matches(day_times: dict[str, Any], manual_filter: str) -> bool:
    flag = day_times.get("plannedDraftManuallyEdited")
    if manual_filter == "edited":
        return flag is True
    if manual_filter == "not_edited":
        return flag is False
    return True


def detect_schedule_sources(data: dict[str, Any]) -> SourceDetection:
    sources = {key: {"person_days": 0, "segments": 0, "work_segments": 0, "dates": set()} for key in SCHEDULE_SOURCES}
    manual = {"true_person_days": 0, "false_person_days": 0, "missing_person_days": 0}
    for store_day in data.get("storeDayTimes") or []:
        if not isinstance(store_day, dict):
            continue
        value = store_day.get("operatingDate")
        operating_day = date.fromisoformat(str(value)[:10]) if value else None
        for person_day in store_day.get("people") or []:
            if not isinstance(person_day, dict):
                continue
            day_times = person_day.get("dayTimes") or {}
            if not isinstance(day_times, dict):
                continue
            flag = day_times.get("plannedDraftManuallyEdited")
            if flag is True:
                manual["true_person_days"] += 1
            elif flag is False:
                manual["false_person_days"] += 1
            else:
                manual["missing_person_days"] += 1
            for source in SCHEDULE_SOURCES:
                segments = day_times.get(source)
                if not isinstance(segments, list) or not segments:
                    continue
                work_count = sum(_is_work(segment) for segment in segments)
                sources[source]["person_days"] += 1
                sources[source]["segments"] += len(segments)
                sources[source]["work_segments"] += work_count
                if operating_day and work_count:
                    sources[source]["dates"].add(operating_day)
    for stats in sources.values():
        dates = sorted(stats.pop("dates"))
        stats["date_count"] = len(dates)
        stats["first_date"] = dates[0] if dates else None
        stats["last_date"] = dates[-1] if dates else None
    return SourceDetection(sources=sources, manual_edit=manual)


def filter_schedule_data(data: dict[str, Any], schedule_source: str, manual_filter: str = "all"):
    validate_schedule_source(schedule_source)
    validate_manual_filter(manual_filter)
    if schedule_source != "plannedDraft":
        manual_filter = "all"
    filtered = deepcopy(data)
    if schedule_source != "plannedDraft" or manual_filter == "all":
        return filtered, manual_filter
    for store_day in filtered.get("storeDayTimes") or []:
        if not isinstance(store_day, dict):
            continue
        for person_day in store_day.get("people") or []:
            if not isinstance(person_day, dict):
                continue
            day_times = person_day.get("dayTimes") or {}
            if isinstance(day_times, dict) and not _matches(day_times, manual_filter):
                day_times["plannedDraft"] = []
    return filtered, manual_filter
