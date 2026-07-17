from datetime import date, datetime

from workforce_validator.analytics import (
    SHIFT_PERIOD_AFTERNOON,
    SHIFT_PERIOD_MORNING,
    analyze_daily_absences,
    analyze_shift_balance,
    classify_shift_period,
)
from workforce_validator.models import AbsenceDay, ShiftRow


def shift(person_id, start_hour):
    start = datetime(2026, 8, 3, start_hour, 0)
    return ShiftRow(14947, person_id, 40, start.date(), start, start.replace(hour=start_hour + 6), 6.0, 0.0)


def test_shift_cutoff_is_1300():
    assert classify_shift_period(datetime(2026, 8, 3, 12, 59)) == SHIFT_PERIOD_MORNING
    assert classify_shift_period(datetime(2026, 8, 3, 13, 0)) == SHIFT_PERIOD_AFTERNOON


def test_shift_balance_identifies_rotation_and_single_periods():
    rows = analyze_shift_balance([
        shift("E1", 9),
        shift("E1", 14),
        shift("E2", 8),
        shift("E2", 10),
        shift("E3", 13),
    ])
    by_person = {row["personId"]: row for row in rows}
    assert by_person["E1"]["estado_rotacion"] == "Mañana y tarde"
    assert by_person["E1"]["indice_equilibrio_pct"] == 100.0
    assert by_person["E2"]["estado_rotacion"] == "Solo mañanas"
    assert by_person["E2"]["sesgo_tarde_pct"] == -100.0
    assert by_person["E3"]["estado_rotacion"] == "Solo tardes"


def test_daily_absences_preserve_zero_days_and_unique_employees():
    absences = [
        AbsenceDay(14947, "E1", date(2026, 8, 3), "VACACIONES", "VALIDATED"),
        AbsenceDay(14947, "E1", date(2026, 8, 3), "OTRA", "APPROVED"),
        AbsenceDay(14947, "E2", date(2026, 8, 3), "VACACIONES", "VALIDATED"),
    ]
    rows = analyze_daily_absences(absences, {date(2026, 8, 3), date(2026, 8, 4)})
    assert rows[0]["empleados_ausentes"] == 2
    assert rows[0]["registros_ausencia"] == 3
    assert rows[1]["empleados_ausentes"] == 0
    assert rows[1]["registros_ausencia"] == 0
