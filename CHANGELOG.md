# Changelog

## 1.1.0 - 2026-07-16

- Modulariza el motor en el paquete `workforce_validator`.
- Externaliza umbrales en `config/rules.json`.
- Separa las cuatro restricciones en módulos independientes.
- Añade pruebas unitarias de límites, fuentes, configuración y API pública.
- Añade una prueba de regresión integral y CI con GitHub Actions.
- Mantiene `validator_engine.py` y `schedule_adapter.py` como fachadas compatibles.
