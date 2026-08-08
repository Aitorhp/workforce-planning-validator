#!/usr/bin/env python3
"""Genera el HTML único distribuible del validador.

El HTML funcional base se conserva comprimido en los fragmentos
``html_assets/reference_payload_*.js``. Antes de volver a comprimirlo, este
generador aplica las extensiones de presentación que deben mantenerse en
paridad con Streamlit.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "html_assets"
OUTPUT = ROOT / "validador_distribuible.html"

PAYLOAD_FILES = [
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

PAYLOAD_RE = re.compile(r'"([A-Za-z0-9+/=]+)";?\s*$')


def read_payload() -> str:
    chunks: list[str] = []
    for name in PAYLOAD_FILES:
        path = ASSET_DIR / name
        if not path.exists():
            raise FileNotFoundError(f"Falta el payload requerido: {path}")
        text = path.read_text(encoding="utf-8").strip()
        match = PAYLOAD_RE.search(text)
        if not match:
            raise ValueError(f"No se pudo extraer el payload de {path}")
        chunks.append(match.group(1))
    return "".join(chunks)


def _replace(source: str, old: str, new: str, *, expected: int, label: str) -> str:
    found = source.count(old)
    if found != expected:
        raise ValueError(f"Parche HTML '{label}': se esperaban {expected} coincidencias y se encontraron {found}")
    return source.replace(old, new)


def patch_contract_hours_heatmap(source: str) -> str:
    """Replica en el HTML las mejoras visuales del mapa empleado-semana.

    Solo transforma la presentación. Los valores de contrato, desviación y
    explicación por ausencia ya vienen calculados por el motor JavaScript
    equivalente al motor Python.
    """

    source = _replace(
        source,
        '"Mostrar solo empleados con alguna desviacion":"Show only employees with a deviation",',
        '"Mostrar solo empleados con alguna desviacion":"Show only employees with a deviation",\n'
        '  "Neutralizar déficits totalmente explicables por ausencias":"Neutralize shortfalls fully explainable by absences",',
        expected=1,
        label="traducción del nuevo filtro",
    )

    source = _replace(
        source,
        'f:{ wkDev:true, wkStatus:null,',
        'f:{ wkDev:true, wkNeutralizeAbs:false, wkStatus:null,',
        expected=2,
        label="estado del filtro",
    )

    source = _replace(
        source,
        'h+=`<label class="chk"><input type="checkbox" id="wkDev" ${S.f.wkDev?"checked":""}> ${t("Mostrar solo empleados con alguna desviacion")}</label>`;',
        'h+=`<div class="controls"><label class="chk"><input type="checkbox" id="wkDev" ${S.f.wkDev?"checked":""}> ${t("Mostrar solo empleados con alguna desviacion")}</label>`+\n'
        '     `<label class="chk"><input type="checkbox" id="wkNeutralizeAbs" ${S.f.wkNeutralizeAbs?"checked":""}> ${t("Neutralizar déficits totalmente explicables por ausencias")}</label></div>`;',
        expected=1,
        label="controles del mapa",
    )

    source = _replace(
        source,
        'const pivot=new Map(); const explSet=new Set();',
        'const pivot=new Map(); const explSet=new Set(); const fullExplSet=new Set();',
        expected=1,
        label="conjuntos de explicación",
    )

    source = _replace(
        source,
        'if(String(r.posible_explicacion_por_ausencia).includes("PODRIA EXPLICAR")) explSet.add(r.Empleado+"|"+r.Semana);',
        'if(String(r.posible_explicacion_por_ausencia).includes("PODRIA EXPLICAR")) explSet.add(r.Empleado+"|"+r.Semana); '
        'if(r.deficit_explicable) fullExplSet.add(r.Empleado+"|"+r.Semana);',
        expected=1,
        label="identificación de déficit explicable",
    )

    source = _replace(
        source,
        'const matrix=rowEmps.map(e=>semanas.map(s=>pivot.has(e+"|"+s)?pivot.get(e+"|"+s):null));',
        'const displayValue=(e,s)=>{ const key=e+"|"+s; const v=pivot.has(key)?pivot.get(key):null; '
        'return S.f.wkNeutralizeAbs&&fullExplSet.has(key)&&v!=null&&v< -0.01?0:v; };\n'
        '    const matrix=rowEmps.map(e=>semanas.map(s=>displayValue(e,s)));',
        expected=1,
        label="neutralización visual",
    )

    old_text = '''const matText=rowEmps.map((e,i)=>semanas.map((s,j)=>{ const v=matrix[i][j]; if(v==null)return""; return (v>=0?"+":"")+v.toFixed(1)+(explSet.has(e+"|"+s)?" ✓":""); }));

    h+=chartHeatmapText(rowEmps,semanas,matrix,matText,color);'''
    new_text = '''const matText=rowEmps.map((e,i)=>semanas.map((s,j)=>{ const v=matrix[i][j]; if(v==null)return""; const key=e+"|"+s; if(S.f.wkNeutralizeAbs&&fullExplSet.has(key)&&Math.abs(v)<=0.01)return"0"; return (v>=0?"+":"")+v.toFixed(1)+(explSet.has(key)?" ✓":""); }));

    const employeeLabels=rowEmps.map(e=>{ const employeeRows=rows.filter(r=>r.Empleado===e).sort((a,b)=>a.ano_iso-b.ano_iso||a.semana_iso-b.semana_iso); const values=[]; employeeRows.forEach(r=>{ const v=Number(r._app); if(Number.isNaN(v))return; if(!values.length||Math.abs(values[values.length-1]-v)>0.01)values.push(v); }); const contract=values.length?values.map(v=>Number.isInteger(v)?String(v):fmt(v,1)).join(" → ")+" h":"— h"; return e+" · "+contract; });
    const weekLabels=totals.map(x=>dmy(x.inicio));
    h+=chartHeatmapText(employeeLabels,weekLabels,matrix,matText,color);'''
    source = _replace(source, old_text, new_text, expected=1, label="etiquetas del mapa")

    source = _replace(
        source,
        'on("wkDev","change",e=>{S.f.wkDev=e.target.checked;renderTab();});',
        'on("wkDev","change",e=>{S.f.wkDev=e.target.checked;renderTab();});\n'
        '  on("wkNeutralizeAbs","change",e=>{S.f.wkNeutralizeAbs=e.target.checked;renderTab();});',
        expected=1,
        label="binding del nuevo filtro",
    )

    return source


def patched_payload(payload: str) -> tuple[str, bytes]:
    compressed = base64.b64decode(payload, validate=True)
    source = gzip.decompress(compressed).decode("utf-8")
    source = patch_contract_hours_heatmap(source)
    source_bytes = source.encode("utf-8")
    # mtime=0 hace que el artefacto sea reproducible entre ejecuciones.
    compressed_patched = gzip.compress(source_bytes, mtime=0)
    return base64.b64encode(compressed_patched).decode("ascii"), source_bytes


def build_html(payload: str) -> str:
    payload, source = patched_payload(payload)
    if b"<html" not in source.lower() or b"</html>" not in source.lower():
        raise ValueError("El payload no reconstruye un documento HTML completo")

    source_sha = hashlib.sha256(source).hexdigest()
    return f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Validador de planificaciones</title><meta name="wf-source-sha256" content="{source_sha}"></head><body><p style="font-family:system-ui;padding:24px">Cargando validador...</p><script>window.__WFV_PAYLOAD="{payload}";</script><script>(async()=>{{try{{const b=Uint8Array.from(atob(window.__WFV_PAYLOAD),c=>c.charCodeAt(0));const stream=new Blob([b]).stream().pipeThrough(new DecompressionStream("gzip"));const html=await new Response(stream).text();document.open();document.write(html);document.close();}}catch(e){{document.body.innerHTML="<pre>Error al cargar el validador: "+String(e)+"</pre>";}}}})();</script></body></html>'''


def main() -> None:
    payload = read_payload()
    html = build_html(payload)
    OUTPUT.write_text(html, encoding="utf-8", newline="\n")
    print(f"Generado: {OUTPUT.relative_to(ROOT)} ({len(html):,} bytes)")


if __name__ == "__main__":
    main()
