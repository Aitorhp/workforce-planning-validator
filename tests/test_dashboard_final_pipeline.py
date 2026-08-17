from dashboard_final import REQUIRED_DASHBOARD_RENDERERS, build_dashboard_source


def test_complete_dashboard_pipeline_preserves_all_renderers_and_compiles():
    source = build_dashboard_source()

    for renderer in REQUIRED_DASHBOARD_RENDERERS:
        assert renderer in source

    assert "Mínimo de sábados o domingos libres" in source
    assert "weekend_flexible_distinct_weekends" in source
    assert "No combinable sin reutilizar días" in source
    assert "tabs = st.tabs" in source

    compile(source, "app.py", "exec")
