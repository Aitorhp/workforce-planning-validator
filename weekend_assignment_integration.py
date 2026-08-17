from __future__ import annotations

import re

from weekend_assignment_dashboard import DASHBOARD_WEEKEND_OVERRIDE


def apply_weekend_assignment_support(source: str) -> str:
    """Integrate weekend assignment rules without deleting adjacent renderers.

    This is strictly a presentation-layer transformation. It injects the
    evaluator import and replaces only the top-level ``render_weekends``
    function body. The previous implementation used the tabs block as the end
    marker, which could remove every renderer defined between ``render_weekends``
    and the tabs declaration.
    """
    import_marker = "from validator_engine import ("
    import_line = "from weekend_assignment_dashboard import evaluate_weekend_rule_table\n\n"
    if import_line not in source:
        if import_marker not in source:
            raise RuntimeError("No se encontró el bloque de importaciones del dashboard.")
        source = source.replace(import_marker, import_line + import_marker, 1)

    pattern = re.compile(
        r"\ndef render_weekends\(frames, data_dates\):.*?(?=\ndef [A-Za-z_]\w*\()",
        re.S,
    )
    matches = pattern.findall(source)
    if len(matches) != 1:
        raise RuntimeError(
            f"Se esperaba un único render_weekends configurable y se encontraron {len(matches)}."
        )

    patched = pattern.sub(
        "\n" + DASHBOARD_WEEKEND_OVERRIDE.rstrip() + "\n\n",
        source,
        count=1,
    )

    required_renderers = (
        "def render_summary(frames):",
        "def render_restrictions(frames):",
        "def render_weekly(frames):",
        "def render_coverage(frames, data_dates):",
        "def render_shift_balance(frames):",
        "def render_absences(frames):",
        "def render_weekends(frames, data_dates):",
    )
    missing = [renderer for renderer in required_renderers if renderer not in patched]
    if missing:
        raise RuntimeError(
            "La integración de fines de semana eliminó renderizadores requeridos: "
            + ", ".join(missing)
        )
    return patched
