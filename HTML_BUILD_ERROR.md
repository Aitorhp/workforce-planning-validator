# Error de generación del HTML distribuible

La generación automática ha fallado. Este fichero se versiona temporalmente para diagnosticar el parche real aplicado a los payloads.

```text
Traceback (most recent call last):
  File "/home/runner/work/workforce-planning-validator/workforce-planning-validator/scripts/build_distributable_html.py", line 290, in <module>
    main()
  File "/home/runner/work/workforce-planning-validator/workforce-planning-validator/scripts/build_distributable_html.py", line 284, in main
    html = build_html(payload)
           ^^^^^^^^^^^^^^^^^^^
  File "/home/runner/work/workforce-planning-validator/workforce-planning-validator/scripts/build_distributable_html.py", line 274, in build_html
    payload, source = patched_payload(payload)
                      ^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/runner/work/workforce-planning-validator/workforce-planning-validator/scripts/build_distributable_html.py", line 264, in patched_payload
    source = patch_workforce_insights(source)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/runner/work/workforce-planning-validator/workforce-planning-validator/scripts/workforce_insights_html_patch.py", line 179, in patch_workforce_insights
    source = _insert_mix_tab(source)
             ^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/runner/work/workforce-planning-validator/workforce-planning-validator/scripts/workforce_insights_html_patch.py", line 34, in _insert_mix_tab
    raise ValueError(
ValueError: Parche HTML de insights: no se encontró la lista de pestañas para insertar Mix de plantilla
```
