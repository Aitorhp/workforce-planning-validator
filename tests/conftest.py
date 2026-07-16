from datetime import date, datetime, timedelta
import pytest
from workforce_validator.models import ShiftRow

@pytest.fixture
def make_shift():
    def factory(work_day: date, start: str, end: str, person_id="E1", contract=40):
        start_dt = datetime.fromisoformat(f"{work_day.isoformat()}T{start}:00")
        end_dt = datetime.fromisoformat(f"{work_day.isoformat()}T{end}:00")
        if end_dt <= start_dt:
            end_dt += timedelta(days=1)
        return ShiftRow(14947, person_id, contract, work_day, start_dt, end_dt, round((end_dt-start_dt).total_seconds()/3600, 4), 0.0)
    return factory
