from __future__ import annotations

import re
from pathlib import Path

from contract_hours_heatmap_dashboard import apply_contract_hours_heatmap_support
from contract_shift_dashboard import apply_contract_shift_support
from dashboard_extensions import apply_extensions
from multi_file_dashboard import apply_multi_file_support
from review_iteration_dashboard import apply_review_iteration_support

runner = Path("dashboard_patch_v3.py").read_text(encoding="utf-8")
runner = re.sub(r'\nexec\(compile\(source, "app.py", "exec"\), \{.*$', '', runner, flags=re.S)
namespace = {"__name__": "dashboard_patch_v3_base", "__file__": "dashboard_patch_v3.py"}
exec(compile(runner, "dashboard_patch_v3.py", "exec"), namespace)
source = apply_extensions(namespace["source"])
source = apply_multi_file_support(source)
source = apply_contract_shift_support(source)
source = apply_review_iteration_support(source)
source = apply_contract_hours_heatmap_support(source)
exec(compile(source, "app.py", "exec"), {"__name__": "__main__", "__file__": "app.py"})
