# Validador HTML autónomo

Este directorio contiene la versión HTML autónoma del validador de planificaciones.

## Regla de mantenimiento

A partir de esta versión, cualquier cambio funcional o de presentación que afecte al validador debe evaluarse y, cuando aplique, implementarse en las dos superficies de usuario:

1. Aplicación Streamlit (`dashboard_final.py` y sus módulos de presentación/extensión).
2. HTML autónomo (`standalone/validador_completo_dos_meses.html`).

El HTML debe seguir pudiendo abrirse directamente desde un navegador, sin servidor, instalación de Python ni dependencias externas.

La lógica de negocio principal debe permanecer en el paquete Python `workforce_validator` siempre que sea posible. Cuando el HTML replique cálculos en JavaScript, los cambios deben mantenerse en paridad con el comportamiento de la aplicación Streamlit y cubrirse con las comprobaciones de paridad existentes o equivalentes.

## Referencia

El fichero `standalone/validador_completo_dos_meses.html` es el artefacto HTML de referencia para distribución directa a usuarios.
