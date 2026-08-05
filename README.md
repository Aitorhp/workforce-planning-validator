# Workforce Planning Validator

Aplicacion Streamlit para validar planificaciones de personal y analizar restricciones legales, horas semanales, ausencias y descansos.

## Arranque

```bash
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

En Windows tambien puede utilizarse `lanzar_app.bat`.

## Carga de planificaciones

La interfaz admite un fichero mensual o dos ficheros de meses consecutivos de la misma tienda. Cuando se utilizan dos ficheros, se comprueba que no existan fechas operativas solapadas antes de ejecutar el motor.

## Origenes de horarios

- `planned`: plan publicado.
- `plannedDraft`: borrador generado por el planificador.
- `plannedDraftManuallyEdited` es un indicador booleano y solo se utiliza como filtro de `plannedDraft`.

## Informe HTML compartible

Tras ejecutar la validacion, la barra lateral permite descargar un unico archivo HTML autonomo. El informe:

- contiene las secciones principales del dashboard;
- puede abrirse sin instalar Python ni Streamlit;
- permite cambiar entre castellano e ingles desde la cabecera;
- incluye un mapa empleado-fin de semana con columnas fijas, busqueda y filtro de alertas.

## Arquitectura

La logica productiva se encuentra en `workforce_validator/`:

- `config.py`: carga y valida `config/rules.json`.
- `extraction.py`: transforma el JSON en turnos y ausencias.
- `weekly_hours.py`: control semanal de horas.
- `rules/`: una restriccion por modulo.
- `summary.py`: agregados empleado-mes.
- `engine.py`: orquestacion.
- `dataframes.py`, `excel.py` y `html_report.py`: salidas.

`validator_engine.py` y `schedule_adapter.py` son fachadas de compatibilidad para la interfaz actual.

## Configuracion

Los umbrales se modifican en `config/rules.json`. Tambien puede utilizarse otra configuracion mediante la variable de entorno `WORKFORCE_VALIDATOR_CONFIG`.

## Pruebas

```bash
pytest
```

La suite cubre los limites exactos de las cuatro reglas, fuentes de horarios, filtro manual, configuracion externa, compatibilidad publica, combinacion de ficheros, informe HTML y regresion integral. GitHub Actions ejecuta las pruebas con Python 3.11 y 3.12.

## Añadir una regla

Consulte `docs/ADDING_RULES.md`. Toda regla nueva debe incluir modulo propio, entrada en el registro, configuracion y pruebas unitarias y de regresion.
