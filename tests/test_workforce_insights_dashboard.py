import pandas as pd

from workforce_insights_dashboard import (
    OLD_WEEKEND_ROTATION,
    apply_workforce_insights_support,
    prepare_workforce_mix,
)


def test_prepare_workforce_mix_counts_each_employee_once_and_builds_percentages():
    weekly = pd.DataFrame([
        {"id_tienda": 1, "personId": "A", "applicableWorkingHours": 40, "inicio_semana": "2026-08-03"},
        {"id_tienda": 1, "personId": "A", "applicableWorkingHours": 40, "inicio_semana": "2026-08-10"},
        {"id_tienda": 1, "personId": "B", "applicableWorkingHours": 20, "inicio_semana": "2026-08-03"},
        {"id_tienda": 1, "personId": "C", "applicableWorkingHours": 20, "inicio_semana": "2026-08-03"},
        {"id_tienda": 2, "personId": "D", "applicableWorkingHours": 30, "inicio_semana": "2026-08-03"},
    ])

    employees, mix = prepare_workforce_mix(weekly)

    assert len(employees) == 4
    assert mix.set_index("applicableWorkingHours")["Empleados"].to_dict() == {20: 2, 30: 1, 40: 1}
    assert round(float(mix["Porcentaje plantilla"].sum()), 8) == 100.0
    assert round(float(mix["Porcentaje horas"].sum()), 8) == 100.0


def test_prepare_workforce_mix_uses_latest_contract_and_store_filter():
    weekly = pd.DataFrame([
        {"id_tienda": 1, "personId": "A", "applicableWorkingHours": 30, "inicio_semana": "2026-08-03"},
        {"id_tienda": 1, "personId": "A", "applicableWorkingHours": 35, "inicio_semana": "2026-08-10"},
        {"id_tienda": 2, "personId": "B", "applicableWorkingHours": 20, "inicio_semana": "2026-08-10"},
    ])

    employees, mix = prepare_workforce_mix(weekly, store_id="1")

    assert len(employees) == 1
    assert employees.iloc[0]["applicableWorkingHours"] == 35
    assert mix.iloc[0]["Empleados"] == 1


def test_source_patch_adds_mix_tab_and_compact_weekend_percentage_chart():
    source = (
        "from validator_engine import (\n    x,\n)\n"
        "def placeholder():\n"
        + OLD_WEEKEND_ROTATION
        + "\ndef render_weekends(frames, data_dates):\n    return 'weekends'\n\n"
        'tabs = st.tabs(["Resumen", "Restricciones", "Horas contractuales", "Cobertura diaria", "Balance mañana/tarde", "Ausencias", "Fines de semana", "Metodologia"])\n'
        "with tabs[6]: render_weekends(frames, filtered_data_dates)\n"
        "with tabs[7]: render_methodology()\n"
    )

    patched = apply_workforce_insights_support(source)

    assert "height=255" in patched
    assert "porcentaje_plantilla" in patched
    assert "def render_workforce_mix(frames):" in patched
    assert '"Mix de plantilla"' in patched
    assert "with tabs[7]: render_workforce_mix(frames)" in patched
    assert "with tabs[8]: render_methodology()" in patched
    compile(patched, "synthetic_dashboard.py", "exec")
