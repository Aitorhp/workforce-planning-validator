# Modelo de datos actual — JSON de entrada

## 1. Separación entre formato de origen y modelo de negocio

El JSON actual es un **formato de entrada**, no el contrato conceptual que debería imponer una futura integración. El motor Python conoce todavía parte de esta estructura en `workforce_validator/schedule_sources.py`, `workforce_validator/extraction.py`, `workforce_validator/dates.py` y `workforce_validator/multi_file.py`.

La ruta funcional principal es:

```text
raíz
├── store
│   └── id
└── storeDayTimes[]
    ├── operatingDate
    └── people[]
        ├── personId
        ├── person
        │   ├── personId
        │   └── applicableWorkingHours
        └── dayTimes
            ├── planned[]
            ├── plannedDraft[]
            ├── plannedDraftManuallyEdited
            └── absences[]
```

## 2. Campos realmente consumidos por el motor Python

| Campo origen | Ruta JSON | Tipo esperado/observado | Obligatorio para qué | Significado efectivo | Consumidor | Transformación |
|---|---|---|---|---|---|---|
| Tienda | `store.id` | cualquiera no vacío en carga múltiple | Identidad de tienda | Clave de agrupación | `extraction.py`, `multi_file.py` | Se conserva como `store_id`; en multi-file se compara mediante `str(value)`. |
| Día operativo | `storeDayTimes[].operatingDate` | valor convertible por primeros 10 caracteres a ISO `YYYY-MM-DD` | Cobertura, presencia, turno, ausencia | Fecha de negocio a la que pertenece el bloque | `extraction.py`, `dates.py`, `schedule_sources.py`, `multi_file.py` | `date.fromisoformat(str(value)[:10])`. |
| Personas del día | `storeDayTimes[].people` | lista | Navegación | Registros persona-día | `extraction.py`, `schedule_sources.py` | `None`/ausente -> lista vacía. |
| Identificador empleado | `people[].personId` | cualquiera | Identidad | Identificador preferido | `extraction.py` | Si la clave existe se usa; si no, fallback a `person.personId`. |
| Identificador fallback | `people[].person.personId` | cualquiera | Solo si falta `people[].personId` | Identidad alternativa | `extraction.py` | Fallback. |
| Horas contractuales | `people[].person.applicableWorkingHours` | cualquier valor; semanal intenta `float()` | Resumen y control semanal | Horas aplicables asociadas al empleado | `extraction.py`, indirectamente `weekly_hours.py` | Se conserva crudo en `ShiftRow`/`employee_months`; semanal convierte a `float` o `None`. |
| Contenedor diario | `people[].dayTimes` | objeto/dict | Horarios y ausencias | Agrupa fuentes de horario y ausencias | `extraction.py`, `schedule_sources.py` | Ausente -> `{}`. |
| Plan publicado | `dayTimes.planned[]` | lista de segmentos | Fuente `planned` | Horario publicado | `schedule_sources.py`, `extraction.py` | Solo segmentos `WORK` forman turno. |
| Borrador | `dayTimes.plannedDraft[]` | lista de segmentos | Fuente `plannedDraft` | Horario borrador | `schedule_sources.py`, `extraction.py` | Puede vaciarse por filtro manual. |
| Flag de edición | `dayTimes.plannedDraftManuallyEdited` | booleano estricto `True`/`False`; puede faltar | Filtro de borrador | Atributo del `plannedDraft`, **no horario** | `schedule_sources.py` | `edited` exige `is True`; `not_edited` exige `is False`; ausente no entra en ninguno. |
| Segmento: tipo de hora | `planned[*].hourType`, `plannedDraft[*].hourType` | texto | Para que el segmento sea trabajo | Clasifica el segmento | `schedule_sources.py`, `extraction.py` | `str(...).upper() == "WORK"`. |
| Segmento: inicio | `...startDateTime` | string ISO compatible con `datetime.fromisoformat` | Segmento WORK válido | Inicio real usado en cálculos | `extraction.py`, `io.py` | Se parsea y se elimina `tzinfo` sin conversión. |
| Segmento: fin | `...endDateTime` | string ISO | Segmento WORK válido | Fin real usado en cálculos | `extraction.py`, `io.py` | Debe cumplir `end > start`. |
| Ausencias | `dayTimes.absences[]` | lista de objetos | Contexto de ausencia | Registros de ausencia del persona-día | `extraction.py` | Solo `VALIDATED`/`APPROVED`. |
| Estado ausencia | `absences[*].status` | texto | Aceptación | Estado del registro | `extraction.py` | `str(...).upper()`. |
| Tipo ausencia: nombre | `absences[*].type.name` | texto | Etiqueta | Nombre preferido | `extraction.py` | Primera opción de etiqueta. |
| Tipo ausencia: descripción | `absences[*].type.description` | texto | Fallback | Descripción alternativa | `extraction.py` | Segunda opción. |
| Id ausencia | `absences[*].id` | cualquiera | Fallback | Identificador usado como etiqueta si falta tipo | `extraction.py` | Tercera opción; si tampoco existe -> `AUSENCIA`. |

## 3. Campos no exigidos por el motor modular

La auditoría del paquete `workforce_validator/` no demuestra dependencia funcional de nombres, apellidos, puestos, departamentos u otros atributos descriptivos de persona. La presentación actual trabaja principalmente con `id_tienda`, `personId`, contrato y resultados derivados.

**COMPORTAMIENTO OBSERVADO:** si una nueva fuente ofrece más atributos, no son necesarios para reproducir el núcleo de resultados verificado actualmente salvo que una extensión futura los consuma.

## 4. Semántica de presencia del empleado

En `extraction.py::extract_data()` un empleado se considera presente en una fecha por el hecho de existir un registro `people[]` válido para ese `operatingDate`, incluso si:

- no tiene ningún segmento WORK;
- su horario seleccionado está vacío;
- el borrador ha sido excluido por el filtro manual;
- tiene una ausencia;
- no tiene ausencia.

Esa presencia se guarda en:

```python
employee_presence_dates[(store_id, person_id)].add(operating_day)
```

y participa en la detección de `AUSENTE TODO EL PERIODO`.

## 5. Resolución actual de `applicableWorkingHours`

### En extracción mensual

Para cada persona-día se ejecuta conceptualmente:

```python
employee_months[(store_id, person_id, YYYY-MM)] = applicable_hours
```

Por tanto, si el mismo empleado aparece varias veces en un mes con valores distintos, **el último registro procesado de ese mes sobrescribe los anteriores**.

### En cada `ShiftRow`

El turno conserva el valor `applicableWorkingHours` leído en ese persona-día.

### En control semanal

`weekly_hours.py` reduce posteriormente los valores a **un único contrato por empleado para todo el periodo**. Inicializa desde `employee_months` y vuelve a sobrescribirlo con cada turno que tenga contrato no vacío; como los turnos se ordenan cronológicamente, el último turno con valor no vacío suele prevalecer.

**COMPORTAMIENTO OBSERVADO:** el control semanal no selecciona contractualmente un valor distinto por semana. Una variación mensual puede acabar aplicándose retrospectivamente a todas las semanas del periodo combinado.

**DUDA FUNCIONAL:** debe confirmarse si esta resolución global es intencionada o una limitación histórica. No debe “corregirse” durante una migración de fuente sin una decisión funcional explícita, porque alteraría resultados.

## 6. Reglas de robustez de estructura

- Raíz JSON: debe ser objeto/dict (`io.py::load_json_bytes`).
- Codificación: UTF-8 o UTF-8 con BOM (`utf-8-sig`).
- `storeDayTimes`: en `extract_data()` debe ser lista; de lo contrario lanza `ValueError`.
- Elementos de `storeDayTimes` que no sean dict o no tengan `operatingDate`: se omiten.
- Elementos de `people` no dict: se omiten.
- Horario seleccionado que no sea lista: se trata como vacío.
- Segmentos no dict: se omiten.
- Ausencias no dict: se omiten.

## 7. Acoplamiento con el formato actual

| Fichero | Función | Campo origen | Tipo de acoplamiento | Impacto al cambiar fuente |
|---|---|---|---|---|
| `workforce_validator/io.py` | `load_json_bytes()` | raíz JSON | Ingestión | Sustituible si la nueva fuente no es JSON. |
| `workforce_validator/schedule_sources.py` | `detect_schedule_sources()` | `storeDayTimes`, `people`, `dayTimes`, `planned`, `plannedDraft`, flag | Ingestión/compatibilidad | Debe adaptarse o trasladarse al adaptador. |
| `workforce_validator/schedule_sources.py` | `filter_schedule_data()` | mismos campos | Ingestión | Debe preservarse semántica, no necesariamente estructura. |
| `workforce_validator/extraction.py` | `extract_data()` | `store`, `storeDayTimes`, `people`, `person`, contrato, horarios, ausencias | Ingestión hacia modelo interno | Principal punto de sustitución. |
| `workforce_validator/dates.py` | `collect_data_dates()` | `storeDayTimes[].operatingDate` | Ingestión temporal | Nueva fuente debe producir cobertura explícita equivalente. |
| `workforce_validator/multi_file.py` | `combine_planning_documents()` | `store.id`, `storeDayTimes` | Compatibilidad multi-JSON | No tiene sentido conservarlo si la nueva fuente ya entrega un periodo unificado. |
| Tests de fixture | varios | estructura actual | Test | Deben conservarse como referencia de compatibilidad y añadirse fixtures canónicos/nueva fuente. |

## 8. Requisito para una nueva fuente

La nueva fuente **no necesita** tener claves llamadas `storeDayTimes`, `people` o `dayTimes`. Necesita poder suministrar información semánticamente equivalente a la descrita en [CANONICAL_DATA_MODEL.md](CANONICAL_DATA_MODEL.md), incluyendo una distinción explícita entre:

1. día disponible en el dataset;
2. empleado presente en la fuente ese día;
3. empleado con turno WORK ese día;
4. empleado con ausencia aceptada ese día.

Confundir cualquiera de esas cuatro condiciones cambiaría el control semanal, la detección de ausencia total o las métricas de descanso.