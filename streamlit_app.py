from __future__ import annotations

import runpy
import sys

import schedule_adapter

# Mantiene la fachada corregida del motor y aplica todas las capas visuales
# acumuladas en esta rama, incluidas las extensiones de fines de semana.
sys.modules["validator_engine"] = schedule_adapter
runpy.run_path("dashboard_final.py", run_name="__main__")
