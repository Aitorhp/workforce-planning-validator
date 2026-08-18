from scripts.workforce_insights_html_patch import patch_workforce_insights


def _source():
    return '''
<html><head></head><body><script>
const I18N_EN={
  // ---- Metodología ----
};
const tabs=[["summary","Resumen"],["weekends","Fines de semana"],["methodology","Metodología"]];
function renderTab(){
  let html="";
  if(S.tab==="summary") html=renderSummary(F);
  else if(S.tab==="weekends") html=renderWeekends(F);
  else html=renderMethodology(F);
}
function renderWeekends(F){
  const employees=[];
  const rot=[];
  let h="";
  h+=chartLines([{name:t("Fin de semana completo"),color:"#2563eb",points:rot.map(r=>({y:r.comp}))},{name:t("Sábado libre"),color:"#22a447",points:rot.map(r=>({y:r.sab}))},{name:t("Domingo libre"),color:"#f59e0b",points:rot.map(r=>({y:r.dom}))}],rot.map(r=>r.label),{h:390,dec:0})+`</div>`;
  return h;
}
/* ---------- Metodología ---------- */
</script></body></html>
'''


def test_html_patch_adds_compact_weekend_percentage_visual():
    patched = patch_workforce_insights(_source())
    assert '{h:255,dec:0}' in patched
    assert 'wfv-weekend-share' in patched
    assert 'Peso de la plantilla con fin de semana completo libre' in patched
    assert 'Porcentaje calculado sobre {n} empleado(s)' in patched


def test_html_patch_adds_workforce_mix_tab_and_renderer():
    patched = patch_workforce_insights(_source())
    assert '["workforceMix","Mix de plantilla"]' in patched
    assert 'function renderWorkforceMix(F)' in patched
    assert 'S.tab==="workforceMix"' in patched
    assert 'Distribución por horas de contrato' in patched
    assert '% horas contratadas' in patched


def test_html_patch_injects_required_styles_and_translations():
    patched = patch_workforce_insights(_source())
    assert 'wfv-workforce-insights-style' in patched
    assert '"Mix de plantilla":"Workforce mix"' in patched
    assert patched.count('function renderWorkforceMix(F)') == 1
