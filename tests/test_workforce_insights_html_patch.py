from scripts.workforce_insights_html_patch import patch_workforce_insights


def _source():
    return '''
<html><head></head><body><script>
const I18N_EN={
  // ---- Metodología ----
};
const TAB_KEYS=["Resumen","Restricciones","Horas contractuales","Cobertura diaria","Balance mañana/tarde","Ausencias","Fines de semana","Metodología"];
function renderWeekends(F){
  const employees=[];
  const rot=[];
  let h="";
  h+=chartLines([{name:t("Fin de semana completo"),color:"#2563eb",points:rot.map(r=>({y:r.comp}))},{name:t("Sábado libre"),color:"#22a447",points:rot.map(r=>({y:r.sab}))},{name:t("Domingo libre"),color:"#f59e0b",points:rot.map(r=>({y:r.dom}))}],rot.map(r=>r.label),{h:390,dec:0})+`</div>`;
  return h;
}
/* ---------- Metodología ---------- */
function renderMetodologia(){return "method";}
const RENDERERS=[renderResumen,renderRestricciones,renderHoras,renderCobertura,renderBalance,renderAusencias,renderWeekends,renderMetodologia];
function renderTab(){
  const F=S.frames; const panel=document.getElementById("panel");
  panel.innerHTML = S.tab===7? renderMetodologia() : RENDERERS[S.tab](F);
}
</script></body></html>
'''


def test_html_patch_adds_compact_weekend_magnitude_visual():
    patched = patch_workforce_insights(_source())
    assert '{h:255,dec:0}' in patched
    assert 'wfv-weekend-share' in patched
    assert 'Magnitud del descanso por fin de semana' in patched
    assert 'Base del porcentaje: {n} empleado(s)' in patched


def test_html_patch_adds_workforce_mix_tab_and_renderer_using_real_navigation_shape():
    patched = patch_workforce_insights(_source())
    assert '"Fines de semana","Mix de plantilla","Metodología"' in patched
    assert 'function renderWorkforceMix(F)' in patched
    assert 'renderWeekends,renderWorkforceMix,renderMetodologia' in patched
    assert 'S.tab===8? renderMetodologia()' in patched
    assert 'Distribución por horas de contrato' in patched
    assert '% horas contratadas' in patched


def test_html_patch_injects_required_styles_and_translations():
    patched = patch_workforce_insights(_source())
    assert 'wfv-workforce-insights-style' in patched
    assert '"Mix de plantilla":"Workforce mix"' in patched
    assert '"Magnitud del descanso por fin de semana":"Weekend rest magnitude"' in patched
    assert patched.count('function renderWorkforceMix(F)') == 1
