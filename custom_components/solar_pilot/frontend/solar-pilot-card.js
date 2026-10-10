/* SolarPilot 1.0.0-beta.62. Central priorities, start explanations and evidence-based reliability; no external dependencies. */
const spEscape = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const spPower = value => value == null || !Number.isFinite(Number(value)) ? "—" : Math.abs(Number(value)) >= 1000 ? `${(Number(value)/1000).toLocaleString("nl-BE",{maximumFractionDigits:2})} kW` : `${Math.round(Number(value))} W`;
const spTemp = value => value == null || !Number.isFinite(Number(value)) ? "—" : `${Number(value).toLocaleString("nl-BE",{maximumFractionDigits:1})} °C`;
const spDuration = value => { const s=Math.max(0,Number(value)||0),h=Math.floor(s/3600),m=Math.floor((s%3600)/60); return h?`${h}u${m?` ${m}m`:''}`:`${m}m`; };
const spEuro = value => value == null || !Number.isFinite(Number(value)) ? "—" : new Intl.NumberFormat("nl-BE",{style:"currency",currency:"EUR"}).format(Number(value));
const spKwh = value => value == null || !Number.isFinite(Number(value)) ? "—" : `${Number(value).toLocaleString("nl-BE",{maximumFractionDigits:2})} kWh`;
const spPct = value => value == null || !Number.isFinite(Number(value)) ? "—" : `${Number(value).toLocaleString("nl-BE",{maximumFractionDigits:1})}%`;
const spWallboxMode = value => {
  const raw=String(value??'').trim(),key=raw.toLocaleLowerCase('nl-BE').replace(/[\s-]+/g,'_');
  return ({stopped:'Gestopt',solar:'Zonneladen',full_solar:'Volledig zonneladen',manual:'Handmatig laden',unknown:'Onbekend'})[key]||raw||'Onbekend';
};


/* Read-only popup. Its DOM and polling lifecycle are independent of live card renders. */
class SolarPilotConsumerHistoryDialog extends HTMLElement {
  constructor(){
    super(); this.attachShadow({mode:'open'}); this._seq=0; this._range=7; this._day=null;
    this._isOpen=false; this._lastFetch=0; this._data=null; this._timer=null;
    this.shadowRoot.innerHTML=`<style>
      :host{font-family:var(--paper-font-body1_-_font-family,system-ui,sans-serif);color:var(--primary-text-color,#e6edf5)}
      *{box-sizing:border-box}dialog{color:var(--primary-text-color,#e6edf5);background:var(--card-background-color,#1c1f24);border:1px solid var(--divider-color,#39434d);border-radius:20px;padding:0;width:min(940px,calc(100vw - 24px));max-width:none;max-height:calc(100dvh - 32px);box-shadow:0 20px 80px #0007;overflow:hidden}
      dialog::backdrop{background:#0009}header{padding:20px 22px 14px;border-bottom:1px solid var(--divider-color,#39434d);display:flex;gap:16px;align-items:flex-start}
      .grow{flex:1;min-width:0}h2{font-size:22px;margin:0 0 5px;letter-spacing:-.3px}.device-name{font-size:15px;margin:0;overflow-wrap:anywhere}.live{font-size:12px;margin:9px 0 0;color:var(--secondary-text-color,#a6b2bf);line-height:1.4}
      button,input{font:inherit;color:inherit}button{background:transparent;border:1px solid var(--divider-color,#46515c);border-radius:10px;min-height:40px;padding:8px 12px;cursor:pointer;font-size:12px;font-weight:650}
      button:hover{background:var(--secondary-background-color,#282e37)}button:disabled{opacity:.4;cursor:default}button:focus-visible,input:focus-visible,summary:focus-visible{outline:3px solid var(--primary-color,#00a0c6);outline-offset:2px}
      .close{font-size:24px;line-height:1;width:42px}.navigation{padding:14px 22px 4px;display:flex;gap:8px;align-items:center;flex-wrap:wrap}
      input[type=date]{background:var(--secondary-background-color,#282e37);border:1px solid var(--divider-color,#46515c);border-radius:10px;min-height:40px;padding:8px;width:158px;min-width:0;color-scheme:dark light}
      .update-status{font-size:11px;min-height:24px;padding:4px 22px;color:var(--secondary-text-color,#a6b2bf)}.update-status.error{color:var(--error-color,#ed7575)}
      .scroll{overflow:auto;max-height:calc(100dvh - 270px);min-height:160px;padding:0 22px 22px;overscroll-behavior:contain;scrollbar-gutter:stable}
      .metrics{display:grid;grid-template-columns:2fr 1fr 1fr;gap:10px;margin:10px 0 14px}.metric{padding:14px;border:1px solid var(--divider-color,#39434d);border-radius:14px;min-width:0}.metric label,.metric small{display:block;font-size:11px;color:var(--secondary-text-color,#a6b2bf)}.metric strong{font-size:25px;display:block;margin:5px 0}.metric small{font-size:10px;line-height:1.4;overflow-wrap:anywhere}
      .muted,.note{overflow-wrap:anywhere;color:var(--secondary-text-color,#a6b2bf);font-size:12px;line-height:1.5}.notice{padding:11px 13px;border-left:3px solid var(--warning-color,#e4ae48);background:var(--secondary-background-color,#282e37);border-radius:9px;font-size:12px;line-height:1.5;margin:12px 0}
      h3{font-size:15px;margin:20px 0 10px}.timeline{position:relative;height:30px;background:var(--secondary-background-color,#282e37);border:1px solid var(--divider-color,#39434d);border-radius:9px;overflow:hidden}.segment{position:absolute;height:100%;min-width:2px;background:var(--primary-color,#00a0c6);opacity:.95}.segment.external{background:var(--warning-color,#e4ae48)}.segment.unknown{background:var(--secondary-text-color,#a6b2bf);opacity:.6}.segment.ongoing{background-image:repeating-linear-gradient(135deg,transparent 0 8px,#fff2 8px 11px)}
      .axis{display:flex;justify-content:space-between;font-size:10px;color:var(--secondary-text-color,#a6b2bf);margin-top:7px}.legend{display:flex;gap:14px;flex-wrap:wrap;margin-top:9px;font-size:10px;color:var(--secondary-text-color,#a6b2bf)}.dot{width:8px;height:8px;border-radius:50%;display:inline-block;background:var(--primary-color,#00a0c6);margin-right:4px}.dot.external{background:var(--warning-color,#e4ae48)}.dot.unknown{background:var(--secondary-text-color,#a6b2bf)}
      .period-head{display:flex;align-items:center;gap:8px;margin-top:18px}.period-head h3{margin:0;flex:1}.period-head button[aria-pressed=true]{background:var(--primary-color,#00a0c6);color:var(--text-primary-color,#fff);border-color:transparent}
      .days{display:grid;grid-template-columns:repeat(9,minmax(0,1fr));gap:5px;margin-top:12px}.days.month{grid-template-columns:repeat(10,minmax(0,1fr))}.day{min-width:0;padding:8px 3px 5px;border-radius:9px;display:flex;align-items:center;flex-direction:column;font-weight:500;gap:4px}.day[aria-pressed=true]{border-color:var(--primary-color,#00a0c6);background:var(--secondary-background-color,#282e37)}.bar-slot{height:56px;width:15px;display:flex;align-items:flex-end;background:var(--secondary-background-color,#282e37);border-radius:4px;overflow:hidden}.bar{width:100%;background:var(--primary-color,#00a0c6);min-height:2px}.day.missing .bar-slot{background:repeating-linear-gradient(135deg,transparent 0 4px,var(--divider-color,#39434d) 4px 5px)}.day small{font-size:10px;white-space:nowrap}.day b{font-size:10px;font-weight:600}
      .session{padding:14px;margin:9px 0;border:1px solid var(--divider-color,#39434d);border-radius:13px}.session-head{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.session-head strong{font-size:14px}.duration{margin-left:auto;font-size:13px;font-weight:700}.pill{font-size:10px;border-radius:999px;background:var(--secondary-background-color,#282e37);padding:4px 7px}.pill.running{border:1px solid var(--primary-color,#00a0c6)}.reasons{margin:11px 0 0;display:grid;grid-template-columns:74px 1fr;gap:6px 10px;font-size:12px;line-height:1.5}.reasons dt{color:var(--secondary-text-color,#a6b2bf)}.reasons dd{margin:0;overflow-wrap:anywhere}.empty{padding:24px 12px;border:1px dashed var(--divider-color,#39434d);border-radius:12px;font-size:13px;line-height:1.6;margin-top:12px}.event{padding:10px 0;border-bottom:1px solid var(--divider-color,#39434d);font-size:12px;line-height:1.5}.event time{color:var(--secondary-text-color,#a6b2bf);margin-right:10px}details{margin-top:18px}summary{cursor:pointer;font-size:13px;font-weight:600}
      @media(max-width:540px){dialog{width:calc(100vw - 12px);max-height:calc(100dvh - 12px);border-radius:15px}header{padding:16px 14px 12px}.navigation{padding:12px 14px 4px;gap:6px}.update-status{padding:4px 14px}.scroll{padding:0 14px 18px;max-height:calc(100dvh - 270px)}h2{font-size:19px}.metrics{gap:6px}.metric{padding:10px 8px}.metric strong{font-size:20px}.days{gap:3px}.days.month{grid-template-columns:repeat(9,minmax(0,1fr))}.session{padding:11px}.reasons{grid-template-columns:58px 1fr}.navigation button{padding:8px 10px}.navigation .refresh{margin-left:auto}.device-name{font-size:13px}}
    </style><dialog aria-labelledby="history-title"><header><div class="grow"><h2 id="history-title">Apparaatgeschiedenis</h2><p class="device-name"></p><p class="live"></p></div><button class="close" data-action="close" aria-label="Apparaatgeschiedenis sluiten">×</button></header><div class="navigation"><button data-action="prev" aria-label="Vorige dag">‹</button><input type="date" aria-label="Dag selecteren"><button data-action="next" aria-label="Volgende dag">›</button><button data-action="today">Vandaag</button><button class="refresh" data-action="refresh" aria-label="Geschiedenis vernieuwen">Vernieuwen</button></div><div class="update-status" role="status" aria-live="polite"></div><div class="scroll"><div class="content"><div class="empty">Geschiedenis laden…</div></div></div></dialog>`;
    this._dialog=this.shadowRoot.querySelector('dialog');this._body=this.shadowRoot.querySelector('.content');this._scroll=this.shadowRoot.querySelector('.scroll');this._input=this.shadowRoot.querySelector('input');
    this.shadowRoot.addEventListener('click',e=>this._click(e));
    this._input.addEventListener('change',()=>{if(this._input.value&&this._input.checkValidity())this._selectDay(this._input.value);});
    this._dialog.addEventListener('close',()=>this._cleanup());
    this._dialog.addEventListener('cancel',()=>this._cleanup());
    this._dialog.addEventListener('click',e=>{if(e.target!==this._dialog)return;const r=this._dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)this.close();});
    this._visibility=()=>{if(this._isOpen&&document.visibilityState!=='hidden')this._fetch(false);};
  }
  open(hass,entryId,device){
    this._hass=hass;this._entryId=entryId;this._deviceId=device.id;this._device=device;
    this._day=null;this._data=null;this._lastRenderedDay=null;this._range=7;this._revision=device.history?.revision;
    this._input.value='';this._input.removeAttribute('min');this._input.removeAttribute('max');this._scroll.scrollTop=0;
    this.shadowRoot.querySelector('.device-name').textContent=device.name||'Verbruiker';
    this.shadowRoot.querySelector('.live').textContent=device.reason||'';
    this._body.innerHTML='<div class="empty">Geschiedenis laden…</div>';this._isOpen=true;
    this._dialog.showModal();this.shadowRoot.querySelector('[data-action=close]').focus();
    clearInterval(this._timer);this._timer=setInterval(()=>{if(document.visibilityState!=='hidden')this._fetch(false);},30000);
    document.addEventListener('visibilitychange',this._visibility);
    this._fetch(true);
  }
  setContext(hass,device){
    this._hass=hass;if(!this._isOpen)return;
    if(device){this._device=device;this.shadowRoot.querySelector('.live').textContent=device.reason||'';
      const revision=device.history?.revision;if(revision!==this._revision){this._revision=revision;this._fetch(false);}}
  }
  close(){if(this._dialog.open)this._dialog.close();this._cleanup();}
  _cleanup(){if(!this._isOpen)return;this._isOpen=false;this._seq++;this._inflight=0;clearInterval(this._timer);this._timer=null;document.removeEventListener('visibilitychange',this._visibility);this.dispatchEvent(new CustomEvent('history-closed'));}
  disconnectedCallback(){this.close();}
  _status(text,error=false){const el=this.shadowRoot.querySelector('.update-status');el.textContent=text;el.classList.toggle('error',error);}
  async _fetch(force){
    if(!this._isOpen||(!force&&(this._inflight||Date.now()-this._lastFetch<5000)))return;
    const seq=++this._seq;this._inflight=seq;this._lastFetch=Date.now();
    this._status('Geschiedenis ophalen…');let timeout;
    try{
      const msg={type:'solar_pilot/consumer_history',config_entry_id:this._entryId,device_id:this._deviceId};if(this._day)msg.date=this._day;
      const send=this._hass?.callWS?m=>this._hass.callWS(m):this._hass?.connection?.sendMessagePromise?m=>this._hass.connection.sendMessagePromise(m):null;
      if(!send)throw new Error('Geen Home Assistant-verbinding beschikbaar. Open dit dashboard in Home Assistant.');
      const result=await Promise.race([send(msg),new Promise((_,reject)=>{timeout=setTimeout(()=>reject(new Error('Geen antwoord. Controleer de verbinding en probeer opnieuw.')),15000);})]);
      if(!this._isOpen||seq!==this._seq)return;
      this._data=result;this._day=result.date;this._input.value=result.date;this._input.min=result.first_date;this._input.max=result.today;
      this.shadowRoot.querySelector('[data-action=prev]').disabled=result.date<=result.first_date;
      this.shadowRoot.querySelector('[data-action=next]').disabled=result.date>=result.today;
      this.shadowRoot.querySelector('.device-name').textContent=result.name||this._device?.name||'Verbruiker';
      this.shadowRoot.querySelector('.live').textContent=result.current_status||this._device?.reason||'';
      this._renderData();this._status(`Bijgewerkt ${this._clock(result.generated_at)} · alleen lezen`);
    }catch(err){if(this._isOpen&&seq===this._seq){this._status(err?.message||'Geschiedenis niet beschikbaar; controleer of de nieuwe integratie geladen is.',true);if(!this._data)this._body.innerHTML='<div class="empty">Nog geen geschiedenis geladen. Dit venster schakelt geen apparaten. Gebruik Vernieuwen om opnieuw te proberen.</div>';}}
    finally{clearTimeout(timeout);if(this._inflight===seq)this._inflight=0;}
  }
  _clock(iso){if(!iso)return '—';try{return new Intl.DateTimeFormat('nl-BE',{hour:'2-digit',minute:'2-digit',timeZone:this._data?.timezone||'Europe/Brussels'}).format(new Date(iso));}catch(_){return '—';}}
  _duration(s){if(s==null)return '—';s=Math.max(0,Math.round(Number(s)||0));if(s<60)return `${s} s`;const h=Math.floor(s/3600),m=Math.floor(s%3600/60);return h?`${h} u ${m} min`:`${m} min`;}
  _selectDay(day){this._day=day;this._fetch(true);}
  _shiftDay(n){if(!this._day)return;const d=new Date(this._day+'T12:00:00Z');d.setUTCDate(d.getUTCDate()+n);this._selectDay(d.toISOString().slice(0,10));}
  _click(e){
    const b=e.target.closest('button');if(!b||b.disabled)return;
    if(b.dataset.day){this._selectDay(b.dataset.day);return;}
    const a=b.dataset.action;if(a==='close')this.close();else if(a==='refresh')this._fetch(true);else if(a==='prev')this._shiftDay(-1);else if(a==='next')this._shiftDay(1);else if(a==='today')this._selectDay(this._data?.today||null);else if(a==='range'){this._range=Number(b.dataset.value)===30?30:7;this._renderData();}
  }
  _renderData(){
    const x=this._data;if(!x)return;
    const sameDay=x.date===this._lastRenderedDay, scroll=sameDay?this._scroll.scrollTop:0;
    const eventsOpen=!!this._body.querySelector('details.events')?.open;
    const focusedDay=this.shadowRoot.activeElement?.dataset?.day;
    const days=(x.days||[]).slice(-this._range),max=Math.max(3600,...days.map(d=>Number(d.on_s)||0));
    const sessions=x.sessions||[], labels={solarpilot:'SolarPilot',external:'Extern',unknown:'Onbekend'};
    const pct=v=>Math.min(100,Math.max(0,Number(v)||0));
    const caption=x.has_data?this._duration(x.on_s):'—';
    this._body.innerHTML=`<div class="metrics"><div class="metric"><label>Geregistreerde draaitijd</label><strong data-total>${caption}</strong><small>waargenomen aan-/actiefstatus</small></div><div class="metric"><label>Starts</label><strong>${Number(x.starts)||0}</strong><small>bevestigde overgangen</small></div><div class="metric"><label>Stops</label><strong>${Number(x.stops)||0}</strong><small>meetgaten niet meegeteld</small></div></div>
      ${x.recording_error?`<div class="notice">${spEscape(x.recording_error)}</div>`:''}
      ${x.partial?`<div class="notice">Onvolledige meetdekking: ${this._duration(x.unobserved_s)} van deze dag niet geregistreerd. Ontbrekende perioden zijn geen bewezen stilstand en worden niet bij de draaitijd geteld.</div>`:''}
      <h3>Wanneer ingeschakeld</h3><div class="timeline" role="img" aria-label="Geregistreerde aan-perioden van de gekozen dag">${sessions.map(s=>`<span class="segment ${s.start_source==='external'?'external':s.start_source==='unknown'?'unknown':''} ${s.ongoing?'ongoing':''}" style="left:${pct(s.left_pct)}%;width:${pct(s.width_pct)}%" title="${spEscape(this._clock(s.segment_start)+' – '+this._clock(s.segment_end)+' · '+this._duration(s.duration_s))}"></span>`).join('')}</div><div class="axis"><span>00:00</span><span>${x.day_seconds===86400?'12:00':`${x.day_seconds/3600} uur (tijdwissel)`}</span><span>24:00</span></div><div class="legend"><span><i class="dot"></i>SolarPilot-start</span><span><i class="dot external"></i>Extern gestart</span><span><i class="dot unknown"></i>Begin onbekend</span></div>
      <p class="note">Lege stukken betekenen: geen geregistreerde aan-tijd. Ze bewijzen geen uitschakeling tijdens een meetonderbreking.</p>
      <div class="period-head"><h3>Draaitijd per dag</h3><button data-action="range" data-value="7" aria-pressed="${this._range===7}">7 dagen</button><button data-action="range" data-value="30" aria-pressed="${this._range===30}">30 dagen</button></div>
      <div class="days ${this._range===30?'month':''}">${days.map(d=>`<button class="day ${d.on_s==null?'missing':''}" data-day="${spEscape(d.date)}" aria-pressed="${d.date===x.date}" aria-label="${spEscape(d.date+' · '+(d.on_s==null?'geen registratie':this._duration(d.on_s)))}"><span class="bar-slot">${d.on_s!=null?`<span class="bar" style="height:${pct(Number(d.on_s)/max*100)}%"></span>`:''}</span><small>${spEscape(d.date.slice(8)+'/'+d.date.slice(5,7))}</small><b>${d.on_s==null?'—':spEscape(spDuration(d.on_s))}</b></button>`).join('')}</div>
      <h3>Sessies · ${spEscape(x.date)}</h3>${!sessions.length?`<div class="empty">${x.has_data?'Geen ingeschakelde sessie geregistreerd voor deze dag.':'Voor deze dag is nog geen geschiedenis beschikbaar.'}</div>`:sessions.map(s=>{
        const startLabel=s.continued_from_previous_day?'00:00 (doorlopend)':this._clock(s.segment_start);
        const endLabel=s.continues_next_day?'24:00 (loopt door)':s.ongoing?'loopt nog':this._clock(s.segment_end);
        const startReason=(s.continued_from_previous_day?'Gestart op '+this._clock(s.start)+' in een vorige dag. ':'')+(s.start_reason||'Niet vastgesteld; er is geen betrouwbare eerdere oorzaak geregistreerd.');
        const stopReason=s.continues_next_day?'Nog geen stop: deze sessie loopt door na de gekozen dag.':s.ongoing?'Nog geen stop bevestigd. Laatste waarneming: '+this._clock(s.observed_until):s.stop_reason||'Niet vastgesteld; er is geen betrouwbare stopoorzaak geregistreerd.';
        return `<article class="session"><div class="session-head"><strong>${spEscape(startLabel)} → ${spEscape(endLabel)}</strong><span class="pill ${s.ongoing&&!s.continues_next_day?'running':''}">${spEscape(s.ongoing&&!s.continues_next_day?'Actief':labels[s.start_source]||'Onbekend')}</span><span class="duration">${this._duration(s.duration_s)}</span></div><dl class="reasons"><dt>Startreden</dt><dd>${spEscape(startReason)}</dd><dt>Stopreden</dt><dd>${spEscape(stopReason)}</dd></dl></article>`;}).join('')}
      ${x.sessions_truncated?'<div class="notice">Het maximum aantal bewaarde sessies is bereikt. De dagtotalen blijven beschikbaar; de oudste sessiedetails van deze dag zijn niet meer volledig.</div>':''}
      ${(x.events||[]).length?`<details class="events" ${eventsOpen?'open':''}><summary>Opdrachten, onderbrekingen en meldingen (${x.events.length})</summary>${x.events.map(e=>`<div class="event"><time>${this._clock(e.at)}</time>${spEscape(e.reason)}</div>`).join('')}</details>`:''}
      <p class="note">${spEscape(x.note||'')} Registratie sinds ${spEscape(x.recording_since||'—')}. Geschiedenis blijft lokaal bewaard, maximaal ${Number(x.retention_days)||30} dagen. Geen oude start-/stopredenen verzonnen of uit voorspellingen afgeleid.</p>`;
    this._lastRenderedDay=x.date;this._scroll.scrollTop=scroll;
    if(focusedDay){const b=Array.from(this._body.querySelectorAll('button[data-day]')).find(b=>b.dataset.day===focusedDay);b?.focus({preventScroll:true});}
  }
}
if(!customElements.get('solar-pilot-consumer-history-dialog'))customElements.define('solar-pilot-consumer-history-dialog',SolarPilotConsumerHistoryDialog);

/* An explicit, admin-only download. No background export or upload to ChatGPT. */
class SolarPilotAnalysisDialog extends HTMLElement {
  constructor(){super();this.attachShadow({mode:'open'});this._seq=0;this._open=false;
    this.shadowRoot.innerHTML=`<style>:host{font-family:var(--paper-font-body1_-_font-family,system-ui,sans-serif);color:var(--primary-text-color,#eee)}*{box-sizing:border-box}dialog{width:min(640px,calc(100vw - 28px));max-height:90dvh;overflow:auto;border:1px solid var(--divider-color,#555);border-radius:18px;background:var(--card-background-color,#222);color:inherit;padding:22px}dialog::backdrop{background:#0009}header{display:flex;gap:12px;align-items:center}h2{font-size:22px;margin:0;flex:1}p{line-height:1.55;font-size:14px;color:var(--secondary-text-color,#aaa)}label{display:block;margin:18px 0;font-size:15px}select,button{font:inherit;color:inherit;background:var(--card-background-color,#222);border:1px solid var(--divider-color,#666);border-radius:10px;min-height:44px;padding:9px 12px}select{display:block;width:100%;margin-top:7px}input{min-width:20px;min-height:20px;vertical-align:middle;margin-right:7px}.download{background:var(--primary-color,#009bbd);color:white;font-weight:700;width:100%}.status{white-space:pre-wrap;overflow-wrap:anywhere}.note{border-left:3px solid var(--warning-color,#cf9c23);padding-left:12px}button:disabled{opacity:.5}.close{min-width:44px}button:focus-visible,select:focus-visible,input:focus-visible{outline:3px solid var(--primary-color,#009bbd)}</style>
      <dialog aria-labelledby="analysis-title"><header><h2 id="analysis-title">Analyse-export</h2><button class="close" aria-label="Analyse sluiten">×</button></header>
      <p>Download één gecomprimeerd analysebestand (.json.gz) met instellingen, start- en wachtredenen en alle beschikbare metingen. Ook zeven dagen blijven volledig behouden; compressie maakt het bestand kleiner.</p>
      <label>Periode<select class="hours"><option value="1">Laatste uur</option><option value="24" selected>Laatste 24 uur</option><option value="168">Laatste 7 dagen</option></select></label>
      <label><input type="checkbox" class="names">Echte entiteitsnamen en toestelnamen opnemen</label>
      <p class="note">Zonder vinkje worden namen vervangen door consistente codes. Energie-, temperatuur- en gebruikspatronen blijven persoonlijke gegevens. Controleer het bestand voordat je het zelf in ChatGPT uploadt. SolarPilot verstuurt niets automatisch.</p>
      <details><summary>Welke geschiedenis is beschikbaar?</summary><p>Registratie begint na deze update. Standaard elke 5 minuten, maximaal 7 dagen. De laatste maximaal 2 uur bevat daarnaast regelcycli met hogere resolutie zolang Home Assistant blijft draaien. Een onderbreking blijft een hiaat; er wordt geen verleden verzonnen.</p><p>Actuele en lokaal opgeslagen modellen, dagkosten, toestelsessies, Wallbox, warm water, klimaat, PV, planning, batterijscenario’s, fasebewaking en SolarPilot-fouten zijn inbegrepen. Uitgeschakelde of niet gekoppelde onderdelen worden als zodanig aangeduid.</p></details>
      <p class="status" role="status" aria-live="polite"></p><button class="download">Analysebestand downloaden</button></dialog>`;
    this._dialog=this.shadowRoot.querySelector('dialog');
    this.shadowRoot.querySelector('.close').addEventListener('click',()=>this.close());
    this._dialog.addEventListener('cancel',ev=>{ev.preventDefault();this.close();});
    this._dialog.addEventListener('click',ev=>{if(ev.target===this._dialog){const b=this._dialog.getBoundingClientRect();if(ev.clientX<b.left||ev.clientX>b.right||ev.clientY<b.top||ev.clientY>b.bottom)this.close();}});
    this.shadowRoot.querySelector('.download').addEventListener('click',()=>this._download());
  }
  open(hass,entryId){this._hass=hass;this._entryId=entryId;this._open=true;this._seq++;this.shadowRoot.querySelector('.status').textContent='';this.shadowRoot.querySelector('.download').disabled=!entryId;this._dialog.showModal();}
  close(){if(this._dialog.open)this._dialog.close();this._open=false;this._seq++;}
  disconnectedCallback(){this.close();}
  async _download(){const n=++this._seq,b=this.shadowRoot.querySelector('.download'),status=this.shadowRoot.querySelector('.status'),hass=this._hass;let cleanupPath='';b.disabled=true;status.textContent='Analyse wordt samengesteld…';
    try{const answer=await hass.callWS({type:'solar_pilot/analysis_export',config_entry_id:this._entryId,hours:Number(this.shadowRoot.querySelector('.hours').value),include_names:this.shadowRoot.querySelector('.names').checked,download:true});
      if(answer.download_url&&/^\/api\/solar_pilot\/analysis\/[A-Za-z0-9_-]+$/.test(String(answer.download_url)))cleanupPath=String(answer.download_url);
      if(n!==this._seq||!this._open)return;
      let blob;
      if(answer.download_url){
        const path=String(answer.download_url);
        if(!/^\/api\/solar_pilot\/analysis\/[A-Za-z0-9_-]+$/.test(path))throw new Error('Geen geldig lokaal downloadadres ontvangen');
        if(typeof hass.fetchWithAuth!=='function')throw new Error('Heropen Home Assistant om de beveiligde download te gebruiken');
        status.textContent='Analyse is samengesteld; bestand wordt gedownload…';
        const response=await hass.fetchWithAuth(path,{method:'GET'});
        if(!response.ok)throw new Error(response.status===404||response.status===410?'De download is verlopen. Maak de export opnieuw.':'Download mislukt. Controleer of je als beheerder bent aangemeld.');
        blob=await response.blob();
      }else if(typeof answer.content==='string')blob=new Blob([answer.content],{type:'application/json;charset=utf-8'});
      else throw new Error('Geen bruikbaar exportbestand ontvangen');
      if(n!==this._seq||!this._open)return;
      if(!blob.size)throw new Error('Het ontvangen analysebestand is leeg');
      const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=String(answer.filename||'SolarPilot-analyse.json.gz').replace(/[^a-zA-Z0-9._-]/g,'_');document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),30000);status.textContent='Analysebestand gedownload. Voeg dit bestand zelf toe in ChatGPT; publiceer het niet op GitHub. Compressie laat de metingen intact.';
    }catch(e){if(n===this._seq&&this._open)status.textContent=e?.message||String(e);}finally{
      // Cleanup cannot hold up a received download. Also discard a late result
      // after closing the dialog; the server expiry is the final fallback.
      if(cleanupPath&&typeof hass.fetchWithAuth==='function'){try{Promise.resolve(hass.fetchWithAuth(cleanupPath,{method:'DELETE'})).catch(()=>{});}catch{}}
      if(n===this._seq)b.disabled=false;
    }
  }
}
if(!customElements.get('solar-pilot-analysis-dialog'))customElements.define('solar-pilot-analysis-dialog',SolarPilotAnalysisDialog);

/* Bounded learning inbox: own shadow DOM, no device action or silent permission changes. */
class SolarPilotLearningDialog extends HTMLElement {
  constructor(){
    super();this.attachShadow({mode:'open'});this._seq=0;this._isOpen=false;this._busy=false;this._data=null;
    this.shadowRoot.innerHTML=`<style>
    :host{color:var(--primary-text-color,#e6edf5);font:14px/1.5 system-ui,sans-serif}*{box-sizing:border-box}dialog{color:inherit;background:var(--card-background-color,#1c1f24);border:1px solid var(--divider-color,#39434d);border-radius:18px;padding:0;width:min(940px,calc(100vw - 16px));max-width:none;max-height:calc(100dvh - 24px);overflow:hidden}dialog::backdrop{background:#0009}header{display:flex;gap:12px;padding:18px;border-bottom:1px solid var(--divider-color,#39434d);align-items:center}h2{font-size:21px;flex:1;margin:0}.scroll{padding:0 18px 22px;max-height:calc(100dvh - 180px);overflow:auto;overscroll-behavior:contain;scrollbar-gutter:stable}.status{padding:8px 18px;font-size:12px;min-height:34px}.error{color:var(--error-color,#ed7575)}.note,small{color:var(--secondary-text-color,#a7b0be);font-size:12px;display:block}button,select{font:inherit;color:inherit;border:1px solid var(--divider-color,#48515c);border-radius:9px;padding:8px 11px;background:var(--secondary-background-color,#292e35);min-height:40px;max-width:100%;cursor:pointer}button:disabled{opacity:.5;cursor:default}button:focus-visible,select:focus-visible,summary:focus-visible{outline:3px solid var(--primary-color,#00a0c6);outline-offset:2px}button.close{font-size:23px}.question,.model,.policy{padding:14px;border:1px solid var(--divider-color,#39434d);border-radius:13px;margin:12px 0}.question.attention{border-left:4px solid var(--warning-color,#e2b256)}.question h3,.model h3{font-size:16px;margin:0 0 8px}h3{font-size:16px}.actions{display:flex;flex-wrap:wrap;gap:8px}.question p,.model p{margin:7px 0 12px;overflow-wrap:anywhere}summary{font-weight:600;cursor:pointer;padding:8px 0}.inputs{display:grid;grid-template-columns:1fr 1fr;gap:12px}.inputs label{display:flex;flex-direction:column;gap:5px}.inputs select{width:100%;font-size:13px}label.notification{display:flex;flex-direction:row;gap:8px;align-items:center}.tablewrap{overflow:auto;margin:10px 0;border:1px solid var(--divider-color,#39434d);border-radius:8px}table{border-collapse:collapse;width:100%;font-size:12px}th,td{text-align:left;vertical-align:top;padding:8px;white-space:nowrap;border-bottom:1px solid var(--divider-color,#39434d)}pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:260px;overflow:auto;font-size:11px;background:var(--secondary-background-color,#292e35);padding:10px;border-radius:8px}.tag{display:inline-block;padding:2px 8px;border:1px solid var(--divider-color,#39434d);border-radius:20px;font-size:11px;margin:5px 0}.summary{padding:12px;border-left:3px solid var(--primary-color,#00a0c6);background:var(--secondary-background-color,#292e35);border-radius:10px}.audit{padding:8px 0;border-bottom:1px solid var(--divider-color,#39434d);overflow-wrap:anywhere;font-size:12px}@media(max-width:560px){header{padding:12px;gap:6px}h2{font-size:18px}.scroll{padding:0 12px 16px}.inputs{grid-template-columns:1fr}header button{font-size:12px;padding:8px}.question,.model,.policy{padding:11px}}
    </style><dialog aria-labelledby="learning-title"><header><h2 id="learning-title">Leren & vragen</h2><button class="refresh" aria-label="Leergegevens vernieuwen">Vernieuwen</button><button class="close" aria-label="Leerdialoog sluiten">×</button></header><div class="status" role="status" aria-live="polite"></div><div class="scroll"><div class="body"></div></div></dialog>`;
    this._dialog=this.shadowRoot.querySelector('dialog');this._body=this.shadowRoot.querySelector('.body');this._scroll=this.shadowRoot.querySelector('.scroll');
    this.shadowRoot.querySelector('.close').onclick=()=>this.close();
    this.shadowRoot.querySelector('.refresh').onclick=()=>this._read(true);
    this._dialog.addEventListener('cancel',e=>{e.preventDefault();this.close();});
    this._dialog.addEventListener('click',e=>{if(e.target===this._dialog){const b=this._dialog.getBoundingClientRect();if(e.clientX<b.left||e.clientX>b.right||e.clientY<b.top||e.clientY>b.bottom)this.close();}});
    this._body.addEventListener('click',e=>this._click(e));
  }
  open(hass,entry){this._hass=hass;this._entry=entry;this._isOpen=true;this._busy=false;this._seq++;if(!this._dialog.open)this._dialog.showModal();this._read();clearInterval(this._timer);this._timer=setInterval(()=>this._read(),60000);}
  close(){this._isOpen=false;this._seq++;clearInterval(this._timer);this._timer=null;this._dialog.close();}
  disconnectedCallback(){this.close();}
  _status(text,error=false){const el=this.shadowRoot.querySelector('.status');el.textContent=text;el.classList.toggle('error',error);}
  async _read(force=false){
    if(!this._isOpen||this._busy)return;
    if(!force&&this._body.contains(this.shadowRoot.activeElement)&&['SELECT','INPUT'].includes(this.shadowRoot.activeElement?.tagName))return;
    await this._request({operation:'read'});
  }
  async _request(extra){
    if(!this._hass?.callWS||!this._entry){this._status('SolarPilot-context niet beschikbaar.',true);return;}
    if(this._busy)return;
    this._busy=true;const seq=++this._seq;this._status('Gegevens worden gecontroleerd…');
    this._body.querySelectorAll('button,input,select').forEach(b=>b.disabled=true);
    try{
      const result=await this._hass.callWS({type:'solar_pilot/learning',config_entry_id:this._entry,...extra});
      if(seq!==this._seq||!this._isOpen)return;
      this._data=result;this._render(result);this._status('Lokale gegevens · geen toestelopdracht. Laatste verversing '+new Date().toLocaleTimeString('nl-BE'));
      if(result.navigation){this.dispatchEvent(new CustomEvent('learning-navigation',{detail:result.navigation,bubbles:true,composed:true}));}
      return true;
    }catch(err){if(seq===this._seq&&this._isOpen)this._status(err?.message||'Leerbewerking niet bevestigd; ververs de actuele toestand.',true);return false;}
    finally{if(seq===this._seq){this._busy=false;this._body.querySelectorAll('button,input,select').forEach(b=>b.disabled=false);}}
  }
  _evidence(m){
    const x=m.evidence||{},rows=[];
    const add=(name,value)=>rows.push(`<tr><td>${spEscape(name)}</td><td>${spEscape(value??'onbekend')}</td></tr>`);
    const pct=v=>v==null?'onbekend':`${Math.round(Number(v)*100)}%`;
    if(m.id==='pv'){add('Bruikbare live dagen',x.distinct_live_days);add('Leerwaarnemingen',x.samples);add('Bron voorspelling',x.source);add('Modelzekerheid (geen nauwkeurigheidskans)',pct(x.confidence));add('Factor voor plaatselijke zon',x.factor);}
    else if(m.id==='tank'){add('Afkoeling',x.loss_c_h==null?'onbekend':`${x.loss_c_h} °C/uur`);add('Herkomst afkoeling',x.loss_source);add('Dagen / waarnemingen afkoeling',`${x.loss_days??0} / ${x.loss_samples??0}`);add('Opwarming',x.heat_c_h==null?'onbekend':`${x.heat_c_h} °C/uur`);add('Herkomst opwarming',x.heat_source);add('Dagen / waarnemingen opwarming',`${x.heat_days??0} / ${x.heat_samples??0}`);}
    else if(m.id==='heatpump'){for(const p of Object.values(x.contexts||{}))add(p.label,`${p.status||'Nog niet geleerd'} · ${p.samples??0} stappen · ${p.watts==null?'vermogen nog onbekend':spPower(p.watts)}`);add('Realtime netruimte','gebruikt nooit deze schatting');}
    else if(m.id==='devices'){add('Bevestigde Wallbox-overdrachten',x.successes);add('Mislukte overdrachten',x.failures);add('Gemeten terugmeldinterval',x.reported_interval_median_s==null?'onbekend':`${Math.round(x.reported_interval_median_s)} s`);add('Effectieve wachttijd',`${x.effective_stable_s??'onbekend'} s`);for(const [id,p] of Object.entries(x.profiles||{}))add(id,`${p.samples??0} monsters · mediaan ${spPower(p.median_w)} · P90 ${spPower(p.p90_w)}`);}
    else if(m.id==='phase'){add('Geaccepteerde veranderingen',x.accepted_events);add('Afgewezen veranderingen',x.rejected_events);add('Afzonderlijke regelvrijgave',x.use_for_control?'actief':'niet actief');for(const p of Object.values(x.devices||{}))add(p.name,`${p.classification||'onbekend'} · ${p.reliable?'betrouwbaar':'nog niet betrouwbaar'} · advies ${p.used_for_advice?'ja':'nee'} · regeling ${p.control_allowed?'toegestaan':'niet vrijgegeven'}`);}
    else if(m.id==='battery'){add('Fysieke batterij gekoppeld',x.physical_battery_configured?'ja':'nee');add('What-if-uitkomst','Simulatie, geen gemeten fysieke batterijprestatie');}
    return `<div class="tablewrap"><table><tbody>${rows.join('')}</tbody></table></div><details data-key="raw-${spEscape(m.id)}"><summary>Technische details voor analyse</summary><pre>${spEscape(JSON.stringify(x,null,2))}</pre></details>`;
  }
  _render(data){
    const pos=this._scroll.scrollTop,opens=new Set(Array.from(this._body.querySelectorAll('details[open]'),d=>d.dataset.key));
    const policy=data.policy||{},q=data.quality?.last_7d||{},sam=data.sampling||{},counts=sam.attempts_7d||{};
    const models=(data.models||[]).filter(x=>x.id!=='climate'),pvEvidence=models.find(x=>x.id==='pv')?.evidence||{},baseEvidence=models.find(x=>x.id==='base')?.evidence||{},deviceEvidence=models.find(x=>x.id==='devices')?.evidence||{};
    const pvModel=pvEvidence.forecast_calibration?.model||{};
    const readable={'accepted':'Aanvaarde metingen','accepted_corrected':'Ook tijdens EV/lasten bruikbaar','site_source':'Net/PV-bron onbruikbaar','wallbox_source':'Wallboxmeting onbruikbaar','consumer_source':'Toestelmeting onbruikbaar','settling':'Wacht op stabilisatie','protected_dhw':'Beschermde boilerperiode apart','quiet_policy':'Overgeslagen door rustig-meetbeleid','source_alignment':'Tijdstempels niet passend','learning_disabled':'Leren uitgeschakeld','battery_source':'Batterijbron onbruikbaar','battery_fleet':'Batterijvloot niet gevalideerd','balance':'Energiebalans niet plausibel','sample_interval':'Vorige meting te recent'};
    this._body.innerHTML=`<p class="summary">Leren, toetsen en pas daarna toepassen. Een hoger percentage is niet het doel: minder voorspellingsfouten en minder onnodige ingrepen wel.</p><p class="note">${spEscape(data.contract||'Geen nieuwe fysieke rechten door deze pagina.')}</p>
    <section class="policy"><h3>Hoe mag SolarPilot leren?</h3><div class="inputs"><label><span>Brongebruik <button type="button" data-learning-help="sampling" title="Alleen actuele, afzonderlijke meters aftrekken; geen schattingen leren." aria-label="Uitleg brongebruik">?</button></span><select data-policy="sampling"><option value="metered" ${policy.sampling==='metered'?'selected':''}>Gemeten verbruik meenemen</option><option value="quiet" ${policy.sampling==='quiet'?'selected':''}>Alleen rustige momenten</option></select><small>Geschatte, dubbele, onbereikbare of niet-passende bronnen worden niet als echte meting geleerd.</small></label><label><span>Recent verbruiksprofiel <button type="button" data-learning-help="adaptation" title="Een recent profiel pas gebruiken na onafhankelijke vergelijking en binnen een grens van 25%." aria-label="Uitleg recente voorspellingen">?</button></span><select data-policy="adaptation"><option value="assisted" ${policy.adaptation==='assisted'?'selected':''}>Eerst mijn toestemming</option><option value="automatic" ${policy.adaptation==='automatic'?'selected':''}>Begrensd automatisch</option></select><small>Alleen basislastvoorspelling: minstens 4 vergelijkingsdagen, ≥10% én ≥20 W minder fout, maximaal ±25%. Niet voldoen → gewoon profiel.</small></label></div><label class="notification"><input type="checkbox" data-policy="notifications" ${policy.notifications?'checked':''}>Vragen ook als Home Assistant-melding <button type="button" data-learning-help="notifications" title="Optionele HA-melding, maximaal eens per dag. Geen push of automatische ChatGPT-upload." aria-label="Uitleg meldingen">?</button></label><small>Maximaal één bijgewerkte melding per dag bij nieuwe vragen. Geen pushbericht of ChatGPT-bericht; kies en beoordeel de antwoorden hier.</small><p><button class="save-policy">Mijn leerkeuzes opslaan</button></p></section>
    <section><h3>Acties aanbevolen · ${Number(data.questions?.length||0)}</h3>${(data.questions||[]).map(item=>`<article class="question ${item.severity==='attention'?'attention':''}"><h3>${spEscape(item.title)}</h3><p>${spEscape(item.message)}</p><div class="actions">${(item.choices||[]).map(a=>`<button data-question="${spEscape(item.id)}" data-revision="${spEscape(item.revision)}" data-choice="${spEscape(a.id)}">${spEscape(a.label)}</button>`).join('')}</div></article>`).join('')||'<p>Geen concrete actie nodig. SolarPilot blijft meten en leren binnen de bestaande grenzen.</p>'}</section>
    <section class="model"><h3>Metingen</h3><p>Dekking: <b>${q.covered_hours==null?'nog onbekend':Number(q.covered_hours).toLocaleString('nl-BE')+' uur'}</b> · ${q.coverage_pct==null?'percentage nog onbekend':Number(q.coverage_pct).toLocaleString('nl-BE')+'% van de waargenomen periode'}.</p><p>${spEscape(sam.last?.reason||'Nog geen meetcontrole.')}</p><details data-key="coverage"><summary>Ontbrekende bronnen en technische meetdetails</summary><p class="note">${spEscape(q.coverage_note||'Oude meetdekking wordt niet achteraf ingevuld.')}</p><div class="tablewrap"><table><thead><tr><th>Leerwaarnemingen, laatste 7 kalenderdagen</th><th>Aantal</th></tr></thead><tbody>${Object.entries(counts).map(([key,n])=>`<tr><td>${spEscape(readable[key]||key)}</td><td>${Number(n)}</td></tr>`).join('')}</tbody></table></div></details></section>
    <section class="model"><h3>Zonnevoorspelling</h3><p>Gemiddelde fout bij zon: <b>${spPower(q.pv_daylight_mae_w)}</b>. Systematische richting: <b>${q.pv_daylight_bias_w==null?'onbekend':(q.pv_daylight_bias_w>=0?'forecast gemiddeld te laag '+spPower(q.pv_daylight_bias_w):'forecast gemiddeld te hoog '+spPower(Math.abs(q.pv_daylight_bias_w)))}</b>.</p><p>Lokale kalibratie: <b>${Number(pvModel.days||0)}/${Number(pvModel.minimum_days_required||5)} geldige dagen</b> · ${Math.round(Number(pvEvidence.forecast_calibration?.confidence||0)*100)}% bewijs voor het huidige tijdvak.</p><details data-key="pv-quality"><summary>Ochtend, middag en namiddag</summary><pre>${spEscape(JSON.stringify(pvModel.periods||{},null,2))}</pre></details></section>
    <section class="model"><h3>Huishoudelijk verbruik</h3><p>Voorspelfout gewone basislast: <b>${spPower(q.base_mae_w)}</b> · bias ${q.base_bias_w==null?'onbekend':(q.base_bias_w>=0?'+':'')+spPower(q.base_bias_w)}.</p><p class="note">Warmtepompperioden worden vanaf beta.36 niet meer als gewone huishoudelijke basislast gescoord of aangeleerd. Onverklaarde hoge pieken blijven apart.</p></section>
    <section class="model"><h3>Toestellen</h3><p>${Object.keys(deviceEvidence.profiles||{}).length} toestelprofiel(en) met eigen metingen. Faseherkenning en Wallbox-overdracht tonen afzonderlijk of bewijs betrouwbaar én voor regeling vrijgegeven is.</p><details data-key="device-quality"><summary>Technische toestelprofielen</summary><pre>${spEscape(JSON.stringify(deviceEvidence.profiles||{},null,2))}</pre></details></section>
    <h3>Wat kent SolarPilot al?</h3>${models.map(m=>`<article class="model"><h3>${spEscape(m.name)} <span class="tag">${m.enabled?'Leren / analyseren':'Niet actief'}</span></h3><p>${spEscape(m.state)}</p><p class="note">${spEscape(m.effect)}</p><details data-key="model-${spEscape(m.id)}"><summary>Meetbasis en herkomst</summary>${m.id==='base'?`<div class="tablewrap"><table><thead><tr><th>Uur/dagtype</th><th>Dagen</th><th>Herkomst</th><th>Voorspelling</th><th>Recente variant</th></tr></thead><tbody>${(m.evidence?.buckets||[]).map(b=>`<tr><td>${spEscape(b.bucket)}</td><td>${Number(b.days)}/${Number(b.minimum_days)}</td><td>${spEscape(b.source)}</td><td>${spPower(b.prediction_w)}</td><td>${b.candidate_applied?'Toegepast':b.candidate_eligible?'Beter; toestemming nodig':'Nog niet aangetoond'}</td></tr>`).join('')}</tbody></table></div>`:this._evidence(m)}</details></article>`).join('')}
    <details data-key="audit"><summary>Antwoorden en modelaanpassingen</summary>${(data.audit||[]).slice(-30).reverse().map(x=>`<div class="audit"><strong>${spEscape(x.time)}</strong> ${spEscape(x.event)}<pre>${spEscape(JSON.stringify(x.details,null,2))}</pre></div>`).join('')||'<p>Nog geen keuzes of adaptaties geregistreerd.</p>'}</details><p class="note">${spEscape(data.error||'Geen softwarezelfwijziging. Alle gegevens blijven lokaal en gaan alleen via een bewuste analyse-export naar buiten.')}</p>`;
    this._body.querySelectorAll('details').forEach(d=>d.open=opens.has(d.dataset.key));this._scroll.scrollTop=pos;
  }
  async _click(event){
    const b=event.target.closest('button');if(!b||this._busy)return;
    if(b.dataset.learningHelp){this.dispatchEvent(new CustomEvent('learning-help',{detail:b.dataset.learningHelp,bubbles:true,composed:true}));return;}
    if(b.dataset.question){await this._request({operation:'answer',question:b.dataset.question,revision:b.dataset.revision,choice:b.dataset.choice});return;}
    if(b.classList.contains('save-policy')){
      const changes=Array.from(this._body.querySelectorAll('[data-policy]'),el=>[el.dataset.policy,el.type==='checkbox'?el.checked:el.value]).filter(([k,v])=>v!==this._data?.policy?.[k]);
      for(const [setting,value] of changes){if(!this._isOpen)return;const ok=await this._request({operation:'policy',setting,value});if(!ok)break;}
      if(!changes.length)this._status('Deze leerkeuzes zijn al opgeslagen.');
    }
  }
}
if(!customElements.get('solar-pilot-learning-dialog'))customElements.define('solar-pilot-learning-dialog',SolarPilotLearningDialog);

class SolarPilotPVDialog extends HTMLElement {
  constructor(){
    super();this.attachShadow({mode:'open'});this._seq=0;this._open=false;this._data=null;
    this.shadowRoot.innerHTML=`<style>
      :host{font-family:var(--paper-font-body1_-_font-family,system-ui,sans-serif);color:var(--primary-text-color,#e8edf3)}
      dialog{width:min(1000px,calc(100vw - 30px));max-height:calc(100dvh - 30px);padding:0;border:1px solid var(--divider-color,#43505b);border-radius:22px;background:var(--card-background-color,#17212b);color:inherit;box-sizing:border-box;box-shadow:0 22px 75px #0006}dialog::backdrop{background:#0009}
      header{display:flex;gap:14px;align-items:start;padding:22px;border-bottom:1px solid var(--divider-color,#43505b)}h2{margin:0;font-size:22px}header p{margin:7px 0 0;font-size:13px;color:var(--secondary-text-color,#a9b8c4)}.grow{flex:1}
      button,select{font:inherit;padding:10px 13px;min-height:40px;border:1px solid var(--divider-color,#43505b);border-radius:11px;color:inherit;background:var(--secondary-background-color,#243341);cursor:pointer}button:focus-visible,select:focus-visible{outline:2px solid var(--primary-color,#00a0c6);outline-offset:2px}button:disabled{opacity:.5}.close{font-size:22px;padding:2px 12px}.toolbar{display:flex;gap:9px;align-items:center;flex-wrap:wrap;padding:12px 22px}.status{font-size:12px;padding:0 22px 12px;color:var(--secondary-text-color,#a9b8c4)}.scroll{overflow:auto;max-height:calc(100dvh - 235px);padding:0 22px 22px}.box{border:1px solid var(--divider-color,#43505b);padding:15px;border-radius:15px;margin-bottom:14px}.metrics{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px}.metric{padding:14px;border-radius:13px;background:var(--secondary-background-color,#243341)}.metric small{display:block;font-size:11px;color:var(--secondary-text-color,#a9b8c4)}.metric strong{display:block;font-size:24px;margin-top:6px}.hint{font-size:12px;line-height:1.65;color:var(--secondary-text-color,#a9b8c4)}.warning{border-left:4px solid var(--warning-color,#d8a34f);padding:12px;background:var(--secondary-background-color,#243341);border-radius:8px}.table-wrap{overflow:auto}table{border-collapse:collapse;width:100%;font-size:12px}th,td{padding:11px 8px;border-bottom:1px solid var(--divider-color,#43505b);text-align:left;vertical-align:top}th{color:var(--secondary-text-color,#a9b8c4);font-size:11px}h3{font-size:16px;margin:12px 0}.good{color:var(--success-color,#64c592)}.muted{color:var(--secondary-text-color,#a9b8c4)}details{margin:14px 0}summary{cursor:pointer;font-size:13px;font-weight:600}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:11px}.chart{width:100%;height:170px;display:block;margin-top:10px}.legend{display:flex;gap:16px;font-size:11px;flex-wrap:wrap}.raw{color:var(--secondary-text-color,#a9b8c4)}.corrected{color:var(--primary-color,#00a0c6)}.measured{color:var(--success-color,#64c592)}
      @media(max-width:560px){dialog{width:calc(100vw - 12px);max-height:calc(100dvh - 12px);border-radius:15px}header{padding:17px 14px}h2{font-size:20px}.toolbar{padding:10px 14px}.status{padding:0 14px 10px}.scroll{padding:0 14px 18px;max-height:calc(100dvh - 240px)}.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.metric strong{font-size:21px}.box{padding:11px}th,td{padding:9px 5px}.history{min-width:690px}}
    </style><dialog aria-labelledby="pv-title"><header><div class="grow"><h2 id="pv-title">Zon · voorspelling & diagnose</h2><p>Ruwe bron, lokale correctie en echte productie naast elkaar.</p></div><button class="close" data-action="close" aria-label="Sluiten">×</button></header><div class="toolbar"><label>Dag <select aria-label="Diagnosedag"></select></label><button data-action="refresh">Vernieuwen</button><button data-action="export">Analyse-export</button><button data-action="reset">PV-profiel wissen…</button></div><div class="status" role="status"></div><div class="scroll"><div class="content">Gegevens laden…</div></div></dialog>`;
    this._dialog=this.shadowRoot.querySelector('dialog');this._scroll=this.shadowRoot.querySelector('.scroll');this._body=this.shadowRoot.querySelector('.content');this._days=this.shadowRoot.querySelector('select');
    this._days.addEventListener('change',()=>this._renderData());
    this.shadowRoot.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;switch(b.dataset.action){case'close':this.close();break;case'refresh':this._fetch();break;case'export':this.dispatchEvent(new CustomEvent('pv-export'));break;case'reset':if(window.confirm('Alleen het lokale PV-correctieprofiel en de PV-diagnose wissen? Andere leerdata, instellingen en apparaatstanden blijven behouden.'))this._fetch(true);break;}});
    this._dialog.addEventListener('close',()=>{this._open=false;this._seq++;});
    this._dialog.addEventListener('click',e=>{if(e.target!==this._dialog)return;const r=this._dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)this.close();});
  }
  open(hass,id){this._hass=hass;this._id=id;this._open=true;this._data=null;this._days.replaceChildren();this._body.textContent="Gegevens laden…";this._scroll.scrollTop=0;this._dialog.showModal();this._fetch();}
  close(){this._open=false;this._seq++;if(this._dialog.open)this._dialog.close();}
  disconnectedCallback(){this.close();}
  async _fetch(reset=false){
    if(!this._open)return;const seq=++this._seq;const status=this.shadowRoot.querySelector('.status');status.textContent='Lokale PV-gegevens ophalen…';let timer;
    const msg={type:'solar_pilot/pv_diagnostics',config_entry_id:this._id};if(reset)msg.reset_confirm=true;
    try{const send=this._hass?.callWS?m=>this._hass.callWS(m):m=>this._hass.connection.sendMessagePromise(m);
      const data=await Promise.race([send(msg),new Promise((_,reject)=>timer=setTimeout(()=>reject(new Error('Geen antwoord ontvangen; probeer opnieuw.')),15000))]);
      if(!this._open||seq!==this._seq)return;this._data=data;const chosen=this._days.value,days=[...new Set((data.history||[]).map(x=>String(x.time||'').slice(0,10)))].sort().reverse();
      this._days.replaceChildren();for(const day of days){const opt=document.createElement('option');opt.value=day;opt.textContent=day;this._days.append(opt);}if(days.includes(chosen))this._days.value=chosen;
      this._renderData();status.textContent=(data.summary?.updated?'Bijgewerkt '+new Date(data.summary.updated).toLocaleTimeString('nl-BE'):'Nog geen kwartiergegevens')+' · alleen lezen; geen cloudoproep';
    }catch(e){if(this._open&&seq===this._seq)status.textContent=e?.message||'PV-diagnose niet beschikbaar';}
    finally{clearTimeout(timer);}
  }
  _chart(rows){
    const vals=rows.flatMap(r=>[r.raw_w,r.corrected_w,r.actual_w]).filter(x=>x!=null&&Number.isFinite(Number(x)));if(!vals.length)return '';
    const max=Math.max(100,...vals);const paths=(key)=>{let path='',last=false;rows.forEach((r,i)=>{let v=r[key];if(v==null||!Number.isFinite(Number(v))){last=false;return;}path+=`${last?'L':'M'}${(30+i*730/Math.max(1,rows.length-1)).toFixed(1)},${(150-v/max*135).toFixed(1)} `;last=true;});return path;};
    return `<svg class="chart" viewBox="0 0 780 170" aria-label="Ruw, gecorrigeerd en gemeten PV-verloop"><path d="M30 15V150H760" fill="none" stroke="var(--divider-color,#43505b)"/><text x="32" y="12" fill="currentColor" font-size="10">${spEscape(spPower(max))}</text><path d="${paths('raw_w')}" fill="none" stroke="var(--secondary-text-color,#a9b8c4)" stroke-width="2" stroke-dasharray="4 3"/><path d="${paths('corrected_w')}" fill="none" stroke="var(--primary-color,#00a0c6)" stroke-width="2"/><path d="${paths('actual_w')}" fill="none" stroke="var(--success-color,#64c592)" stroke-width="2"/></svg><div class="legend"><span class="raw">⋯ Forecast.Solar ruw</span><span class="corrected">— lokaal gecorrigeerd</span><span class="measured">— werkelijk gemeten</span></div>`;
  }
  _renderData(){
    const top=this._scroll.scrollTop,opened=[...this._body.querySelectorAll('details')].map(x=>x.open),d=this._data||{},s=d.summary||{},m=s.model||{},rows=(d.history||[]).filter(r=>String(r.time).slice(0,10)===this._days.value),f=x=>x==null?'—':Number(x).toLocaleString('nl-BE',{maximumFractionDigits:2});
    this._body.innerHTML=`<div class="box"><h3>${spEscape(s.status||'Geen gegevens')}</h3><p class="hint">${spEscape(s.note||'Alleen voorspellend; de actuele net- en PV-meters blijven leidend.')}</p>${s.warning||s.error?`<p class="warning">${spEscape(s.warning||s.error)}</p>`:''}<div class="metrics"><div class="metric"><small>Geldige leerdagen</small><strong>${Number(m.days||0)}</strong></div><div class="metric"><small>Factor nu · ${Number(s.comparable_days||0)} vergelijkbare dagen</small><strong>× ${f(s.factor)}</strong></div><div class="metric"><small>Lokale correctiezekerheid</small><strong>${s.confidence==null?'—':Math.round(s.confidence*100)+'%'}</strong></div><div class="metric"><small>Kwartieren gebruikt / geweigerd</small><strong>${Number(m.accepted||0)} / ${Number(m.rejected||0)}</strong></div><div class="metric"><small>Afwijking gecorrigeerd bij zon</small><strong>${spPower(m.mae_w)}</strong></div><div class="metric"><small>AC-omvormer / DC-panelen</small><strong>${spPower(s.inverter_limit_w)}</strong><small>${f(Number(s.panel_peak_wp||0)/1000)} kWp</small></div></div><p class="hint">${spEscape(m.last_reason||'Nog geen volledige meetperiode')}. Het dagenaantal is geen garantie; voor elk zonnestandvak is afzonderlijk bewijs nodig.</p></div>
      <div class="box"><h3>Vooruitkijken, geen vrij vermogen</h3><div class="table-wrap"><table><thead><tr><th>Moment</th><th>Forecast.Solar ruw</th><th>SolarPilot gecorrigeerd</th><th>Factor</th></tr></thead><tbody>${(s.horizon||[]).map(r=>`<tr><td>${r.hours?'+'+Number(r.hours)+' uur':'Nu'}</td><td>${spPower(r.raw_w)}</td><td><strong>${spPower(r.corrected_w)}</strong></td><td>× ${f(r.factor)}</td></tr>`).join('')}</tbody></table></div><p>Vandaag resterend: <b>${spKwh(s.raw_remaining_today_kwh)} → ${spKwh(s.corrected_remaining_today_kwh)}</b></p><p class="hint">${spEscape(s.energy_methods?.remaining_today||'Geen volledige energiedekking')}. Morgen: ${spKwh(s.corrected_tomorrow_kwh)}. Een streepje is onbekend, geen nulproductie.</p></div>
      <p class="hint">${spEscape(s.curve_method||'')} · Native nu-sensor: ${spPower(s.native_raw_now_w)}.</p><div class="box"><h3>Diagnose per kwartier · ${spEscape(this._days.value||'nog geen gegevens')}</h3>${rows.length?this._chart(rows):'<p class="hint">Registratie begint na installatie. De eerste tien minuten worden niet geleerd; daarna zijn volledige kwartieren nodig.</p>'}<div class="table-wrap"><table class="history"><thead><tr><th>Tijd</th><th>Ruw</th><th>Gecorrigeerd</th><th>Werkelijk</th><th>Fout ruw</th><th>Factor</th><th>Leerbesluit</th></tr></thead><tbody>${rows.slice().reverse().map(r=>`<tr><td>${spEscape(String(r.time).slice(11,16))}</td><td>${spPower(r.raw_w)}</td><td>${spPower(r.corrected_w)}</td><td>${spPower(r.actual_w)}</td><td>${r.error_w==null?'—':f(r.error_w)+' W'}<br>${r.error_pct==null?'—':f(r.error_pct)+'%'}</td><td>${f(r.factor)}</td><td class="${r.accepted?'good':'muted'}">${spEscape(r.reason)}</td></tr>`).join('')}</tbody></table></div></div>
      <details><summary>Bronnen, instellingen en beperkingen</summary><pre>${spEscape(JSON.stringify({bronnen:d.sources,forecast_solar:d.source_metadata,gevonden:d.candidate_sources,instellingen:d.settings},null,2))}</pre>${(d.limitations||[]).map(x=>`<p class="hint">${spEscape(x)}</p>`).join('')}</details>`;
    [...this._body.querySelectorAll('details')].forEach((x,i)=>{if(i<opened.length)x.open=opened[i];});this._scroll.scrollTop=top;
  }
}
if(!customElements.get('solar-pilot-pv-dialog'))customElements.define('solar-pilot-pv-dialog',SolarPilotPVDialog);

/* Stable draft editor. Telemetry updates replace the context, never its DOM. */
class SolarPilotPriorityDialog extends HTMLElement {
  constructor(){
    super();this.attachShadow({mode:'open'});this._seq=0;this._busy=false;this._dirty=false;
    this.shadowRoot.innerHTML=`<style>
      :host{font-family:var(--paper-font-body1_-_font-family,system-ui,sans-serif);color:var(--primary-text-color,#202735)}
      *{box-sizing:border-box}dialog{color:inherit;background:var(--card-background-color,#fff);border:1px solid var(--divider-color,#dce1e7);border-radius:20px;padding:22px;width:min(900px,96vw);max-height:92dvh;overflow:auto}dialog::backdrop{background:#0008}
      header{display:flex;gap:16px;align-items:start}header>div{flex:1;min-width:0}h2{font-size:22px;margin:0 0 8px}h3{font-size:15px;margin:10px 0}p{line-height:1.55;margin:7px 0;font-size:13px}small{display:block;line-height:1.5;color:var(--secondary-text-color,#697485);font-size:12px}
      button,select,input{font:inherit;color:inherit}button{min-height:44px;min-width:44px;cursor:pointer;border:1px solid var(--divider-color,#dce1e7);background:var(--card-background-color,#fff);border-radius:10px;padding:9px 13px;font-size:13px}button:disabled{opacity:.45;cursor:default}button:focus-visible,select:focus-visible,input:focus-visible,[draggable]:focus-visible{outline:3px solid var(--primary-color,#287c59);outline-offset:2px}
      .intro{background:var(--secondary-background-color,#f3f5f7);border-radius:12px;padding:12px;margin:12px 0}.rows{list-style:none;margin:14px 0;padding:0;display:grid;gap:10px}.row{display:grid;grid-template-columns:48px minmax(0,1fr) 220px 48px;gap:12px;align-items:center;border:1px solid var(--divider-color,#dce1e7);border-radius:14px;padding:12px}.row.locked{background:var(--secondary-background-color,#f3f5f7)}.rank{font-weight:750;font-size:18px;text-align:center}.rank.fixed{font-size:11px;line-height:1.3}.rank span{font-size:12px;display:block;color:var(--secondary-text-color,#697485)}.title{font-size:14px;overflow-wrap:anywhere}.permission{font-size:12px}.permission b{display:block;margin-bottom:4px}.permission select{display:block;width:100%;min-height:44px;border:1px solid var(--divider-color,#dce1e7);border-radius:8px;padding:7px;background:var(--card-background-color,#fff);margin-top:5px;font-size:12px}.moves{display:grid;gap:5px}.moves button{padding:6px;font-size:20px;font-weight:700}.row.dragover{outline:2px solid var(--primary-color,#287c59)}.note{font-size:12px;margin-top:6px}.actions{position:sticky;bottom:-22px;padding:13px 0;background:var(--card-background-color,#fff);border-top:1px solid var(--divider-color,#dce1e7)}.confirm{display:flex;align-items:start;gap:9px;font-size:13px;line-height:1.5}.confirm input{width:20px;height:20px;flex-shrink:0}.buttons{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}.save{background:var(--primary-color,#287c59);color:var(--text-primary-color,#fff);border-color:transparent}.status{min-height:22px;font-size:13px;line-height:1.5;margin:10px 0}.status.error{color:var(--error-color,#b3261e)}
      @media(max-width:620px){dialog{padding:14px;max-height:95dvh}.row{grid-template-columns:44px minmax(0,1fr) 48px;gap:8px}.permission{grid-column:2;grid-row:2}.moves{grid-column:3;grid-row:1 / span 2}.rank{align-self:start}.actions{bottom:-14px}h2{font-size:20px}}
    </style><dialog aria-labelledby="priority-title"><header><div><h2 id="priority-title">Voorrang en autoladen instellen</h2><p>Alle regels staan in één lijst. Beschermde regels staan vast; de andere regels kun je slepen of met de pijltjes verplaatsen.</p></div><button type="button" data-close aria-label="Voorrang sluiten">✕</button></header><div class="content"></div><p class="status" role="status" aria-live="polite"></p></dialog>`;
    this.dialog=this.shadowRoot.querySelector('dialog');this.content=this.shadowRoot.querySelector('.content');this.status=this.shadowRoot.querySelector('.status');
    this.dialog.addEventListener('cancel',e=>{e.preventDefault();this.close();});
    this.shadowRoot.addEventListener('click',e=>this._click(e));this.shadowRoot.addEventListener('change',e=>this._change(e));
    this.shadowRoot.addEventListener('dragstart',e=>{const row=e.target.closest('[data-row]');if(!row||this._busy||!this._admin())return e.preventDefault();this._drag=row.dataset.row;e.dataTransfer.setData('text/plain',this._drag);e.dataTransfer.effectAllowed='move';});
    this.shadowRoot.addEventListener('dragover',e=>{const row=e.target.closest('[data-row]');if(row&&this._drag){e.preventDefault();e.dataTransfer.dropEffect='move';}});
    this.shadowRoot.addEventListener('drop',e=>{const row=e.target.closest('[data-row]');if(!row||!this._drag)return;e.preventDefault();const key=this._drag;this._drag=null;this._move(key,this._order.indexOf(row.dataset.row));});
    this.shadowRoot.addEventListener('dragend',()=>{this._drag=null;});
  }
  set hass(h){this._hass=h;if(this.dialog.open)this._controls();}
  _admin(){return this._hass?.user?.is_admin===true;}
  _message(text,error=false){this.status.textContent=text;this.status.classList.toggle('error',error);}
  async open(hass,entryId){
    this._hass=hass;this._entryId=entryId;this._opener=this.getRootNode()?.activeElement;this._dirty=false;this._data=null;this._saving=false;
    if(!this.dialog.open)this.dialog.showModal();this.content.textContent='De actuele voorrang wordt opgehaald…';this._message('');
    await this._load();
  }
  async _load(){
    if(!this._admin()||!this._entryId){this.content.textContent='Alleen een beheerder kan deze lijst aanpassen. Het overzicht blijft leesbaar in SolarPilot.';return;}
    const seq=++this._seq;this._busy=true;this._controls();
    try{const data=await this._hass.callWS({type:'solar_pilot/priority_board',config_entry_id:this._entryId});
      if(seq!==this._seq||!this.dialog.open)return;this._accept(data);this._message('Nog niets gewijzigd.');
    }catch(e){if(seq===this._seq)this._message('De lijst kon niet worden geladen: '+(e.message||String(e)),true);}
    finally{if(seq===this._seq){this._saving=false;this._busy=false;this._controls();}}
  }
  _accept(data){
    if(!data||!Array.isArray(data.order)||!Array.isArray(data.rows)||typeof data.revision!=='string')throw Error('Ongeldig antwoord; niets opgeslagen.');
    this._data=structuredClone(data);this._order=[...data.order];this._permissions={...data.wallbox_power};this._dirty=false;this._confirmed=false;this._renderDraft();
  }
  _controls(){
    if(!this.content)return;const readonly=this._busy||!this._admin();
    this.content.querySelectorAll('select,input,[data-move],[data-reload]').forEach(e=>{e.disabled=readonly||e.dataset.edge==='true';});
    this.content.querySelectorAll('[draggable]').forEach(e=>e.draggable=!readonly);
    this.shadowRoot.querySelectorAll('[data-close]').forEach(e=>e.disabled=!!this._saving);
    const save=this.content.querySelector('[data-save]');if(save)save.disabled=readonly||!this._dirty||!this._confirmed;
  }
  _renderDraft(focusKey=null){
    const data=this._data,rows=new Map(data.rows.map(r=>[r.id,r])),powerOutcome=r=>String(r?.power_label||'Niet vastgesteld').replace(/^Wallbox-vermogen:\s*/i,'');
    this.content.innerHTML=`<div class="intro"><p>${spEscape(data.note)}</p><small>‘Ja’ is een toestemming, geen garantie dat er nu vermogen beschikbaar is. Alleen veilige, bevestigde zonnelaadsessies tellen mee.</small></div><ol class="rows priority-stack">${(data.protected||[]).map(r=>`<li class="row locked"><div class="rank fixed">VAST<span aria-hidden="true">🔒</span></div><div class="title"><strong>${spEscape(r.name)}</strong><small>${spEscape(r.active?'Actief':'Niet ingesteld of niet actief')}</small><small class="note">${spEscape(r.reason||'')}</small></div><div class="permission"><b>Mag de auto minder laden?</b><small>${spEscape(powerOutcome(r))}</small></div><div></div></li>`).join('')}${this._order.map((key,n)=>{
      const r=rows.get(key);if(!r)return '';const isDevice=key.startsWith('device:');const yes=this._permissions[key]===true;
      const beforeWallbox=this._order.indexOf(key)<this._order.indexOf('wallbox');
      const relation=!isDevice?powerOutcome(r):!yes?'Nee · alleen werkelijk vrij zonneoverschot.':beforeWallbox?'Ja · dit toestel staat vóór Auto laden.':'Nee · Auto laden staat hoger.';
      const savedPermission=isDevice&&yes&&!beforeWallbox?'<small>Toestemming is bewaard; wordt gebruikt als je dit toestel boven Auto laden zet.</small>':'';
      return `<li class="row" data-row="${spEscape(key)}" draggable="true"><div class="rank">${n+1}<span aria-hidden="true">⠿</span></div><div class="title"><strong>${spEscape(r.name)}</strong><small>${spEscape(r.status||(r.active?'Ingesteld':'Niet actief'))}</small><small class="note">${spEscape(r.reason||'')}</small></div><div class="permission">${isDevice?`<label>Mag de auto minder laden?<select data-power="${spEscape(key)}" aria-label="Mag de auto minder laden voor ${spEscape(r.name)}?"><option value="yes" ${yes?'selected':''}>Ja · binnen veilige grenzen</option><option value="no" ${!yes?'selected':''}>Nee · alleen vrij overschot</option></select></label><small>${spEscape(relation)}</small>${savedPermission}`:`<b>Mag de auto minder laden?</b><small>${spEscape(relation)}</small>`}</div><div class="moves"><button type="button" data-move="${spEscape(key)}" data-delta="-1" data-edge="${n===0}" aria-label="${spEscape(r.name)} hoger">↑</button><button type="button" data-move="${spEscape(key)}" data-delta="1" data-edge="${n===this._order.length-1}" aria-label="${spEscape(r.name)} lager">↓</button></div></li>`;
    }).join('')}</ol><div class="actions"><label class="confirm"><input type="checkbox" data-confirm ${this._confirmed?'checked':''}>Deze volgorde en keuzes toepassen. Lopende programma’s en beschermde looptijden blijven behouden.</label><div class="buttons"><button type="button" class="save" data-save>Voorrang opslaan</button><button type="button" data-close>Annuleren</button><button type="button" data-reload>Actuele instellingen opnieuw laden</button></div></div>`;
    this._controls();if(focusKey){Array.from(this.content.querySelectorAll('[data-move]')).find(e=>e.dataset.move===focusKey&&!e.disabled)?.focus({preventScroll:true});}
  }
  _changed(){this._dirty=JSON.stringify(this._order)!==JSON.stringify(this._data.order)||Object.keys(this._permissions).some(k=>this._permissions[k]!==this._data.wallbox_power[k]);this._confirmed=false;}
  _move(key,index){
    if(this._busy||!this._admin()||!this._order.includes(key)||index<0||index>=this._order.length)return;
    const order=[...this._order];order.splice(order.indexOf(key),1);order.splice(index,0,key);
    const rule=(this._data.constraints||[]).find(c=>order.indexOf(c.before)>=order.indexOf(c.after));
    if(rule){this._message(rule.reason,true);return;}
    this._order=order;this._changed();this._renderDraft(key);this._message('Volgorde aangepast, nog niet opgeslagen.');
  }
  _change(e){if(this._busy||!this._admin())return;
    if(e.target.matches('[data-confirm]')){this._confirmed=e.target.checked;this._controls();}
    if(e.target.matches('[data-power]')){this._permissions[e.target.dataset.power]=e.target.value==='yes';this._changed();const confirm=this.content.querySelector('[data-confirm]');if(confirm)confirm.checked=false;this._controls();this._message('Toestemming aangepast, nog niet opgeslagen.');}
  }
  _click(e){const b=e.target.closest('button');if(!b)return;
    if(b.hasAttribute('data-close'))return this.close();
    if(b.hasAttribute('data-move'))return this._move(b.dataset.move,this._order.indexOf(b.dataset.move)+Number(b.dataset.delta));
    if(b.hasAttribute('data-save'))return this._save();
    if(b.hasAttribute('data-reload')){if(this._dirty&&!window.confirm('Niet-opgeslagen keuzes weggooien en de actuele lijst ophalen?'))return;this._message('');return this._load();}
  }
  async _save(){
    if(this._busy||!this._admin()||!this._dirty||!this._confirmed)return;
    this._saving=true;this._busy=true;this._controls();const seq=++this._seq;this._message('Instellingen opslaan…');
    try{const result=await this._hass.callWS({type:'solar_pilot/priority_board',config_entry_id:this._entryId,save:{revision:this._data.revision,order:[...this._order],wallbox_power:{...this._permissions},confirm:true}});
      if(seq!==this._seq||!this.dialog.open)return;this._accept(result);this._message(result.message||'Voorrang opgeslagen.');this.dispatchEvent(new CustomEvent('priority-saved',{detail:result}));
    }catch(e){if(seq===this._seq){this._confirmed=false;const box=this.content.querySelector('[data-confirm]');if(box)box.checked=false;this._message('Opslag niet bevestigd: '+(e.message||String(e))+'. Je keuzes blijven hier staan. Bij een verbindingsfout: vernieuw eerst de lijst om te controleren wat is opgeslagen.',true);}}
    finally{if(seq===this._seq){this._saving=false;this._busy=false;this._controls();}}
  }
  close(force=false){
    if(!force&&(this._saving||this._dirty&&!window.confirm('Niet-opgeslagen wijzigingen weggooien?')))return;
    this._seq++;this.dialog.close();this._dirty=false;this._saving=false;this._busy=false;this._opener?.focus?.();this.dispatchEvent(new CustomEvent('priority-closed'));
  }
}
if(!customElements.get('solar-pilot-priority-dialog'))customElements.define('solar-pilot-priority-dialog',SolarPilotPriorityDialog);

/* Own UI history only: same URL, no HA router patch, form data or control replay. */
class SolarPilotUiHistory {
  static bus={cards:new Map(),session:`sp-${Date.now()}-${Math.random().toString(36).slice(2)}`,entries:[],cursor:0,applying:false,pending:null};
  constructor(card){this.card=card;this.id=`card-${Math.random().toString(36).slice(2)}`;this.layers=[];this.modals=new Map();this.serial=0;this.connected=false;}
  connect(){if(this.connected)return;this.connected=true;const b=SolarPilotUiHistory.bus;b.cards.set(this.id,this);if(!b.listener){b.listener=e=>SolarPilotUiHistory._pop(e);window.addEventListener('popstate',b.listener);}}
  disconnect(){this.connected=false;this.layers=[];const b=SolarPilotUiHistory.bus;b.cards.delete(this.id);if(!b.cards.size&&b.listener){window.removeEventListener('popstate',b.listener);b.listener=null;b.pending=null;}}
  static _snapshot(){const cards={};for(const [id,h] of this.bus.cards)cards[id]={view:h.card._view,layers:[...h.layers]};return cards;}
  static _marker(state=history.state){return state?.solarPilotUi;}
  static _owned(state=history.state){const m=this._marker(state),b=this.bus;return m?.session===b.session&&Number.isInteger(m.entry)&&!!b.entries[m.entry]&&location.href===b.url;}
  static _state(entry){const state=history.state&&typeof history.state==='object'&&!Array.isArray(history.state)?{...history.state}:{};return{...state,solarPilotUi:{session:this.bus.session,entry}};}
  prepare(){this._opener=this.card.shadowRoot.activeElement;const b=SolarPilotUiHistory.bus;if(!this.connected||b.applying)return;if(b.pending){b.pending=null;this._replaceNext=true;}if(SolarPilotUiHistory._owned()){b.cursor=SolarPilotUiHistory._marker().entry;return;}b.url=location.href;b.entries=[SolarPilotUiHistory._snapshot()];b.cursor=0;b.pending=null;history.replaceState(SolarPilotUiHistory._state(0),'',b.url);}
  _push(){const b=SolarPilotUiHistory.bus;if(!this.connected||b.applying)return;const snapshot=SolarPilotUiHistory._snapshot();if(b.pending||this._replaceNext){b.pending=null;this._replaceNext=false;b.entries[b.cursor]=snapshot;history.replaceState(SolarPilotUiHistory._state(b.cursor),'',b.url);return;}b.entries.splice(b.cursor+1);b.entries.push(snapshot);b.cursor=b.entries.length-1;history.pushState(SolarPilotUiHistory._state(b.cursor),'',b.url);}
  view(view){if(!['overview','loads','comfort','planning','energy','storage','priorities','export','guide'].includes(view)||view===this.card._view)return;this.prepare();this.card._view=view;this.card._renderSignature='';this.card._render();this._push();}
  track(element,restore){
    const dialog=element.dialog||element._dialog;if(!dialog?.open)return;const existing=this.layers.find(key=>this.modals.get(key)?.element===element);if(existing)return;
    if(!element._spHistoryClose){const original=element.close.bind(element);element._spHistoryClose=original;
      element.close=(...args)=>{const value=original(...args);if(value?.then){const pending=Promise.resolve(value);element._spClosingPromise=pending;pending.finally(()=>{if(element._spClosingPromise===pending)element._spClosingPromise=null;}).catch(()=>{});}if(!dialog.open)this._closed(element);return value;};
      dialog.addEventListener('cancel',e=>{e.preventDefault();e.stopImmediatePropagation();element.close();},true);
      dialog.addEventListener('close',()=>{if(!dialog.open)this._closed(element);});
    }
    const key=`${this.id}-modal-${++this.serial}`;this.modals.set(key,{element,restore,opener:this._opener});this.layers.push(key);this._push();
  }
  step(element,restore){const b=SolarPilotUiHistory.bus;if(!this.connected||b.applying)return;const index=this.layers.findIndex(key=>this.modals.get(key)?.element===element);if(index<0)return;const old=this.modals.get(this.layers[index]),key=`${this.id}-modal-${++this.serial}`;this.modals.set(key,{element,restore,opener:old.opener});this.layers[index]=key;this._push();}
  back(element){const b=SolarPilotUiHistory.bus;if(!this.connected||b.applying||!SolarPilotUiHistory._owned()||b.cursor<1||!this.layers.some(key=>this.modals.get(key)?.element===element))return false;b.moving=true;history.go(-1);return true;}
  _closed(element){const before=this.layers.length;this.layers=this.layers.filter(key=>{const e=this.modals.get(key)?.element;return e!==element&&(e?.dialog||e?._dialog)?.open;});const b=SolarPilotUiHistory.bus;if(before===this.layers.length||!this.connected||b.applying||!SolarPilotUiHistory._owned())return;b.pending=SolarPilotUiHistory._snapshot();queueMicrotask(()=>SolarPilotUiHistory._finishClose());}
  static _same(a,b){for(const [id,h] of this.bus.cards){const initial={view:h.card._config?.default_view||'overview',layers:[]};if(JSON.stringify(a[id]||initial)!==JSON.stringify(b[id]||initial))return false;}return true;}
  static _finishClose(){const b=this.bus,wanted=b.pending;if(!wanted||b.applying||!this._owned())return;b.pending=null;let target=b.cursor-1;while(target>=0&&!this._same(b.entries[target],wanted))target--;if(target>=0){b.moving=true;history.go(target-b.cursor);}else{b.entries[b.cursor]=wanted;history.replaceState(this._state(b.cursor),'',b.url);}}
  _canClose(keys){for(const key of [...keys].reverse()){const e=this.modals.get(key)?.element;if(!(e?.dialog||e?._dialog)?.open)continue;if(e._saving||(e.localName==='solar-pilot-options-dialog'&&e._busy))return false;if((e._dirty||e._draftStarted)&&!window.confirm('Niet-opgeslagen wijzigingen weggooien?'))return false;}return true;}
  async _apply(target){
    if(!this.connected)return true;
    const desired=target||{view:this.card._config?.default_view||'overview',layers:[]};const closing=this.layers.filter(key=>!desired.layers.includes(key));
    for(const key of [...closing].reverse()){const item=this.modals.get(key);await item?.element.close?.(true);if((item?.element.dialog||item?.element._dialog)?.open)return false;item?.opener?.focus?.({preventScroll:true});}
    this.layers=this.layers.filter(key=>desired.layers.includes(key));
    if(this.card._view!==desired.view){this.card._view=desired.view;this.card._renderSignature='';this.card._render();}
    for(const key of desired.layers){if(this.layers.includes(key))continue;const item=this.modals.get(key);if(!item)continue;await item.element._spClosingPromise;if(!this.connected)return true;await item.restore();if((item.element.dialog||item.element._dialog)?.open)this.layers.push(key);}
    return true;
  }
  static async _pop(event){
    const b=this.bus;if(!this._owned(event.state))return;const next=this._marker(event.state).entry,previous=b.cursor;if(b.recovering){if(next===previous){b.recovering=false;b.moving=false;}else history.go(previous-next);return;}if(b.applying){b.queued=true;return;}if(next===previous){b.moving=false;return;}b.pending=null;b.applying=true;
    try{const snapshot=b.entries[next];for(const [id,h] of b.cards){const desired=snapshot[id]?.layers||[];if(!h._canClose(h.layers.filter(key=>!desired.includes(key)))){b.recovering=true;b.moving=true;history.go(previous-next);return;}}for(const [id,h] of b.cards){if(!await h._apply(snapshot[id])){b.recovering=true;b.moving=true;history.go(previous-next);return;}}b.cursor=next;}catch(error){b.cursor=next;b.entries[next]=this._snapshot();for(const h of b.cards.values()){h.card._error='Dit venster kon niet worden teruggezet. Open het opnieuw; er is niets opgeslagen.';h.card._render();}}finally{b.applying=false;b.moving=!!b.recovering;if(b.queued){b.queued=false;queueMicrotask(()=>this._pop({state:history.state}));}}
  }
}

class SolarPilotCard extends HTMLElement {
  constructor(){
    super(); this.attachShadow({mode:"open"}); this._busy=false; this._error=""; this._feedback=""; this._view="overview"; this._renderSignature=""; this._lastRenderedView="";
    this._content=document.createElement("div");this.shadowRoot.appendChild(this._content);this._uiHistory=new SolarPilotUiHistory(this);
    this.shadowRoot.addEventListener("click",ev=>this._click(ev));
    this.shadowRoot.addEventListener("change",ev=>this._change(ev));
  }
  setConfig(config){ this._config=config||{}; this._entity=this._config.entity; this._view=this._config.default_view||"overview"; this._last=null; }
  set hass(hass){
    this._hass=hass;
    if(this._optionsDialog)this._optionsDialog.hass=hass;
    if(this._priorityDialog)this._priorityDialog.hass=hass;
    if(!this._entity || !hass.states[this._entity]) this._entity=this._config?.entity || Object.keys(hass.states).find(id=>hass.states[id].attributes?.solar_pilot===true);
    const state=hass.states[this._entity];
    if(state===this._last) return;
    this._last=state;
    if(this._deviceManager){this._deviceManager.hass=hass;this._deviceManager.update(state?.attributes?.device_management);}
    this._historyDialog?.setContext(hass,this._device(this._historyDialog._deviceId));
    if(["INPUT","SELECT","TEXTAREA"].includes(this.shadowRoot.activeElement?.tagName)) return;
    const signature=this._viewRenderSignature();
    if(signature && signature===this._renderSignature) return;
    this._render();
  }
  connectedCallback(){this._uiHistory.connect();}
  disconnectedCallback(){this._uiHistory.disconnect();this._priorityDialog?.close(true);this._deviceManager?.close();this._pvDialog?.close();this._learningDialog?.close();this._analysisDialog?.close();this._historyDialog?.close();this._helpDialog?.close();this._optionsDialog?.close(true);}
  _openPV(){
    this._uiHistory.prepare();
    if(!this._pvDialog){this._pvDialog=document.createElement('solar-pilot-pv-dialog');this.shadowRoot.appendChild(this._pvDialog);this._pvDialog.addEventListener('pv-export',()=>{this._pvDialog.close();this._goExport();});}
    this._pvDialog.open(this._hass,this._last?.attributes?.config_entry_id);this._uiHistory.track(this._pvDialog,()=>this._pvDialog.open(this._hass,this._last?.attributes?.config_entry_id));
  }
  _pvSummary(c){
    const p=c.ems.pv_forecast||{},rows=p.horizon||[];
    return `<section class="pv-summary"><div class="sectionhead"><div><h2>Zon & voorspelling</h2><p>${spEscape(p.status||'Nog geen Forecast.Solar-gegevens')}</p></div><button type="button" class="mini" data-action="pv_diagnostics">PV-diagnose</button></div>${p.warning?this._notice(spEscape(p.warning),true):''}<div class="summarygrid">${rows.map(r=>this._tile(r.hours?'Over '+r.hours+' uur':'Verwacht nu',spPower(r.corrected_w),p.show_raw!==false?'Forecast.Solar ruw: '+spPower(r.raw_w)+' · factor ×'+Number(r.factor||1).toLocaleString('nl-BE'):'Lokale correctie; niet het actuele overschot')).join('')}${this._tile('Vandaag resterend',spKwh(p.corrected_remaining_today_kwh),'energieverwachting; geen meting')}${this._tile('PV-model',Number(p.model?.days||0)+' dagen',p.model?.last_reason||'Wachten op bruikbare kwartiermetingen')}</div><p class="note">${Number(p.panel_peak_wp||0).toLocaleString('nl-BE')} Wp panelen en een AC-limiet zijn verschillende grootheden. De ingestelde grens staat in PV-diagnose. Clipping wordt niet als schaduw geleerd. Realtime verbruik blijft op echte meters geregeld.</p></section>`;
  }
  _openLearning(){
    this._uiHistory.prepare();
    if(!this._learningDialog){this._learningDialog=document.createElement('solar-pilot-learning-dialog');this.shadowRoot.appendChild(this._learningDialog);this._learningDialog.addEventListener('learning-help',e=>this._openHelp('learning_hub',e.detail,'Uitleg leerbeleid'));this._learningDialog.addEventListener('learning-navigation',e=>{this._learningDialog.close();if(e.detail==='export')this._goExport();else if(e.detail==='configure')this._openOptions();});}
    this._learningDialog.open(this._hass,this._last?.attributes?.config_entry_id);this._uiHistory.track(this._learningDialog,()=>this._learningDialog.open(this._hass,this._last?.attributes?.config_entry_id));
  }
  _openAnalysis(){
    this._uiHistory.prepare();
    if(!this._analysisDialog){this._analysisDialog=document.createElement('solar-pilot-analysis-dialog');this.shadowRoot.appendChild(this._analysisDialog);}
    this._analysisDialog.open(this._hass,this._last?.attributes?.config_entry_id);this._uiHistory.track(this._analysisDialog,()=>this._analysisDialog.open(this._hass,this._last?.attributes?.config_entry_id));
  }
  _openHistory(device){
    this._uiHistory.prepare();
    if(!this._historyDialog){
      this._historyDialog=document.createElement('solar-pilot-consumer-history-dialog');this.shadowRoot.appendChild(this._historyDialog);
      this._historyDialog.addEventListener('history-closed',()=>requestAnimationFrame(()=>{
        if(this.isConnected&&!this._historyDialog._isOpen){const b=Array.from(this.shadowRoot.querySelectorAll('button[data-action=history]')).find(b=>b.dataset.id===this._historyDialog._deviceId);b?.focus({preventScroll:true});}
      }));
    }
    this._historyDialog.open(this._hass,this._last?.attributes?.config_entry_id,device);this._uiHistory.track(this._historyDialog,()=>this._historyDialog.open(this._hass,this._last?.attributes?.config_entry_id,this._device(device.id)||device));
  }
  _captureUiState(){
    if(this._lastRenderedView!==this._view) return null;
    const keyed={},details=[];
    for(const d of (this._content||this.shadowRoot).querySelectorAll('details')){
      const key=d.dataset.uiKey;
      if(key)keyed[key]=d.open;else details.push(d.open);
    }
    return {keyed,details};
  }
  _restoreUiState(state){
    if(!state) return;
    let i=0;
    for(const d of (this._content||this.shadowRoot).querySelectorAll('details')){
      const key=d.dataset.uiKey;
      if(key){if(Object.prototype.hasOwnProperty.call(state.keyed||{},key))d.open=!!state.keyed[key];}
      else{if(i<state.details.length)d.open=!!state.details[i];i++;}
    }
  }
  _viewRenderSignature(){
    if(this._view!=="guide") return "";
    const c=this._ctx(),a=c.a;
    return JSON.stringify([this._view,a.mode,a.problem,a.removal,c.guide.rules_hash,this._busy,this._error,this._feedback]);
  }
  getCardSize(){return 9;} getLayoutOptions(){return {grid_columns:12,grid_rows:8};} static getStubConfig(){return {};}
  _ctx(){
    const a=this._last?.attributes||{}, ems=a.ems||{};
    const guideEntity=a.guide_entity || Object.keys(this._hass?.states||{}).find(id=>this._hass.states[id]?.attributes?.solar_pilot_guide===true);
    const guide=guideEntity?(this._hass?.states?.[guideEntity]?.attributes||{}):{};
    return {a,devices:a.devices||[],wb:a.wallbox||{},panasonic:a.panasonic||ems.panasonic||{},sgBoost:a.sg_boost||ems.sg_boost||{},learning:a.learning||{},ems,cap:ems.capacity||{},economy:ems.economy||{},forecast:ems.forecast||{},planner:ems.planner||{},phase:ems.phase||{},localPv:ems.local_pv||{},phaseLearning:ems.phase_learning||{},phaseAttribution:ems.phase_attribution||{},historicalPhase:ems.historical_phase_profile||{},batteryAnalysis:ems.battery_analysis||{},batteryFleet:ems.battery_fleet||{},smartClimate:ems.smart_climate||{},today:ems.today||{},electricityToday:ems.electricity_today||{},guide};
  }
  _tile(label,value,note="",cls="") { return `<div class="tile ${cls}"><span>${spEscape(label)}</span><strong>${value}</strong>${note?`<small>${spEscape(note)}</small>`:''}</div>`; }
  _energyTile(kind,a){
    const meta=a.energy_display||{},source=meta[kind]||{},solar=kind==='pv';
    const number=v=>typeof v==='number'&&Number.isFinite(v),clamp=v=>Math.max(0,Math.min(1,v));
    const watts=source.value_w,stamp=source.reported_at,age=number(stamp)?Date.now()/1000-stamp:Infinity;
    const stale=number(meta.stale_s)&&meta.stale_s>0?meta.stale_s:120;
    const available=number(watts)&&number(stamp)&&age>=-5&&age<=stale&&(!solar||watts>=0)
      &&this._last?.state!=='unavailable'&&this._last?.state!=='unknown'&&!this._last?.attributes?.restored;
    const label=solar?'Zonnepanelen':'Net';
    if(!available)return this._tile(label,'—','Actuele meting ontbreekt','energy-tile energy-unknown');
    const limit=number(meta.inverter_limit_w)&&meta.inverter_limit_w>0?meta.inverter_limit_w:null;
    const reference=number(a.max_import_w)&&a.max_import_w>0?a.max_import_w:limit;
    const fraction=solar?(limit?clamp(watts/limit):null):(watts>0?(reference?clamp(watts/reference):null):0);
    const value=solar?spPower(watts):watts===0?'in balans':`${watts>0?'afname':'injectie'} ${spPower(Math.abs(watts))}`;
    const note=solar?(watts===0?'Geen productie':limit?`${Math.round(watts/limit*100)}% van omvormervermogen`:'actueel'):'P1 · actuele meting';
    if(fraction==null)return this._tile(label,value,note,'energy-tile energy-unknown');
    const hue=solar?120*fraction:watts<0?120:95*(1-fraction);
    const position=solar?fraction:watts<=0?0:fraction;
    const title=solar?`Productiekleur van 0 tot ${spPower(limit)} omvormervermogen.`:`Groen bij injectie; oplopende afname verkleurt tot rood bij ${spPower(reference)}. Dit is een kleurschaal, geen elektrische beveiliging.`;
    return `<div class="tile energy-tile" data-energy="${kind}" style="--energy-hue:${hue.toFixed(1)}" title="${spEscape(title)}"><span>${label}</span><strong>${value}</strong><small>${spEscape(note)}</small><div class="energy-scale ${solar?'solar-scale':'grid-scale'}" aria-hidden="true"><i style="left:${(position*100).toFixed(1)}%"></i></div></div>`;
  }
  _wallboxActivity(wb){
    const known=wb.activity_known??(wb.power_w!=null&&Number.isFinite(Number(wb.power_w))&&wb.last_report_age_s!=null&&Number(wb.last_report_age_s)<=Number(wb.stale_s??120));
    const active=!!known&&Number(wb.power_w)>=Number(wb.charging_threshold_w??50);
    const native=wb.activity_details?.current;
    const label=!known?'LAADSTATUS ONBEKEND':active?'AUTO LAADT':native?.known&&native.active===false&&native.label?String(native.label).toLocaleUpperCase('nl-BE'):wb.activity==='waiting'||wb.demand?'WACHT OP LAADSTROOM':wb.connected===false?'GEEN AUTO AANGESLOTEN':'AUTO LAADT NIET';
    return {known,active,label};
  }
  _deviceActivity(d){
    const known=d.available!==false,active=known&&!!d.on;
    const phase=String(d.dishwasher?.phase||'');
    const phaseLabel=({Running:'Programma loopt',Washing:'Wassen',Prewash:'Voorspoelen','Pre Wash':'Voorspoelen','Pre wash':'Voorspoelen','Main Wash':'Hoofdwas',Rinsing:'Spoelen',Drying:'Drogen','Ado Drying':'Nadrogen',Paused:'Gepauzeerd'})[phase]||phase;
    return {known,active,label:!known?'STATUS ONBEKEND':!active?'UIT':d.kind==='dishwasher'?(d.dishwasher?.airdry?'NADROGEN ACTIEF':'PROGRAMMA ACTIEF'):d.manual_forced?'ACTIEF · HANDMATIG':d.owned?'ACTIEF · SOLARPILOT':'ACTIEF · EXTERN',phase:phaseLabel};
  }
  _activeLoads(c){
    const rows=[];let unknown=c.devices.filter(d=>d.available===false).map(d=>d.name);
    for(const d of c.devices){const activity=this._deviceActivity(d);if(!activity.active)continue;rows.push({name:d.name,status:activity.label,power:d.isolated?null:d.power_w,estimated:!d.isolated&&d.estimated,view:'loads',detail:d.isolated?d.isolation_reason||'Broncontrole; vermogen niet betrouwbaar':d.kind==='dishwasher'?`Programma ${d.dishwasher?.program||'onbekend'}${activity.phase?' · '+activity.phase:''}`:d.reason||'',id:d.id});}
    if(c.wb.enabled){const activity=this._wallboxActivity(c.wb);if(activity.active)rows.push({name:c.wb.name||'Auto laden',status:activity.label,power:c.wb.power_w,view:'loads',detail:c.wb.session_confirmed?spWallboxMode(c.wb.effective_mode):'Werkelijk laadvermogen gemeten; laadmodus niet bevestigd'});else if(!activity.known)unknown.push(c.wb.name||'Wallbox');}
    return `<section class="active-loads" aria-label="Actieve toestellen en programma's"><div class="sectionhead"><h2>Nu actief</h2><button type="button" class="mini" data-action="active_loads">Alle toestellen bekijken</button></div><p class="sub">Wat werkelijk aanstaat of een programma uitvoert. Actief betekent niet dat het toestel op dit moment uitsluitend zonnestroom gebruikt.</p>${rows.length?`<div class="active-list">${rows.map(r=>`<div class="active-load"><div class="grow"><strong>${spEscape(r.name)}</strong> <span class="runstate active">${spEscape(r.status)}</span><small>${spEscape(r.detail)}</small></div><div class="active-power"><b>${r.estimated?'≈ ':''}${spPower(r.power)}</b><small>${r.power==null?'vermogen onbekend':r.estimated?'geschat vermogen':'gemeten vermogen'}</small></div></div>`).join('')}</div>`:'<p class="empty">Geen van de gekoppelde toestellen is nu bevestigd actief.</p>'}${unknown.length?`<p class="note">Niet bevestigd door ontbrekende of verouderde gegevens: ${unknown.map(spEscape).join(', ')}.</p>`:''}<p class="note">De warmtepomp staat in het overzicht afzonderlijk. Een SG-aanvraag bewijst niet dat de warmtepomp nu draait.</p></section>`;
  }
  _savings(c){
    const report=c.ems.savings||{},today=report.today||{},period=report.available_period||{};
    const reference=report.managed_reference?.today||{estimated_benefit_eur:c.economy.enabled?c.today.estimated_value_eur:null,solar_kwh:c.today.managed_solar_kwh};
    const range=period.start_date?`${period.start_date}${period.end_date!==period.start_date?' tot '+period.end_date:''} · ${Number(period.recorded_days||0)} bijgehouden dag(en)`:'Nog geen afzonderlijke meetperiode voor automatische sturing';
    const quality=x=>x.value_partial?'onvolledig: alleen perioden met bruikbare metingen en prijzen':x.power_estimated?'deels geschat toestelvermogen':x.power_quality_unknown?'kwaliteit van het toestelvermogen onbekend':'op basis van gemeten toestelvermogen';
    return `<section class="savings-summary" aria-label="Voordeel van automatische sturing"><h2>Voordeel van automatisch gestuurd zonverbruik</h2><p class="sub">Een schatting in euro, vergeleken met dezelfde energie van het net kopen en de zon terugleveren. Dit is niet de bewezen extra besparing tegenover een woning zonder SolarPilot.</p><div class="summarygrid">
      ${this._tile('Vandaag · geschat voordeel',spEuro(today.estimated_benefit_eur),today.coverage_s>0?`${spKwh(today.solar_kwh)} op zon · ${quality(today)}`:'De afzonderlijke automatische telling begint met deze update.')}
      ${this._tile('Bewaarde periode · geschat voordeel',spEuro(period.estimated_benefit_eur),range)}
      ${this._tile('Bewezen extra besparing door SolarPilot','Nog niet vast te stellen','Geen gemeten vergelijking zonder automatische sturing')}
    </div>${today.value_partial||period.value_partial?'<p class="note">Ontbrekende meetperioden of prijzen worden niet als € 0 ingevuld. Een getoond bedrag kan dus slechts een deel van de periode omvatten.</p>':''}<p class="note">Handmatige starts en boosts tellen niet mee. Autonoom autoladen, boiler en ruimteklimaat zijn niet in dit eurobedrag opgenomen.</p><details><summary>Berekening, meetperiode en eerdere telling</summary><p>${spEscape(report.formula||'Bijgehouden zonnestroom × (afnameprijs − injectievergoeding), per meetinterval.')}</p><p>Huidige afnameprijs: ${c.economy.enabled&&c.economy.import_eur_kwh!=null?Number(c.economy.import_eur_kwh).toLocaleString('nl-BE',{maximumFractionDigits:3})+' €/kWh':'niet beschikbaar'} · injectievergoeding: ${c.economy.enabled&&c.economy.export_eur_kwh!=null?Number(c.economy.export_eur_kwh).toLocaleString('nl-BE',{maximumFractionDigits:3})+' €/kWh':'niet beschikbaar'}. Eerdere meetperioden behouden hun toen gebruikte prijs.</p><p>${spEscape(report.history_note||'De afzonderlijke automatische telling is nog niet beschikbaar. Oude dagtotalen worden niet achteraf als automatische besparing aangemerkt.')}</p><p>${spEscape(report.cost_note||'Dit voordeel zit al in lagere netafname; trek het niet nogmaals van de elektriciteitskost af.')} Vaste kosten en capaciteitstarief zijn niet inbegrepen.</p><p>Reeds geregistreerd gestuurd zonverbruik vandaag: <b>${spKwh(reference.solar_kwh)}</b> · geschatte waarde <b>${spEuro(reference.estimated_benefit_eur)}</b>. Deze oudere, ruimere telling kan ook handmatige bediening bevatten; de historische meetkwaliteit is niet volledig bekend.</p><p>Ook stroom die de auto anders zou gebruiken is niet automatisch extra winst voor SolarPilot. Voor bewezen extra besparing is een betrouwbare vergelijking met de situatie zonder deze sturing nodig.</p></details></section>`;
  }
  _todayCost(c){
    const x=c.electricityToday||{};
    return `<section class="electricity-today"><h2>Elektriciteitskost vandaag · tot nu toe</h2><p class="sub">Gemeten dagcijfers, los van de komende planhorizon. ${spEscape(x.coverage_note||'Wacht op de eerste meetperiode.')}</p><div class="summarygrid">
      ${this._tile('Netafnamekost vandaag',spEuro(x.import_cost_eur),`${spKwh(x.import_kwh)} afgenomen`)}
      ${this._tile('Injectievergoeding vandaag',spEuro(x.export_revenue_eur),`${spKwh(x.export_kwh)} teruggeleverd · aftrek van de netafnamekost`)}
      ${this._tile('Netto elektriciteitskost vandaag',spEuro(x.net_cost_eur),'netafnamekost − injectievergoeding','net-cost')}
      ${this._tile('Rechtstreeks verbruikte zon',spKwh(x.direct_pv_kwh),x.solar_note||'Wordt niet als netafname aangerekend')}
      ${this._tile('Vermeden netaankoop door zon',spEuro(x.pv_avoided_cost_eur),'informatief: al verwerkt in lagere netafname, niet nogmaals aftrekken')}
      ${this._tile('Zonneproductie vandaag',spKwh(x.pv_kwh),x.pv_partial?'PV-meetperiode onvolledig':'gemeten productie')}
    </div><p class="note">${spEscape(x.note||'Indicatief; exclusief vaste kosten en capaciteitstarief.')}${x.legacy_price_estimate?' Bij de update overgenomen dagtotalen zijn eenmalig gewaardeerd tegen het toen ingestelde tarief; daarna worden tariefwijzigingen per meetinterval verwerkt.':''}</p></section>`;
  }
  _wallboxPriority(c){
    const w=c.wb,p=w.consumer_priority||{};
    if(!w.per_device_priority)return '';
    const names=c.devices.filter(d=>d.wallbox_first).map(d=>d.name);
    return `<section class="external wallbox-priority"><h2>Actuele verdeling rond Auto laden</h2><p>${spEscape(p.reason||'Wacht op gegevens')}</p><div class="summarygrid">
      ${this._tile('Minimum zonneladen',w.priority_min_power_w>0?spPower(w.priority_min_power_w):'Nog instellen','afhankelijk van de werkelijk gebruikte laadfasen')}
      ${this._tile('Mogelijk voor de Wallbox',spPower(p.potential_w),'inclusief alleen meetbaar vrij te geven lagere lasten; geen vrije injectie')}
      ${this._tile('Lagere verbruikers',spEscape(names.join(', ')||'geen'),'eigen minimumlooptijd, rusttijd en beschermde cycli blijven gelden')}
    </div>${p.remaining_s?`<p class="note">Resterende wachttijd: ${spDuration(p.remaining_s)}</p>`:''}<p class="note">Zonder laadvraag geen reservering. Klein overschot mag naar lagere verbruikers; bij voldoende stabiel vermogen krijgen die een veilige stop voordat de auto autonoom start. Als de auto niet begint, wordt vermogen niet onbeperkt vastgehouden.</p></section>`;
  }
  _notice(text,warn=false){ return text?`<div class="notice ${warn?'warn':''}">${text}</div>`:""; }
  _nav(){
    const items=[["overview","Overzicht"],["priorities","Voorrang"],["loads","Toestellen"],["comfort","Warmtepomp"],["planning","Planning"],["energy","Energie"],["storage","Batterij"],["export","Export"],["guide","Uitleg"]];
    return `<div class="nav" role="tablist">${items.map(([id,label])=>`<button role="tab" aria-selected="${this._view===id}" class="${this._view===id?'active':''}" data-action="view" data-value="${id}">${label}</button>`).join('')}</div>`;
  }
  _globalAlerts(c){
    const {a,ems}=c;
    const isolated=Array.isArray(a.isolated_devices)?a.isolated_devices:[];
    const automaticRestart=a.restart_recovery_pending===true;
    const sourceWait=!automaticRestart&&a.problem_kind==='source_wait';
    const sourceConfiguration=!automaticRestart&&a.problem_kind==='source_configuration';
    const recoveryNames=Array.isArray(a.restart_recovery_devices)?a.restart_recovery_devices:[];
    const problem=a.problem||(automaticRestart?`Wacht op betrouwbare toestelstatus${recoveryNames.length?': '+recoveryNames.join(' · '):''}; SolarPilot controleert automatisch opnieuw.`:'');
    const title=automaticRestart?'Automatische herstartcontrole':sourceWait?'Automatische broncontrole':sourceConfiguration?'Toestelgegevens controleren':'Aandacht nodig';
    const sourceNote=sourceWait?'SolarPilot controleert automatisch opnieuw zodra actuele gegevens beschikbaar zijn.':sourceConfiguration?'Controleer de gekoppelde bronnen en instellingen van dit toestel.':'';
    const canReset=!automaticRestart&&!sourceWait&&!sourceConfiguration&&a.reset_entity;
    const isolatedNotice=isolated.length?this._notice(`<strong>${isolated.length===1?'Toestel tijdelijk apart gehouden':'Toestellen tijdelijk apart gehouden'}</strong><br>${isolated.map(d=>`${spEscape(d.name)}: ${spEscape(d.reason||'betrouwbare toestelgegevens ontbreken')}`).join('<br>')}<br>Deze toestellen worden tijdelijk niet bediend. SolarPilot controleert automatisch opnieuw.${a.mode==='solar'?'<br>Andere beschikbare toestellen kunnen automatisch verder zodra hun eigen voorwaarden zijn gehaald.':''}${Number(a.isolated_reserve_w)>0?`<br>Veiligheidsreserve voor mogelijk verbruik: ${spPower(a.isolated_reserve_w)}. Dit is geen gemeten verbruik.`:''}`):'';
    const isolatedWait=isolated.length&&(sourceWait||automaticRestart&&a.problem_kind==='restart_wait'&&a.restart_blocking!==true);
    return `${!this._last?this._notice('Geen SolarPilot-status gevonden. Voeg eerst de integratie toe.',true):''}${problem&&!isolatedWait?this._notice(`<strong>${title}</strong><br>${spEscape(problem)}${sourceNote?'<br>'+sourceNote:''}${canReset?'<br><button data-action="reset" class="mini">Controle afronden</button>':''}`,!automaticRestart&&!sourceWait):''}${isolatedNotice}${this._error?`<div role="alert" class="error">${spEscape(this._error)}</div>`:''}${this._feedback?`<div role="status" class="notice">${spEscape(this._feedback)}</div>`:''}${ems.legacy_conflicts?.length?this._notice(`<strong>Dubbele regeling geblokkeerd</strong><br>${ems.legacy_conflicts.map(x=>spEscape(x.name)).join(' · ')}<br>Automatisch regelen blijft geblokkeerd tot deze vervangen regelaars uit staan.`,true):''}`;
  }
  _modeBar(a){
    const mode=a.mode||"observe";
    const resume=a.auto_resume_after_restart===true,linked=!!a.auto_resume_after_restart_entity;
    const protectedPause=['internal_fault','removal','command_fault'].includes(a.pause_cause);
    const pendingResume=a.restart_requested_mode==='solar'&&!protectedPause;
    const pausePolicy=protectedPause?'Deze bescherming wordt niet automatisch opgeheven.':pendingResume?'SolarPilot hervat automatisch zodra de herstartcontrole klaar is.':resume?'Bij de volgende herstart hervat SolarPilot automatisch na de opstartcontrole.':'Pauze blijft na een herstart behouden. Kies Automatisch regelen om te hervatten.';
    const pauseReason=a.pause_reason?`${spEscape(a.pause_reason)}<br>`:'';
    const paused=mode==='paused'?this._notice(`${pauseReason}Geen nieuwe starts. Eigen onderbreekbare lasten worden veilig vrijgegeven; beschermde cycli mogen afwerken.<br>${pausePolicy}`,protectedPause):'';
    const restartSwitch=`<div class="restart-policy"><span>Na herstart automatisch hervatten<small>Geldt voor Pauze; Alleen bekijken blijft behouden.</small></span><button type="button" class="toggle mini ${resume?'active':''}" data-action="restart_auto" role="switch" aria-label="Na herstart automatisch hervatten" aria-checked="${resume}" ${this._busy||!linked?'disabled':''}>${linked?(resume?'Aan':'Uit'):'Niet beschikbaar'}</button></div>`;
    const observeNotice=mode==='observe'?this._notice(pendingResume?`${pauseReason}SolarPilot hervat automatisch zodra de herstartcontrole klaar is.`:'Alleen kijken, leren en adviseren. Er worden geen gewone flexibele verbruikers bediend. Alleen bekijken blijft ook na een herstart behouden.'):'';
    return `<div class="modes">${[["observe","Alleen bekijken"],["solar","Automatisch regelen"],["paused","Pauze"]].map(([v,l])=>`<button data-action="mode" data-value="${v}" class="${mode===v?'active':''}" ${this._busy?'disabled':''}>${l}</button>`).join('')}</div>${restartSwitch}${observeNotice}${paused}`;
  }
  _reasonTime(value){
    if(value==null)return '';
    const stamp=typeof value==='number'?value*1000:Date.parse(value);
    if(!Number.isFinite(stamp)||stamp<=0)return '';
    try{return new Date(stamp).toLocaleString('nl-BE',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit',timeZone:this._hass?.config?.time_zone||undefined});}catch{return '';}
  }
  _plainReason(value){
    return String(value||'Nog geen betrouwbare reden beschikbaar.').replace(/\bcoast\b/gi,'periode zonder verwarming of koeling').replace(/\bnative\b/gi,'toestel').replace(/\bP1\b/g,'netmeter').replace(/\bACK\b/g,'bevestiging');
  }
  _knownPower(value,{known=true,estimated=false,label='Vermogen'}={}){
    const valid=known&&value!=null&&value!==''&&Number.isFinite(Number(value));
    return `<div class="reason-power"><b>${valid?spPower(Math.abs(Number(value))):'Vermogen nog niet bekend'}</b>${valid?`<small>${spEscape(label)} · ${estimated?'geschat':'gemeten'}</small>`:''}</div>`;
  }
  _powerReadingKnown(power){
    if(power?.valid!==true||power.value_w==null||!Number.isFinite(Number(power.value_w))||Number(power.value_w)<0)return false;
    const stamp=Number(power.measured_wall),limit=Number(power.stale_s),age=Date.now()/1000-stamp;
    return Number.isFinite(stamp)&&stamp>0&&Number.isFinite(limit)&&limit>0&&age>=-5&&age<=limit;
  }
  _reasonFacts(facts){
    return `<div class="start-facts">${facts.map(([label,value])=>`<span>${spEscape(label)}<b>${spEscape(value)}</b></span>`).join('')}</div>`;
  }
  _remainingTime(value){
    if(value==null||value===''||!Number.isFinite(Number(value)))return 'nog niet bekend';
    return Number(value)<=0?'gereed':Number(value)<60?`nog ${Math.ceil(Number(value))} s`:`nog ${spDuration(value)}`;
  }
  _overviewBatteryExplanation(fleet){
    const names=new Map((fleet.batteries||[]).map(b=>[b.id,b.name||'Batterij']));
    const faults=Object.entries(fleet.faults||{}),pending=fleet.pending&&typeof fleet.pending==='object'&&Object.keys(fleet.pending).length?fleet.pending:null;
    const control=faults.length?'Controle nodig':pending?'Wacht op bevestiging':fleet.control_enabled?'Regeling aan':'Alleen bekijken';
    const facts=[['Bediening',control],['Laadvermogen',fleet.aggregate?.valid===true?spPower(fleet.aggregate.charge_w):'nog niet bekend'],['Vermogen naar huis',fleet.aggregate?.valid===true?spPower(fleet.aggregate.discharge_w):'nog niet bekend']];
    const status=[...faults.map(([id,reason])=>`${names.get(id)||'Batterij'}: ${this._plainReason(reason)}`),...(pending?[`${names.get(pending.id)||'Batterij'}: wacht op bevestiging van de eerdere opdracht.`]:[])];
    return `${this._reasonFacts(facts)}${status.length?`<div class="condition-group waiting"><b>${faults.length?'Controle nodig':'Wacht op bevestiging'}</b><ul>${status.map(x=>`<li>${spEscape(x)}</li>`).join('')}</ul></div>`:''}<p><b>Advies voor de batterij:</b> ${spEscape(this._plainReason(fleet.reason))}</p>${(fleet.batteries||[]).map(b=>`<p><b>${spEscape(b.name||'Batterij')}</b> · ${b.valid===true?'metingen beschikbaar':'wacht op betrouwbare metingen'} · ${b.control_kind==='read_only'||!b.control_enabled||!b.exclusive_control_confirmed?'alleen bekijken':'bediening vrijgegeven'}</p>`).join('')}<p class="note">Het advies is geen bevestiging dat een opdracht uitgevoerd is. ${!fleet.control_enabled?'SolarPilot stuurt deze batterij niet aan.':'De precieze uitvoerreden is alleen bekend als de regeling die heeft gemeld.'}</p>`;
  }
  _reasonRow({name,state,reason,extra='',change=null,view='',id='',key='',details='',power='',activity='inactive'}){
    const time=change?this._reasonTime(change.at||change.timestamp):'';
    const last=change?.reason?`<details class="reason-history" data-ui-key="${spEscape(key+':history')}"><summary>Laatste ${change.confirmed===false?'waarneming':'verandering'}${time?' · '+spEscape(time):''}</summary><p>${spEscape(this._plainReason(change.reason))}</p>${['external','Home Assistant'].includes(change.source)?'<small>Buiten een bevestigde SolarPilot-opdracht veranderd; de precieze veroorzaker is niet bekend.</small>':''}</details>`:'';
    const visual=['active','available','unknown'].includes(activity)?activity:'inactive';
    return `<article class="reason-row is-${visual}" data-activity="${visual}"><div class="row"><strong class="grow">${spEscape(name)}</strong><span class="badge">${spEscape(state)}</span></div>${power}<p>${spEscape(this._plainReason(reason))}</p>${extra?`<small>${spEscape(extra)}</small>`:''}${details?`<details class="reason-details" data-ui-key="${spEscape(key+':why')}"><summary>Waarom wel of nog niet?</summary>${details}</details>`:''}${last}${id?`<button type="button" class="mini" data-action="history" data-id="${spEscape(id)}">Geschiedenis</button>`:view?`<button type="button" class="mini" data-action="view" data-value="${spEscape(view)}">Instellen en details</button>`:''}</article>`;
  }
  _decisionBoard(c){
    const rows=[],p=c.panasonic||{},s=c.sgBoost||{};
    if(p.configured||s.configured){
      const active=s.relay_confirmed===true&&s.relay_on===true;
      const status=s.relay_confirmed!==true?'Contactstatus onbekend':active?'SG-contact actief':'SG-contact open';
      rows.push(this._reasonRow({name:'Warmtepomp — Panasonic-regeling',state:status,reason:s.reason||'Panasonic regelt zelfstandig; zonneboost is niet ingesteld.',extra:`Tank ${spTemp(p.temperature_c??s.temperature_c)} · ${active&&s.panasonic_confirmed!==true?'Panasonic-reactie niet afzonderlijk bevestigd.':'Panasonic regelt comfort en beveiligingen.'}`,view:'comfort',key:'overview:sg',details:this._sgDetails(c,'overview'),power:this._heatpumpPower(c),activity:active?'active':s.desired_on===true?'available':s.relay_confirmed!==true?'unknown':'inactive'}));
    }
    for(const device of c.devices||[]){
      const reason=device.isolation_reason||device.start_diagnostics?.summary||device.reason;
      const activity=this._deviceActivity(device);
      const state=!activity.known?'Niet bereikbaar':activity.active?device.kind==='dishwasher'?(device.dishwasher?.airdry?'Nadrogen actief':'Programma loopt'):(device.manual_forced?'Actief · handmatig':device.owned?'Actief · SolarPilot':'Actief · toestel'):device.mode==='disabled'?'Niet automatisch geregeld':device.kind==='dishwasher'&&!device.dishwasher?.app_request?'Nog niet klaargezet':'Wacht';
      const w=device.dishwasher||{},checks=device.kind==='dishwasher'?this._dishwasherGates(w):[];
      const deadline=w.start_deadline?this._reasonTime(w.start_deadline):'';
      const programme=device.kind==='dishwasher'?this._reasonFacts([['Programma',w.program||'nog niet bekend'],['Vrijgegeven beurt',w.app_request||w.ticket_armed?'klaargezet':w.app_request===false&&w.ticket_armed===false?'nog niet klaargezet':'nog niet bekend'],['Uiterlijk starten',deadline||'nog niet bekend']]):'';
      rows.push(this._reasonRow({name:device.name,state,reason,extra:activity.active&&device.kind==='dishwasher'?'Een lopend programma wordt niet onderbroken.':'',change:device.history?.last_change,id:device.id,key:'overview:device:'+device.id,details:programme+this._startExplanation(device,c.a?.mode,checks),power:this._knownPower(device.power_w,{known:activity.known&&!device.isolated,estimated:device.estimated===true}),activity:activity.active?'active':activity.known?'inactive':'unknown'}));
    }
    if(c.wb?.enabled){
      const wb=c.wb,activity=this._wallboxActivity(wb),observation=wb.activity_details||{},current=observation.current||{};
      rows.push(this._reasonRow({name:'Auto laden',state:activity.label,reason:current.reason||(activity.active?'De auto laadt; de Wallbox bepaalt zelf het laden.':activity.known?'De auto laadt nu niet; de Wallbox heeft geen precieze wachtreden gemeld.':'Wacht op een betrouwbare laadstatus.'),extra:this._plainReason(wb.consumer_priority?.reason||wb.reason||'SolarPilot leest de Wallbox en verdeelt het resterende overschot.'),change:observation.last_stop?{at:observation.last_stop.observed_stop_at,reason:observation.last_stop.stop_reason,confirmed:observation.last_stop.stop_confirmed}:null,view:'priorities',key:'overview:wallbox',details:this._wallboxExplanation(wb,activity,'overview:wallbox:periods'),power:this._knownPower(wb.power_w,{known:activity.known,label:'Auto laden'}),activity:activity.active?'active':activity.known?'inactive':'unknown'}));
    }
    if(c.batteryFleet?.enabled){
      const fleet=c.batteryFleet,aggregate=fleet.aggregate||{},charging=aggregate.valid===true&&Number(aggregate.charge_w)>50,discharging=aggregate.valid===true&&Number(aggregate.discharge_w)>50;
      const control=Object.keys(fleet.faults||{}).length?'Controle nodig':Object.keys(fleet.pending||{}).length?'Wacht op bevestiging':fleet.control_enabled?'Regeling aan':'Alleen bekijken';
      const actual=charging&&discharging?'Batterijen laden en leveren stroom':charging?'Batterij laadt':discharging?'Batterij levert stroom':'';
      const reason=Object.keys(fleet.faults||{}).length?'Een batterijopdracht vraagt controle.':Object.keys(fleet.pending||{}).length?'Wacht op bevestiging van een batterijopdracht.':!fleet.control_enabled?'SolarPilot bekijkt de batterij en geeft advies.':fleet.reason?`Batterijadvies: ${fleet.reason}`:'Nog geen batterijadvies ontvangen.';
      rows.push(this._reasonRow({name:'Batterij',state:actual?`${actual} · ${control}`:control,reason,view:'storage',key:'overview:battery',details:this._overviewBatteryExplanation(fleet),power:this._knownPower(aggregate.power_w,{known:aggregate.valid===true,label:Number(aggregate.power_w)<0?'Netto laden':Number(aggregate.power_w)>0?'Netto naar huis':'Netto batterijvermogen'}),activity:actual?'active':'inactive'}));
    }
    return `<section class="decision-board"><style>.decision-board{--sp-activity-blue:#03a9f4;margin:22px 0}.decision-board>p{color:var(--secondary-text-color);font-size:13px}.reason-list{display:grid;align-items:start;gap:12px;grid-template-columns:repeat(auto-fit,minmax(min(100%,310px),1fr))}.reason-row{min-width:0;border:1px solid var(--divider-color);border-radius:16px;padding:16px;background:var(--card-background-color)}.reason-row.is-active{border-color:var(--sp-activity-blue);box-shadow:inset 4px 0 0 var(--sp-activity-blue)}.reason-row.is-active .badge{background:var(--sp-activity-blue);color:#071b26}.reason-row.is-available{border-color:var(--sp-activity-blue);border-style:dashed}.reason-row .row{gap:8px;align-items:flex-start;flex-wrap:wrap}.reason-row .badge{white-space:normal;font-size:11px}.reason-row p{line-height:1.5;margin:9px 0;overflow-wrap:anywhere;font-size:14px}.reason-row>small,.reason-history small{display:block;color:var(--secondary-text-color);font-size:12px;line-height:1.5}.reason-row .mini{margin-top:10px}.reason-power{margin:10px 0}.reason-power>b{font-size:18px}.reason-power>small,.shared-heatpump-power>small{display:block;color:var(--secondary-text-color);font-size:12px;line-height:1.5}.shared-heatpump-power{padding:12px 16px;border:1px solid var(--divider-color);border-radius:12px;margin:12px 0}.reason-details>summary{padding:10px 12px;background:var(--secondary-background-color);border:1px solid var(--divider-color);border-radius:10px;font-size:12px;line-height:1.4}.reason-details[open]>summary{border-color:var(--sp-activity-blue)}.reason-details .start-facts{grid-template-columns:repeat(2,minmax(0,1fr))}.reason-details .start-facts b{display:block;overflow-wrap:anywhere}.condition-group{margin:12px 0;font-size:12px;line-height:1.5}.condition-group ul{padding-left:18px;margin:6px 0}.condition-group.ready>b{color:var(--success-color,#4caf50)}.condition-group.waiting>b{color:var(--warning-color,#ffb300)}.reason-details .note{font-size:12px}@media(max-width:420px){.reason-details .start-facts{grid-template-columns:1fr}}.reason-history{margin-top:10px;font-size:12px}.reason-history summary{cursor:pointer;padding:4px 0}.reason-history p{font-size:12px}.activity-legend{display:flex;gap:8px 18px;flex-wrap:wrap;margin:12px 0;color:var(--secondary-text-color);font-size:12px}.activity-legend span{display:flex;align-items:center;gap:6px}.activity-swatch{width:14px;height:14px;border:2px solid var(--sp-activity-blue);border-radius:4px;box-shadow:inset 3px 0 0 var(--sp-activity-blue)}.activity-swatch.available{border-style:dashed;box-shadow:none}</style><h2>Wat gebeurt er en waarom?</h2><p>Hier zie je wat elk toestel nu doet, waarom het wacht en welke verandering het laatst is waargenomen.</p><div class="activity-legend" aria-label="Betekenis van de blauwe randen"><span><i class="activity-swatch" aria-hidden="true"></i>Bevestigd actief</span><span><i class="activity-swatch available" aria-hidden="true"></i>Aanvraag wacht op bevestiging</span></div><div class="reason-list">${rows.join('')||'<p>Nog geen gekoppelde toestellen.</p>'}</div></section>`;
  }
  _overview(c){
    const {a,panasonic,sgBoost,wb,cap,forecast,localPv,batteryFleet,batteryAnalysis,phase,today,planner,ems}=c;
    const batteryText=batteryFleet.enabled?(batteryFleet.aggregate?.soc_pct==null?'vloot actief':`${spPct(batteryFleet.aggregate.soc_pct)} · ${spPower(batteryFleet.aggregate?.power_w)}`):(batteryAnalysis.enabled?'what-if actief':'niet gekoppeld');
    const managedNote=a.isolated_devices?.length?'Deel van de toestelgegevens ontbreekt; mogelijk verbruik wordt apart gereserveerd.':`${a.energy_estimated?'deels geschat':'gemeten of teruggemeld'} · autoladen apart`;
    return `<section class="view overview-view">
      <div class="flowgrid">
        ${this._energyTile('pv',a)}
        ${this._energyTile('grid',a)}
        ${this._tile(a.isolated_devices?.length?'Bekend vermogen SolarPilot-toestellen':'Vermogen SolarPilot-toestellen',`${a.energy_estimated?'≈ ':''}${spPower(a.managed_w)}`,managedNote)}
        ${this._tile('Vrij overschot',spPower(a.free_w),`reserve ${spPower(a.reserve_w)}`)}
      </div>
      <p class="energy-legend">Zon: rood weinig → groen veel. Net: groen injectie → geel, oranje en rood bij afname. Kleur is geen foutmelding.</p>
      ${this._decisionBoard(c)}
      <details class="technical-overview" data-ui-key="overview:technical"><summary>Metingen, voorspellingen en technische details</summary>
      ${this._activeLoads(c)}<div class="summarygrid">
        ${this._tile('Warmtepomp',spTemp(panasonic.temperature_c),sgBoost.reason||'Panasonic regelt zelfstandig')}
        ${this._tile('Wallbox',wb.enabled?`${spEscape(this._wallboxActivity(wb).label)} · ${spPower(wb.power_w)}`:'niet gemonitord',wb.enabled?'De Wallbox bepaalt zelf het laden; SolarPilot leest de status.':'',wb.enabled&&this._wallboxActivity(wb).active?'active-tile':'')}
        ${this._tile('Batterij',batteryText,batteryFleet.reason||batteryAnalysis.note||'')}
        ${this._tile('Kwartierpiek',cap.enabled?(cap.current_average_w==null?'—':spPower(cap.current_average_w)):'uit',cap.enabled?`vrije ruimte ${spPower(cap.optional_headroom_w)}`:'')}
        ${this._tile('Lokale PV-voorspelling',localPv.enabled?(localPv.corrected_power_w==null?'—':spPower(localPv.corrected_power_w)):'uit',localPv.enabled?`${Math.round(Number(localPv.confidence||0)*100)}% · ${localPv.reason||''}`:'')}
      </div></details>
      <div class="kpis">
        ${this._tile('Zelfconsumptie vandaag',today.self_consumption_pct==null?'—':spPct(today.self_consumption_pct),'indicatieve toerekening')}
        ${this._tile('Op zon geregeld',`${Number(today.managed_solar_kwh||0).toLocaleString('nl-BE',{maximumFractionDigits:2})} kWh`,today.managed_kwh!=null?`van ${Number(today.managed_kwh||0).toLocaleString('nl-BE',{maximumFractionDigits:2})} kWh geregeld`:'' )}
        ${this._tile('Elektriciteitskost vandaag',spEuro(c.electricityToday?.net_cost_eur),'netafname min injectie · tot nu toe')}
      </div>
      ${this._savings(c)}
      ${ems.advice?.length?`<div class="advice"><strong>Advies</strong>${ems.advice.slice(0,4).map(x=>`<p>${spEscape(x)}</p>`).join('')}</div>`:''}
      ${ems.warnings?.length?this._notice(ems.warnings.map(x=>spEscape(x)).join('<br>'),true):''}
      ${forecast.enabled||planner.enabled?`<div class="inlinefacts"><span>Forecast: <b>${forecast.remaining_today_kwh==null?'—':Number(forecast.remaining_today_kwh).toLocaleString('nl-BE',{maximumFractionDigits:1})+' kWh resterend'}</b></span><span>Planner: <b>${planner.held_devices?.length?planner.held_devices.length+' start(s) uitgesteld':'geen start uitgesteld'}</b></span></div>`:''}
      <details class="decisions" data-ui-key="overview:decisions"><summary>Waarom doet SolarPilot dit?</summary>${(a.recent_decisions||[]).slice(0,10).map(x=>`<div class="log"><time>${spEscape(new Date(x.time).toLocaleTimeString('nl-BE',{hour:'2-digit',minute:'2-digit',second:'2-digit'}))}</time>${spEscape(x.message)}</div>`).join('')||'<p>Nog geen beslissingen geregistreerd.</p>'}</details>
    </section>`;
  }
  _wallboxExplanation(wb,activity,key=''){
    const observation=wb.activity_details||{},current=observation.current||{},last=observation.last_stop;
    const when=value=>{if(value==null||!Number.isFinite(Number(value))||Number(value)<=0)return 'tijdstip onbekend';try{return new Date(Number(value)*1000).toLocaleString('nl-BE',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit',timeZone:this._hass?.config?.time_zone||undefined});}catch{return 'tijdstip onbekend';}};
    const reason=!activity.known?'Een actuele, betrouwbare laadmeting ontbreekt; wachten of stoppen is niet bevestigd.':activity.active?'De auto laadt nu; er is geen actuele laadstop.':current.known?current.reason:'Nog geen actuele wachtreden ontvangen. De ingestelde laadmodus alleen verklaart niet waarom de auto wacht.';
    const stop=event=>event.stop_confirmed?`<p><b>Laadstop waargenomen: ${spEscape(when(event.observed_stop_at))}</b></p><p>Wallbox meldde toen: ${spEscape(event.stop_reason||'Exacte stopoorzaak niet gemeld.')}</p>${!event.cause_reported?'<p class="note">De laadstop is gezien, maar de exacte oorzaak is niet doorgegeven.</p>':''}`:`<p><b>Laadstop niet bevestigd</b> · metingen onderbroken op ${spEscape(when(event.unavailable_observed_at))}</p><p>${spEscape(event.stop_reason||'Het einde van de laadperiode is niet waargenomen.')}</p>`;
    const priority=wb.per_device_priority?wb.consumer_priority?.reason:wb.reason;
    return `<div class="start-explanation wb-wait"><strong>${activity.active?'Wat doet de Wallbox nu?':'Waarop wacht de Wallbox?'}</strong><p>${spEscape(reason)}</p>${activity.known&&current.known&&current.native_status?`<small>Door de Wallbox gemelde status: ${spEscape(current.native_status)}</small>`:''}<p><b>SolarPilot verdeelt de zonnestroom zo:</b> ${spEscape(priority||'Nog geen actuele verdelingsregel ontvangen.')}</p><small>Dit is de SolarPilot-regel voor andere toestellen, niet automatisch de oorzaak van een laadstop. De benodigde laadstroom en wachttijd staan hieronder bij Actuele verdeling.</small></div>
      <div class="start-explanation wb-stop"><strong>Laatste laadstop</strong>${last?stop(last):'<p>Nog geen laadstop waargenomen sinds deze registratie. Eerdere stops worden niet achteraf ingevuld.</p>'}<small>Het tijdstip is de waarneming in Home Assistant, niet het exacte fysieke stopmoment. Wie of wat de stop veroorzaakte is alleen bekend als de Wallbox dit meldt.</small></div>
      ${Array.isArray(observation.history)&&observation.history.length?`<details class="wb-stop-history"${key?` data-ui-key="${spEscape(key)}"`:''}><summary>Laadgeschiedenis · ${observation.history.length} bewaarde laadperioden</summary>${observation.history.map(event=>`<div class="start-explanation"><p>${event.start_confirmed?'Begin waargenomen':'Bij eerste controle al aan het laden'}: ${spEscape(when(event.observed_start_at))}</p>${stop(event)}</div>`).join('')}<p class="note">Maximaal 30 laadperioden bewaard. Een ontbrekende meting of herstart bewijst geen laadstop.</p></details>`:''}`;
  }
  _wallbox(c){
    const {wb}=c;if(!wb.enabled)return `<div class="empty">Wallbox-monitor is niet geconfigureerd.</div>`;
    const activity=this._wallboxActivity(wb);
    return `<section class="policy"><div class="row"><div class="grow"><h2>Auto laden in de gezamenlijke volgorde</h2><p>De volledige volgorde en de gevolgen voor autoladen staan op één plek.</p></div><button type="button" data-action="view" data-value="priorities">Naar Voorrang</button></div></section>
      <section class="external wallbox-device${activity.active?' on':''}"><div class="row"><div class="icon">EV</div><div class="grow"><h2>${spEscape(wb.name||'Wallbox')} <span class="runstate ${activity.active?'active':''}">${spEscape(activity.label)}</span> <span class="readonly">WALLBOX REGELT ZELF</span></h2><p>${spEscape((wb.per_device_priority?wb.consumer_priority?.reason:wb.reason)||'Extern geregeld')}</p></div><strong>${spPower(wb.power_w)}</strong></div><p class="note">SolarPilot leest het werkelijke laden; de Wallbox kiest zelf de laadstroom. Een ingestelde laadmodus is geen bewijs dat de auto nu laadt.</p>${this._wallboxExplanation(wb,activity)}${this._wallboxProfile(wb)}<div class="facts"><span>Ingestelde Wallbox-modus <b>${spEscape(spWallboxMode(wb.configured_mode||wb.reported_mode))}</b></span><span>Werkelijk gedetecteerde sessie <b>${spEscape(wb.session_value||(!wb.session_entity?'geen sessiesensor gekoppeld':spWallboxMode(wb.effective_mode)))}</b></span><span>Laadvermogen <b>${spPower(wb.power_w)}</b></span><span>Wallbox-vermogen terugnemen <b>${wb.reclaim_allowed_now?'ja, nu bevestigd':'nee, nu niet beschikbaar'}</b></span>${wb.last_report_age_s!=null?`<span>Rapport <b>${Math.round(Number(wb.last_report_age_s))} s oud</b></span>`:''}</div><p class="note wb-session">${spEscape(wb.reclaim_reason||wb.session_reason||'Alleen werkelijk vrij zonneoverschot wordt gebruikt.')}</p>${wb.warning?this._notice(spEscape(wb.warning),true):''}</section>`;
  }
  _startExplanation(d,mode,extra=[]){
    const diagnostics=d.start_diagnostics&&typeof d.start_diagnostics==='object'?d.start_diagnostics:null;
    const requirements=d.start_requirements&&typeof d.start_requirements==='object'?d.start_requirements:null;
    const reason=diagnostics?.summary||d.reason||'Nog geen actuele beslisreden ontvangen; de oorzaak is niet vastgesteld.';
    if(d.isolated)return `<div class="start-explanation"><strong>Toestel tijdelijk apart gehouden</strong><p>${spEscape(d.isolation_reason||reason)}</p><p>${d.available===false?'De actuele activiteit is onbekend.':'Het toestel meldt zijn activiteit; het vermogen of andere benodigde gegevens zijn niet betrouwbaar.'} SolarPilot bedient dit toestel tijdelijk niet en controleert de gegevens automatisch opnieuw. Zodra ze betrouwbaar zijn, kan het toestel opnieuw meedoen met behoud van minimale looptijd, rusttijd en overige voorwaarden.</p>${Number(d.isolation_reserve_w)>0?`<p>Veiligheidsreserve voor mogelijk verbruik: <b>${spPower(d.isolation_reserve_w)}</b>. Dit is geen gemeten verbruik.</p>`:''}</div>`;
    if(d.on&&d.available!==false)return `<div class="start-explanation"><strong>Waarom dit toestel nu actief is</strong><p>${spEscape(reason)}</p><p class="start-ready">${d.kind==='dishwasher'?'Een lopende afwasbeurt wordt niet opnieuw gestart en niet onderbroken om stroom vrij te maken.':'Startvoorwaarden gelden voor een volgende start, niet voor het toestel dat al draait.'}</p><small>De actuele beslisreden komt rechtstreeks uit de regelaar.</small></div>`;
    const wait=s=>s==null||s===''||!Number.isFinite(Number(s))?'nog niet bekend':Number(s)<60?`${Math.max(0,Math.ceil(Number(s)))} s`:spDuration(s);
    const explain=(key,value={})=>({
      global_solar_mode:'Automatisch regelen staat niet aan.',
      recovery_clear:'De herstartcontrole voor dit toestel is nog bezig.',
      automatic_participation:'Dit toestel staat op Uitgesloten.',
      reliable_energy_measurement:'Een betrouwbare actuele energiemeting ontbreekt.',
      availability_and_fault:!value.observed?'Nog geen actuele toestelstatus ontvangen.':value.fault?`Toestelfout: ${value.fault}`:'Toestel is niet beschikbaar.',
      release:'De externe vrijgave om te starten ontbreekt.',
      demand_or_time_window:d.kind==='dishwasher'&&d.dishwasher?.ticket_armed?`${d.dishwasher?.arming_mode==='app'?'APP-startvraag':'Startvraag'} ontvangen; wacht op bevestigde toestelstatus.`:value.time_window_enabled&&!value.time_window_active_now?`Buiten het toegestane tijdvenster ${String(value.time_window_start||'').slice(0,5)}–${String(value.time_window_end||'').slice(0,5)}.`:'Het toestel meldt nog geen startvraag.',
      minimum_rest:value.remaining_s==null?'Minimale rusttijd is nog niet bekend.':`Minimale rusttijd: nog ${wait(value.remaining_s)}.`,
      non_interruptible_cycle_release:'De beschermde cyclus is nog niet voor één volledige beurt vrijgegeven.',
      daily_maximum:`Dagmaximum bereikt${value.limit_s?` (${spDuration(value.used_s)} van ${spDuration(value.limit_s)})`:''}.`,
      planner_start_block:value.reason||'De planning houdt deze start nog tegen.',
      wallbox_start_block:value.reason||'Auto laden houdt deze start nog tegen.',
      runtime_start_block:value.reason||'Een hogere of beschermde regeling houdt deze start nog tegen.',
      general_increase_permission:value.reason||'Een veiligheidscontrole houdt nieuwe starts tegen.',
      allocated_start_power:`Na de reserves en hogere voorrangen is ${spPower(value.available_w)} beschikbaar voor dit toestel; de start vraagt ${spPower(value.required_w)}.`,
    }[key]||value.reason||'Een startvoorwaarde is nog niet gehaald.');
    let missing=[];
    if(requirements){
      const keys=Array.isArray(diagnostics?.missing)?diagnostics.missing:Object.keys(requirements).filter(key=>requirements[key]?.met===false);
      missing=keys.map(key=>explain(key,requirements[key])).filter(Boolean);
    }else{
      if(mode!=='solar')missing.push('Automatische regeling staat niet aan.');
      if(d.mode!=='auto')missing.push('Dit toestel staat op Uitgesloten.');
      if(!d.available)missing.push('Toestel is niet beschikbaar.');
    }
    const power=diagnostics?.power,stable=diagnostics?.stable_start;
    if(!d.on&&power&&power.measurement_valid===false&&(!requirements||!Object.prototype.hasOwnProperty.call(requirements,'reliable_energy_measurement')))missing.push('Een betrouwbare actuele energiemeting ontbreekt.');
    const pool=power?.solar_start_pool,required=Number(power?.required_start_w);
    const allocation=power?.allocation;
    const available=pool?Number(pool.available_solar_w):allocation?Number(allocation.available_w):Number(power?.measured_free_w);
    if(!d.on&&power?.measurement_valid&&Number.isFinite(required)&&Number.isFinite(available)&&required>available&&/vermogen|prioriteit/i.test(reason)&&!(d.kind==='dishwasher'&&!pool)){
      missing.push(`Nog ongeveer ${spPower(required-available)} ${pool?'zonnevermogen voor dit toestel':'vrije zonnestroom'} nodig.`);
    }
    if(pool?.import_headroom_after_release_w!=null&&Number(pool.import_headroom_after_release_w)<Number(power.minimum_w))missing.push(`De ingestelde netafnamegrens laat momenteel ${spPower(pool.import_headroom_after_release_w)} extra verbruik toe; dit toestel vraagt minstens ${spPower(power.minimum_w)}.`);
    for(const [label,value,state] of extra){if(state!=='ok')missing.push(`${label}: ${value}.`);}
    missing=[...new Set(missing)];
    const sharing=pool?`<span>Van autoladen beschikbaar <b>${spPower(pool.wallbox_solar_w)}</b></span>${Number(pool.lower_loads_releasable_w)>0?`<span>Van lagere toestellen vrij te maken <b>${spPower(pool.lower_loads_releasable_w)}</b></span>`:''}<span>Zonnevermogen voor dit toestel <b>${spPower(pool.available_solar_w)}</b></span>`:allocation?`<span>Beschikbaar voor dit toestel <b>${spPower(allocation.available_w)}</b></span>${Number(allocation.comfort_and_cycle_reserve_w)>0?`<span>Reserve voor comfort en lopende afwas <b>${spPower(allocation.comfort_and_cycle_reserve_w)}</b></span>`:''}`:'';
    const powerFacts=power?`<div class="start-facts"><span>Benodigd voor start <b>${spPower(power.required_start_w)}</b></span><span>Vrije zonnestroom na huisreserve <b>${power.measurement_valid?spPower(power.measured_free_w):'niet betrouwbaar'}</b></span>${sharing}<span>Stabiel nodig <b>${stable?.remaining_s!=null?(stable.remaining_s>0?'nog '+wait(stable.remaining_s):'gereed'):stable?.configured_s!=null?(Number(stable.configured_s)>0?wait(stable.configured_s)+' vereist':'geen wachttijd'):'nog niet bekend'}</b></span></div><p class="power-note">${pool?'Het vermogen voor dit toestel telt toegelaten zonnestroom uit autoladen mee, na reserves en begrensd door de echte zonneopbrengst. De Wallbox regelt zelf terug; dit is geen extra netcapaciteit. Lagere toestellen moeten eerst veilig stoppen. Wachttijden en elektrische grenzen blijven gelden.':d.kind==='dishwasher'?'Vrije zonnestroom is niet het totale startvermogen. Toegelaten vermogen uit autoladen kan ook meetellen, zodra de toestelstatus en de laadgegevens betrouwbaar zijn.':''}${power.note?` ${spEscape(power.note)}`:''}</p>`:'';
    const readyLabels={global_solar_mode:'Automatisch regelen staat aan.',recovery_clear:'Herstartcontrole afgerond.',automatic_participation:'Dit toestel mag automatisch meedoen.',reliable_energy_measurement:'Actuele energiemeting betrouwbaar.',availability_and_fault:'Toestel beschikbaar zonder gemelde fout.',release:'Vrijgavevoorwaarden zijn gehaald.',demand_or_time_window:'Startvraag of toegestaan tijdvenster aanwezig.',minimum_rest:'Minimale rusttijd afgerond.',non_interruptible_cycle_release:'Eén volledige beschermde cyclus vrijgegeven.',daily_maximum:'Dagmaximum laat deze start toe.',planner_start_block:'Planning houdt deze start niet tegen.',wallbox_start_block:'Autoladen houdt deze start niet tegen.',runtime_start_block:'Andere regelingen laten deze start toe.',general_increase_permission:'Veiligheidscontrole laat nieuwe starts toe.',allocated_start_power:'Voldoende vermogen aan dit toestel toegewezen.'};
    const ready=requirements?Object.entries(requirements).filter(([key,value])=>value?.met===true&&value.required!==false&&readyLabels[key]).map(([key])=>readyLabels[key]):[];
    const readyHtml=ready.length?`<div class="condition-group ready"><b>In orde</b><ul>${ready.map(text=>`<li>${spEscape(text)}</li>`).join('')}</ul></div>`:'';
    const missingHtml=missing.length?`<div class="start-missing"><b>Nog nodig</b><ul>${missing.map(text=>`<li>${spEscape(text)}</li>`).join('')}</ul></div>`:requirements?'<p class="start-ready">Geen ontbrekende startvoorwaarde gemeld; de beslisreden hierboven blijft leidend.</p>':'<p>De afzonderlijke startvoorwaarden zijn nog niet volledig ontvangen.</p>';
    return `<div class="start-explanation"><strong>${d.available===false?'Toestelactiviteit nog niet bevestigd':'Waarom dit toestel nog niet gestart is'}</strong><p>${spEscape(reason)}</p>${powerFacts}${missingHtml}${readyHtml}<small>De beslisreden komt rechtstreeks uit de regelaar. Een ontbrekende externe oorzaak wordt niet ingevuld.</small></div>`;
  }
  _deviceCard(d,mode){
    if(d.kind==='dishwasher')return this._dishwasherCard(d,mode);
    const activity=this._deviceActivity(d),physicalOn=activity.active, actuallyUsing=physicalOn&&Number(d.power_w||0)>10;
    const statusLabel=activity.label;
    const stateClass=physicalOn?` on ${d.manual_forced?'manual':d.owned?'owned':'external-on'}`:'';
    const manualButton=d.manual_forced
      ?`<button class="mini manual active" data-action="manual_stop" data-id="${spEscape(d.id)}" ${d.isolated||!d.available?'disabled':''}>Manueel stoppen</button>`
      :`<button class="mini manual" data-action="manual_start" data-id="${spEscape(d.id)}" ${mode!=='solar'||!d.available||d.isolated?'disabled':''}>Manueel starten</button>`;
    return `<div class="device${stateClass}"><div class="row"><div class="icon">${d.kind==='number'?'↗':d.non_interruptible?'◷':'⏻'}</div><div class="grow"><strong>${spEscape(d.name)} <span class="runstate ${physicalOn?'active':''}">${statusLabel}</span>${actuallyUsing&&!d.isolated?` <span class="using">VERBRUIKT</span>`:''}${d.phase?.classification&&d.phase.classification!=='unknown'?` <span class="phasepill">${spEscape(d.phase.classification)} ${Math.round(Number(d.phase.confidence||0)*100)}%</span>`:''}</strong>${d.boost_seconds>0?`<small>Boost nog ${Math.ceil(d.boost_seconds/60)} min</small>`:''}${d.manual_stop_requested?'<small>Manuele stop wacht op minimale looptijd</small>':''}</div><strong class="devicepower">${activity.known&&!d.isolated?`${d.estimated?'≈ ':''}${spPower(d.power_w)}`:'onbekend'}</strong></div>${this._startExplanation(d,mode)}
      ${d.reclaim_block?this._notice(`Overname geblokkeerd: ${spEscape(d.reclaim_block)}`,true):''}${d.planner_hold?this._notice(`<strong>Planner wacht</strong><br>${spEscape(d.planner_reason||'Wacht op gunstiger zonne-uur')}`):''}
      <div class="meta">${d.wallbox_first?'Auto laden eerst · ':d.wallbox_precedence==='consumer_first'?'Dit toestel vóór Auto laden · ':''}${d.time_window_enabled?`Tijdvenster ${spEscape(String(d.time_window_start||'').slice(0,5))}–${spEscape(String(d.time_window_end||'').slice(0,5))}`:'Geen tijdvenster'}${Number(d.min_daily_runtime_s)>0?` · vandaag ${spDuration(d.daily_runtime_s)} / min ${spDuration(d.min_daily_runtime_s)}`:''}${Number(d.effective_nominal_w)>Number(d.configured_nominal_w||0)+1?` · planningswaarde ${spPower(d.effective_nominal_w)}`:''}${d.cycle_learning&&Number(d.cycle_learning.energy_kwh||0)>0?` · cyclus ${Number(d.cycle_learning.energy_kwh).toLocaleString('nl-BE',{maximumFractionDigits:2})} kWh / ${Math.round(Number(d.cycle_learning.duration_min||0))} min (${Math.round(Number(d.cycle_learning.confidence||0)*100)}%)`:''}</div>
      ${d.wallbox_power_reason?`<details><summary>Vermogensverdeling met de Wallbox</summary><p class="note">${spEscape(d.wallbox_power_reason)}</p><p class="note">Alleen bij bevestigde autonome zonneregeling. Bij manueel laden telt uitsluitend echte injectie; elektrische grenzen en minimumlooptijden blijven gelden.</p></details>`:''}
      ${d.deadline_urgent?this._notice(`<strong>Dagminimum heeft nu voorrang</strong><br>${d.deadline_grid_allowed?'Netstroom mag binnen de ingestelde grenzen worden gebruikt.':'Alleen beschikbare zonnestroom; deadline heft netblokkering niet op.'}`,d.deadline_grid_allowed):''}
      <div class="controls"><button type="button" data-action="view" data-value="priorities">Voorrang bekijken</button><button class="mini ${d.mode==='auto'?'active':''}" data-action="participate" data-id="${spEscape(d.id)}">${d.mode==='auto'?'Auto':'Uitgesloten'}</button>${manualButton}<span class="spacer"></span>${d.boost_seconds>0?`<button class="mini" data-action="cancel" data-id="${spEscape(d.id)}">Boost stoppen</button>`:`<button class="mini" data-action="boost" data-id="${spEscape(d.id)}" ${mode!=='solar'||d.mode!=='auto'||!d.available||d.isolated?'disabled':''}>Boost 30 min</button>`}<button class="mini" data-action="history" data-id="${spEscape(d.id)}" aria-label="Apparaatgeschiedenis ${spEscape(d.name)}">Geschiedenis${d.history?.on_s!=null?` · ${spDuration(d.history.on_s)} vandaag`:""}</button><button class="mini" data-action="info" data-id="${spEscape(d.id)}">Info</button></div>
      ${(d.owned||!d.available)&&mode!=='solar'?`<button class="linkbtn" data-action="takeover" data-id="${spEscape(d.id)}">Handmatig overnemen — schakelt niet uit</button>`:''}</div>`;
  }
  _dishwasherGates(w){
    const gateLabels={connection:'Verbinding actueel',remote:'Start op afstand vrijgegeven',door:'Deur gesloten',program:'Programma gekozen',native_delay_zero:'Geen eigen uitgestelde start',alarm:'Geen technisch alarm',start_button:'AEG START beschikbaar'},gates=w.gates||{},link=w.connection_report;
    const checks=Object.entries(gateLabels).filter(([key])=>Object.prototype.hasOwnProperty.call(gates,key)&&!gates[key]).map(([key,label])=>[label,key==='connection'&&link?.age_s!=null&&Number(link.age_s)>Number(link.maximum_age_s)?`laatste terugmelding ${spDuration(Number(link.age_s))} oud; maximaal ${spDuration(link.maximum_age_s)}`:'niet gehaald','blocked']);
    if(w.app_request===false&&w.ticket_armed===false)checks.push(['Eén beurt vrijgegeven','nog niet','blocked']);
    return checks;
  }
  _dishwasherCard(d,mode){
    const w=d.dishwasher||{},p=w.last_measured_profile,activity=this._deviceActivity(d),active=activity.active,app=w.arming_mode==='app';
    const done=w.cycle_status==='completed'&&w.completion?.confirmed;
    const deadline=w.start_deadline?new Date(w.start_deadline).toLocaleString('nl-BE',{weekday:'short',day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}):'';
    const ended=done?new Date(w.completion.ended_at_local).toLocaleString('nl-BE',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}):'';
    const badge=done?'KLAAR':w.airdry?'AIRDRY — NADROGEN':!d.available?'ONBEKEND':active?(d.owned?'PROGRAMMA ACTIEF':'EXTERN PROGRAMMA'):(w.app_request||w.ticket_armed)?'KLAARGEZET':'NIET KLAARGEZET';
    const rows=p?.stages?Object.entries(p.stages).map(([name,x])=>`<tr><td>${spEscape(name)}</td><td>${x.seconds>0?spPower(x.kwh*3600000/x.seconds):'—'}</td><td>${spPower(x.peak_w)}</td><td>${spDuration(x.seconds)}</td></tr>`).join(''):'';
    const gateChecks=this._dishwasherGates(w);
    return `<div class="device dishwasher${active?' on owned':''}"><div class="row"><div class="icon">◷</div><div class="grow"><strong>${spEscape(d.name)} <span class="runstate ${active?'active':''}">${badge}</span></strong></div><b class="power">${d.available&&!d.isolated?`${d.estimated?'≈ ':''}${spPower(d.power_w)}`:'onbekend'}</b></div>
      <div class="facts"><span>Programma <b>${spEscape(w.program||'Onbekend')}</b></span><span>Fase <b>${spEscape(activity.phase||'Onbekend')}</b></span><span>Vermogen <b>${!d.available||d.isolated?'onbekend':d.estimated?'geschat, geen eigen meting':'gemeten'}</b></span></div>
      ${this._startExplanation({...d,reason:d.reason||w.gate_reason},mode,gateChecks)}
      ${app?`<p class="note app-plan">${spEscape(w.app_message||'Klaarzetten met Delay Start / APP op de machine')}${deadline?` · Uiterlijk starten: <b>${spEscape(deadline)}</b>`:''}</p>`:''}
      ${done?`<p class="note dw-completed"><b>Afwasmachine klaar · beëindigd op ${spEscape(ended)}</b> — niet automatisch als leeggemaakt gemarkeerd.</p>`:''}
      ${w.cycle_status==='end_unconfirmed'?'<p class="note">Einde niet bevestigd; uit of onbereikbaar is geen succesvol einde.</p>':''}
      ${w.priority_policy?.configured?`<div class="note dw-priority"><strong>Warmtepompcomfort eerst · daarna afwasmachine</strong><br>Afwasmachine vóór Wallbox, lagere flexibele lasten en extra SG-zonneboost volgens de bewaarde volgorde. Minimumlooptijden en gewone comfortregeling blijven behouden.<br>${spEscape(w.priority_policy.ev_solar_priority?'Ook op zonnevermogen dat Full Solar nu gebruikt; tijdelijke netafname mogelijk tijdens terugregelen.':'Geen voorrangsstart op huidig EV-vermogen: alleen echt restoverschot vóór de deadline.')}${w.priority_policy.conditional_ev_w>0?`<br>Voorwaardelijk zonnevermogen uit EV: ${spPower(w.priority_policy.conditional_ev_w)} — geen extra netcapaciteit.`:''}${w.priority_policy.unmetered_reserve_w>0?`<br>Zonder exclusieve afwasmeter: ${spPower(w.priority_policy.unmetered_reserve_w)} extra ruimte gereserveerd voor nog komende verwarmpieken; conservatieve schatting.`:''}${w.priority_policy.ev_start_block?`<br><b>${spEscape(w.priority_policy.ev_start_block)}</b>`:''}${w.priority_policy.wallbox_response?.reason?`<br>${spEscape(w.priority_policy.wallbox_response.reason)}`:''}</div>`:''}
      <p class="note">${spEscape(w.power_source||'Handmatige schatting')} · geen onderbreking van een lopend programma.</p>
      <div class="controls"><button type="button" data-action="view" data-value="priorities">Voorrang bekijken</button><button class="mini ${d.mode==='auto'?'active':''}" data-action="participate" data-id="${spEscape(d.id)}">${d.mode==='auto'?'Auto':'Uitgesloten'}</button>
      ${(w.app_request||w.ticket_armed)?`<button class="mini" data-action="dishwasher_cancel" data-id="${spEscape(d.id)}">Klaarzetten annuleren</button>`:app?'':`<button class="mini" data-action="dishwasher_arm" data-id="${spEscape(d.id)}" ${!w.ready||w.attempted||active||!d.available||d.isolated?'disabled':''}>Eén beurt klaarzetten</button>`}
      <button class="mini" data-action="history" data-id="${spEscape(d.id)}">Geschiedenis${d.history?.on_s!=null?` · ${spDuration(d.history.on_s)} vandaag`:''}</button><button class="mini" data-action="info" data-id="${spEscape(d.id)}">Info</button></div>
      ${mode!=='solar'&&w.ticket_armed?'<p class="note">Klaargezet, maar geen fysieke start zolang Automatisch regelen niet actief is.</p>':''}
      <details><summary>Vermogensprofiel · ${Number(w.profile_count||0)} volledig gemeten cycli</summary><p>${spEscape(w.profile_note||'Nog geen meting. Ontbrekende fasen zijn onbekend, niet 0 W.')}</p>${rows?`<p>Laatste complete cyclus ${spEscape(p.program)} · ${spKwh(p.energy_kwh)} · ${spDuration(p.duration_s)}</p><div style="overflow:auto"><table class="dw-profile-table" style="border-collapse:separate;border-spacing:10px 5px;text-align:left"><thead><tr><th>Fase</th><th>Gemiddeld</th><th>Piek</th><th>Duur</th></tr></thead><tbody>${rows}</tbody></table></div>`:''}<p class="note">Shelly uitsluitend als vermogensmeter. Een lage vermogensfase is geen voltooid programma. Nog onbekende fasen en schattingen worden niet als zeker of nul weergegeven.</p></details></div>`;
  }
  _loads(c){
    const {a,devices}=c,mode=a.mode||'observe';
    return `<section class="view"><div class="sectionhead"><h2>Toestellen</h2><button type="button" data-action="manage_devices">Toestellen beheren</button></div><p class="sub">Bij elk toestel zie je wat nodig is om te starten en waarom het nu wacht of draait. De gezamenlijke rangorde beheer je via Voorrang.</p>${this._wallbox(c)}${this._wallboxPriority(c)}${!devices.length?'<div class="empty">Nog geen bestuurbare toestellen toegevoegd.</div>':devices.map(d=>this._deviceCard(d,mode)).join('')}</section>`;
  }
  _climateModeLabel(mode){return ({auto:'Automatisch',off:'Uit',heat:'Verwarmen',cool:'Koelen',heat_cool:'Automatisch'})[mode]||mode||'Onbekend';}
  _panasonicProgramLabel(program){return ({heating:'Verwarmen',cooling:'Koelen',off:'Uit',auto:'Automatisch',dhw:'Warm water',unknown:'Warmtepompprogramma onbekend'})[String(program||'').toLowerCase()]||'Warmtepompprogramma onbekend';}
  _sgConfirmation(s){
    const desired=s.desired_on===true?'Aangevraagd':s.desired_on===false?'Niet aangevraagd':'Onbekend';
    const relay=s.relay_confirmed===true?(s.relay_on===true?'Actief':s.relay_on===false?'Open':'Onbekend'):'Nog niet bevestigd';
    const response=s.panasonic_confirmed===true?'Afzonderlijk bevestigd':'Niet afzonderlijk bevestigd';
    return this._reasonFacts([['SolarPilot-aanvraag',desired],['SG-contact',relay],['Panasonic-reactie',response]]);
  }
  _heatpumpPower(c){
    const p=c.panasonic||{},s=c.sgBoost||{};
    const value=p.power_w??s.power_w,kind=p.power_kind??s.power_kind,scope=p.power_scope??s.power_scope;
    const labels={total:'Totaal warmtepomp',heat_pump:'Totaal warmtepomp',supply_1:'Alleen voeding 1 · gedeeltelijke meting',supply1:'Alleen voeding 1 · gedeeltelijke meting',supply_2:'Alleen voeding 2 · gedeeltelijke meting',supply2:'Alleen voeding 2 · gedeeltelijke meting',heater:'Alleen elektrische ondersteuning',unknown:'Dekking onbekend',unconfirmed:'Dekking nog niet bevestigd'};
    const known=value!=null&&Number.isFinite(Number(value))&&Number(value)>=0&&['measured','estimated'].includes(kind);
    return this._knownPower(value,{known,estimated:kind==='estimated',label:p.power_label||labels[scope]||'Dekking onbekend'});
  }
  _sgDetails(c,scope='comfort'){
    const s=c.sgBoost||{},p=c.panasonic||{},zones=p.zones||c.smartClimate?.zones||[];
    const facts=[['Tanktemperatuur',spTemp(p.temperature_c??s.temperature_c)],['Gemeld tankdoel',spTemp(p.target_c??s.target_c)],['Startdrempel',spPower(s.start_threshold_w)],['Voorlopige vermogensraming',spPower(s.estimated_power_w)],['Resterende sessie',this._remainingTime(s.remaining_s)],['Rusttijd',this._remainingTime(s.rest_remaining_s)]];
    const blocks=Array.isArray(s.blocked_reasons)?s.blocked_reasons:[];
    return `${this._sgConfirmation(s)}${this._reasonFacts(facts)}${blocks.length?`<div class="condition-group waiting"><b>Nog nodig</b><ul>${blocks.map(x=>`<li>${spEscape(this._plainReason(typeof x==='string'?x:x.reason))}</li>`).join('')}</ul></div>`:''}<p class="note">${s.relay_on===true&&s.relay_confirmed===true&&s.panasonic_confirmed!==true?'SG-contact actief; Panasonic-reactie niet afzonderlijk bevestigd. ':''}Een normaal tankdoel in de app bewijst niet welk effectief SG-doel Panasonic gebruikt.</p><details data-ui-key="sg:${spEscape(scope)}:monitor"><summary>Panasonic en ruimtes · alleen uitlezen</summary><p>${spEscape(p.program_label||this._panasonicProgramLabel(p.program))}</p>${zones.map(z=>`<div class="zone"><span><b>${spEscape(z.name||'Ruimte')}</b><small>Gewenst ${spTemp(z.target??z.target_c)}</small></span><b>${spTemp(z.current??z.temperature_c)}</b><em>${spEscape(this._climateModeLabel(String(z.mode||'').toLowerCase()))}${z.action?` · ${spEscape(({heating:'verwarmt',cooling:'koelt',idle:'niet actief',off:'niet actief'})[z.action]||z.action)}`:''}</em></div>`).join('')||'<p>Geen betrouwbare ruimtemetingen beschikbaar.</p>'}<p class="note">Panasonic regelt comfort, verwarmen/koelen, elektrische ondersteuning en sterilisatie. SolarPilot schrijft geen tankdoel of kamerstand. Het gemeten verbruik kan na het vrijgeven van SG blijven doorlopen.</p></details>`;
  }
  _heatpump(c){
    const s=c.sgBoost||{},p=c.panasonic||{},active=s.relay_confirmed===true&&s.relay_on===true;
    const switchEntity=s.enabled_entity,ready=!!switchEntity&&!this._busy;
    const manual=s.manual_hold===true||s.state==='manual_hold';
    return `<section class="heatpump-sg${active?' sg-active':''}" style="border:1px solid ${active?'#03a9f4':'var(--divider-color)'};border-radius:16px;padding:16px"><div class="sectionhead"><div><h2>Warmtepomp — Panasonic-regeling</h2><p>Panasonic regelt zelfstandig. SolarPilot vraagt alleen extra zonneboost aan.</p></div><button type="button" role="switch" aria-checked="${s.enabled===true}" aria-label="Automatische zonneboost" class="toggle ${s.enabled===true?'active':''}" data-action="sg_boost_enabled" ${ready?'':'disabled'}>${s.enabled===true?'Aan':'Uit'}</button></div><p><b>${spEscape(this._plainReason(s.reason||'Automatische zonneboost is nog niet gekoppeld.'))}</b></p><div class="flowgrid three">${this._tile('Tanktemperatuur',spTemp(p.temperature_c??s.temperature_c),'Panasonic-meting')}${this._tile('SG-contact',s.relay_confirmed===true?(s.relay_on===true?'Actief':s.relay_on===false?'Open':'Onbekend'):'Nog niet bevestigd',s.desired_on===true?'SolarPilot vraagt boost aan':'Geen actuele boostaanvraag')}${this._heatpumpPower(c)}</div>${manual?`<p class="note">Handmatige bediening blijft behouden.</p><button type="button" class="mini" data-action="sg_boost_resume" ${!s.resume_entity||this._busy?'disabled':''}>Automatische zonneboost hervatten</button>`:''}<details data-ui-key="sg:comfort:details"><summary>Details en voorwaarden</summary>${this._sgDetails(c)}<button type="button" class="mini" data-action="configure" data-config-step="sg_boost">Zonneboost instellen</button></details></section>`;
  }
  _comfort(c){return `<section class="view">${this._heatpump(c)}</section>`;}
  _plannerSettingControl(item){
    const value=item.value,disabled=this._busy?'disabled':'';
    if(item.type==='boolean')return `<label class="setting-switch"><input type="checkbox" data-planner-setting="${spEscape(item.key)}" data-planner-type="boolean" ${value?'checked':''} ${disabled}><span>${value?'Aan':'Uit'}</span></label>`;
    return `<div class="settinginput"><input type="number" data-planner-setting="${spEscape(item.key)}" data-planner-type="number" min="${Number(item.min)}" max="${Number(item.max)}" step="${Number(item.step)}" value="${Number(value)}" ${disabled}><span>${spEscape(item.unit||'')}</span></div>`;
  }
  _planning(c){
    const p=c.planner||{}, timeline=p.timeline||[], devices=Object.values(p.devices||{}), settings=p.settings_catalog||[];
    const conf=Math.round(Number(p.confidence||0)*100), q=p.quality?.last_7d||{}, replay=p.replay||{}, qfind=p.quality?.findings||[];
    const qscore=q.quality_score==null?'—':`${Number(q.quality_score).toLocaleString('nl-BE',{maximumFractionDigits:0})}%`;
    const mae=v=>v==null?'—':spPower(v);
    return `<section class="view planning"><h2>Planning · komende ${Number(p.horizon_h||36)} uur</h2><p class="sub">Rolling horizon. SolarPilot voert alleen het huidige planblok uit en controleert eerst opnieuw de echte meters en beveiligingen.</p>
      <div class="summarygrid">
        ${this._tile('Basislastvertrouwen',`${conf}%`,`${Number(p.plan_runs||0)} planberekeningen, geen leerdagen`)}
        ${this._tile('Meetdekking planner',q.covered_hours==null?'—':`${Number(q.covered_hours).toLocaleString('nl-BE',{maximumFractionDigits:1})} uur`,`${Number(q.samples||0)} vergelijkingen · ${Number(q.days||0)} kalenderdagen`)}
        ${this._tile('PV-fout · hele dag',mae(q.pv_mae_w),'gemiddelde absolute fout; inclusief nacht')}
        ${this._tile('PV-fout · bij zon',mae(q.pv_daylight_mae_w),`${Number(q.pv_daylight_samples||0)} bruikbare vergelijkingen vanaf beta.30`)}
        ${this._tile('Basislastfout',mae(q.base_mae_w),'alleen bruikbare samples')}
        ${this._tile('Verwachte netafname',`${Number(p.predicted_import_kwh||0).toLocaleString('nl-BE',{maximumFractionDigits:2})} kWh`,'hele planhorizon')}
        ${this._tile('Verwachte injectie',`${Number(p.predicted_export_kwh||0).toLocaleString('nl-BE',{maximumFractionDigits:2})} kWh`,'na geplande flexlasten')}
        ${this._tile('Geschatte energiekost · planhorizon',spEuro(p.predicted_cost_eur),'komende 36 uur / ingestelde horizon · PV en injectie al verrekend')}
        ${this._tile('Planblok',`${Number(p.slot_min||15)} min`,`herplanning ${Number(p.settings?.replan_min||15)} min`)}
      </div>
      ${(p.warnings||[]).length?this._notice((p.warnings||[]).map(x=>spEscape(x)).join('<br>'),true):''}
      ${(p.findings||[]).length?`<div class="advice"><strong>Bevindingen</strong>${p.findings.map(x=>`<p>${spEscape(x)}</p>`).join('')}</div>`:''}
      <details class="planned-cost"><summary>Uitsplitsing verwachte energiekost · planhorizon</summary><div class="summarygrid">
        ${this._tile('Verwachte netafnamekost',spEuro(p.cost_breakdown?.import_cost_eur),'toekomstige afname × tarief per planblok')}
        ${this._tile('Verwachte injectievergoeding',spEuro(p.cost_breakdown?.export_revenue_eur),'al afgetrokken van de geschatte energiekost')}
        ${this._tile('Verwachte lokaal gebruikte zon',spKwh(p.predicted_self_use_kwh),p.cost_breakdown?.storage_advisory?'inclusief batterijadvies':'niet ingekocht van het net')}
      </div><p class="note">${spEscape(p.cost_breakdown?.note||'Nog geen plan beschikbaar.')}</p></details>
      ${this._todayCost(c)}
      <details open><summary>Dagdoelen & geplande apparaten</summary>${devices.length?devices.map(d=>`<div class="scenario"><span>${spEscape(d.name)}<small>nodig ${Number(d.required_kwh||0).toLocaleString('nl-BE',{maximumFractionDigits:2})} kWh${d.contiguous_cycle?` · beschermde cyclus ${spEscape(d.cycle_program||'standaard')} · ${Math.round(Number(d.cycle_duration_min||0))} min`:''}</small></span><b>${Number(d.planned_kwh||0).toLocaleString('nl-BE',{maximumFractionDigits:2})} kWh gepland</b></div><p class="note">${spEscape(d.reason||'')}${d.contiguous_cycle?` · cyclusprofiel ${Math.round(Number(d.cycle_confidence||0)*100)}% vertrouwen`:''}</p>`).join(''):'<div class="empty">Nog geen flexibele verbruiker met dagdoel, beschermde cyclus of planner-vrijgave.</div>'}</details>
      <details open><summary>Plannerkwaliteit · voorspelling versus werkelijkheid</summary><div class="summarygrid">${this._tile('Netfout',mae(q.net_mae_w),'werkelijk netresultaat versus plan')}${this._tile('Uitvoering klopt',q.execution_match_pct==null?'—':`${Number(q.execution_match_pct).toLocaleString('nl-BE',{maximumFractionDigits:0})}%`,'geplande run/stop versus echte toestand')}</div>${qfind.length?`<div class="advice">${qfind.map(x=>`<p>${spEscape(x)}</p>`).join('')}</div>`:'<p class="note">Nog onvoldoende data.</p>'}<p class="note">Geen losse totaalscore: beoordeel meetdekking, netfout, PV-fout en uitvoering afzonderlijk. Planberekeningen tellen nooit als extra leerdag.</p></details>
      <details><summary>What-if · recente plannerreplay</summary>${replay.ready?`<p class="note">${spEscape(replay.reason||'')}</p><div class="scenario-list">${(replay.scenarios||[]).map((r,i)=>`<div class="scenario"><span>${spEscape(r.label)}<small>${r.days||0} replaydagen · piek ${spPower(r.peak_w||0)}</small></span><b>€ ${Number(r.cost_eur||0).toLocaleString('nl-BE',{maximumFractionDigits:2})}</b>${i?`<small>Δ import ${Number(r.delta_import_kwh||0).toLocaleString('nl-BE',{maximumFractionDigits:2})} kWh · Δ kost € ${Number(r.delta_cost_eur||0).toLocaleString('nl-BE',{maximumFractionDigits:2})} · Δ piek ${spPower(r.delta_peak_w||0)}</small>`:''}</div>`).join('')}</div><p class="note"><strong>Belangrijk:</strong> dit herplant op werkelijk gemeten PV en basislast, maar simuleert niet exact ieder historisch apparaatgedrag. Gebruik het als richtinggevende vergelijking.</p>`:`<div class="empty">${spEscape(replay.reason||'Nog onvoldoende replaydata.')}</div>`}</details>
      <details><summary>Tijdlijn · eerste ${Math.min(timeline.length,48)} blokken</summary><div class="planlist">${timeline.slice(0,48).map(x=>`<div class="phaserow"><div><strong>${spEscape(new Date(x.start).toLocaleString('nl-BE',{weekday:'short',hour:'2-digit',minute:'2-digit'}))}</strong><small>PV ${spPower(x.pv_w)} · basis ${spPower(x.base_w)} · gepland ${spPower(x.planned_load_w)}${Number(x.battery_w||0)?` · batterij ${Number(x.battery_w)>0?'+':''}${spPower(x.battery_w)}`:''}</small></div><b>${Number(x.net_w)>=0?'net '+spPower(x.net_w):'injectie '+spPower(Math.abs(Number(x.net_w)))}</b><p>${(x.devices||[]).map(spEscape).join(' · ')||'geen flexlast gepland'}</p></div>`).join('')}</div></details>
      <details class="settings-shell"><summary><span><b>Plannerinstellingen</b><small>${settings.length} instellingen · wijzigbaar met advies</small></span><em>openen</em></summary><section class="settings-panel"><p class="sub">Elke wijziging toont eerst wat ze doet en welke gevolgen ze waarschijnlijk heeft. De replay hierboven helpt om enkele strategieverschillen op jouw recente meetdata te beoordelen.</p><div class="settinglist">${settings.map(item=>`<div class="settingrow"><div class="settingcopy"><strong>${spEscape(item.label)}</strong><p>${spEscape(item.description||'')}</p><div class="settingadvice"><b>Advies:</b> ${spEscape(item.recommendation||'')}</div>${item.type==='number'?`<small><b>Lager:</b> ${spEscape(item.lower_effect||'—')}<br><b>Hoger:</b> ${spEscape(item.higher_effect||'—')}</small>`:`<small><b>Aan:</b> ${spEscape(item.on_effect||'—')}<br><b>Uit:</b> ${spEscape(item.off_effect||'—')}</small>`}</div><div class="settingcontrol">${this._plannerSettingControl(item)}<button class="resetsetting" data-action="planner_reset" data-setting="${spEscape(item.key)}">↺</button><small>standaard: ${spEscape(item.default)}</small></div></div>`).join('')}</div></section></details>
      <details><summary>Hoe wordt gekozen?</summary><p class="note">De planner vergelijkt per tijdblok lokale PV, geleerd basisverbruik, prijzen, kwartierpiek en de deadline van elk toestel. Beschermde cycli worden als één aaneengesloten blok gepland. Veiligheidsregels, actuele P1/PV, minimumlooptijden, comfort en Panasonic-sterilisatie staan buiten de optimalisatie en kunnen het plan altijd overrulen.</p></details>
    </section>`;
  }
  _energy(c){
    const {cap,economy,forecast,planner,phase,localPv,phaseLearning,phaseAttribution,historicalPhase,learning,today}=c;
    return `<section class="view ems"><h2>Energie, net & voorspelling</h2><p class="sub">Actuele meters zijn leidend; forecast en leren verfijnen alleen de planning.</p><div class="summarygrid">
      ${this._tile('Kwartierpiek',cap.enabled?(cap.current_average_w==null?'—':spPower(cap.current_average_w)):'uit',cap.enabled?`vrije ruimte ${spPower(cap.optional_headroom_w)}`:'')}
      ${this._tile('Fasebewaking',phase.enabled?(phase.headroom_w==null?'—':`${spPower(phase.headroom_w)} vrij`):'uit',phase.reason||'')}
      ${this._tile('Zonnevoorspelling',forecast.enabled?(forecast.remaining_today_kwh==null?'—':`${Number(forecast.remaining_today_kwh).toLocaleString('nl-BE',{maximumFractionDigits:1})} kWh resterend`):'uit',forecast.tomorrow_kwh==null?'':`morgen ${Number(forecast.tomorrow_kwh).toLocaleString('nl-BE',{maximumFractionDigits:1})} kWh`)}
      ${this._tile('Lokale PV-correctie',localPv.enabled?(localPv.corrected_power_w==null?'—':spPower(localPv.corrected_power_w)):'uit',localPv.enabled?`${Math.round(Number(localPv.confidence||0)*100)}% · ${localPv.reason||''}`:'')}
      ${this._tile('Planner',planner.enabled?(planner.held_devices?.length?`${planner.held_devices.length} start(s) wachten`:'geen uitstel'):'uit',planner.early_grid_devices?.length?`netfallback: ${planner.early_grid_devices.join(', ')}`:'zonnestroom eerst')}
      ${this._tile('Waarde eigen zon',economy.enabled?`€ ${Number(economy.self_use_value_eur_kwh||0).toLocaleString('nl-BE',{maximumFractionDigits:3})}/kWh`:'—',economy.enabled?`afname €${Number(economy.import_eur_kwh||0).toLocaleString('nl-BE',{maximumFractionDigits:3})} · injectie €${Number(economy.export_eur_kwh||0).toLocaleString('nl-BE',{maximumFractionDigits:3})}`:'')}
    </div>
    ${phaseAttribution.enabled?`<details open><summary>Faseverdeling & herkende toestellen</summary><p class="note">P1-fasen zijn netto. Herkend toestelvermogen is bruto; batterijbijdrage is getekend. De restwaarde is geen exact onbekend verbruik.</p><div class="phaselist">${(phaseAttribution.phases||[]).map((x,idx)=>{const hist=historicalPhase.stats?.['L'+(idx+1)+' max W']||{};return `<div class="phaserow"><div><strong>${spEscape(x.name)}</strong><small>netto ${spPower(x.net_w)} · herkend ${spPower(x.known_device_w)}${Number(x.battery_net_w||0)?` · batterij ${(Number(x.battery_net_w)>=0?'+':'−')}${spPower(Math.abs(Number(x.battery_net_w)))}`:''}</small></div><b>rest ${spPower(x.residual_net_w)}</b><p>${(x.devices||[]).slice(0,5).map(d=>`${spEscape(d.name)} ${spPower(d.power_w)}`).join(' · ')||'Nog geen apparaten betrouwbaar herkend'}${hist.p95_import_w!=null?` · historisch P95 ${spPower(hist.p95_import_w)}`:''}</p></div>`}).join('')}</div></details>`:''}
    <details class="learning"><summary>Leren & modelkwaliteit</summary><div class="row"><div class="grow"><strong>Toestelvermogen en Wallbox-respons leren</strong><p>Deze schakelaar geldt alleen voor toestelvermogens en Wallbox-respons. Andere modellen hebben hun eigen instellingen; veiligheidsgrenzen worden nooit automatisch versoepeld.</p></div><button role="switch" class="toggle ${learning.enabled?'active':''}" data-action="learning" ${!learning.switch_entity?'disabled':''}>${learning.enabled?'Aan':'Uit'}</button></div><div class="facts"><span>Wallbox-overdrachten <b>${Number(learning.successes||0)}</b></span><span>Fase-events <b>${Number(phaseLearning.accepted_events||0)}</b></span><span>PV-model <b>${localPv.enabled?Math.round(Number(localPv.confidence||0)*100)+'%':'uit'}</b></span></div>${learning.reset_entity?'<button class="mini" data-action="reset_learning">Apparaat-, lokale PV-, fase- en activiteitsleerdata wissen</button>':''}</details>
    ${this._savings(c)}
    ${this._todayCost(c)}
    <div class="kpis">${this._tile('Site-import vandaag',`${Number(today.site_import_kwh||0).toLocaleString('nl-BE',{maximumFractionDigits:2})} kWh`)}${this._tile('Site-export vandaag',`${Number(today.site_export_kwh||0).toLocaleString('nl-BE',{maximumFractionDigits:2})} kWh`)}${this._tile('PV vandaag',`${Number(today.pv_kwh||0).toLocaleString('nl-BE',{maximumFractionDigits:2})} kWh`)}</div></section>`;
  }
  _storage(c){
    const {batteryFleet,batteryAnalysis}=c;
    return `<section class="view"><h2>Thuisbatterijen</h2><p class="sub">Analyse kan nu al. Fysieke aansturing blijft afzonderlijk en expliciet opt-in.</p>${batteryFleet.enabled?`<section class="battery"><div class="sectionhead"><div><h2>Batterijvloot</h2><p>${spEscape(batteryFleet.reason||'')}</p></div><span class="badge">${batteryFleet.control_enabled?'BEDIENING TOEGESTAAN':'READ-ONLY'}</span></div><div class="flowgrid three">${this._tile('Gemiddelde SoC',spPct(batteryFleet.aggregate?.soc_pct))}${this._tile('Vermogen',spPower(batteryFleet.aggregate?.power_w))}${this._tile('Capaciteit',batteryFleet.aggregate?.capacity_kwh==null?'—':`${Number(batteryFleet.aggregate.capacity_kwh).toLocaleString('nl-BE',{maximumFractionDigits:1})} kWh`)}</div>${(batteryFleet.batteries||[]).map(b=>`<div class="batteryrow"><span>${spEscape(b.name)}<small>${spEscape(b.phase_hint||'unknown')} · ${b.controllable?'bestuurbaar':'read-only'}</small></span><b>${spPct(b.soc_pct)} · ${spPower(b.power_w)}</b></div>`).join('')}${batteryFleet.faults&&Object.keys(batteryFleet.faults).length?this._notice(Object.values(batteryFleet.faults).map(x=>spEscape(x)).join('<br>'),true):''}</section>`:'<div class="empty">Nog geen echte thuisbatterij gekoppeld.</div>'}${batteryAnalysis.enabled?`<details open><summary>Batterijscenario’s · what-if</summary><p class="note"><b>${Number(batteryAnalysis.roundtrip_loss_pct??20).toLocaleString('nl-BE',{maximumFractionDigits:1})}% totaal round-trip verlies</b> · batterij/omvormerconversie. ${spEscape(batteryAnalysis.note||'')}</p>${(batteryAnalysis.scenarios||[]).filter(x=>Math.abs(Number(x.power_kw)-5)<.01).map(x=>`<div class="scenario"><span>${Number(x.capacity_kwh).toLocaleString('nl-BE')} kWh · ${Number(x.power_kw).toLocaleString('nl-BE')} kW</span><b>${Number(x.avoided_import_kwh||0).toLocaleString('nl-BE',{maximumFractionDigits:0})} kWh vermeden afname*</b></div>`).join('')}<p class="note">* Technische simulatie op historie + live data; geen jaarprognose of koopadvies.</p></details>`:''}</section>`;
  }
  _guide(c){
    const g=c.guide, removal=c.a.removal||{};
    if(!g.solar_pilot_guide)return `<section class="view"><div class="empty">Actuele uitleg wordt geladen. Herlaad de pagina als SolarPilot net is toegevoegd.</div></section>`;
    const removeBox=`<details open><summary>Installatie & volledig verwijderen</summary><p>SolarPilot is zelfvoorzienend: de frontend zit in dezelfde integratiemap. Voor verwijderen laat je SolarPilot eerst alle eigen regelingen veilig vrijgeven.</p><div class="notice ${removal.ready?'':'warn'}"><strong>${spEscape(removal.status||'Niet voorbereid')}</strong>${(removal.blockers||[]).length?`<br>${(removal.blockers||[]).map(x=>spEscape(x)).join('<br>')}`:'<br>SolarPilot bezit geen actieve regeling meer.'}</div>${c.a.prepare_remove_entity?`<button data-action="prepare_remove" ${this._busy?'disabled':''}>Verwijderen voorbereiden</button>`:''}<p class="note">Daarna: Instellingen → Apparaten & diensten → SolarPilot → Verwijderen. Bij handmatige installatie verwijder je tenslotte /config/custom_components/solar_pilot en herstart je Home Assistant. Gekoppelde apparaten worden niet verwijderd.</p></details>`;
    return `<section class="view guide"><div class="guidehero"><h2>${spEscape(g.title||'SolarPilot · Actuele werking')}</h2><p>${spEscape(g.intro||'')}</p><small>Versie ${spEscape(g.version||'')} · bijgewerkt ${spEscape(g.updated||'')}</small></div>${removeBox}${(g.sections||[]).map((s,i)=>`<details ${i===0?'open':''}><summary>${spEscape(s.title)}</summary>${(s.paragraphs||[]).map(p=>`<p>${spEscape(p)}</p>`).join('')}${(s.bullets||[]).length?`<ul>${s.bullets.map(b=>`<li>${spEscape(b)}</li>`).join('')}</ul>`:''}</details>`).join('')}</section>`;
  }
  _goExport(){this._uiHistory.view('export');}
  _openPriorities(){
    this._uiHistory.prepare();
    if(!this._priorityDialog){this._priorityDialog=document.createElement('solar-pilot-priority-dialog');this.shadowRoot.append(this._priorityDialog);this._priorityDialog.addEventListener('priority-saved',()=>{this._error='';});this._priorityDialog.addEventListener('priority-closed',()=>requestAnimationFrame(()=>this._content.querySelector('[data-action=priority_edit]')?.focus({preventScroll:true})));}
    this._priorityDialog.open(this._hass,this._last?.attributes?.config_entry_id);this._uiHistory.track(this._priorityDialog,()=>this._priorityDialog.open(this._hass,this._last?.attributes?.config_entry_id));
  }
  _priorities(c){
    const b=c.a.priority_board;
    if(!b)return `<section><h2>Voorrang</h2><p class="note">De centrale lijst is nog niet ontvangen. Controleer of integratie én kaart op dezelfde nieuwe versie staan.</p></section>`;
    const wallboxPosition=(b.rows||[]).find(r=>r.id==='wallbox')?.position??0,powerOutcome=r=>String(r?.power_label||'Niet vastgesteld').replace(/^Wallbox-vermogen:\s*/i,'');
    const fixed=(b.protected||[]).map(r=>`<div class="priority-row fixed"><div class="priority-number">Vast<small aria-hidden="true">🔒</small></div><div><b>${spEscape(r.name)}</b><small>${spEscape(r.active?'Actief':'Niet ingesteld of niet actief')}</small><p>Mag de auto minder laden? <strong>${spEscape(powerOutcome(r))}</strong></p><small>${spEscape(r.reason||'')}</small></div></div>`).join('');
    const rows=(b.rows||[]).map(r=>{const before=!!r.device_id&&Number(r.position)<Number(wallboxPosition);const relation=!r.device_id?powerOutcome(r):!r.wallbox_power?'Nee · alleen werkelijk vrij zonneoverschot':before?'Ja · toestel staat vóór Auto laden':'Nee · Auto laden staat hoger';const savedPermission=r.device_id&&r.wallbox_power&&!before?'<small>Toestemming is bewaard; wordt gebruikt als je dit toestel boven Auto laden zet.</small>':'';return `<div class="priority-row"><div class="priority-number">${r.position}</div><div><b>${spEscape(r.name)}</b><small>${spEscape(r.status||(r.active?'Ingesteld':'Niet actief'))}</small><p>Mag de auto minder laden? <strong>${spEscape(relation)}</strong></p>${savedPermission}${r.device_id?`<small>Nu uitvoerbaar: ${spEscape(powerOutcome(r))}</small>`:''}<small>${spEscape(r.reason||'')}</small></div></div>`}).join('');
    return `<section><div class="sectionhead"><div><h2>Voorrang en autoladen</h2><p>Van boven naar beneden staat wie als eerste energie krijgt.</p></div><button type="button" data-action="priority_edit" ${this._hass?.user?.is_admin===true?'':'disabled'}>Voorrang instellen</button></div><p class="note">${spEscape(b.note)}</p><div class="priority-stack" aria-label="Volledige voorrangslijst">${fixed}${rows}</div><p class="note">Bescherming en noodzakelijk comfort staan vast. Apparaten, Auto laden en extra warm water kun je binnen de veilige grenzen verplaatsen. Een nieuw toestel start nooit vanzelf.</p><button type="button" class="mini" data-action="manage_devices">Toestellen beheren</button></section>`;
  }
  _export(c){return `<section><div class="sectionhead"><div><h2>Export</h2><p>Eén lokaal onderzoeksbestand voor instellingen, metingen en beslissingen.</p></div></div><div class="export-grid"><div><strong>Instellingen & voorrang</strong><p>Actuele configuratie, centrale volgorde, toestemmingen en wachtende wijzigingen.</p></div><div><strong>Energie & zonneverwachting</strong><p>Beschikbare net-, zonne- en fasegegevens, prognose, lokale correctie en planningsgegevens.</p></div><div><strong>Werking & onderzoek</strong><p>Status, bewaarde meetpunten en gebeurtenissen, leergegevens, warm water, klimaat en afwas.</p></div></div><p class="note">Kies 1 uur, 24 uur of 7 dagen. Alleen werkelijk bewaarde gegevens worden meegenomen; ontbrekende geschiedenis wordt niet aangevuld. Namen en entiteiten worden standaard vervangen door pseudoniemen. Controleer het bestand voor je het deelt.</p><button type="button" data-action="analysis_export">Export samenstellen</button><p class="note">Exporteren wijzigt geen instellingen, schakelt geen toestel en verstuurt niets naar een externe dienst. Dit is een onderzoeksbestand, geen herstelbare Home Assistant-back-up.</p></section>`;}
  _viewHtml(c){return ({overview:()=>this._overview(c),loads:()=>this._loads(c),comfort:()=>this._comfort(c),planning:()=>this._planning(c),energy:()=>this._energy(c),storage:()=>this._storage(c),priorities:()=>this._priorities(c),export:()=>this._export(c),guide:()=>this._guide(c)}[this._view]||(()=>this._overview(c)))();}
  _render(){
    const uiState=this._captureUiState();
    const c=this._ctx(),a=c.a;
    this._content.innerHTML=`<style>
      .wallbox-device.on,.active-tile,.active-load{border-color:var(--primary-color,#287c59);box-shadow:inset 4px 0 0 var(--primary-color,#287c59);background:var(--secondary-background-color,#f3f5f7)}.wallbox-device.on .icon{background:var(--primary-color,#287c59);color:var(--text-primary-color,#fff)}.active-loads,.savings-summary{margin:15px 0;border:1px solid var(--divider-color,#dce1e7);border-radius:14px;padding:13px}.active-loads h2,.savings-summary h2{margin:0}.active-list{display:grid;gap:8px;margin-top:10px}.active-load{display:flex;align-items:center;gap:10px;padding:11px 12px;border:1px solid var(--primary-color,#287c59);border-radius:11px;min-width:0}.active-load strong{font-size:13px;overflow-wrap:anywhere}.active-load small{display:block;font-size:11px;color:var(--secondary-text-color,#697485);line-height:1.45;margin-top:4px}.active-power{flex:0 0 auto;text-align:right;font-size:14px}.active-power small{max-width:110px}.savings-summary p{font-size:12px;line-height:1.55}.savings-summary .tile strong{font-variant-numeric:tabular-nums}@media(max-width:420px){.active-load{align-items:flex-start;flex-wrap:wrap}.active-load>.grow{flex-basis:100%}.active-power{text-align:left}.active-power small{max-width:none}.active-loads .sectionhead{align-items:flex-start;flex-wrap:wrap}}
      .priority-stack{margin:12px 0;border:1px solid var(--divider-color,#dce1e7);border-radius:13px;overflow:hidden}.priority-stack .priority-row{grid-template-columns:42px minmax(0,1fr);padding:13px}.priority-stack .priority-row:first-child{border-top:0}.priority-stack .priority-row.fixed{background:var(--secondary-background-color,#f5f7f8)}.priority-stack .priority-number{text-align:center}.priority-stack .priority-number small{font-size:11px}.priority-stack .priority-row.fixed .priority-number{font-size:10px;line-height:1.4;text-transform:uppercase}
      .start-explanation{margin:10px 0;padding:11px 12px;border-radius:11px;background:var(--secondary-background-color,#f3f5f7);border-left:3px solid var(--primary-color,#287c59)}.start-explanation>strong{font-size:12px}.start-explanation>p{font-size:12px;line-height:1.5;margin:5px 0}.start-facts{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;margin:9px 0}.start-facts span{font-size:10px;line-height:1.4;padding:7px;border-radius:8px;background:var(--card-background-color,#fff)}.start-facts b{display:block;font-size:12px;margin-top:2px}.start-missing{font-size:11px;line-height:1.5;margin:8px 0}.start-missing ul{margin:4px 0 0;padding-left:18px}.start-ready{font-size:11px!important}.start-explanation>small{display:block;color:var(--secondary-text-color,#697485);font-size:10px;line-height:1.45}@media(max-width:420px){.start-facts{grid-template-columns:1fr}}
      .priority-row{display:grid;grid-template-columns:30px minmax(0,1fr);gap:10px;padding:13px 0;border-top:1px solid var(--divider-color,#dce1e7)}.priority-row b{font-size:14px}.priority-row p{font-size:12px;margin:5px 0;line-height:1.55}.priority-row small{display:block;font-size:11px;color:var(--secondary-text-color,#697485)}.priority-number{font-weight:750;font-size:18px}.priority-protected{padding:13px;border-radius:12px;background:var(--secondary-background-color,#f5f7f8);margin:12px 0}.priority-protected p{font-size:12px;line-height:1.5}.export-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin:14px 0}.export-grid>div{padding:14px;background:var(--secondary-background-color,#f5f7f8);border-radius:12px}.export-grid strong{font-size:13px}.export-grid p{font-size:12px;line-height:1.5}.option-question{border-radius:50%;width:28px;min-width:28px;min-height:28px;padding:0;margin:3px 5px;font-weight:800;vertical-align:middle}.comfort-new{padding:16px;border:1px solid var(--divider-color);border-radius:14px;margin:14px 0}.comfort-new h3{margin:0 0 10px}.charging-profile{margin:12px 0;font-size:13px;line-height:1.6}.charging-profile small{display:block;color:var(--secondary-text-color)}:host{display:block;color:var(--primary-text-color,#202735);font-family:var(--paper-font-body1_-_font-family,system-ui,sans-serif)}*{box-sizing:border-box}ha-card{display:block;border-radius:20px;overflow:hidden;background:var(--ha-card-background,var(--card-background-color,#fff));border:1px solid var(--divider-color,#e0e4e9);box-shadow:none}.head{padding:20px 20px 10px;display:flex;align-items:center;gap:12px}.logo{width:42px;height:42px;display:grid;place-items:center;border-radius:13px;background:var(--secondary-background-color,#f1f4f6);font-size:23px}.grow{flex:1;min-width:0}.head h1{font-size:22px;margin:0;letter-spacing:-.6px}.head p,h2+p,.sub{margin:4px 0 0;color:var(--secondary-text-color,#697485);font-size:12px;line-height:1.5}.tag{font-size:10px;font-weight:750;color:var(--secondary-text-color,#697485);text-align:right}.body{padding:0 20px 18px}.modes{display:flex;gap:6px;margin:8px 0 10px}.modes button{flex:1}.restart-policy{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:8px 0;font-size:11px}.restart-policy>span{min-width:0;line-height:1.4}.restart-policy small{display:block;margin-top:2px;font-size:10px;color:var(--secondary-text-color,#697485)}.restart-policy>button{flex:0 0 auto}.nav{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;padding:8px 0 13px}.nav button{white-space:normal;border-radius:999px;padding:8px 7px;min-height:38px;line-height:1.15}.nav button.active{background:var(--primary-color,#287c59);color:var(--text-primary-color,#fff);border-color:transparent}button,input{font:inherit;color:inherit}button{cursor:pointer;border:1px solid var(--divider-color,#dce1e7);background:var(--card-background-color,#fff);border-radius:10px;padding:8px 11px;font-size:12px;font-weight:650;min-height:39px}button:hover{background:var(--secondary-background-color,#f3f5f7)}button.active,.toggle.active{background:var(--primary-color,#287c59);color:var(--text-primary-color,#fff);border-color:transparent}button:disabled{opacity:.45;cursor:default}button:focus-visible,input:focus-visible,summary:focus-visible{outline:3px solid var(--primary-color,#287c59);outline-offset:2px}.view{}h2{font-size:15px;margin:16px 0 2px}.flowgrid,.summarygrid,.kpis{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin:10px 0}.flowgrid.three{grid-template-columns:repeat(3,minmax(0,1fr))}.tile{border:1px solid var(--divider-color,#e0e4e9);border-radius:13px;padding:11px;min-width:0}.tile span,.tile small{display:block;color:var(--secondary-text-color,#697485);font-size:10px;line-height:1.35}.tile strong{display:block;font-size:17px;line-height:1.2;margin:5px 0 3px;overflow-wrap:anywhere}.tile small{overflow-wrap:anywhere}.energy-tile{border-color:hsl(var(--energy-hue) 65% 45%);box-shadow:inset 4px 0 0 hsl(var(--energy-hue) 65% 45%);background:linear-gradient(110deg,hsl(var(--energy-hue) 70% 50% / .14),hsl(var(--energy-hue) 70% 50% / .025))}.energy-unknown{border-color:var(--divider-color,#e0e4e9);box-shadow:none;background:none}.energy-scale{height:6px;margin:12px 5px 3px;border-radius:6px;position:relative}.solar-scale{background:linear-gradient(90deg,#dc4545,#e98525,#e4c82f,#a2c92f,#369b47)}.grid-scale{background:linear-gradient(90deg,#369b47,#a2c92f,#e4c82f,#e98525,#dc4545)}.energy-scale i{position:absolute;top:-3px;width:5px;height:12px;border-radius:3px;transform:translateX(-50%);background:var(--primary-text-color,#202735);box-shadow:0 0 0 2px var(--card-background-color,#fff)}.energy-legend{font-size:10px;line-height:1.5;color:var(--secondary-text-color,#697485);margin:5px 0 14px}.notice{padding:11px 12px;margin:10px 0;border-radius:11px;background:var(--secondary-background-color,#f3f5f7);font-size:12px;line-height:1.5;border-left:3px solid var(--primary-color,#287c59)}.notice.warn{border-left-color:var(--warning-color,#bf810e)}.error{color:var(--error-color,#b3261e);font-size:12px;margin:8px 0}.advice{padding:12px;border-radius:13px;background:var(--secondary-background-color,#f3f5f7);margin:10px 0}.advice p{font-size:11px;margin:5px 0}.inlinefacts,.facts{display:flex;gap:8px 14px;flex-wrap:wrap;font-size:11px;color:var(--secondary-text-color,#697485);margin:10px 0}.inlinefacts b,.facts b{color:var(--primary-text-color,#202735)}.row,.sectionhead{display:flex;align-items:center;gap:10px}.sectionhead{justify-content:space-between}.sectionhead h2{margin-top:0}.sectionhead p{margin:3px 0}.policy,.external,.device,.dhw,.climate,.battery{border:1px solid var(--divider-color,#e0e4e9);border-radius:14px;padding:13px;margin:10px 0}.device.on{border-color:var(--primary-color,#287c59);box-shadow:inset 4px 0 0 var(--primary-color,#287c59);background:var(--secondary-background-color,#f3f5f7)}.device.on.manual{box-shadow:inset 4px 0 0 var(--warning-color,#bf810e)}.device.on .icon{background:var(--primary-color,#287c59);color:var(--text-primary-color,#fff)}.device.on.manual .icon{background:var(--warning-color,#bf810e)}.devicepower{font-variant-numeric:tabular-nums}.runstate,.using{display:inline-block;font-size:9px;font-weight:800;letter-spacing:.35px;padding:3px 6px;border-radius:999px;background:var(--secondary-background-color,#eef2f3);color:var(--secondary-text-color,#697485);vertical-align:middle}.runstate.active{background:var(--primary-color,#287c59);color:var(--text-primary-color,#fff)}.device.manual .runstate.active{background:var(--warning-color,#bf810e);color:#fff}.using{background:var(--primary-color,#287c59);color:#fff}.mobile-menu{display:none;align-items:center;justify-content:center;width:42px;height:42px;padding:0;font-size:22px;border-radius:12px;flex:0 0 auto}.policy{background:var(--secondary-background-color,#f7f8f9)}.toggle{border-radius:999px;white-space:nowrap}.external .icon,.device .icon{width:34px;height:34px;border-radius:10px;display:grid;place-items:center;background:var(--secondary-background-color,#eef2f3);font-size:12px;font-weight:750;flex:0 0 auto}.readonly,.badge,.phasepill{display:inline-block;font-size:9px;font-weight:800;letter-spacing:.35px;padding:3px 6px;border-radius:999px;background:var(--secondary-background-color,#eef2f3);color:var(--secondary-text-color,#697485);vertical-align:middle}.external h2{margin:0;font-size:14px}.external p,.device p{margin:3px 0;color:var(--secondary-text-color,#697485);font-size:11px;line-height:1.4}.meta,.note{font-size:10px;line-height:1.5;color:var(--secondary-text-color,#697485);margin:8px 0}.controls{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-top:9px}.controls label{font-size:10px;color:var(--secondary-text-color,#697485);display:flex;align-items:center;gap:5px}.controls input,.formgrid input{width:58px;min-height:36px;text-align:center;border:1px solid var(--divider-color,#dce1e7);border-radius:9px;background:var(--card-background-color,#fff)}.spacer{flex:1}.mini{min-height:34px;padding:6px 9px;font-size:10px}.linkbtn{border:0;background:none;text-decoration:underline;padding:5px 0;min-height:28px;color:var(--secondary-text-color,#697485)}.empty{padding:14px;border:1px dashed var(--divider-color,#dce1e7);border-radius:13px;color:var(--secondary-text-color,#697485);font-size:12px;margin:10px 0}.formgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:10px 0}.formgrid label{font-size:10px;color:var(--secondary-text-color,#697485)}.formgrid label span{display:flex;align-items:center;gap:4px;margin-top:4px;color:var(--primary-text-color,#202735)}.settings-panel{padding:0 12px 14px}.settings-shell{border:1px solid var(--divider-color,#e0e4e9);border-radius:16px;margin-top:14px;overflow:hidden;background:var(--card-background-color,#fff)}.settings-shell>summary{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:14px 16px;background:var(--secondary-background-color,#f3f5f7);cursor:pointer;border:0}.settings-shell>summary span{display:flex;flex-direction:column;gap:2px}.settings-shell>summary small{font-weight:500;color:var(--secondary-text-color,#697485)}.settings-shell>summary em{font-size:9px;font-style:normal;color:var(--secondary-text-color,#697485);text-transform:uppercase}.settinglist{display:grid;gap:8px;margin:10px 0}.settingrow{display:grid;grid-template-columns:minmax(0,1fr) minmax(150px,220px);gap:12px;padding:12px;border:1px solid var(--divider-color,#e0e4e9);border-radius:12px}.settingcopy p{font-size:11px;line-height:1.45;margin:4px 0;color:var(--secondary-text-color,#697485)}.settingcopy small{display:block;font-size:10px;line-height:1.5;color:var(--secondary-text-color,#697485);margin-top:6px}.settingadvice{font-size:10px;line-height:1.45;padding:7px 8px;border-radius:8px;background:var(--secondary-background-color,#f3f5f7);margin-top:7px}.settingcontrol{display:flex;flex-direction:column;gap:6px;align-items:stretch;justify-content:flex-start}.settingcontrol>small{font-size:9px;color:var(--secondary-text-color,#697485)}.settinginput{display:flex;align-items:center;gap:5px}.settinginput input{width:100%;min-width:80px;min-height:38px;border:1px solid var(--divider-color,#dce1e7);border-radius:9px;padding:5px;background:var(--card-background-color,#fff)}.settinginput span{font-size:10px;color:var(--secondary-text-color,#697485)}.setting-switch{display:flex;gap:8px;align-items:center;font-size:11px;min-height:38px}.setting-switch input{width:18px;height:18px}.entityselect{width:100%;min-height:38px;border:1px solid var(--divider-color,#dce1e7);border-radius:9px;padding:5px;background:var(--card-background-color,#fff);color:var(--primary-text-color,#202735);font-size:10px}.entityselect.multi{min-height:76px}.resetsetting{min-height:30px;padding:4px 7px}.zone>span{min-width:0;overflow-wrap:anywhere}.zone>em{max-width:40%;text-align:right;overflow-wrap:anywhere}details{border-top:1px solid var(--divider-color,#e0e4e9);padding:11px 0;margin-top:8px}summary{cursor:pointer;font-weight:700;font-size:12px}.log{font-size:10px;line-height:1.5;padding:6px 0;border-top:1px solid var(--divider-color,#e0e4e9)}.log time{color:var(--secondary-text-color,#697485);margin-right:5px}.phaserow,.batteryrow,.scenario,.zone{padding:9px 0;border-top:1px solid var(--divider-color,#e0e4e9);font-size:11px}.phaserow>div,.batteryrow,.scenario,.zone{display:flex;align-items:center;justify-content:space-between;gap:8px}.phaserow small,.batteryrow small,.zone small{display:block;color:var(--secondary-text-color,#697485);font-size:9px;margin-top:3px}.phaserow p{margin:5px 0 0;color:var(--secondary-text-color,#697485);font-size:10px}.zone em{font-size:10px;color:var(--secondary-text-color,#697485);font-style:normal}.guidehero{padding:14px;border-radius:13px;background:var(--secondary-background-color,#f5f7f8)}.guidehero h2{margin:0}.guidehero p,.guide details p,.guide li{font-size:12px;line-height:1.55}.guidehero small{font-size:10px;color:var(--secondary-text-color,#697485)}.guide ul{padding-left:18px}.footer{display:flex;justify-content:space-between;align-items:center;gap:10px;border-top:1px solid var(--divider-color,#e0e4e9);margin-top:15px;padding-top:12px}.footer span{font-size:9px;color:var(--secondary-text-color,#697485)}a{color:var(--primary-color,#287c59);font-size:11px;text-decoration:none}@media(max-width:699px){.mobile-menu{display:flex}.head{padding-left:12px}.body{padding-inline:14px}.controls{gap:5px}.controls .spacer{display:none}.device .controls{align-items:stretch}.device .controls button{flex:1 1 auto}}@media(max-width:560px){.settingrow{grid-template-columns:1fr}.settingcontrol{align-items:stretch}}@media(max-width:370px){.body{padding-inline:14px}.head{padding-inline:14px}.nav{grid-template-columns:repeat(2,minmax(0,1fr))}.flowgrid.three{grid-template-columns:1fr}.formgrid{grid-template-columns:1fr}.tag{display:none}}@media(min-width:700px){.nav{grid-template-columns:repeat(auto-fit,minmax(90px,1fr))}.summarygrid{grid-template-columns:repeat(3,minmax(0,1fr))}.kpis{grid-template-columns:repeat(3,minmax(0,1fr))}.flowgrid{grid-template-columns:repeat(4,minmax(0,1fr))}}
    </style><ha-card><div class="head"><button class="mobile-menu" data-action="ha_menu" aria-label="Home Assistant-menu openen" title="Menu">☰</button><div class="logo">☀</div><div class="grow"><h1>${spEscape(this._config?.title||'SolarPilot')}</h1><p>Slim zonne-energie verdelen zonder comfort te verliezen</p></div><div class="tag">${spEscape(a.integration_version||'versie onbekend')}<br>LOKAAL EMS</div></div><div class="body">${this._modeBar(a)}${this._globalAlerts(c)}${Number(a.learning_insights?.open_questions||0)>0?`<div class="advice"><strong>SolarPilot heeft ${Number(a.learning_insights.open_questions)} leervragen of bevindingen</strong><p>Nieuwe voorkeuren worden niet uit gewoontes afgeleid.</p><button type="button" data-action="learning_hub">Leren & vragen openen</button></div>`:''}${this._nav()}${this._view==='planning'?this._pvSummary(c):''}${this._viewHtml(c)}<div class="footer" style="flex-wrap:wrap" aria-label="Onderzoek en instellingen"><strong style="width:100%;font-size:12px">Instellingen & controle</strong><button type="button" class="linkbtn" data-action="manage_devices">Toestellen beheren</button><button type="button" class="linkbtn" data-action="pv_diagnostics">Zon · PV-diagnose</button><button type="button" class="linkbtn" data-action="learning_hub">Leren & vragen${Number(a.learning_insights?.open_questions||0)>0?` · ${Number(a.learning_insights.open_questions)}`:''}</button><button type="button" class="linkbtn" data-action="export_hub">Export</button><span>Geen elektrische beveiliging · actuele uitleg is release-gebonden</span><button type="button" class="linkbtn" data-action="configure">Instellingen & uitleg</button> <a href="/config/integrations/integration/solar_pilot">HA-instellingen ↗</a></div></div></ha-card>`;
    this._restoreUiState(uiState);
    this._installHelpButtons();
    this._lastRenderedView=this._view;
    this._renderSignature=this._viewRenderSignature();
  }
  async _loadOptionHelpers(){
    if(!customElements.get('solar-pilot-option-help-dialog')){
      if(!this._optionLoad)this._optionLoad=import('/solar_pilot_static/option-help.js?v=1.0.0-beta.62').catch(e=>{this._optionLoad=null;throw e;});
      await this._optionLoad;
    }
  }
  async _openHelp(step,key,title){
    this._uiHistory.prepare();
    try{await this._loadOptionHelpers();if(!this.isConnected)return;if(!this._helpDialog){this._helpDialog=document.createElement('solar-pilot-option-help-dialog');this.shadowRoot.append(this._helpDialog);}const opened=this._helpDialog.open(step,key,title);this._uiHistory.track(this._helpDialog,()=>this._helpDialog.open(step,key,title));await opened;}
    catch(e){this._error='Uitleg niet geladen: '+(e.message||String(e));this._render();}
  }
  async _openDevices(){
    this._uiHistory.prepare();
    try{await this._loadOptionHelpers();if(!this.isConnected)return;
      if(!this._deviceManager){this._deviceManager=document.createElement('solar-pilot-device-manager-dialog');this.shadowRoot.append(this._deviceManager);this._deviceManager.addEventListener('device-options',e=>this._openOptions(e.detail.step,e.detail.id,e.detail.section));this._deviceManager.addEventListener('device-history',e=>this._openHistory(e.detail));}
      this._deviceManager.open(this._hass,this._last?.attributes?.device_management);this._uiHistory.track(this._deviceManager,()=>this._deviceManager.open(this._hass,this._last?.attributes?.device_management));
    }catch(e){this._error=e.message||String(e);this._render();}
  }
  async _openOptions(step=null,deviceId=null,section=null){
    this._uiHistory.prepare();
    try{
      await this._loadOptionHelpers(); if(!this.isConnected)return;
      const entryId=this._last?.attributes?.config_entry_id;
      if(!entryId){this._error='Config entry ontbreekt; open de HA-instellingen.';this._render();return;}
      if(!this._optionsDialog){this._optionsDialog=document.createElement('solar-pilot-options-dialog');this._optionsDialog.uiHistory=this._uiHistory;this.shadowRoot.append(this._optionsDialog);}
      const hub=['sg_boost','panasonic_monitor','comfort'].includes(step)?'comfort_hub':'loads_hub';
      const route=step?[{next_step_id:hub},{next_step_id:step}]:[];
      if(deviceId)route.push({device_id:deviceId,...(section?{section}:{})});
      await this._optionsDialog._spClosingPromise;if(!this.isConnected)return;const opened=this._optionsDialog.open(this._hass,entryId,route);this._uiHistory.track(this._optionsDialog,()=>this._optionsDialog.open(this._hass,this._last?.attributes?.config_entry_id));await opened;
    }catch(e){this._error='Configuratie niet geladen: '+(e.message||String(e));this._render();}
  }
  _question(step,key,title){return `<button type="button" class="option-question" data-action="option_help" data-help-step="${spEscape(step)}" data-help-key="${spEscape(key)}" data-help-title="${spEscape(title||key)}" title="Uitleg bij ${spEscape(title||key)}" aria-label="Uitleg bij ${spEscape(title||key)}">?</button>`;}
  _installHelpButtons(){
    for(const el of this._content.querySelectorAll('[data-planner-setting],[data-priority]')){
      const step=el.dataset.plannerSetting?'planner':'device';
      const key=el.dataset.plannerSetting||'priority';
      const span=document.createElement('span');span.innerHTML=this._question(step,key,key);el.after(span.firstElementChild);
    }
    const actions={priority_edit:['dashboard','priority_board'],learning_hub:['dashboard','learning_hub'],analysis_export:['dashboard','analysis_export'],dishwasher_arm:['dashboard','dishwasher_arm'],dishwasher_cancel:['dashboard','dishwasher_cancel'],sg_boost_enabled:['sg_boost','enabled'],others_first:['dashboard','others_first'],participate:['dashboard','participation'],manual_start:['dashboard','manual_start'],manual_stop:['dashboard','manual_stop'],boost:['dashboard','boost']};
    for(const [action,[step,key]] of Object.entries(actions))for(const el of this._content.querySelectorAll(`[data-action="${action}"]`)){const span=document.createElement('span');span.innerHTML=this._question(step,key,el.textContent);el.after(span.firstElementChild);}
    for(const b of this._content.querySelectorAll('[data-action=option_help]')){
      const explain=async()=>{try{await this._loadOptionHelpers();const data=await customElements.get('solar-pilot-option-help-dialog').catalog();const row=data.entries[`${b.dataset.helpStep}.${b.dataset.helpKey}`];if(row){b.title=row.short;b.dataset.helpTitle=row.title;}}catch(_){}};
      b.addEventListener('pointerenter',explain,{once:true});b.addEventListener('focus',explain,{once:true});
    }
  }
  _wallboxProfile(wb){const p=wb.charging_profile;if(!p)return '';return `<div class="charging-profile"><strong>${Number(p.phases)} fase${p.phases===1?'':'n'} · max. ${Number(p.max_current_a).toLocaleString('nl-BE')} A · ≈ ${spPower(p.maximum_power_w)}</strong>${this._question('wallbox','profile_auto','Automatisch laadprofiel')}<small>Stroom: ${spEscape(p.current_source)} · Fasen: ${spEscape(p.phase_source)}</small>${p.warning?`<small>${spEscape(p.warning)}</small>`:''}<small>Panasonic-comfort blijft beschikbaar; extra SG-zonneboost gebruikt werkelijk restoverschot.</small></div>`;}
  async _perform(domain,service,data,successMessage=''){if(this._busy)return false;this._busy=true;this._error="";this._feedback="";this._render();try{await this._hass.callService(domain,service,data);this._feedback=successMessage;return true;}catch(err){this._error=err?.message||String(err);return false;}finally{this._busy=false;this._render();}}
  _device(id){return this._last?.attributes?.devices?.find(d=>d.id===id);}
  async _click(ev){
    const b=ev.target.closest("button[data-action]"); if(!b||b.disabled||this._busy)return;
    const c=this._ctx(),a=c.a,d=this._device(b.dataset.id),action=b.dataset.action;
    if(action==='learning_hub'){return this._openLearning();}
    if(action==='export_hub'){return this._goExport();}
    if(action==='priority_edit'){return this._openPriorities();}
    if(action==='analysis_export'){return this._openAnalysis();}
    if(action==='pv_diagnostics'){return this._openPV();}
    if(action==='configure'){return this._openOptions(b.dataset.configStep||null);}
    if(action==='manage_devices'){return this._openDevices();}
    if(action==='option_help'){ev.preventDefault();return this._openHelp(b.dataset.helpStep,b.dataset.helpKey,b.dataset.helpTitle);}
    if(action==='ha_menu'){this.dispatchEvent(new CustomEvent('hass-toggle-menu',{bubbles:true,composed:true}));return;}
    if(action==='view'){this._uiHistory.view(b.dataset.value||'overview');return;}
    if(action==='active_loads'){this._uiHistory.view('loads');return;}
    if(action==='mode'&&a.mode_entity){if(b.dataset.value==='solar'&&a.mode!=='solar'&&!window.confirm('Automatische toestelbediening activeren? Controleer eerst meter-richting, vermogen en beveiligingen.'))return;return this._perform('select','select_option',{entity_id:a.mode_entity,option:b.dataset.value});}
    if(action==='restart_auto'&&a.auto_resume_after_restart_entity)return this._perform('switch',a.auto_resume_after_restart===true?'turn_off':'turn_on',{entity_id:a.auto_resume_after_restart_entity});
    if(action==='reset'&&a.reset_entity)return this._perform('button','press',{entity_id:a.reset_entity});
    if(action==='prepare_remove'&&a.prepare_remove_entity){if(!window.confirm('SolarPilot veilig voorbereiden voor verwijderen? Nieuwe starts stoppen; eigen regelingen worden rustig vrijgegeven. Beschermde cycli worden niet hard afgebroken.'))return;return this._perform('button','press',{entity_id:a.prepare_remove_entity});}
    if(action==='others_first'&&c.wb.priority_switch)return this._perform('switch',c.wb.others_first?'turn_off':'turn_on',{entity_id:c.wb.priority_switch});
    if(action==='learning'&&c.learning.switch_entity)return this._perform('switch',c.learning.enabled?'turn_off':'turn_on',{entity_id:c.learning.switch_entity});
    if(action==='reset_learning'&&c.learning.reset_entity){if(!window.confirm('Wis apparaatvermogen/Wallbox-respons, lokale PV-profielen, faseprofielen en activiteitsmetingen? Het bewaarde klimaatarchief blijft behouden. Actieve bediening, handmatige bescherming en veiligheidsinstellingen blijven behouden.'))return;return this._perform('button','press',{entity_id:c.learning.reset_entity});}
    if(action==='sg_boost_enabled'){
      const s=c.sgBoost||{},entity=s.enabled_entity;
      if(!entity){this._error='De bediening voor zonneboost is niet beschikbaar.';this._render();return;}
      return this._perform('switch',s.enabled===true?'turn_off':'turn_on',{entity_id:entity});
    }
    if(action==='sg_boost_resume'){
      if(!c.sgBoost?.resume_entity){this._error='De bediening om zonneboost te hervatten is niet beschikbaar.';this._render();return;}
      return this._perform('button','press',{entity_id:c.sgBoost.resume_entity},'Zonneboost hervat zodra de actuele voorwaarden zijn gehaald.');
    }
    if(action==='planner_reset'){const item=(c.planner.settings_catalog||[]).find(x=>x.key===b.dataset.setting);if(!item)return;if(!window.confirm(`${item.label} terugzetten naar de aanbevolen standaard (${item.default})?`))return;return this._perform('solar_pilot','set_planner_setting',{config_entry_id:a.config_entry_id,setting:item.key,value:item.default});}
    if(!d)return;
    if(action==='dishwasher_arm'){if(!window.confirm(`${d.name}: één beurt automatisch laten starten?\n\nLaad de machine, kies het programma en activeer toegestane bediening op afstand. De deur moet gesloten zijn. Er volgt maximaal één START nadat de zonne- en planningsvoorwaarden kloppen. Een gestart programma loopt uit, ook wanneer later netstroom nodig is. Klaarzetten is geen controle op lekkage of een garantie op uitsluitend zon.`))return;return this._perform('button','press',{entity_id:d.dishwasher_arm_entity});}
    if(action==='dishwasher_cancel'){if(!window.confirm('Toekomstige starttoestemming intrekken? Een reeds gestart programma wordt NIET gestopt.'))return;return this._perform('button','press',{entity_id:d.dishwasher_cancel_entity});}
    if(action==='history'){this._openHistory(d);return;}
    if(action==='participate')return this._perform('select','select_option',{entity_id:d.mode_entity,option:d.mode==='auto'?'disabled':'auto'});
    if(action==='manual_start'){if(!window.confirm(`${d.name} manueel starten?\n\nSolarPilot mag hiervoor netstroom gebruiken binnen de ingestelde softwaregrenzen. Minimum rust-/looptijden, vrijgave en veiligheidsregels blijven gelden. Het toestel blijft manueel actief tot je het vrijgeeft of een veiligheidsregel ingrijpt.`))return;return this._perform('button','press',{entity_id:d.manual_start_entity});}
    if(action==='manual_stop'){if(!window.confirm(`${d.name}: manuele start stoppen/vrijgeven?\n\nAls de minimale looptijd nog niet voorbij is, wacht SolarPilot die eerst veilig af.`))return;return this._perform('button','press',{entity_id:d.manual_stop_entity});}
    if(action==='boost'){if(!window.confirm(`${d.name}: 30 minuten boost aanvragen? Dit kan netstroom gebruiken binnen de ingestelde grenzen.`))return;return this._perform('button','press',{entity_id:d.boost_entity});}
    if(action==='cancel')return this._perform('button','press',{entity_id:d.cancel_entity});
    if(action==='takeover'){if(!window.confirm(`${d.name}: zelf bediening overnemen? SolarPilot schakelt het toestel niet uit.`))return;return this._perform('button','press',{entity_id:d.takeover_entity});}
    if(action==='info'&&d.status_entity)this.dispatchEvent(new CustomEvent('hass-more-info',{detail:{entityId:d.status_entity},bubbles:true,composed:true}));
  }
  async _change(ev){
    const plannerKey=ev.target.dataset.plannerSetting;
    if(plannerKey){const c=this._ctx(),item=(c.planner.settings_catalog||[]).find(x=>x.key===plannerKey);if(!item)return;let value=item.type==='boolean'?!!ev.target.checked:Number(ev.target.value);if(item.type==='number'&&(!Number.isFinite(value)||!ev.target.checkValidity())){this._error='Controleer de plannerwaarde en het toegestane bereik.';this._render();return;}const old=item.value;const impact=item.type==='number'?`Lager: ${item.lower_effect||'—'}\nHoger: ${item.higher_effect||'—'}`:`Aan: ${item.on_effect||'—'}\nUit: ${item.off_effect||'—'}`;const msg=`${item.label}\n\n${item.description||''}\n\nAdvies: ${item.recommendation||''}\n\n${impact}\n\nNu: ${old}\nNieuw: ${value}\n\nWijziging toepassen?`;if(!window.confirm(msg)){this._render();return;}return this._perform('solar_pilot','set_planner_setting',{config_entry_id:c.a.config_entry_id,setting:plannerKey,value});}
    const id=ev.target.dataset.priority;if(!id)return;const d=this._device(id),value=Number(ev.target.value);if(!Number.isInteger(value)||value<1||value>100){this._error='Kies een geheel getal van 1 tot en met 100.';this._render();return;}if(d?.priority_entity)return this._perform('number','set_value',{entity_id:d.priority_entity,value});
  }
}

class SolarPilotGuideCard extends HTMLElement {
  constructor(){super();this.attachShadow({mode:"open"});this._state=null;} setConfig(config){this._config=config||{};this._entity=this._config.entity;}
  set hass(hass){this._hass=hass;if(!this._entity||!hass.states[this._entity])this._entity=this._config?.entity||Object.keys(hass.states).find(id=>hass.states[id]?.attributes?.solar_pilot_guide===true);const state=hass.states[this._entity];if(state===this._state)return;this._state=state;this._render();}
  getCardSize(){return 12;}getLayoutOptions(){return {grid_columns:12,grid_rows:12};}static getStubConfig(){return {};}
  _render(){const open=Array.from(this.shadowRoot.querySelectorAll("details"),d=>d.open),g=this._state?.attributes||{};this.shadowRoot.innerHTML=`<style>:host{display:block;font-family:var(--paper-font-body1_-_font-family,system-ui,sans-serif);color:var(--primary-text-color,#202735)}ha-card{padding:18px;border-radius:20px}h1{font-size:20px;margin:0 0 4px}.meta{font-size:11px;color:var(--secondary-text-color,#697485);margin-bottom:16px}.intro{font-size:13px;line-height:1.6;padding:12px;border-radius:12px;background:var(--secondary-background-color,#f5f7f8);margin-bottom:12px}details{border-top:1px solid var(--divider-color,#e0e4e9);padding:12px 0}summary{cursor:pointer;font-weight:700;font-size:14px}.body p,.body li{font-size:13px;line-height:1.6}.body ul{padding-left:20px}.empty{font-size:13px;color:var(--secondary-text-color,#697485)}</style><ha-card><h1>${spEscape(g.title||'SolarPilot · Actuele werking')}</h1>${g.solar_pilot_guide?`<div class="meta">Versie ${spEscape(g.version||'')} · bijgewerkt ${spEscape(g.updated||'')}</div><div class="intro">${spEscape(g.intro||'')}</div>${(g.sections||[]).map((s,i)=>`<details ${i===0?'open':''}><summary>${spEscape(s.title)}</summary><div class="body">${(s.paragraphs||[]).map(p=>`<p>${spEscape(p)}</p>`).join('')}${(s.bullets||[]).length?`<ul>${s.bullets.map(b=>`<li>${spEscape(b)}</li>`).join('')}</ul>`:''}</div></details>`).join('')}`:'<div class="empty">Voeg SolarPilot toe en controleer of sensor “Actuele uitleg” beschikbaar is.</div>'}</ha-card>`;Array.from(this.shadowRoot.querySelectorAll("details")).forEach((d,i)=>{if(i<open.length)d.open=!!open[i];});}
}
if(!customElements.get('solar-pilot-card'))customElements.define('solar-pilot-card',SolarPilotCard);
if(!customElements.get('solar-pilot-guide-card'))customElements.define('solar-pilot-guide-card',SolarPilotGuideCard);
window.customCards=window.customCards||[];
// A new release URL may evaluate in the same page. Update our catalog entries
// in place and remove only our duplicates, preserving other integrations.
for(const card of [
  {type:'solar-pilot-card',name:'SolarPilot · Control Center',description:'Geïntegreerd lokaal EMS met overzichtelijke tabbladen voor verbruikers, comfort, energie en opslag.',preview:true},
  {type:'solar-pilot-guide-card',name:'SolarPilot · Actuele uitleg',description:'Release-gebonden uitleg van alle huidige SolarPilot-regels.',preview:true}
]){
  const index=window.customCards.findIndex(entry=>entry?.type===card.type);
  if(index<0){window.customCards.push(card);continue;}
  window.customCards[index]=card;
  for(let i=window.customCards.length-1;i>index;i--)if(window.customCards[i]?.type===card.type)window.customCards.splice(i,1);
}
