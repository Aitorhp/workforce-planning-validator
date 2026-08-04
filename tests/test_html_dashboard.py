from __future__ import annotations

import re
from pathlib import Path

from dashboard_extensions import apply_extensions
from html_dashboard import apply_html_report_support
from multi_file_dashboard import apply_multi_file_support


def test_dashboard_adds_html_export_and_new_weekend_map():
    runner = Path("dashboard_patch_v3.py").read_text(encoding="utf-8")
    runner = re.sub(
        r'\nexec\(compile\(source, "app.py", "exec"\), \{.*$',
        "",
        runner,
        flags=re.S,
    )
    namespace = {
        "__name__": "dashboard_patch_v3_html_test",
        "__file__": "dashboard_patch_v3.py",
    }
    exec(compile(runner, "dashboard_patch_v3.py", "exec"), namespace)

    source = apply_extensions(namespace["source"])
    source = apply_multi_file_support(source)
    source = apply_html_report_support(source)

    compile(source, "app.py", "exec")
    assert "build_html_report" in source
    assert "Descargar informe HTML / Download HTML" in source
    assert "build_weekend_map_component" in source
    assert "streamlit.components.v1" in source
    assert "go.Heatmap(z=matrix.to_numpy()" not in source
