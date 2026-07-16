# Añadir una nueva restriccion

1. Añadir su configuracion a `config/rules.json` y a `ValidatorSettings`.
2. Crear un modulo en `workforce_validator/rules/` con una funcion `validate`.
3. Registrar la funcion en `rules/registry.py`.
4. Incorporar el contador mensual correspondiente en `summary.py` si debe aparecer en el dashboard.
5. Crear pruebas de cumplimiento, incumplimiento y limites.
6. Actualizar la prueba de regresion cuando el nuevo resultado sea deliberado.
7. Actualizar README, manual y CHANGELOG.

No deben modificarse otras reglas para incorporar una nueva.
