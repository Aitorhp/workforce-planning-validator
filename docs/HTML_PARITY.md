# HTML autónomo y paridad con Streamlit

## 1. Dos superficies de producto

El repositorio mantiene dos soportes de usuario:

1. aplicación Streamlit;
2. HTML autónomo/distribuible.

`README.md` y `standalone/README.md` establecen que cualquier cambio visible o funcional debe revisarse en ambos soportes salvo excepción técnica documentada.

## 2. Piezas del HTML

| Pieza | Clasificación | Papel |
|---|---|---|
| `validador_completo_dos_meses.html` | Lanzador interno | Carga `reference_payload_*.js`, descomprime el HTML de referencia y lo escribe en el navegador. |
| `html_assets/reference_payload_*.js` | Fuente versionada de referencia | Fragmentos base64 de un payload gzip que reconstruye un HTML completo con lógica JavaScript. |
| `scripts/build_distributable_html.py` | Generador | Reconstruye la referencia, aplica parches, recomprime y genera el entregable. |
| `scripts/weekend_html_patch.py` | Parche productivo | Replica reglas/UX actuales de fines de semana. |
| `scripts/workforce_insights_html_patch.py` | Parche productivo | Replica mejoras de descansos y Mix de plantilla. |
| `patch_contract_hours_heatmap()` dentro del generador | Parche productivo | Replica neutralización visual y etiquetas del heatmap. |
| `patch_collapsible_sidebar()` | Parche de UX | Añade sidebar plegable al HTML. |
| `validador_distribuible.html` | **Artefacto generado** | Único fichero autocontenido que debe entregarse al usuario. |

## 3. `validador_completo_dos_meses.html`

Es un loader fino. Declara scripts externos correspondientes a todos los `reference_payload_*.js`, concatena el payload global expuesto y usa `DecompressionStream("gzip")` para obtener el HTML real.

No debe confundirse este lanzador con el código funcional completo.

## 4. Generación de `validador_distribuible.html`

Comando documentado:

```bash
python scripts/build_distributable_html.py
```

Flujo de `scripts/build_distributable_html.py`:

```text
reference_payload_*.js
  |
  |-- extraer fragmentos base64
  |-- concatenar
  |-- base64 decode
  |-- gzip decompress
  v
HTML/JS de referencia
  |
  |-- patch_weekend_assignment
  |-- patch_workforce_insights
  |-- patch_contract_hours_heatmap
  |-- patch_collapsible_sidebar
  v
HTML/JS final
  |
  |-- sha256 de la fuente
  |-- gzip.compress(..., mtime=0)
  |-- base64
  v
validador_distribuible.html
```

El uso de `mtime=0` hace reproducible la compresión entre ejecuciones.

## 5. Fuente vs artefacto

### COMPORTAMIENTO OBSERVADO

`validador_distribuible.html` se sobrescribe por el generador y puede regenerarse también mediante `.github/workflows/build-distributable-html.yml`.

### Regla

**No editar manualmente `validador_distribuible.html` como fuente de verdad.**

Si se necesita cambiar comportamiento HTML debe modificarse:

- la referencia/payload que corresponda; o
- un parche/generador versionado.

Después se regenera el artefacto.

## 6. Lógica de negocio en JavaScript

El HTML autónomo no ejecuta el paquete Python `workforce_validator`. El payload de referencia contiene una implementación JavaScript que reproduce cálculos y UI.

Por ello la paridad no está garantizada automáticamente por compartir código. Debe verificarse por resultados.

`standalone/README.md` reconoce explícitamente que, cuando el HTML replica cálculos en JavaScript, deben mantenerse en paridad con el comportamiento de Streamlit/Python.

## 7. Pruebas actuales del HTML

`tests/test_html_dashboard.py` verifica, entre otras cosas:

- que los payloads de referencia reconstruyen un HTML con SHA esperado;
- que existen controles/features de la iteración;
- que la referencia es autocontenida respecto a scripts/estilos externos.

Además existen:

- `tests/test_weekend_html_patch.py`;
- `tests/test_workforce_insights_html_patch.py`.

Estas pruebas son importantes, pero prueban sobre todo **estructura, presencia de features y estabilidad del payload**, no una equivalencia numérica exhaustiva contra el motor Python.

## 8. Paridad que debe verificarse al cambiar la fuente

La nueva fuente afecta potencialmente a ambas superficies. Deben compararse, para un fixture común:

| Resultado | Python/Streamlit | HTML |
|---|---:|---:|
| turnos normalizados | Sí | Sí |
| horas netas | Sí | Sí |
| incidencias de reglas | Sí | Sí |
| resumen mensual | Sí | Sí |
| control semanal | Sí | Sí |
| cobertura semanal | Sí | Sí |
| ausencias y explicación | Sí | Sí |
| fines de semana | Sí | Sí |
| cambios de contrato | visible | visible |
| balance de franjas | visible | visible |
| Mix de plantilla | visible | visible |

## 9. Estrategia recomendada de paridad

### Nivel 1 — Golden Master Python

Fijar datasets de referencia del motor Python actual.

### Nivel 2 — Golden Master HTML/JS

Con la misma entrada semántica, instrumentar o exponer los datasets internos equivalentes del HTML y compararlos con los resultados Python normalizados.

### Nivel 3 — Smoke/UI

Verificar que tabs, filtros, KPIs y exportaciones siguen presentes.

No utilizar únicamente screenshots o presencia de textos para demostrar equivalencia de cálculos.

## 10. Parches de fin de semana

La lógica de asignación de descansos tiene implementaciones específicas en Streamlit y HTML. Cualquier cambio en:

- mínimo de fines completos;
- sábados;
- domingos;
- regla flexible;
- restricción de fines distintos;
- no reutilización de días;

debe tener test equivalente en ambos soportes.

## 11. Parches de Workforce Insights

La reducción de la gráfica de rotación, el porcentaje de plantilla con fin completo libre y `Mix de plantilla` se incorporan mediante `workforce_insights_dashboard.py` en Streamlit y `scripts/workforce_insights_html_patch.py` en HTML.

Esto confirma que el HTML distribuible no se deriva automáticamente del source Streamlit; la paridad se mantiene manualmente mediante implementaciones coordinadas.

## 12. Recomendación para una nueva fuente

### ESTADO ACTUAL

Hay dos implementaciones de producto que deben recibir semántica equivalente.

### RECOMENDACIÓN

Definir primero el modelo canónico y fixtures Golden Master independientes del formato. Después adaptar tanto el pipeline Python como el JavaScript a ese contrato, o generar para HTML un payload canónico equivalente. No cambiar simultáneamente las fórmulas.