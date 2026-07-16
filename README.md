# Validador de planificaciones Streamlit

La aplicación permite cargar un JSON/TXT y elegir qué origen de horarios se valida:

- `planned`: plan publicado.
- `plannedDraft`: borrador generado por el planificador.
- `plannedDraftManuallyEdited`: borrador editado manualmente.

El selector aparece después de cargar el fichero y solo muestra fuentes con segmentos `WORK`. Al cambiar la selección, todo el motor se ejecuta de nuevo sobre esa fuente: turnos, restricciones, horas semanales, descansos, fines de semana y relación con ausencias. Las fuentes nunca se mezclan.

## Ejecución en Windows

1. Descomprime el proyecto.
2. Haz doble clic en `lanzar_app.bat`.
3. Sube el JSON o TXT.
4. Selecciona el origen de horarios en el panel lateral.

Ejecución manual:

```bash
py -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Archivos

- `app.py`: interfaz Streamlit y visualizaciones.
- `validator_engine.py`: extracción parametrizable y motor de cálculo.
- `MANUAL_CALCULOS.docx`: metodología completa.
- `tests/test_schedule_sources.py`: pruebas de aislamiento entre fuentes.
