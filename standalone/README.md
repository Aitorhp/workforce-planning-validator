# Validador HTML autónomo

La versión de navegador de referencia se lanza desde `../validador_completo_dos_meses.html`.

El lanzador reconstruye el HTML de referencia a partir de los ficheros `../html_assets/reference_payload_*.js`. Estos assets contienen comprimido el HTML autónomo entregado como referencia y permiten mantenerlo versionado junto a la aplicación Streamlit.

Para distribuir esta versión de navegador deben conservarse juntos el fichero `validador_completo_dos_meses.html` y el directorio `html_assets`. No requiere servidor, instalación de Python ni ejecución de Streamlit.

## Regla de mantenimiento

A partir de esta versión, cualquier cambio funcional o de presentación que afecte al validador debe evaluarse y, cuando aplique, implementarse en las dos superficies de usuario:

1. Aplicación Streamlit (`dashboard_final.py` y sus módulos de presentación/extensión).
2. Versión HTML de navegador (`validador_completo_dos_meses.html` y sus `reference_payload_*.js`).

La lógica de negocio principal debe permanecer en el paquete Python `workforce_validator` siempre que sea posible. Cuando el HTML replique cálculos en JavaScript, los cambios deben mantenerse en paridad con el comportamiento de la aplicación Streamlit y cubrirse con las comprobaciones de paridad existentes o equivalentes.

## Referencia importada

SHA-256 del HTML fuente incorporado: `e3f19d2603bede97523751948e03cca18e8e8569a39004cf319413c1017091c2`.
