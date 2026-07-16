from __future__ import annotations

from typing import Protocol
from workforce_validator.config import ValidatorSettings
from workforce_validator.models import Incident, ShiftRow

class ValidationRule(Protocol):
    def __call__(self, shifts: list[ShiftRow], settings: ValidatorSettings) -> list[Incident]: ...

def number_text(value: float) -> str:
    return f"{value:g}".replace(".", ",")
