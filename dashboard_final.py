from __future__ import annotations

import re
from pathlib import Path

from dashboard_extensions import apply_extensions

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
exec(compile(source, "app.py", "exec"), {"__name__": "__main__", "__file__": "app.py"})
