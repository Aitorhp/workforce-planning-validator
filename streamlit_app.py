from __future__ import annotations

import runpy
import sys

import schedule_adapter

# app.py mantiene la interfaz existente. Esta sustitucion hace que sus imports
# de validator_engine utilicen el modelo corregido de plannedDraftManuallyEdited.
sys.modules["validator_engine"] = schedule_adapter
runpy.run_path("app.py", run_name="__main__")
