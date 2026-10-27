"""Browser-check the compact SG card with fictitious measurements only.

Run build_example.py first. This check proves browser behavior, never live
Home Assistant access, Shelly timer acceptance or physical Panasonic response.
"""
import os
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('SOLARPILOT_SCREENSHOT_DIR', '/tmp/solarpilot-browser-tests'))
OUT.mkdir(parents=True, exist_ok=True)
errors = []
with sync_playwright() as p:
    executable = os.environ.get('SOLARPILOT_CHROMIUM_PATH') or shutil.which('chromium')
    browser = p.chromium.launch(**({'executable_path': executable} if executable else {}),
                                headless=True, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width': 390, 'height': 844}, locale='nl-BE')
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.set_content((ROOT / 'SolarPilot-voorbeeld.html').read_text(encoding='utf-8'), wait_until='load')
    page.wait_for_selector('solar-pilot-card >> h1')
    page.locator('solar-pilot-card >> button[role=tab][data-action=view][data-value=comfort]').click()
    panel = page.locator('solar-pilot-card >> .heatpump-sg')
    page.screenshot(path=str(OUT / 'SolarPilot-SG-compact-390.png'), full_page=True)
    panel.locator('details[data-ui-key="sg:comfort:details"] > summary').click()
    panel.locator('details[data-ui-key="sg:comfort:monitor"] > summary').click()
    assert panel.locator('[role=switch]').count() == 1
    assert panel.locator('input, select').count() == 0
    assert '50 °C' in panel.inner_text() and 'Verwarmen' in panel.inner_text()
    assert 'SG-contact actief.' in panel.inner_text()
    assert 'Panasonic-reactie niet afzonderlijk bevestigd' not in panel.inner_text()
    assert 'voeding 1 1,72 kW · voeding 2 0 W' in panel.inner_text()
    assert 'Totaal voeding 1 + voeding 2' in panel.inner_text()
    assert 'compressor draait · 33 Hz' in panel.inner_text()
    assert panel.locator('[data-sg-stage=received]').count()==0
    assert 'Ontvangen SG-status' not in panel.inner_text()
    assert 'Compressorbedrijf bewijst geen extra verbruik door SG' in panel.inner_text()
    assert 'SG-effect op verbruik' not in panel.inner_text()
    assert 'Algemene SG-boost' in panel.inner_text()
    assert 'Extra-koelbeveiliging\nNiet bevestigd' in panel.inner_text()
    page.evaluate('''() => {window.c=document.querySelector('solar-pilot-card');window.calls=[];
      c._hass.callService=async(...args)=>calls.push(args);
      window.before=[...c.shadowRoot.querySelectorAll('details')].map(d=>[d.dataset.uiKey,d.open]);
      for(let n=0;n<80;n++){const a=structuredClone(c._last.attributes);a.panasonic.temperature_c=46+n/100;
        c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};}}''')
    assert page.evaluate('JSON.stringify(before)===JSON.stringify([...c.shadowRoot.querySelectorAll("details")].map(d=>[d.dataset.uiKey,d.open]))')
    assert page.evaluate('calls.length') == 0
    q = panel.locator('[data-help-key=enabled]')
    q.click()
    host = page.locator('solar-pilot-option-help-dialog')
    assert host.locator('dialog').is_visible()
    assert 'SG' in host.locator('dialog').inner_text()
    # Opening help is also stable while backend reports keep arriving.
    page.evaluate('''() => {for(let n=0;n<80;n++){const a=structuredClone(c._last.attributes);
      a.panasonic.temperature_c=47+n/100;
      c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};}}''')
    assert host.locator('dialog').is_visible()
    assert page.evaluate('JSON.stringify(before)===JSON.stringify([...c.shadowRoot.querySelectorAll("details")].map(d=>[d.dataset.uiKey,d.open]))')
    for width in (320, 390, 768, 1280):
        page.set_viewport_size({'width': width, 'height': 1000})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), width
        assert panel.evaluate('e=>e.scrollWidth<=e.clientWidth+1'), width
        assert host.locator('dialog').evaluate('e=>e.scrollWidth<=e.clientWidth+1'), width
        page.screenshot(path=str(OUT / f'SolarPilot-SG-help-{width}.png'))
    page.keyboard.press('Escape')
    page.screenshot(path=str(OUT / 'SolarPilot-SG-details-1280.png'), full_page=True)
    # Receiving SG can be confirmed independently; caused extra consumption is
    # still not established by either compressor activity or received SG.
    page.evaluate('''() => {const a=structuredClone(c._last.attributes);
      a.panasonic.sg_status='active';a.panasonic.sg_status_confirmed=true;
      a.panasonic.sg_status_observed_at=Date.now()/1000;
      c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};}''')
    assert 'Ontvangen SG-status\nActief · afzonderlijk bevestigd' in panel.inner_text()
    assert 'Compressorbedrijf bewijst geen extra verbruik door SG' in panel.inner_text()
    assert 'SG-effect op verbruik' not in panel.inner_text()
    # A manually ON contact is not a SolarPilot lease, and a missing second
    # meter does not turn a partial value into a total.
    page.evaluate('''() => {const a=structuredClone(c._last.attributes);
      a.panasonic.power_supply2_w=null;a.panasonic.power_supply2_valid=false;
      a.panasonic.power_complete=false;a.panasonic.power_w=null;a.panasonic.power_kind='unknown';
      a.sg_boost.owner='manual';a.sg_boost.manual_hold=true;a.sg_boost.lease_confirmed=false;
      c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};}''')
    assert 'voeding 1 1,72 kW · voeding 2 onbekend' in panel.inner_text()
    assert 'Totaal onbekend · deelmeting onvolledig' in panel.inner_text()
    assert 'Bevestigde lokale toestemming\nNiet bevestigd' in panel.inner_text()
    # An unknown native measurement stays unknown; an ON policy is no relay proof.
    page.evaluate('''() => {const a=structuredClone(c._last.attributes);a.panasonic.power_w=null;
      a.panasonic.power_kind='unknown';a.sg_boost.relay_on=null;a.sg_boost.relay_confirmed=false;
      a.sg_boost.desired_on=true;a.sg_boost.panasonic_confirmed=null;
      a.panasonic.sg_status='unknown';a.panasonic.sg_status_confirmed=false;
      a.panasonic.compressor_running=null;a.panasonic.compressor_frequency_hz=null;
      a.sg_boost.reason='Wacht op betrouwbare contactstatus';
      c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};}''')
    assert 'Vermogen nog niet bekend' in panel.inner_text()
    assert 'Nog niet bevestigd' in panel.inner_text() and 'Afzonderlijk bevestigd' not in panel.inner_text()
    assert 'compressor draait' not in panel.inner_text()
    assert 'Compressorfrequentie' not in panel.inner_text()
    assert panel.locator('[data-sg-stage=received]').count()==0
    assert page.evaluate('calls.length') == 0
    # beta.84 temporary requests: select a mode and duration, never write the
    # physical switch or claim the selected request as a confirmed contact.
    page.evaluate("""() => {
      window.manualCalls=[];c._hass.callService=async(domain,service,data)=>manualCalls.push({domain,service,data});
      const a=structuredClone(c._last.attributes),now=Date.now()/1000;
      a.mode='solar';a.sg_boost.enabled=true;a.sg_boost.configured=true;
      a.sg_boost.observed_at=now;a.sg_boost.relay_observed_at=now;
      a.sg_boost.relay_on=false;a.sg_boost.relay_confirmed=true;a.sg_boost.desired_on=false;
      a.sg_boost.manual_hold=false;a.sg_boost.owner='none';a.sg_boost.lease_confirmed=false;
      a.sg_boost.manual_control={mode:'auto',active:false,duration_s:null,expires_at:null,remaining_s:null,reason:''};
      c.hass={...c._hass,user:{id:'fictitious-admin',is_admin:true},states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};
    }""")
    controls=panel.locator('[data-sg-manual-control]')
    choices=[('on',1800),('on',3600),('off',1800),('off',3600),('auto',None)]
    for width in (320,390,768,1280):
        page.set_viewport_size({'width':width,'height':1000})
        page.evaluate('manualCalls.length=0')
        for mode,duration in choices:
            selector=f'button[data-action=sg_manual_control][data-sg-mode={mode}]'
            if duration is not None:
                selector+=f'[data-sg-duration="{duration}"]'
            controls.locator(selector).click()
            page.wait_for_function('!c._busy')
            assert controls.get_attribute('data-sg-manual-control')=='auto'
            assert panel.locator('[data-sg-stage=relay]').inner_text()=='SG-contact\nOpen'
        received=page.evaluate('manualCalls')
        expected=[]
        for mode,duration in choices:
            data={'config_entry_id':page.evaluate('c._last.attributes.config_entry_id'),'mode':mode}
            if duration is not None:
                data['duration_s']=duration
            expected.append({'domain':'solar_pilot','service':'sg_manual_control','data':data})
        assert received==expected,received
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
        assert controls.evaluate('e=>e.scrollWidth<=e.clientWidth+1'),width
        page.screenshot(path=str(OUT/f'SolarPilot-SG-temporary-{width}.png'),full_page=True)
    page.evaluate("""() => {const a=structuredClone(c._last.attributes),now=Date.now()/1000;
      a.sg_boost.observed_at=now;a.sg_boost.manual_control={mode:'on',active:true,duration_s:1800,
        expires_at:now+90,remaining_s:90,reason:'Veilige fasegrens bereikt'};
      c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};} """)
    assert 'Handmatig AAN · aanvraag' in controls.inner_text()
    assert 'daarna automatisch' in controls.inner_text() and 'Aanvraag wacht:' in controls.inner_text()
    assert 'Veilige fasegrens bereikt' in controls.inner_text()
    # Countdown refresh preserves an already-open help modal and never sends a
    # service to expire a mode. Only a fresh backend snapshot can confirm Auto.
    panel.locator('[data-help-key=enabled]').click()
    assert host.locator('dialog').is_visible()
    page.evaluate("""() => {window.manualBefore=manualCalls.length;const a=structuredClone(c._last.attributes),now=Date.now()/1000;
      a.sg_boost.observed_at=now;a.sg_boost.manual_control.expires_at=now-1;
      a.sg_boost.manual_control.remaining_s=0;
      c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};
      c._refreshObservationDisplay();} """)
    assert host.locator('dialog').is_visible()
    assert 'Tijd verstreken · wacht op automatische beoordeling' in controls.inner_text()
    assert page.evaluate('manualCalls.length===manualBefore')
    page.keyboard.press('Escape')
    page.evaluate("""() => {const a=structuredClone(c._last.attributes);a.sg_boost.observed_at=Date.now()/1000;
      a.sg_boost.manual_control={mode:'auto',active:false,duration_s:null,expires_at:null,remaining_s:null,reason:''};
      c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};} """)
    assert controls.get_attribute('data-sg-manual-control')=='auto'
    assert 'Tijd verstreken' not in controls.inner_text()
    page.evaluate("""() => {const a=structuredClone(c._last.attributes),now=Date.now()/1000;
      a.sg_boost.observed_at=now;a.sg_boost.state='waiting_surplus';a.sg_boost.completion_hold=false;
      Object.assign(a.sg_boost,{start_required_s:120,start_remaining_s:0,start_valid_until:now-1,
        start_cloud_active:true,start_cloud_kind:'measurement_gap',start_cloud_remaining_s:180,
        start_cloud_valid_until:now+180});
      c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};} """)
    wait=panel.locator('[data-sg-wait=start_gap]')
    assert 'Korte meetonderbreking' in wait.inner_text()
    assert 'Wachttijd verstreken · wacht op actuele meting' in wait.inner_text()
    assert 'maximaal 5 min overbrugging' in wait.inner_text()
    assert panel.locator('[data-sg-stage=relay]').inner_text()=='SG-contact\nOpen'
    assert page.evaluate('manualCalls.length===manualBefore')
    page.locator('solar-pilot-card >> button[role=tab][data-action=view][data-value=overview]').click()
    overview=page.locator('solar-pilot-card >> [data-reason-key="overview:sg"] [data-sg-manual-control]')
    assert overview.locator('button[data-action=sg_manual_control]').count()==5
    assert overview.evaluate('e=>e.scrollWidth<=e.clientWidth+1')
    # A rejected HP report remains unknown. SG may separately re-confirm
    # actual P1/PV residual using the full configured SG total-power estimate.
    page.evaluate("""() => {const a=structuredClone(c._last.attributes),now=Date.now()/1000;
      const p=a.panasonic,s=a.sg_boost;
      Object.assign(p,{power_scope:'split',power_w:null,power_kind:'unknown',power_complete:false,
        power_supply1_w:null,power_supply1_valid:false,power_supply1_observed_at:null,
        power_supply2_w:0,power_supply2_valid:true,power_supply2_observed_at:now});
      p.power_activity={state:'unknown',active:false,complete:false,total_w:null,observed_at:null,stale_s:120,
        supplies:[{number:1,role:'main',valid:false,watts:null,observed_at:null,state:'unknown'},
          {number:2,role:'heater',valid:true,watts:0,observed_at:now,state:'off'}]};
      p.power_source_quality={supply1:{valid:false,watts:null,rejection_reason:'negative',
        source_reported_wall:now,source_value:'-12',source_watts:-12,source_unit:'W',measured_wall:null}};
      Object.assign(s,{observed_at:now,profile:'general',state:'completion_hold',completion_hold:true,
        start_cloud_active:false,reassessment_kind:'fresh_residual_surplus',
        reassessment_state:'confirming_fresh_residual_surplus',reassessment_remaining_s:240,
        reassessment_required_s:300,reassessment_reports:3,reassessment_source_current:true,
        reassessment_final_report_required:false,reassessment_valid_until:now+120,
        residual_reassessment_available:true,residual_reassessment_threshold_w:3200,
        real_residual_surplus_w:5600,estimated_power_w:3200});
      a.ems.electrical_limits={source_valid:true,source_observed_at:now,source_stale_s:120,
        sg_solar_valid:true,sg_solar_observed_at:now,sg_residual_solar_w:5600,
        sg_eligible_solar_w:5600,sg_hp_solar_w:0};
      c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};} """)
    overview_row=page.locator('solar-pilot-card >> [data-reason-key="overview:sg"]')
    for width in (320,390,768,1280):
        page.set_viewport_size({'width':width,'height':1000})
        first=overview_row.locator('[data-supply-number="1"]')
        assert 'Ongeldige meetwaarde' in first.inner_text()
        assert '0 W' not in first.inner_text() and '12 W' not in first.inner_text()
        assert first.get_attribute('data-supply-quality')=='invalid'
        assert '0 W' in overview_row.locator('[data-supply-number="2"]').inner_text()
        assert 'actuele P1/PV-metingen' in overview_row.locator('[data-sg-optional-meter]').inner_text()
        optional_note=overview_row.locator('[data-sg-optional-meter]').inner_text()
        assert '3,2 kW geraamd totaalvermogen bij SG' in optional_note
        assert 'Warmtepompbijdrage blijft onbekend' in optional_note
        assert 'zonder volledige actuele warmtepompmeting telt de hele raming als mogelijke toename' in optional_note
        assert 'geraamde extra opname' not in optional_note
        residual=overview_row.locator('[data-sg-wait=reassessment]')
        assert 'restoverschot herbevestigen' in residual.inner_text()
        assert 'van 5 min' in residual.inner_text() and 'Restoverschot 5,6 kW · nodig 3,2 kW' in residual.inner_text()
        assert overview_row.locator('[data-sg-stage=relay]').inner_text()=='SG-contact\nOpen'
        assert overview_row.evaluate('e=>e.scrollWidth<=e.clientWidth+1'),width
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
        page.screenshot(path=str(OUT/f'SolarPilot-SG-residual-{width}.png'),full_page=True)
    overview_row.locator('[data-help-key=sg_manual_control]').click()
    assert host.locator('dialog').is_visible()
    page.evaluate("""() => {const a=structuredClone(c._last.attributes),now=Date.now()/1000;
      a.panasonic.power_source_quality.supply1.source_reported_wall=now-121;
      a.sg_boost.observed_at=now;a.sg_boost.reassessment_valid_until=now-1;
      c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};
      c._refreshObservationDisplay();} """)
    assert host.locator('dialog').is_visible()
    assert 'Geen actuele meting' in overview_row.locator('[data-supply-number="1"]').inner_text()
    assert 'Ongeldige meetwaarde' not in overview_row.locator('[data-supply-number="1"]').inner_text()
    assert 'Herbevestiging onbekend' in overview_row.locator('[data-sg-wait=reassessment]').inner_text()
    assert 'Restoverschot 5,6 kW' not in overview_row.locator('[data-sg-wait=reassessment]').inner_text()
    assert page.evaluate('manualCalls.length===manualBefore')
    page.keyboard.press('Escape')
    # beta.87 backend-approved zero keeps the negative raw report in Details.
    page.evaluate("""() => {const a=structuredClone(c._last.attributes),now=Date.now()/1000,p=a.panasonic;
      window.normalizationOriginalStamp=now;
      Object.assign(p,{power_w:0,power_kind:'measured',power_complete:true,power_observed_at:now,
        power_supply1_w:0,power_supply1_valid:true,power_supply1_observed_at:now,
        power_supply2_w:0,power_supply2_valid:true,power_supply2_observed_at:now});
      Object.assign(p.power_activity,{state:'off',active:false,complete:true,total_w:0,observed_at:now});
      for(const row of p.power_activity.supplies)Object.assign(row,{valid:true,watts:0,observed_at:now,state:'off'});
      p.power_source_quality.supply1={valid:true,watts:0,source_watts:-12,source_value:'-12',source_unit:'W',
        source_reported_wall:now,source_timestamp_kind:'last_reported',measured_wall:now,
        normalized:true,normalization_reason:'negative_as_zero',rejection_reason:null,reason:''};
      a.sg_boost.observed_at=now;
      c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};} """)
    why=overview_row.locator('details[data-ui-key="overview:sg:why"]')
    if not why.evaluate('e=>e.open'):
        why.locator(':scope > summary').click()
    for width in (320,390,768,1280):
        page.set_viewport_size({'width':width,'height':1000})
        first=overview_row.locator('[data-supply-number="1"]')
        assert '0 W' in first.inner_text() and 'Geen verbruik' in first.inner_text()
        assert 'Ongeldige meetwaarde' not in first.inner_text() and 'Geen actuele meting' not in first.inner_text()
        assert '12 W' not in first.inner_text()
        proof=overview_row.locator('[data-heatpump-provenance]')
        assert 'Bron -12 W → toegepast 0 W' in proof.inner_text()
        assert 'bron niet actueel' not in proof.inner_text()
        assert 'laatste bronrapport' in proof.inner_text()
        assert overview_row.locator('[data-sg-stage=relay]').inner_text()=='SG-contact\nOpen'
        assert overview_row.evaluate('e=>e.scrollWidth<=e.clientWidth+1'),width
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
        page.screenshot(path=str(OUT/f'SolarPilot-HP-normalized-zero-{width}.png'),full_page=True)
    overview_row.locator('[data-help-key=sg_manual_control]').click()
    assert host.locator('dialog').is_visible()
    page.evaluate("""() => {for(let i=0;i<80;i++){const a=structuredClone(c._last.attributes);
      a.sg_boost.observed_at=Date.now()/1000;
      c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};}} """)
    assert host.locator('dialog').is_visible() and why.evaluate('e=>e.open')
    assert page.evaluate('c._last.attributes.panasonic.power_source_quality.supply1.source_reported_wall===normalizationOriginalStamp')
    page.evaluate("""() => {const a=structuredClone(c._last.attributes),old=Date.now()/1000-121,p=a.panasonic;
      p.power_observed_at=old;p.power_supply1_observed_at=old;p.power_supply2_observed_at=old;
      p.power_activity.observed_at=old;for(const row of p.power_activity.supplies)row.observed_at=old;
      p.power_source_quality.supply1.source_reported_wall=old;p.power_source_quality.supply1.measured_wall=old;
      c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};
      c._refreshObservationDisplay();} """)
    first=overview_row.locator('[data-supply-number="1"]')
    assert 'Geen actuele meting' in first.inner_text() and '0 W' not in first.inner_text()
    assert 'Bron -12 W → toegepast 0 W · bron niet actueel' in overview_row.locator('[data-heatpump-provenance]').inner_text()
    assert host.locator('dialog').is_visible()
    page.evaluate("""() => {const a=structuredClone(c._last.attributes),p=a.panasonic;
      p.power_w=null;p.power_kind='unknown';p.power_complete=false;p.power_supply1_w=null;p.power_supply1_valid=false;
      p.power_activity.complete=false;p.power_activity.total_w=null;p.power_activity.state='unknown';
      Object.assign(p.power_activity.supplies[0],{valid:false,watts:null,observed_at:null,state:'unknown'});
      Object.assign(p.power_source_quality.supply1,{valid:false,watts:null,source_watts:null,source_value:null,
        source_reported_wall:null,measured_wall:null,normalized:false,normalization_reason:null,rejection_reason:'missing'});
      c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};} """)
    assert 'Geen actuele meting' in first.inner_text() and '0 W' not in first.inner_text()
    assert '→ toegepast 0 W' not in overview_row.locator('[data-heatpump-provenance]').inner_text()
    assert host.locator('dialog').is_visible() and page.evaluate('manualCalls.length===manualBefore')
    page.keyboard.press('Escape')
    assert not errors, errors
    browser.close()
print('OK: SG details and help each survive 80 updates; independent compressor/received SG/uptake and split meter evidence; honest unknowns/manual lease; 320/390/768/1280 browser layout; zero device calls from observations; temporary SG service-only ON/OFF 30/60 and Auto payloads at every width, separate contact proof, expiry waits for backend and keeps modal; completed startclock through brief measurement gap never claims contact ON; actual residual rearm, rejected fresh HP reading versus stale source, configured total estimate without a complete HP measurement and modal retention at four widths; normalized HP zero preserves raw negative Details and original report time, stale/missing values stay unknown, modal survives80updates. Fictitious data only.')
