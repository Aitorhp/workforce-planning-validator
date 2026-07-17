# Changelog

## 2.2.0 - 2026-07-17

- Sustituye el gráfico de sesgo mañana/tarde por una comparación de mañanas y tardes medias por semana y empleado.
- Añade un selector global de semana en el panel lateral.
- El filtro semanal se aplica a turnos, horas contractuales, cobertura diaria, balance de franjas, ausencias e incidencias.
- Mantiene sin reinterpretar los resúmenes cuya unidad original es empleado-mes.
- Actualiza el generador del manual funcional con el balance de franjas, el filtro semanal y la explicación de déficits por ausencias.

## 2.1.0 - 2026-07-17

- Añade el balance de turnos de mañana y tarde con corte a las 13:00.
- Incorpora el índice de equilibrio y la identificación de empleados sin rotación.
- Añade el calendario diario de ausencias y el diagnóstico contractual asociado a ausencias.

## 1.1.0 - 2026-07-16

- Modulariza el motor en el paquete `workforce_validator`.
- Externaliza umbrales en `config/rules.json`.
- Separa las cuatro restricciones en módulos independientes.
- Añade pruebas unitarias de límites, fuentes, configuración y API pública.
- Añade una prueba de regresión integral y CI con GitHub Actions.
- Mantiene `validator_engine.py` y `schedule_adapter.py` como fachadas compatibles.
