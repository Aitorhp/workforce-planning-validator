import pandas as pd

from review_iteration_dashboard import (
    active_planning_week_starts,
    apply_weekend_rule_thresholds,
    build_contract_lookup,
    restrict_to_active_planning_weeks,
)


def test_empty_weeks_are_removed_from_week_and_absence_views():
    shifts = pd.DataFrame([
        {"id_tienda": 1, "personId": "A", "day": "2026-08-03", "horas_totales": 8, "applicableWorkingHours": 40},
        {"id_tienda": 1, "personId": "B", "day": "2026-08-10", "horas_totales": 6, "applicableWorkingHours": 20},
        {"id_tienda": 1, "personId": "A", "day": "2026-08-17", "horas_totales": 0, "applicableWorkingHours": 40},
    ])
    weekly = pd.DataFrame([
        {"id_tienda": 1, "personId": "A", "inicio_semana": "2026-08-03", "applicableWorkingHours": 40},
        {"id_tienda": 1, "personId": "B", "inicio_semana": "2026-08-10", "applicableWorkingHours": 20},
        {"id_tienda": 1, "personId": "A", "inicio_semana": "2026-08-17", "applicableWorkingHours": 40},
    ])
    absences = pd.DataFrame([
        {"id_tienda": 1, "personId": "A", "fecha": "2026-08-18"},
        {"id_tienda": 1, "personId": "B", "fecha": "2026-08-11"},
    ])
    frames = {"shifts": shifts, "weekly": weekly, "absences": absences, "absence_daily": pd.DataFrame()}

    active = active_planning_week_starts(shifts)
    filtered, active_dates = restrict_to_active_planning_weeks(frames, pd.date_range("2026-08-03", "2026-08-23"))

    assert [value.strftime("%Y-%m-%d") for value in active] == ["2026-08-03", "2026-08-10"]
    assert filtered["weekly"]["inicio_semana"].tolist() == ["2026-08-03", "2026-08-10"]
    assert filtered["absences"]["fecha"].tolist() == ["2026-08-11"]
    assert max(pd.Timestamp(value) for value in active_dates) == pd.Timestamp("2026-08-16")


def test_contract_lookup_prefers_latest_weekly_contract():
    frames = {
        "summaries": pd.DataFrame([
            {"id_tienda": 1, "personId": "A", "mes": "2026-08", "applicableWorkingHours": 30},
        ]),
        "shifts": pd.DataFrame([
            {"id_tienda": 1, "personId": "A", "day": "2026-08-03", "applicableWorkingHours": 35},
        ]),
        "weekly": pd.DataFrame([
            {"id_tienda": 1, "personId": "A", "inicio_semana": "2026-08-03", "applicableWorkingHours": 35},
            {"id_tienda": 1, "personId": "A", "inicio_semana": "2026-08-10", "applicableWorkingHours": 40},
        ]),
    }
    assert build_contract_lookup(frames)[('1', 'A')] == 40


def test_weekend_thresholds_are_independent_and_zero_disables_rule():
    employees = pd.DataFrame([
        {"personId": "A", "fines_semana_libres": 0, "sabados_libres": 2, "domingos_libres": 0},
        {"personId": "B", "fines_semana_libres": 2, "sabados_libres": 0, "domingos_libres": 1},
    ])
    result = apply_weekend_rule_thresholds(employees, 1, 2, 0)
    a = result.set_index("personId").loc["A"]
    b = result.set_index("personId").loc["B"]
    assert bool(a["incumple_fin_semana"]) is True
    assert bool(a["incumple_sabado"]) is False
    assert bool(a["incumple_domingo"]) is False
    assert bool(b["incumple_fin_semana"]) is False
    assert bool(b["incumple_sabado"]) is True
    assert bool(b["incumple_domingo"]) is False
