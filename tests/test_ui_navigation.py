"""Navigation contract; real history behaviour is checked by the browser probe."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CARD = (ROOT / "custom_components/solar_pilot/frontend/solar-pilot-card.js").read_text(encoding="utf-8")
OPTIONS = (ROOT / "custom_components/solar_pilot/frontend/option-help.js").read_text(encoding="utf-8")


def test_ui_history_is_namespaced_same_url_and_retains_ha_state():
    history_code = CARD.split("class SolarPilotUiHistory", 1)[1].split("class SolarPilotCard", 1)[0]
    assert "solarPilotUi:{session:this.bus.session,entry}" in history_code
    assert "{...history.state}" in history_code
    assert "history.pushState(SolarPilotUiHistory._state(b.cursor),'',b.url)" in history_code
    assert "location.href===b.url" in history_code
    assert "window.addEventListener('popstate',b.listener)" in history_code
    assert "window.removeEventListener('popstate',b.listener)" in history_code
    assert "this.bus.cards" in history_code
    assert "form.elements" not in history_code
    assert "callService" not in history_code


def test_back_and_forward_do_not_replay_native_form_submissions():
    back_code = OPTIONS.split("async _back(){", 1)[1].split("_controls(disabled)", 1)[0]
    assert "{next_step_id}" in back_code
    assert "this.flow?.type!=='menu'" in back_code
    assert "'delete'" in back_code
    assert "{handler:this.entryId}" in back_code
    assert "form.elements" not in back_code
    assert "device_id" not in back_code
    assert "{values}" not in back_code
    assert "this._uiHistory.track(this._optionsDialog,()=>this._optionsDialog.open(this._hass,this._last?.attributes?.config_entry_id))" in CARD
    assert "this.uiHistory?.step(this,async()=>" in OPTIONS
    assert "this.uiHistory?.back(this)" in OPTIONS
    assert "Je eerdere invoer is niet teruggezet" in OPTIONS


def test_settings_has_visible_back_and_both_dirty_and_busy_guards():
    assert 'class="back" type="button" aria-label="Terug naar SolarPilot">‹ Terug' in OPTIONS
    assert "this._dirty||this._draftStarted" in OPTIONS
    assert "Niet-opgeslagen wijzigingen weggooien?" in OPTIONS
    assert "if(this._busy||!this._open)return" in OPTIONS
    assert "if(this._busy||!force&&!this._discard())return false" in OPTIONS
    assert "this._draftStarted=true" in OPTIONS
    assert "const path=this.flow?.type==='menu'?this._menuPath.slice(0,-1):[...this._formParent]" in OPTIONS


def test_modal_back_preserves_drafts_when_declined_and_never_moves_on_disconnect():
    history_code = CARD.split("class SolarPilotUiHistory", 1)[1].split("class SolarPilotCard", 1)[0]
    disconnect = history_code.split("disconnect(){", 1)[1].split("static _snapshot", 1)[0]
    assert "history.go" not in disconnect
    assert "e._saving" in history_code
    assert "e.localName==='solar-pilot-options-dialog'&&e._busy" in history_code
    assert "history.go(previous-next)" in history_code
    assert "b.recovering=true" in history_code
    assert "dialog.addEventListener('cancel'" in history_code
    assert "this._uiHistory.disconnect();" in CARD
    assert "this._optionsDialog?.close(true)" in CARD
