from __future__ import annotations

from copy import deepcopy
from datetime import date
from typing import Any, Sequence

from workforce_validator.dates import collect_data_dates


def _month_index(day: date) -> int:
    return day.year * 12 + day.month


def combine_planning_documents(documents: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Combina una o dos planificaciones mensuales compatibles.

    La función no altera los cálculos del validador. Únicamente construye una
    entrada equivalente a un único JSON, tras comprobar que los documentos
    pertenecen a la misma tienda, cubren meses consecutivos y no comparten
    ninguna fecha operativa.
    """
    items = list(documents)
    if not items:
        raise ValueError("Debe proporcionarse al menos una planificación.")
    if len(items) > 2:
        raise ValueError("Solo se admite un máximo de dos planificaciones.")

    inspected: list[tuple[date, date, dict[str, Any], set[date]]] = []
    store_ids: list[Any] = []

    for position, document in enumerate(items, start=1):
        if not isinstance(document, dict):
            raise ValueError(f"El fichero {position} no contiene un objeto JSON válido.")

        store_id = (document.get("store") or {}).get("id")
        if store_id in (None, ""):
            raise ValueError(f"No se ha podido identificar la tienda del fichero {position}.")
        store_ids.append(store_id)

        dates = collect_data_dates(document)
        if not dates:
            raise ValueError(f"El fichero {position} no contiene fechas en storeDayTimes.")

        months = {(day.year, day.month) for day in dates}
        if len(months) != 1:
            raise ValueError(
                f"El fichero {position} debe corresponder a un único mes calendario; "
                f"se han detectado {len(months)} meses."
            )

        inspected.append((min(dates), max(dates), document, dates))

    normalized_store_ids = {str(value) for value in store_ids}
    if len(normalized_store_ids) != 1:
        raise ValueError(
            "Los ficheros pertenecen a tiendas distintas: "
            + ", ".join(str(value) for value in store_ids)
            + "."
        )

    inspected.sort(key=lambda item: item[0])

    if len(inspected) == 2:
        first_start, first_end, _, first_dates = inspected[0]
        second_start, second_end, _, second_dates = inspected[1]
        overlap = sorted(first_dates & second_dates)
        if overlap:
            preview = ", ".join(day.isoformat() for day in overlap[:5])
            suffix = "..." if len(overlap) > 5 else ""
            raise ValueError(f"Los periodos se solapan en estas fechas: {preview}{suffix}")

        if _month_index(second_start) - _month_index(first_start) != 1:
            raise ValueError(
                "Los ficheros deben corresponder a meses consecutivos. "
                f"Se han detectado {first_start:%Y-%m} y {second_start:%Y-%m}."
            )

        if first_end >= second_start:
            raise ValueError("El segundo periodo debe comenzar después de finalizar el primero.")

    combined = deepcopy(inspected[0][2])
    combined_days: list[dict[str, Any]] = []
    for _, _, document, _ in inspected:
        days = document.get("storeDayTimes") or []
        if not isinstance(days, list):
            raise ValueError("El campo 'storeDayTimes' debe ser una lista en todos los ficheros.")
        combined_days.extend(deepcopy(days))

    combined_days.sort(key=lambda item: str(item.get("operatingDate", "")) if isinstance(item, dict) else "")
    combined["storeDayTimes"] = combined_days
    return combined
