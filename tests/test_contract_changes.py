from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd

from workforce_validator.config import SETTINGS
from workforce_validator.contracts import analyze_contract_changes
from workforce_validator.models import ShiftRow
from workforce_validator.reporting import build_html_report, build_shift_balance_dataframe
from workforce_validator.weekly_hours import analyze_weekly_hours


def test_contract_changes_only_returns_employees_with_different_values():
    rows = analyze_contract_changes({
        (14947, "E1", "2026-08"): 30,
        (14947, "E1", "2026-09"): 40,
        (14947, "E2", "2026-08"): 20,
        (14947, "E2", "2026-09"): 20,
    })
    assert len(rows) == 1
    assert rows[0]["personId"] == "E1"
    assert rows[0]["variacion_horas"] == 10.0
    assert rows[0]["requiere_revision"] == "SI"


def test_week_crossing_contract_change_is_not_evaluated_arbitrarily():
    data_dates = {date(2026, 8, 31) + timedelta(days=index) for index in range(7)}
    start = datetime(2026, 8, 31, 9, 0)
    shifts = [
        ShiftRow(14947, "E1", 30 if index == 0 else 40, day, start + timedelta(days=index), start + timedelta(days=index, hours=6), 6.0, 0.0)
        for index, day in enumerate(sorted(data_dates))
    ]
    rows = analyze_weekly_hours(
        shifts,
        {
            (14947, "E1", "2026-08"): 30,
            (14947, "E1", "2026-09"): 40,
        },
        data_dates,
        [],
        {(14947, "E1"): data_dates},
        SETTINGS,
    )
    assert len(rows) == 1
    assert rows[0]["estado_planificacion"] == "CAMBIO CONTRATO"
    assert rows[0]["applicableWorkingHours"] is None
    assert "2026-08: 30" in rows[0]["detalle_contrato_semana"]
    assert "2026-09: 40" in rows[0]["detalle_contrato_semana"]


def test_streamlit_and_html_share_three_band_calculation():
    shifts = pd.DataFrame([
        {"id_tienda":14947,"personId":"E1","hora_inicio":pd.Timestamp("2026-08-03 09:00"),"horas_totales":6.0,"day":pd.Timestamp("2026-08-03")},
        {"id_tienda":14947,"personId":"E1","hora_inicio":pd.Timestamp("2026-08-04 12:00"),"horas_totales":6.0,"day":pd.Timestamp("2026-08-04")},
        {"id_tienda":14947,"personId":"E1","hora_inicio":pd.Timestamp("2026-08-05 15:00"),"horas_totales":6.0,"day":pd.Timestamp("2026-08-05")},
    ])
    balance = build_shift_balance_dataframe(
        shifts,
        datetime.strptime("11:00", "%H:%M").time(),
        datetime.strptime("14:00", "%H:%M").time(),
        1,
    )
    assert balance.iloc[0]["turnos_manana"] == 1
    assert balance.iloc[0]["turnos_central"] == 1
    assert balance.iloc[0]["turnos_tarde"] == 1

    changes = pd.DataFrame(analyze_contract_changes({
        (14947, "E1", "2026-08"): 30,
        (14947, "E1", "2026-09"): 40,
    }))
    html = build_html_report(
        {"shifts": shifts, "contract_changes": changes, "absence_daily": pd.DataFrame()},
        14947,
        "plannedDraft",
        datetime.strptime("11:00", "%H:%M").time(),
        datetime.strptime("14:00", "%H:%M").time(),
        date(2026, 8, 1),
        date(2026, 9, 30),
    ).decode("utf-8")
    assert "Cambios de horas contractuales entre meses" in html
    assert "Balance mañana / central / tarde" in html
    assert "11:00" in html and "14:00" in html
