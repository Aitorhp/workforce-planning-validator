# Arquitectura

## Capas

1. **Entrada**: `io.py` y `schedule_sources.py`.
2. **Extraccion**: `extraction.py` forma turnos diarios, ausencias y presencia.
3. **Reglas**: `rules/` contiene validaciones independientes.
4. **Calculos**: `weekly_hours.py` y `summary.py`.
5. **Orquestacion**: `engine.py`.
6. **Salidas**: `dataframes.py` y `excel.py`.
7. **Compatibilidad**: `validator_engine.py` y `schedule_adapter.py`.

La interfaz Streamlit consume exclusivamente la API publica y no necesita conocer la implementacion de cada regla.
