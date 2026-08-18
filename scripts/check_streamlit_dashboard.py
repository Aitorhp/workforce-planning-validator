from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard_final import (
    REQUIRED_DASHBOARD_RENDERERS,
    REQUIRED_PRESENTATION_MARKERS,
    build_dashboard_source,
)


def main() -> None:
    source = build_dashboard_source()
    missing = [renderer for renderer in REQUIRED_DASHBOARD_RENDERERS if renderer not in source]
    if missing:
        raise SystemExit("ERROR: faltan renderizadores: " + ", ".join(missing))

    required_features = (
        "Mínimo de sábados o domingos libres",
        "weekend_flexible_distinct_weekends",
        "No combinable sin reutilizar días",
        'st.markdown("#### Magnitud del descanso por fin de semana")',
        'yaxis_title="% de plantilla con fin de semana completo libre"',
        "Base del porcentaje:",
    ) + REQUIRED_PRESENTATION_MARKERS
    absent_features = [feature for feature in required_features if feature not in source]
    if absent_features:
        raise SystemExit("ERROR: faltan cambios funcionales/visuales: " + ", ".join(absent_features))

    compile(source, "app.py", "exec")
    print("OK: dashboard Streamlit compuesto y compilado correctamente.")
    print(f"OK: {len(REQUIRED_DASHBOARD_RENDERERS)} renderizadores principales presentes.")
    print("OK: lógica configurable de fines de semana presente.")
    print("OK: visual 'Magnitud del descanso por fin de semana' presente en el código final ejecutado.")


if __name__ == "__main__":
    main()
