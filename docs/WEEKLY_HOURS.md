# Horas contractuales y control semanal

## 1. Fuente de verdad

La lógica principal está en `workforce_validator/weekly_hours.py::analyze_weekly_hours()` y consume:

- `shifts: list[ShiftRow]`;
- `employee_months`;
- `data_dates`;
- `absences`;
- `employee_presence_dates`;
- `ValidatorSettings`.

## 2. Resolución de horas contractuales

### Extracción

`extraction.py` lee `person.applicableWorkingHours` en cada persona-día. El valor se guarda:

- en cada `ShiftRow` del día;
- en `employee_months[(store, person, YYYY-MM)]`, donde registros posteriores del mismo mes sobrescriben anteriores.

### Reducción semanal actual

`analyze_weekly_hours()` crea `applicable_by_employee`, no un contrato por semana:

1. recorre `employee_months` y asigna cada valor a `(store, person)`;
2. recorre los turnos y, cuando `shift.applicable_working_hours not in (None, "")`, vuelve a sobrescribirlo.

Como `extract_data()` ordena los turnos cronológicamente, en la práctica el último turno con contrato no vacío suele prevalecer para **todas las semanas del empleado**.

**COMPORTAMIENTO OBSERVADO:** un cambio contractual entre agosto y septiembre puede hacer que el contrato de septiembre se utilice también al evaluar semanas de agosto.

`contract_shift_dashboard.py::build_contract_change_table()` añade una alerta visual cuando detecta cambios entre meses consecutivos, pero no corrige ni sustituye este comportamiento del motor.

## 3. Conversión numérica

Por semana se intenta:

```python
contracted = float(applicable)
```

Si el valor provoca `TypeError` o `ValueError`, el contrato se trata como `None`.

Consecuencias:

- `40` -> `40.0`;
- `"40"` -> `40.0`;
- `None` -> `None`;
- `"texto"` -> `None`;
- `""` -> `None` por error de conversión;
- no existe rechazo específico de booleanos en este punto (`float(True) == 1.0`).

La validación estricta de booleanos de `config.py::_number()` afecta a configuración, no al dato contractual de empleados.

## 4. Construcción de semanas

Si `data_dates` está vacío se devuelve lista vacía.

En caso contrario:

```text
first_week = lunes de min(data_dates)
last_week  = lunes de max(data_dates)
```

Se generan todos los lunes comprendidos entre ambos. Cada semana es lunes-domingo.

## 5. Horas planificadas

Cada `ShiftRow` contribuye:

```python
hours_by_week[(store, person, week_start(shift.work_day))] += shift.worked_hours
```

Por tanto:

```text
horas_planificadas = suma de worked_hours de los turnos cuyo work_day cae en la semana
```

Se redondea a 4 decimales.

## 6. Fórmulas

Con `P = horas_planificadas` y `C = applicableWorkingHours` numérico:

```text
diferencia = P - C
horas_no_planificadas_hasta_contrato = max(C - P, 0)
horas_planificadas_en_exceso         = max(P - C, 0)
```

Todos se redondean a cuatro decimales.

### Ejemplo

Contrato 40 h, planificadas 38 h:

```text
diferencia = -2
faltan = 2
exceso = 0
```

Contrato 40 h, planificadas 42 h:

```text
diferencia = +2
faltan = 0
exceso = 2
```

## 7. Cobertura y evaluabilidad

Para cada semana:

```python
covered = len(week_days & data_dates)
complete = covered == 7
```

`dias_cubiertos_fichero` mide cobertura del **dataset**, no días trabajados por el empleado.

Una semana con 6 fechas en `data_dates` siempre es `NO EVALUABLE`, aunque el empleado tenga turnos perfectamente definidos en los seis días o no tuviera obligación de trabajar el séptimo.

## 8. Estados exactos

Orden de decisión:

```text
1. si semana incompleta -> NO EVALUABLE
2. si contrato no convertible -> SIN HORAS CONTRATO
3. si abs(diferencia) <= tolerancia -> COINCIDE
4. si diferencia < 0 -> FALTAN HORAS
5. en otro caso -> EXCESO HORAS
```

Tolerancia actual: `0.01 h`, desde `config/rules.json`.

| Estado | Condición exacta |
|---|---|
| `NO EVALUABLE` | `dias_cubiertos_fichero != 7` |
| `SIN HORAS CONTRATO` | semana completa y `float(applicable)` falla |
| `COINCIDE` | semana completa, contrato válido y `abs(P-C) <= tolerance` |
| `FALTAN HORAS` | condiciones anteriores falsas y `P-C < 0` |
| `EXCESO HORAS` | condiciones anteriores falsas y `P-C > tolerance` |

`cumple_horas_contrato`:

- `SI` para `COINCIDE`;
- `NO` para `FALTAN HORAS` y `EXCESO HORAS`;
- `NO EVALUABLE` para los demás estados.

## 9. Tolerancia — ejemplos

Con tolerancia `0.01` y contrato `40`:

- `40.00` -> `COINCIDE`;
- `39.995` -> diferencia `-0.005`, `COINCIDE`;
- `40.01` -> diferencia `+0.01`, `COINCIDE` por `<=`;
- `40.0101` -> tras redondeo a 4 decimales, diferencia `+0.0101`, `EXCESO HORAS`.

La comparación usa la diferencia ya redondeada a cuatro decimales.

## 10. Empleados y semanas generadas

El bucle semanal se ejecuta para cada empleado presente en `applicable_by_employee` y para todas las semanas del rango global del dataset.

Esto implica que un empleado puede recibir una fila semanal con `0` horas aunque no aparezca en esa semana concreta, siempre que:

- exista en la estructura contractual reducida;
- la semana esté dentro del rango global.

Si los siete días existen en `data_dates`, esa fila puede ser evaluable contra su contrato global.

## 11. Semana ISO

Campos:

```text
ano_iso     = monday.isocalendar().year
semana_iso  = monday.isocalendar().week
inicio_semana = monday
fin_semana    = monday + 6 días
```

Esto debe conservarse en cambios de año ISO.

## 12. Presentación frente a motor

`review_iteration_dashboard.py::restrict_to_active_planning_weeks()` puede ocultar del dashboard semanas donde no existe **ningún** turno positivo en la tienda. No elimina esas filas del `ValidationResult`.

`contract_hours_heatmap_dashboard.py` puede neutralizar visualmente a cero déficits totalmente explicables por ausencia. Tampoco modifica `weekly_rows`.

El Golden Master debe comparar primero la salida cruda del motor y después, por separado, los datasets filtrados/transformados de presentación.

## 13. Duda funcional principal

### DUDA FUNCIONAL

¿Debe `applicableWorkingHours` ser históricamente variable por semana/mes o es correcto utilizar un único valor por empleado para todo el periodo combinado?

El código actual implementa lo segundo. La migración de fuente debe mantenerlo hasta que se apruebe expresamente un cambio funcional.

## 14. Referencias

- `workforce_validator/extraction.py::extract_data`
- `workforce_validator/weekly_hours.py::analyze_weekly_hours`
- `workforce_validator/dates.py::week_start`
- `config/rules.json`
- `contract_shift_dashboard.py::build_contract_change_table`
- `review_iteration_dashboard.py::restrict_to_active_planning_weeks`
- `contract_hours_heatmap_dashboard.py::apply_contract_hours_heatmap_support`
- `tests/test_regression.py`
- `tests/test_contract_shift_dashboard.py`
- `tests/test_review_iteration_dashboard.py`