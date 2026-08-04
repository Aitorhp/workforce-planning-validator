from __future__ import annotations

import re
from pathlib import Path

from contract_shift_dashboard import apply_contract_and_shift_band_support
from dashboard_extensions import apply_extensions
from multi_file_dashboard import apply_multi_file_support


def test_dashboard_source_supports_two_files_contract_review_three_bands_and_compiles():
    runner = Path("dashboard_patch_v3.py").read_text(encoding="utf-8")
    runner = re.sub(
        r'\nexec\(compile\(source, "app.py", "exec"\), \{.*$',
        "",
        runner,
        flags=re.S,
    )
    namespace = {
        "__name__": "dashboard_patch_v3_test",
        "__file__": "dashboard_patch_v3.py",
    }
    exec(compile(runner, "dashboard_patch_v3.py", "exec"), namespace)

    source = apply_extensions(namespace["source"])
    source = apply_multi_file_support(source)
    source = apply_contract_and_shift_band_support(source)

    compile(source, "app.py", "exec")
    assert "accept_multiple_files=True" in source
    assert "combine_planning_documents" in source
    assert "Periodo combinado" in source
    assert "shift_morning_cutoff" in source
    assert "shift_afternoon_cutoff" in source
    assert "turnos_central" in source
    assert "Cambios de horas contractuales entre meses" in source
    assert "Descargar informe HTML" in source
    assert "build_html_report" in source
