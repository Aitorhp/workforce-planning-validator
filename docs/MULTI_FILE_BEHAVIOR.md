# Comportamiento con varios ficheros

## 1. Fuente de verdad

La combinación está implementada en `workforce_validator/multi_file.py::combine_planning_documents()` y se integra en Streamlit mediante `multi_file_dashboard.py::apply_multi_file_support()`.

La función no ejecuta reglas: construye una entrada equivalente a un único JSON y después se invoca el mismo `run_validation()`.

## 2. Número de ficheros admitido

```text
mínimo: 1
máximo: 2
```

Más de dos documentos producen `ValueError`.

## 3. Validaciones por documento

Cada documento debe:

- ser un objeto/dict;
- contener `store.id` no vacío;
- contener al menos una fecha válida obtenible por `collect_data_dates()`;
- contener fechas pertenecientes a **un único mes calendario**.

Un fichero que contenga, por ejemplo, `2026-08-31` y `2026-09-01` se rechaza, aunque solo cubra dos días.

## 4. Reglas al combinar dos ficheros

Los documentos se ordenan por su primera fecha.

Deben cumplir:

1. misma tienda, comparada mediante `str(store_id)`;
2. meses calendario consecutivos;
3. ningún `operatingDate` compartido entre ambos;
4. la última fecha del primero debe ser anterior a la primera fecha del segundo.

### Solapamiento

Cualquier fecha operativa común provoca `ValueError` con mensaje de periodos solapados.

No existe una política de “último fichero gana”, merge por empleado ni deduplicación selectiva.

### Meses consecutivos no significa fechas contiguas

Estos dos ficheros son estructuralmente aceptables:

```text
Fichero A: agosto, fechas 20/08–31/08
Fichero B: septiembre, fechas 10/09–30/09
```

Los meses son consecutivos y no se solapan. El hueco 01/09–09/09 no hace fallar `combine_planning_documents()`.

La falta de fechas se refleja posteriormente en `data_dates` y puede convertir semanas en `NO EVALUABLE`.

## 5. Construcción del documento combinado

La función:

1. hace `deepcopy` del primer documento cronológico;
2. concatena los `storeDayTimes` de cada documento;
3. ordena los días por representación textual de `operatingDate`;
4. sustituye `combined["storeDayTimes"]` por esa lista.

No modifica la lógica de horarios, ausencias o contratos.

## 6. Deduplicación

### Entre ficheros

El solapamiento de fechas se rechaza antes de combinar, por lo que no existe deduplicación entre dos documentos.

### Dentro de un mismo fichero

**COMPORTAMIENTO OBSERVADO:** no existe validación explícita contra dos entradas `storeDayTimes` con el mismo `operatingDate` dentro del mismo documento.

`collect_data_dates()` usa un conjunto y ocultaría el duplicado para cobertura, pero `extract_data()` recorrería ambos bloques y podría:

- duplicar turnos;
- sumar horas duplicadas;
- sobrescribir contrato mensual;
- procesar presencia/ausencias repetidas.

**RECOMENDACIÓN:** incluir este caso en calidad de entrada o en un adaptador futuro, pero no cambiarlo silenciosamente durante la migración.

## 7. Efecto en rachas de días trabajados

Como los turnos combinados se entregan juntos a `find_consecutive_streaks()`, la continuidad atraviesa la frontera de fichero y de mes.

Ejemplo:

```text
30/08 WORK
31/08 WORK
01/09 WORK
02/09 WORK
```

Forma una única racha de cuatro días.

Por ello usar dos ficheros consecutivos **sí puede cambiar** `max_dias_consecutivos` e incidencias respecto a analizarlos por separado.

## 8. Efecto en descanso entre jornadas

Los turnos de ambos meses se ordenan juntos por timestamp. El último turno del primer fichero y el primero del segundo se comparan como cualquier par consecutivo.

Por tanto, la carga doble puede revelar una incidencia de descanso que no existe al validar cada fichero de forma aislada.

## 9. Efecto en semanas evaluables

La unión de `storeDayTimes` amplía `data_dates` antes de `analyze_weekly_hours()`.

Ejemplo:

```text
Agosto aporta lunes 31/08
Septiembre aporta martes 01/09–domingo 06/09
```

La combinación permite tener los siete días de la semana lunes-domingo y volverla evaluable. Analizados por separado, ambos ficheros tendrían una semana de borde incompleta.

Por tanto, el análisis conjunto puede cambiar:

- `dias_cubiertos_fichero`;
- `semana_completa_en_fichero`;
- `estado_planificacion`;
- déficit/exceso;
- explicación por ausencias.

## 10. Efecto en horas contractuales

El análisis conjunto puede cambiar el contrato efectivo global del empleado, porque `weekly_hours.py` termina conservando un único `applicableWorkingHours` por empleado y los turnos posteriores pueden sobrescribir el valor.

Así, añadir septiembre puede modificar el contrato utilizado para evaluar agosto.

Este comportamiento está documentado en [WEEKLY_HOURS.md](WEEKLY_HOURS.md) y debe preservarse en el Golden Master inicial.

## 11. Efecto en ausencias

Las ausencias de ambos documentos se combinan en una única lista. Además:

- `average_daily` se calcula sobre todos los turnos del periodo combinado;
- `AUSENTE TODO EL PERIODO` usa todas las fechas de presencia y ausencia;
- una ausencia de una semana de frontera puede pasar a estar dentro de una semana completa gracias al segundo fichero.

Por tanto, la carga doble puede cambiar la interpretación explicativa de ausencias.

## 12. Efecto en meses

Los resúmenes siguen teniendo granularidad empleado-mes. Combinar no fusiona agosto y septiembre en una fila.

Sin embargo, cálculos globales pueden cruzar el límite:

- rachas;
- descanso entre jornadas;
- contrato semanal efectivo;
- media diaria para ausencias.

## 13. Efecto en fines de semana

### Resumen mensual del motor

`summary.py` sigue calculando cada mes por calendario. Una pareja sábado-domingo que cruza de mes no se considera fin completo en `dates.weekend_counts()`.

### Dashboard actual

La presentación utiliza el `data_dates` combinado y puede emparejar un sábado de un mes con el domingo siguiente del otro mes si ambos están cubiertos.

Por tanto, combinar dos meses también puede modificar el análisis visual de fines de semana de frontera.

## 14. Pruebas existentes

`tests/test_multi_file.py` cubre:

- un documento;
- orden cronológico de dos meses consecutivos;
- rechazo de tiendas distintas;
- rechazo de solapamiento;
- rechazo de meses no consecutivos;
- obligación de un único mes por fichero.

`tests/test_multi_file_dashboard.py` cubre la integración de la carga múltiple en el source del dashboard.

## 15. Casos Golden Master obligatorios

### Dos ficheros contiguos

Esperado: combinar, ejecutar como un solo periodo y permitir continuidad temporal entre ambos.

### Dos ficheros solapados

Esperado: `combine_planning_documents()` debe lanzar `ValueError`; no debe llegar al motor.

### Dos meses consecutivos con hueco de fechas

Esperado: combinación permitida; las semanas afectadas reflejan cobertura incompleta.

## 16. Nueva fuente

Si la futura fuente ya entrega un rango temporal unificado —API, DB, CSV consolidado— no es necesario emular dos JSON ni conservar `combine_planning_documents()` como interfaz. Lo que debe preservarse es el **conjunto canónico final de fechas, turnos, contratos, presencia y ausencias** antes de llamar al motor.