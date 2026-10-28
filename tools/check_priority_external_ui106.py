"""Exercise the reported priority moves and external SG countdown in Chromium."""
from pathlib import Path
import json
import os
import shutil

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("SOLARPILOT_SCREENSHOT_DIR", "/tmp/solarpilot-ui106"))
OUT.mkdir(parents=True, exist_ok=True)
errors = []
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=shutil.which("chromium"), headless=True,
                                args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 390, "height": 844}, locale="nl-BE")
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.set_content((ROOT / "SolarPilot-voorbeeld.html").read_text(), wait_until="load")
    page.wait_for_selector("solar-pilot-card >> h1")
    page.evaluate("""() => {
      const c=document.querySelector('solar-pilot-card');window.c=c;window.calls=[];
      const order=['device:dishwasher','wallbox','dhw_extra','device:flex_load'];
      const original=structuredClone(c._last.attributes.priority_board);
      window.board={...original,active:true,revision:'fixture106',order,
        rows:order.map(id=>original.rows.find(row=>row.id===id)),
        wallbox_power:{'device:dishwasher':true,'device:flex_load':true},
        constraints:[{before:'device:dishwasher',after:'dhw_extra',reason:'Beschermde afwas vóór SG'}]};
      c.hass={...c._hass,user:{id:'fixture-admin',is_admin:true},callWS:async message=>{
        calls.push(structuredClone(message));
        if(message.type!=='solar_pilot/priority_board')throw Error('Unexpected endpoint');
        if(message.save){board={...board,order:message.save.order,
          wallbox_power:message.save.wallbox_power,revision:'saved106',message:'Voorrang opgeslagen.'};}
        return structuredClone(board);
      }};
    }""")
    page.locator("solar-pilot-card >> .nav [data-value=priorities]").click()
    page.locator("solar-pilot-card >> [data-action=priority_edit]").click()
    editor = page.locator("solar-pilot-priority-dialog")
    editor.locator('[data-move="dhw_extra"][data-delta="-1"]').click()
    editor.locator('[data-move="device:flex_load"][data-delta="-1"]').click()
    assert page.evaluate("JSON.stringify(c._priorityDialog._order)===JSON.stringify(['device:dishwasher','dhw_extra','device:flex_load','wallbox'])")
    assert editor.locator(".status.error").count() == 0
    # Use the rank/grip rather than a native permission select. Chromium's
    # first dragged move enters a target; later moves deliver the dragover
    # that accepts a drop. Exercise that native sequence with multiple moves.
    page.evaluate("""() => {
      window.priorityDragProof={};const root=c._priorityDialog.shadowRoot;
      const node=el=>el?{tag:el.tagName,row:el.closest('[data-row]')?.dataset.row,
        classes:el.className,action:el.dataset?.move||el.dataset?.action||null}:null;
      const rect=el=>{const r=el.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height};};
      window.priorityDragSnapshot=()=>({order:[...c._priorityDialog._order],
        drag:c._priorityDialog._drag,scrollTop:c._priorityDialog.dialog.scrollTop,
        status:c._priorityDialog.status.textContent,
        dialog:rect(c._priorityDialog.dialog),viewport:{width:innerWidth,height:innerHeight},
        rows:[...root.querySelectorAll('[data-row]')].map(row=>{
          const grip=row.querySelector('.rank'),r=grip.getBoundingClientRect();
          return {id:row.dataset.row,draggable:row.draggable,row:rect(row),grip:rect(grip),
            gripHit:node(root.elementFromPoint(r.x+r.width/2,r.y+r.height/2))};})});
      window.priorityDragDiagnostics={before:priorityDragSnapshot(),events:[]};
      for(const type of ['pointerdown','mousedown','dragstart','dragenter','dragover','drop','dragend','pointerup','mouseup'])
        root.addEventListener(type,e=>{
          if(priorityDragDiagnostics.events.length<100)priorityDragDiagnostics.events.push({
            type:e.type,phase:'capture',target:node(e.target),trusted:e.isTrusted,x:e.clientX,y:e.clientY,
            hit:node(root.elementFromPoint(e.clientX,e.clientY)),
            drag:c._priorityDialog._drag,defaultPrevented:e.defaultPrevented,
            scrollTop:c._priorityDialog.dialog.scrollTop,order:[...c._priorityDialog._order]});
        },{capture:true});
      for(const type of ['dragover','drop'])root.addEventListener(type,e=>{
        if(priorityDragDiagnostics.events.length<100)priorityDragDiagnostics.events.push({
          type:e.type,phase:'after-handler',target:node(e.target),trusted:e.isTrusted,
          defaultPrevented:e.defaultPrevented,drag:c._priorityDialog._drag,
          scrollTop:c._priorityDialog.dialog.scrollTop,order:[...c._priorityDialog._order]});
      });
      root.addEventListener('pointerdown',e=>{
        priorityDragProof.pointerRow=e.target.closest('[data-row]')?.dataset.row;
        priorityDragProof.pointerGrip=!!e.target.closest('.rank');
      },{once:true,capture:true});
      for(const type of ['dragstart','drop'])root.addEventListener(type,e=>{
        priorityDragProof[type]={row:e.target.closest('[data-row]')?.dataset.row,trusted:e.isTrusted};
      },{once:true});
    }""")
    editor.locator('[data-row="device:flex_load"] > .rank').drag_to(
        editor.locator('[data-row="dhw_extra"] > .rank'), steps=20)
    drag_diagnostics = page.evaluate("""({...priorityDragDiagnostics,
      after:priorityDragSnapshot(),proof:priorityDragProof})""")
    print("Priority drag diagnostics: " + json.dumps(drag_diagnostics, ensure_ascii=False), flush=True)
    assert page.evaluate("c._priorityDialog._order.indexOf('device:flex_load')<c._priorityDialog._order.indexOf('dhw_extra')"), drag_diagnostics
    assert page.evaluate("""priorityDragProof.pointerRow==='device:flex_load'&&priorityDragProof.pointerGrip===true&&
      priorityDragProof.dragstart.row==='device:flex_load'&&priorityDragProof.dragstart.trusted===true&&
      priorityDragProof.drop.row==='dhw_extra'&&priorityDragProof.drop.trusted===true""")
    editor.locator("[data-confirm]").check()
    editor.locator("[data-save]").click()
    page.wait_for_function("c._priorityDialog.status.textContent==='Voorrang opgeslagen.'")
    assert page.evaluate("board.order.at(-1)==='wallbox'&&calls.at(-1).save.confirm===true")
    for width in (320, 390, 768, 1280):
        page.set_viewport_size({"width": width, "height": 900})
        assert editor.locator("dialog").evaluate("el=>el.scrollWidth<=el.clientWidth+2")
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path=str(OUT / "priority106-mobile.png"), full_page=True)
    editor.locator("[data-close]").first.click()
    page.locator("solar-pilot-card >> .nav [data-value=overview]").click()
    page.evaluate("""() => {
      const a=structuredClone(c._last.attributes),now=Date.now()/1000;
      a.sg_boost={...a.sg_boost,configured:true,enabled:true,state:'external_on',
        observed_at:now,relay_on:true,relay_confirmed:true,relay_observed_at:now,
        relay_valid_until:null,desired_on:false,owner:'external',
        manual_control:{mode:'auto',active:false},
        external_control:{active:true,duration_s:900,expires_at:now+650,remaining_s:650}};
      c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{
        state:'Zonnestroom',attributes:a}}};
    }""")
    control = page.locator("solar-pilot-card >> [data-sg-manual-control=external]")
    assert control.count() >= 1
    assert "Handmatig aan · automatische overname" in control.first.inner_text()
    assert "daarna beoordelen of SG aan mag blijven" in control.first.inner_text()
    assert "Geen zonneboost aangevraagd; het SG-contact is nog actief" not in page.locator("solar-pilot-card").inner_text()
    page.screenshot(path=str(OUT / "sg-external106-mobile.png"), full_page=True)
    assert not errors, errors
    browser.close()
print("Priority moves, drag, save, mobile layout and external SG countdown OK")
