"""Real browser interactions against local fixtures; no HA or physical commands."""
from pathlib import Path
import os, shutil
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('SOLARPILOT_SCREENSHOT_DIR','/tmp/solarpilot-ui35'));OUT.mkdir(parents=True,exist_ok=True)
errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=shutil.which('chromium'),headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1360,'height':1060},locale='nl-BE')
    page.set_default_timeout(10000)
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.set_content((ROOT/'SolarPilot-voorbeeld.html').read_text(),wait_until='load')
    page.wait_for_selector('solar-pilot-card >> h1')
    page.evaluate('''()=>{
      document.body.style.maxWidth='1100px';const c=document.querySelector('solar-pilot-card');window.c=c;
      window.calls=[];window.commands=[];window.server=structuredClone(c._last.attributes.priority_board);
      window.server.note='Voorbeeldopstelling · de bestaande instellingen blijven behouden totdat je bevestigt.';
      c.hass={...c._hass,user:{is_admin:true},callService:async(...args)=>commands.push(args),callWS:async msg=>{
        calls.push(structuredClone(msg));
        if(msg.type==='solar_pilot/priority_board'){
          if(msg.save){if(window.failSave)throw Error('De instellingen zijn intussen gewijzigd');
            server={...server,active:true,revision:'next-'+calls.length,order:msg.save.order,wallbox_power:msg.save.wallbox_power,message:'Voorrang opgeslagen.'};
            server.rows=server.order.map((id,i)=>({...server.rows.find(r=>r.id===id),position:i+1,wallbox_power:server.wallbox_power[id]}));}
          return structuredClone(server);
        }
        if(msg.type==='solar_pilot/analysis_export')return{filename:'solarpilot-voorbeeld.json',content:'{"fixture":true}'};
        throw Error('Onverwachte endpoint '+msg.type);
      }};
    }''')
    page.locator('solar-pilot-card >> .nav [data-value=priorities]').click()
    assert page.locator('solar-pilot-card >> .nav button').count()==9
    assert page.locator('solar-pilot-card >> .priority-row').count()==page.evaluate('server.rows.length+server.protected.length')
    assert page.locator('solar-pilot-card >> .priority-row.fixed').count()==page.evaluate('server.protected.length')
    overview_text=page.locator('solar-pilot-card >> ha-card').inner_text()
    assert 'Voorrang en autoladen' in overview_text
    assert overview_text.count('Mag de auto minder laden?')==page.evaluate('server.rows.length+server.protected.length')
    below_overview=page.locator('solar-pilot-card >> .priority-row').filter(has_text='Flexlast · voorbeeld')
    assert 'Mag de auto minder laden? Nee · Auto laden staat hoger' in below_overview.inner_text()
    assert 'Toestemming is bewaard; wordt gebruikt als je dit toestel boven Auto laden zet.' in below_overview.inner_text()
    assert 'legacy' not in overview_text.lower() and 'oude expliciete' not in overview_text.lower()
    assert page.evaluate('commands.length===0&&calls.length===0')
    page.screenshot(path=str(OUT/'SolarPilot-beta35-voorrang-desktop.png'),full_page=True)
    page.locator('solar-pilot-card >> [data-action=priority_edit]').click()
    editor=page.locator('solar-pilot-priority-dialog');dialog=editor.locator('dialog')
    page.wait_for_selector('solar-pilot-priority-dialog >> [data-row]')
    assert editor.locator('.row.locked').count()==page.evaluate('server.protected.length')
    assert editor.locator('.row').count()==page.evaluate('server.rows.length+server.protected.length')
    assert editor.locator('.permission').count()==page.evaluate('server.rows.length+server.protected.length')
    permission_labels = dialog.inner_text().count('Mag de auto minder laden?')
    expected_labels = page.evaluate('server.rows.length+server.protected.length')
    assert permission_labels == expected_labels, (permission_labels, expected_labels)
    below_editor=editor.locator('[data-row="device:flex_load"]')
    assert 'Nee · Auto laden staat hoger.' in below_editor.inner_text()
    assert 'Toestemming is bewaard; wordt gebruikt als je dit toestel boven Auto laden zet.' in below_editor.inner_text()
    assert below_editor.locator('[data-power]').input_value()=='yes'
    assert 'legacy' not in dialog.inner_text().lower() and 'oude expliciete' not in dialog.inner_text().lower()
    assert editor.locator('[data-save]').is_disabled()
    # Explicit movement and permission edit: no save, no device command.
    editor.locator('[data-move="device:flex_load"][data-delta="-1"]').click()
    editor.locator('[data-power="device:flex_load"]').select_option('no')
    assert page.evaluate('calls.length===1&&commands.length===0')
    assert editor.locator('[data-save]').is_disabled()
    editor.locator('[data-confirm]').check()
    assert editor.locator('[data-save]').is_enabled()
    page.evaluate('''()=>{window.dialogNode=c._priorityDialog.dialog;window.draft=JSON.stringify(c._priorityDialog._order);
      c._priorityDialog.dialog.scrollTop=180;window.scrollBefore=dialogNode.scrollTop;
      for(let i=0;i<100;i++){const a=structuredClone(c._last.attributes);a.grid_w=-500-i;c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};}
    }''')
    assert page.evaluate('dialogNode===c._priorityDialog.dialog&&dialogNode.open&&dialogNode.scrollTop===scrollBefore&&JSON.stringify(c._priorityDialog._order)===draft')
    assert editor.locator('[data-power="device:flex_load"]').input_value()=='no'
    assert editor.locator('[data-confirm]').is_checked()
    # Actual drag/drop events move a row without saving and reset consent.
    editor.locator('[data-row="device:extra"]').drag_to(editor.locator('[data-row="device:flex_load"]'))
    assert page.evaluate("c._priorityDialog._order.indexOf('device:extra')<c._priorityDialog._order.indexOf('device:flex_load')")
    assert not editor.locator('[data-confirm]').is_checked()
    assert page.evaluate('commands.length===0&&calls.length===1')
    page.evaluate('c._priorityDialog.dialog.scrollTop=0')
    page.screenshot(path=str(OUT/'SolarPilot-beta35-editor-desktop.png'),full_page=True)
    # Error retains every local edit; retry needs fresh confirmation.
    page.evaluate('window.failSave=true');editor.locator('[data-confirm]').check();editor.locator('[data-save]').click()
    page.wait_for_function("c._priorityDialog.status.textContent.includes('Opslag niet bevestigd')")
    assert editor.locator('[data-power="device:flex_load"]').input_value()=='no'
    assert not editor.locator('[data-confirm]').is_checked()
    page.evaluate('window.failSave=false');editor.locator('[data-confirm]').check();editor.locator('[data-save]').click()
    page.wait_for_function("c._priorityDialog.status.textContent==='Voorrang opgeslagen.'")
    assert page.evaluate('server.active && commands.length===0 && calls.at(-1).save.confirm===true')
    assert editor.locator('[data-save]').is_disabled()
    editor.locator('[data-close]').first.click()
    # Fresh returned names are text, not HTML; read-only users cannot edit.
    page.evaluate("server.rows[0].name='Toestel <img src=x onerror=window.injected=true>'")
    page.locator('solar-pilot-card >> [data-action=priority_edit]').click()
    page.wait_for_selector('solar-pilot-priority-dialog >> [data-row]')
    assert editor.locator('img').count()==0 and '<img' in dialog.inner_text()
    page.evaluate('c.hass={...c._hass,user:{is_admin:false}}')
    assert editor.locator('[data-move]').first.is_disabled()
    page.evaluate('c.hass={...c._hass,user:{is_admin:true}}')
    # Enforced buffer position and accessible arrows on narrow screens.
    page.evaluate("server.rows[0].name='Afwasmachine';c._priorityDialog._data.rows=structuredClone(server.rows);c._priorityDialog._renderDraft()")
    for width in (320,390,768,1360):
        page.set_viewport_size({'width':width,'height':900})
        assert dialog.evaluate('el=>el.scrollWidth<=el.clientWidth+2'),width
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
    page.set_viewport_size({'width':390,'height':844});page.evaluate('c._priorityDialog.dialog.scrollTop=0')
    page.screenshot(path=str(OUT/'SolarPilot-beta35-editor-mobiel.png'),full_page=True)
    # Constraint: buffer may move above ordinary loads, never above Wallbox.
    page.evaluate("c._priorityDialog._move('dhw_extra',0)")
    assert 'Wallbox' in editor.locator('.status').inner_text()
    assert page.evaluate("c._priorityDialog._order.indexOf('wallbox')<c._priorityDialog._order.indexOf('dhw_extra')")
    editor.locator('[data-close]').first.click()
    # A single Export hub opens the existing scoped export builder.
    page.locator('solar-pilot-card >> .nav [data-value=export]').click()
    assert 'geen herstelbare Home Assistant-back-up' in page.locator('solar-pilot-card >> ha-card').inner_text()
    page.screenshot(path=str(OUT/'SolarPilot-beta35-export-mobiel.png'),full_page=True)
    page.locator('solar-pilot-card >> [data-action=analysis_export]').click()
    export=page.locator('solar-pilot-analysis-dialog')
    assert export.locator('dialog').is_visible()
    assert not export.locator('.names').is_checked()
    with page.expect_download():export.locator('.download').click()
    assert page.evaluate("calls.at(-1).type==='solar_pilot/analysis_export'&&calls.at(-1).include_names===false&&commands.length===0")
    export.locator('.close').click()
    # A pending read is cancellable; closing never issues a save.
    page.locator('solar-pilot-card >> .nav [data-value=priorities]').click()
    page.evaluate("()=>{window.realWS=c._hass.callWS;c._hass.callWS=()=>new Promise(resolve=>window.resolveRead=resolve);}")
    page.locator('solar-pilot-card >> [data-action=priority_edit]').click()
    editor.locator('[data-close]').first.click()
    assert not dialog.is_visible()
    page.evaluate('()=>{window.resolveRead(structuredClone(server));c._hass.callWS=window.realWS;}')
    assert not dialog.is_visible()
    page.locator('solar-pilot-card >> [data-action=priority_edit]').click()
    page.wait_for_selector('solar-pilot-priority-dialog >> [data-power]')
    editor.locator('[data-power="device:flex_load"]').select_option('yes')
    page.evaluate('window.confirm=()=>false')
    editor.locator('[data-close]').first.click()
    assert dialog.is_visible()
    page.evaluate('window.confirm=()=>true')
    editor.locator('[data-close]').first.click()
    assert not dialog.is_visible()
    # Non-admin sees priority overview, but no editing button usable.
    # Supply a fresh HA state snapshot together with this fixture's changed
    # user; clicking the already-selected tab is no longer a forced rerender.
    page.evaluate('''()=>{c.hass={...c._hass,user:{is_admin:false},states:{...c._hass.states,[c._entity]:{...c._last}}};}''')
    page.locator('solar-pilot-card >> .nav [data-value=priorities]').click()
    assert page.locator('solar-pilot-card >> [data-action=priority_edit]').is_disabled()
    assert not errors,errors
    browser.close()
print('OK: priority editor, actual drag/drop, arrows, confirmation, preserved drafts, errors, admin boundary, mobile widths and Export; zero physical commands.')
