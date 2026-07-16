from __future__ import annotations

import runpy
import sys

import schedule_adapter

# Mantiene la fachada corregida del motor y aplica la capa de presentacion
# especializada en control contractual semanal y cobertura diaria.
sys.modules["validator_engine"] = schedule_adapter
runpy.run_path("dashboard_patch.py", run_name="__main__")
