from __future__ import annotations

import base64
import gzip
import re
from pathlib import Path

from contract_hours_heatmap_dashboard import apply_contract_hours_heatmap_support
from contract_shift_dashboard import apply_contract_shift_support
from dashboard_extensions import apply_extensions
from multi_file_dashboard import apply_multi_file_support
from review_iteration_dashboard import apply_review_iteration_support
from scripts.build_distributable_html import build_html, patched_payload, read_payload


def build_dashboard_source() -> str:
    runner = Path("dashboard_patch_v3.py").read_text(encoding="utf-8")
    runner = re.sub(r'\nexec\(compile\(source, "app.py", "exec"\), \{.*$', '', runner, flags=re.S)
    namespace = {"__name__": "dashboard_patch_v3_test", "__file__": "dashboard_patch_v3.py"}
    exec(compile(runner, "dashboard_patch_v3.py", "exec"), namespace)
    source = apply_extensions(namespace["source"])
    source = apply_multi_file_support(source)
    source = apply_contract_shift_support(source)
    source = apply_review_iteration_support(source)
    return apply_contract_hours_heatmap_support(source)


def test_contract_heatmap_support_is_applied_and_compiles():
    source = build_dashboard_source()

    assert "weekly_heatmap_neutralize_absence" in source
    assert "Neutralizar déficits totalmente explicables por ausencias" in source
    assert 'eq("PODRIA EXPLICAR TODAS LAS HORAS FALTANTES")' in source
    assert 'strftime("%d/%m/%Y")' in source
    assert 'contract_text = " → ".join' in source
    assert 'return"0"' in source or '"0" if neutralize_absence' in source
    assert "Semana desde %{x}" in source

    compile(source, "app.py", "exec")


def test_neutralization_keeps_employee_filter_on_original_deviation():
    source = build_dashboard_source()

    filter_position = source.index('if only_deviations:')
    neutralization_position = source.index('if neutralize_absence and not pivot.empty:')
    assert filter_position < neutralization_position


def test_distributable_html_contains_equivalent_contract_heatmap_controls():
    payload = read_payload()
    patched, source_bytes = patched_payload(payload)
    source = source_bytes.decode("utf-8")

    assert "wkNeutralizeAbs:false" in source
    assert 'id="wkNeutralizeAbs"' in source
    assert 'on("wkNeutralizeAbs","change"' in source
    assert "Neutralize shortfalls fully explainable by absences" in source
    assert "fullExplSet" in source
    assert 'return"0"' in source
    assert 'const weekLabels=totals.map(x=>dmy(x.inicio));' in source
    assert 'join(" → ")+" h"' in source

    # El payload generado debe seguir siendo un gzip HTML autocontenido válido.
    decoded = gzip.decompress(base64.b64decode(patched)).decode("utf-8")
    assert decoded == source
    html = build_html(payload)
    assert "window.__WFV_PAYLOAD" in html
    assert "wf-source-sha256" in html
