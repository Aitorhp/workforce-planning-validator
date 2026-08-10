# Validador HTML autónomo

La versión HTML del validador se mantiene junto a Streamlit y tiene dos representaciones:

- `../validador_completo_dos_meses.html`: lanzador interno basado en los payloads versionados.
- `../validador_distribuible.html`: **único fichero que debe entregarse a usuarios**. Es autocontenido y no necesita la carpeta `html_assets`.

## Fichero distribuible

`validador_distribuible.html` se genera mediante:

```bash
python scripts/build_distributable_html.py
```

El generador concatena `../html_assets/reference_payload_*.js`, valida que reconstruyan un HTML completo, aplica los parches de presentación versionados —incluido `scripts/weekend_html_patch.py` para mantener en paridad las reglas configurables de descanso— y escribe de nuevo el fichero distribuible. El resultado puede copiarse, enviarse o abrirse directamente desde un navegador sin Python, Streamlit, servidor ni ficheros auxiliares.

Además, `.github/workflows/build-distributable-html.yml` ejecuta esta regeneración automáticamente cuando cambian los payloads HTML, el propio generador o el parche de fines de semana. Si el resultado cambia, GitHub Actions sobrescribe y versiona `validador_distribuible.html` en la rama activa.

## Regla de mantenimiento

A partir de esta versión, cualquier cambio funcional o de presentación que afecte al validador debe evaluarse y, cuando aplique, implementarse en las dos superficies de usuario:

1. Aplicación Streamlit (`dashboard_final.py` y sus módulos de presentación/extensión).
2. Versión HTML de navegador (`validador_completo_dos_meses.html`, sus `reference_payload_*.js` y los parches aplicados por el generador).

**Toda iteración que cambie el HTML debe terminar con la regeneración de `validador_distribuible.html`.** Ese nombre es estable: se sobrescribe, no se crean copias con sufijos de versión.

La lógica de negocio principal debe permanecer en el paquete Python `workforce_validator` siempre que sea posible. Cuando el HTML replique cálculos en JavaScript, los cambios deben mantenerse en paridad con el comportamiento de la aplicación Streamlit y cubrirse con las comprobaciones de paridad existentes o equivalentes.

## Iteración actual

La versión actual incorpora:

- exclusión de semanas completamente vacías de planificación en los análisis temporales;
- horas contractuales visibles en las tablas de empleado/tienda y orden descendente por contrato;
- descarga XLSX de las tablas visibles en HTML;
- reglas editables para fines de semana completos, sábados libres, domingos libres y un número mínimo de sábados o domingos libres;
- opción para exigir que los días usados por la regla «sábados o domingos» pertenezcan a fines de semana distintos;
- asignación de días concretos entre reglas sin reutilizar el mismo sábado o domingo, buscando una combinación válida antes de levantar una incidencia de combinación.

SHA-256 del HTML fuente reconstruido: `dd663c22a014f634ebf1dca766174634e8fadb498d87a26bf069b0263f0fcf91`.
