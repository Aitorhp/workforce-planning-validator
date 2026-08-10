#!/usr/bin/env python3
"""Diagnóstico temporal del bloque funcional de fines de semana del HTML base."""
from __future__ import annotations

import base64
import gzip
from pathlib import Path

from build_distributable_html import read_payload

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "standalone" / "weekend_source_diagnostic.txt"

payload = read_payload()
source = gzip.decompress(base64.b64decode(payload, validate=True)).decode("utf-8")
markers = ['t("Resumen del periodo")', 't("Mapa empleado-fin de semana")', 't("Fines completos")']
parts = []
for marker in markers:
    index = source.find(marker)
    if index < 0:
        parts.append(f"MARKER {marker!r}: NOT FOUND")
        continue
    function_start = source.rfind("function ", 0, index)
    if function_start < 0:
        function_start = max(0, index - 4000)
    next_function = source.find("\nfunction ", index)
    if next_function < 0:
        next_function = min(len(source), index + 22000)
    block = source[function_start:next_function]
    block = block.replace(";", ";\n").replace("}", "}\n")
    parts.append(f"MARKER {marker!r}\n{block}")
OUTPUT.write_text("\n\n===== WEEKEND FUNCTION =====\n\n".join(parts), encoding="utf-8")
print(OUTPUT)
