from __future__ import annotations


def relocate_html_download_block(source: str) -> str:
    """Mueve la descarga HTML al flujo principal del dashboard.

    La transformación de contratos se aplica después de habilitar la carga de
    varios ficheros. En ese punto el primer título de la aplicación está dentro
    del bloque ``if not uploaded_files``. Insertar allí código sin sangría rompe
    la compilación del dashboard generado. Esta función extrae ese bloque y lo
    coloca antes del último título, que pertenece al flujo principal ya
    analizado.
    """
    block_start = "period_start = min(result.data_dates) if result.data_dates else None\n"
    block_end = "    use_container_width=True,\n)\n\n"
    title_anchor = 'st.title("Validador de planificaciones")'

    start = source.find(block_start)
    if start < 0:
        raise RuntimeError("No se encontró el bloque de descarga HTML generado.")
    end = source.find(block_end, start)
    if end < 0:
        raise RuntimeError("No se encontró el final del bloque de descarga HTML.")
    end += len(block_end)

    html_block = source[start:end]
    source_without_block = source[:start] + source[end:]
    title_position = source_without_block.rfind(title_anchor)
    if title_position < 0:
        raise RuntimeError("No se encontró el título principal del dashboard.")

    return (
        source_without_block[:title_position]
        + html_block
        + source_without_block[title_position:]
    )
