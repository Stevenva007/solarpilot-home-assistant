"""Actual browser code with native options-flow fixtures; never device commands."""
from pathlib import Path
import json,os,shutil
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('SOLARPILOT_SCREENSHOT_DIR','/tmp/solarpilot-ui34'));OUT.mkdir(parents=True,exist_ok=True)
errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=shutil.which('chromium'),headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1080},locale='nl-BE')
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.set_content((ROOT/'SolarPilot-voorbeeld.html').read_text(),wait_until='load')
    page.wait_for_selector('solar-pilot-card >> h1')
    page.evaluate('''()=>{
      const c=document.querySelector('solar-pilot-card');window.c=c;
      window.apiCalls=[];window.actuatorCalls=[];window.historyReads=[];
      const a=structuredClone(c._last.attributes);a.mode='solar';a.config_entry_id='fixture-entry';a.editable=false;
      a.device_management={editable_while_active:true,status:'Voorbeeldgegevens — regeling blijft actief tijdens configureren.',error:'',
        pending:[{key:'device:dryer',name:'Ontvochtiger kelder',reason:'Toestel is actief; huidige koppeling blijft gelden tot vrijgave'}],
        devices:[{id:'dw',name:'Afwasmachine keuken',kind:'dishwasher',appliance_type:'dishwasher',mode:'auto',on:true},
                 {id:'dryer',name:'Ontvochtiger kelder',kind:'switch',appliance_type:'other',mode:'auto',on:true,pending:'Wacht op veilige vrijgave'}],
        archives:[{id:'old_dw',name:'Vorige afwasmachine',archived_at:1790710000}]};
      window.choiceForm={type:'form',flow_id:'fixture-flow',step_id:'apply_changes',errors:{},description_placeholders:{summary:'Afwasmachine: direct toepassen zonder herladen; huidige aanvraag blijft op dezelfde dag.',issue:''},data_schema:[
        {name:'request_scope',required:true,default:'future',selector:{select:{options:[{value:'future',label:'Alleen volgende beurten'},{value:'current',label:'Ook huidige aanvraag'}]}}},
        {name:'confirm',required:true,default:false,selector:{boolean:{}}}
      ]};
      const menu=(id,opts)=>({type:'menu',flow_id:'fixture-flow',step_id:id,menu_options:opts});
      const form=(step,schema)=>({type:'form',flow_id:'fixture-flow',step_id:step,errors:{},data_schema:schema});
      window.apiHandler=async(method,path,data)=>{
        apiCalls.push({method,path,data});if(method==='delete')return{};
        if(path==='config/config_entries/options/flow')return menu('init',['loads_hub','comfort_hub']);
        if(data.next_step_id==='loads_hub')return menu('loads_hub',['add','manage_device','replace','pending_changes']);
        if(data.next_step_id==='manage_device')return form('manage_device',[]);
        if(data.next_step_id==='replace')return form('replace',[]);
        if(data.next_step_id==='pending_changes')return form('pending_changes',[{name:'cancel',selector:{select:{multiple:true,options:[{value:'device:dryer',label:'Ontvochtiger — wijziging wacht'}]}}}]);
        if(data.device_id&&data.section)return form('device',[{name:'name',required:true,default:'Afwasmachine keuken',selector:{text:{}}},{name:'appliance_type',required:true,default:'dishwasher',selector:{select:{options:['dishwasher','washing_machine','tumble_dryer','other']}}}]);
        if(data.device_id)return form('confirm_replace',[{name:'confirm',required:true,default:false,selector:{boolean:{}}}]);
        if(data.name)return structuredClone(choiceForm);
        if(window.rejectSave)throw Error('Fixture: opslagverbinding onderbroken');
        return{type:'create_entry',data:{}};
      };
      c.hass={...c._hass,user:{is_admin:true},callApi:(...args)=>window.apiHandler(...args),callService:async(...args)=>actuatorCalls.push(args),callWS:async m=>{historyReads.push(m);throw Error('Historiefixture alleen routecontrole');},states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};
    }''')
    page.locator('solar-pilot-card >> button[data-action=view][data-value=loads]').click()
    page.locator('solar-pilot-card >> button[data-action=manage_devices]').first.click()
    manager=page.locator('solar-pilot-device-manager-dialog');dialog=manager.locator('dialog')
    assert dialog.is_visible() and 'Wacht op veilige vrijgave' in dialog.inner_text()
    assert manager.locator('[data-go=manage_device]').count()==6
    assert manager.locator('[data-history=old_dw]').count()==1
    assert page.evaluate('apiCalls.length===0 && actuatorCalls.length===0')
    page.evaluate('''()=>{window.managerNode=c._deviceManager.dialog;managerNode.scrollTop=140;window.oldScroll=managerNode.scrollTop;
      for(let n=0;n<80;n++){const a=structuredClone(c._last.attributes);a.grid_w=-n;c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};}}
    ''')
    assert page.evaluate('managerNode===c._deviceManager.dialog && managerNode.open && managerNode.scrollTop===oldScroll')
    page.screenshot(path=str(OUT/'SolarPilot-beta34-toestelbeheer-desktop.png'),full_page=True)
    manager.locator('[data-go=manage_device][data-id=dw][data-section=settings]').click()
    options=page.locator('solar-pilot-options-dialog')
    page.wait_for_selector('solar-pilot-options-dialog >> input[name=name]')
    assert page.evaluate("apiCalls.slice(0,4).map(x=>x.data.next_step_id||x.data.device_id||'init').join(',')==='init,loads_hub,manage_device,dw'")
    assert 'opnieuw laden' not in options.locator('dialog').inner_text()
    options.locator('[name=name]').fill('Afwasmachine nieuw label')
    options.locator('button[type=submit]').click()
    page.wait_for_selector('solar-pilot-options-dialog >> select[name=request_scope]')
    assert options.locator('[name=request_scope]').input_value()=='future'
    options.locator('[name=request_scope]').select_option('current')
    options.locator('[name=confirm]').check()
    options.locator('button[data-help=request_scope]').click()
    helpbox=options.locator('solar-pilot-option-help-dialog')
    assert 'geplande kalenderdag' in helpbox.locator('dialog').inner_text()
    page.evaluate('''()=>{window.savedOptions=c._optionsDialog.dialog;window.savedHelp=c._optionsDialog.helpDialog.dialog;
      for(let n=0;n<80;n++){const a=structuredClone(c._last.attributes);a.grid_w=-1000-n;c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};}}
    ''')
    assert page.evaluate('savedOptions.open && savedHelp.open && savedOptions===c._optionsDialog.dialog')
    assert options.locator('[name=request_scope]').input_value()=='current' and options.locator('[name=confirm]').is_checked()
    helpbox.locator('.close').click()
    page.screenshot(path=str(OUT/'SolarPilot-beta34-wijzigingen.png'),full_page=True)
    page.evaluate('window.rejectSave=true');options.locator('button[type=submit]').click()
    page.wait_for_function("c._optionsDialog.error.textContent.includes('niet bevestigd')")
    assert options.locator('[name=request_scope]').input_value()=='current'
    page.evaluate('window.rejectSave=false');options.locator('button[type=submit]').click()
    page.wait_for_function("c._optionsDialog.content.textContent.includes('opgeslagen zonder volledige herlading')")
    assert page.evaluate('apiCalls.at(-1).data.confirm===true && apiCalls.at(-1).data.request_scope==="current" && actuatorCalls.length===0')
    options.locator('[data-close]').click()
    # Live management update uses the new snapshot, not the previous tick.
    page.locator('solar-pilot-card >> button[data-action=manage_devices]').first.click()
    page.evaluate('''()=>{const a=structuredClone(c._last.attributes);a.device_management.devices[0].name='Nieuw label <img src=x onerror="window.bad=true">';c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};}''')
    assert 'Nieuw label <img' in dialog.inner_text() and manager.locator('img').count()==0
    # Pending list uses native flow, not a direct config mutation.
    manager.locator('[data-go=pending_changes]').click();page.wait_for_selector('solar-pilot-options-dialog >> select[name=cancel]')
    options.locator('[name=cancel]').select_option('device:dryer');options.locator('button[type=submit]').click()
    page.wait_for_function('c._optionsDialog.flow===null')
    assert page.evaluate("apiCalls.at(-1).data.cancel[0]==='device:dryer'")
    options.locator('[data-close]').click()
    # Mobile, category disclaimer and archive read-only.
    page.set_viewport_size({'width':390,'height':844})
    page.locator('solar-pilot-card >> button[data-action=manage_devices]').first.click()
    page.evaluate('c._deviceManager.dialog.scrollTop=0')
    assert dialog.evaluate('el=>el.scrollWidth<=el.clientWidth+2')
    page.screenshot(path=str(OUT/'SolarPilot-beta34-toestelbeheer-mobiel.png'),full_page=True)
    manager.locator('[data-history=old_dw]').click()
    page.wait_for_function("historyReads.length===1")
    assert page.evaluate("historyReads[0].device_id==='old_dw' && actuatorCalls.length===0")
    page.evaluate('c._historyDialog.close();c.hass={...c._hass,user:{is_admin:false}}')
    page.locator('solar-pilot-card >> button[data-action=manage_devices]').first.click()
    assert manager.locator('[data-go]').count()==0 and manager.locator('[data-history]').count()==3
    assert not errors,errors
    browser.close()
print('OK: actual live settings/device UI; routes, consent/scope, deferred edits, archive reads, 80 updates, mobile, XSS, no actuator calls.')
