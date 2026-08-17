from __future__ import annotations

import re
from pathlib import Path

from contract_hours_heatmap_dashboard import apply_contract_hours_heatmap_support
from contract_shift_dashboard import apply_contract_shift_support
from dashboard_extensions import apply_extensions
from multi_file_dashboard import apply_multi_file_support
from review_iteration_dashboard import apply_review_iteration_support
from weekend_assignment_integration import apply_weekend_assignment_support
from workforce_insights_dashboard import apply_workforce_insights_support


REQUIRED_DASHBOARD_RENDERERS = (
    "def render_summary(frames):",
    "def render_restrictions(frames):",
    "def render_weekly(frames):",
    "def render_coverage(frames, data_dates):",
    "def render_shift_balance(frames):",
    "def render_absences(frames):",
    "def render_weekends(frames, data_dates):",
    "def render_workforce_mix(frames):",
)


def build_dashboard_source() -> str:
    """Compose every presentation layer and return the executable dashboard source."""
    runner = Path("dashboard_patch_v3.py").read_text(encoding="utf-8")
    runner = re.sub(
        r'\nexec\(compile\(source, "app.py", "exec"\), \{.*$',
        "",
        runner,
        flags=re.S,
    )
    namespace = {"__name__": "dashboard_patch_v3_base", "__file__": "dashboard_patch_v3.py"}
    exec(compile(runner, "dashboard_patch_v3.py", "exec"), namespace)

    source = apply_extensions(namespace["source"])
    source = apply_multi_file_support(source)
    source = apply_contract_shift_support(source)
    source = apply_review_iteration_support(source)
    source = apply_weekend_assignment_support(source)
    source = apply_contract_hours_heatmap_support(source)
    source = apply_workforce_insights_support(source)

    missing = [renderer for renderer in REQUIRED_DASHBOARD_RENDERERS if renderer not in source]
    if missing:
        raise RuntimeError(
            "La composición final del dashboard ha perdido renderizadores requeridos: "
            + ", ".join(missing)
        )

    compile(source, "app.py", "exec")
    return source


def run_dashboard() -> None:
    source = build_dashboard_source()
    exec(compile(source, "app.py", "exec"), {"__name__": "__main__", "__file__": "app.py"})


if __name__ == "__main__":
    run_dashboard()
