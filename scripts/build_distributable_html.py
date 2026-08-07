#!/usr/bin/env python3
"""Genera el HTML único distribuible del validador.

El HTML funcional completo se conserva comprimido en los fragmentos
``html_assets/reference_payload_*.js``. Este script concatena esos fragmentos
en el orden definido, valida que formen un gzip correcto y genera un único
``validador_distribuible.html`` que no depende de ningún fichero externo.

El fichero de salida es un artefacto generado: debe sobrescribirse en cada
iteración que modifique la versión HTML del validador.
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

# Orden canónico de los payloads que reconstruyen el HTML de referencia.
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

PAYLOAD_RE = re.compile(r'\+?="([A-Za-z0-9+/=]+)";?\s*$')


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


def build_html(payload: str) -> str:
    compressed = base64.b64decode(payload, validate=True)
    source = gzip.decompress(compressed)
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
