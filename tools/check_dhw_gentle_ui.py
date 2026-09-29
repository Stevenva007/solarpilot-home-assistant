"""Check the real beta.30 DHW UI with fictitious measurements only."""
import os
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('SOLARPILOT_SCREENSHOT_DIR','/tmp/solarpilot-browser-tests'))
OUT.mkdir(parents=True,exist_ok=True)
errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=shutil.which('chromium'),headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1100},locale='nl-BE')
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.set_content((ROOT/'SolarPilot-voorbeeld.html').read_text(encoding='utf-8'),wait_until='load')
    page.wait_for_selector('solar-pilot-card >> h1')
    page.locator('solar-pilot-card >> button[data-action=view][data-value=comfort]').click()
    page.locator('solar-pilot-card >> .dhw-rules summary').click()
    assert page.locator('solar-pilot-card >> [data-dhw-setting=normal_c]').input_value()=='50'
    assert page.locator('solar-pilot-card >> [data-dhw-setting=minimum_c]').input_value()=='46'
    assert page.locator('solar-pilot-card >> [data-dhw-setting=minimum_buffer_c]').count()==0
    text=page.locator('solar-pilot-card >> .dhw').inner_text()
    for needle in ('Herstart Panasonic','45 °C','46 °C om 09:00','geen gegarandeerd minimum','Panasonic bepaalt','30 min'):
        assert needle in text,needle
    page.evaluate('''() => { window.c=document.querySelector('solar-pilot-card');window.writes=[];
      c.hass={...c._hass,callService:async(...args)=>writes.push(args)};
      const a=structuredClone(c._last.attributes);a.dhw.comfort_plan.warning='Fictieve meting: 45,5 °C onder comfortgrens; normaal doel blijft 50 °C';
      a.dhw.comfort_plan.below_floor=true;a.dhw.comfort_plan.projected_c=43.3;a.dhw.temperature_c=45.5;
      c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};
    }''')
    assert 'Fictieve meting' in page.locator('solar-pilot-card >> .comfort-new').inner_text()
    # Help for independent normal target; no device call on opening/help hover.
    q=page.locator('solar-pilot-card >> .dhw-rules [data-help-key=normal_c]')
    q.hover();page.wait_for_timeout(100);q.click()
    help_host=page.locator('solar-pilot-option-help-dialog')
    assert help_host.locator('dialog').first.is_visible()
    help_text=help_host.locator('dialog').first.inner_text()
    assert __import__('json').loads((ROOT/'custom_components/solar_pilot/manifest.json').read_text())['version'] in help_text and '50 °C' in help_text and 'legionella' in help_text
    page.evaluate('''() => { window.dialogBefore=c._helpDialog.dialog;
      for(let n=0;n<80;n++){const a=structuredClone(c._last.attributes);a.grid_w=-1500-n;
      c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};}
    }''')
    assert page.evaluate('dialogBefore.open && c._helpDialog.dialog===dialogBefore')
    page.keyboard.press('Escape')
    assert page.locator('solar-pilot-card >> .dhw-rules').get_attribute('open') is not None
    for width in (320,390,768,1440):
        page.set_viewport_size({'width':width,'height':1100})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
        assert page.locator('solar-pilot-card >> .dhw').evaluate('e=>e.scrollWidth<=e.clientWidth+1'),width
    page.set_viewport_size({'width':1440,'height':1100})
    page.locator('solar-pilot-card >> .dhw').screenshot(path=str(OUT/'SolarPilot-beta28-warmwater-desktop.png'))
    page.set_viewport_size({'width':390,'height':844})
    page.locator('solar-pilot-card >> .dhw').screenshot(path=str(OUT/'SolarPilot-beta28-warmwater-mobiel.png'))
    assert page.evaluate('writes.length')==0
    assert not errors,errors
    browser.close()
print('OK: beta.30 normal 50 / monitored 46 / native 45, no buffer field, warnings, 80 updates, help, 320/390/768/1440 layout, zero device calls. Fictitious data only.')
