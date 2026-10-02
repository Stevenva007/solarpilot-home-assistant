"""Test the actual beta.30 UI with explicit fictitious native-HA API responses.

No running Home Assistant, cloud access, or physical commands. Requires optional
local playwright + Chromium, not production/test dependencies for the integration.
Set SOLARPILOT_SCREENSHOT_DIR to keep rendered previews outside the repository.
"""
from pathlib import Path
import os
import shutil
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
output=Path(os.environ.get('SOLARPILOT_SCREENSHOT_DIR','/tmp/solarpilot-browser-tests'))
output.mkdir(parents=True,exist_ok=True)
errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=shutil.which('chromium'),headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1000},locale='nl-BE')
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.set_content((ROOT/'SolarPilot-voorbeeld.html').read_text(encoding='utf-8'),wait_until='load')
    page.wait_for_selector('solar-pilot-card >> h1')
    page.evaluate('''() => {
      window.apiCalls=[]; window.actuatorCalls=[];
      const c=document.querySelector('solar-pilot-card');window.c=c;
      const a=structuredClone(c._last.attributes);a.config_entry_id='fictieve-config-entry';
      a.dhw.settings={...a.dhw.settings,morning_enabled:true,morning_time:'09:00:00',morning_c:45,evening_enabled:true,evening_cap_c:55,night_policy:'minimum_until_solar'};
      a.dhw.comfort_plan={projected_c:46.3,reason:'Fictieve voorbeeldgegevens: avondvoorraad gereed',evening_target_c:55,forecast_source:'Fictieve solarhorizon',required_lead_min:95};
      a.dhw.tank_learning={loss_c_h:.25,loss_source:'Voorlopige schatting',heat_c_h:6,heat_source:'Voorlopige schatting'};
      a.wallbox.charging_profile={phases:1,max_current_a:25,maximum_power_w:5750,current_source:'Wallbox-integratie (fictief)',phase_source:'Handmatig bevestigd'};
      c.hass={...c._hass,user:{is_admin:true},callService:async(...args)=>{window.actuatorCalls.push(args);throw Error('Geen echte bediening in deze proef');},states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};
      window.demoForm={type:'form',flow_id:'fictieve-flow',step_id:'dhw_comfort',errors:{},data_schema:[
        {name:'night_policy',required:true,selector:{select:{options:[{value:'base',label:'Bestaand basisregime'},{value:'minimum_until_solar',label:'Minimum bewaken; daarna wachten op zon'}]}},default:'base'},
        {name:'morning_enabled',required:true,selector:{boolean:{}},default:false},
        {name:'morning_time',required:true,selector:{time:{}},default:'09:00:00'},
        {name:'morning_c',required:true,selector:{number:{min:40,max:50,step:1}},default:45},
        {name:'morning_margin_c',required:true,selector:{number:{min:0,max:3,step:.5}},default:1},
        {name:'evening_enabled',required:true,selector:{boolean:{}},default:false},
        {name:'evening_cap_c',required:true,selector:{number:{min:50,max:59,step:1}},default:55},
        {name:'evening_lookahead_h',required:true,selector:{number:{min:.5,max:6,step:.5}},default:3},
        {name:'predictive_cooling_enabled',required:true,selector:{boolean:{}},default:false}
      ]};
      window.apiHandler=async(method,path,data)=>{
        window.apiCalls.push({method,path,data});
        if(method==='delete')return{};
        if(path==='config/config_entries/options/flow')return{type:'menu',step_id:'init',flow_id:'fictieve-flow',menu_options:['dhw_comfort','wallbox']};
        if(data.next_step_id==='dhw_comfort')return structuredClone(window.demoForm);
        return{type:'create_entry',title:'Opgeslagen',data:{}};
      };
      c.hass={...c._hass,callApi:(...args)=>window.apiHandler(...args)};
    }''')
    # Every directly editable scalar/control has question help; hover is harmless.
    page.locator('solar-pilot-card >> button[data-action=view][data-value=comfort]').click()
    assert '46 °C om 09:00' in page.locator('solar-pilot-card >> .comfort-new').inner_text()
    page.locator('solar-pilot-card >> .dhw-rules summary').click()
    control=page.locator('solar-pilot-card >> [data-dhw-setting]').first
    assert control.evaluate("el=>el.nextElementSibling?.dataset.action==='option_help'")
    q=page.locator('solar-pilot-card >> .comfort-new [data-help-key=morning_enabled]')
    q.hover();page.wait_for_timeout(70)
    assert 'Uitleg bij' not in q.get_attribute('title')
    q.click()
    help_host=page.locator('solar-pilot-option-help-dialog');assert help_host.locator('dialog').first.is_visible()
    assert ('SolarPilot '+__import__('json').loads((ROOT/'custom_components/solar_pilot/manifest.json').read_text())['version']) in help_host.locator('dialog').inner_text()
    help_host.locator('.close').first.click()
    assert page.evaluate('window.apiCalls.length===0 && window.actuatorCalls.length===0')

    page.locator('solar-pilot-card >> .comfort-new button[data-action=configure]').click()
    host=page.locator('solar-pilot-options-dialog');assert host.locator('dialog').first.is_visible()
    host.locator('button[data-menu=dhw_comfort]').click()
    page.wait_for_selector('solar-pilot-options-dialog >> [name=morning_c]')
    assert host.locator('.field').count()==host.locator('.field button.help').count()==9
    host.locator('[name=night_policy]').select_option('minimum_until_solar')
    host.locator('[name=morning_enabled]').check()
    host.locator('[name=morning_c]').fill('46')
    host.locator('[name=evening_enabled]').check()
    host.locator('[name=predictive_cooling_enabled]').check()
    host.locator('[name=morning_time]').fill('08:55')
    host.locator('button[data-help=evening_enabled]').click()
    nested=host.locator('solar-pilot-option-help-dialog')
    assert nested.locator('dialog').is_visible()
    assert 'avond' in nested.locator('dialog').inner_text().lower()
    # Main 5s refresh must not close either dialog or reset field edits.
    page.evaluate('''()=>{window.savedOptions=c._optionsDialog.dialog;window.savedHelp=c._optionsDialog.helpDialog.dialog;
       window.savedOptions.scrollTop=150;window.scrollBefore=window.savedOptions.scrollTop;
       for(let n=0;n<80;n++){const a=structuredClone(c._last.attributes);a.grid_w=-2200-n;c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};}}
    ''')
    assert page.evaluate('c._optionsDialog.dialog===savedOptions && savedOptions.open && savedHelp.open')
    assert page.evaluate('savedOptions.scrollTop===scrollBefore')
    assert host.locator('[name=morning_c]').input_value()=='46'
    assert host.locator('[name=morning_time]').input_value()=='08:55'
    assert page.evaluate('window.apiCalls.length')==2

    for width in (320,390,768,1440):
        page.set_viewport_size({'width':width,'height':900})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
        assert nested.locator('dialog').evaluate('e=>e.scrollWidth<=e.clientWidth+1'),width
        assert host.locator('dialog').first.evaluate('e=>e.scrollWidth<=e.clientWidth+1'),width
    page.set_viewport_size({'width':1440,'height':1000})
    page.screenshot(path=str(output/'SolarPilot-beta28-uitleg-desktop.png'))
    page.set_viewport_size({'width':390,'height':844})
    page.screenshot(path=str(output/'SolarPilot-beta28-uitleg-mobiel.png'))
    page.keyboard.press('Escape')
    assert not nested.locator('dialog').is_visible()
    assert host.locator('dialog').first.is_visible()
    # Explicitly label the preview, never imply it is the user's live installation.
    host.locator('[name=morning_c]').fill('45');host.locator('[name=morning_time]').fill('09:00')
    page.set_viewport_size({'width':1440,'height':1000})
    page.evaluate("c._optionsDialog.shadowRoot.querySelector('h2').textContent='Ochtend & avondvoorraad · fictief voorbeeld';c._optionsDialog.dialog.scrollTop=0")
    page.screenshot(path=str(output/'SolarPilot-beta28-instellingen-desktop.png'))
    # Regression: the real HA browser raised "Method not implemented" when
    # reading HTMLFormElement.elements. Read scoped controls instead; no extra
    # permission, validation bypass or actuator request is introduced.
    page.evaluate("Object.defineProperty(c._optionsDialog.content.querySelector('form'),'elements',{get(){throw Error('Method not implemented.')}})")
    host.locator('button[type=submit]').dblclick()
    page.wait_for_function("c._optionsDialog.flow===null")
    assert page.evaluate('apiCalls.length')==3
    sent=page.evaluate('apiCalls[2].data')
    assert sent==dict(night_policy='minimum_until_solar',morning_enabled=True,morning_time='09:00:00',morning_c=45,morning_margin_c=1,evening_enabled=True,evening_cap_c=55,evening_lookahead_h=3,predictive_cooling_enabled=True),sent
    assert page.evaluate('actuatorCalls.length')==0
    host.locator('[data-close]').click()

    # Lost server response must not produce "saved" or automatic retry.
    page.evaluate('''async()=>{window.apiHandler=async(...args)=>{window.apiCalls.push(args);throw Error('Test: verbinding verbroken');};await c._openOptions();}''')
    assert 'niet bevestigd' in host.locator('.error').inner_text()
    assert 'Instellingen opgeslagen' not in host.locator('dialog').first.inner_text()
    host.locator('.close').first.click()

    # Non-admin opens a read-only explanation; no options API invocation.
    before=page.evaluate('apiCalls.length')
    page.evaluate('''async()=>{c.hass={...c._hass,user:{is_admin:false}};await c._openOptions();}''')
    assert 'Alleen een Home Assistant-beheerder' in host.locator('dialog').first.inner_text()
    assert page.evaluate('apiCalls.length')==before
    host.locator('.close').first.click()

    # Actual generic form handles current entity/defaults/multiselect and escapes names.
    page.evaluate('''async()=>{c.hass={...c._hass,user:{is_admin:true},states:{...c._hass.states,'sensor.demo':{state:'25',attributes:{device_class:'current',friendly_name:'<img src=x onerror=alert(1)>'}},'number.demo':{state:'25',attributes:{friendly_name:'Demo stroom'}}}};
      window.apiHandler=async(method,path,data)=>{window.apiCalls.push({method,path,data});if(method==='delete')return{};return{type:'form',step_id:'wallbox',flow_id:'fictieve-flow',data_schema:[
        {name:'max_current_entity',required:false,selector:{entity:{domain:['sensor','number']}},description:{suggested_value:'sensor.demo'}},
        {name:'phases_entity',required:false,selector:{entity:{domain:'sensor'}}},
        {name:'charging_phases',required:true,selector:{select:{options:[{value:'1',label:'1 fase'},{value:'3',label:'3 fasen'}]}},default:'1'},
        {name:'enabled',required:true,selector:{boolean:{}},default:false},
        {name:'extra_test',required:false,selector:{entity:{domain:['sensor','number'],multiple:true}},default:['sensor.demo']}
      ],errors:{}};};await c._openOptions();}''')
    assert host.locator('img').count()==0
    assert host.locator('[name=max_current_entity]').input_value()=='sensor.demo'
    assert host.locator('[name=extra_test]').evaluate('e=>e.selectedOptions[0].value')=='sensor.demo'
    host.locator('[name=charging_phases]').select_option('3')
    host.locator('[name=extra_test]').select_option(['sensor.demo','number.demo'])
    page.evaluate("Object.defineProperty(c._optionsDialog.content.querySelector('form'),'elements',{get(){throw Error('Method not implemented.')}});Object.defineProperty(c._optionsDialog.content.querySelector('[name=extra_test]'),'selectedOptions',{get(){throw Error('Method not implemented.')}})")
    host.locator('button[type=submit]').click()
    last=page.evaluate('apiCalls[apiCalls.length-1].data')
    assert last['charging_phases']=='3' and last['enabled'] is False and 'phases_entity' not in last
    assert sorted(last['extra_test'])==['number.demo','sensor.demo']
    # This fixture returns another form instead of completing the save. Closing
    # its changed, staged values must explicitly confirm that they may be lost.
    def discard_fictitious_options(dialog):
        assert dialog.type == 'confirm'
        assert dialog.message == 'Niet-opgeslagen wijzigingen weggooien?'
        dialog.accept()
    page.once('dialog', discard_fictitious_options)
    host.locator('.close').first.click()
    page.wait_for_function('!c._optionsDialog.dialog.open && !c._uiHistory.constructor.bus.moving')

    # Unsupported selector refuses to submit rather than silently dropping a field.
    page.evaluate('''async()=>{window.apiHandler=async()=>({type:'form',flow_id:'fictieve-flow',step_id:'wallbox',data_schema:[{name:'future_field',required:true,selector:{future_widget:{}}}]});await c._openOptions();}''')
    assert host.locator('button[type=submit]').is_disabled()
    assert 'standaard Home Assistant-configuratie' in host.locator('dialog').first.inner_text()
    host.locator('.close').first.click()
    assert page.evaluate('actuatorCalls.length')==0
    assert not errors,errors
    browser.close()
print('OK: beta.30 opties + uitleg, 80 updates, mobiele/desktop-breedtes, payloads, foutafhandeling, geen actuatoraanroepen. HA API getest met fixtures, niet een echte server.')
