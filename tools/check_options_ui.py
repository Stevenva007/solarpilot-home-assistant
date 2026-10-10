"""Test the actual SG UI with explicit fictitious native-HA API responses.

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
      a.wallbox.charging_profile={phases:1,max_current_a:25,maximum_power_w:5750,current_source:'Wallbox-integratie (fictief)',phase_source:'Handmatig bevestigd'};
      c.hass={...c._hass,user:{is_admin:true},callService:async(...args)=>{window.actuatorCalls.push(args);throw Error('Geen echte bediening in deze proef');},states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};
      window.demoForm={type:'form',flow_id:'fictieve-flow',step_id:'sg_boost',errors:{},data_schema:[
        {name:'entity_id',required:false,selector:{entity:{domain:'switch'}},default:'switch.example_sg_contact'},
        {name:'enabled',required:true,selector:{boolean:{}},default:false},
        {name:'commissioning_confirmed',required:true,selector:{boolean:{}},default:false},
        {name:'watchdog_confirmed',required:true,selector:{boolean:{}},default:false},
        {name:'threshold_w',required:true,selector:{number:{min:500,max:20000,step:50}},default:3000},
        {name:'expected_power_w',required:true,selector:{number:{min:100,max:30000,step:50}},default:3200}
      ]};
      window.apiHandler=async(method,path,data)=>{
        window.apiCalls.push({method,path,data});
        if(method==='delete')return{};
        if(path==='config/config_entries/options/flow')return{type:'menu',step_id:'init',flow_id:'fictieve-flow',menu_options:['comfort_hub','wallbox']};
        if(data.next_step_id==='comfort_hub')return{type:'menu',step_id:'comfort_hub',flow_id:'fictieve-flow',menu_options:['sg_boost','sg_sources','sg_advanced']};
        if(data.next_step_id==='sg_boost')return structuredClone(window.demoForm);
        return{type:'create_entry',title:'Opgeslagen',data:{}};
      };
      c.hass={...c._hass,callApi:(...args)=>window.apiHandler(...args)};
    }''')
    # SG policy help is informational; opening/hovering does not call any actuator.
    page.locator('solar-pilot-card >> button[data-action=view][data-value=comfort]').click()
    panel=page.locator('solar-pilot-card >> .heatpump-sg')
    q=panel.locator('[data-help-key=enabled]')
    q.hover();page.wait_for_timeout(70)
    assert 'Uitleg bij' not in q.get_attribute('title')
    q.click()
    help_host=page.locator('solar-pilot-option-help-dialog');assert help_host.locator('dialog').first.is_visible()
    assert ('SolarPilot '+__import__('json').loads((ROOT/'custom_components/solar_pilot/manifest.json').read_text())['version']) in help_host.locator('dialog').inner_text()
    help_host.locator('.close').first.click()
    assert page.evaluate('window.apiCalls.length===0 && window.actuatorCalls.length===0')

    panel.locator('details[data-ui-key="sg:comfort:details"] > summary').click()
    panel.locator('button[data-action=configure]').click()
    host=page.locator('solar-pilot-options-dialog');assert host.locator('dialog').first.is_visible()
    page.wait_for_selector('solar-pilot-options-dialog >> [name=threshold_w]')
    assert host.locator('.field').count()==host.locator('.field button.help').count()==6
    host.locator('[name=enabled]').check()
    host.locator('[name=commissioning_confirmed]').check()
    host.locator('[name=watchdog_confirmed]').check()
    host.locator('[name=threshold_w]').fill('3500')
    host.locator('[name=expected_power_w]').fill('3400')
    host.locator('button[data-help=watchdog_confirmed]').click()
    nested=host.locator('solar-pilot-option-help-dialog')
    assert nested.locator('dialog').is_visible()
    assert 'terugval' in nested.locator('dialog').inner_text().lower()
    # Main refresh preserves dialogs, draft fields and scroll position.
    page.evaluate('''()=>{window.savedOptions=c._optionsDialog.dialog;window.savedHelp=c._optionsDialog.helpDialog.dialog;
       window.savedOptions.scrollTop=150;window.scrollBefore=window.savedOptions.scrollTop;
       for(let n=0;n<80;n++){const a=structuredClone(c._last.attributes);a.grid_w=-2200-n;c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};}}
    ''')
    assert page.evaluate('c._optionsDialog.dialog===savedOptions && savedOptions.open && savedHelp.open')
    assert page.evaluate('savedOptions.scrollTop===scrollBefore')
    assert host.locator('[name=threshold_w]').input_value()=='3500'
    assert host.locator('[name=expected_power_w]').input_value()=='3400'
    assert page.evaluate('window.apiCalls.length')==3

    for width in (320,390,768,1280):
        page.set_viewport_size({'width':width,'height':900})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
        assert nested.locator('dialog').evaluate('e=>e.scrollWidth<=e.clientWidth+1'),width
        assert host.locator('dialog').first.evaluate('e=>e.scrollWidth<=e.clientWidth+1'),width
        page.screenshot(path=str(output/f'SolarPilot-SG-uitleg-{width}.png'))
    page.keyboard.press('Escape')
    assert not nested.locator('dialog').is_visible()
    assert host.locator('dialog').first.is_visible()
    page.evaluate("c._optionsDialog.shadowRoot.querySelector('h2').textContent='SG-zonneboost · fictief voorbeeld';c._optionsDialog.dialog.scrollTop=0")
    page.screenshot(path=str(output/'SolarPilot-SG-instellingen.png'))
    # Scoped controls work even where HTMLFormElement.elements is unsupported.
    page.evaluate("Object.defineProperty(c._optionsDialog.content.querySelector('form'),'elements',{get(){throw Error('Method not implemented.')}})")
    host.locator('button[type=submit]').dblclick()
    page.wait_for_function("c._optionsDialog.flow===null")
    assert page.evaluate('apiCalls.length')==4
    sent=page.evaluate('apiCalls[3].data')
    assert sent==dict(entity_id='switch.example_sg_contact',enabled=True,
        commissioning_confirmed=True,watchdog_confirmed=True,threshold_w=3500,expected_power_w=3400),sent
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
print('OK: SG opties + uitleg, 80 updates, mobiele/desktop-breedtes, payloads, foutafhandeling, geen actuatoraanroepen. HA API getest met fixtures, niet een echte server.')
