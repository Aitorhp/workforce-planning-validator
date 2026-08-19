# Ausencias y explicación del déficit semanal

## 1. Extracción de ausencias

Fuente: `workforce_validator/extraction.py::extract_data()`.

Las ausencias se buscan en:

```text
storeDayTimes[].people[].dayTimes.absences[]
```

Solo se conservan registros cuyo estado, normalizado a mayúsculas, sea:

```text
VALIDATED
APPROVED
```

Cualquier otro estado se ignora completamente en `ValidationResult.absences`.

## 2. Etiqueta de tipo

Para cada ausencia aceptada se obtiene el tipo con este orden de fallback:

```text
absence.type.name
-> absence.type.description
-> absence.id
-> "AUSENCIA"
```

Se convierte a texto al crear `AbsenceDay`.

## 3. Deduplicación

La deduplicación se realiza dentro de cada persona-día usando:

```text
(absence_type, absence_status)
```

Por tanto:

- dos registros idénticos de tipo+estado producen una sola `AbsenceDay`;
- el mismo tipo con `VALIDATED` y `APPROVED` produce dos registros distintos;
- el análisis semanal posterior agrupa tipos por día mediante un set, por lo que esos dos estados no duplican el nombre de tipo en `tipos_ausencia`.

## 4. Ausencia y turno el mismo día

Para la explicación semanal, `weekly_hours.py` solo considera como `absence_days` los días que cumplen simultáneamente:

```text
hay ausencia aceptada
AND el empleado NO tiene turno ese día
AND el día está en data_dates
AND el día pertenece a la semana
```

Por tanto, una ausencia aceptada el mismo día que existe un `ShiftRow` **no se utiliza para explicar horas faltantes**.

Esto no elimina la ausencia de `ValidationResult.absences`; simplemente la excluye de ese cálculo explicativo.

## 5. Media de horas diarias

Para cada empleado:

```python
average_daily = sum(shift.worked_hours for todos sus turnos) / numero_de_turnos
```

La media se calcula sobre **todos los turnos del periodo analizado**, no sobre la semana concreta y no sobre horas contractuales.

Si el empleado no tiene turnos, la media es `None`.

## 6. Horas potenciales asociadas a ausencia

Para una semana:

```text
horas_potenciales_asociadas_ausencia
    = número de días de ausencia sin turno
      × media de horas diarias del empleado
```

Se redondea a cuatro decimales.

### Ejemplo

Empleado con turnos del periodo de:

```text
8 h, 6 h, 7 h, 7 h
```

Media diaria:

```text
(8 + 6 + 7 + 7) / 4 = 7 h
```

Si en una semana tiene dos días de ausencia aceptada sin turno:

```text
horas_potenciales_asociadas_ausencia = 2 × 7 = 14 h
```

Estas 14 h **no se suman como trabajo real**. Son una estimación diagnóstica.

## 7. Condición para intentar explicar déficit

La lógica solo intenta explicar déficit por ausencia cuando:

```text
semana completa en fichero
AND horas faltantes > weekly_hours_tolerance
AND existe al menos un día de ausencia aceptada sin turno dentro de data_dates
```

Si no se cumplen esas condiciones, el valor es `NO`, salvo el caso especial `AUSENTE TODO EL PERIODO`.

## 8. Estados de explicación

Orden conceptual:

### `AUSENTE TODO EL PERIODO`

Se activa cuando:

```text
presence_dates no está vacío
AND presence_dates es subconjunto de all_absence_dates
AND el empleado no tiene ningún worked_day
```

`presence_dates` significa fechas en que el empleado aparece en `people[]`, no todas las fechas globales del fichero.

### `NO`

No existe un déficit semanal elegible para explicación por ausencia.

### `AUSENCIA SIN MEDIA CALCULABLE`

Existe déficit + ausencia aplicable, pero el empleado no tiene turnos con los que calcular `average_daily`.

### `PODRIA EXPLICAR TODAS LAS HORAS FALTANTES`

```text
horas_potenciales + tolerance >= horas_faltantes
```

### `PODRIA EXPLICAR PARTE DE LAS HORAS FALTANTES`

Existe estimación positiva, pero no alcanza el déficit dentro de tolerancia.

## 9. Ejemplos numéricos

### Déficit totalmente explicable

```text
Contrato: 40 h
Planificado: 32 h
Faltan: 8 h
Media diaria: 8 h
1 día ausencia sin turno
Potencial: 8 h
```

Resultado: `PODRIA EXPLICAR TODAS LAS HORAS FALTANTES`.

### Déficit parcialmente explicable

```text
Contrato: 40 h
Planificado: 28 h
Faltan: 12 h
Media diaria: 8 h
1 día ausencia sin turno
Potencial: 8 h
```

Resultado: `PODRIA EXPLICAR PARTE DE LAS HORAS FALTANTES`.

### Ausencia que coincide con turno

```text
Miércoles: ausencia VALIDATED + turno WORK de 6 h
```

El miércoles permanece en el dataset de ausencias, pero no cuenta como `dias_ausencia_sin_turno` y no aporta horas potenciales.

### Ausente todo el periodo

Si el empleado aparece en la fuente los días 1–5, tiene ausencia aceptada todos esos días y no tiene ningún turno en todo el dataset, el estado especial es `AUSENTE TODO EL PERIODO`.

## 10. Naturaleza de la estimación

**COMPORTAMIENTO OBSERVADO:** `horas_potenciales_asociadas_ausencia` no representa horas reales de una ausencia ni lee una duración contractual de la ausencia. Multiplica número de días por la media observada de turnos planificados del empleado.

Por tanto debe presentarse como:

> estimación explicativa del déficit

no como:

> horas de ausencia computadas o devengadas.

La presentación actual respeta esa distinción y puede mostrar `planificadas + ausencia estimada`, pero lo utiliza como señal diagnóstica.

## 11. Analytics diarios de ausencia

`workforce_validator/analytics.py::analyze_daily_absences()` genera una fila por cada `data_date`, conservando días con cero ausencias.

Campos:

- `fecha`;
- `empleados_ausentes`: empleados únicos por tienda/persona;
- `registros_ausencia`: número de `AbsenceDay`;
- `tipos_ausencia`: tipos únicos concatenados.

`tests/test_analytics.py` verifica que dos registros de un empleado más otro empleado producen 2 empleados ausentes y 3 registros, y que el día siguiente sin ausencias se conserva con cero.

## 12. Requisitos para una nueva fuente

La nueva fuente debe permitir distinguir:

- estado de ausencia;
- tipo de ausencia;
- fecha operativa;
- empleado/tienda;
- presencia del empleado aunque no trabaje;
- coexistencia de ausencia y turno en el mismo día.

No es suficiente entregar únicamente “días no trabajados”: ausencia y descanso ordinario tienen semántica distinta.

## 13. Dudas funcionales

### DUDA FUNCIONAL

No puede inferirse del código si `APPROVED` y `VALIDATED` tienen exactamente el mismo significado de negocio; el motor los acepta por igual.

### DUDA FUNCIONAL

La media diaria global puede cambiar cuando se amplía el periodo con un segundo fichero, lo que puede cambiar retrospectivamente las horas potenciales explicativas de semanas del primer mes. Es el comportamiento actual y debe contemplarse en el Golden Master antes de considerar una alternativa.