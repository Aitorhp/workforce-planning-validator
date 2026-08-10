from scripts.weekend_html_patch import patch_weekend_assignment


def test_weekend_html_patch_updates_state_bindings_and_renderer():
    source = '''
const I18N_EN = {
  // ---- Metodología ----
};
const S={f:{ wkDev:true, wkStatus:null, wkendReqFull:1, wkendReqSat:1, wkendReqSun:1, wkendAlerts:true }};
function renderWeekends(F){return "legacy";}


/* ---------- Metodología ---------- */
function wire(){
  on("wkendReqSun","change",e=>{S.f.wkendReqSun=Math.max(0,Math.floor(Number(e.target.value)||0));renderTab();});
}
function selectSource(){
  S.f={ wkDev:true, wkStatus:null, wkendReqFull:1, wkendReqSat:1, wkendReqSun:1, wkendAlerts:true };
}
'''
    patched = patch_weekend_assignment(source)
    assert patched.count("wkendReqFlex:0") == 2
    assert "wkendFlexDistinct:false" in patched
    assert 'id="wkendReqFlex"' in patched
    assert 'id="wkendFlexDistinct"' in patched
    assert 'on("wkendReqFlex","change"' in patched
    assert 'on("wkendFlexDistinct","change"' in patched
    assert "No combinable sin reutilizar días" in patched
    assert 'return "legacy"' not in patched
