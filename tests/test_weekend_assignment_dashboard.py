import pandas as pd

from weekend_assignment_dashboard import (
    _build_weekend_states,
    apply_weekend_assignment_support,
    evaluate_weekend_assignment,
)


def _states(free_days, start="2026-08-01", end="2026-08-31"):
    dates = pd.date_range(start, end)
    free = {pd.Timestamp(day) for day in free_days}
    shifts = pd.DataFrame([
        {"id_tienda": 1, "personId": "A", "day": day}
        for day in dates
        if day.weekday() in (5, 6) and day not in free
    ])
    return _build_weekend_states(shifts, 1, "A", dates, dates)


def test_saturday_rule_is_met_by_a_full_free_weekend():
    result = evaluate_weekend_assignment(
        _states(["2026-08-01", "2026-08-02"]), minimum_saturdays=1
    )
    assert result["incumple_alguna_regla"] is False


def test_two_flexible_days_can_come_from_one_full_weekend():
    weekend = _states(["2026-08-01", "2026-08-02"])
    result = evaluate_weekend_assignment(weekend, minimum_flexible_days=2)
    distinct = evaluate_weekend_assignment(
        weekend, minimum_flexible_days=2, distinct_flexible_weekends=True
    )
    assert result["incumple_alguna_regla"] is False
    assert distinct["incumple_sabado_o_domingo"] is True


def test_full_weekend_plus_two_flexible_days_accepts_two_full_weekends():
    result = evaluate_weekend_assignment(
        _states(["2026-08-01", "2026-08-02", "2026-08-08", "2026-08-09"]),
        minimum_full_weekends=1,
        minimum_flexible_days=2,
    )
    assert result["incumple_alguna_regla"] is False


def test_full_weekend_plus_flexible_days_accepts_separate_sat_and_sun():
    result = evaluate_weekend_assignment(
        _states(["2026-08-01", "2026-08-02", "2026-08-08", "2026-08-16"]),
        minimum_full_weekends=1,
        minimum_flexible_days=2,
    )
    assert result["incumple_alguna_regla"] is False


def test_combination_alert_when_same_days_would_need_reuse():
    result = evaluate_weekend_assignment(
        _states(["2026-08-01", "2026-08-02"]),
        minimum_full_weekends=1,
        minimum_saturdays=1,
    )
    assert result["incumple_fin_semana"] is False
    assert result["incumple_sabado"] is False
    assert result["incumple_combinacion"] is True
    assert result["incumple_alguna_regla"] is True


def test_different_days_of_same_weekend_can_satisfy_different_day_rules():
    result = evaluate_weekend_assignment(
        _states(["2026-08-01", "2026-08-02"]),
        minimum_saturdays=1,
        minimum_flexible_days=1,
    )
    assert result["incumple_alguna_regla"] is False


def test_source_patch_replaces_only_weekend_renderer():
    tabs = 'tabs = st.tabs(["Resumen", "Restricciones", "Horas contractuales", "Cobertura diaria", "Balance mañana/tarde", "Ausencias", "Fines de semana", "Metodologia"])'
    source = (
        "from validator_engine import (\n    x,\n)\n"
        "def render_weekends(frames, data_dates):\n    return 'legacy'\n\n"
        + tabs
        + "\n"
    )
    patched = apply_weekend_assignment_support(source)
    assert "weekend_assignment_dashboard import evaluate_weekend_rule_table" in patched
    assert "Mínimo de sábados o domingos libres" in patched
    assert "No combinable sin reutilizar días" in patched
    assert "return 'legacy'" not in patched
