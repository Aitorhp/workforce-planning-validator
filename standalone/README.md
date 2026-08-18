# Validador HTML autónomo

La versión HTML del validador se mantiene junto a Streamlit y tiene dos representaciones:

- `../validador_completo_dos_meses.html`: lanzador interno basado en los payloads versionados.
- `../validador_distribuible.html`: **único fichero que debe entregarse a usuarios**. Es autocontenido y no necesita la carpeta `html_assets`.

## Fichero distribuible

`validador_distribuible.html` se genera mediante:

```bash
python scripts/build_distributable_html.py
```

El generador concatena `../html_assets/reference_payload_*.js`, valida que reconstruyan un HTML completo, aplica todos los parches de presentación versionados —incluidos `scripts/weekend_html_patch.py` y `scripts/workforce_insights_html_patch.py`— y escribe de nuevo el fichero distribuible. El resultado puede copiarse, enviarse o abrirse directamente desde un navegador sin Python, Streamlit, servidor ni ficheros auxiliares.

Además, `.github/workflows/build-distributable-html.yml` ejecuta esta regeneración automáticamente cuando cambian los payloads HTML, el propio generador o cualquiera de los parches HTML registrados. Si el resultado cambia, GitHub Actions sobrescribe y versiona `validador_distribuible.html` en la rama activa.

## Regla de mantenimiento obligatoria

El proyecto tiene dos superficies de usuario y **todo cambio visible o funcional debe mantenerse en paridad en ambas**:

1. Aplicación Streamlit (`dashboard_final.py` y sus módulos de presentación/extensión).
2. Versión HTML de navegador (`validador_completo_dos_meses.html`, `reference_payload_*.js`, los parches de `scripts/` y `validador_distribuible.html`).

Esto incluye, sin excepción por defecto, nuevas pestañas, gráficos, tablas, filtros, textos, KPIs, navegación y cambios de comportamiento. Solo puede omitirse uno de los soportes cuando el cambio sea técnicamente exclusivo de la otra superficie y esa excepción quede documentada expresamente en la propia iteración.

**Una iteración de interfaz no se considera terminada hasta comprobar ambos soportes.** Si afecta al HTML, debe actualizarse el parche/generador correspondiente y terminar con la regeneración de `validador_distribuible.html`. Ese nombre es estable: se sobrescribe, no se crean copias con sufijos de versión. El HTML distribuible generado no se edita manualmente como fuente de verdad.

La lógica de negocio principal debe permanecer en el paquete Python `workforce_validator` siempre que sea posible. Cuando el HTML replique cálculos en JavaScript, los cambios deben mantenerse en paridad con el comportamiento de la aplicación Streamlit y cubrirse con las comprobaciones de paridad existentes o equivalentes.

## Iteración actual

La versión actual incorpora:

- exclusión de semanas completamente vacías de planificación en los análisis temporales;
- horas contractuales visibles en las tablas de empleado/tienda y orden descendente por contrato;
- descarga XLSX de las tablas visibles en HTML;
- reglas editables para fines de semana completos, sábados libres, domingos libres y un número mínimo de sábados o domingos libres;
- opción para exigir que los días usados por la regla «sábados o domingos» pertenezcan a fines de semana distintos;
- asignación de días concretos entre reglas sin reutilizar el mismo sábado o domingo, buscando una combinación válida antes de levantar una incidencia de combinación;
- visualización compacta de rotación de fines de semana y porcentaje de plantilla con fin de semana completo libre;
- pestaña informativa `Mix de plantilla` con empleados por horas contractuales, peso sobre la plantilla y peso sobre las horas contratadas semanales.
