# Auditoría temporal

Esta sección es crítica: el sistema maneja simultáneamente día operativo, timestamps de turno, mes calendario, semana lunes-domingo, semana ISO, cobertura de fichero y ventanas de presentación.

## 1. Día operativo

### Origen

`workforce_validator/extraction.py::extract_data()` obtiene:

```python
operating_day = date.fromisoformat(str(store_day["operatingDate"])[:10])
```

Ese valor se convierte en `ShiftRow.work_day` y `AbsenceDay.absence_day`.

### Relación con timestamps

El código **no comprueba** que `shift_start.date()` o `shift_end.date()` coincidan con `operatingDate`. El día operativo es una dimensión independiente aportada por la fuente.

Consecuencia: un turno puede atravesar medianoche y seguir perteneciendo al `operatingDate` de origen. Mes, semana y días consecutivos usan `work_day`; el descanso entre jornadas usa timestamps reales.

### Timezone y offsets

`workforce_validator/io.py::parse_iso_datetime()`:

1. acepta ISO;
2. transforma sufijo `Z` en `+00:00`;
3. usa `datetime.fromisoformat()`;
4. finalmente ejecuta `.replace(tzinfo=None)`.

**COMPORTAMIENTO OBSERVADO:** el offset se elimina **sin convertir el instante**. `09:00+02:00` se convierte en datetime naive `09:00`, no en `07:00 UTC`.

Esto significa que comparaciones posteriores operan sobre las horas de reloj resultantes, no necesariamente sobre instantes absolutos cuando existen offsets diferentes.

**DUDA FUNCIONAL:** confirmar si la fuente garantiza un único timezone/offset coherente. Una migración no debe introducir conversión UTC silenciosa porque cambiaría descansos y franjas.

## 2. Mes

La clave mensual se calcula con `dates.py::month_key(day)`:

```text
YYYY-MM
```

El mes se deriva de `work_day`, no de `shift_start`.

Agregaciones mensuales principales:

- `employee_months`;
- `summary.py::build_monthly_summaries()`;
- mes de incidencias;
- resumen de fines de semana del motor.

### Rachas entre meses

Las rachas se calculan sobre todas las fechas del empleado antes de seleccionar el mes. No se reinician el día 1.

Una racha 29/07–03/08 de seis días:

- tiene longitud 6;
- toca julio y agosto;
- genera incidencia de días consecutivos en ambos meses;
- `max_dias_consecutivos` puede ser 6 tanto en julio como en agosto porque el resumen toma la racha global que toca el mes.

Ver `tests/test_rules.py::test_cross_month_streak_is_reported_in_both_months`.

## 3. Semana

`dates.py::week_start(day)` resta `day.weekday()`, por lo que:

```text
inicio = lunes
fin = domingo
```

`weekly_hours.py` crea `inicio_semana = monday` y `fin_semana = monday + 6 días`.

### ISO week

Los campos se calculan desde el lunes:

```python
monday.isocalendar().year
monday.isocalendar().week
```

Produciendo:

- `ano_iso`;
- `semana_iso`.

En cambio de año ISO, el año ISO puede diferir del año calendario del propio lunes/días cercanos al límite; la fuente de verdad es `date.isocalendar()`.

## 4. Cobertura semanal — fichero vs empleado

`collect_data_dates()` devuelve el conjunto de todos los `operatingDate` presentes en `storeDayTimes`, haya o no turnos.

Para cada semana:

```python
week_days = {lunes, ..., domingo}
covered = len(week_days & data_dates)
complete = covered == 7
```

Campos:

- `dias_cubiertos_fichero = covered`;
- `semana_completa_en_fichero = SI/NO`.

### Diferencia fundamental

**Caso A — el empleado no trabaja el miércoles, pero el fichero contiene miércoles**

```text
data_dates: L M X J V S D
turnos empleado: L M J V
```

`covered = 7`, por tanto la semana es evaluable. Miércoles cuenta como día cubierto sin trabajo.

**Caso B — el fichero no contiene miércoles**

```text
data_dates: L M   J V S D
turnos empleado: L M J V
```

`covered = 6`; la semana se marca `NO EVALUABLE` para todos los empleados, aunque el empleado individualmente no necesitara trabajar ese día.

Esta distinción debe preservarse en cualquier nueva fuente.

### Semana parcial en extremos del dataset

`weekly_hours.py` crea semanas desde el lunes de `min(data_dates)` hasta el lunes de `max(data_dates)`. Las semanas de borde se incluyen, pero si faltan días quedan `NO EVALUABLE`.

## 5. Filtro visual de semanas activas

`review_iteration_dashboard.py::restrict_to_active_planning_weeks()` aplica **solo en presentación** una regla adicional:

- identifica semanas donde existe al menos un turno con `horas_totales > 0` en toda la planificación;
- filtra las vistas semanales/ausencias a esas semanas;
- no modifica el `ValidationResult` original ni los resúmenes mensuales.

Por tanto, una semana puede existir en `result.weekly_rows` y no mostrarse en el dashboard si toda la planificación de la tienda está vacía esa semana.

## 6. Fines de semana — motor mensual

`dates.py::weekend_counts(year, month, worked_days)` usa todos los sábados/domingo del calendario del mes.

### Sábados libres

Todos los sábados calendario no trabajados.

### Domingos libres

Todos los domingos calendario no trabajados.

### Fin de semana completo libre

Se ancla en un sábado del mes y exige:

```text
sábado no trabajado
AND domingo siguiente pertenece al mismo mes
AND domingo no trabajado
```

#### Sábado en un mes + domingo en el siguiente

No cuenta como fin de semana completo en el resumen mensual del motor.

#### Solo existe sábado o domingo en el fichero

El resumen mensual del motor no consulta cobertura: al generar el calendario completo, un día ausente del fichero pero no trabajado puede contabilizarse como libre. Esta limitación es distinta de la lógica del dashboard.

## 7. Fines de semana — presentación actual

`dashboard_extensions.py::prepare_weekend_analysis()` usa `data_dates` reales:

- sábados evaluables = sábados presentes en `data_dates`;
- domingos evaluables = domingos presentes;
- pareja completa = sábado presente cuyo domingo siguiente también está en el `date_set`.

A diferencia del motor mensual, no exige que el domingo pertenezca al mismo mes; una pareja sábado-domingo que cruza fin de mes puede atribuirse al mes del sábado.

Posteriormente `weekend_assignment_dashboard.py::_build_weekend_states()` mantiene la misma idea: un fin completo está anclado en sábado y exige que el domingo exista en el conjunto global evaluable.

**COMPORTAMIENTO OBSERVADO:** existen dos semánticas de fin de semana en el producto: la de `summary.py` y la de la pestaña Streamlit/HTML. Deben compararse por separado en una migración.

## 8. Días consecutivos

`find_consecutive_streaks(days)`:

1. `sorted(set(days))` — elimina duplicados;
2. primera fecha inicia racha;
3. una fecha continúa cuando `current == previous + 1 día`;
4. cualquier hueco rompe la racha.

No depende de `data_dates`: solo de días con `ShiftRow`.

### Entre ficheros

Si dos ficheros mensuales se combinan antes del motor, sus turnos forman una única lista. Una racha 30/08, 31/08, 01/09, 02/09 continúa normalmente.

Si existe un hueco real de fechas con ausencia de turnos, la racha se rompe, independientemente de si el fichero cubre o no esos días.

## 9. Descanso entre jornadas

La regla usa:

```text
current.shift_start - previous.shift_end
```

No usa diferencia entre `work_day`.

Ejemplo atravesando medianoche:

```text
Turno A: 03/08 18:00 -> 04/08 01:00
Turno B: 04/08 12:00 -> 18:00
```

Descanso = 11 h, por lo que cumple exactamente con el límite actual.

Si B empieza a las 11:59, el descanso es 10 h 59 min y genera incidencia.

El mes de la incidencia se toma de `current.work_day`.

## 10. Cambio de año ISO — caso obligatorio

Ejemplo conceptual:

```text
2026-12-28 (lunes) -> semana ISO correspondiente a ese lunes
...
2027-01-03 (domingo) -> misma semana lunes-domingo
```

La fila semanal usa `ano_iso` y `semana_iso` del lunes. No debe construirse manualmente con `calendar year + week number` de cada día.

## 11. Requisitos temporales para una nueva fuente

El adaptador debe entregar explícitamente:

- `work_day`/día operativo;
- timestamps con la misma semántica local que el sistema actual;
- `data_dates` completos, incluidos días con cero turnos;
- presencia del empleado independiente del trabajo;
- continuidad entre ficheros/períodos antes de ejecutar reglas.

Una fuente que solo entregue “días con turnos” no es suficiente para reproducir el control semanal ni las visualizaciones de cobertura.