#!/usr/bin/env python3
"""Parche temporal e idempotente para integrar weekend_html_patch en el generador."""
from pathlib import Path

path = Path(__file__).with_name("build_distributable_html.py")
source = path.read_text(encoding="utf-8")

import_line = "from pathlib import Path\n"
weekend_import = "from weekend_html_patch import patch_weekend_assignment\n"
if weekend_import not in source:
    if import_line not in source:
        raise RuntimeError("No se encontró el bloque de imports del generador")
    source = source.replace(import_line, import_line + "\n" + weekend_import, 1)

call_marker = "    source = patch_contract_hours_heatmap(source)\n"
weekend_call = "    source = patch_weekend_assignment(source)\n"
if weekend_call not in source:
    if call_marker not in source:
        raise RuntimeError("No se encontró patched_payload en el generador")
    source = source.replace(call_marker, weekend_call + call_marker, 1)

path.write_text(source, encoding="utf-8", newline="\n")
print(path)
