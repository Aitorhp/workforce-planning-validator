from __future__ import annotations

import runpy
import sys

import schedule_adapter

# Mantiene la fachada corregida del motor y aplica las capas de presentación
# de control contractual, cobertura, rotación, ausencias y fines de semana.
sys.modules["validator_engine"] = schedule_adapter
runpy.run_path("dashboard_final.py", run_name="__main__")
