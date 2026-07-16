from __future__ import annotations

import calendar
from datetime import date, timedelta
from typing import Iterable


def month_key(day: date) -> str:
    return day.strftime("%Y-%m")


def daterange(start: date, end: date) -> Iterable[date]:
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def find_consecutive_streaks(days: list[date]) -> list[list[date]]:
    if not days:
        return []
    unique_days = sorted(set(days))
    streaks: list[list[date]] = [[unique_days[0]]]
    for current in unique_days[1:]:
        if current == streaks[-1][-1] + timedelta(days=1):
            streaks[-1].append(current)
        else:
            streaks.append([current])
    return streaks


def weekend_counts(year: int, month: int, worked_days: set[date]) -> tuple[int, int, int]:
    month_days = [date(year, month, day) for day in range(1, calendar.monthrange(year, month)[1] + 1)]
    saturdays = [day for day in month_days if day.weekday() == 5]
    sundays = [day for day in month_days if day.weekday() == 6]
    free_saturdays = sum(day not in worked_days for day in saturdays)
    free_sundays = sum(day not in worked_days for day in sundays)
    complete = sum(
        saturday not in worked_days
        and (saturday + timedelta(days=1)).month == month
        and saturday + timedelta(days=1) not in worked_days
        for saturday in saturdays
    )
    return complete, free_saturdays, free_sundays


def week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def collect_data_dates(data: dict) -> set[date]:
    return {
        date.fromisoformat(str(item.get("operatingDate"))[:10])
        for item in data.get("storeDayTimes") or []
        if isinstance(item, dict) and item.get("operatingDate")
    }
