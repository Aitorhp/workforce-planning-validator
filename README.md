# Workforce Planning Validator

Aplicacion Streamlit para validar planificaciones de personal y analizar restricciones legales, horas semanales, ausencias y descansos.

## Arranque

```bash
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

En Windows tambien puede utilizarse `lanzar_app.bat`.

## Origenes de horarios

- `planned`: plan publicado.
- `plannedDraft`: borrador generado por el planificador.
- `plannedDraftManuallyEdited` es un indicador booleano y solo se utiliza como filtro de `plannedDraft`.

## Arquitectura

La logica productiva se encuentra en `workforce_validator/`:

- `config.py`: carga y valida `config/rules.json`.
- `extraction.py`: transforma el JSON en turnos y ausencias.
- `weekly_hours.py`: control semanal de horas.
- `rules/`: una restriccion por modulo.
- `summary.py`: agregados empleado-mes.
- `engine.py`: orquestacion.
- `dataframes.py` y `excel.py`: salidas.

`validator_engine.py` y `schedule_adapter.py` son fachadas de compatibilidad para la interfaz actual.

## Configuracion

Los umbrales se modifican en `config/rules.json`. Tambien puede utilizarse otra configuracion mediante la variable de entorno `WORKFORCE_VALIDATOR_CONFIG`.

## Pruebas

```bash
pytest
```

La suite cubre los limites exactos de las cuatro reglas, fuentes de horarios, filtro manual, configuracion externa, compatibilidad publica y regresion integral. GitHub Actions ejecuta las pruebas con Python 3.11 y 3.12.

## Añadir una regla

Consulte `docs/ADDING_RULES.md`. Toda regla nueva debe incluir modulo propio, entrada en el registro, configuracion y pruebas unitarias y de regresion.
