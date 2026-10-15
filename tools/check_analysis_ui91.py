"""Browser acceptance for analysis-driven beta.91 presentation changes.

Fictitious local evidence only. Every network request is blocked, all service
calls fail, and only explicit read-only learning/PV RPCs are accepted.
"""
import os
from pathlib import Path
import shutil

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("SOLARPILOT_SCREENSHOT_DIR", "/tmp/solarpilot-browser-tests"))


SETUP = """() => {
 window.c=document.querySelector('solar-pilot-card');window.analysisCalls=[];
 window.analysisDeviceCalls=[];window.analysisSettingsRoutes=[];
 const now=Date.now()/1000;
 window.learningData={ready:true,models:[],policy:{},quality:{},questions:[],audit:[],
  contract:'FICTIEVE GEGEVENS · uitsluitend browserproef.',
  sampling:{last:{valid:false,watts:null,code:'settling'},
   status:{state:'transient_wait',severity:'info',kind:'load_settling',
    reason:'Last na inschakeling of herstel aan het stabiliseren <img src=x onerror="window.analysisInjected=true">',
    started_at:now-20,ends_at:now+100,remaining_s:100,last_checked_at:now},
   exclusions_7d:{settling_attempts:3,heatpump_unknown_attempts:488,
    other_heatpump_context_attempts:11,note:'Kwartierpogingen, geen gemeten uren.'},
   attempts_7d:{settling:3,heatpump_heatpump_unknown:488}}};
 const band=(label,n)=>({label,samples:n,unique_targets:n,distinct_days:2,
  mae_w:600,bias_w:-120,conditions:[{condition:'daylight',samples:n-1,
   unique_targets:n-1,distinct_days:2,mae_w:900,bias_w:-300}]});
 window.pvData={summary:{status:'FICTIEVE GEGEVENS · PV-onderzoek',model:{}},history:[],
  forecast_evidence:{version:1,summary:{ahead_comparisons:173,unique_targets:100,
   distinct_days:2,by_recorded_lead:[band('3–12 uur',47)],
   lead_cohort_evidence:{version:1,unique_targets:60,distinct_days:2,pending_selections:8,
    selection_reason:'Eerste geldige bron <img src=x onerror="window.analysisInjected=true">',
    dependency_reason:'De reeksen delen dezelfde oorspronkelijke meetkwartieren.',
    by_recorded_lead:[band('0–1 uur',13),band('1–3 uur',20),band('3–12 uur',47)]}}}};
 const a=structuredClone(c._last.attributes);a.config_entry_id='fictional-analysis91';
 a.sg_boost={...a.sg_boost,configured:true,enabled:true,state:'waiting',
  reason:'Nieuwe sessie wacht op actuele zon',desired_on:false,relay_on:null,
  relay_confirmed:false,relay_observed_at:now,observed_at:now,
  rearm_wait:{original_stop_reason:'Oude stop: langdurige netafname <img>',
   current_condition:'Nieuwe sessie wacht op voldoende actuele zon'}};
 a.panasonic={...a.panasonic,source_stale_s:120,
  display_tank:{available:true,temperature_c:49,temperature_stamp:now,
   target_c:50,target_stamp:now-7},
  sg_tank_goal:{read_only:true,source:'local_confirmed_profile',normal_target_c:50,
   calculated_c:57.5,profile_percent:115,profile_confirmed_at:now-100,
   normal_target_reported_at:now-7,valid_until:now+113}};
 window.analysisAttributes=a;
 window.publishAnalysis=()=>{c.hass={...c._hass,user:{id:'fictional-admin',is_admin:true},
  callService:async(...args)=>{analysisDeviceCalls.push(args);throw Error('Unexpected actuator call');},
  callWS:async msg=>{analysisCalls.push(msg);
   if(msg.type==='solar_pilot/learning'&&msg.operation==='read')return structuredClone(learningData);
   if(msg.type==='solar_pilot/pv_diagnostics'&&!msg.reset_confirm)return structuredClone(pvData);
   throw Error('Unexpected non-read RPC');},
  states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:structuredClone(analysisAttributes)}}};};
 publishAnalysis();
} """


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    errors = []
    with sync_playwright() as p:
        executable = os.environ.get("SOLARPILOT_CHROMIUM_PATH") or shutil.which("chromium")
        browser = p.chromium.launch(**({"executable_path": executable} if executable else {}),
                                    headless=True, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 390, "height": 1000}, locale="nl-BE",
                                timezone_id="Europe/Brussels")
        page.route("**/*", lambda route: route.abort())
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.set_content((ROOT / "SolarPilot-voorbeeld.html").read_text(), wait_until="load")
        page.wait_for_selector("solar-pilot-card >> h1")
        page.evaluate(SETUP)
        card = page.locator("solar-pilot-card")

        # Opening the real quality popup accepts one read RPC, with an
        # informative wait instead of a bad-binding investigation.
        card.locator('.footer [data-action="learning_hub"]').click()
        quality_tag = page.evaluate("c._learningDialog.localName")
        quality = page.locator(quality_tag)
        waiting = quality.locator('[data-sampling-state="transient_wait"]')
        waiting.wait_for(state="visible")
        assert "100 s resterend" in waiting.inner_text()
        assert "Tijdelijke leerwacht vanaf" in waiting.inner_text()
        assert "Langer wachten verhelpt" not in waiting.inner_text()
        assert quality.locator("img").count() == 0
        quality.locator('details[data-key="coverage"] > summary').click()
        assert "stabilisatiewacht: 3" in quality.locator("[data-learning-exclusions]").inner_text()
        assert "warmtepompcontext: 488" in quality.locator("[data-learning-exclusions]").inner_text()
        for width in (320, 390, 768, 1280):
            page.set_viewport_size({"width": width, "height": 1000})
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"), width
            assert quality.locator("dialog").evaluate("e=>e.scrollWidth<=e.clientWidth+1"), width
            page.screenshot(path=str(OUT / f"SolarPilot-leerwacht91-{width}.png"))

        # A later original measurement may replace the short wait with a
        # separate unknown-context exclusion. No metric is filled with zero.
        page.evaluate("""() => {learningData.sampling.status={state:'excluded',
          scope:'heatpump_context',code:'heatpump_heatpump_unknown',
          reason:'Actuele warmtepomptaak niet bevestigd',last_checked_at:Date.now()/1000};
          return c._learningDialog._read(true);} """)
        excluded = quality.locator('[data-sampling-state="excluded"]')
        excluded.wait_for(state="visible")
        assert "staat los van een korte stabilisatiewacht" in excluded.inner_text()
        assert quality.locator('details[data-key="coverage"]').get_attribute("open") is not None
        quality.locator(".close").click()

        card.locator('.footer [data-action="pv_diagnostics"]').click()
        pv_tag = page.evaluate("c._pvDialog.localName")
        pv = page.locator(pv_tag)
        ahead = pv.locator("details[data-pv-ahead-evidence]")
        ahead.wait_for(state="visible")
        ahead.locator(":scope > summary").click()
        cohorts = pv.locator("[data-pv-lead-cohorts]")
        assert "60 unieke doelkwartieren" in cohorts.inner_text()
        assert "8 vastgelegde voorspellingen" in cohorts.inner_text()
        assert cohorts.locator("tbody tr").count() == 6
        assert cohorts.locator('[data-pv-condition="daylight"]').count() == 3
        assert "dezelfde oorspronkelijke meetkwartieren" in cohorts.inner_text()
        assert "niet achteraf ingevuld" in cohorts.inner_text()
        assert pv.locator("img").count() == 0
        for width in (320, 390, 768, 1280):
            page.set_viewport_size({"width": width, "height": 1000})
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"), width
            assert pv.locator("dialog").evaluate("e=>e.scrollWidth<=e.clientWidth+1"), width
            page.screenshot(path=str(OUT / f"SolarPilot-PV-cohorten91-{width}.png"))
        pv.locator(".close").click()

        card.locator('button[role="tab"][data-action="view"][data-value="comfort"]').click()
        panel = card.locator(".heatpump-sg")
        assert "57,5 °C" in panel.inner_text()
        assert "SG-doel bij AAN · berekend" in panel.inner_text()
        panel.locator('details[data-ui-key="sg:comfort:details"] > summary').click()
        assert "Oorspronkelijke stopreden" in panel.inner_text()
        assert "Oude stop: langdurige netafname <img>" in panel.inner_text()
        assert "Actuele herstartvoorwaarde" in panel.inner_text()
        assert "Nieuwe sessie wacht op voldoende actuele zon" in panel.inner_text()
        assert panel.locator("img").count() == 0

        # Missing display confirmation remains unknown and offers only the
        # explicit settings route. It never writes a universal 115% default.
        page.evaluate("""() => {analysisAttributes.panasonic.sg_tank_goal={read_only:true,
          source:'none',reason:'profile_unconfirmed',calculated_c:null};
          c._openOptions=async step=>analysisSettingsRoutes.push(step);
          c._view='overview';publishAnalysis();} """)
        sources = card.locator('[data-boiler-temperatures] button[data-config-step="sg_sources"]')
        assert sources.count() == 1
        sources.click()
        assert page.evaluate("analysisSettingsRoutes") == ["sg_sources"]
        assert "57,5 °C" not in card.locator("[data-boiler-temperatures]").inner_text()
        assert page.evaluate("analysisDeviceCalls.length") == 0
        assert page.evaluate("window.analysisInjected===true") is False
        assert all(call["type"] in ("solar_pilot/learning", "solar_pilot/pv_diagnostics")
                   for call in page.evaluate("analysisCalls"))
        assert not errors, errors
        browser.close()
    print("Analysis beta91 browser validation: timed learning wait, separate unknown-context exclusions, original PV lead cohorts/daylight/dependency, SG stop versus current gate, conditional source-confirmed goal with unknown contact and explicit settings route, escaped evidence, four mobile/desktop widths, read-only RPCs and zero device calls passed. Fictitious evidence only.")


if __name__ == "__main__":
    run()
