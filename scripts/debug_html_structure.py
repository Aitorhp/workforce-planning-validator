#!/usr/bin/env python3
from __future__ import annotations

import base64
import gzip

from build_distributable_html import read_payload

# Diagnóstico temporal: contexto real de navegación del payload HTML base.
def main() -> None:
    source = gzip.decompress(base64.b64decode(read_payload(), validate=True)).decode("utf-8")
    print("\n--- CONTEXTO DE NAVEGACION DEL HTML BASE ---")
    for needle in ("Fines de semana", "weekends", "Metodología", "Metodologia", "renderTab", "tabs"):
        positions = []
        start = 0
        while True:
            pos = source.find(needle, start)
            if pos < 0:
                break
            positions.append(pos)
            start = pos + len(needle)
        print(f"\n[{needle}] coincidencias={len(positions)}")
        for pos in positions[:8]:
            left = max(0, pos - 320)
            right = min(len(source), pos + 520)
            print(source[left:right].replace("\n", "\\n"))
            print("---")


if __name__ == "__main__":
    main()
