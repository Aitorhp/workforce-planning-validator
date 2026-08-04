from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping


def _normalise_contract(value: Any) -> tuple[str, float | None]:
    if value in (None, ""):
        return "SIN INFORMAR", None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value).strip(), None
    return f"{numeric:g}", numeric


def analyze_contract_changes(
    employee_months: Mapping[tuple[Any, Any, str], Any],
) -> list[dict[str, Any]]:
    """Localiza empleados cuyo applicableWorkingHours cambia entre meses."""
    grouped: dict[tuple[Any, Any], list[tuple[str, Any]]] = defaultdict(list)
    for (store_id, person_id, month), value in employee_months.items():
        grouped[(store_id, person_id)].append((month, value))

    rows: list[dict[str, Any]] = []
    for (store_id, person_id), entries in sorted(
        grouped.items(), key=lambda item: (str(item[0][0]), str(item[0][1]))
    ):
        entries.sort(key=lambda item: item[0])
        normalised = [(month, *_normalise_contract(value)) for month, value in entries]
        distinct = {text for _, text, _ in normalised}
        if len(normalised) < 2 or len(distinct) <= 1:
            continue
        first_month, first_text, first_numeric = normalised[0]
        last_month, last_text, last_numeric = normalised[-1]
        variation = (
            round(last_numeric - first_numeric, 4)
            if first_numeric is not None and last_numeric is not None
            else None
        )
        rows.append(
            {
                "id_tienda": store_id,
                "personId": person_id,
                "mes_anterior": first_month,
                "horas_mes_anterior": first_numeric if first_numeric is not None else first_text,
                "mes_posterior": last_month,
                "horas_mes_posterior": last_numeric if last_numeric is not None else last_text,
                "variacion_horas": variation,
                "detalle_contrato": "; ".join(
                    f"{month}: {text} h" for month, text, _ in normalised
                ),
                "requiere_revision": "SI",
            }
        )
    return rows
