from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pandas as pd

from workforce_validator.html_report import build_html_report, build_weekend_map_component


def sample_frames():
    shifts = pd.DataFrame([
        {
            "id_tienda": 3394,
            "personId": "E1",
            "applicableWorkingHours": 40,
            "day": pd.Timestamp("2026-08-01"),
            "horas_totales": 8.0,
        }
    ])
    summaries = pd.DataFrame([
        {
            "id_tienda": 3394,
            "personId": "E1",
            "applicableWorkingHours": 40,
            "mes": "2026-08",
            "cumple_todas_las_reglas": "SI",
            "fines_semana_completos_libres": 4,
            "sabados_libres": 4,
            "domingos_libres": 5,
        }
    ])
    weekly = pd.DataFrame([
        {
            "id_tienda": 3394,
            "personId": "E1",
            "applicableWorkingHours": 40,
            "ano_iso": 2026,
            "semana_iso": 31,
            "inicio_semana": pd.Timestamp("2026-07-27"),
            "fin_semana": pd.Timestamp("2026-08-02"),
            "horas_planificadas": 8.0,
            "horas_no_planificadas_hasta_contrato": 32.0,
            "horas_planificadas_en_exceso": 0.0,
            "horas_potenciales_asociadas_ausencia": 0.0,
        }
    ])
    return {
        "shifts": shifts,
        "summaries": summaries,
        "weekly": weekly,
        "incidents": pd.DataFrame(),
        "absences": pd.DataFrame(),
        "shift_balance": pd.DataFrame(),
        "absence_daily": pd.DataFrame(),
    }


def test_builds_self_contained_bilingual_html_report():
    dates = {date(2026, 8, day) for day in range(1, 32)}
    result = SimpleNamespace(source_data={"store": {"id": 3394}}, data_dates=dates)

    report = build_html_report(
        result,
        sample_frames(),
        "Plan publicado",
        file_names=["agosto.json"],
    ).decode("utf-8")

    assert "<!doctype html>" in report.lower()
    assert 'data-language="es"' in report
    assert 'data-language="en"' in report
    assert "Resumen" in report
    assert "Overview" in report
    assert "weekend-search" in report
    assert "employee-col" in report
    assert "plotly" in report.lower()


def test_weekend_component_has_filters_and_fixed_columns():
    weekends = pd.DataFrame([
        {
            "id_tienda": 3394,
            "personId": "E1",
            "applicableWorkingHours": 40,
            "inicio_fin_semana": pd.Timestamp("2026-08-01"),
            "Fin de semana": "01/08 - 02/08",
            "sabado_libre": True,
            "domingo_libre": False,
        }
    ])

    component = build_weekend_map_component(weekends, language="es")

    assert "weekend-search" in component
    assert "weekend-alerts" in component
    assert "position:sticky" in component
    assert "3394 · E1 · 40 h" in component
