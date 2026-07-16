# Validador de planificaciones Streamlit

La aplicacion analiza los dos origenes reales de horarios del JSON:

- `planned`: plan publicado.
- `plannedDraft`: borrador generado por el planificador.

`plannedDraftManuallyEdited` no es una lista de horarios. Es un indicador booleano asociado a cada registro persona-dia de `plannedDraft`.

Cuando se selecciona `plannedDraft`, la interfaz permite filtrar:

- todos los borradores;
- solo `plannedDraftManuallyEdited = true`;
- solo `plannedDraftManuallyEdited = false`.

## Arranque

```bash
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

`streamlit_app.py` es el punto de entrada recomendado. Mantiene compatibilidad con la version anterior de `app.py` y aplica el modelo corregido mediante `schedule_adapter.py`.

## Logica

- `planned` y `plannedDraft` nunca se mezclan.
- El filtro manual solo aplica a `plannedDraft`.
- El dashboard muestra cobertura temporal por origen.
- Si no existen registros editados manualmente, la opcion no aparece y se informa del recuento.
- Todas las incidencias, horas, descansos y KPI se recalculan para el universo seleccionado.

## Pruebas

```bash
pytest -q
```
