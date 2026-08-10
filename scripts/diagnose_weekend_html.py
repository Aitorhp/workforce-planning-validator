#!/usr/bin/env python3
"""Diagnóstico temporal de prepWeekend del HTML base."""
from __future__ import annotations

import base64
import gzip
from pathlib import Path

from build_distributable_html import read_payload

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "standalone" / "weekend_source_diagnostic.txt"

payload = read_payload()
source = gzip.decompress(base64.b64decode(payload, validate=True)).decode("utf-8")
start = source.find("function prepWeekend")
if start < 0:
    raise RuntimeError("No se encontró prepWeekend")
end = source.find("\nfunction ", start + 1)
if end < 0:
    end = min(len(source), start + 18000)
block = source[start:end].replace(";", ";\n").replace("}", "}\n")
OUTPUT.write_text(block, encoding="utf-8")
print(OUTPUT)
