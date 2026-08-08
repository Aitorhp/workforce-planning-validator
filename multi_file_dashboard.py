from __future__ import annotations


def apply_multi_file_support(source: str) -> str:
    """Adapta la interfaz Streamlit para validar uno o dos JSON mensuales."""
    source = source.replace(
        "    load_json_bytes,\n",
        "    load_json_bytes,\n    combine_planning_documents,\n",
        1,
    )

    old_cache = '''@st.cache_data(show_spinner=False)
def parse_file(file_bytes: bytes):
    data = load_json_bytes(file_bytes)
    return data, detect_schedule_sources(data)


@st.cache_data(show_spinner=False)
def analyse(file_bytes: bytes, schedule_source: str):
    data = load_json_bytes(file_bytes)
    result = run_validation(data, schedule_source)
    return result, result_dataframes(result)
'''
    new_cache = '''@st.cache_data(show_spinner=False)
def parse_files(file_payloads: tuple[bytes, ...]):
    documents = [load_json_bytes(file_bytes) for file_bytes in file_payloads]
    data = combine_planning_documents(documents)
    return data, detect_schedule_sources(data)


@st.cache_data(show_spinner=False)
def analyse(file_payloads: tuple[bytes, ...], schedule_source: str):
    documents = [load_json_bytes(file_bytes) for file_bytes in file_payloads]
    data = combine_planning_documents(documents)
    result = run_validation(data, schedule_source)
    return result, result_dataframes(result)
'''
    if old_cache not in source:
        raise RuntimeError("No se encontró el bloque de carga y análisis esperado.")
    source = source.replace(old_cache, new_cache, 1)

    old_upload = '''st.sidebar.title("Validador")
uploaded = st.sidebar.file_uploader("Subir planificacion JSON/TXT", type=["json","txt"])
if uploaded is None:
    st.title("Validador de planificaciones")
    st.info("Sube un fichero para detectar los origenes de horarios disponibles.")
    st.stop()

try:
    data, source_stats = parse_file(uploaded.getvalue())
except Exception as exc:
    st.error(f"No se ha podido leer el fichero: {exc}")
    st.stop()
'''
    new_upload = '''st.sidebar.title("Validador")
uploaded_files = st.sidebar.file_uploader(
    "Subir una o dos planificaciones JSON/TXT",
    type=["json", "txt"],
    accept_multiple_files=True,
    help="Puede cargar un único mes o dos meses consecutivos de la misma tienda. Los periodos no pueden solaparse.",
)
if not uploaded_files:
    st.title("Validador de planificaciones")
    st.info("Sube uno o dos ficheros para detectar los orígenes de horarios disponibles.")
    st.stop()
if len(uploaded_files) > 2:
    st.error("Solo se admite un máximo de dos ficheros.")
    st.stop()

file_payloads = tuple(uploaded.getvalue() for uploaded in uploaded_files)
file_names = [uploaded.name for uploaded in uploaded_files]
try:
    data, source_stats = parse_files(file_payloads)
except Exception as exc:
    st.error(f"No se han podido combinar los ficheros: {exc}")
    st.stop()
'''
    if old_upload not in source:
        raise RuntimeError("No se encontró el bloque de subida esperado.")
    source = source.replace(old_upload, new_upload, 1)

    old_analyse = '        result, frames = analyse(uploaded.getvalue(), selected_source)'
    new_analyse = '        result, frames = analyse(file_payloads, selected_source)'
    if old_analyse not in source:
        raise RuntimeError("No se encontró la llamada de análisis esperada.")
    source = source.replace(old_analyse, new_analyse, 1)

    old_file_caption = 'st.sidebar.caption(f"Fichero: {uploaded.name}")\nrender_rules_panel()'
    new_file_caption = '''st.sidebar.markdown("**Ficheros analizados:**")
for file_name in file_names:
    st.sidebar.caption(f"• {file_name}")
if result.data_dates:
    period_start = min(result.data_dates)
    period_end = max(result.data_dates)
    st.sidebar.caption(f"Periodo combinado: {period_start:%d/%m/%Y} - {period_end:%d/%m/%Y}")
render_rules_panel()'''
    if old_file_caption not in source:
        raise RuntimeError("No se encontró el bloque de identificación de fichero esperado.")
    source = source.replace(old_file_caption, new_file_caption, 1)

    old_source_box = '''f'<div class="source-box"><b>Origen analizado:</b> {SCHEDULE_SOURCES[selected_source]} '
    f'(<code>{selected_source}</code>). Todas las incidencias, horas y visualizaciones corresponden exclusivamente a esta fuente.</div>','''
    new_source_box = '''f'<div class="source-box"><b>Origen analizado:</b> {SCHEDULE_SOURCES[selected_source]} '
    f'(<code>{selected_source}</code>). Se han combinado {len(uploaded_files)} fichero(s) de la misma tienda; '
    f'todas las incidencias, horas y visualizaciones corresponden al periodo completo.</div>','''
    if old_source_box in source:
        source = source.replace(old_source_box, new_source_box, 1)

    return source
