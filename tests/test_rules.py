from datetime import date, timedelta
from workforce_validator.config import SETTINGS
from workforce_validator.rules.max_shift_duration import validate as max_shift
from workforce_validator.rules.min_shift_duration import validate as min_shift
from workforce_validator.rules.min_rest_between_shifts import validate as min_rest
from workforce_validator.rules.max_consecutive_days import validate as consecutive


def test_exact_max_shift_complies(make_shift):
    assert max_shift([make_shift(date(2026,8,3), "09:00", "16:30")], SETTINGS) == []

def test_shift_over_max_fails(make_shift):
    assert max_shift([make_shift(date(2026,8,3), "09:00", "16:31")], SETTINGS)[0].incident_type == "TURNO_SUPERIOR_7_5H"

def test_exact_min_shift_complies(make_shift):
    assert min_shift([make_shift(date(2026,8,3), "09:00", "13:00")], SETTINGS) == []

def test_shift_under_min_fails(make_shift):
    assert min_shift([make_shift(date(2026,8,3), "09:00", "12:59")], SETTINGS)[0].incident_type == "TURNO_INFERIOR_4H"

def test_exact_rest_complies(make_shift):
    shifts=[make_shift(date(2026,8,3),"12:00","20:00"), make_shift(date(2026,8,4),"07:00","13:00")]
    assert min_rest(shifts, SETTINGS) == []

def test_rest_under_limit_fails(make_shift):
    shifts=[make_shift(date(2026,8,3),"12:00","20:00"), make_shift(date(2026,8,4),"06:59","13:00")]
    assert min_rest(shifts, SETTINGS)[0].incident_type == "DESCANSO_INFERIOR_11H"

def test_five_days_comply(make_shift):
    start=date(2026,8,3)
    assert consecutive([make_shift(start+timedelta(days=i),"09:00","15:00") for i in range(5)], SETTINGS) == []

def test_six_days_fail(make_shift):
    start=date(2026,8,3)
    incidents=consecutive([make_shift(start+timedelta(days=i),"09:00","15:00") for i in range(6)], SETTINGS)
    assert len(incidents) == 1 and incidents[0].observed_value == 6.0

def test_cross_month_streak_is_reported_in_both_months(make_shift):
    start=date(2026,7,29)
    incidents=consecutive([make_shift(start+timedelta(days=i),"09:00","15:00") for i in range(6)], SETTINGS)
    assert [item.month for item in incidents] == ["2026-07", "2026-08"]
