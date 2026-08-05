from __future__ import annotations

import base64
import gzip
import re
from pathlib import Path


def _standalone_html() -> str:
    payload = ""
    for path in sorted(Path("html_assets").glob("payload_*.js")):
        text = path.read_text(encoding="utf-8")
        match = re.search(r'\+"([A-Za-z0-9+/=]+)";', text)
        assert match, f"Formato de paquete no válido: {path}"
        payload += match.group(1)
    return gzip.decompress(base64.b64decode(payload)).decode("utf-8")


def test_standalone_html_keeps_reference_features_and_adds_new_controls():
    loader = Path("validador_completo_dos_meses.html").read_text(encoding="utf-8")
    assert "payload_1.js" in loader
    html = _standalone_html()
    assert "accept=.json,.txt" in html.replace('"', "")
    assert "Descargar Excel de detalle" in html
    assert 'id="morningCutoff"' in html
    assert 'id="afternoonCutoff"' in html
    assert "CENTRAL" in html
    assert "Cambios de horas contractuales entre meses consecutivos" in html
    assert "REVISAR CAMBIO DE CONTRATO" in html
