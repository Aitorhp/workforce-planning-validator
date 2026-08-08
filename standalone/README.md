# Validador HTML autónomo

La versión HTML del validador se mantiene junto a Streamlit y tiene dos representaciones:

- `../validador_completo_dos_meses.html`: lanzador interno basado en los payloads versionados.
- `../validador_distribuible.html`: **único fichero que debe entregarse a usuarios**. Es autocontenido y no necesita la carpeta `html_assets`.

## Fichero distribuible

`validador_distribuible.html` se genera mediante:

```bash
python scripts/build_distributable_html.py
```

El generador concatena `../html_assets/reference_payload_*.js`, valida que reconstruyan un HTML completo y escribe de nuevo el fichero distribuible. El resultado puede copiarse, enviarse o abrirse directamente desde un navegador sin Python, Streamlit, servidor ni ficheros auxiliares.

Además, `.github/workflows/build-distributable-html.yml` ejecuta esta regeneración automáticamente cuando cambian los payloads HTML o el propio generador. Si el resultado cambia, GitHub Actions sobrescribe y versiona `validador_distribuible.html` en la rama activa.

## Regla de mantenimiento

A partir de esta versión, cualquier cambio funcional o de presentación que afecte al validador debe evaluarse y, cuando aplique, implementarse en las dos superficies de usuario:

1. Aplicación Streamlit (`dashboard_final.py` y sus módulos de presentación/extensión).
2. Versión HTML de navegador (`validador_completo_dos_meses.html` y sus `reference_payload_*.js`).

**Toda iteración que cambie el HTML debe terminar con la regeneración de `validador_distribuible.html`.** Ese nombre es estable: se sobrescribe, no se crean copias con sufijos de versión.

La lógica de negocio principal debe permanecer en el paquete Python `workforce_validator` siempre que sea posible. Cuando el HTML replique cálculos en JavaScript, los cambios deben mantenerse en paridad con el comportamiento de la aplicación Streamlit y cubrirse con las comprobaciones de paridad existentes o equivalentes.

## Iteración actual

La versión actual incorpora:

- exclusión de semanas completamente vacías de planificación en los análisis temporales;
- horas contractuales visibles en las tablas de empleado/tienda y orden descendente por contrato;
- descarga XLSX de las tablas visibles en HTML;
- reglas editables para fines de semana completos, sábados y domingos libres, recalculadas al modificar sus parámetros.

SHA-256 del HTML fuente reconstruido: `f70cb40696250e6b7cdfe70fd9875db82070497a3e709b1cabb1e381e746b650`.
