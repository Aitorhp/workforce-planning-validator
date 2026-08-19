# Matriz de equivalencia para una nueva fuente

Utilizar esta plantilla antes de implementar `NewSourceAdapter`. No rellenar una equivalencia por similitud de nombre: cada fila debe validarse semánticamente con ejemplos reales.

| Concepto funcional | Fuente actual | Campo canónico | Nueva fuente | Transformación necesaria | Validación requerida |
|---|---|---|---|---|---|
| Tienda | `store.id` | `store_id` | TBD | TBD | Identidad estable y comparable |
| Empleado | `people[].personId` o fallback `person.personId` | `person_id` | TBD | TBD | Estable entre fechas/ficheros |
| Fecha operativa | `storeDayTimes[].operatingDate` | `work_day` / `data_dates` | TBD | TBD | Distinguir cobertura de turno |
| Presencia empleado-día | existencia de `people[]` en `operatingDate` | `presence_dates` | TBD | TBD | Puede existir sin turno |
| Horas contrato | `person.applicableWorkingHours` | `applicable_working_hours` | TBD | TBD | Preservar nulos/textos y temporalidad necesaria |
| Mes contractual | `operatingDate -> YYYY-MM` | `employee_month_contract` | TBD | TBD | Último valor procesado por mes en equivalencia actual |
| Plan publicado | `dayTimes.planned` | `schedule_source=planned` | TBD | TBD | No mezclar con draft |
| Borrador | `dayTimes.plannedDraft` | `schedule_source=plannedDraft` | TBD | TBD | No fallback silencioso |
| Flag edición manual | `dayTimes.plannedDraftManuallyEdited` | `manual_edit_state` | TBD | TBD | Trivalente true/false/missing |
| Tipo de segmento | `hourType` | `segment_kind` | TBD | TBD | Identificar equivalencia exacta a WORK |
| Inicio segmento | `startDateTime` | `segment_start` | TBD | TBD | Semántica timezone equivalente |
| Fin segmento | `endDateTime` | `segment_end` | TBD | TBD | `end > start` |
| Inicio turno | primer inicio WORK | `shift_start` | derivado/TBD | TBD | Igual al algoritmo actual |
| Fin turno | máximo fin WORK | `shift_end` | derivado/TBD | TBD | Igual al algoritmo actual |
| Horas netas | suma duraciones WORK | `worked_hours` | derivado/TBD | TBD | Comparar a 4 decimales |
| Descanso interno | gaps positivos `<= max_internal_break_hours` | `break_hours` | derivado/TBD | TBD | Umbral configurable |
| Ausencia | `dayTimes.absences[]` | `absence` | TBD | TBD | Puede coexistir con turno |
| Estado ausencia | `absence.status` | `absence_status` | TBD | TBD | Mapear solo equivalentes a VALIDATED/APPROVED |
| Tipo ausencia | `type.name` → `description` → `id` | `absence_type` | TBD | TBD | Definir fallback |
| Cobertura global | todos los `operatingDate` | `data_dates` | TBD | TBD | Incluir días con cero trabajo |
| Fuente disponible | presencia/listas en `dayTimes` | capabilities | TBD | TBD | Detectar planned/draft disponibles |
| Tienda en carga múltiple | igualdad `str(store.id)` | mismo `store_id` | TBD | TBD | Rechazar mezcla equivalente |
| Solapamiento de periodos | operatingDate común entre ficheros | integridad temporal | TBD | TBD | Definir política explícita |
| Mes único por fichero actual | fechas de cada JSON | restricción solo CurrentJsonAdapter | N/A/TBD | TBD | No forzar si nueva fuente no usa ficheros mensuales |

## Checklist de validación semántica

- [ ] La nueva fuente puede representar un día cubierto con cero turnos.
- [ ] Puede representar un empleado presente sin turno.
- [ ] Puede distinguir plan publicado y borrador, si ambos existen.
- [ ] Puede distinguir draft editado, no editado y flag desconocido/ausente.
- [ ] Se ha definido qué códigos equivalen a `WORK`.
- [ ] Se ha documentado timezone/offset de timestamps.
- [ ] Se ha demostrado cómo reconstruir múltiples segmentos de un mismo día.
- [ ] Se ha definido la granularidad histórica del contrato.
- [ ] Se han mapeado estados de ausencia con evidencia funcional.
- [ ] Se puede reconstruir cobertura completa del dataset.
- [ ] Se han identificado duplicados/solapamientos posibles de la nueva fuente.
- [ ] Se han creado fixtures equivalentes para Golden Master.

## Ficha de transformación por campo

Para cada fila no trivial, completar además:

```text
Concepto:
Campo/ruta externa:
Ejemplo real:
Tipo externo:
Valores nulos/ausentes:
Transformación:
Valor canónico resultante:
Caso frontera:
Prueba automatizada:
Duda funcional pendiente:
```

## Criterio de cierre

La matriz no se considera completa mientras exista algún `TBD` en un concepto que alimente:

- construcción de turnos;
- reglas;
- cobertura semanal;
- contrato;
- ausencias;
- fines de semana;
- dashboards o HTML.

Una nueva fuente puede omitir conceptos que no existan funcionalmente solo si se documenta el comportamiento sustituto y se demuestra que no cambia resultados esperados.