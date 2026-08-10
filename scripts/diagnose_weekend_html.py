#!/usr/bin/env python3
"""Diagnóstico temporal del estado y bindings de fines de semana del HTML base."""
from __future__ import annotations

import base64
import gzip
import re
from pathlib import Path

from build_distributable_html import read_payload

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "standalone" / "weekend_source_diagnostic.txt"

payload = read_payload()
source = gzip.decompress(base64.b64decode(payload, validate=True)).decode("utf-8")
markers = ["wkendReqFull", "wkendReqSat", "wkendReqSun", "wkendAlerts", "wkendDiag"]
parts = []
for marker in markers:
    positions = [m.start() for m in re.finditer(re.escape(marker), source)]
    for number, index in enumerate(positions, 1):
        start = max(0, index - 900)
        end = min(len(source), index + 1500)
        excerpt = source[start:end].replace(";", ";\n").replace("}", "}\n")
        parts.append(f"MARKER {marker!r} {number}/{len(positions)}\n{excerpt}")
OUTPUT.write_text("\n\n===== WEEKEND STATE =====\n\n".join(parts), encoding="utf-8")
print(OUTPUT)
