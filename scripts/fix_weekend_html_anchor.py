#!/usr/bin/env python3
"""Ajuste temporal para hacer robusto el anclaje de renderWeekends."""
from pathlib import Path

path = Path(__file__).with_name("weekend_html_patch.py")
source = path.read_text(encoding="utf-8")
start = source.find("    pattern = re.compile(")
if start < 0:
    print("El anclaje ya no usa regex; no hay nada que modificar.")
    raise SystemExit(0)
end_marker = "    return pattern.sub(\n        WEEKEND_RENDER + '\\n\\n\\n/* ---------- Metodología ---------- */', source, count=1\n    )\n"
end = source.find(end_marker, start)
if end < 0:
    raise RuntimeError("No se encontró el final del reemplazo regex de renderWeekends")
end += len(end_marker)
replacement = '''    start_marker = "function renderWeekends(F){"\n    end_marker = "/* ---------- Metodología ---------- */"\n    render_start = source.find(start_marker)\n    if render_start < 0:\n        raise ValueError("Parche HTML de fines de semana: no se encontró renderWeekends")\n    render_end = source.find(end_marker, render_start)\n    if render_end < 0:\n        raise ValueError("Parche HTML de fines de semana: no se encontró el final de renderWeekends")\n    if source.find(start_marker, render_start + len(start_marker), render_end) >= 0:\n        raise ValueError("Parche HTML de fines de semana: se encontró más de un renderWeekends")\n    return source[:render_start] + WEEKEND_RENDER + "\\n\\n\\n" + source[render_end:]\n'''
path.write_text(source[:start] + replacement + source[end:], encoding="utf-8", newline="\n")
print(path)
