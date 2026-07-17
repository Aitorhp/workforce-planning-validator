from __future__ import annotations

import runpy
import sys

import schedule_adapter

# Mantiene la fachada corregida del motor y aplica las capas de presentación
# especializadas en control contractual, cobertura, rotación y ausencias.
sys.modules["validator_engine"] = schedule_adapter
runpy.run_path("dashboard_patch_v2.py", run_name="__main__")
