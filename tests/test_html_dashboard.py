from __future__ import annotations

import base64
import gzip
import hashlib
import re
from pathlib import Path


REFERENCE_PAYLOADS = [
    "reference_payload_1.js",
    "reference_payload_2.js",
    "reference_payload_3.js",
    "reference_payload_4.js",
    "reference_payload_5.js",
    "reference_payload_6_1.js",
    "reference_payload_6_2.js",
    "reference_payload_6_3.js",
    "reference_payload_6_4.js",
    "reference_payload_7.js",
    "reference_payload_8_1.js",
    "reference_payload_8_2.js",
    "reference_payload_8_3.js",
    "reference_payload_8_4.js",
]


def _standalone_html() -> str:
    payload = ""
    for name in REFERENCE_PAYLOADS:
        path = Path("html_assets") / name
        text = path.read_text(encoding="utf-8").strip()
        match = re.search(r'\+?="([A-Za-z0-9+/=]+)";?\s*$', text)
        assert match, f"Formato de paquete no válido: {path}"
        payload += match.group(1)
    return gzip.decompress(base64.b64decode(payload)).decode("utf-8")


def test_reference_html_reconstructs_expected_iteration():
    html = _standalone_html()
    assert hashlib.sha256(html.encode("utf-8")).hexdigest() == "f70cb40696250e6b7cdfe70fd9875db82070497a3e709b1cabb1e381e746b650"


def test_standalone_html_keeps_reference_features_and_adds_new_controls():
    loader = Path("validador_completo_dos_meses.html").read_text(encoding="utf-8")
    assert "reference_payload_1.js" in loader
    html = _standalone_html()
    assert "accept=.json,.txt" in html.replace('"', "")
    assert "Descargar Excel de detalle" in html
    assert 'id="morningCutoff"' in html
    assert 'id="afternoonCutoff"' in html
    assert "CENTRAL" in html
    assert "Cambios de horas contractuales entre meses consecutivos" in html
    assert "REVISAR CAMBIO DE CONTRATO" in html
    assert "activePlanningWeekSet" in html
    assert 'id="wkendReqFull"' in html
    assert 'id="wkendReqSat"' in html
    assert 'id="wkendReqSun"' in html
    assert "data-table-export" in html
    assert "downloadTableXlsx" in html
    assert "Horas contrato" in html


def test_reference_html_is_self_contained():
    html = _standalone_html().lower()
    assert "<script src=" not in html
    assert 'rel="stylesheet"' not in html
