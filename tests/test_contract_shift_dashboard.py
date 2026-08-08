from datetime import time

import pandas as pd
import pytest

from contract_shift_dashboard import (
    apply_contract_shift_support,
    build_configurable_shift_balance,
    build_contract_change_table,
)


def test_contract_change_table_only_flags_consecutive_differences():
    summaries = pd.DataFrame([
        {"id_tienda": 1, "personId": "A", "mes": "2026-08", "applicableWorkingHours": 40},
        {"id_tienda": 1, "personId": "A", "mes": "2026-09", "applicableWorkingHours": 35},
        {"id_tienda": 1, "personId": "B", "mes": "2026-08", "applicableWorkingHours": 40},
        {"id_tienda": 1, "personId": "B", "mes": "2026-09", "applicableWorkingHours": 40},
        {"id_tienda": 1, "personId": "C", "mes": "2026-08", "applicableWorkingHours": 20},
        {"id_tienda": 1, "personId": "C", "mes": "2026-10", "applicableWorkingHours": 30},
    ])

    result = build_contract_change_table(summaries)

    assert result[["personId", "mes_anterior", "mes_siguiente"]].to_dict("records") == [
        {"personId": "A", "mes_anterior": "2026-08", "mes_siguiente": "2026-09"}
    ]
    assert result.iloc[0]["diferencia_horas"] == -5


def test_shift_boundaries_are_central_and_cutoffs_are_configurable():
    shifts = pd.DataFrame([
        {"id_tienda": 1, "personId": "A", "hora_inicio": "2026-08-01 10:59", "horas_totales": 5},
        {"id_tienda": 1, "personId": "A", "hora_inicio": "2026-08-02 11:00", "horas_totales": 6},
        {"id_tienda": 1, "personId": "A", "hora_inicio": "2026-08-03 14:00", "horas_totales": 7},
        {"id_tienda": 1, "personId": "A", "hora_inicio": "2026-08-04 14:01", "horas_totales": 4},
    ])

    result = build_configurable_shift_balance(
        shifts, time(11, 0), time(14, 0), weeks_in_scope=1
    ).iloc[0]

    assert result["turnos_manana"] == 1
    assert result["turnos_central"] == 2
    assert result["turnos_tarde"] == 1
    assert result["horas_central"] == 13
    assert result["franjas_cubiertas"] == 3


def test_invalid_cutoff_order_is_rejected():
    shifts = pd.DataFrame([
        {"id_tienda": 1, "personId": "A", "hora_inicio": "2026-08-01 10:00", "horas_totales": 5}
    ])
    with pytest.raises(ValueError, match="anterior"):
        build_configurable_shift_balance(shifts, time(15), time(14))


def test_dashboard_patch_injects_new_controls_and_compiles():
    source = '''
import pandas as pd
from validator_engine import (
    run_validation,
)
def render_weekly(frames):
    return None
def render_shift_balance(frames):
    return None
tabs = st.tabs(["Resumen", "Restricciones", "Horas contractuales", "Cobertura diaria", "Balance mañana/tarde", "Ausencias", "Fines de semana", "Metodologia"])
'''
    patched = apply_contract_shift_support(source)
    compile(patched, "app.py", "exec")
    assert "shift_balance_morning_cutoff" in patched
    assert "shift_balance_afternoon_cutoff" in patched
    assert "turnos_central" in patched
    assert "Cambios de horas contractuales" in patched
