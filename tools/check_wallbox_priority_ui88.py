"""Chromium acceptance for timed Wallbox priority, using fictitious data only.

The fake policy responder proves frontend interaction, never device operation.
Run tools/build_example.py first.
"""
import os
from pathlib import Path
import shutil

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("SOLARPILOT_SCREENSHOT_DIR", "/tmp/solarpilot-browser-tests"))
OUT.mkdir(parents=True, exist_ok=True)
errors = []

SETUP = """() => {
 window.c=document.querySelector('solar-pilot-card');window.priorityCalls=[];
 const now=Date.now()/1000;window.prioritySeconds={'30m':1800,'1h':3600,'2h':7200,'3h':10800,'4h':14400,'5h':18000};
 window.choice=(target,option='auto')=>({target,option,mode:option==='auto'?'auto':'wallbox_first',active:option!=='auto',
   eligible:true,duration_s:prioritySeconds[option]??null,expires_at:prioritySeconds[option]?Date.now()/1000+prioritySeconds[option]:null,
   remaining_s:prioritySeconds[option]??null,indefinite:option==='until_auto',label:'synthetisch'});
 window.priorityModel={general:choice('global'),devices:{fan:choice('device:fan'),heater:choice('device:heater')},
   sg_boost:choice('dhw_extra'),available:true,mixed:false,observed_at:now};
 const a=structuredClone(c._last.attributes);a.mode='solar';
 const example=(a.devices||[]).find(d=>d.kind!=='dishwasher')||{};
 a.devices=[{...example,id:'fan',name:'Voorbeeldtoestel',kind:'switch',mode:'auto',available:true,wallbox_first:false,power_w:0},
   {...example,id:'heater',name:'Tweede voorbeeldtoestel',kind:'switch',mode:'auto',available:true,wallbox_first:true,power_w:0},
   {id:'dishwasher',name:'Afwasmachine',kind:'dishwasher',mode:'auto',available:true,power_w:0,dishwasher:{}}];
 a.wallbox={...a.wallbox,enabled:true};a.sg_boost={...a.sg_boost,configured:true};
 a.priority_board={note:'Synthetische bewaarde volgorde',protected:[],rows:[
   {id:'device:fan',device_id:'fan',name:'Voorbeeldtoestel',position:1},
   {id:'wallbox',name:'Auto laden',position:2},
   {id:'device:heater',device_id:'heater',name:'Tweede voorbeeldtoestel',position:3},
   {id:'dhw_extra',name:'Extra SG-zonneboost',position:4}]};
 a.config_entry_id='synthetic-entry';window.priorityAttributes=a;
 window.publishPriority=()=>{const next=structuredClone(priorityAttributes);next.wallbox_priority=structuredClone(priorityModel);
   c.hass={...c._hass,user:{id:'synthetic-admin',is_admin:true},states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:next}}};};
 c._hass.callService=async(domain,service,data)=>{
   priorityCalls.push({domain,service,data});
   if(domain!=='solar_pilot'||service!=='wallbox_priority_control')throw Error('Unexpected physical or unrelated command');
   if(data.target==='global'){
     priorityModel.general=choice('global',data.option);for(const id of Object.keys(priorityModel.devices))priorityModel.devices[id]=choice('device:'+id,data.option);
     priorityModel.sg_boost=choice('dhw_extra',data.option);
   }else if(data.target==='dhw_extra')priorityModel.sg_boost=choice(data.target,data.option);
   else if(data.target.startsWith('device:')&&Object.hasOwn(priorityModel.devices,data.target.slice(7)))priorityModel.devices[data.target.slice(7)]=choice(data.target,data.option);
   else throw Error('Unexpected target');
   priorityModel.mixed=[...Object.values(priorityModel.devices),priorityModel.sg_boost].some(x=>x.option!==priorityModel.general.option);
   priorityModel.observed_at=Date.now()/1000;publishPriority();
 };
 c._view='overview';publishPriority();
} """

with sync_playwright() as p:
    executable = os.environ.get("SOLARPILOT_CHROMIUM_PATH") or shutil.which("chromium")
    browser = p.chromium.launch(**({"executable_path": executable} if executable else {}),
                                headless=True, args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 390, "height": 900}, locale="nl-BE")
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.set_content((ROOT / "SolarPilot-voorbeeld.html").read_text(), wait_until="load")
    page.wait_for_selector("solar-pilot-card >> h1")
    page.evaluate(SETUP)
    card = page.locator("solar-pilot-card")

    def control(target):
        return card.locator(f'[data-wallbox-priority-target="{target}"]')

    def picker():
        return card.locator('[data-wallbox-priority-dialog]')

    assert card.locator('[data-wallbox-priority-target]').count() == 4
    assert card.locator('[data-wallbox-priority-target="device:dishwasher"]').count() == 0
    assert card.locator('[data-wallbox-priority-target="wallbox"]').count() == 0
    assert page.evaluate('priorityCalls.length') == 0

    # Every duration opens the same seven-option picker, fans out through one
    # policy request, and returns all choices to saved defaults on global AUTO.
    for option in ("30m", "1h", "2h", "3h", "4h", "5h", "until_auto"):
        control("global").locator('[data-action="wallbox_priority_toggle"]').click()
        assert picker().locator('dialog').is_visible()
        assert picker().locator('[data-priority-option]').count() == 7
        picker().locator(f'[data-priority-option="{option}"]').click()
        assert not picker().locator('dialog').is_visible()
        assert page.evaluate('priorityCalls.at(-1).data') == {
            "config_entry_id": "synthetic-entry", "target": "global", "option": option}
        assert page.evaluate('[priorityModel.general,...Object.values(priorityModel.devices),priorityModel.sg_boost].every(x=>x.option===priorityCalls.at(-1).data.option)')
        if option == "until_auto":
            assert control("global").locator('[data-wallbox-priority-clock]').inner_text() == "tot ik terug op automatisch zet"
        else:
            assert control("global").locator('[data-wallbox-priority-clock]').inner_text().startswith("Nog ")
        control("global").locator('[data-action="wallbox_priority_toggle"]').click()
        assert page.evaluate('[priorityModel.general,...Object.values(priorityModel.devices),priorityModel.sg_boost].every(x=>x.option==="auto")')

    # An individual remains editable under an active general policy.
    control("global").locator('[data-action="wallbox_priority_toggle"]').click()
    picker().locator('[data-priority-option="2h"]').click()
    control("device:fan").locator('[data-action="wallbox_priority_toggle"]').click()
    assert page.evaluate('priorityModel.general.option') == "2h"
    assert page.evaluate('priorityModel.devices.fan.option') == "auto"
    assert control("global").locator('[data-wallbox-priority-mixed]').is_visible()
    control("device:fan").locator('[data-action="wallbox_priority_toggle"]').click()
    picker().locator('[data-priority-option="30m"]').click()
    assert page.evaluate('priorityModel.devices.fan.option') == "30m"
    assert page.evaluate('priorityModel.sg_boost.option') == "2h"
    control("global").locator('[data-action="wallbox_priority_auto"]').click()
    assert page.evaluate('[priorityModel.general,...Object.values(priorityModel.devices),priorityModel.sg_boost].every(x=>x.option==="auto")')

    # Global AUTO can also clear an individually active policy when the general
    # switch itself is already in AUTO.
    control("device:fan").locator('[data-action="wallbox_priority_toggle"]').click()
    picker().locator('[data-priority-option="1h"]').click()
    control("global").locator('[data-action="wallbox_priority_auto"]').click()
    assert page.evaluate('priorityModel.devices.fan.option') == "auto"

    # The display counts down without WS/service calls, replacing the picker or
    # losing keyboard focus. Telemetry updates preserve the same dialog DOM.
    page.evaluate("""() => {priorityModel.general=choice('global','30m');
      priorityModel.general.expires_at=Date.now()/1000+125;priorityModel.observed_at=Date.now()/1000;publishPriority();}""")
    clock = control("global").locator('[data-wallbox-priority-clock]')
    initial_clock = clock.inner_text()
    count = page.evaluate('priorityCalls.length')
    control("global").locator('[data-action="wallbox_priority_duration"]').click()
    focus = picker().locator('[data-priority-option="1h"]')
    focus.focus()
    page.evaluate("""() => {window.savedPriorityDialog=c._wallboxPriorityDialog;window.savedPriorityNode=savedPriorityDialog.dialog;
      for(let n=0;n<80;n++){priorityAttributes.free_w=1500+n;publishPriority();}}""")
    assert page.evaluate('c._wallboxPriorityDialog===savedPriorityDialog&&savedPriorityDialog.dialog===savedPriorityNode')
    assert focus.evaluate('e=>e===e.getRootNode().activeElement')
    page.wait_for_timeout(2100)
    assert clock.inner_text() != initial_clock
    assert focus.evaluate('e=>e===e.getRootNode().activeElement')
    assert page.evaluate('priorityCalls.length') == count
    for width in (320, 360, 390, 768):
        page.set_viewport_size({"width": width, "height": 1000})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), width
        assert picker().locator('dialog').evaluate('e=>e.scrollWidth<=e.clientWidth+1'), width
        assert control("global").evaluate('e=>e.scrollWidth<=e.clientWidth+1'), width
        page.screenshot(path=str(OUT / f"SolarPilot-Wallbox-voorrang-{width}.png"), full_page=True)
    page.keyboard.press("Escape")
    assert not picker().locator('dialog').is_visible()

    # Restart/reconnect receives the saved absolute end time, never a newly
    # granted full duration; backend AUTO is displayed without a browser write.
    saved_deadline = page.evaluate('priorityModel.general.expires_at')
    page.evaluate('publishPriority()')
    assert page.evaluate('priorityModel.general.expires_at') == saved_deadline
    assert clock.inner_text().startswith('Nog ') and '30:00' not in clock.inner_text()
    page.evaluate("""() => {priorityModel.general.expires_at=Date.now()/1000-1;priorityModel.observed_at=Date.now()/1000;publishPriority();}""")
    assert clock.inner_text() == 'Tijd verstreken · wacht op actuele status'
    page.evaluate("""() => {priorityModel.general=choice('global');for(const id of Object.keys(priorityModel.devices))priorityModel.devices[id]=choice('device:'+id);priorityModel.sg_boost=choice('dhw_extra');priorityModel.mixed=false;priorityModel.observed_at=Date.now()/1000;publishPriority();}""")
    assert clock.inner_text() == 'Automatisch'
    assert page.evaluate('priorityCalls.length') == count

    # Per-device controls remain in the actual device and priority pages; none
    # is created for the dishwasher, native comfort, Wallbox itself or battery.
    for view in ('loads', 'priorities'):
        card.locator(f'button[role="tab"][data-value="{view}"]').click()
        assert card.locator('[data-wallbox-priority-target]').count() == 4
        assert card.locator('[data-wallbox-priority-target="device:dishwasher"]').count() == 0
    card.locator('button[role="tab"][data-value="comfort"]').click()
    assert card.locator('[data-wallbox-priority-target]').count() == 1
    assert control('dhw_extra').is_visible()
    assert card.locator('[data-action="sg_boost_enabled"]').count() == 1
    assert card.locator('[data-sg-manual-control]').count() == 1

    # Permission revocation closes the stale picker and cannot send a command.
    control('dhw_extra').locator('[data-action="wallbox_priority_toggle"]').click()
    assert picker().locator('dialog').is_visible()
    page.evaluate("""() => {c.hass={...c._hass,user:{id:'synthetic-viewer',is_admin:false}};}""")
    assert not picker().locator('dialog').is_visible()
    assert control('dhw_extra').locator('[data-action="wallbox_priority_toggle"]').is_disabled()
    assert page.evaluate("c._setWallboxPriority('dhw_extra','1h')") is False
    assert page.evaluate('priorityCalls.length') == count
    assert not errors, errors
    print('Wallbox priority browser validation: all seven durations, global reset, individual exceptions, clocks, restart deadlines, modal focus, permissions and four mobile widths passed; fictitious policy data only.')
    browser.close()
