/* SolarPilot 1.0.0-beta.101. Central priorities, start explanations and evidence-based reliability; no external dependencies. */
const SP_CARD_VERSION = '1.0.0-beta.101';
const SP_DIALOG_RELEASE = SP_CARD_VERSION.toLowerCase().replace(/[^a-z0-9]+/g,'-');
const SP_ANALYSIS_DIALOG_TAG = `solar-pilot-analysis-dialog-${SP_DIALOG_RELEASE}`;
const SP_QUALITY_DIALOG_TAG = `solar-pilot-learning-dialog-${SP_DIALOG_RELEASE}`;
const SP_HEATPUMP_HISTORY_TAG = `solar-pilot-heatpump-history-dialog-${SP_DIALOG_RELEASE}`;
const SP_WATER_HISTORY_TAG = `solar-pilot-water-history-dialog-${SP_DIALOG_RELEASE}`;
const SP_PV_DIALOG_TAG = `solar-pilot-pv-dialog-${SP_DIALOG_RELEASE}`;
const SP_CONSUMER_HISTORY_TAG = `solar-pilot-consumer-history-dialog-${SP_DIALOG_RELEASE}`;
const SP_SOURCE_HISTORY_TAG = `solar-pilot-source-history-dialog-${SP_DIALOG_RELEASE}`;
const SP_PRIORITY_DIALOG_TAG = `solar-pilot-priority-dialog-${SP_DIALOG_RELEASE}`;
const SP_WALLBOX_PRIORITY_DIALOG_TAG = `solar-pilot-wallbox-priority-dialog-${SP_DIALOG_RELEASE}`;
const SP_OPTION_HELP_TAG = `solar-pilot-option-help-dialog-${SP_DIALOG_RELEASE}`;
const SP_OPTIONS_DIALOG_TAG = `solar-pilot-options-dialog-${SP_DIALOG_RELEASE}`;
const SP_DEVICE_MANAGER_TAG = `solar-pilot-device-manager-dialog-${SP_DIALOG_RELEASE}`;
// Retain stable aliases on a fresh page; an old constructor is never this release.
const spDialogTag = (stable,bound) => customElements.get(stable)?.solarPilotRelease===SP_CARD_VERSION?stable:bound;
const spEscape = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
// Booleans, empty strings and missing values are not numeric measurements.
const spNumber = value => {
  if(typeof value!=='number'&&(typeof value!=='string'||!value.trim()))return null;
  const number=Number(value);return Number.isFinite(number)?number:null;
};
const spPower = value => {const n=spNumber(value);return n==null?"—":Math.abs(n)>=1000?`${(n/1000).toLocaleString("nl-BE",{maximumFractionDigits:2})} kW`:`${Math.round(n)} W`;};
const spTemp = value => {const n=spNumber(value);return n==null?"—":`${n.toLocaleString("nl-BE",{maximumFractionDigits:1})} °C`;};
const spTankHistoryValue=(value,binding)=>{
  if(spNumber(value)==null||!binding||!['display_tank','configured'].includes(binding.source)||!['tank_temperature_entity','tank_target_entity'].includes(binding.role)||typeof binding.entity!=='string'||!/^[a-z0-9_]+\.[a-z0-9_]+$/.test(binding.entity))return spTemp(value);
  const label=binding.role==='tank_temperature_entity'?'gemeten boilertemperatuur':'ingesteld boilerdoel';
  return `<button type="button" data-action="heatpump_source_history" data-history-role="${binding.role}" data-history-source="${binding.source}" data-history-entity="${spEscape(binding.entity)}" aria-label="Home Assistant-historie van ${label}" style="font:inherit;font-weight:inherit;color:inherit;background:transparent;border:0;padding:0;min-height:34px;text-decoration:underline;text-decoration-style:dotted;cursor:pointer">${spTemp(value)}</button>`;
};
const spDuration = value => { const n=spNumber(value);if(n==null)return '—';const s=Math.max(0,n),h=Math.floor(s/3600),m=Math.floor((s%3600)/60); return h?`${h}u${m?` ${m}m`:''}`:`${m}m`; };
const spEuro = value => {const n=spNumber(value);return n==null?"—":new Intl.NumberFormat("nl-BE",{style:"currency",currency:"EUR"}).format(n);};
const spKwh = value => {const n=spNumber(value);return n==null?"—":`${n.toLocaleString("nl-BE",{maximumFractionDigits:2})} kWh`;};
const spPct = value => {const n=spNumber(value);return n==null?"—":`${n.toLocaleString("nl-BE",{maximumFractionDigits:1})}%`;};
const spWaterNumber=value=>typeof value==='number'&&Number.isFinite(value)&&value>=0?value:null;
const spWaterLiters=value=>{const n=spWaterNumber(value);return n==null?'—':`${n.toLocaleString('nl-BE',{maximumFractionDigits:1})} L`;};
const spWaterFlow=value=>{const n=spWaterNumber(value);return n==null?'—':`${n.toLocaleString('nl-BE',{maximumFractionDigits:2})} L/min`;};
const spWaterReason=reason=>({current:'Bruikbaar bronrapport',not_configured:'Geen bron gekoppeld',missing:'Bron ontbreekt',unavailable:'Bron niet beschikbaar',stale:'Bronrapport verouderd',future_report:'Bronrapport ligt in de toekomst',restored_or_estimated:'Herstelde of geschatte waarde',report_time_unknown:'Oorspronkelijke rapporttijd ontbreekt',invalid_source_metadata:'Eenheid of sensortype past niet',invalid_value:'Ongeldige bronwaarde'})[reason]||'Bruikbaarheid van de bron is onbekend';
const spWaterReading=(reading,at,{unit=null,flag=false,current=false}={})=>{
  const time=n=>typeof n==='number'&&Number.isFinite(n)&&n>0;
  if(!reading||reading.fresh===false||!time(at)||!time(reading.reported_at)||reading.reported_at>at+5||!time(reading.valid_until)||reading.valid_until<at||reading.valid_until<reading.reported_at||current&&reading.fresh!==true||unit&&reading.unit!==unit)return null;
  return flag?(typeof reading.value==='boolean'?reading.value:null):spWaterNumber(reading.value);
};
const SP_WALLBOX_PRIORITY_OPTIONS = [['30m','30 min'],['1h','1 uur'],['2h','2 uur'],['3h','3 uur'],['4h','4 uur'],['5h','5 uur'],['until_auto','Tot ik terug uitschakel']];
const spWallboxPriorityCountdown=(choice,now)=>{
  if(choice?.active!==true)return 'Automatisch';
  if(choice.indefinite===true&&choice.option==='until_auto')return 'tot ik terug op automatisch zet';
  if(typeof choice.expires_at!=='number'||!Number.isFinite(choice.expires_at)||typeof now!=='number'||!Number.isFinite(now))return 'Eindtijd niet beschikbaar';
  const seconds=Math.max(0,Math.ceil(choice.expires_at-now));
  if(seconds===0)return 'Tijd verstreken · wacht op actuele status';
  const h=Math.floor(seconds/3600),m=Math.floor(seconds%3600/60),s=seconds%60;
  return `Nog ${h?`${h}:${String(m).padStart(2,'0')}`:m}:${String(s).padStart(2,'0')}`;
};
// A calculated preview is separate from the ordinary reported tank goal.
// Archived previews are assessed at their capture time, never rebuilt today.
const spCalculatedTankGoal=(value,{now=Date.now()/1000,stale=120}={})=>{
  const number=v=>typeof v==='number'&&Number.isFinite(v),stamp=v=>number(v)&&v>0&&v<=now+5;
  if(!value||value.read_only!==true||value.source!=='local_confirmed_profile'||!number(now)||!number(stale)||stale<=0||
    !number(value.normal_target_c)||value.normal_target_c<0||value.normal_target_c>100||!number(value.calculated_c)||value.calculated_c<0||value.calculated_c>100||
    !number(value.profile_percent)||value.profile_percent<100||value.profile_percent>200||!stamp(value.profile_confirmed_at)||!stamp(value.normal_target_reported_at)||
    now-value.normal_target_reported_at>stale||!number(value.valid_until)||value.valid_until<=now)return null;
  return {value:value.calculated_c,normal:value.normal_target_c,percent:value.profile_percent,normalStamp:value.normal_target_reported_at,confirmedAt:value.profile_confirmed_at};
};
const spWallboxMode = value => {
  const raw=String(value??'').trim(),key=raw.toLocaleLowerCase('nl-BE').replace(/[\s-]+/g,'_');
  return ({stopped:'Gestopt',solar:'Zonneladen',full_solar:'Volledig zonneladen',manual:'Handmatig laden',unknown:'Onbekend'})[key]||raw||'Onbekend';
};

const spProofClock=(value,timeZone)=>{const n=spNumber(value);if(n==null||n<=0)return '—';try{return new Date(n*1000).toLocaleString('nl-BE',{...(timeZone?{timeZone}:{}),hour12:false});}catch{return '—';}};
const spTransportProof=value=>{
  if(!value||typeof value!=='object')return 'Onbekend';
  const operations={read:'Lezen',on:'AAN',renew:'Toestemming vernieuwen',off:'UIT'},phases={pending:'In behandeling',confirmed:'Bevestigd',failed:'Niet bevestigd',send_uncertain:'Verzending onzeker',not_sent:'Niet verzonden',accepted_readback_unconfirmed:'Geaccepteerd, terugmelding niet bevestigd'},categories={none:'geen afwijking',timeout:'time-out',cancelled:'onderbroken',write_uncertain:'verzending onzeker',unavailable:'niet bereikbaar',invalid_response:'ongeldig antwoord',contact_unconfirmed:'contact niet bevestigd',lease_unconfirmed:'lokale toestemming niet bevestigd',mapping_or_setup_changed:'koppeling gewijzigd',policy_changed:'beleid gewijzigd',unknown:'oorzaak onbekend'};
  return `${operations[value.operation]||'Onbekende stap'} · ${phases[value.phase]||'onbekende uitkomst'} · ${categories[value.category]||'oorzaak onbekend'}`;
};
const spInvestigationProofRows=(item,timeZone)=>{
  const metrics=item.metrics&&typeof item.metrics==='object'?item.metrics:{},parts=[];
  const dossier=metrics.source_dossier;
  if(dossier?.schema===1&&dossier.read_only===true){
    const roles={session:'Gekoppelde sessie',status:'Native status',mode:'Native modus',power:'Native vermogen'},sources=[dossier.session,...(Array.isArray(dossier.known_sources)?dossier.known_sources.slice(0,3):[])].filter(r=>r&&typeof r==='object');
    parts.push(`<h4>Oorspronkelijke Wallbox-rapporten</h4><dl class="investigation-metrics" data-source-dossier>${sources.map(r=>`<div><dt>${spEscape(roles[r.role]||'Vergelijkingsbron')}</dt><dd>${spEscape(r.role==='power'?spPower(r.watts):typeof r.value==='string'?r.value.slice(0,120):'Onbekend')} · ${spEscape(spProofClock(r.reported_wall,timeZone))} · ${r.fresh===true?'actueel':'verouderd / ontbreekt'}${r.platform==='template'?' · template':''}</dd></div>`).join('')}</dl>${dossier.dependency_relation==='verified_state_template_dependencies'?`<h4>Afhankelijkheden van de laatste geslaagde templateverwerking</h4><dl class="investigation-metrics" data-template-dependencies>${(Array.isArray(dossier.dependencies)?dossier.dependencies:[]).slice(0,16).map((r,i)=>`<div><dt>Afhankelijkheid ${i+1}${Array.isArray(r?.matches_configured_roles)&&r.matches_configured_roles.length?' · '+spEscape(r.matches_configured_roles.filter(role=>Object.hasOwn(roles,role)).map(role=>roles[role]).join(', ')):''}</dt><dd>${spEscape(spProofClock(r?.reported_wall,timeZone))} · ${r?.fresh===true?'actueel':'verouderd / ontbreekt'}</dd></div>`).join('')}</dl><p>${dossier.dependency_coverage==='partial'?'De bronlijst is begrensd of gebruikt brede luistervoorwaarden.':'Dit bewijst uitsluitend de afhankelijkheden van de laatste geslaagde verwerking.'} De templateformule blijft lokaal; toekomstige afhankelijkheden en triggers zijn hiermee niet volledig bewezen.</p>`:'<p>Dit zijn gekoppelde vergelijkingsbronnen. Templateformule, triggers en afhankelijkheidsrelatie zijn onbekend.</p>'}<p>Een nieuw rapport van een andere bron vernieuwt de sessie niet.</p>`);
  }
  const proof=metrics.proof;
  if(item.id==='solar_balance'&&proof&&typeof proof==='object'){
    parts.push(`<h4>Tijdsafstemming zonnebalans</h4><dl class="investigation-metrics" data-solar-balance-proof><div><dt>Net / PV</dt><dd>${spPower(proof.grid_w)} / ${spPower(proof.pv_w)}</dd></div><div><dt>Verschil oorspronkelijke rapporttijden</dt><dd>${spNumber(proof.source_skew_s)==null?'Onbekend':spEscape(String(proof.source_skew_s)+' s')} · ${proof.time_aligned===true?'passend':proof.time_aligned===false?'niet passend':'onbekend'}</dd></div>${(Array.isArray(proof.source_reports)?proof.source_reports:[]).slice(0,3).map(r=>`<div><dt>${r?.role==='grid'?'Netrapport':r?.role==='pv'?'PV-rapport':r?.role==='grid_export'?'Injectierapport':'Bronrapport'}</dt><dd>${spEscape(spProofClock(r?.reported_wall,timeZone))}</dd></div>`).join('')}</dl><p>Volledige dekking van productie en opslag is onbekend. Een afwijking geeft een uitleesbaar controlespoor en verandert geen tekenrichting of regelvrijgave.</p>`);
  }
  if(item.id==='sg_policy'&&Array.isArray(metrics.recent_sessions)){
    const interruptions={restart:'herstart',shutdown:'afsluiten',source_loss:'bronverlies',source_gap:'meetgat',invalid_time:'ongeldig tijdstip',binding_changed:'gewijzigde bronkoppeling'};
    parts.push(`<h4>SG-onderzoeksperioden</h4><div data-sg-research-records>${metrics.recent_sessions.slice(-12).reverse().filter(r=>r&&typeof r==='object').map(r=>`<article class="investigation-item"><strong>${spEscape(spProofClock(r.started_at,timeZone))} → ${r.interrupted===true?'einde onbekend':spEscape(spProofClock(r.ended_at,timeZone))}</strong><p>${r.interrupted===true?'Onderbroken door '+(interruptions[r.interruption]||'onbekende onderbreking')+'; niet vergelijkbaar.':r.comparable===true?'Vergelijkbare meetdekking.':'Meetdekking of beleidsvergelijking onvolledig.'} Laatst waargenomen: ${spEscape(spProofClock(r.last_observed_at,timeZone))}.</p><dl class="investigation-metrics"><div><dt>Stopbesluit regelaar</dt><dd>${r.controller_stop?spEscape(spProofClock(r.controller_stop.ended_at,timeZone)+' · '+String(r.controller_stop.reason||'Reden onbekend').slice(0,240)):'Onbekend'}</dd></div><div><dt>Gemeld SG-contact</dt><dd>${r.contact_end?.state===true?'Gesloten':r.contact_end?.state===false?'Open':'Onbekend'} · ${spEscape(spProofClock(r.contact_end?.reported_at,timeZone))}</dd></div><div><dt>Transportstap</dt><dd>${spEscape(spTransportProof(r.transport))}</dd></div></dl></article>`).join('')}</div>`);
  }
  return parts.join('');
};
const spInvestigationProof=(item,timeZone)=>{
  const metrics=item?.metrics||{},assessmentMetrics={source_dossier:metrics.assessment_source_dossier,proof:metrics.assessment_proof};
  const assessment=spInvestigationProofRows({...item,metrics:assessmentMetrics},timeZone),current=spInvestigationProofRows(item,timeZone);
  if(!assessment)return current;
  const summary=typeof item.assessment_summary==='string'?item.assessment_summary.slice(0,1200):'',evidence=Array.isArray(item.assessment_evidence)?item.assessment_evidence.slice(0,6).filter(v=>typeof v==='string'):[];
  return `<section data-proof-era="assessment"><h4>Meetbasis beoordeling · ${spEscape(spProofClock(item.assessment_observed_at,timeZone))}</h4>${summary?`<p>${spEscape(summary)}</p>`:''}${evidence.length?`<ul>${evidence.map(v=>`<li>${spEscape(v.slice(0,800))}</li>`).join('')}</ul>`:''}${assessment}</section>${current?`<section data-proof-era="current"><h4>Actuele broncontrole · ${spEscape(spProofClock(item.current_observed_at,timeZone))}</h4>${current}</section>`:''}`;
};

/* Local, descriptive research only. Neither uploaded text nor these statuses
   grants control authority. Keep this renderer bounded even for malformed data. */
const spInvestigationHtml = (data,{current=true,timeZone}={}) => {
  const text=(value,limit=800)=>typeof value==='string'?value.slice(0,limit):'';
  const valid=!!data&&data.schema===1&&data.read_only===true&&Array.isArray(data.items);
  const stamp=valid&&typeof data.updated_at==='number'&&Number.isFinite(data.updated_at)&&data.updated_at>0&&Number.isFinite(new Date(data.updated_at*1000).getTime())?data.updated_at:null;
  const age=stamp==null?null:Date.now()/1000-stamp;
  const fresh=valid&&current===true&&age!=null&&age>=-5&&age<=180;
  const state=!valid||stamp==null?'unavailable':fresh?'current':'stale';
  let checked='nog niet beschikbaar';
  if(stamp!=null){try{checked=new Date(stamp*1000).toLocaleString('nl-BE',{...(timeZone?{timeZone}:{}),hour12:false});}catch{checked='tijdstip niet beschikbaar';}}
  const list=(values,limit=6)=>Array.isArray(values)?values.slice(0,limit).filter(value=>typeof value==='string'&&value.slice(0,800).trim()).map(value=>`<li>${spEscape(text(value))}</li>`).join(''):'';
  const statuses={collecting:'Meer meetgegevens nodig',check_needed:'Controle nodig',not_configured:'Bron of functie niet ingesteld',observed_ok:'Geen afwijking in deze metingen'};
  const proposalKinds={logic_update:'Softwarevoorstel',software_proposal:'Softwarevoorstel',setting:'Instellingsvoorstel',inspection:'Controlevoorstel',measurement_check:'Meetcontrole',data_review:'Gegevens beoordelen'};
  const items=valid?data.items.slice(0,8).filter(item=>item&&typeof item==='object'&&!Array.isArray(item)):[];
  return `<section class="automatic-investigation" data-investigation-current="${state}" aria-label="Automatisch onderzoek"><h3>Automatisch onderzoek</h3><p class="note">Laatste lokale beoordeling: ${spEscape(checked)}${state==='stale'?' · verouderd':state==='unavailable'?' · nog onbekend':''}.</p>${!fresh?`<p class="notice warn">${state==='stale'?'De huidige beoordeling is verlopen. Hieronder staan eerdere bevindingen; ze bevestigen de actuele toestand niet.':'De lokale onderzoeksgegevens zijn nog niet beschikbaar.'}</p>`:''}<p class="note">${spEscape(text(valid?data.notice:'',1200)||'SolarPilot onderzoekt gekoppelde metingen lokaal. Voorstellen veranderen geen instellingen of toestellen en voeren geen software-update uit.')}</p>${items.map((item,index)=>{
    const id=typeof item.id==='string'&&/^[a-z0-9][a-z0-9_.:-]{0,63}$/.test(item.id)?item.id:`item-${index}`;
    const status=typeof item.status==='string'&&Object.hasOwn(statuses,item.status)?item.status:'unknown';
    const evidence=list(item.evidence),hypotheses=list(item.hypotheses,4),proof=spInvestigationProof(item,timeZone);
    const proposals=Array.isArray(item.proposals)?item.proposals.slice(0,4).filter(value=>value&&typeof value==='object'&&typeof value.text==='string'&&value.text.slice(0,1200).trim()):[];
    const metrics=item.metrics&&typeof item.metrics==='object'&&!Array.isArray(item.metrics)?Object.entries(item.metrics).filter(([,value])=>typeof value==='string'||typeof value==='number'&&Number.isFinite(value)||typeof value==='boolean').slice(0,8):[];
    return `<article class="investigation-item" data-investigation-id="${spEscape(id)}"><div class="investigation-head"><strong>${spEscape(text(item.title,180)||'Lokale bevinding')}</strong><span class="investigation-status" data-investigation-status="${fresh?status:'unknown'}">${spEscape(fresh?(statuses[status]||'Status onbekend'):'Eerdere beoordeling')}</span></div><p>${spEscape(text(item.summary,1200))}</p>${typeof item.next_action==='string'&&item.next_action.slice(0,1200).trim()?`<p class="investigation-next"><b>Volgende stap:</b> ${spEscape(text(item.next_action,1200))}</p>`:''}${evidence||hypotheses||metrics.length||proposals.length||proof?`<details data-ui-key="investigation-${spEscape(id)}" data-key="investigation-${spEscape(id)}" data-reason-key="investigation:${spEscape(id)}"><summary>Meetbasis en voorstellen</summary>${evidence?`<h4>Waargenomen</h4><ul>${evidence}</ul>`:''}${hypotheses?`<h4>Mogelijke verklaringen · niet bewezen</h4><ul>${hypotheses}</ul>`:''}${metrics.length?`<dl class="investigation-metrics">${metrics.map(([key,value])=>`<div><dt>${spEscape(text(key,120))}</dt><dd>${spEscape(typeof value==='string'?text(value,200):String(value))}</dd></div>`).join('')}</dl>`:''}${proof}${proposals.length?`<h4>Voorstellen · niet automatisch toegepast</h4><ul>${proposals.map(proposal=>`<li><b>${spEscape(typeof proposal.kind==='string'&&Object.hasOwn(proposalKinds,proposal.kind)?proposalKinds[proposal.kind]:'Voorstel')}:</b> ${spEscape(text(proposal.text,1200))}</li>`).join('')}</ul>`:''}</details>`:''}</article>`;
  }).join('')}${valid&&!items.length?'<p class="note">Nog geen afzonderlijke onderzoeksbevindingen.</p>':''}<p class="note">Deze beoordeling staat los van een eerder geüpload adviesrapport. De meetbasis gaat mee in een nieuwe analyse-export.</p></section>`;
};
const SP_INVESTIGATION_STYLE=`.automatic-investigation{margin:18px 0;padding-top:10px;border-top:1px solid var(--divider-color,#39434d)}.automatic-investigation h3{font-size:15px}.investigation-item{padding:12px;border:1px solid var(--divider-color,#39434d);border-radius:12px;margin:10px 0;min-width:0}.investigation-head{display:flex;justify-content:space-between;align-items:flex-start;gap:8px;flex-wrap:wrap}.investigation-head strong{font-size:13px;overflow-wrap:anywhere;min-width:0}.investigation-status{font-size:10px;border:1px solid var(--divider-color,#39434d);border-radius:12px;padding:3px 7px;max-width:100%;overflow-wrap:anywhere}.investigation-item p,.investigation-item li,.investigation-item summary,.investigation-item dt,.investigation-item dd{font-size:12px;line-height:1.55;overflow-wrap:anywhere;white-space:pre-wrap}.investigation-item p{margin:8px 0}.investigation-item h4{font-size:12px;margin:12px 0 5px}.investigation-item ul{padding-left:18px;margin:6px 0}.investigation-metrics{margin:10px 0}.investigation-metrics>div{display:flex;flex-wrap:wrap;gap:4px 10px;border-bottom:1px solid var(--divider-color,#39434d);padding:5px 0}.investigation-metrics dt{flex:1 1 150px;min-width:0}.investigation-metrics dd{margin:0;max-width:100%}`;


/* Read-only popup. Its DOM and polling lifecycle are independent of live card renders. */
class SolarPilotConsumerHistoryDialog extends HTMLElement {
  static solarPilotRelease=SP_CARD_VERSION;
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
    this._dialog.addEventListener('close',()=>{if(!this._dialog.open)this._cleanup();});
    this._dialog.addEventListener('cancel',()=>this._cleanup());
    this._dialog.addEventListener('click',e=>{if(e.target!==this._dialog)return;const r=this._dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)this.close();});
    this._visibility=()=>{if(this._isOpen&&document.visibilityState!=='hidden')this._fetch(false);};
    const scrubStyle=document.createElement('style');
    scrubStyle.textContent=`[data-history-scrub]{touch-action:pan-y;cursor:crosshair;min-height:28px;overflow:hidden}[data-history-scrub]:focus-visible{outline:3px solid var(--primary-color,#00a0c6);outline-offset:3px}.history-crosshair{position:absolute;top:-4px;bottom:-4px;width:2px;transform:translateX(-50%);background:var(--primary-text-color,#fff);box-shadow:0 0 0 1px #0008;pointer-events:none;z-index:2}.history-readout{position:sticky;top:0;z-index:5;max-height:45dvh;overflow-y:auto;background:var(--card-background-color,#1c1f24);border:1px solid var(--divider-color,#46515c);border-radius:12px;padding:10px 12px;margin:12px 0;box-shadow:0 3px 12px #0003;font-size:11px;line-height:1.4;overflow-wrap:anywhere}.history-readout strong{font-size:13px}.scrub-values{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:7px 14px;margin-top:7px}.scrub-values b,.scrub-values small{display:block}.scrub-values b{font-size:13px}.scrub-values small,.scrub-hint{font-size:10px;color:var(--secondary-text-color,#a6b2bf)}.scrub-controls{display:flex;gap:6px;flex-wrap:wrap;margin-top:7px}.scrub-controls button{min-height:32px;padding:5px 8px;font-size:10px}.history-readout p{margin:5px 0 0}@media(max-width:540px){.scrub-values{grid-template-columns:repeat(2,minmax(0,1fr));gap:5px 10px}.history-readout{padding:8px 10px}.history-readout strong{font-size:12px}}`;
    scrubStyle.textContent+=`.consumer-readout details{margin-top:7px}.consumer-readout summary{font-size:11px}.consumer-readout .reasons{grid-template-columns:1fr;gap:2px}.consumer-readout .reasons dt{font-weight:650}.consumer-readout .reasons dd+dt{margin-top:7px}`;
    this.shadowRoot.append(scrubStyle);
    this._body.addEventListener('pointerdown',e=>this._scrubPointerDown(e));
    this._body.addEventListener('pointermove',e=>this._scrubPointerMove(e));
    this._body.addEventListener('pointerup',e=>this._scrubPointerUp(e));
    this._body.addEventListener('pointercancel',e=>this._scrubPointerCancel(e));
    this._body.addEventListener('lostpointercapture',e=>this._scrubPointerCancel(e));
    this._body.addEventListener('keydown',e=>this._scrubKeydown(e));

  }
  open(hass,entryId,device){
    this._resetScrub();this._historySelection=null;this._scrubPendingDay=null;
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
  setContext(hass,device,entryId){
    if(this._isOpen&&entryId!==undefined&&entryId!==this._entryId)this.close();
    this._hass=hass;if(!this._isOpen)return;
    if(device){this._device=device;this.shadowRoot.querySelector('.live').textContent=device.reason||'';
      const revision=device.history?.revision;if(revision!==this._revision){this._revision=revision;this._fetch(false);}}
  }
  close(){if(this._dialog.open)this._dialog.close();this._cleanup();}
  _cleanup(){this._resetScrub();this._historySelection=null;if(!this._isOpen)return;this._isOpen=false;this._seq++;this._inflight=0;clearInterval(this._timer);this._timer=null;document.removeEventListener('visibilitychange',this._visibility);this.dispatchEvent(new CustomEvent('history-closed'));}
  disconnectedCallback(){this.close();}
  _status(text,error=false){const el=this.shadowRoot.querySelector('.update-status');el.textContent=text;el.classList.toggle('error',error);}
  _resetScrub(){this._scrub=null;this._cancelScrubPointer();}
  _cancelScrubPointer(){const pointer=this._scrubPointer;this._scrubPointer=null;if(pointer&&this._body?.hasPointerCapture?.(pointer.id))this._body.releasePointerCapture(pointer.id);}
  _scrubBounds(){
    const x=this._data,start=x?.day_start,end=x?.day_end;if(this._scrubPendingDay&&this._scrubPendingDay!==x?.date)return null;
    return typeof start==='number'&&Number.isFinite(start)&&start>0&&typeof end==='number'&&Number.isFinite(end)&&end>start&&end-start===Number(x.day_seconds)?{start,end}:null;
  }
  _scrubSelection(target,{snap=true}={}){
    const bounds=this._scrubBounds();if(!bounds||typeof target!=='number'||!Number.isFinite(target))return null;
    const at=Math.min(bounds.end-.001,Math.max(bounds.start,target));let point=null;
    if(snap)for(const p of this._scrubPoints())if(Math.abs(p.captured_at-at)<=150&&(!point||Math.abs(p.captured_at-at)<Math.abs(point.captured_at-at)))point=p;
    return {at:point?point.captured_at:at,point};
  }
  _setScrub(target,options){this._historySelection=null;const selected=this._scrubSelection(target,options);if(!selected)return;this._scrub={date:this._data.date,at:selected.at,pointAt:selected.point?.captured_at??null};this._syncScrub();}
  _scrubState(){
    const s=this._scrub,bounds=this._scrubBounds();if(!s||s.date!==this._data?.date||!bounds||s.at<bounds.start||s.at>=bounds.end)return null;
    return {at:s.at,point:s.pointAt===s.at?this._scrubPoints().find(p=>p.captured_at===s.at)||null:null};
  }
  _scrubClock(at){try{return new Intl.DateTimeFormat('nl-BE',{hour:'2-digit',minute:'2-digit',second:'2-digit',timeZone:this._data?.timezone||'Europe/Brussels',timeZoneName:'shortOffset'}).format(new Date(at*1000));}catch{return '—';}}
  _scrubAttributes(lane,label){const bounds=this._scrubBounds();return `data-history-scrub="${spEscape(lane)}" role="slider" tabindex="0" aria-label="${spEscape(label+' · tijd selecteren')}" aria-valuemin="0" aria-valuemax="${bounds?Math.round(bounds.end-bounds.start):0}" aria-valuenow="0" aria-valuetext="Nog geen tijd geselecteerd" aria-disabled="${!bounds}"`;}
  _syncScrub(){
    const state=this._scrubState(),bounds=this._scrubBounds(),readout=this._body?.querySelector?.('[data-history-readout]');
    if(readout){const before=readout.getBoundingClientRect().height;readout.innerHTML=this._scrubReadoutHtml();const delta=readout.getBoundingClientRect().height-before;if(delta&&this._scroll)this._scroll.scrollTop+=delta;}
    for(const lane of this._body?.querySelectorAll?.('[data-history-scrub]')||[]){const marker=lane.querySelector('[data-history-crosshair]');if(marker){marker.hidden=!state;if(state)marker.style.left=`${(state.at-bounds.start)/(bounds.end-bounds.start)*100}%`;}lane.setAttribute('aria-disabled',!bounds);lane.setAttribute('aria-valuenow',state?Math.round(state.at-bounds.start):0);lane.setAttribute('aria-valuetext',state?(state.point?'Meetpunt ':'Gekozen tijd ')+this._scrubClock(state.at):'Nog geen tijd geselecteerd');}
    this._keepConsumerScrubVisible();
  }
  _keepConsumerScrubVisible(){
    if(!this._scrubState()||!this._scroll)return;
    const readout=this._body?.querySelector?.('[data-consumer-readout]'),lane=this._body?.querySelector?.('[data-history-scrub="consumer"]');if(!readout||!lane)return;
    const overlap=readout.getBoundingClientRect().bottom+8-lane.getBoundingClientRect().top;
    if(overlap>0)this._scroll.scrollTop=Math.max(0,this._scroll.scrollTop-overlap);
  }
  _scrubTarget(e,rect){const bounds=this._scrubBounds();return bounds&&rect?.width>0?bounds.start+Math.min(1,Math.max(0,(e.clientX-rect.left)/rect.width))*(bounds.end-bounds.start):null;}
  _scrubPointerDown(e){
    const lane=e.target.closest?.('[data-history-scrub]');if(!lane||!this._scrubBounds()||e.button!==0)return;
    if(this._scrubPointer||e.isPrimary===false){this._cancelScrubPointer();return;}
    this._scrubPointer={id:e.pointerId,x:e.clientX,y:e.clientY,rect:lane.getBoundingClientRect(),drag:false,type:e.pointerType};if(e.pointerType==='mouse')this._setScrub(this._scrubTarget(e,this._scrubPointer.rect));
  }
  _scrubPointerMove(e){
    const p=this._scrubPointer;if(!p){if(e.pointerType==='mouse'&&!e.buttons){const lane=e.target.closest?.('[data-history-scrub]');if(lane)this._setScrub(this._scrubTarget(e,lane.getBoundingClientRect()));}return;}
    if(e.pointerId!==p.id)return;
    const dx=Math.abs(e.clientX-p.x),dy=Math.abs(e.clientY-p.y);if(!p.drag&&dy>6&&dy>=dx){this._cancelScrubPointer();return;}
    if(!p.drag&&dx>=6&&dx>dy*1.3){p.drag=true;this._body.setPointerCapture?.(p.id);}
    if(p.drag){if(e.cancelable)e.preventDefault();this._setScrub(this._scrubTarget(e,p.rect));}
  }
  _scrubPointerUp(e){const p=this._scrubPointer;if(!p||e.pointerId!==p.id)return;this._setScrub(this._scrubTarget(e,p.rect));this._cancelScrubPointer();}
  _scrubPointerCancel(e){if(this._scrubPointer?.id===e.pointerId)this._cancelScrubPointer();}
  _scrubKeydown(e){
    const lane=e.target.closest?.('[data-history-scrub]'),bounds=this._scrubBounds();if(!lane||!bounds)return;
    const state=this._scrubState(),at=state?.at??bounds.start,step=e.shiftKey?900:60;let target;
    if(e.key==='ArrowRight'||e.key==='ArrowUp')target=at+step;else if(e.key==='ArrowLeft'||e.key==='ArrowDown')target=at-step;else if(e.key==='Home')target=bounds.start;else if(e.key==='End')target=bounds.end-.001;else return;
    e.preventDefault();this._setScrub(target,{snap:false});
  }
  _scrubPoints(){return [];}
  _historyItemKey(item,kind){return JSON.stringify(kind==='session'?[kind,item.id??null,item.start??item.segment_start]:[kind,item.at,item.kind??item.type??'',item.reason??'']);}
  _historyTimestamp(value){const stamp=typeof value==='number'?value:Date.parse(value)/1000;if(!Number.isFinite(stamp)||stamp<=0)return '—';try{return new Intl.DateTimeFormat('nl-BE',{day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit',timeZone:this._data?.timezone||'Europe/Brussels',timeZoneName:'shortOffset'}).format(new Date(stamp*1000));}catch{return '—';}}
  _consumerSessionAt(at){return (this._data?.sessions||[]).find(s=>{const start=Date.parse(s.segment_start)/1000,end=Date.parse(s.segment_end)/1000;return start<=at&&(end>at||end===at&&(start===end||s.ongoing===true||s.stop_confirmed===false));});}
  _consumerSessionHtml(session){
    const sources={solarpilot:'SolarPilot-opdracht',external:'Extern / toestel',unknown:'Niet vastgesteld'},start=session.start??session.segment_start,last=session.observed_until??session.segment_end;
    const stop=session.stop_confirmed===true?'Stop waargenomen':session.ongoing===true?'Nog geen stop bevestigd':'Einde onbekend';
    return `<dl class="reasons"><dt>Begin</dt><dd>${spEscape(this._historyTimestamp(start))} · ${session.start_confirmed===true?'overgang bevestigd':'eerder begin niet vastgesteld'}<br>${spEscape(sources[session.start_source]||sources.unknown)}</dd><dt>Startreden</dt><dd>${spEscape(session.start_reason||'Geen betrouwbare startreden geregistreerd.')}</dd><dt>Einde</dt><dd>${stop}${session.stop_confirmed===true?' · '+spEscape(this._historyTimestamp(session.end??session.segment_end)):''}<br>Laatst waargenomen ${spEscape(this._historyTimestamp(last))}</dd><dt>Stopreden</dt><dd>${spEscape(session.stop_reason||'Geen betrouwbare stopreden geregistreerd.')}<br>${spEscape(sources[session.stop_source]||sources.unknown)}</dd><dt>Duur deze dag</dt><dd>${spEscape(this._duration(session.duration_s))} geregistreerd</dd></dl>`;
  }
  _scrubReadoutHtml(){
    const selected=this._scrubState(),x=this._data;
    if(!selected)return '<strong>Bekijk een moment of gebeurtenis</strong><p class="scrub-hint">Tik, sleep horizontaal of gebruik de pijltjestoetsen op de tijdlijn. Kies een sessie of melding voor de oorspronkelijke details. Lege perioden blijven onbekend.</p>';
    const chosen=this._historySelection,event=chosen?.kind==='event'?(x.events||[]).find(e=>this._historyItemKey(e,'event')===chosen.key):null;
    const session=chosen?.kind==='session'?(x.sessions||[]).find(s=>this._historyItemKey(s,'session')===chosen.key):this._consumerSessionAt(selected.at);
    const daily=`<p class="scrub-hint">Dagtotaal: ${spEscape(this._duration(x.on_s))} geregistreerde AAN-tijd. Momentvermogen en sessieverbruik zijn niet in deze registratie bewaard.</p>`;
    return `<strong data-scrub-time>${event?'Geregistreerde gebeurtenis':'Gekozen tijd'} ${spEscape(this._scrubClock(selected.at))}</strong>${event?`<p>${spEscape(String(event.reason||'Geen toelichting bewaard.').slice(0,100))}${String(event.reason||'').length>100?'…':''}</p><details data-consumer-selection><summary>Oorspronkelijke melding</summary><p>${spEscape(event.reason||'Geen toelichting bewaard.')}</p><small>Vastgelegd ${spEscape(this._historyTimestamp(event.at))}</small>${daily}</details>`:session?`<p><b>AAN-periode geregistreerd</b></p><p>${spEscape(this._clock(session.segment_start))} → ${spEscape(this._clock(session.segment_end))} · ${spEscape(this._duration(session.duration_s))} geregistreerd deze dag</p><details data-consumer-selection><summary>Oorspronkelijke waarnemingen en redenen</summary>${this._consumerSessionHtml(session)}${daily}</details>`:'<p><b>Onbekend bij deze tijd</b></p><p class="scrub-hint">Geen betrouwbare AAN-periode op dit moment geregistreerd. Dit bewijst geen UIT-stand.</p>'+daily}<div class="scrub-controls"><button data-action="scrub-clear">Selectie wissen</button></div>`;
  }
  _historyRequest(){return{type:'solar_pilot/consumer_history',config_entry_id:this._entryId,device_id:this._deviceId};}
  async _fetch(force){
    if(!this._isOpen||(!force&&(this._inflight||Date.now()-this._lastFetch<5000)))return;
    const seq=++this._seq;this._inflight=seq;this._lastFetch=Date.now();
    this._status('Geschiedenis ophalen…');let timeout;
    try{
      const msg=this._historyRequest();if(this._day)msg.date=this._day;
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
  _duration(s){s=spNumber(s);if(s==null)return '—';s=Math.max(0,Math.round(s));if(s<60)return `${s} s`;const h=Math.floor(s/3600),m=Math.floor(s%3600/60);return h?`${h} u ${m} min`:`${m} min`;}
  _selectDay(day){this._resetScrub();this._historySelection=null;this._scrubPendingDay=day||this._data?.today;this._syncScrub();this._day=day;this._fetch(true);}
  _shiftDay(n){if(!this._day)return;const d=new Date(this._day+'T12:00:00Z');d.setUTCDate(d.getUTCDate()+n);this._selectDay(d.toISOString().slice(0,10));}
  _click(e){
    const b=e.target.closest('button');if(!b||b.disabled)return;
    if(b.dataset.historySession||b.dataset.historyEvent){const kind=b.dataset.historySession?'session':'event',key=b.dataset.historySession||b.dataset.historyEvent,item=(kind==='session'?this._data?.sessions:this._data?.events)?.find(row=>this._historyItemKey(row,kind)===key);if(item){const stamp=Date.parse(kind==='session'?item.segment_start:item.at)/1000;this._setScrub(stamp,{snap:false});this._historySelection={kind,key};this._syncScrub();}return;}
    if(b.dataset.action==='scrub-clear'){this._resetScrub();this._historySelection=null;this._syncScrub();return;}
    if(b.dataset.action==='source-history'){this.dispatchEvent(new CustomEvent('source-history',{detail:{kind:'consumer',item_id:this._deviceId},bubbles:true,composed:true}));return;}
    if(b.dataset.action==='heatpump_source_history'){this.dispatchEvent(new CustomEvent('source-history',{detail:{kind:'heatpump',role:b.dataset.historyRole,source:b.dataset.historySource,expectedEntity:b.dataset.historyEntity},bubbles:true,composed:true}));return;}
    if(b.dataset.day){this._selectDay(b.dataset.day);return;}
    const a=b.dataset.action;if(a==='close')this.close();else if(a==='refresh')this._fetch(true);else if(a==='prev')this._shiftDay(-1);else if(a==='next')this._shiftDay(1);else if(a==='today')this._selectDay(this._data?.today||null);else if(a==='range'){this._range=Number(b.dataset.value)===30?30:7;this._renderData();}
  }
  _renderData(){
    const x=this._data;if(!x)return;
    if(this._scrub?.date!==x.date){this._resetScrub();this._historySelection=null;}if(this._scrubPendingDay===x.date)this._scrubPendingDay=null;
    const sameDay=x.date===this._lastRenderedDay, scroll=sameDay?this._scroll.scrollTop:0;
    const eventsOpen=!!this._body.querySelector('details.events')?.open;
    const focusedDay=this.shadowRoot.activeElement?.dataset?.day;
    const focusedLane=this.shadowRoot.activeElement?.dataset?.historyScrub;
    const days=(x.days||[]).slice(-this._range),max=Math.max(3600,...days.map(d=>Number(d.on_s)||0));
    const sessions=x.sessions||[], labels={solarpilot:'SolarPilot',external:'Extern',unknown:'Onbekend'};
    const pct=v=>Math.min(100,Math.max(0,Number(v)||0));
    const caption=x.has_data?this._duration(x.on_s):'—';
    this._body.innerHTML=`<div class="metrics"><div class="metric"><label>Geregistreerde draaitijd</label><strong data-total>${caption}</strong><small>waargenomen aan-/actiefstatus</small></div><div class="metric"><label>Starts</label><strong>${Number(x.starts)||0}</strong><small>bevestigde overgangen</small></div><div class="metric"><label>Stops</label><strong>${Number(x.stops)||0}</strong><small>meetgaten niet meegeteld</small></div></div>
      ${x.recording_error?`<div class="notice">${spEscape(x.recording_error)}</div>`:''}
      ${x.partial?`<div class="notice">Onvolledige meetdekking: ${this._duration(x.unobserved_s)} van deze dag niet geregistreerd. Ontbrekende perioden zijn geen bewezen stilstand en worden niet bij de draaitijd geteld.</div>`:''}
      <section class="history-readout consumer-readout" data-consumer-readout data-history-readout aria-label="Historisch geselecteerd moment">${this._scrubReadoutHtml()}</section><h3>Wanneer ingeschakeld</h3><div class="timeline" ${this._scrubAttributes('consumer','Geregistreerde aan-perioden van de gekozen dag')}>${sessions.map(s=>`<span class="segment ${s.start_source==='external'?'external':s.start_source==='unknown'?'unknown':''} ${s.ongoing?'ongoing':''}" style="left:${pct(s.left_pct)}%;width:${pct(s.width_pct)}%" title="${spEscape(this._clock(s.segment_start)+' – '+this._clock(s.segment_end)+' · '+this._duration(s.duration_s))}"></span>`).join('')}<i class="history-crosshair" data-history-crosshair hidden></i></div><div class="axis"><span>00:00</span><span>${x.day_seconds===86400?'12:00':`${x.day_seconds/3600} uur (tijdwissel)`}</span><span>24:00</span></div><div class="legend"><span><i class="dot"></i>SolarPilot-start</span><span><i class="dot external"></i>Extern gestart</span><span><i class="dot unknown"></i>Begin onbekend</span></div>
      <p class="note">Lege stukken betekenen: geen geregistreerde aan-tijd. Ze bewijzen geen uitschakeling tijdens een meetonderbreking.</p>
      <div class="period-head"><h3>Draaitijd per dag</h3><button data-action="range" data-value="7" aria-pressed="${this._range===7}">7 dagen</button><button data-action="range" data-value="30" aria-pressed="${this._range===30}">30 dagen</button></div>
      <div class="days ${this._range===30?'month':''}">${days.map(d=>`<button class="day ${d.on_s==null?'missing':''}" data-day="${spEscape(d.date)}" aria-pressed="${d.date===x.date}" aria-label="${spEscape(d.date+' · '+(d.on_s==null?'geen registratie':this._duration(d.on_s)))}"><span class="bar-slot">${d.on_s!=null?`<span class="bar" style="height:${pct(Number(d.on_s)/max*100)}%"></span>`:''}</span><small>${spEscape(d.date.slice(8)+'/'+d.date.slice(5,7))}</small><b>${d.on_s==null?'—':spEscape(spDuration(d.on_s))}</b></button>`).join('')}</div>
      <h3>Sessies · ${spEscape(x.date)}</h3>${!sessions.length?`<div class="empty">${x.has_data?'Geen ingeschakelde sessie geregistreerd voor deze dag.':'Voor deze dag is nog geen geschiedenis beschikbaar.'}</div>`:sessions.map(s=>{
        const startLabel=s.continued_from_previous_day?'00:00 (doorlopend)':this._clock(s.segment_start);
        const endLabel=s.continues_next_day?'24:00 (loopt door)':s.ongoing?'loopt nog':this._clock(s.segment_end);
        const startReason=(s.continued_from_previous_day?'Gestart op '+this._clock(s.start)+' in een vorige dag. ':'')+(s.start_reason||'Niet vastgesteld; er is geen betrouwbare eerdere oorzaak geregistreerd.');
        const stopReason=s.continues_next_day?'Nog geen stop: deze sessie loopt door na de gekozen dag.':s.ongoing?'Nog geen stop bevestigd. Laatste waarneming: '+this._clock(s.observed_until):s.stop_reason||'Niet vastgesteld; er is geen betrouwbare stopoorzaak geregistreerd.';
        return `<article class="session"><div class="session-head"><button data-history-session="${spEscape(this._historyItemKey(s,'session'))}" aria-label="${spEscape('Details sessie '+startLabel+' – '+endLabel)}"><strong>${spEscape(startLabel)} → ${spEscape(endLabel)}</strong></button><span class="pill ${s.ongoing&&!s.continues_next_day?'running':''}">${spEscape(s.ongoing&&!s.continues_next_day?'Actief':labels[s.start_source]||'Onbekend')}</span><span class="duration">${this._duration(s.duration_s)}</span></div><dl class="reasons"><dt>Startreden</dt><dd>${spEscape(startReason)}</dd><dt>Stopreden</dt><dd>${spEscape(stopReason)}</dd></dl><details><summary>Oorspronkelijke waarnemingen en bevestiging</summary>${this._consumerSessionHtml(s)}</details></article>`;}).join('')}
      ${x.sessions_truncated?'<div class="notice">Het maximum aantal bewaarde sessies is bereikt. De dagtotalen blijven beschikbaar; de oudste sessiedetails van deze dag zijn niet meer volledig.</div>':''}
      ${(x.events||[]).length?`<details class="events" ${eventsOpen?'open':''}><summary>Opdrachten, onderbrekingen en meldingen (${x.events.length})</summary>${x.events.map(e=>`<div class="event"><button data-history-event="${spEscape(this._historyItemKey(e,'event'))}" aria-label="${spEscape('Details gebeurtenis '+this._clock(e.at))}"><time>${this._clock(e.at)}</time>${spEscape(e.reason)}</button></div>`).join('')}</details>`:''}
      <button data-action="source-history">Bronhistorie in Home Assistant</button><p class="note">Bronhistorie betreft de huidige koppeling. Home Assistant bepaalt welke Recorder-gegevens beschikbaar zijn; ontbrekend verleden wordt niet aangevuld.</p>
      <p class="note">${spEscape(x.note||'')} Registratie sinds ${spEscape(x.recording_since||'—')}. Geschiedenis blijft lokaal bewaard, maximaal ${Number(x.retention_days)||30} dagen. Geen oude start-/stopredenen verzonnen of uit voorspellingen afgeleid.</p>`;
    this._syncScrub();this._lastRenderedDay=x.date;this._scroll.scrollTop=scroll;this._keepConsumerScrubVisible();
    if(focusedLane){const lane=Array.from(this._body.querySelectorAll('[data-history-scrub]')).find(el=>el.dataset.historyScrub===focusedLane);lane?.focus({preventScroll:true});}
    if(focusedDay){const b=Array.from(this._body.querySelectorAll('button[data-day]')).find(b=>b.dataset.day===focusedDay);b?.focus({preventScroll:true});}
  }
}
if(!customElements.get('solar-pilot-consumer-history-dialog'))customElements.define('solar-pilot-consumer-history-dialog',SolarPilotConsumerHistoryDialog);
if(!customElements.get(SP_CONSUMER_HISTORY_TAG))customElements.define(SP_CONSUMER_HISTORY_TAG,class extends SolarPilotConsumerHistoryDialog {});

/* Water and appliance context are recorded observations, never device attribution. */
class SolarPilotWaterHistoryDialog extends SolarPilotConsumerHistoryDialog {
  constructor(){
    super();this.shadowRoot.querySelector('#history-title').textContent='Watergeschiedenis';this.shadowRoot.querySelector('.close').setAttribute('aria-label','Watergeschiedenis sluiten');
    const style=document.createElement('style');style.textContent=`.water-samples{height:58px}.water-sample{position:absolute;bottom:0;width:3px;min-height:2px;transform:translateX(-50%);background:#29b6f6}.water-sample.temperature{background:#ffb74d}.water-sample.active{background:#ab87e5;height:100%}.water-sample.inactive{background:#78909c;height:5px}.water-sample.leak{background:#ef7676;height:100%}.water-sample.clear{background:#80b9aa;height:5px}.water-readout details{margin-top:7px}.water-readout summary{font-size:11px}.water-proof{margin:8px 0;font-size:11px}.water-proof dt{font-weight:650;margin-top:7px}.water-proof dd{margin:2px 0;overflow-wrap:anywhere}.water-readout .scrub-values{grid-template-columns:repeat(3,minmax(0,1fr));gap:5px 10px}.water-readout .scrub-values b{font-size:12px}.water-point-note{font-size:11px;line-height:1.5}.water-readout button{min-height:32px}.water-event{display:block;text-align:left;width:100%;margin:7px 0;white-space:normal}@media(max-width:540px){.water-readout .scrub-values{grid-template-columns:repeat(2,minmax(0,1fr))}}`;
    style.textContent+='.metrics{grid-template-columns:2fr 1fr}';this.shadowRoot.append(style);
  }
  _waterUser(hass=this._hass){return JSON.stringify([hass?.user?.id??null,hass?.user?.is_admin===true]);}
  open(hass,entryId,device){this._waterIdentity=this._waterUser(hass);this._waterEvent=null;this._waterActiveLane='water-flow';super.open(hass,entryId,device);}
  setContext(hass,device,entryId){if(this._isOpen&&this._waterUser(hass)!==this._waterIdentity)this.close();super.setContext(hass,device,entryId);}
  _cleanup(){this._waterEvent=null;super._cleanup();}
  _historyRequest(){return{type:'solar_pilot/water_history',config_entry_id:this._entryId};}
  _validatedWaterDay(data){
    const date=value=>typeof value==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(value)&&Number.isFinite(Date.parse(value+'T12:00:00Z'))&&new Date(value+'T12:00:00Z').toISOString().slice(0,10)===value;
    const stamp=value=>typeof value==='number'&&Number.isFinite(value)&&value>0;
    if(!data||data.schema!==1||data.read_only!==true||!date(data.date)||!date(data.today)||!date(data.min_date)||data.date<data.min_date||data.date>data.today||!stamp(data.day_start)||!stamp(data.day_end)||data.day_end<=data.day_start||data.day_end-data.day_start>172800||!stamp(data.generated_at)||typeof data.timezone!=='string'||!Array.isArray(data.points)||data.points.length>8192||!Array.isArray(data.intervals)||data.intervals.length>8192||!Array.isArray(data.events)||data.events.length>512||!Array.isArray(data.days)||data.days.length>30)throw Error('Geen bruikbare watergeschiedenis ontvangen.');
    try{const calendar=new Intl.DateTimeFormat('sv-SE',{timeZone:data.timezone,year:'numeric',month:'2-digit',day:'2-digit'});if(calendar.format(new Date(data.day_start*1000))!==data.date||calendar.format(new Date((data.day_end-.001)*1000))!==data.date)throw Error();}catch{throw Error('Daggrenzen of tijdzone in watergeschiedenis passen niet bij de gekozen dag.');}
    return{...data,day_seconds:data.day_end-data.day_start,points:data.points.filter(p=>p&&stamp(p.captured_at)&&p.captured_at>=data.day_start&&p.captured_at<data.day_end).sort((a,b)=>a.captured_at-b.captured_at),events:data.events.filter(e=>e&&stamp(e.at)&&e.at>=data.day_start&&e.at<data.day_end&&typeof e.kind==='string'),intervals:data.intervals.filter(i=>i&&stamp(i.start)&&stamp(i.end)&&i.end>i.start&&i.start<data.day_end&&i.end>data.day_start&&spWaterNumber(i.volume_l)!=null),days:data.days.filter(d=>d&&date(d.date)&&d.date>=data.min_date&&d.date<=data.today)};
  }
  async _fetch(force){
    if(!this._isOpen||(!force&&(this._inflight||Date.now()-this._lastFetch<5000)))return;
    const seq=++this._seq,identity=this._waterIdentity,entry=this._entryId;this._inflight=seq;this._lastFetch=Date.now();this._status('Watergeschiedenis ophalen…');let timer;
    try{const msg=this._historyRequest();if(this._day)msg.date=this._day;
      const send=this._hass?.callWS?m=>this._hass.callWS(m):this._hass?.connection?.sendMessagePromise?m=>this._hass.connection.sendMessagePromise(m):null;if(!send)throw Error('Geen Home Assistant-verbinding beschikbaar.');
      const result=await Promise.race([send(msg),new Promise((_,reject)=>timer=setTimeout(()=>reject(Error('Geen antwoord; probeer opnieuw.')),15000))]);
      if(!this._isOpen||seq!==this._seq||entry!==this._entryId||identity!==this._waterUser())return;
      const data=this._validatedWaterDay(result);if(msg.date&&data.date!==msg.date)throw Error('Het antwoord hoort bij een andere dag; kies de dag opnieuw.');this._data=data;this._day=data.date;this._input.value=data.date;this._input.min=data.min_date;this._input.max=data.today;
      this.shadowRoot.querySelector('[data-action=prev]').disabled=data.date<=data.min_date;this.shadowRoot.querySelector('[data-action=next]').disabled=data.date>=data.today;
      this._renderData();this._status(`Bijgewerkt ${this._clock(data.generated_at)} · alleen lezen`);
    }catch(error){if(this._isOpen&&seq===this._seq&&identity===this._waterUser()){this._status(error?.message||'Watergeschiedenis niet beschikbaar.',true);if(!this._data)this._body.innerHTML='<div class="empty">Nog geen watergeschiedenis beschikbaar. Ontbrekende metingen worden niet aangevuld. Vernieuw of controleer de gekoppelde bronnen en leesrechten.</div>';}}
    finally{clearTimeout(timer);if(this._inflight===seq)this._inflight=0;}
  }
  _clock(value){return typeof value==='number'?this._scrubClock(value):super._clock(value);}
  _scrubPoints(){const bounds=this._scrubBounds();return bounds?(this._data?.points||[]).filter(p=>p&&typeof p.captured_at==='number'&&Number.isFinite(p.captured_at)&&p.captured_at>=bounds.start&&p.captured_at<bounds.end):[];}
  _scrubSelection(target,{snap=true}={}){
    const selected=super._scrubSelection(target,{snap:false});if(!selected)return selected;
    let point=null;for(const p of this._scrubPoints())if((snap?Math.abs(p.captured_at-selected.at)<=30:p.captured_at===selected.at)&&(!point||Math.abs(p.captured_at-selected.at)<Math.abs(point.captured_at-selected.at)))point=p;
    return{at:point?point.captured_at:selected.at,point};
  }
  _setScrub(target,options){this._waterEvent=null;super._setScrub(target,options);}
  _waterPointerLane(e){const value=e.target.closest?.('[data-history-scrub]')?.dataset?.historyScrub;if(['water-flow','water-temperature','water-dishwasher','water-leak'].includes(value))this._waterActiveLane=value;}
  _scrubPointerDown(e){this._waterPointerLane(e);super._scrubPointerDown(e);}
  _scrubPointerMove(e){if(!this._scrubPointer)this._waterPointerLane(e);super._scrubPointerMove(e);}
  _scrubKeydown(e){this._waterPointerLane(e);super._scrubKeydown(e);}
  _pointWater(point){
    const at=point?.captured_at,temperature=spWaterReading(point?.context?.boiler?.temperature,at),target=spWaterReading(point?.context?.boiler?.target,at);
    return{flow:spWaterReading(point?.flow,at,{unit:'L/min',current:true}),volume:spWaterReading(point?.volume,at,{unit:'L',current:true}),leak:spWaterReading(point?.native_leak,at,{flag:true,current:true}),temperature:temperature!=null&&temperature<=100?temperature:null,target:target!=null&&target<=100?target:null,dishwasher:spWaterReading(point?.context?.dishwasher,at,{flag:true})};
  }
  _waterEventLabel(event){
    const labels={counter_reset:'Tellerstand teruggelopen; vergelijking onderbroken',counter_gap:'Meetgat bij vergelijking van tellerstanden',binding_changed:'Bronkoppeling gewijzigd; eerdere meetketen onderbroken',advisory_started:event.cause==='native_leak'?'Watermeter meldde een mogelijk lek':event.cause==='continuous_flow'?'Langdurige stroming gemeld':'Watermeter en stromingspatroon vroegen controle',advisory_resolved:'Eerdere waterwaarschuwing afgehandeld',flow_state:{unknown:'Stromingspatroon onbekend',clear:'Geen aanhoudend stromingspatroon gemeten',pending:'Stromingspatroon wordt gevolgd',suspected:'Langdurige stroming waargenomen'}[event.state]||'Stromingspatroon gewijzigd'};
    return labels[event.kind]||'Waterwaarneming';
  }
  _scrubReadoutHtml(){
    const selected=this._scrubState();if(!selected)return '<strong>Kies een watermeetpunt</strong><p class="scrub-hint">Tik, sleep horizontaal of gebruik de pijltjestoetsen op een balk. Binnen 30 seconden kiest de cursor een werkelijk bewaard meetpunt. Daarbuiten blijven de waarden onbekend.</p>';
    const point=selected.point,v=point?this._pointWater(point):{},event=this._waterEvent&&(this._data.events||[]).find(e=>e.at===this._waterEvent.at&&e.kind===this._waterEvent.kind);
    const field=(label,value)=>`<div><small>${label}</small><b>${spEscape(value)}</b></div>`;
    const proof=(label,reading)=>`<dt>${label}</dt><dd>${spEscape(this._historyTimestamp(reading?.reported_at))} · geldig tot ${spEscape(this._historyTimestamp(reading?.valid_until))}</dd>`;
    return `<strong data-scrub-time>${point?'Meetpunt':'Gekozen tijd'} ${spEscape(this._scrubClock(selected.at))}</strong>${event?`<p>${spEscape(this._waterEventLabel(event))}</p>`:''}${!point?'<p class="scrub-hint">Geen exact bewaard meetpunt op deze gekozen tijd. Waarden bij deze tijd zijn onbekend; de huidige meting wordt niet teruggeplaatst.</p>':`<div class="scrub-values">${field('Stroming',spWaterFlow(v.flow))}${field('Meterstand',spWaterLiters(v.volume))}${field('Boiler',spTemp(v.temperature))}${field('Ingesteld doel',spTemp(v.target))}${field('Vaatwasstatus',v.dishwasher===true?'Programma actief':v.dishwasher===false?'Niet actief gemeld':'Onbekend')}${field('Lekmelding meter',v.leak===true?'Lek gemeld':v.leak===false?'Niet gemeld':'Onbekend')}</div><details data-water-key="point:${spEscape(this._data.date+':'+point.captured_at)}"><summary>Oorspronkelijke tijden en betekenis</summary><dl class="water-proof">${proof('Flowrapport',point.flow)}${proof('Tellerrapport',point.volume)}${proof('Lekrapport',point.native_leak)}${proof('Boilerrapport',point.context?.boiler?.temperature)}${proof('Doelrapport',point.context?.boiler?.target)}${proof('Vaatwasrapport',point.context?.dishwasher)}</dl><p class="scrub-hint">Actualiteit is beoordeeld op dit bewaarde meetpunt. Een rapporttijd bewijst niet het fysieke meetmoment. Gelijktijdigheid bewijst geen oorzaak of liters per toestel.</p></details>`}<div class="scrub-controls"><button data-water-step="-1">Vorig meetpunt</button><button data-water-step="1">Volgend meetpunt</button><button data-action="scrub-clear">Wissen</button></div>`;
  }
  _syncScrub(){super._syncScrub();this._keepWaterScrubVisible();}
  _keepWaterScrubVisible(){
    if(!this._scrubState()||!this._scroll)return;const active=['water-flow','water-temperature','water-dishwasher','water-leak'].includes(this._waterActiveLane)?this._waterActiveLane:'water-flow',readout=this._body?.querySelector?.('[data-water-readout]'),lane=this._body?.querySelector?.(`[data-history-scrub="${active}"]`);if(!readout||!lane)return;
    const heading=lane.previousElementSibling?.tagName==='H3'?lane.previousElementSibling:lane,overlap=readout.getBoundingClientRect().bottom+8-heading.getBoundingClientRect().top;if(overlap>0)this._scroll.scrollTop=Math.max(0,this._scroll.scrollTop-overlap);
  }
  _click(e){
    const b=e.target.closest('button');if(!b||b.disabled)return;
    if(b.dataset.waterStep){const selected=this._scrubState(),points=this._scrubPoints(),dir=Number(b.dataset.waterStep),at=selected?.at??(dir>0?-Infinity:Infinity),point=dir>0?points.find(p=>p.captured_at>at):[...points].reverse().find(p=>p.captured_at<at);if(point)this._setScrub(point.captured_at);return;}
    if(b.dataset.waterEvent){const event=this._data?.events?.[Number(b.dataset.waterEvent)-1];if(event){this._setScrub(event.at,{snap:false});this._waterEvent=event;this._syncScrub();}return;}
    if(b.dataset.action==='source-history'){this.dispatchEvent(new CustomEvent('source-history',{detail:{kind:'water'},bubbles:true,composed:true}));return;}
    super._click(e);
  }
  _waterLane(kind,label){
    const bounds=this._scrubBounds(),points=this._scrubPoints(),rows=points.map(p=>({p,v:this._pointWater(p)})),values=rows.map(({v})=>kind==='water-flow'?v.flow:kind==='water-temperature'?v.temperature:null).filter(v=>v!=null),maximum=Math.max(kind==='water-temperature'?60:1,...values);
    const bars=rows.map(({p,v})=>{const value=kind==='water-flow'?v.flow:kind==='water-temperature'?v.temperature:kind==='water-dishwasher'?v.dishwasher:v.leak;if(value==null||!bounds)return '';
      const cls=kind==='water-temperature'?'temperature':kind==='water-dishwasher'?(value?'active':'inactive'):kind==='water-leak'?(value?'leak':'clear'):'';
      const text=kind==='water-flow'?spWaterFlow(value):kind==='water-temperature'?spTemp(value):value?'Actief gemeld':'Niet actief gemeld';
      return `<i class="water-sample ${cls}" style="left:${(p.captured_at-bounds.start)/(bounds.end-bounds.start)*100}%;${typeof value==='number'?`height:${Math.max(3,value/maximum*100)}%;`:''}" title="${spEscape(this._scrubClock(p.captured_at)+' · '+text)}"></i>`;
    }).join('');
    return `<h3>${label}</h3><div class="timeline water-samples" ${this._scrubAttributes(kind,label)}>${bars}<i class="history-crosshair" data-history-crosshair hidden></i></div>`;
  }
  _waterCorrelationsHtml(){
    const x=this._data,raw=x.correlations,c=raw?.read_only===true&&raw.scope==='household_water'?raw:{},bounds=this._scrubBounds(),stamp=n=>typeof n==='number'&&Number.isFinite(n)&&n>0,period=row=>row&&stamp(row.start)&&stamp(row.end)&&row.end>row.start&&bounds&&row.start<bounds.end&&row.end>=bounds.start;
    const drops=(Array.isArray(c.boiler_drops)?c.boiler_drops:[]).filter(row=>period(row)&&row.end-row.start<=1800&&spWaterNumber(row.temperature_start_c)!=null&&row.temperature_start_c<=100&&spWaterNumber(row.temperature_end_c)!=null&&row.temperature_end_c<=100&&spWaterNumber(row.drop_c)!=null&&row.drop_c>=2);
    const dish=(Array.isArray(c.dishwasher_intervals)?c.dishwasher_intervals:[]).filter(row=>period(row)&&row.scope==='household_during_observed_dishwasher');
    const volume=row=>row.volume_partial===true&&spWaterNumber(row.observed_volume_l)!=null?`${spWaterLiters(row.observed_volume_l)} huishoudelijke tellerstijging in bruikbare deelintervallen`:'Geen bruikbare huishoudelijke tellerstijging voor dit gehele tijdvenster';
    return `<section class="water-correlations"><h3>Boiler en water samen bekijken</h3><p class="note">Een daling vanaf 2 °C vergelijkt oorspronkelijke verse temperatuurmetingen van dezelfde bronkoppeling, maximaal 30 minuten uit elkaar. Gelijktijdigheid is geen bewijs van warmwatertap, oorzaak of verbruik per toestel.</p><details data-water-key="boiler:${spEscape(x.date)}"><summary>Vergelijkbare boilerdalingen (${drops.length})</summary>${drops.slice(-200).map(row=>`<article class="session"><strong>${spEscape(this._historyTimestamp(row.start)+' → '+this._historyTimestamp(row.end))}</strong><p>${spTemp(row.temperature_start_c)} → ${spTemp(row.temperature_end_c)} · daling ${spTemp(row.drop_c)}</p><p class="note">${row.water_observed===true?'Water waargenomen in hetzelfde tijdvenster.':'Geen bevestigde waterwaarneming in dit tijdvenster; dit bewijst geen stilstand.'} ${row.flow_observed===true?'Er is positieve stroming bewaard.':''} ${spEscape(volume(row))}. Deze liters horen bij de huishoudwatermeter.</p></article>`).join('')||'<p class="note">Nog geen vergelijkbare boilerdaling in de bewaarde meetpunten.</p>'}${drops.length>200?'<p class="note">De laatste 200 vergelijkingen zijn zichtbaar; de bewaarde metingen blijven beschikbaar.</p>':''}</details><details data-water-key="dishwasher:${spEscape(x.date)}"><summary>Waargenomen actief vaatwasprogramma (${dish.length})</summary>${dish.slice(-200).map(row=>`<article class="session"><strong>${spEscape(this._historyTimestamp(row.start)+' → '+this._historyTimestamp(row.end))}</strong><p class="note">${spEscape(volume(row))}. Het programma is gelijktijdig actief waargenomen; dit is geen gemeten vaatwasverbruik.</p></article>`).join('')||'<p class="note">Geen vergelijkbare actieve vaatwascontext voor deze dag bewaard.</p>'}${dish.length>200?'<p class="note">De laatste 200 tijdvensters zijn zichtbaar.</p>':''}</details></section>`;
  }
  _renderData(){
    const x=this._data;if(!x)return;if(this._scrub?.date!==x.date){this._resetScrub();this._waterEvent=null;}if(this._scrubPendingDay===x.date)this._scrubPendingDay=null;
    const sameDay=this._lastRenderedDay===x.date,scroll=sameDay?this._scroll.scrollTop:0,focused=this.shadowRoot.activeElement?.dataset?.historyScrub,opened=new Set(sameDay?Array.from(this._body.querySelectorAll?.('details[data-water-key]')||[]).filter(d=>d.open).map(d=>d.dataset.waterKey):[]),focusedKey=this.shadowRoot.activeElement?.closest?.('details[data-water-key]')?.dataset?.waterKey;
    const byDay=new Map((x.days||[]).map(d=>[d.date,d])),days=[];for(let n=29;n>=0;n--){const d=new Date(x.today+'T12:00:00Z');d.setUTCDate(d.getUTCDate()-n);const date=d.toISOString().slice(0,10);if(date>=x.min_date)days.push(byDay.get(date)||{date,volume_l:null});}
    const shown=days.slice(-this._range),maximum=Math.max(1,...shown.map(d=>spWaterNumber(d.volume_l)??0));
    this._body.innerHTML=`<div class="metrics"><div class="metric"><label>Geregistreerd op deze dag</label><strong data-water-total>${spWaterLiters(x.volume_l)}</strong><small>huishoudelijk water · onvolledig dagbeeld</small></div><div class="metric"><label>Meetdekking teller</label><strong>${spEscape(this._duration(x.volume_covered_s))}</strong><small>bruikbare tellervergelijkingen</small></div></div><section class="history-readout water-readout" data-water-readout data-history-readout aria-label="Historisch watermeetpunt">${this._scrubReadoutHtml()}</section>${this._waterLane('water-flow','Geregistreerde stroming')}${this._waterLane('water-temperature','Boilertemperatuur bij meetpunten')}${this._waterLane('water-dishwasher','Vaatwasstatus bij meetpunten')}${this._waterLane('water-leak','Lekmelding watermeter bij meetpunten')}<div class="axis"><span>00:00</span><span>${x.day_seconds===86400?'12:00':spEscape(x.day_seconds/3600+' uur · tijdwissel')}</span><span>24:00</span></div><p class="water-point-note note">Elke streep is een bewaard meetpunt; er wordt geen lijn over meetgaten getrokken. Vaatwas: hoge paarse streep = actief, korte grijze = niet actief gemeld. Lekmelding: hoge rode streep = melding, korte groene = niet gemeld. Ontbrekende streep blijft onbekend.</p><div class="period-head"><h3>Water per dag</h3><button data-action="range" data-value="7" aria-pressed="${this._range===7}">7 dagen</button><button data-action="range" data-value="30" aria-pressed="${this._range===30}">30 dagen</button></div><div class="days ${this._range===30?'month':''}">${shown.map(d=>`<button class="day ${spWaterNumber(d.volume_l)==null?'missing':''}" data-day="${spEscape(d.date)}" aria-pressed="${d.date===x.date}" aria-label="${spEscape(d.date+' · '+spWaterLiters(d.volume_l)+' geregistreerd')}"><span class="bar-slot">${spWaterNumber(d.volume_l)!=null?`<span class="bar" style="height:${d.volume_l/maximum*100}%"></span>`:''}</span><small>${spEscape(d.date.slice(8)+'/'+d.date.slice(5,7))}</small><b>${spEscape(spWaterLiters(d.volume_l))}</b></button>`).join('')}</div><p class="note">Alleen bekende tellerstijgingen tellen mee. Lege dagen en meetgaten zijn geen 0 liter. Een verschil over lokale middernacht wordt niet willekeurig verdeeld.</p>${(x.events||[]).length?`<details data-water-key="events:${spEscape(x.date)}"><summary>Oorspronkelijke gebeurtenissen (${x.events.length})</summary>${x.events.map((event,i)=>`<button class="water-event" data-water-event="${i+1}">${spEscape(this._scrubClock(event.at)+' · '+this._waterEventLabel(event))}</button>`).join('')}</details>`:''}<details data-water-key="intervals:${spEscape(x.date)}"><summary>Tellervergelijkingen en dekking</summary>${(x.intervals||[]).slice(-200).map(row=>`<p class="note">${spEscape(this._historyTimestamp(row.start)+' → '+this._historyTimestamp(row.end))} · ${spEscape(spWaterLiters(row.volume_l))}${row.day===x.date?' geregistreerd op deze dag':' · niet aan één lokale dag toegeschreven'}</p>`).join('')||'<p class="note">Geen betrouwbare tellervergelijking voor deze dag bewaard.</p>'}${x.intervals.length>200?'<p class="note">De laatste 200 tellervergelijkingen zijn zichtbaar.</p>':''}<p class="note">${spEscape(x.coverage?.note||'')} Bewaargrens: ${Number(x.coverage?.point_cap)||8192} punten over 30 dagen. Verdwenen oudere detailpunten worden niet aangevuld.</p></details>${this._waterCorrelationsHtml()}<p class="note">Water, boiler en vaatwasser zijn gelijktijdige waarnemingen. Een temperatuurdaling bewijst geen warmwatertap en een actief programma krijgt geen huishoudelijke liters toegeschreven.</p><button data-action="source-history">Bronhistorie in Home Assistant</button>`;
    this._syncScrub();for(const detail of this._body.querySelectorAll?.('details[data-water-key]')||[])if(opened.has(detail.dataset.waterKey))detail.open=true;this._lastRenderedDay=x.date;this._scroll.scrollTop=scroll;this._keepWaterScrubVisible();if(focused)Array.from(this._body.querySelectorAll('[data-history-scrub]')).find(el=>el.dataset.historyScrub===focused)?.focus({preventScroll:true});if(sameDay&&focusedKey)Array.from(this._body.querySelectorAll?.('details[data-water-key]')||[]).find(el=>el.dataset.waterKey===focusedKey)?.querySelector('summary')?.focus({preventScroll:true});
  }
}
if(!customElements.get(SP_WATER_HISTORY_TAG))customElements.define(SP_WATER_HISTORY_TAG,SolarPilotWaterHistoryDialog);

/* Entity history stays in Home Assistant; the catalogue exposes approved roles only. */
class SolarPilotSourceHistoryDialog extends HTMLElement {
  static solarPilotRelease=SP_CARD_VERSION;
  constructor(){
    super();this.attachShadow({mode:'open'});this._seq=0;this._isOpen=false;this._data=null;
    this.shadowRoot.innerHTML=`<style>:host{font-family:var(--paper-font-body1_-_font-family,system-ui,sans-serif);color:var(--primary-text-color,#e6edf5)}*{box-sizing:border-box}dialog{width:min(620px,calc(100vw - 24px));max-height:calc(100dvh - 24px);padding:0;border:1px solid var(--divider-color,#46515c);border-radius:16px;color:inherit;background:var(--card-background-color,#1c1f24)}dialog::backdrop{background:#0009}header{display:flex;align-items:flex-start;gap:16px;padding:18px;border-bottom:1px solid var(--divider-color,#46515c)}h2{margin:0;font-size:20px;flex:1;overflow-wrap:anywhere}button,a{font:inherit;color:inherit;border:1px solid var(--divider-color,#46515c);border-radius:10px;padding:9px 12px;min-height:40px;background:transparent;cursor:pointer}button:focus-visible,a:focus-visible{outline:3px solid var(--primary-color,#00a0c6);outline-offset:2px}button:disabled{opacity:.5}.close{font-size:22px}.body{overflow:auto;max-height:calc(100dvh - 150px);padding:16px 18px}p,small{font-size:12px;line-height:1.5;overflow-wrap:anywhere}small{display:block;color:var(--secondary-text-color,#a6b2bf);margin-top:6px}ul{padding:0;list-style:none}li{padding:12px 0;border-top:1px solid var(--divider-color,#46515c)}li strong{display:block;font-size:14px;overflow-wrap:anywhere}.actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}a{font-size:11px;text-decoration:none;display:inline-flex;align-items:center}.status{font-size:12px;min-height:20px}.note{color:var(--secondary-text-color,#a6b2bf)}@media(max-width:400px){header,.body{padding:14px}h2{font-size:18px}}</style><dialog aria-labelledby="source-history-title"><header><h2 id="source-history-title">Bronhistorie in Home Assistant</h2><button class="close" aria-label="Bronhistorie sluiten">×</button></header><div class="body"><p class="status" role="status" aria-live="polite"></p><div class="sources"></div></div></dialog>`;
    this._dialog=this.shadowRoot.querySelector('dialog');this._statusEl=this.shadowRoot.querySelector('.status');this._body=this.shadowRoot.querySelector('.sources');
    this.shadowRoot.querySelector('.close').addEventListener('click',()=>this.close());
    this.shadowRoot.addEventListener('click',e=>{const b=e.target.closest('button[data-source-index]');if(b&&!b.disabled)this._fetch(Number(b.dataset.sourceIndex));});
    this._dialog.addEventListener('close',()=>{if(!this._dialog.open)this._cleanup();});this._dialog.addEventListener('cancel',()=>this._cleanup());
    this._dialog.addEventListener('click',e=>{if(e.target!==this._dialog)return;const r=this._dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)this.close();});
  }
  _userKey(hass=this._hass){return JSON.stringify([hass?.user?.id??null,hass?.user?.is_admin===true]);}
  open(hass,entryId,kind,itemId,options={}){
    this._cleanup();this._hass=hass;this._entryId=entryId;this._kind=kind;this._itemId=itemId;this._source=options.source;this._directRole=options.role;this._expectedEntity=options.expectedEntity;this._identity=this._userKey();this._isOpen=true;this._body.textContent='';this._dialog.showModal();this.shadowRoot.querySelector('.close').focus();this._fetch();
  }
  updateContext(hass,entryId){if(this._isOpen&&(entryId!==this._entryId||this._userKey(hass)!==this._identity))this.close();this._hass=hass;}
  _cleanup(){this._isOpen=false;this._seq++;this._data=null;this._busy=false;}
  close(){this._cleanup();if(this._dialog.open)this._dialog.close();}
  disconnectedCallback(){this.close();}
  _request(){return{type:'solar_pilot/source_history',config_entry_id:this._entryId,kind:this._kind,...(this._kind==='heatpump'?{source:this._source}:['wallbox','water'].includes(this._kind)?{}:{item_id:this._itemId})};}
  _validated(data){
    const allowed=new Set(['schema','read_only','scope','kind','item_id','name','sources','note']);
    if(!data||data.schema!==1||data.read_only!==true||data.scope!=='current_configured_sources'||data.kind!==this._kind||(['wallbox','heatpump','water'].includes(this._kind)?Object.hasOwn(data,'item_id'):data.item_id!==this._itemId)||Object.keys(data).some(k=>!allowed.has(k))||!Array.isArray(data.sources)||data.sources.length>40)throw new Error('Geen bruikbaar overzicht van toegestane bronnen ontvangen.');
    const sources=data.sources.filter(s=>s&&typeof s.role==='string'&&typeof s.label==='string'&&typeof s.entity_id==='string'&&/^[a-z0-9_]+\.[a-z0-9_]+$/.test(s.entity_id)&&Object.keys(s).every(k=>['role','label','entity_id'].includes(k)));
    return{...data,sources};
  }
  permits(entityId){return this._isOpen&&this._identity===this._userKey()&&this._data?.sources.some(s=>s.entity_id===entityId);}
  async _fetch(index){
    if(!this._isOpen||this._busy)return;const selected=Number.isInteger(index)?this._data?.sources[index]:null,seq=++this._seq,identity=this._identity;this._busy=true;this._statusEl.textContent=selected?'Bronkoppeling controleren…':'Toegestane bronkoppelingen ophalen…';let timer;
    for(const b of this._body.querySelectorAll('button'))b.disabled=true;
    try{const send=this._hass?.callWS?m=>this._hass.callWS(m):m=>this._hass.connection.sendMessagePromise(m),data=await Promise.race([send(this._request()),new Promise((_,reject)=>timer=setTimeout(()=>reject(new Error('Geen antwoord ontvangen; sluit het venster en probeer opnieuw.')),15000))]);
      if(!this._isOpen||seq!==this._seq||identity!==this._userKey())return;this._data=this._validated(data);
      if(this._directRole){const matches=this._data.sources.filter(s=>s.role===this._directRole);if(matches.length!==1||matches[0].entity_id!==this._expectedEntity){this._data={...this._data,sources:[]};this._render();this._statusEl.textContent='Deze getoonde temperatuurbron is niet meer beschikbaar of de koppeling is gewijzigd. Er is geen andere bron geopend.';return;}this._data={...this._data,sources:matches};this._render();this.dispatchEvent(new CustomEvent('source-history-open',{detail:{entityId:matches[0].entity_id,entryId:this._entryId,userKey:this._identity},bubbles:true,composed:true}));return;}
      this._render();
      if(selected){if(!this._data.sources.some(s=>s.role===selected.role&&s.entity_id===selected.entity_id)){this._statusEl.textContent='De koppeling is gewijzigd. Kies een huidige bron opnieuw.';return;}this.dispatchEvent(new CustomEvent('source-history-open',{detail:{entityId:selected.entity_id,entryId:this._entryId,userKey:this._identity},bubbles:true,composed:true}));}
    }catch(error){if(this._isOpen&&seq===this._seq){this._data=null;this._body.textContent='';this._statusEl.textContent=error?.message||'Bronhistorie niet beschikbaar voor deze gebruiker.';}}
    finally{clearTimeout(timer);if(seq===this._seq){this._busy=false;for(const b of this._body.querySelectorAll('button'))b.disabled=false;}}
  }
  _render(){
    const d=this._data;this._statusEl.textContent=d?.name||'Toegestane bronnen';
    this._body.innerHTML=`<p class="note">Dit zijn de huidige bronkoppelingen. De Home Assistant-historie hoort bij de entiteit; oudere gegevens kunnen bij een eerdere koppeling horen. Recorder en je toegangsrechten bepalen welke metingen beschikbaar zijn.</p>${d.sources.length?`<ul>${d.sources.map((s,i)=>`<li><strong>${spEscape(s.label)}</strong><small>${spEscape(s.entity_id)}</small><div class="actions"><button data-source-index="${i}">Historie bekijken</button><a href="/history?entity_id=${encodeURIComponent(s.entity_id)}" target="_blank" rel="noopener noreferrer">Historiepagina openen ↗</a></div></li>`).join('')}</ul>`:'<p>Geen gekoppelde bronnen met leesrechten beschikbaar. Er worden geen ontbrekende metingen ingevuld.</p>'}${d.note?`<p class="note">${spEscape(d.note)}</p>`:''}<p class="note">Historie bekijken opent het historische tabblad van Home Assistant en geeft geen toestelopdracht.</p>`;
  }
}
if(!customElements.get(SP_SOURCE_HISTORY_TAG))customElements.define(SP_SOURCE_HISTORY_TAG,SolarPilotSourceHistoryDialog);

/* Native heatpump observations share the stable read-only lifecycle, not consumer start attribution. */
class SolarPilotHeatpumpHistoryDialog extends SolarPilotConsumerHistoryDialog {
  constructor(){
    super();
    this.shadowRoot.querySelector('h2').textContent='Warmtepompgeschiedenis';
    this.shadowRoot.querySelector('[data-action=close]').setAttribute('aria-label','Warmtepompgeschiedenis sluiten');
    const style=document.createElement('style');
    style.textContent=`.evidence-table{max-width:100%;overflow-x:auto}.evidence-table table{border-collapse:collapse;min-width:760px;width:100%;font-size:11px}.evidence-table th,.evidence-table td{text-align:left;vertical-align:top;padding:8px;border-bottom:1px solid var(--divider-color,#39434d)}.evidence-table small{display:block;font-size:10px;color:var(--secondary-text-color,#a6b2bf)}h2{overflow-wrap:anywhere}.metrics{grid-template-columns:2fr 1fr 1fr 2fr}.task-timeline .segment{background:#03a9f4}.task-timeline .segment.tapwater{background:#f2b544}.task-timeline .segment.cooling{background:#77cfca}.task-timeline .segment.other{background:#b6a0d5}.task-timeline .segment.unknown{background:var(--secondary-text-color,#a6b2bf)}.segment.derived{background-image:repeating-linear-gradient(135deg,transparent 0 5px,#fff5 5px 8px)}.task-timeline .segment.ongoing:not(.derived){background-image:none;box-shadow:inset -3px 0 0 #fff8}.task-list{display:grid;gap:7px}.task-row,.sg-lane{display:flex;align-items:center;flex-wrap:wrap;gap:8px;padding:10px 12px;border:1px solid var(--divider-color,#39434d);border-radius:10px;min-width:0}.task-row>strong,.sg-lane>strong{flex:1;min-width:100px;overflow-wrap:anywhere;font-size:12px}.task-row .duration{margin-left:0}.contact-overlay{margin:9px 0 15px}.contact-head{display:flex;align-items:center;justify-content:space-between;gap:10px;font-size:11px;margin-bottom:5px}.contact-timeline{height:16px;background:repeating-linear-gradient(135deg,#76818b18 0 4px,transparent 4px 8px)}.contact-timeline .segment{min-width:0}.contact-timeline .contact-on{background:#00a0c6;opacity:1}.contact-timeline .contact-off{background:var(--card-background-color,#1c1f24);box-shadow:inset 0 -3px 0 #657580;opacity:1}.contact-timeline .contact-unknown{background:repeating-linear-gradient(135deg,#87939e66 0 3px,transparent 3px 6px);opacity:1}.dot.contact-off{background:#657580}.dot.contact-unknown{border-radius:1px;background:repeating-linear-gradient(135deg,#87939e 0 2px,transparent 2px 4px)}.tank-history{margin:12px 0;padding:12px;border:1px solid var(--divider-color,#39434d);border-radius:12px}.tank-history>strong{font-size:12px}.tank-values{display:flex;flex-wrap:wrap;gap:12px 24px;margin:7px 0;font-size:11px}.tank-values b{font-size:16px;display:block;margin-top:4px}.tank-history small,.session-tank small{display:block;font-size:10px;color:var(--secondary-text-color,#a6b2bf);line-height:1.5}.session-tank{font-size:12px;padding-top:7px;border-top:1px solid var(--divider-color,#39434d)}.support-history .timeline{height:13px}.support-history{margin:12px 0}.support-history h4{font-size:11px;margin:0 0 5px}.support-history .segment{background:#b6a0d5}.sg-lanes{display:grid;gap:10px;margin:12px 0}.sg-lane .timeline{width:100%;height:18px}.sg-lane small{width:100%;font-size:11px;color:var(--secondary-text-color,#a6b2bf)}.day .energy{font-size:9px;color:var(--secondary-text-color,#a6b2bf);white-space:normal;overflow-wrap:anywhere;text-align:center}.period-head{flex-wrap:wrap}.period-head h3{min-width:120px}.evidence.derived{border:1px dashed var(--warning-color,#e4ae48)}.evidence.confirmed{border:1px solid #03a9f4}.session-task{font-size:12px;line-height:1.5;margin:10px 0 0;overflow-wrap:anywhere}.coverage{font-size:11px}.history-details p{font-size:12px;line-height:1.6;overflow-wrap:anywhere}@media(max-width:540px){.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.metric strong{font-size:20px}.days{grid-template-columns:repeat(7,minmax(0,1fr))}.days.month{grid-template-columns:repeat(6,minmax(0,1fr))}.day small{font-size:9px}.task-row{padding:9px}.period-head button{padding:8px 10px}}`;
    this.shadowRoot.append(style);
    const periodStyle=document.createElement('style');
    periodStyle.textContent=`.session-task small{display:block;font-size:10px;line-height:1.5;color:var(--secondary-text-color,#a6b2bf);margin-top:3px}.session-task-summary{padding:10px 12px;margin:12px 0;border-radius:10px;background:var(--secondary-background-color,#282e37)}.session-task-summary .session-task:first-child{margin-top:0}.session-task-details{margin:12px 0}.session-task-details summary{font-size:12px;line-height:1.5}.session-task .period-duration{font-size:11px}`;
    this.shadowRoot.append(periodStyle);
  }
  _historyRequest(){return{type:'solar_pilot/heatpump_history',config_entry_id:this._entryId};}
  open(hass,entryId,device){
    super.open(hass,entryId,device);clearInterval(this._readingTimer);
    this._readingTimer=setInterval(()=>{if(this._isOpen&&document.visibilityState!=='hidden'&&this._data&&this._temperatureSignature()!==this._readingsSignature)this._renderData();},1000);
  }
  _cleanup(){clearInterval(this._readingTimer);this._readingTimer=null;super._cleanup();}
  _scrubPoints(){
    const x=this._data,bounds=this._scrubBounds(),evidence=x?.native_evidence;
    return bounds&&evidence?.schema===1&&evidence.read_only===true&&Array.isArray(evidence.points)?evidence.points.filter(p=>p&&typeof p.captured_at==='number'&&Number.isFinite(p.captured_at)&&p.captured_at>=bounds.start&&p.captured_at<bounds.end).slice(-8192).sort((a,b)=>a.captured_at-b.captured_at):[];
  }
  _scrubSourceFresh(stamp,at,stale,until){return typeof stamp==='number'&&Number.isFinite(stamp)&&stamp>0&&typeof stale==='number'&&Number.isFinite(stale)&&stale>0&&at-stamp>=-5&&at-stamp<=stale&&(until===undefined||typeof until==='number'&&Number.isFinite(until)&&until>at);}
  _scrubInterval(rows,at,{point=false}={}){if(!Array.isArray(rows))return null;return rows.find(s=>s&&Date.parse(s.segment_start)/1000<=at&&Date.parse(s.segment_end)/1000>at)||(point?rows.find(s=>s&&Date.parse(s.segment_start)/1000<=at&&Date.parse(s.segment_end)/1000===at&&(s.ongoing===true||s.stop_confirmed===false)):null);}
  _scrubReadoutHtml(){
    const selected=this._scrubState(),points=this._scrubPoints();
    if(!selected)return `<strong>Bekijk een moment op de tijdlijn</strong><p class="scrub-hint">Beweeg de muis, tik of sleep horizontaal over een balk. Met de pijltjestoetsen kies je een tijd. Meetpunten worden binnen 2½ minuut geselecteerd op hun werkelijke vastlegtijd.</p>${!this._scrubBounds()?'<p class="scrub-hint">Tijdselectie is beschikbaar zodra de bijgewerkte dagregistratie geladen is.</p>':''}`;
    const {at,point}=selected,x=this._data,tank=point?.tank||{},stale=point?.source_stale_s??120,power=point?.power;
    const fresh=(stamp,limit=stale,until)=>this._scrubSourceFresh(stamp,at,limit,until),temp=fresh(tank.temperature_reported_at)?spTemp(tank.temperature_c):'—',target=fresh(tank.ordinary_target_reported_at)?spTemp(tank.ordinary_target_c):'—';
    const total=power?.schema===1&&power.complete===true&&power.kind==='measured'&&['total','split'].includes(power.source_scope)&&typeof power.total_w==='number'&&Number.isFinite(power.total_w)&&power.total_w>=0&&typeof power.valid_until==='number'&&Number.isFinite(power.valid_until)&&fresh(power.reported_at,power.stale_s,power.valid_until)?spPower(power.total_w):'—';
    const endpoint={point:!!point},native=point?.native,task=this._scrubInterval(x.task_sessions,at,endpoint),support=this._scrubInterval(x.support_sessions,at,endpoint);let contact=x.sg_contact_overlay?.schema===1?this._scrubInterval(x.sg_contact_overlay.segments,at):null;
    const sourceContact=point?.sg_goal;if(!contact&&['on','off'].includes(sourceContact?.contact_state)&&typeof sourceContact.contact_valid_until==='number'&&Number.isFinite(sourceContact.contact_valid_until)&&fresh(sourceContact.contact_reported_at,sourceContact.contact_stale_s,sourceContact.contact_valid_until))contact={state:sourceContact.contact_state,reported_at:sourceContact.contact_reported_at};
    const nativeTasks={space_heating:'Verwarmen',space_cooling:'Koelen',tapwater_heating:'Boiler opwarmen',sterilization:'Sterilisatie'},nativeTask=native?.confirmed===true&&native.fresh===true&&fresh(native.reported_at,native.stale_s)&&Object.hasOwn(nativeTasks,native.function)?nativeTasks[native.function]+' · Bevestigd':null;
    const sgState=key=>this._scrubInterval(x.sg?.[key]?.sessions,at,endpoint)?'AAN geregistreerd':'Onbekend / geen AAN-periode';
    const contactNames={on:'AAN',off:'UIT',unknown:'Onbekend / meetgat'},goal=point?this._historyCalculatedGoal(point):null;
    const value=(label,text,stamp)=>`<span>${spEscape(label)}<b>${spEscape(text)}</b>${stamp!=null?`<small>Bron ${spEscape(this._scrubClock(stamp))}</small>`:''}</span>`;
    return `<strong data-scrub-time>${point?'Meetpunt':'Gekozen tijd'} ${spEscape(this._scrubClock(at))}</strong><div class="scrub-values">${value('Totaal vermogen',total,total!=='—'?power.reported_at:null)}${value('Boilertemperatuur',temp,temp!=='—'?tank.temperature_reported_at:null)}${value('Ingesteld boilerdoel',target,target!=='—'?tank.ordinary_target_reported_at:null)}${value('Taak',task?(task.label||'Taak onbekend')+' · '+this._tier(task.tier):nativeTask||'Onbekend / meetgat')}${value('SG-contact',contactNames[contact?.state]||'Onbekend / meetgat',contact?.reported_at)}${value('Elektrische ondersteuning',support?'Geregistreerd':'Onbekend / geen periode')}${value('SG-aanvraag',sgState('request'))}${value('Panasonic SG-ontvangst',sgState('received'))}${goal?value(goal.label,spTemp(goal.value),goal.normalStamp):''}${(Array.isArray(point?.supplies)?point.supplies:[]).slice(0,2).map((s,i)=>value('Voeding '+(i+1),s.valid===true&&typeof s.watts==='number'&&Number.isFinite(s.watts)&&s.watts>=0&&fresh(s.reported_at)?spPower(s.watts):'—',s.valid===true&&fresh(s.reported_at)?s.reported_at:null)).join('')}</div><p class="scrub-hint">${point?'Waarden horen bij dit vastgelegde meetpunt; afzonderlijke bronrapporten staan erbij.':'Geen vastgelegd meetpunt binnen 2½ minuut. Vermogen en temperatuur bij deze tijd zijn onbekend.'} ${spEscape(spKwh(x.energy_kwh))} is het dagtotaal, geen verbruik op dit moment.</p><div class="scrub-controls">${points.length?`<button data-action="scrub-prev" ${points.some(p=>p.captured_at<at)?'':'disabled'}>‹ Vorig meetpunt</button><button data-action="scrub-next" ${points.some(p=>p.captured_at>at)?'':'disabled'}>Volgend meetpunt ›</button>`:''}<button data-action="scrub-clear">Selectie wissen</button></div>`;
  }
  _click(e){
    const action=e.target.closest('button')?.dataset.action;if(action==='scrub-clear'){this._resetScrub();this._syncScrub();return;}
    if(action==='scrub-prev'||action==='scrub-next'){const state=this._scrubState(),points=this._scrubPoints(),point=action==='scrub-prev'?points.filter(p=>p.captured_at<(state?.at??Infinity)).at(-1):points.find(p=>p.captured_at>(state?.at??-Infinity));if(point)this._setScrub(point.captured_at);this._body?.querySelector?.(`[data-action=${action}]`)?.focus({preventScroll:true});return;}super._click(e);
  }
  _temperatureSignature(){
    const x=this._data,current=x?.tank_temperature?.current||{},now=Date.now()/1000;
    const fresh=(stamp,limit)=>typeof stamp==='number'&&Number.isFinite(stamp)&&stamp>0&&typeof limit==='number'&&Number.isFinite(limit)&&limit>0&&now-stamp>=-5&&now-stamp<=limit;
    const goal=current.sg_goal||{};
    return JSON.stringify([x?.date===x?.today,current.current===true,fresh(current.captured_at,current.capture_stale_s??30),fresh(current.temperature_reported_at,current.stale_s??120),fresh(current.ordinary_target_reported_at,current.stale_s??120),!!spCalculatedTankGoal(goal,{now,stale:current.stale_s??120}),fresh(goal.contact_reported_at,goal.contact_stale_s??120)&&typeof goal.contact_valid_until==='number'&&goal.contact_valid_until>now]);
  }
  setContext(hass,device,entryId){if(this._isOpen&&entryId!==this._entryId)this.close();super.setContext(hass,device);}
  _clock(iso){
    if(!iso||Number(this._data?.day_seconds)===86400)return super._clock(iso);
    try{return new Intl.DateTimeFormat('nl-BE',{hour:'2-digit',minute:'2-digit',timeZone:this._data?.timezone||'Europe/Brussels',timeZoneName:'shortOffset'}).format(new Date(iso));}catch(_){return '—';}
  }
  _tier(tier){return tier==='confirmed'?'Bevestigd':tier==='derived'?'Afgeleid':'Taak onbekend';}
  _taskClass(task){return task==='tapwater_heating'?'tapwater':task==='space_cooling'?'cooling':task==='space_heating'?'heating':task==='unknown'?'unknown':'other';}
  _timeline(sessions,{tasks=false,label='Geregistreerde actieve perioden',lane=tasks?'task':'activity'}={}){
    const pct=value=>Math.min(100,Math.max(0,Number(value)||0));
    return `<div class="timeline ${tasks?'task-timeline':''}" ${this._scrubAttributes(lane,label)}>${sessions.map(s=>`<span class="segment ${tasks?this._taskClass(s.task):''} ${s.tier==='derived'?'derived':''} ${s.tier==='unknown'?'unknown':''} ${s.ongoing?'ongoing':''}" data-history-task="${spEscape(tasks?s.task||'unknown':'activity')}" style="left:${pct(s.left_pct)}%;width:${pct(s.width_pct)}%" title="${spEscape(this._clock(s.segment_start)+' – '+this._clock(s.segment_end)+(tasks?' · '+(s.label||'Taak onbekend')+' · '+this._tier(s.tier):'')+' · '+this._duration(s.duration_s))}"></span>`).join('')}<i class="history-crosshair" data-history-crosshair hidden></i></div>`;
  }
  _reportClock(value){const n=spNumber(value);if(n==null||n<=0)return '—';try{return new Intl.DateTimeFormat('nl-BE',{hour:'2-digit',minute:'2-digit',second:'2-digit',timeZone:this._data?.timezone||'Europe/Brussels',...(Number(this._data?.day_seconds)!==86400?{timeZoneName:'shortOffset'}:{})}).format(new Date(n*1000));}catch{return '—';}}
  _electricalClock(iso,short){return short===true?this._reportClock(Date.parse(iso)/1000):this._clock(iso);}
  _recordedPeriodSeconds(row,from=Date.parse(row.segment_start)/1000,to=Date.parse(row.segment_end)/1000){
    const span=to-from,value=row.duration_s;return typeof value==='number'&&Number.isFinite(value)&&value>=0&&Math.abs(value-span)<=1.1?value:span;
  }
  _sessionPeriods(rows,session){
    const bounds=this._scrubBounds(),start=Date.parse(session.segment_start)/1000,end=Date.parse(session.segment_end)/1000;
    if(!Number.isFinite(start)||!Number.isFinite(end)||end<start)return [];
    const left=Math.max(start,bounds?.start??start),right=Math.min(end,bounds?.end??end),parentSeconds=this._recordedPeriodSeconds(session,start,end);if(right<left)return [];
    return (Array.isArray(rows)?rows:[]).flatMap(row=>{if(!row||typeof row!=='object')return [];const from=Date.parse(row.segment_start)/1000,to=Date.parse(row.segment_end)/1000;if(!Number.isFinite(from)||!Number.isFinite(to)||to<from)return [];
      const recorded=this._recordedPeriodSeconds(row,from,to);
      if(from===to)return from>=left&&from<=right&&(!bounds||from<bounds.end)&&!(recorded>0&&parentSeconds===0)?[{...row,period_start:from,period_end:to,period_s:Math.min(recorded,parentSeconds),period_clipped:false,period_precision:recorded>0}]:[];
      const a=Math.max(left,from),b=Math.min(right,to),clipped=a!==from||b!==to,seconds=Math.min(recorded,parentSeconds,clipped?b-a:recorded);return b>a?[{...row,period_start:a,period_end:b,period_s:seconds,period_clipped:clipped,period_precision:!clipped&&recorded!==to-from}]:[];
    }).sort((a,b)=>a.period_start-b.period_start||a.period_end-b.period_end);
  }
  _periodDuration(seconds){
    if(typeof seconds!=='number'||!Number.isFinite(seconds)||seconds<0)return '—';if(seconds===0)return 'duur niet vastgesteld';if(seconds<.1)return '< 0,1 s';
    const tenths=Math.round(seconds*10),hours=Math.floor(tenths/36000),minutes=Math.floor(tenths%36000/600),rest=tenths%600/10,parts=[];
    if(hours)parts.push(hours+' u');if(minutes)parts.push(minutes+' min');if(rest||!parts.length)parts.push(rest.toLocaleString('nl-BE',{maximumFractionDigits:1})+' s');return parts.join(' ');
  }
  _sessionPeriodRow(row,{support=false}={}){
    const point=row.period_s===0,clocks=point?'Meetpunt '+this._reportClock(row.period_start):this._reportClock(row.period_start)+' – '+this._reportClock(row.period_end),tier=support?'derived':row.tier,label=support?'Elektrische ondersteuning':row.label||'Taak onbekend';
    return `<p class="session-task" ${support?'data-session-support':'data-session-task-period'}>${spEscape(clocks+' · '+label)}${['confirmed','derived'].includes(tier)?` <span class="pill evidence ${tier}">${this._tier(tier)}</span>`:''}<span class="period-duration"> · ${spEscape(this._periodDuration(row.period_s))}</span>${row.period_clipped?'<small>Getoond binnen deze sessie en dag.</small>':row.period_precision?'<small>Tijden op hele seconden; duur uit de registratie.</small>':''}</p>`;
  }
  _sessionTasksHtml(rows,session){
    if(rows.length<=8)return rows.map(row=>this._sessionPeriodRow(row)).join('');
    let latest=-Infinity,total=0,overlap=false;for(const row of rows){total+=row.period_s;if(row.period_s>0){if(row.period_start<latest&&row.period_end>row.period_start)overlap=true;latest=Math.max(latest,row.period_end);}}
    if(total>this._recordedPeriodSeconds(session)+.1)overlap=true;
    const groups=new Map();for(const row of rows){const key=JSON.stringify([row.task||'unknown',row.tier||'unknown']);if(!groups.has(key))groups.set(key,{label:row.label||'Taak onbekend',tier:row.tier,seconds:0,count:0,points:0});const group=groups.get(key);group.seconds+=row.period_s;group.count++;if(row.period_s===0)group.points++;}
    const key='session-tasks:'+this._data.date+':'+String(session.id??'')+':'+String(session.start??session.segment_start);
    return `<div class="session-task-summary" data-session-task-summary>${overlap?'<p class="note" data-session-period-overlap>Opgetelde duur · perioden overlappen. Dit is geen extra sessielooptijd.</p>':''}${Array.from(groups.values(),group=>`<p class="session-task">${spEscape(group.label)}${['confirmed','derived'].includes(group.tier)?` <span class="pill evidence ${group.tier}">${this._tier(group.tier)}</span>`:''}<b class="period-duration"> · ${spEscape(this._periodDuration(group.seconds))}</b><small>${group.count} ${group.count===1?'waarneming':'waarnemingen'}${group.points?' · '+group.points+' '+(group.points===1?'meetpunt zonder vastgestelde duur':'meetpunten zonder vastgestelde duur'):''}</small></p>`).join('')}</div><details class="history-details session-task-details" data-history-key="${spEscape(key)}"><summary>Alle ${rows.length} taakperioden en meetpunten · chronologisch</summary><p class="note">Dit zijn afzonderlijke waarnemingen. De samenvatting vult geen onbekende perioden in en voegt geen looptijd of verbruik toe.</p>${rows.map(row=>this._sessionPeriodRow(row)).join('')}</details>`;
  }
  _sgContactOverlayHtml(data){
    const valid=data?.schema===1,states={on:'SG-contact AAN',off:'SG-contact UIT',unknown:'SG-contact onbekend'},pct=value=>Math.min(100,Math.max(0,spNumber(value)??0));
    const segments=valid&&Array.isArray(data.segments)?data.segments.slice(-2000).filter(s=>s&&Object.hasOwn(states,s.state)):[];
    return `<section class="contact-overlay" data-sg-contact-overlay><div class="contact-head"><strong>SG-contact</strong><span>${valid&&data.on_s!=null?this._duration(data.on_s)+' AAN':'AAN-tijd onbekend'}</span></div><div class="timeline contact-timeline" ${this._scrubAttributes('contact','Gemelde SG-contactstand op dezelfde tijdas als de warmtepomptaken')}>${segments.map(s=>`<span class="segment contact-${s.state}" data-sg-contact-state="${s.state}" style="left:${pct(s.left_pct)}%;width:${pct(s.width_pct)}%" title="${spEscape(this._clock(s.segment_start)+' – '+this._clock(s.segment_end)+' · '+states[s.state]+(s.reported_at!=null?' · bronrapport '+this._reportClock(s.reported_at):''))}"></span>`).join('')}<i class="history-crosshair" data-history-crosshair hidden></i></div><div class="legend"><span><i class="dot"></i>AAN</span><span><i class="dot contact-off"></i>UIT</span><span><i class="dot contact-unknown"></i>Onbekend / meetgat</span></div>${!segments.length?'<p class="note">Nog geen betrouwbare contactperioden geregistreerd.</p>':''}${data?.segments_truncated===true||valid&&Array.isArray(data.segments)&&data.segments.length>2000?'<p class="note">Oudste contactperioden zijn niet meer volledig.</p>':''}</section>`;
  }
  _tankPointDate(stamp){
    const n=spNumber(stamp);if(n==null||n<=0)return null;
    try{return new Intl.DateTimeFormat('en-CA',{timeZone:this._data?.timezone||'Europe/Brussels',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(n*1000));}catch{return null;}
  }
  _tankHistoryPoints(){
    const data=this._data?.tank_temperature;
    return data?.schema===1&&Array.isArray(data.points)?data.points.filter(p=>p&&this._tankPointDate(p.captured_at)===this._data.date).slice(-2000):[];
  }
  _tankHistoryHtml(){
    const x=this._data,data=x.tank_temperature,capture=spNumber(data?.current?.captured_at),captureAge=capture==null?Infinity:Date.now()/1000-capture,live=x.date===x.today&&data?.schema===1&&data.current?.current===true&&captureAge>=-5&&captureAge<=(spNumber(data.current.capture_stale_s)??30);
    const points=this._tankHistoryPoints(),point=live?data.current:points.at(-1),label=live?'Boiler nu':'Laatste vastgelegde boilermeting';
    const fresh=(stamp)=>{const n=spNumber(stamp),limit=spNumber(data?.current?.stale_s)??120,age=n==null?Infinity:Date.now()/1000-n;return n!=null&&age>=-5&&age<=limit;};
    const temp=point&&(!live||fresh(point.temperature_reported_at))?point.temperature_c:null,target=point&&(!live||fresh(point.ordinary_target_reported_at))?point.ordinary_target_c:null;
    const goal=this._historyCalculatedGoal(point,{live});
    const reading=(value,key,stamp)=>{const binding=this._device?.tank_sources?.[key];return live&&binding&&spNumber(binding.value)===spNumber(value)&&binding.reportedAt===stamp?spTankHistoryValue(value,binding):spTemp(value);};
    return `<section class="tank-history" data-tank-history="${live?'current':'recorded'}"><strong>${label}</strong><div class="tank-values"><span>Temperatuur <b data-tank-temperature>${reading(temp,'temperature_c',point?.temperature_reported_at)}</b></span><span>Ingesteld doel <b data-tank-target>${reading(target,'target_c',point?.ordinary_target_reported_at)}</b></span>${goal?`<span>${spEscape(goal.label)} <b data-tank-sg-target>${spTemp(goal.value)}</b></span>`:''}</div><small>${point?`Bronrapporten: ${spEscape(this._reportClock(point.temperature_reported_at))} / ${spEscape(this._reportClock(point.ordinary_target_reported_at))}`:'Geen betrouwbare meting voor deze dag.'}</small>${data?.points_truncated===true?'<small>Oudste meetpunten zijn niet meer volledig.</small>':''}</section>`;
  }
  _historyCalculatedGoal(point,{live=false,diagnostic=false}={}){
    const value=point?.sg_goal,now=live?Date.now()/1000:spNumber(point?.captured_at),stale=spNumber(point?.stale_s??point?.source_stale_s??point?.sg_goal?.stale_s)??120;
    if(now==null)return null;
    const goal=spCalculatedTankGoal(value,{now,stale}),contactStamp=spNumber(value?.contact_reported_at),contactUntil=spNumber(value?.contact_valid_until),contactStale=spNumber(value?.contact_stale_s)??120;
    const contactKnown=['on','off'].includes(value?.contact_state)&&contactStamp!=null&&contactStamp>0&&now-contactStamp>=-5&&now-contactStamp<=contactStale&&contactUntil!=null&&contactUntil>now;
    return goal?{...goal,label:contactKnown&&value.contact_state==='on'?'SG-doel · berekend':'SG-doel bij AAN · berekend',contactState:contactKnown?value.contact_state:'unknown'}:null;
  }
  _sessionTankHtml(session){
    const start=Date.parse(session.segment_start)/1000,end=Date.parse(session.segment_end)/1000;
    const points=this._tankHistoryPoints().filter(p=>spNumber(p.captured_at)>=start&&spNumber(p.captured_at)<=end),temperatures=points.filter(p=>spNumber(p.temperature_c)!=null&&spNumber(p.temperature_reported_at)>=start&&spNumber(p.temperature_reported_at)<=end),targets=points.filter(p=>spNumber(p.ordinary_target_c)!=null&&spNumber(p.ordinary_target_reported_at)>=start&&spNumber(p.ordinary_target_reported_at)<=end);
    const first=temperatures[0],last=temperatures.at(-1),target=targets.at(-1);
    if(!first&&!target)return '';
    const goalPoint=points.at(-1),goal=this._historyCalculatedGoal(goalPoint);
    return `<p class="session-tank" data-session-tank>Boiler: ${first?`${spTemp(first.temperature_c)}${last!==first?' → '+spTemp(last.temperature_c):''}`:'—'} · ingesteld doel ${spTemp(target?.ordinary_target_c)}${goal?`<span data-session-sg-goal> · ${spEscape(goal.label)} ${spTemp(goal.value)}</span>`:''}<small>Gemeten om ${spEscape(first?this._reportClock(first.temperature_reported_at):'—')}${last&&last!==first?' – '+spEscape(this._reportClock(last.temperature_reported_at)):''}${target?' · doel gemeld om '+spEscape(this._reportClock(target.ordinary_target_reported_at)):''}${goal?' · SG-doelbron '+spEscape(this._reportClock(goal.normalStamp)):''}</small></p>`;
  }
  _nativeHistoryCaption(point){
    const n=point?.native||{},contract=point?.source_contract;
    const recorded=contract?.schema===1&&contract.read_only===true&&n.source==='aquarea_poll',profile=recorded&&contract.contract_id==='aioaquarea_ng_1_3_1_special_status'&&contract.action_semantics==='special_status';
    if(profile){const raw=['OFF','IDLE','HEATING','COOLING','HEATING_WATER'].includes(contract.raw_device_action)?contract.raw_device_action:'onbekend';return {profile:true,verified:contract.verified===true,label:'SDK-profielstatus: '+raw};}
    if(recorded&&contract.contract_id==='aioaquarea_ng_split_operation_status_v1'&&contract.action_semantics==='operation_status'){const raw=['OFF','IDLE','HEATING','COOLING','HEATING_WATER'].includes(contract.raw_device_action)?contract.raw_device_action:'onbekend';return {profile:true,verified:contract.verified===true,label:'Panasonic-bronstatus: '+raw};}
    if(recorded){const raw=['OFF','IDLE','HEATING','COOLING','HEATING_WATER'].includes(contract.raw_device_action)?contract.raw_device_action:'onbekend';return {profile:true,verified:false,label:'Panasonic-bronstatus: '+raw};}
    const names={space_heating:'Ruimte verwarmen',space_cooling:'Ruimte koelen',tapwater_heating:'Boiler opwarmen',sterilization:'Sterilisatie gemeld'};
    return {profile:false,label:n.confirmed===true?(names[n.function]||'Onbekend'):n.inactive_reported===true?(n.global_off===true?'Native globaal UIT':n.inactive_scope==='space_circuit'?'Native ruimtekring in rust':'Native rust · bereik onbekend'):'Onbekend'};
  }
  _nativeEvidenceHtml(evidence){
    const valid=evidence?.schema===1&&evidence.read_only===true&&Array.isArray(evidence.points),points=valid?evidence.points.slice(-200).filter(p=>p&&typeof p==='object'):[];
    return `<details class="history-details" data-history-key="native"><summary>Native programma en tankmetingen</summary><p>Normaal tankdoel, effectief programmadoel en native voltooiing staan apart.</p>${points.length?`<div class="evidence-table"><table><thead><tr><th>Vastgelegd</th><th>Panasonic-status · oorspronkelijk rapport</th><th>Tank · oorspronkelijk rapport</th><th>Gewoon doel · oorspronkelijk rapport</th><th>Berekend SG-doel</th><th>Effectief doel</th><th>Voeding 1 / 2 · oorspronkelijke rapporten</th><th>Native voltooiing</th></tr></thead><tbody>${points.map(p=>{const n=p.native||{},t=p.tank||{},goal=this._historyCalculatedGoal(p,{diagnostic:true}),caption=this._nativeHistoryCaption(p);return `<tr><td>${spEscape(this._reportClock(p.captured_at))}${p.continuity===false?'<small>begin / onderbreking</small>':''}</td><td>${spEscape(caption.label)}${caption.profile?`<small>${caption.verified?'Bronmapping bij vastlegging bevestigd':'Bronmapping bij vastlegging onvolledig'}</small>`:''}${n.start_observed===true?`<small>${caption.profile?'Overgang bronstatus waargenomen':'Native start waargenomen'}</small>`:''}<small>${spEscape(this._reportClock(n.reported_at))}${n.fresh===false?' · niet actueel':''}</small></td><td>${spTemp(t.temperature_c)}<small>${spEscape(this._reportClock(t.temperature_reported_at))}</small></td><td>${spTemp(t.ordinary_target_c)}<small>${spEscape(this._reportClock(t.ordinary_target_reported_at))}</small></td><td data-history-sg-calculation>${goal?`${spTemp(goal.value)}<small>${spEscape(goal.label)} · ${spPct(goal.percent)}</small><small>Normaal doel gerapporteerd ${spEscape(this._reportClock(goal.normalStamp))}</small><small>SG-contact ${goal.contactState==='on'?'AAN':goal.contactState==='off'?'UIT':'onbekend'} bij vastlegging</small>`:'—'}</td><td>Onbekend</td><td>${(Array.isArray(p.supplies)?p.supplies:[]).slice(0,2).map(s=>`${s.valid===true?spPower(s.watts):'—'}<small>${spEscape(this._reportClock(s.reported_at))}${s.valid!==true?' · onbruikbaar / ontbreekt':''}</small>`).join(' / ')}</td><td>Onbekend</td></tr>`;}).join('')}</tbody></table></div>`:'<p>Nog geen vergelijkingspunten geregistreerd. Oudere historie wordt niet achteraf aangevuld.</p>'}${evidence?.points_truncated===true||valid&&evidence.points.length>200?'<p class="notice">Een deel van de vergelijkingspunten is niet in dit overzicht beschikbaar. Ruwe activiteit, dagtotalen en oorspronkelijke meetgaten blijven afzonderlijk behouden.</p>':''}<p>Een gemelde ruststand of hoge temperatuur bevestigt geen voltooide sterilisatie. Vergelijkingspunten zijn geen continue programmameting.</p></details>`;
  }
  _electricalEvidenceHtml(data){
    const sessions=Array.isArray(data?.sessions)?data.sessions:[],short=sessions.filter(s=>s.short_observed_period===true);
    return `<details class="history-details" data-history-key="electrical"><summary>Gemeten elektrische perioden${short.length?' · '+short.length+' van maximaal 30 s':''}</summary><p>${data?.has_data?'Afzonderlijke perioden uit complete actuele vermogensmetingen.':'Nog geen betrouwbare registratie van elektrische perioden.'} Korte perioden zijn afzonderlijk herkenbaar; ze tellen niet als bewezen compressorstarts.</p>${sessions.length?`<div class="task-list">${sessions.map(s=>`<div class="task-row"><strong>${spEscape(this._electricalClock(s.segment_start,s.short_observed_period)+' – '+this._electricalClock(s.segment_end,s.short_observed_period))}</strong><span class="duration">${this._duration(s.duration_s)}</span>${s.short_observed_period===true?'<span class="pill evidence">≤ 30 s</span>':''}${s.stop_confirmed!==true?'<span class="pill evidence unknown">Einde onbekend</span>':''}</div>`).join('')}</div>`:''}<p>${data?.has_data?`${Number(data.starts)||0} ruwe startovergangen · ${Number(data.stops)||0} ruwe stopovergangen. `:''}Geen perioden samengevoegd, meetgaten gevuld of besturing gewijzigd.</p>${data?.sessions_truncated===true?'<p class="notice">Oudste elektrische periodedetails zijn niet meer volledig; de bewaarde dagtotalen blijven beschikbaar.</p>':''}</details>`;
  }
  _renderData(){
    const x=this._data;if(!x)return;
    if(this._scrub?.date!==x.date)this._resetScrub();if(this._scrubPendingDay===x.date)this._scrubPendingDay=null;
    const focusedLane=this.shadowRoot.activeElement?.dataset?.historyScrub;
    const scroll=x.date===this._lastRenderedDay?this._scroll.scrollTop:0;
    const opened=new Set(Array.from(this._body.querySelectorAll('details[open][data-history-key]'),d=>d.dataset.historyKey));
    const active=this.shadowRoot.activeElement,focus=active?.tagName==='BUTTON'?{day:active.dataset.day,action:active.dataset.action,value:active.dataset.value}:null;
    const focusedDetail=active?.tagName==='SUMMARY'?active.parentElement?.dataset.historyKey:null;
    const days=(x.days||[]).slice(-this._range),sessions=x.sessions||[],tasks=x.task_sessions||[],totals=x.task_totals||[],supportSessions=x.support_sessions||[],supportTotals=x.support_totals||[];
    const max=Math.max(3600,...days.map(d=>Number(d.on_s)||0)),pct=value=>Math.min(100,Math.max(0,Number(value)||0));
    const caption=x.has_data&&x.on_s!=null?this._duration(x.on_s):'—';
    const count=value=>x.has_data&&value!=null?Math.max(0,Number(value)||0):'—';
    const sgNames={request:'SG-aanvraag',contact:'SG-contact',received:'Panasonic SG-ontvangst'};
    this._body.innerHTML=`<div class="metrics"><div class="metric"><label>Geregistreerde draaitijd</label><strong data-total>${caption}</strong><small>waargenomen warmtepompactiviteit</small></div><div class="metric"><label>Starts</label><strong data-starts>${count(x.starts)}</strong><small>bevestigde overgangen</small></div><div class="metric"><label>Stops</label><strong data-stops>${count(x.stops)}</strong><small>meetgaten niet meegeteld</small></div><div class="metric"><label>Gemeten verbruik</label><strong data-energy>${spKwh(x.energy_kwh)}</strong><small>gehele warmtepomp · ${this._duration(x.energy_known_s)} meetdekking</small></div></div>
      ${x.recording_error?`<div class="notice">${spEscape(x.recording_error)}</div>`:''}
      ${!x.has_data?`<div class="notice">Voor deze dag is nog geen registratie beschikbaar. Registratie sinds ${spEscape(x.recording_since||'nog niet beschikbaar')}.</div>`:x.partial?`<div class="notice">Onvolledige meetdekking: ${this._duration(x.unobserved_s)} niet geregistreerd. Ontbrekende perioden blijven onbekend.</div>`:''}
      ${this._tankHistoryHtml()}<section class="history-readout" data-history-readout aria-label="Historisch geselecteerd moment">${this._scrubReadoutHtml()}</section><h3>Wat deed de warmtepomp?</h3>${this._timeline(tasks,{tasks:true,label:'Geregistreerde warmtepomptaken van de gekozen dag'})}<div class="axis"><span>00:00</span><span>${Number(x.day_seconds)===86400?'12:00':`${Number(x.day_seconds)/3600} uur (tijdwissel)`}</span><span>24:00</span></div><div class="legend"><span><i class="dot" style="background:#03a9f4"></i>Verwarmen</span><span><i class="dot" style="background:#f2b544"></i>Boiler opwarmen</span><span><i class="dot" style="background:#77cfca"></i>Koelen</span><span><i class="dot" style="background:#b6a0d5"></i>Overige taak</span><span><i class="dot unknown"></i>Taak onbekend</span><span>Gearceerd: afgeleid</span></div>
      ${this._sgContactOverlayHtml(x.sg_contact_overlay)}${supportSessions.length?`<section class="support-history" data-support-history><h4>Elektrische ondersteuning · naast de warmtepomptaak</h4>${this._timeline(supportSessions,{lane:'support',label:'Afzonderlijk gemeten elektrische ondersteuning op dezelfde tijdas'})}</section>`:''}<p class="note">Lege perioden zijn geen bewezen stilstand tijdens een meetgat.</p>
      <h3>Taken op deze dag</h3><div class="task-list" data-task-totals>${totals.length?totals.map(t=>`<div class="task-row"><strong>${spEscape(t.label||'Taak onbekend')}</strong>${['confirmed','derived'].includes(t.tier)?`<span class="pill evidence ${t.tier}">${this._tier(t.tier)}</span>`:''}<span class="duration">${this._duration(t.on_s)}</span></div>`).join(''):'<p class="muted">Nog geen taken geregistreerd voor deze dag.</p>'}</div>
      ${supportTotals.length?`<div class="task-list" data-support-totals>${supportTotals.map(t=>`<div class="task-row"><strong>${spEscape(t.label||'Elektrische ondersteuning')}</strong><span class="pill evidence derived">Afgeleid</span><span class="duration">${this._duration(t.on_s)}</span></div>`).join('')}</div>`:''}<div class="period-head"><h3>Draaitijd per dag</h3><button data-action="range" data-value="7" aria-pressed="${this._range===7}">7 dagen</button><button data-action="range" data-value="30" aria-pressed="${this._range===30}">30 dagen</button></div>
      <div class="days ${this._range===30?'month':''}">${days.map(d=>`<button class="day ${d.on_s==null?'missing':''}" data-day="${spEscape(d.date)}" aria-pressed="${d.date===x.date}" aria-label="${spEscape(d.date+' · '+(d.on_s==null?'geen registratie':this._duration(d.on_s))+' · gemeten verbruik '+spKwh(d.energy_kwh))}"><span class="bar-slot">${d.on_s!=null?`<span class="bar" style="height:${pct(Number(d.on_s)/max*100)}%"></span>`:''}</span><small>${spEscape(String(d.date).slice(8)+'/'+String(d.date).slice(5,7))}</small><b>${d.on_s==null?'—':spEscape(spDuration(d.on_s))}</b><span class="energy">${spKwh(d.energy_kwh)}</span></button>`).join('')}</div>
      <h3>Sessies · ${spEscape(x.date)}</h3>${sessions.length?sessions.map(s=>{
        const periodSeconds=this._recordedPeriodSeconds(s),point=periodSeconds===0,short=periodSeconds<120;
        const start=point?'Meetpunt '+this._reportClock(Date.parse(s.segment_start)/1000):s.continued_from_previous_day?'00:00 (doorlopend)':short?this._reportClock(Date.parse(s.segment_start)/1000):this._clock(s.segment_start),end=s.continues_next_day?'24:00 (loopt door)':s.ongoing?'loopt nog':(short?this._reportClock(Date.parse(s.segment_end)/1000):this._clock(s.segment_end))+(s.stop_confirmed?'':' (laatst waargenomen)');
        const status=s.continues_next_day?'Doorlopend':s.ongoing?'Actief':!s.stop_confirmed?'Einde onbekend':s.start_confirmed?'Begin waargenomen':'Begin onbekend';
        const inSession=this._sessionPeriods(tasks,s),inSupport=this._sessionPeriods(supportSessions,s);
        return `<article class="session"><div class="session-head"><strong>${spEscape(point?start:start+' → '+end)}</strong><span class="pill ${s.ongoing&&!s.continues_next_day?'running':''}">${status}</span><span class="duration">${spEscape(this._periodDuration(periodSeconds))}</span></div>${this._sessionTasksHtml(inSession,s)}${inSupport.map(t=>this._sessionPeriodRow(t,{support:true})).join('')}${this._sessionTankHtml(s)}<dl class="reasons"><dt>Begin</dt><dd>${spEscape(s.start_reason||'Panasonic-activiteit waargenomen; de startoorzaak is niet vastgesteld.')}</dd><dt>Einde</dt><dd>${spEscape(s.continues_next_day?'Deze sessie loopt door na de gekozen dag.':s.ongoing?'Nog geen stop bevestigd.':s.stop_reason||(s.stop_confirmed?'Einde van de waargenomen activiteit; de stopoorzaak is niet vastgesteld.':'Geen stop bevestigd; de registratie eindigt bij de laatste betrouwbare waarneming.'))}</dd></dl></article>`;
      }).join(''):`<div class="empty">${x.has_data?'Geen actieve sessie geregistreerd voor deze dag.':'Voor deze dag is nog geen geschiedenis beschikbaar.'}</div>`}
      ${x.sessions_truncated?'<div class="notice">Oudste sessiedetails zijn niet meer volledig; de bewaarde dagtotalen blijven beschikbaar.</div>':''}
      ${x.task_sessions_truncated?'<div class="notice">Oudste taakperioden zijn niet meer volledig; de bewaarde dagtotalen per taak blijven beschikbaar.</div>':''}
      <details class="history-details" data-history-key="sg"><summary>SG-aanvraag, contact en ontvangst</summary><div class="sg-lanes">${Object.entries(sgNames).map(([key,name])=>{const lane=x.sg?.[key];return `<div class="sg-lane" data-sg-history="${key}"><strong>${name}</strong><span class="duration">${lane?.has_data&&lane.on_s!=null?this._duration(lane.on_s):'—'}</span><small>${lane?.has_data?`${this._duration(lane.known_s)} geregistreerd${lane.partial?' · onvolledig':''}`:'Geen betrouwbare registratie'}</small>${this._timeline(lane?.sessions||[],{lane:'sg-'+key,label:name+' van de gekozen dag'})}</div>`;}).join('')}</div><p>Dit zijn afzonderlijke waarnemingen. Een SG-aanvraag bewijst geen gesloten contact of ontvangst door Panasonic. Het gemeten verbruik hierboven is het totale warmtepompverbruik; extra verbruik door SG is niet vastgesteld.</p></details>
      ${this._nativeEvidenceHtml(x.native_evidence)}${this._electricalEvidenceHtml(x.electrical_activity)}
      <details class="history-details" data-history-key="coverage"><summary>Details en meetdekking</summary><p>Panasonic regelt de warmtepomp zelfstandig. Starts en stops tellen alleen bevestigde activiteitsovergangen; een meetgat of herstart telt niet als een stop. Bevestigd betekent een actuele native taak. Afgeleid combineert actueel compleet verbruik met een passende taakcontext. Alleen een gekozen stand bewijst geen actieve taak.</p><p>${this._duration(x.known_s)} activiteit geregistreerd · ${this._duration(x.unobserved_s)} onbekend. Verbruik is geïntegreerd over ${this._duration(x.energy_known_s)} betrouwbare volledige vermogensmetingen. Deelmetingen en meetgaten leveren geen verzonnen totaal of kWh op.</p>${(x.events||[]).map(e=>`<div class="event"><time>${spEscape(this._clock(e.at))}</time>${spEscape(e.reason)}</div>`).join('')}<p>${spEscape(x.note||'')} Registratie sinds ${spEscape(x.recording_since||'—')} · maximaal ${Number(x.retention_days)||30} dagen lokaal bewaard.</p></details>`;
    for(const d of this._body.querySelectorAll('details[data-history-key]'))d.open=opened.has(d.dataset.historyKey);
    this._syncScrub();
    this._readingsSignature=this._temperatureSignature();this._lastRenderedDay=x.date;this._scroll.scrollTop=scroll;
    if(focusedDetail){const detail=Array.from(this._body.querySelectorAll('details[data-history-key]')).find(el=>el.dataset.historyKey===focusedDetail);detail?.querySelector('summary')?.focus({preventScroll:true});}
    if(focusedLane){const lane=Array.from(this._body.querySelectorAll('[data-history-scrub]')).find(e=>e.dataset.historyScrub===focusedLane);lane?.focus({preventScroll:true});}
    if(focus){const b=Array.from(this._body.querySelectorAll('button')).find(b=>focus.day?b.dataset.day===focus.day:b.dataset.action===focus.action&&b.dataset.value===focus.value);b?.focus({preventScroll:true});}
  }
}
if(!customElements.get(SP_HEATPUMP_HISTORY_TAG))customElements.define(SP_HEATPUMP_HISTORY_TAG,SolarPilotHeatpumpHistoryDialog);

/* An explicit, admin-only download. No background export or upload to ChatGPT. */
class SolarPilotAnalysisDialog extends HTMLElement {
  constructor(){super();this.attachShadow({mode:'open'});this._seq=0;this._open=false;
    this.shadowRoot.innerHTML=`<style>:host{font-family:var(--paper-font-body1_-_font-family,system-ui,sans-serif);color:var(--primary-text-color,#eee)}*{box-sizing:border-box}[hidden]{display:none!important}dialog{width:min(640px,calc(100vw - 28px));max-height:90dvh;overflow:auto;border:1px solid var(--divider-color,#555);border-radius:18px;background:var(--card-background-color,#222);color:inherit;padding:22px}dialog::backdrop{background:#0009}header{display:flex;gap:12px;align-items:center}h2{font-size:22px;margin:0;flex:1}p{line-height:1.55;font-size:14px;color:var(--secondary-text-color,#aaa)}label{display:block;margin:18px 0;font-size:15px}select,button{font:inherit;color:inherit;background:var(--card-background-color,#222);border:1px solid var(--divider-color,#666);border-radius:10px;min-height:44px;padding:9px 12px}select{display:block;width:100%;margin-top:7px}input{min-width:20px;min-height:20px;vertical-align:middle;margin-right:7px}.download{background:var(--primary-color,#009bbd);color:white;font-weight:700;width:100%}.status{white-space:pre-wrap;overflow-wrap:anywhere}.note{border-left:3px solid var(--warning-color,#cf9c23);padding-left:12px}button:disabled{opacity:.5}.close{min-width:44px}button:focus-visible,select:focus-visible,input:focus-visible{outline:3px solid var(--primary-color,#009bbd)}</style>
      <dialog aria-labelledby="analysis-title"><header><h2 id="analysis-title">Analyse-export</h2><button class="close" aria-label="Analyse sluiten">×</button></header>
      <p>Download één gecomprimeerd analysebestand (.json.gz) met instellingen, start- en wachtredenen en alle beschikbare metingen. Ook zeven dagen blijven volledig behouden; compressie maakt het bestand kleiner.</p>
      <label hidden>Periode<select class="hours"><option value="1">Laatste uur</option><option value="24">Laatste 24 uur</option><option value="168" selected>Laatste 7 dagen</option></select></label>
      <label hidden><input type="checkbox" class="names">Echte entiteitsnamen en toestelnamen opnemen</label>
      <p class="note">Namen worden vervangen door consistente codes. Energie-, temperatuur- en gebruikspatronen blijven persoonlijke gegevens. Controleer het bestand voordat je het zelf in ChatGPT uploadt. SolarPilot verstuurt niets automatisch.</p>
      <details><summary>Welke geschiedenis is beschikbaar?</summary><p>Bestaande historie blijft behouden. Standaard wordt elke 5 minuten een meetpunt bewaard, maximaal 7 dagen. Nieuwe warmtepompdetails worden vanaf deze versie toegevoegd. De laatste maximaal 2 uur bevat daarnaast regelcycli met hogere resolutie zolang Home Assistant blijft draaien. Een onderbreking blijft een hiaat; ontbrekend verleden wordt niet ingevuld.</p><p>Actuele en lokaal opgeslagen modellen, dagkosten, toestelsessies, Wallbox, warm water, klimaat, PV, planning, batterijscenario’s, fasebewaking en SolarPilot-fouten zijn inbegrepen. Uitgeschakelde of niet gekoppelde onderdelen worden als zodanig aangeduid.</p></details>
      <p class="status" role="status" aria-live="polite"></p><button class="download">Analysebestand downloaden</button><button class="template" hidden disabled>Adviesrapport-sjabloon downloaden</button></dialog>`;
    this._dialog=this.shadowRoot.querySelector('dialog');
    this.shadowRoot.querySelector('.close').addEventListener('click',()=>this.close());
    this._dialog.addEventListener('cancel',ev=>{ev.preventDefault();this.close();});
    this._dialog.addEventListener('click',ev=>{if(ev.target===this._dialog){const b=this._dialog.getBoundingClientRect();if(ev.clientX<b.left||ev.clientX>b.right||ev.clientY<b.top||ev.clientY>b.bottom)this.close();}});
    this.shadowRoot.querySelector('.download').addEventListener('click',()=>this._download());
    this.shadowRoot.querySelector('.template').addEventListener('click',()=>this._downloadTemplate());
  }
  open(hass,entryId){this._hass=hass;this._entryId=entryId;this._template=null;this.shadowRoot.querySelector('.template').hidden=true;this._open=true;this._seq++;this.shadowRoot.querySelector('.status').textContent='';this.shadowRoot.querySelector('.download').disabled=!entryId||hass?.user?.is_admin!==true;this._dialog.showModal();}
  close(){if(this._dialog.open)this._dialog.close();this._open=false;this._seq++;}
  disconnectedCallback(){this.close();}
  _downloadTemplate(){if(!this._template)return;const blob=new Blob([JSON.stringify(this._template,null,2)],{type:'application/json;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='SolarPilot-adviesrapport-sjabloon.json';document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),30000);}
  async _download(){if(this._hass?.user?.is_admin!==true){this.shadowRoot.querySelector('.status').textContent='Meld je aan als beheerder om het analysebestand te downloaden.';return;}const n=++this._seq,b=this.shadowRoot.querySelector('.download'),status=this.shadowRoot.querySelector('.status'),hass=this._hass;let cleanupPath='';b.disabled=true;status.textContent='Analyse wordt samengesteld…';
    try{const answer=await hass.callWS({type:'solar_pilot/analysis_export',config_entry_id:this._entryId,hours:Number(this.shadowRoot.querySelector('.hours').value),include_names:this.shadowRoot.querySelector('.names').checked,download:true});
      if(answer.download_url&&/^\/api\/solar_pilot\/analysis\/[A-Za-z0-9_-]+$/.test(String(answer.download_url)))cleanupPath=String(answer.download_url);
      if(n!==this._seq||!this._open)return;
      if(answer.feedback_template?.schema==='solarpilot.analysis_feedback'){
        this._template=answer.feedback_template;const template=this.shadowRoot.querySelector('.template');template.hidden=false;template.disabled=false;
      }
      this.dispatchEvent(new CustomEvent('analysis-prepared',{detail:{source_export:answer.source_export,quality:answer.quality},bubbles:true,composed:true}));
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
if(!customElements.get(SP_ANALYSIS_DIALOG_TAG))customElements.define(SP_ANALYSIS_DIALOG_TAG,class extends SolarPilotAnalysisDialog {});

/* Bounded learning inbox: own shadow DOM, no device action or silent permission changes. */
class SolarPilotLearningDialog extends HTMLElement {
  constructor(){
    super();this.attachShadow({mode:'open'});this._seq=0;this._isOpen=false;this._busy=false;this._data=null;
    this.shadowRoot.innerHTML=`<style>${SP_INVESTIGATION_STYLE}
    :host{color:var(--primary-text-color,#e6edf5);font:14px/1.5 system-ui,sans-serif}*{box-sizing:border-box}dialog{color:inherit;background:var(--card-background-color,#1c1f24);border:1px solid var(--divider-color,#39434d);border-radius:18px;padding:0;width:min(940px,calc(100vw - 16px));max-width:none;max-height:calc(100dvh - 24px);overflow:hidden}dialog::backdrop{background:#0009}header{display:flex;gap:12px;padding:18px;border-bottom:1px solid var(--divider-color,#39434d);align-items:center}h2{font-size:21px;flex:1;margin:0}.scroll{padding:0 18px 22px;max-height:calc(100dvh - 180px);overflow:auto;overscroll-behavior:contain;scrollbar-gutter:stable}.status{padding:8px 18px;font-size:12px;min-height:34px}.error{color:var(--error-color,#ed7575)}.note,small{color:var(--secondary-text-color,#a7b0be);font-size:12px;display:block}button,select{font:inherit;color:inherit;border:1px solid var(--divider-color,#48515c);border-radius:9px;padding:8px 11px;background:var(--secondary-background-color,#292e35);min-height:40px;max-width:100%;cursor:pointer}button:disabled{opacity:.5;cursor:default}button:focus-visible,select:focus-visible,summary:focus-visible{outline:3px solid var(--primary-color,#00a0c6);outline-offset:2px}button.close{font-size:23px}.question,.model,.policy{padding:14px;border:1px solid var(--divider-color,#39434d);border-radius:13px;margin:12px 0}.question.attention{border-left:4px solid var(--warning-color,#e2b256)}.question h3,.model h3{font-size:16px;margin:0 0 8px}h3{font-size:16px}.actions{display:flex;flex-wrap:wrap;gap:8px}.question p,.model p{margin:7px 0 12px;overflow-wrap:anywhere}summary{font-weight:600;cursor:pointer;padding:8px 0}.inputs{display:grid;grid-template-columns:1fr 1fr;gap:12px}.inputs label{display:flex;flex-direction:column;gap:5px}.inputs select{width:100%;font-size:13px}label.notification{display:flex;flex-direction:row;gap:8px;align-items:center}.tablewrap{overflow:auto;margin:10px 0;border:1px solid var(--divider-color,#39434d);border-radius:8px}table{border-collapse:collapse;width:100%;font-size:12px}th,td{text-align:left;vertical-align:top;padding:8px;white-space:nowrap;border-bottom:1px solid var(--divider-color,#39434d)}pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:260px;overflow:auto;font-size:11px;background:var(--secondary-background-color,#292e35);padding:10px;border-radius:8px}.tag{display:inline-block;padding:2px 8px;border:1px solid var(--divider-color,#39434d);border-radius:20px;font-size:11px;margin:5px 0}.summary{padding:12px;border-left:3px solid var(--primary-color,#00a0c6);background:var(--secondary-background-color,#292e35);border-radius:10px}.audit{padding:8px 0;border-bottom:1px solid var(--divider-color,#39434d);overflow-wrap:anywhere;font-size:12px}@media(max-width:560px){header{padding:12px;gap:6px}h2{font-size:18px}.scroll{padding:0 12px 16px}.inputs{grid-template-columns:1fr}header button{font-size:12px;padding:8px}.question,.model,.policy{padding:11px}}
    </style><dialog aria-labelledby="learning-title"><header><h2 id="learning-title">Meetkwaliteit</h2><button class="refresh" aria-label="Meetkwaliteit vernieuwen">Vernieuwen</button><button class="close" aria-label="Meetkwaliteit sluiten">×</button></header><div class="status" role="status" aria-live="polite"></div><div class="scroll"><div class="body"></div></div></dialog>`;
    this._dialog=this.shadowRoot.querySelector('dialog');this._body=this.shadowRoot.querySelector('.body');this._scroll=this.shadowRoot.querySelector('.scroll');
    this.shadowRoot.querySelector('.close').onclick=()=>this.close();
    this.shadowRoot.querySelector('.refresh').onclick=()=>this._read(true);
    this._dialog.addEventListener('cancel',e=>{e.preventDefault();this.close();});
    this._dialog.addEventListener('click',e=>{if(e.target===this._dialog){const b=this._dialog.getBoundingClientRect();if(e.clientX<b.left||e.clientX>b.right||e.clientY<b.top||e.clientY>b.bottom)this.close();}});
    this._body.addEventListener('click',e=>this._click(e));
  }
  open(hass,entry){this._hass=hass;this._entry=entry;this._isOpen=true;this._busy=false;this._seq++;this._data=null;this._body.innerHTML='';if(!this._dialog.open)this._dialog.showModal();this._read();clearInterval(this._timer);this._timer=setInterval(()=>this._read(),60000);clearInterval(this._expiryTimer);this._expiryTimer=setInterval(()=>this._refreshInvestigationDisplay(),10000);}
  close(){this._isOpen=false;this._seq++;clearInterval(this._timer);this._timer=null;clearInterval(this._expiryTimer);this._expiryTimer=null;this._dialog.close();}
  disconnectedCallback(){this.close();}
  _status(text,error=false){const el=this.shadowRoot.querySelector('.status');el.textContent=text;el.classList.toggle('error',error);}
  _refreshInvestigationDisplay(){
    if(!this._isOpen||!this._data)return;
    const current=this._body.querySelector('.automatic-investigation');if(!current)return;
    const holder=document.createElement('div');holder.innerHTML=spInvestigationHtml(this._data.investigation,{current:this._data.ready===true,timeZone:this._hass?.config?.time_zone});
    const next=holder.firstElementChild;if(current.dataset.investigationCurrent===next?.dataset.investigationCurrent)return;
    const pos=this._scroll.scrollTop,opens=new Set(Array.from(current.querySelectorAll('details[open]'),d=>d.dataset.key));
    next.querySelectorAll('details').forEach(d=>d.open=opens.has(d.dataset.key));current.replaceWith(next);this._scroll.scrollTop=pos;
  }
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
    const policy=data.policy||{},q=data.quality?.last_7d||{},sam=data.sampling||{},counts=sam.attempts_7d||{},samplingStatus=sam.status||{};
    const models=(data.models||[]).filter(x=>x.id!=='climate'),pvEvidence=models.find(x=>x.id==='pv')?.evidence||{},baseEvidence=models.find(x=>x.id==='base')?.evidence||{},deviceEvidence=models.find(x=>x.id==='devices')?.evidence||{};
    const pvCalibration=pvEvidence.forecast_calibration||{},pvModel=pvCalibration.model||{},pvProfile=pvCalibration.calibration||{};
    const readable={'accepted':'Aanvaarde metingen','accepted_corrected':'Ook tijdens EV/lasten bruikbaar','site_source':'Net/PV-bron onbruikbaar','wallbox_source':'Wallboxmeting onbruikbaar','consumer_source':'Toestelmeting onbruikbaar','settling':'Wacht op stabilisatie','protected_dhw':'Beschermde boilerperiode apart','quiet_policy':'Overgeslagen door rustig-meetbeleid','source_alignment':'Tijdstempels niet passend','learning_disabled':'Leren uitgeschakeld','battery_source':'Batterijbron onbruikbaar','battery_fleet':'Batterijvloot niet gevalideerd','balance':'Energiebalans niet plausibel','sample_interval':'Vorige meting te recent'};
    this._body.innerHTML=`<p class="summary">Meetkwaliteit en bronherkomst. Bevindingen en adviezen beoordeel je via het analysebestand.</p><p class="note">${spEscape(data.contract||'Geen nieuwe fysieke rechten door deze pagina.')}</p>${spInvestigationHtml(data.investigation,{current:data.ready===true,timeZone:this._hass?.config?.time_zone})}
    <section class="model"><h3>Metingen</h3><p>Dekking: <b>${q.covered_hours==null?'nog onbekend':Number(q.covered_hours).toLocaleString('nl-BE')+' uur'}</b> · ${q.coverage_pct==null?'percentage nog onbekend':Number(q.coverage_pct).toLocaleString('nl-BE')+'% van de waargenomen periode'}.</p><div data-sampling-state="${spEscape(samplingStatus.state||'unknown')}"><p>${spEscape(samplingStatus.reason||sam.last?.reason||'Nog geen meetcontrole.')}</p>${samplingStatus.state==='transient_wait'?`<p class="note">Tijdelijke leerwacht${typeof samplingStatus.started_at==='number'?' vanaf '+spEscape(spProofClock(samplingStatus.started_at,this._hass?.config?.time_zone)):''}${typeof samplingStatus.ends_at==='number'?' tot '+spEscape(spProofClock(samplingStatus.ends_at,this._hass?.config?.time_zone)):''}${typeof samplingStatus.remaining_s==='number'?' · '+Math.max(0,Math.ceil(samplingStatus.remaining_s))+' s resterend':''}.</p>`:''}${samplingStatus.state==='excluded'?'<p class="note">Deze uitsluiting van basislastleren staat los van een korte stabilisatiewacht.</p>':''}</div><details data-key="coverage"><summary>Ontbrekende bronnen en technische meetdetails</summary><p class="note">${spEscape(q.coverage_note||'Oude meetdekking wordt niet achteraf ingevuld.')}</p>${sam.exclusions_7d?`<p data-learning-exclusions>Meetpogingen met stabilisatiewacht: ${spNumber(sam.exclusions_7d.settling_attempts)??0} · onbekende warmtepompcontext: ${spNumber(sam.exclusions_7d.heatpump_unknown_attempts)??0} · overige warmtepompcontext: ${spNumber(sam.exclusions_7d.other_heatpump_context_attempts)??0}.</p><p class="note">${spEscape(sam.exclusions_7d.note||'')}</p>`:''}<div class="tablewrap"><table><thead><tr><th>Leerwaarnemingen, laatste 7 kalenderdagen</th><th>Aantal</th></tr></thead><tbody>${Object.entries(counts).map(([key,n])=>`<tr><td>${spEscape(readable[key]||key)}</td><td>${Number(n)}</td></tr>`).join('')}</tbody></table></div></details></section>
    <section class="model"><h3>Zonnevoorspelling</h3><p>Gemiddelde fout bij zon: <b>${spPower(q.pv_daylight_mae_w)}</b>. Systematische richting: <b>${q.pv_daylight_bias_w==null?'onbekend':(q.pv_daylight_bias_w>=0?'forecast gemiddeld te laag '+spPower(q.pv_daylight_bias_w):'forecast gemiddeld te hoog '+spPower(Math.abs(q.pv_daylight_bias_w)))}</b>.</p><p>Lokale kalibratie: <b>${spNumber(pvProfile.days??pvCalibration.comparable_days)??'—'}/${spNumber(pvProfile.minimum_days_required??pvModel.minimum_days_required)??5} passende dagen</b> · ${spPct(spNumber(pvProfile.confidence??pvCalibration.confidence)==null?null:spNumber(pvProfile.confidence??pvCalibration.confidence)*100)} bewijs voor het huidige tijdvak. ${Number(pvModel.days||0)} leerdagen totaal.</p>${pvProfile.reason?`<p class="note">${spEscape(pvProfile.reason)}</p>`:''}<details data-key="pv-quality"><summary>Ochtend, middag en namiddag</summary><pre>${spEscape(JSON.stringify(pvModel.periods||{},null,2))}</pre></details></section>
    <section class="model"><h3>Huishoudelijk verbruik</h3><p>Voorspelfout gewone basislast: <b>${spPower(q.base_mae_w)}</b> · bias ${q.base_bias_w==null?'onbekend':(q.base_bias_w>=0?'+':'')+spPower(q.base_bias_w)}.</p><p class="note">Warmtepompperioden worden vanaf beta.36 niet meer als gewone huishoudelijke basislast gescoord of aangeleerd. Onverklaarde hoge pieken blijven apart.</p></section>
    <section class="model"><h3>Toestellen</h3><p>${Object.keys(deviceEvidence.profiles||{}).length} toestelprofiel(en) met eigen metingen. Faseherkenning en Wallbox-overdracht tonen afzonderlijk of bewijs betrouwbaar én voor regeling vrijgegeven is.</p><details data-key="device-quality"><summary>Technische toestelprofielen</summary><pre>${spEscape(JSON.stringify(deviceEvidence.profiles||{},null,2))}</pre></details></section>
    <h3>Wat kent SolarPilot al?</h3>${models.map(m=>`<article class="model"><h3>${spEscape(m.name)} <span class="tag">${m.enabled?'Leren / analyseren':'Niet actief'}</span></h3><p>${spEscape(m.state)}</p><p class="note">${spEscape(m.effect)}</p><details data-key="model-${spEscape(m.id)}"><summary>Meetbasis en herkomst</summary>${m.id==='base'?`<div class="tablewrap"><table><thead><tr><th>Uur/dagtype</th><th>Dagen</th><th>Herkomst</th><th>Voorspelling</th><th>Recente variant</th></tr></thead><tbody>${(m.evidence?.buckets||[]).map(b=>`<tr><td>${spEscape(b.bucket)}</td><td>${Number(b.days)}/${Number(b.minimum_days)}</td><td>${spEscape(b.source)}</td><td>${spPower(b.prediction_w)}</td><td>${b.candidate_applied?'Toegepast':b.candidate_eligible?'Beter; toestemming nodig':'Nog niet aangetoond'}</td></tr>`).join('')}</tbody></table></div>`:this._evidence(m)}</details></article>`).join('')}
    <details data-key="audit"><summary>Antwoorden en modelaanpassingen</summary>${(data.audit||[]).slice(-30).reverse().map(x=>`<div class="audit"><strong>${spEscape(x.time)}</strong> ${spEscape(x.event)}<pre>${spEscape(JSON.stringify(x.details,null,2))}</pre></div>`).join('')||'<p>Nog geen keuzes of adaptaties geregistreerd.</p>'}</details><p class="note">${spEscape(data.error||'Geen softwarezelfwijziging. Alle gegevens blijven lokaal en gaan alleen via een bewuste analyse-export naar buiten.')}</p>`;
    this._body.querySelectorAll('details').forEach(d=>d.open=opens.has(d.dataset.key));this._scroll.scrollTop=pos;
  }
  async _click(event){
    const b=event.target.closest('button');if(!b||this._busy)return;
    if(b.dataset.learningHelp){this.dispatchEvent(new CustomEvent('learning-help',{detail:b.dataset.learningHelp,bubbles:true,composed:true}));return;}

  }
}
if(!customElements.get('solar-pilot-learning-dialog'))customElements.define('solar-pilot-learning-dialog',SolarPilotLearningDialog);
if(!customElements.get(SP_QUALITY_DIALOG_TAG))customElements.define(SP_QUALITY_DIALOG_TAG,class extends SolarPilotLearningDialog {});

class SolarPilotPVDialog extends HTMLElement {
  static solarPilotRelease=SP_CARD_VERSION;
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
    this._dialog.addEventListener('close',()=>{if(!this._dialog.open){this._open=false;this._seq++;}});
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
  _forecastEvidenceHtml(e){
    if(e?.version!==1)return '<p class="hint">Vooruit geregistreerd voorspelbewijs is nog niet beschikbaar; eerdere actuele foutmetingen worden niet achteraf vooruitvoorspellingen.</p>';
    const summary=e.summary||{},margin=summary.planning_margin_comparison||{},buckets=Array.isArray(summary.by_recorded_lead)?summary.by_recorded_lead:[];
    const conditions={daylight:'Daglicht',night:'Nacht · zonnebron bevestigd',other_zero:'Nulproductie · dag/nacht niet bevestigd',unknown:'Omstandigheid onbekend'};
    const cohorts=summary.lead_cohort_evidence,cohortBuckets=cohorts?.version===1&&Array.isArray(cohorts.by_recorded_lead)?cohorts.by_recorded_lead:[];
    const row=(bucket,value,label)=>`<tr data-pv-condition="${spEscape(value.condition||'total')}"><td>${spEscape(String(bucket?.label||'Onbekend').slice(0,60))}</td><td>${spEscape(label)}</td><td>${spNumber(value.samples)??0}</td><td>${spNumber(value.unique_targets)==null?'—':spNumber(value.unique_targets)}</td><td>${spNumber(value.distinct_days)??0}</td><td>${spPower(value.mae_w)}</td><td>${spPower(value.bias_w)}</td></tr>`;
    return `<details data-pv-ahead-evidence data-pv-key="ahead"><summary>Werkelijk vooraf vastgelegde voorspellingen</summary><p>${spNumber(summary.ahead_comparisons)??0} vergelijkingen${spNumber(summary.unique_targets)!=null?' over '+spNumber(summary.unique_targets)+' unieke kwartieren':''} uit ${spNumber(summary.distinct_days)??0} dagen met lokaal vooraf vastgelegde waarden. De uitgiftetijd van de oorspronkelijke provider is onbekend.</p>${buckets.length?`<div class="table-wrap"><table><thead><tr><th>Lokaal vooraf vastgelegd</th><th>Meetreeks</th><th>Vergelijkingen</th><th>Unieke kwartieren</th><th>Dagen</th><th>Gemiddelde fout</th><th>Gemiddelde afwijking</th></tr></thead><tbody>${buckets.slice(0,6).map(b=>row(b,b,'Totaal')+(Array.isArray(b.conditions)?b.conditions:[]).slice(0,4).filter(v=>v&&Object.hasOwn(conditions,v.condition)).map(v=>row(b,v,conditions[v.condition])).join('')).join('')}</tbody></table></div>`:''}<p class="hint">Beoordeel daglicht afzonderlijk: vele nulwaarden in de nacht kunnen de totale fout klein laten lijken. Nulproductie zonder oorspronkelijke zonnebron is geen bewezen nacht.</p><p>Planningsmarge: ${margin.status==='comparison_only'?'alleen vergelijking':margin.status==='insufficient'?'nog onvoldoende bewijs':'onbekend'}${spNumber(margin.margin_w)!=null?' · '+spPower(margin.margin_w):''}. Niet toegepast.</p>${typeof margin.reason==='string'?`<p class="hint">${spEscape(margin.reason.slice(0,500))}</p>`:''}<p class="hint">Actuele voorspellingsfout en fout van vooraf vastgelegde waarden zijn verschillende meetreeksen. Dit onderzoek geeft geen extra startvermogen.</p>${cohortBuckets.length?`<section data-pv-lead-cohorts><h4>Afzonderlijke reeksen per vooruitkijktermijn</h4><p>${spEscape(cohorts.selection_reason||'Eerste geldige voorspelling per doel en termijn; daarna vast.')}.</p><p>${spNumber(cohorts.unique_targets)??0} unieke doelkwartieren · ${spNumber(cohorts.distinct_days)??0} verschillende dagen · ${spNumber(cohorts.pending_selections)??0} vastgelegde voorspellingen wachten op een meting.</p><div class="table-wrap"><table><thead><tr><th>Termijn</th><th>Meetreeks</th><th>Vergelijkingen</th><th>Unieke doelen</th><th>Dagen</th><th>Gemiddelde fout</th><th>Gemiddelde afwijking</th></tr></thead><tbody>${cohortBuckets.slice(0,3).map(b=>row(b,b,'Totaal')+(Array.isArray(b.conditions)?b.conditions:[]).filter(v=>v?.condition==='daylight').map(v=>row(b,v,'Daglicht')).join('')).join('')}</tbody></table></div><p class="hint">${spEscape(cohorts.dependency_reason||'De reeksen delen dezelfde oorspronkelijke metingen.')} Oude voorspellingen worden hiervoor niet achteraf ingevuld.</p></section>`:''}</details>`;
  }
  _quarterEvidenceHtml(e,quarterKey){
    if(e?.version!==1)return '<small>Oud kwartier zonder oorspronkelijk deelmeetbewijs.</small>';
    const original=e.original_reports||{},reasons=Array.isArray(e.rejection_reasons)?e.rejection_reasons:[],names={invalid:'Ongeldige meting',stale:'Verouderd rapport',duplicate:'Herhaald rapport',conflicting:'Tegenstrijdig rapport',source_alignment:'Tijdsafstemming',missing:'Ontbrekend rapport'};
    const timeQuality=original.time_quality,timeLabels={valid:'geldig',unknown:'onbekend',missing:'ontbrekend',zero_sentinel:'nulwaarde als ontbrekende brontijd',invalid:'ongeldig'};
    const times=timeQuality&&typeof timeQuality==='object'?Object.entries(timeLabels).filter(([key])=>spNumber(timeQuality[key])!=null).map(([key,label])=>`${spNumber(timeQuality[key])} ${label}`).join(' · '):'';
    return `<details data-quarter-proof data-pv-key="quarter:${spEscape(String(quarterKey||'unknown').slice(0,80))}"><summary>Oorspronkelijke deelmetingen</summary><p>${spNumber(e.valid_observations)??0} geldig · ${spNumber(e.rejected_observations)??0} afgewezen · ${spNumber(original.distinct)??0} verschillende bronrapporten.</p><p>Grootste oorspronkelijke rapportafstand: ${spNumber(original.max_gap_s)==null?'onbekend':spEscape(String(original.max_gap_s)+' s')}.</p>${times?`<p data-source-time-quality>Brontijden: ${spEscape(times)}.</p>`:''}${reasons.length?`<ul>${reasons.slice(0,8).map(r=>`<li>${spEscape(names[r?.reason]||String(r?.reason||'Onbekende reden').slice(0,80))}: ${spNumber(r?.count)??0}</li>`).join('')}</ul>`:''}${typeof e.coverage_note==='string'?`<p>${spEscape(e.coverage_note.slice(0,500))}</p>`:''}</details>`;
  }
  _renderData(){
    const top=this._scroll.scrollTop,opened=new Set(Array.from(this._body.querySelectorAll('details[open][data-pv-key]'),x=>x.dataset.pvKey)),d=this._data||{},s=d.summary||{},m=s.model||{},rows=(d.history||[]).filter(r=>String(r.time).slice(0,10)===this._days.value),f=x=>x==null?'—':Number(x).toLocaleString('nl-BE',{maximumFractionDigits:2});
    this._body.innerHTML=`<div class="box"><h3>${spEscape(s.status||'Geen gegevens')}</h3><p class="hint">${spEscape(s.note||'Alleen voorspellend; de actuele net- en PV-meters blijven leidend.')}</p>${s.warning||s.error?`<p class="warning">${spEscape(s.warning||s.error)}</p>`:''}<div class="metrics"><div class="metric"><small>Leerdagen totaal</small><strong>${Number(m.days||0)}</strong></div><div class="metric"><small>Factor nu · ${Number(s.calibration?.days??s.comparable_days??0)} vergelijkbare dagen</small><strong>× ${f(s.factor)}</strong></div><div class="metric"><small>Lokale correctiezekerheid</small><strong>${s.confidence==null?'—':Math.round(s.confidence*100)+'%'}</strong></div><div class="metric"><small>Kwartieren gebruikt / geweigerd</small><strong>${Number(m.accepted||0)} / ${Number(m.rejected||0)}</strong></div><div class="metric"><small>Afwijking gecorrigeerd bij zon</small><strong>${spPower(m.mae_w)}</strong></div><div class="metric"><small>AC-omvormer / DC-panelen</small><strong>${spPower(s.inverter_limit_w)}</strong><small>${f(Number(s.panel_peak_wp||0)/1000)} kWp</small></div></div><p class="hint">${spEscape(m.last_reason||'Nog geen volledige meetperiode')}. Het dagenaantal is geen garantie; voor elk zonnestandvak is afzonderlijk bewijs nodig.</p></div>
      <div class="box"><h3>Vooruitkijken, geen vrij vermogen</h3><div class="table-wrap"><table><thead><tr><th>Moment</th><th>Forecast.Solar ruw</th><th>SolarPilot gecorrigeerd</th><th>Factor</th><th>Meetbasis voor dit moment</th></tr></thead><tbody>${(s.horizon||[]).map(r=>`<tr><td>${r.hours?'+'+Number(r.hours)+' uur':'Nu'}</td><td>${spPower(r.raw_w)}</td><td><strong>${spPower(r.corrected_w)}</strong></td><td>× ${f(r.factor)}</td><td>${Number(r.calibration?.days??r.days??0)} / ${Number(r.calibration?.minimum_days_required??s.minimum_days_required??5)} passende dagen<br>${spEscape(r.calibration?.reason||r.source||'Meetbasis nog onbekend')}</td></tr>`).join('')}</tbody></table></div><p>Vandaag resterend: <b>${spKwh(s.raw_remaining_today_kwh)} → ${spKwh(s.corrected_remaining_today_kwh)}</b></p><p class="hint">${spEscape(s.energy_methods?.remaining_today||'Geen volledige energiedekking')}. Morgen: ${spKwh(s.corrected_tomorrow_kwh)}. Een streepje is onbekend, geen nulproductie.</p></div>
      ${(d.quarter_profile?.quarters||[]).length?`<div class="box pv-quarter-profile"><h3>Namiddagprofiel · 15–18 uur · ${spEscape(d.quarter_profile.day||'')}</h3><p class="hint">Actueel model per kwartier. Passende leerdagen horen bij dit tijdvak en seizoen. Een kandidaat-overgang verandert de factor pas na herhaald, volledig meetbewijs.</p><div class="table-wrap"><table><thead><tr><th>Vanaf</th><th>Ruw / gecorrigeerd</th><th>Factor</th><th>Passende dagen</th><th>Overgangsmetingen</th><th>Waarom deze factor?</th></tr></thead><tbody>${d.quarter_profile.quarters.map(r=>`<tr><td>${spEscape(String(r.time).slice(11,16))}</td><td>${spPower(r.raw_w)} / ${spPower(r.corrected_w)}</td><td>× ${f(r.factor)}</td><td>${Number(r.calibration?.days||0)} / ${Number(r.calibration?.minimum_days_required||5)}</td><td>${Number(r.calibration?.edge_candidate_days||0)} / ${Number(r.calibration?.minimum_days_required||5)} dagen<br>${spEscape(({none:'nog geen patroon',pending:'verzamelen',inconsistent:'wisselend patroon',trusted:'herhaald patroon'})[r.calibration?.edge_candidate_state]||'nog geen patroon')}</td><td>${spEscape(r.calibration?.reason||'Geen actuele meetbasis')}</td></tr>`).join('')}</tbody></table></div></div>`:''}
      ${this._forecastEvidenceHtml(d.forecast_evidence)}<p class="hint">${spEscape(s.curve_method||'')} · Native nu-sensor: ${spPower(s.native_raw_now_w)}.</p><div class="box"><h3>Diagnose per kwartier · ${spEscape(this._days.value||'nog geen gegevens')}</h3>${rows.length?this._chart(rows):'<p class="hint">Registratie begint na installatie. De eerste tien minuten worden niet geleerd; daarna zijn volledige kwartieren nodig.</p>'}<div class="table-wrap"><table class="history"><thead><tr><th>Tijd</th><th>Ruw</th><th>Gecorrigeerd</th><th>Werkelijk</th><th>Fout ruw</th><th>Factor</th><th>Leerbesluit</th></tr></thead><tbody>${rows.slice().reverse().map(r=>`<tr><td>${spEscape(String(r.time).slice(11,16))}</td><td>${spPower(r.raw_w)}</td><td>${spPower(r.corrected_w)}</td><td>${spPower(r.actual_w)}</td><td>${r.error_w==null?'—':f(r.error_w)+' W'}<br>${r.error_pct==null?'—':f(r.error_pct)+'%'}</td><td>${f(r.factor)}</td><td class="${r.accepted?'good':'muted'}">${spEscape(r.reason)}${this._quarterEvidenceHtml(r.observation_evidence,r.time)}</td></tr>`).join('')}</tbody></table></div></div>
      <details data-pv-key="sources"><summary>Bronnen, instellingen en beperkingen</summary><pre>${spEscape(JSON.stringify({bronnen:d.sources,forecast_solar:d.source_metadata,gevonden:d.candidate_sources,instellingen:d.settings},null,2))}</pre>${(d.limitations||[]).map(x=>`<p class="hint">${spEscape(x)}</p>`).join('')}</details>`;
    this._body.querySelectorAll('details[data-pv-key]').forEach(x=>x.open=opened.has(x.dataset.pvKey));this._scroll.scrollTop=top;
  }
}
if(!customElements.get('solar-pilot-pv-dialog'))customElements.define('solar-pilot-pv-dialog',SolarPilotPVDialog);
if(!customElements.get(SP_PV_DIALOG_TAG))customElements.define(SP_PV_DIALOG_TAG,class extends SolarPilotPVDialog {});

/* Stable draft editor. Telemetry updates replace the context, never its DOM. */
class SolarPilotPriorityDialog extends HTMLElement {
  static solarPilotRelease=SP_CARD_VERSION;
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
if(!customElements.get(SP_PRIORITY_DIALOG_TAG))customElements.define(SP_PRIORITY_DIALOG_TAG,class extends SolarPilotPriorityDialog {});

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
  view(view){if(!['overview','loads','comfort','water','planning','energy','storage','priorities','export','guide'].includes(view)||view===this.card._view)return;this.prepare();this.card._view=view;this.card._renderSignature='';this.card._render();this._push();}
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
  _canClose(keys){for(const key of [...keys].reverse()){const e=this.modals.get(key)?.element;if(!(e?.dialog||e?._dialog)?.open)continue;if(e._saving||(e.localName==='solar-pilot-options-dialog'&&e._busy||e.localName?.startsWith('solar-pilot-options-dialog-')&&e._busy))return false;if((e._dirty||e._draftStarted)&&!window.confirm('Niet-opgeslagen wijzigingen weggooien?'))return false;}return true;}
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

/* A duration choice is a policy request. It never writes a device or relay. */
class SolarPilotWallboxPriorityDialog extends HTMLElement {
  static solarPilotRelease=SP_CARD_VERSION;
  constructor(){
    super();this.attachShadow({mode:'open'});this._busy=false;
    this.shadowRoot.innerHTML=`<style>:host{font-family:var(--paper-font-body1_-_font-family,system-ui,sans-serif);color:var(--primary-text-color,#202735)}*{box-sizing:border-box}dialog{color:inherit;background:var(--card-background-color,#fff);border:1px solid var(--divider-color,#dce1e7);border-radius:18px;padding:20px;width:min(480px,94vw);max-height:92dvh;overflow:auto}dialog::backdrop{background:#0008}header{display:flex;align-items:start;gap:12px}header>div{flex:1;min-width:0}h2{font-size:20px;line-height:1.35;margin:0;overflow-wrap:anywhere}p{font-size:13px;line-height:1.55}button{font:inherit;color:inherit;cursor:pointer;min-width:44px;min-height:44px;padding:10px;border:1px solid var(--divider-color,#dce1e7);border-radius:10px;background:var(--card-background-color,#fff);overflow-wrap:anywhere}button:focus-visible{outline:3px solid var(--primary-color,#287c59);outline-offset:2px}button:disabled{opacity:.45;cursor:default}.choices{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.choices button:last-child{grid-column:1/-1}.choices button[aria-pressed=true]{background:var(--primary-color,#287c59);color:var(--text-primary-color,#fff)}.status{min-height:20px}.error{color:var(--error-color,#b3261e)}@media(max-width:360px){dialog{padding:14px}h2{font-size:18px}}</style><dialog aria-labelledby="wallbox-priority-duration-title"><header><div><h2 id="wallbox-priority-duration-title">Wallbox voorrang geven</h2><p data-target-label></p></div><button type="button" data-close aria-label="Looptijd kiezen sluiten">✕</button></header><p>Kies hoelang de Wallbox voorrang krijgt.</p><div class="choices">${SP_WALLBOX_PRIORITY_OPTIONS.map(([value,label])=>`<button type="button" data-priority-option="${value}" aria-pressed="false">${label}</button>`).join('')}</div><p data-policy-note></p><p class="status" role="status" aria-live="polite"></p></dialog>`;
    this.dialog=this.shadowRoot.querySelector('dialog');
    this.dialog.addEventListener('cancel',e=>{e.preventDefault();this.close();});
    this.shadowRoot.addEventListener('click',e=>{const b=e.target.closest('button');if(!b||b.disabled)return;if(b.hasAttribute('data-close'))return this.close();if(b.dataset.priorityOption)this._choose(b.dataset.priorityOption);});
  }
  open(card,target,label){
    this.dataset.wallboxPriorityDialog='';
    this._card=card;this._target=target;this._label=label;this._opener=card.shadowRoot.activeElement;this._busy=false;this._saving=false;
    this.shadowRoot.querySelector('[data-target-label]').textContent=label;
    this.shadowRoot.querySelector('[data-policy-note]').textContent=target==='global'?'Geldt voor alle beschikbare toestellen. Je kunt elk toestel daarna afzonderlijk aanpassen. Automatisch herstelt overal de bewaarde voorrangsregels.':'Alleen de verdeling met autoladen verandert. Bij Automatisch gelden opnieuw de bewaarde voorrangsregels.';
    this._message('');if(!this.dialog.open)this.dialog.showModal();this.update();
  }
  update(){
    if(!this.dialog.open)return;
    const choice=this._card?._wallboxPriorityChoice(this._card._ctx(),this._target),admin=this._card?._hass?.user?.is_admin===true;
    this.shadowRoot.querySelectorAll('[data-priority-option]').forEach(b=>{b.disabled=this._busy||!admin||choice?.eligible!==true;b.setAttribute('aria-pressed',String(choice?.active===true&&b.dataset.priorityOption===choice.option));});
    this.shadowRoot.querySelector('[data-close]').disabled=this._busy;
  }
  _message(message,error=false){const node=this.shadowRoot.querySelector('.status');node.textContent=message;node.classList.toggle('error',error);}
  async _choose(option){
    if(this._busy||!SP_WALLBOX_PRIORITY_OPTIONS.some(([key])=>key===option))return;
    this._busy=true;this._saving=true;this.update();this._message('Voorrang versturen…');
    const accepted=await this._card._setWallboxPriority(this._target,option);
    this._busy=false;this._saving=false;this.update();if(accepted)this.close();else this._message('De keuze is niet bevestigd. Controleer de actuele status voordat je opnieuw kiest.',true);
  }
  close(force=false){if(this._busy&&!force)return false;this.dialog.close();const opener=this._opener?.isConnected?this._opener:Array.from(this._card?._content?.querySelectorAll('[data-action=wallbox_priority_toggle]')||[]).find(b=>b.dataset.priorityTarget===this._target);opener?.focus?.({preventScroll:true});return true;}
  disconnectedCallback(){this.close(true);}
}
if(!customElements.get(SP_WALLBOX_PRIORITY_DIALOG_TAG))customElements.define(SP_WALLBOX_PRIORITY_DIALOG_TAG,SolarPilotWallboxPriorityDialog);

class SolarPilotCard extends HTMLElement {
  constructor(){
    super(); this.attachShadow({mode:"open"}); this._busy=false; this._error=""; this._feedback=""; this._view="overview"; this._renderSignature=""; this._lastRenderedView="";
    this._content=document.createElement("div");this.shadowRoot.appendChild(this._content);this._uiHistory=new SolarPilotUiHistory(this);
    this.shadowRoot.addEventListener("click",ev=>this._click(ev));
    this.shadowRoot.addEventListener("change",ev=>this._change(ev));
  }
  setConfig(config){ this._invalidateSgManualRequest();this._invalidateWallboxPriorityRequest();this._config=config||{}; this._entity=this._config.entity; this._view=this._config.default_view||"overview"; this._last=null; }
  set hass(hass){
    const previousUser=this._hass?.user;
    this._hass=hass;
    const userChanged=previousUser&&(previousUser.id!==hass.user?.id||previousUser.is_admin!==hass.user?.is_admin);
    if(userChanged){this._historyDialog?.close();this._sourceHistoryDialog?.close();this._waterHistoryDialog?.close();this._nativeHistorySeq=(this._nativeHistorySeq||0)+1;this._invalidateWallboxPriorityRequest();this._invalidateSgManualRequest();this._heatpumpHistoryDialog?.close();this._analysisFeedbackReport=null;this._analysisFeedbackEntry='';this._analysisFeedbackSeq=(this._analysisFeedbackSeq||0)+1;this._analysisFeedbackReadSeq=(this._analysisFeedbackReadSeq||0)+1;this._analysisFeedbackBusy=false;this._analysisFeedbackReading=false;}
    if(this._optionsDialog)this._optionsDialog.hass=hass;
    if(this._priorityDialog)this._priorityDialog.hass=hass;
    if(!this._entity || !hass.states[this._entity]) this._entity=this._config?.entity || Object.keys(hass.states).find(id=>hass.states[id].attributes?.solar_pilot===true);
    const state=hass.states[this._entity];
    if(state===this._last&&!userChanged) return;
    if(this._last?.attributes?.config_entry_id!==state?.attributes?.config_entry_id){this._invalidateWallboxPriorityRequest();this._invalidateSgManualRequest();this._analysisFeedbackReport=null;this._analysisFeedbackEntry='';this._analysisFeedbackSeq=(this._analysisFeedbackSeq||0)+1;this._analysisFeedbackReadSeq=(this._analysisFeedbackReadSeq||0)+1;this._analysisFeedbackBusy=false;this._analysisFeedbackReading=false;}
    this._last=state;
    this._anchorWallboxPriorityClock();this._wallboxPriorityDialog?.update();
    if(this._deviceManager){this._deviceManager.hass=hass;this._deviceManager.update(state?.attributes?.device_management);}
    this._historyDialog?.setContext(hass,this._device(this._historyDialog._deviceId),state?.attributes?.config_entry_id);
    this._sourceHistoryDialog?.updateContext(hass,state?.attributes?.config_entry_id);
    this._heatpumpHistoryDialog?.setContext(hass,this._heatpumpHistoryDevice(this._ctx()),state?.attributes?.config_entry_id);
    this._waterHistoryDialog?.setContext(hass,{id:'water',history:{revision:state?.attributes?.water?.revision}},state?.attributes?.config_entry_id);
    if(!userChanged&&["INPUT","SELECT","TEXTAREA"].includes(this.shadowRoot.activeElement?.tagName)) return;
    const signature=this._viewRenderSignature();
    if(!userChanged&&signature && signature===this._renderSignature) return;
    this._render();
  }
  connectedCallback(){this._uiHistory.connect();clearInterval(this._observationTimer);this._observationTimer=setInterval(()=>this._refreshObservationDisplay(),10000);clearInterval(this._wallboxPriorityTimer);this._wallboxPriorityTimer=setInterval(()=>this._refreshWallboxPriorityClocks(),1000);}
  disconnectedCallback(){this._invalidateWallboxPriorityRequest();clearInterval(this._wallboxPriorityTimer);this._wallboxPriorityTimer=null;this._invalidateSgManualRequest();clearInterval(this._observationTimer);this._observationTimer=null;this._uiHistory.disconnect();this._priorityDialog?.close(true);this._deviceManager?.close();this._pvDialog?.close();this._learningDialog?.close();this._analysisDialog?.close();this._historyDialog?.close();this._sourceHistoryDialog?.close();this._waterHistoryDialog?.close();this._nativeHistorySeq=(this._nativeHistorySeq||0)+1;this._heatpumpHistoryDialog?.close();this._helpDialog?.close();this._optionsDialog?.close(true);}
  _activityObservationsCurrent(){return this._last?.attributes?.restored!==true&&typeof this._last?.state==='string'&&!!this._last.state&&!['unknown','unavailable'].includes(this._last.state.toLowerCase());}
  _refreshObservationDisplay(){
    if(!this.isConnected)return;
    this.shadowRoot.querySelector('ha-card')?.setAttribute('data-observations-current',String(this._activityObservationsCurrent()));
    if(document.visibilityState==='hidden')return;
    if(this._view==='export'){
      const current=this._content.querySelector('.automatic-investigation');if(!current)return;
      const holder=document.createElement('div');holder.innerHTML=this._investigationHtml(this._ctx());
      const next=holder.firstElementChild;if(current.dataset.investigationCurrent===next?.dataset.investigationCurrent)return;
      const state=this._captureUiState();current.replaceWith(next);this._restoreUiState(state);return;
    }
    if(!['overview','comfort','loads','water'].includes(this._view))return;
    const c=this._ctx();
    if(this._view==='water'){
      const current=this._content.querySelector('[data-water-panel]');if(current){const state=this._captureUiState(),holder=document.createElement('div');holder.innerHTML=this._water(c);current.replaceWith(holder.firstElementChild);this._restoreUiState(state);}return;
    }
    if(this._view==='overview'){
      const water=this._content.querySelector('[data-water-summary]');if(water){const holder=document.createElement('div');holder.innerHTML=this._waterSummary(c);water.replaceWith(holder.firstElementChild);}
      const tiles=['pv','grid'].map(kind=>[kind,this._energyTile(kind,c.a)]),energySignature=JSON.stringify(tiles);
      if(energySignature!==this._energyDisplaySignature){
        for(const [kind,html] of tiles){const current=this._content.querySelector(`[data-energy="${kind}"]`);if(!current)continue;const holder=document.createElement('div');holder.innerHTML=html;current.replaceWith(holder.firstElementChild);}
        this._energyDisplaySignature=energySignature;
      }
    }
    const signature=JSON.stringify([this._heatpumpDisplaySignature(c),this._wallboxActivity(c.wb||{})]);
    if(signature===this._observationSignature)return;
    // Update only the read-only observation block, keeping other device drafts,
    // focused controls, open explanations and modal DOM intact.
    const uiState=this._captureUiState(),holder=document.createElement('div');
    if(this._view==='overview'){
      holder.innerHTML=this._decisionBoard(c);
      for(const key of ['overview:sg','overview:wallbox']){
        const current=this._content.querySelector(`[data-reason-key="${key}"]`),next=holder.querySelector(`[data-reason-key="${key}"]`);
        if(current&&next)current.replaceWith(next);
      }
      const active=this._content.querySelector('.active-loads');if(active){const block=document.createElement('div');block.innerHTML=this._activeLoads(c);active.replaceWith(block.firstElementChild);}
    }else{
      const current=this._content.querySelector('.heatpump-sg');
      holder.innerHTML=this._heatpump(c,this._view);
      const next=holder.firstElementChild;
      if(current&&next){current.replaceWith(next);this._installHelpButtons(next);}
      if(this._view==='loads'){
        const wallbox=this._content.querySelector('.wallbox-device');
        if(wallbox){const block=document.createElement('div');block.innerHTML=this._wallbox(c);const replacement=block.querySelector('.wallbox-device');if(replacement)wallbox.replaceWith(replacement);}
      }
    }
    this._restoreUiState(uiState);this._observationSignature=signature;
  }
  _openPV(){
    this._uiHistory.prepare();
    if(!this._pvDialog){this._pvDialog=document.createElement(spDialogTag('solar-pilot-pv-dialog',SP_PV_DIALOG_TAG));this.shadowRoot.appendChild(this._pvDialog);this._pvDialog.addEventListener('pv-export',()=>{this._pvDialog.close();this._goExport();});}
    this._pvDialog.open(this._hass,this._last?.attributes?.config_entry_id);this._uiHistory.track(this._pvDialog,()=>this._pvDialog.open(this._hass,this._last?.attributes?.config_entry_id));
  }
  _pvSummary(c){
    const p=c.ems.pv_forecast||{},rows=p.horizon||[];
    return `<section class="pv-summary"><div class="sectionhead"><div><h2>Zon & voorspelling</h2><p>${spEscape(p.status||'Nog geen Forecast.Solar-gegevens')}</p></div><button type="button" class="mini" data-action="pv_diagnostics">PV-diagnose</button></div>${p.warning?this._notice(spEscape(p.warning),true):''}<div class="summarygrid">${rows.map(r=>this._tile(r.hours?'Over '+r.hours+' uur':'Verwacht nu',spPower(r.corrected_w),p.show_raw!==false?'Forecast.Solar ruw: '+spPower(r.raw_w)+' · factor ×'+Number(r.factor??1).toLocaleString('nl-BE')+(r.calibration?' · '+Number(r.calibration.days||0)+'/'+Number(r.calibration.minimum_days_required||5)+' passende dagen':''):'Lokale correctie; niet het actuele overschot')).join('')}${this._tile('Vandaag resterend',spKwh(p.corrected_remaining_today_kwh),'energieverwachting; geen meting')}${this._tile('PV-leerdagen totaal',Number(p.model?.days||0)+' dagen',p.calibration?.reason||p.model?.last_reason||'Wachten op bruikbare kwartiermetingen')}</div><p class="note">${Number(p.panel_peak_wp||0).toLocaleString('nl-BE')} Wp panelen en een AC-limiet zijn verschillende grootheden. De ingestelde grens staat in PV-diagnose. Clipping wordt niet als schaduw geleerd. Realtime verbruik blijft op echte meters geregeld.</p></section>`;
  }
  _openLearning(){
    this._uiHistory.prepare();
    if(!this._learningDialog){this._learningDialog=document.createElement(SP_QUALITY_DIALOG_TAG);this.shadowRoot.appendChild(this._learningDialog);this._learningDialog.addEventListener('learning-help',e=>this._openHelp('learning_hub',e.detail,'Uitleg leerbeleid'));this._learningDialog.addEventListener('learning-navigation',e=>{this._learningDialog.close();if(e.detail==='export')this._goExport();else if(e.detail==='configure')this._openOptions();});}
    this._learningDialog.open(this._hass,this._last?.attributes?.config_entry_id);this._uiHistory.track(this._learningDialog,()=>this._learningDialog.open(this._hass,this._last?.attributes?.config_entry_id));
  }
  _openAnalysis(download=false){
    this._uiHistory.prepare();
    if(!this._analysisDialog){this._analysisDialog=document.createElement(SP_ANALYSIS_DIALOG_TAG);this.shadowRoot.appendChild(this._analysisDialog);this._analysisDialog.addEventListener('analysis-prepared',e=>{this._analysisExportMeta=e.detail;});}
    this._analysisDialog.open(this._hass,this._last?.attributes?.config_entry_id);this._uiHistory.track(this._analysisDialog,()=>this._analysisDialog.open(this._hass,this._last?.attributes?.config_entry_id));if(download)this._analysisDialog._download();
  }
  _openHistory(device){
    this._nativeHistorySeq=(this._nativeHistorySeq||0)+1;
    this._uiHistory.prepare();
    if(!this._historyDialog){
      this._historyDialog=document.createElement(spDialogTag('solar-pilot-consumer-history-dialog',SP_CONSUMER_HISTORY_TAG));this.shadowRoot.appendChild(this._historyDialog);
      this._historyDialog.addEventListener('source-history',e=>this._openSourceHistory(e.detail.kind,e.detail.item_id));
      this._historyDialog.addEventListener('history-closed',()=>requestAnimationFrame(()=>{
        if(this.isConnected&&!this._historyDialog._isOpen){const b=Array.from(this.shadowRoot.querySelectorAll('button[data-action=history]')).find(b=>b.dataset.id===this._historyDialog._deviceId);b?.focus({preventScroll:true});}
      }));
    }
    this._historyDialog.open(this._hass,this._last?.attributes?.config_entry_id,device);this._uiHistory.track(this._historyDialog,()=>this._historyDialog.open(this._hass,this._last?.attributes?.config_entry_id,this._device(device.id)||device));
  }
  _sourceHistoryButton(kind,itemId,label='Bronhistorie in Home Assistant'){return `<button type="button" class="mini" data-action="source_history" data-history-kind="${spEscape(kind)}"${itemId!=null?` data-id="${spEscape(itemId)}"`:''} style="max-width:100%;white-space:normal" ${this._last?.attributes?.config_entry_id?'':'disabled'}>${spEscape(label)}</button>`;}
  _openWaterHistory(){
    this._nativeHistorySeq=(this._nativeHistorySeq||0)+1;this._uiHistory.prepare();
    if(!this._waterHistoryDialog){this._waterHistoryDialog=document.createElement(SP_WATER_HISTORY_TAG);this._waterHistoryDialog.dataset.waterHistoryDialog='';this.shadowRoot.append(this._waterHistoryDialog);this._waterHistoryDialog.addEventListener('source-history',()=>this._openSourceHistory('water'));this._waterHistoryDialog.addEventListener('history-closed',()=>requestAnimationFrame(()=>{if(this.isConnected&&!this._waterHistoryDialog._isOpen)this.shadowRoot.querySelector('[data-action=water_history]')?.focus({preventScroll:true});}));}
    const open=()=>this._waterHistoryDialog.open(this._hass,this._last?.attributes?.config_entry_id,{id:'water',name:'Huishoudelijke watermeter',reason:'Alleen gemeten watergegevens; geen toestelbediening.'});open();this._uiHistory.track(this._waterHistoryDialog,open);
  }
  _openSourceHistory(kind,itemId,options={}){
    const entryId=this._last?.attributes?.config_entry_id;if(!entryId||!['consumer','battery','wallbox','heatpump','water'].includes(kind))return;
    if(kind==='heatpump'&&(!['display_tank','configured'].includes(options.source)||!['tank_temperature_entity','tank_target_entity'].includes(options.role)||typeof options.expectedEntity!=='string'||!/^[a-z0-9_]+\.[a-z0-9_]+$/.test(options.expectedEntity)))return;
    this._nativeHistorySeq=(this._nativeHistorySeq||0)+1;
    this._historyDialog?.close();this._heatpumpHistoryDialog?.close();this._waterHistoryDialog?.close();this._uiHistory.prepare();
    if(!this._sourceHistoryDialog){this._sourceHistoryDialog=document.createElement(SP_SOURCE_HISTORY_TAG);this._sourceHistoryDialog.dataset.sourceHistoryDialog='';this.shadowRoot.append(this._sourceHistoryDialog);this._sourceHistoryDialog.addEventListener('source-history-open',e=>this._openNativeSourceHistory(e.detail));}
    const open=()=>this._sourceHistoryDialog.open(this._hass,this._last?.attributes?.config_entry_id,kind,itemId,options);open();this._uiHistory.track(this._sourceHistoryDialog,open);
  }
  async _openNativeSourceHistory(detail){
    const dialog=this._sourceHistoryDialog;if(!detail||detail.entryId!==this._last?.attributes?.config_entry_id||detail.userKey!==dialog?._userKey()||!dialog?.permits(detail.entityId))return;
    const seq=this._nativeHistorySeq=(this._nativeHistorySeq||0)+1,entryId=detail.entryId,userKey=detail.userKey;dialog.close();this._historyDialog?.close();this._waterHistoryDialog?.close();
    const until=Date.now()+2000;while(SolarPilotUiHistory.bus.pending||SolarPilotUiHistory.bus.moving||SolarPilotUiHistory.bus.applying){if(Date.now()>until)return;await new Promise(resolve=>requestAnimationFrame(resolve));}
    if(!this.isConnected||seq!==this._nativeHistorySeq||entryId!==this._last?.attributes?.config_entry_id||userKey!==dialog._userKey()||dialog._isOpen||this._uiHistory.layers.length)return;
    this.dispatchEvent(new CustomEvent('hass-more-info',{detail:{entityId:detail.entityId,view:'history'},bubbles:true,composed:true}));
  }
  _heatpumpHistoryDevice(c){return{id:'heatpump',name:'Warmtepomp',history:c.panasonic?.history,reason:this._heatpumpPresentation(c).label||'Actuele werking onbekend',tank_sources:{temperature_c:this._heatpumpTankObservation(c,'temperature_c'),target_c:this._heatpumpTankObservation(c,'target_c')}};}
  _heatpumpHistoryButton(c){return `<button type="button" class="mini" data-action="heatpump_history" aria-label="Warmtepompgeschiedenis" aria-description="Taken, SG-aanvraag, contact en ontvangst: tik, sleep of gebruik de pijltjestoetsen op de tijdlijnen." ${c.a?.config_entry_id?'':'disabled'}>Geschiedenis</button>`;}
  _openHeatpumpHistory(){
    this._nativeHistorySeq=(this._nativeHistorySeq||0)+1;
    const entryId=this._last?.attributes?.config_entry_id;if(!entryId)return;
    this._uiHistory.prepare();
    if(!this._heatpumpHistoryDialog){
      this._heatpumpHistoryDialog=document.createElement(SP_HEATPUMP_HISTORY_TAG);this._heatpumpHistoryDialog.dataset.heatpumpHistoryDialog='';this.shadowRoot.append(this._heatpumpHistoryDialog);
      this._heatpumpHistoryDialog.addEventListener('source-history',e=>this._openSourceHistory(e.detail.kind,e.detail.item_id,e.detail));
      this._heatpumpHistoryDialog.addEventListener('history-closed',()=>requestAnimationFrame(()=>{if(this.isConnected&&!this._heatpumpHistoryDialog._isOpen)this.shadowRoot.querySelector('button[data-action=heatpump_history]')?.focus({preventScroll:true});}));
    }
    const open=()=>this._heatpumpHistoryDialog.open(this._hass,this._last?.attributes?.config_entry_id,this._heatpumpHistoryDevice(this._ctx()));
    open();this._uiHistory.track(this._heatpumpHistoryDialog,open);
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
    return {a,devices:a.devices||[],wb:a.wallbox||{},water:a.water||{},panasonic:a.panasonic||ems.panasonic||{},sgBoost:a.sg_boost||ems.sg_boost||{},learning:a.learning||{},ems,cap:ems.capacity||{},economy:ems.economy||{},forecast:ems.forecast||{},planner:ems.planner||{},phase:ems.phase||{},localPv:ems.local_pv||{},phaseLearning:ems.phase_learning||{},phaseAttribution:ems.phase_attribution||{},historicalPhase:ems.historical_phase_profile||{},batteryAnalysis:ems.battery_analysis||{},batteryFleet:ems.battery_fleet||{},smartClimate:ems.smart_climate||{},today:ems.today||{},electricityToday:ems.electricity_today||{},guide};
  }
  _tile(label,value,note="",cls="") { return `<div class="tile ${cls}"><span>${spEscape(label)}</span><strong>${value}</strong>${note?`<small>${spEscape(note)}</small>`:''}</div>`; }
  _waterFacts(c){
    const w=c.water||{},now=Date.now()/1000,valid=w.schema===1&&w.read_only===true&&w.configured===true,current=valid&&w.enabled===true&&this._activityObservationsCurrent();
    return{w,valid,flow:current?spWaterReading(w.flow,now,{unit:'L/min',current:true}):null,volume:current?spWaterReading(w.volume,now,{unit:'L',current:true}):null,leak:current?spWaterReading(w.native_leak,now,{flag:true,current:true}):null,today:valid?spWaterNumber(w.today?.volume_l):null};
  }
  _waterAdvisory(facts){
    const {w,flow}=facts,s=w.suspicion||{},elapsed=spWaterNumber(s.elapsed_s),required=spWaterNumber(s.required_s),threshold=spWaterNumber(s.threshold_l_min);
    if(flow==null||!['pending','suspected'].includes(s.state)||elapsed==null||required==null||required<=0||threshold==null||threshold<=0||flow<threshold||s.last_reported_at!==w.flow?.reported_at)return '';
    const text=s.state==='suspected'?'Langdurige stroming waargenomen':'Aanhoudende stroming volgen';
    return this._notice(`<strong>${text}</strong><br>${spEscape(spDuration(elapsed))} met geregistreerde stroming vanaf ${spEscape(spWaterFlow(threshold))}; controlegrens ${spEscape(spDuration(required))}. Controleer of het watergebruik verklaarbaar is.<br>Dit is een patroonwaarschuwing, geen bewezen lek of toestelverbruik.`,s.state==='suspected');
  }
  _waterSummary(c){
    const f=this._waterFacts(c),leak=f.leak===true?'Lek gemeld door watermeter':f.leak===false?'Geen lek gemeld':'Lekstatus onbekend';
    return `<section class="external" data-water-summary><div class="sectionhead"><div><h2>Water</h2><p>${f.valid?`${f.w.enabled===true?'':'Monitoring uit · '}${spEscape(spWaterFlow(f.flow))} · ${spEscape(spWaterLiters(f.today))} geregistreerd vandaag · ${spEscape(leak)}`:'Koppel de huishoudelijke watermeter om verbruik, stroming en de oorspronkelijke lekmelding te volgen.'}</p></div><button type="button" class="mini" data-action="view" data-value="water">Water bekijken</button></div>${f.leak===true?this._notice('De watermeter meldt een mogelijk lek. Controleer de oorspronkelijke melding en het watergebruik.',true):''}</section>`;
  }
  _water(c){
    const f=this._waterFacts(c),{w}=f,zone=this._hass?.config?.time_zone,clock=reading=>spProofClock(reading?.reported_at,zone),coverage=spWaterNumber(w.today?.volume_covered_s);
    const source=(label,reading,value)=>`<div><dt>${spEscape(label)}</dt><dd>${spEscape(value)} · oorspronkelijk rapport ${spEscape(clock(reading))} · ${spEscape(spWaterReason(reading?.reason))}</dd></div>`;
    return `<section class="view" data-water-panel><div class="sectionhead"><div><h2>Watermeter</h2><p>Huishoudelijk watergebruik · alleen uitlezen</p></div><button type="button" class="mini" data-action="configure" data-config-step="water">Watermeter instellen</button></div>${!f.valid?this._notice('Watermonitoring is nog niet ingeschakeld of de bronnen zijn niet gekoppeld. Kies je bestaande totale watermeter, stromingssensor en optionele lekmelding. Er wordt geen kraan of toestel bediend.'):w.enabled!==true?this._notice('Watermonitoring staat uit. Eerdere geregistreerde gegevens blijven in de geschiedenis beschikbaar; actuele waarden worden niet ingevuld.'):''}<div class="summarygrid">${this._tile('Geregistreerd vandaag',spWaterLiters(f.today),coverage==null?'Meetdekking onbekend':`${spDuration(coverage)} met bruikbare tellervergelijking; onvolledig dagbeeld`)}${this._tile('Stroming nu',spWaterFlow(f.flow),f.flow==null?'Actuele betrouwbare flow ontbreekt':'Oorspronkelijk rapport '+clock(w.flow))}${this._tile('Lekmelding watermeter',f.leak===true?'Lek gemeld':f.leak===false?'Geen lek gemeld':'Onbekend',f.leak==null?'Geen actuele betrouwbare lekmelding beschikbaar':'Oorspronkelijke sensorstatus · '+clock(w.native_leak))}</div>${f.leak===true?this._notice('<strong>De watermeter meldt een mogelijk lek.</strong><br>Controleer het watergebruik en de oorspronkelijke meter. De SolarPilot-monitor sluit geen watertoevoer af.',true):''}${this._waterAdvisory(f)}<div class="controls"><button type="button" class="mini" data-action="water_history" ${c.a?.config_entry_id?'':'disabled'}>Watergeschiedenis en samenloop bekijken</button>${this._sourceHistoryButton('water')}</div><p class="note">Liters horen bij de hele huishoudwatermeter. Gelijktijdige boilertemperatuurdaling of een actief vaatwasprogramma bewijst geen oorzaak en krijgt geen toegeschreven liters.</p><details data-ui-key="water:sources"><summary>Oorspronkelijke bronmetingen en dekking</summary><dl class="investigation-metrics">${source('Totale meterstand',w.volume,spWaterLiters(f.volume))}${source('Stroming',w.flow,spWaterFlow(f.flow))}${source('Native lekmelding',w.native_leak,f.leak===true?'Gemeld':f.leak===false?'Niet gemeld':'Onbekend')}</dl><p class="note">Dagverbruik komt uitsluitend uit geldige verschillen van dezelfde totaalmeter. Meetgaten, tellerreset en gewijzigde bronnen blijven onderbrekingen; ontbrekend is geen nul. Stroming wordt niet naar liters omgerekend.</p></details></section>`;
  }
  _energyTile(kind,a){
    const meta=a.energy_display||{},source=meta[kind]||{},solar=kind==='pv';
    const number=v=>typeof v==='number'&&Number.isFinite(v),clamp=v=>Math.max(0,Math.min(1,v));
    const watts=source.value_w,stamp=source.reported_at,age=number(stamp)?Date.now()/1000-stamp:Infinity;
    const stale=number(meta.stale_s)&&meta.stale_s>0?meta.stale_s:120;
    const available=number(watts)&&number(stamp)&&age>=-5&&age<=stale&&(!solar||watts>=0)
      &&this._last?.state!=='unavailable'&&this._last?.state!=='unknown'&&!this._last?.attributes?.restored;
    const label=solar?'Zonnepanelen':'Net';
    if(!available)return `<div class="tile energy-tile energy-unknown" data-energy="${kind}"><span>${label}</span><strong>—</strong><small>Actuele meting ontbreekt</small></div>`;
    const limit=number(meta.inverter_limit_w)&&meta.inverter_limit_w>0?meta.inverter_limit_w:null;
    const reference=number(a.max_import_w)&&a.max_import_w>0?a.max_import_w:limit;
    const fraction=solar?(limit?clamp(watts/limit):null):(watts>0?(reference?clamp(watts/reference):null):0);
    const value=solar?spPower(watts):watts===0?'in balans':`${watts>0?'afname':'injectie'} ${spPower(Math.abs(watts))}`;
    const note=solar?(watts===0?'Geen productie':limit?`${Math.round(watts/limit*100)}% van omvormervermogen`:'actueel'):'P1 · actuele meting';
    if(fraction==null)return `<div class="tile energy-tile energy-unknown" data-energy="${kind}"><span>${label}</span><strong>${value}</strong><small>${spEscape(note)}</small></div>`;
    const hue=solar?120*fraction:watts<0?120:95*(1-fraction);
    const position=solar?fraction:watts<=0?0:fraction;
    const title=solar?`Productiekleur van 0 tot ${spPower(limit)} omvormervermogen.`:`Groen bij injectie; oplopende afname verkleurt tot rood bij ${spPower(reference)}. Dit is een kleurschaal, geen elektrische beveiliging.`;
    return `<div class="tile energy-tile" data-energy="${kind}" style="--energy-hue:${hue.toFixed(1)}" title="${spEscape(title)}"><span>${label}</span><strong>${value}</strong><small>${spEscape(note)}</small><div class="energy-scale ${solar?'solar-scale':'grid-scale'}" aria-hidden="true"><i style="left:${(position*100).toFixed(1)}%"></i></div></div>`;
  }
  _wallboxActivity(wb){
    const power=spNumber(wb.power_w),age=spNumber(wb.last_report_age_s),native=wb.activity_details?.current;
    const snapshotCurrent=this._last?.attributes?.restored!==true&&!['unknown','unavailable'].includes(String(this._last?.state||'').toLowerCase());
    const reportCurrent=!Object.hasOwn(native||{},'report_timestamp')||this._freshObservation(native.report_timestamp,spNumber(wb.stale_s)??120);
    const baseKnown=wb.activity_known===undefined?power!=null&&power>=0&&age!=null&&age>=-5&&age<=(spNumber(wb.stale_s)??120):wb.activity_known===true;
    const known=snapshotCurrent&&reportCurrent&&baseKnown&&power!=null&&power>=0;
    const active=known&&power>=(spNumber(wb.charging_threshold_w)??50);
    const label=!known?'LAADSTATUS ONBEKEND':active?'AUTO LAADT':native?.known&&native.active===false&&native.label?String(native.label).toLocaleUpperCase('nl-BE'):wb.activity==='waiting'||wb.demand?'WACHT OP LAADSTROOM':wb.connected===false?'GEEN AUTO AANGESLOTEN':'AUTO LAADT NIET';
    return {known,active,label};
  }
  _deviceAvailabilityRetry(d){
    const retry=d?.availability_retry;
    if(!this._activityObservationsCurrent()||!['switch','number','script','dishwasher'].includes(d?.kind)||retry?.active!==true||!['source_wait','command_wait'].includes(retry.state)||retry.interval_s!==300)return null;
    const finite=value=>typeof value==='number'&&Number.isFinite(value);
    if(!finite(retry.next_check_wall)||retry.next_check_wall<=0||!finite(retry.remaining_s)||retry.remaining_s<0||retry.remaining_s>300)return null;
    if(d.start_requirements?.availability_and_fault?.fault)return null;
    const remaining=Math.max(0,Math.min(300,Math.ceil(retry.next_check_wall-Date.now()/1000)));
    const check=remaining>0?`Opnieuw controleren over ${remaining<60?remaining+' s':spDuration(remaining)}.`:'Nieuwe controle gepland; wacht op de volgende terugmelding.';
    return {
      label:retry.state==='source_wait'?'Tijdelijk niet bereikbaar':'Wacht op terugmelding',
      reason:typeof retry.reason==='string'&&retry.reason.trim()?retry.reason:retry.state==='source_wait'?'De verbinding of actuele toestelgegevens zijn tijdelijk niet beschikbaar.':'De vorige opdracht is nog niet bevestigd.',
      note:`${check} SolarPilot controleert elke 5 minuten opnieuw. Na herstel beoordeelt SolarPilot opnieuw of bediening op dat moment nodig en toegestaan is.`,
    };
  }
  _deviceActivity(d){
    const snapshotCurrent=this._last?.attributes?.restored!==true&&!['unknown','unavailable'].includes(String(this._last?.state||'').toLowerCase());
    const known=snapshotCurrent&&d.available!==false,active=known&&d.on===true;
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
  _wallboxPriorityChoice(c,target){
    const data=c.a?.wallbox_priority;if(!data||data.available!==true)return null;
    if(typeof target==='string'&&target.startsWith('device:')&&c.devices.some(d=>d.id===target.slice(7)&&d.kind==='dishwasher'))return null;
    const choice=target==='global'?data.general:target==='dhw_extra'?data.sg_boost:typeof target==='string'&&target.startsWith('device:')?data.devices?.[target.slice(7)]:null;
    return choice&&typeof choice==='object'&&!Array.isArray(choice)&&choice.target===target?choice:null;
  }
  _anchorWallboxPriorityClock(){
    const observed=this._last?.attributes?.wallbox_priority?.observed_at;
    if(typeof observed==='number'&&Number.isFinite(observed)&&observed>0&&observed!==this._wallboxPriorityObserved){this._wallboxPriorityObserved=observed;this._wallboxPriorityReceivedAt=performance.now();}
  }
  _wallboxPriorityNow(){
    return typeof this._wallboxPriorityObserved==='number'&&typeof this._wallboxPriorityReceivedAt==='number'?this._wallboxPriorityObserved+Math.max(0,(performance.now()-this._wallboxPriorityReceivedAt)/1000):Date.now()/1000;
  }
  _refreshWallboxPriorityClocks(){
    if(!this.isConnected||document.visibilityState==='hidden')return;
    const c=this._ctx(),now=this._wallboxPriorityNow();
    this._content.querySelectorAll('[data-wallbox-priority-clock]').forEach(node=>{const choice=this._wallboxPriorityChoice(c,node.dataset.wallboxPriorityClock);const text=spWallboxPriorityCountdown(choice,now);if(node.textContent!==text)node.textContent=text;});
  }
  _wallboxPriorityControl(c,target,{label='',compact=false}={}){
    const choice=this._wallboxPriorityChoice(c,target);if(choice?.eligible!==true)return '';
    const global=target==='global',data=c.a.wallbox_priority,active=choice.active===true,individuals=[...Object.values(data.devices||{}),data.sg_boost].filter(Boolean);
    const any=individuals.some(x=>x.active===true),mixed=global&&data.mixed===true,admin=this._hass?.user?.is_admin===true;
    const disabled=this._wallboxPriorityBusy||this._busy||!admin||!c.a.config_entry_id||!this._activityObservationsCurrent();
    const summary=global?'Voor alle beschikbare toestellen':target==='dhw_extra'?'Alleen extra SG-zonneboost; Panasonic-comfort blijft behouden':label;
    const exceptions=mixed?'<small data-wallbox-priority-mixed>Afzonderlijke keuzes wijken af. Elk toestel blijft apart bedienbaar.</small>':'';
    const effective=target==='dhw_extra'?c.sgBoost?.wallbox_first:c.devices.find(d=>`device:${d.id}`===target)?.wallbox_first;
    const baseline=!global&&!active?`<small>Bewaarde verdeling: ${effective===true?'Wallbox eerst':effective===false?'bestaande toestelvoorrang':'volgens de voorrangslijst'}.</small>`:'';
    return `<section class="wallbox-priority-control${compact?' compact':''}" data-wallbox-priority-target="${spEscape(target)}"><div class="wallbox-priority-head"><div><strong>Wallbox voorrang geven</strong>${this._question('dashboard',global?'wallbox_priority':'wallbox_priority_device','Wallbox voorrang geven')}${summary?`<small>${spEscape(summary)}</small>`:''}</div><button type="button" role="switch" class="toggle ${active?'active':''}" aria-label="Wallbox voorrang geven${label?' voor '+spEscape(label):global?' voor alle toestellen':''}" aria-checked="${active}" data-action="wallbox_priority_toggle" data-priority-target="${spEscape(target)}" ${disabled?'disabled':''}>${active?'Aan':'Automatisch'}</button></div><p class="wallbox-priority-clock" data-wallbox-priority-clock="${spEscape(target)}">${spEscape(spWallboxPriorityCountdown(choice,this._wallboxPriorityNow()))}</p>${exceptions}${baseline}${active||global&&any?`<div class="controls">${active?`<button type="button" class="mini" data-action="wallbox_priority_duration" data-priority-target="${spEscape(target)}" ${disabled?'disabled':''}>Looptijd wijzigen</button>`:''}${global?`<button type="button" class="mini" data-action="wallbox_priority_auto" data-priority-target="global" ${disabled?'disabled':''}>Alles automatisch</button>`:''}</div>`:''}${global&&!compact?'<small>Automatisch herstelt de bewaarde voorrangsregels. De afwasmachine blijft buiten deze keuze; beschermde cycli en noodzakelijk comfort blijven behouden.</small>':''}${!admin?'<small>Alleen een Home Assistant-beheerder kan deze keuze wijzigen.</small>':''}</section>`;
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
    const items=[["overview","Overzicht"],["priorities","Voorrang"],["loads","Toestellen"],["comfort","Warmtepomp"],["water","Water"],["planning","Planning"],["energy","Energie"],["storage","Batterij"],["export","Export"],["guide","Uitleg"]];
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
    return `${!this._last?this._notice('Geen SolarPilot-status gevonden. Voeg eerst de integratie toe.',true):''}${this._versionWarning(a)}${problem&&!isolatedWait?this._notice(`<strong>${title}</strong><br>${spEscape(problem)}${sourceNote?'<br>'+sourceNote:''}${canReset?'<br><button data-action="reset" class="mini">Controle afronden</button>':''}`,!automaticRestart&&!sourceWait):''}${isolatedNotice}${this._error?`<div role="alert" class="error">${spEscape(this._error)}</div>`:''}${this._feedback?`<div role="status" class="notice">${spEscape(this._feedback)}</div>`:''}${ems.legacy_conflicts?.length?this._notice(`<strong>Dubbele regeling geblokkeerd</strong><br>${ems.legacy_conflicts.map(x=>spEscape(x.name)).join(' · ')}<br>Automatisch regelen blijft geblokkeerd tot deze vervangen regelaars uit staan.`,true):''}`;
  }
  _versionWarning(a){
    const version=String(a.integration_version||'');
    return /^\d+\.\d+\.\d+(?:-[a-z]+\.\d+)?$/.test(version)&&version!==SP_CARD_VERSION?this._notice(`<strong>Integratie en kaart hebben verschillende versies</strong><br>Integratie ${spEscape(version)} · geladen kaart ${SP_CARD_VERSION}. Werk beide bij, herstart Home Assistant en herlaad de pagina of sluit de HA-app volledig en open ze opnieuw.`,true):'';
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
    const number=spNumber(value),valid=known&&number!=null;
    return `<div class="reason-power"><b>${valid?spPower(Math.abs(number)):'Vermogen nog niet bekend'}</b>${valid?`<small>${spEscape(label)} · ${estimated?'geschat':'gemeten'}</small>`:''}</div>`;
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
    const n=spNumber(value);if(n==null)return 'nog niet bekend';
    return n<=0?'gereed':n<60?`nog ${Math.ceil(n)} s`:`nog ${spDuration(n)}`;
  }
  _overviewBatteryExplanation(fleet){
    const names=new Map((fleet.batteries||[]).map(b=>[b.id,b.name||'Batterij']));
    const faults=Object.entries(fleet.faults||{}),pending=fleet.pending&&typeof fleet.pending==='object'&&Object.keys(fleet.pending).length?fleet.pending:null;
    const control=faults.length?'Controle nodig':pending?'Wacht op bevestiging':fleet.control_enabled?'Regeling aan':'Alleen bekijken';
    const facts=[['Bediening',control],['Laadvermogen',fleet.aggregate?.valid===true?spPower(fleet.aggregate.charge_w):'nog niet bekend'],['Vermogen naar huis',fleet.aggregate?.valid===true?spPower(fleet.aggregate.discharge_w):'nog niet bekend']];
    const status=[...faults.map(([id,reason])=>`${names.get(id)||'Batterij'}: ${this._plainReason(reason)}`),...(pending?[`${names.get(pending.id)||'Batterij'}: wacht op bevestiging van de eerdere opdracht.`]:[])];
    return `${this._reasonFacts(facts)}${status.length?`<div class="condition-group waiting"><b>${faults.length?'Controle nodig':'Wacht op bevestiging'}</b><ul>${status.map(x=>`<li>${spEscape(x)}</li>`).join('')}</ul></div>`:''}<p><b>Advies voor de batterij:</b> ${spEscape(this._plainReason(fleet.reason))}</p>${(fleet.batteries||[]).map(b=>`<p><b>${spEscape(b.name||'Batterij')}</b> · ${b.valid===true?'metingen beschikbaar':'wacht op betrouwbare metingen'} · ${b.control_kind==='read_only'||!b.control_enabled||!b.exclusive_control_confirmed?'alleen bekijken':'bediening vrijgegeven'}</p>`).join('')}<p class="note">Het advies is geen bevestiging dat een opdracht uitgevoerd is. ${!fleet.control_enabled?'SolarPilot stuurt deze batterij niet aan.':'De precieze uitvoerreden is alleen bekend als de regeling die heeft gemeld.'}</p>`;
  }
  _reasonRow({name,state,reason,extra='',change=null,view='',id='',key='',details='',power='',graphic='',status='',footer='',activity='inactive'}){
    const time=change?this._reasonTime(change.at||change.timestamp):'';
    const last=change?.reason?`<details class="reason-history" data-ui-key="${spEscape(key+':history')}"><summary>Laatste ${change.confirmed===false?'waarneming':'verandering'}${time?' · '+spEscape(time):''}</summary><p>${spEscape(this._plainReason(change.reason))}</p>${['external','Home Assistant'].includes(change.source)?'<small>Buiten een bevestigde SolarPilot-opdracht veranderd; de precieze veroorzaker is niet bekend.</small>':''}</details>`:'';
    const visual=['active','available','unknown'].includes(activity)?activity:'inactive';
    const badge=state==null||state===''?'':`<span class="badge">${spEscape(state)}</span>`;
    return `<article class="reason-row is-${visual}" data-activity="${visual}" data-reason-key="${spEscape(key)}"><div class="row"><strong class="grow">${spEscape(name)}</strong>${badge}</div>${graphic}${power}${status}<p>${spEscape(this._plainReason(reason))}</p>${extra?`<small>${spEscape(extra)}</small>`:''}${details?`<details class="reason-details" data-ui-key="${spEscape(key+':why')}"><summary>Waarom wel of nog niet?</summary>${details}</details>`:''}${last}${footer}${id?`<button type="button" class="mini" data-action="history" data-id="${spEscape(id)}">Geschiedenis</button>`:view?`<button type="button" class="mini" data-action="view" data-value="${spEscape(view)}">Instellen en details</button>`:''}</article>`;
  }
  _decisionBoard(c){
    const rows=[],p=c.panasonic||{},s=c.sgBoost||{};
    {
      const operation=this._heatpumpPresentation(c);
      rows.push(this._reasonRow({name:'Warmtepomp — Panasonic-regeling / SG-zonneboost',state:operation.known?operation.label:null,reason:this._heatpumpReason(c),extra:'',view:'comfort',key:'overview:sg',details:this._sgDetails(c,'overview'),power:this._heatpumpPower(c),graphic:this._heatpumpGraphic(c)+this._heatpumpBusiness(c)+this._heatpumpTankSummary(c),status:this._sgStatusStrip(c),footer:this._wallboxPriorityControl(c,'dhw_extra',{label:'extra SG-zonneboost',compact:true})+this._heatpumpHistoryButton(c),activity:operation.active?'active':operation.known?'inactive':'unknown'}));
    }
    for(const device of c.devices||[]){
      const retry=this._deviceAvailabilityRetry(device);
      const reason=retry?.reason||device.isolation_reason||device.start_diagnostics?.summary||device.reason;
      const activity=this._deviceActivity(device);
      const state=retry?.label||(!activity.known?'Niet bereikbaar':activity.active?device.kind==='dishwasher'?(device.dishwasher?.airdry?'Nadrogen actief':'Programma loopt'):(device.manual_forced?'Actief · handmatig':device.owned?'Actief · SolarPilot':'Actief · toestel'):device.mode==='disabled'?'Niet automatisch geregeld':device.kind==='dishwasher'&&device.dishwasher?.request_status==='completed'?'Afwasbeurt klaar':device.kind==='dishwasher'&&device.dishwasher?.request_status==='start_requested'?'Start aangevraagd':device.kind==='dishwasher'&&!device.dishwasher?.app_request?'Nog niet klaargezet':'Wacht');
      const w=device.dishwasher||{},checks=device.kind==='dishwasher'?this._dishwasherGates(w):[];
      const deadline=w.start_deadline?this._reasonTime(w.start_deadline):'';
      const turn=w.request_status==='running'?'gebruikt voor deze beurt':w.request_status==='completed'?'afgewerkt':w.request_status==='start_requested'?'start aangevraagd':w.app_request||w.ticket_armed?'klaargezet':activity.active?'programma loopt':w.request_status==='consumed'?'verbruikt':'nog niet klaargezet';
      const programme=device.kind==='dishwasher'?this._reasonFacts([['Programma',w.program||'nog niet bekend'],['Vrijgegeven beurt',turn],['Vastgelegde startdeadline',deadline||'nog niet bekend'],...(w.start_requested_at?[['Start aangevraagd',this._reasonTime(w.start_requested_at)]]:[]),...(w.start_confirmed_at?[['Start bevestigd',this._reasonTime(w.start_confirmed_at)]]:[])]):'';
      rows.push(this._reasonRow({name:device.name,state,reason,extra:retry?.note||(activity.active&&device.kind==='dishwasher'?'Een lopend programma wordt niet onderbroken.':''),change:device.history?.last_change,id:device.id,key:'overview:device:'+device.id,footer:device.kind==='dishwasher'?'':this._wallboxPriorityControl(c,`device:${device.id}`,{label:device.name,compact:true}),details:programme+this._startExplanation(device,c.a?.mode,checks),power:this._knownPower(device.power_w,{known:activity.known&&!device.isolated,estimated:device.estimated===true}),activity:activity.active?'active':activity.known?'inactive':'unknown'}));
    }
    if(c.wb?.enabled){
      const wb=c.wb,activity=this._wallboxActivity(wb),observation=wb.activity_details||{},current=observation.current||{};
      rows.push(this._reasonRow({name:'Auto laden',state:activity.label,reason:current.reason||(activity.active?'De auto laadt; de Wallbox bepaalt zelf het laden.':activity.known?'De auto laadt nu niet; de Wallbox heeft geen precieze wachtreden gemeld.':'Wacht op een betrouwbare laadstatus.'),extra:this._plainReason(wb.consumer_priority?.reason||wb.reason||'SolarPilot leest de Wallbox en verdeelt het resterende overschot.'),change:observation.last_stop?{at:observation.last_stop.observed_stop_at,reason:observation.last_stop.stop_reason,confirmed:observation.last_stop.stop_confirmed}:null,view:'priorities',key:'overview:wallbox',details:this._wallboxExplanation(wb,activity,'overview:wallbox:periods'),power:this._knownPower(wb.power_w,{known:activity.known,label:'Auto laden'}),footer:this._sourceHistoryButton('wallbox'),activity:activity.active?'active':activity.known?'inactive':'unknown'}));
    }
    if(c.batteryFleet?.enabled){
      const fleet=c.batteryFleet,aggregate=fleet.aggregate||{},charging=aggregate.valid===true&&Number(aggregate.charge_w)>50,discharging=aggregate.valid===true&&Number(aggregate.discharge_w)>50;
      const control=Object.keys(fleet.faults||{}).length?'Controle nodig':Object.keys(fleet.pending||{}).length?'Wacht op bevestiging':fleet.control_enabled?'Regeling aan':'Alleen bekijken';
      const actual=charging&&discharging?'Batterijen laden en leveren stroom':charging?'Batterij laadt':discharging?'Batterij levert stroom':'';
      const reason=Object.keys(fleet.faults||{}).length?'Een batterijopdracht vraagt controle.':Object.keys(fleet.pending||{}).length?'Wacht op bevestiging van een batterijopdracht.':!fleet.control_enabled?'SolarPilot bekijkt de batterij en geeft advies.':fleet.reason?`Batterijadvies: ${fleet.reason}`:'Nog geen batterijadvies ontvangen.';
      rows.push(this._reasonRow({name:'Batterij',state:actual?`${actual} · ${control}`:control,reason,view:'storage',key:'overview:battery',details:this._overviewBatteryExplanation(fleet),footer:(fleet.batteries||[]).map(b=>this._sourceHistoryButton('battery',b.id,'Bronhistorie '+(b.name||'batterij'))).join(''),power:this._knownPower(aggregate.power_w,{known:aggregate.valid===true,label:Number(aggregate.power_w)<0?'Netto laden':Number(aggregate.power_w)>0?'Netto naar huis':'Netto batterijvermogen'}),activity:actual?'active':'inactive'}));
    }
    return `<section class="decision-board"><style>.decision-board{--sp-activity-blue:#03a9f4;margin:22px 0}.decision-board>p{color:var(--secondary-text-color);font-size:13px}.reason-list{display:grid;align-items:start;gap:12px;grid-template-columns:repeat(auto-fit,minmax(min(100%,310px),1fr))}.reason-row{min-width:0;border:1px solid var(--divider-color);border-radius:16px;padding:16px;background:var(--card-background-color)}.reason-row.is-active{border-color:var(--sp-activity-blue);box-shadow:inset 4px 0 0 var(--sp-activity-blue)}.reason-row.is-active .badge{background:var(--sp-activity-blue);color:#071b26}.reason-row.is-available{border-color:var(--sp-activity-blue);border-style:dashed}.reason-row .row{gap:8px;align-items:flex-start;flex-wrap:wrap}.reason-row .badge{white-space:normal;font-size:11px}.reason-row p{line-height:1.5;margin:9px 0;overflow-wrap:anywhere;font-size:14px}.reason-row>small,.reason-history small{display:block;color:var(--secondary-text-color);font-size:12px;line-height:1.5}.reason-row .mini{margin-top:10px}.reason-power{margin:10px 0}.reason-power>b{font-size:18px}.reason-power>small,.shared-heatpump-power>small{display:block;color:var(--secondary-text-color);font-size:12px;line-height:1.5}.shared-heatpump-power{padding:12px 16px;border:1px solid var(--divider-color);border-radius:12px;margin:12px 0}.reason-details>summary{padding:10px 12px;background:var(--secondary-background-color);border:1px solid var(--divider-color);border-radius:10px;font-size:12px;line-height:1.4}.reason-details[open]>summary{border-color:var(--sp-activity-blue)}.reason-details .start-facts{grid-template-columns:repeat(2,minmax(0,1fr))}.reason-details .start-facts b{display:block;overflow-wrap:anywhere}.condition-group{margin:12px 0;font-size:12px;line-height:1.5}.condition-group ul{padding-left:18px;margin:6px 0}.condition-group.ready>b{color:var(--success-color,#4caf50)}.condition-group.waiting>b{color:var(--warning-color,#ffb300)}.reason-details .note{font-size:12px}@media(max-width:420px){.reason-details .start-facts{grid-template-columns:1fr}}.reason-history{margin-top:10px;font-size:12px}.reason-history summary{cursor:pointer;padding:4px 0}.reason-history p{font-size:12px}.activity-legend{display:flex;gap:8px 18px;flex-wrap:wrap;margin:12px 0;color:var(--secondary-text-color);font-size:12px}.activity-legend span{display:flex;align-items:center;gap:6px}.activity-swatch{width:14px;height:14px;border:2px solid var(--sp-activity-blue);border-radius:4px;box-shadow:inset 3px 0 0 var(--sp-activity-blue)}.activity-swatch.available{border-style:dashed;box-shadow:none}</style><h2>Wat gebeurt er en waarom?</h2><p>Hier zie je wat elk toestel nu doet, waarom het wacht en welke verandering het laatst is waargenomen.</p><div class="activity-legend" aria-label="Betekenis van de blauwe randen"><span><i class="activity-swatch" aria-hidden="true"></i>Bevestigd actief of afgeleid uit verbruik</span><span>Warmtepomp: actief bedrijf of gemeten verbruik</span><span><i class="activity-swatch available" aria-hidden="true"></i>Aanvraag wacht op bevestiging</span></div><div class="reason-list">${rows.join('')||'<p>Nog geen gekoppelde toestellen.</p>'}</div></section>`;
  }
  _overview(c){
    const {a,panasonic,sgBoost,wb,cap,forecast,localPv,batteryFleet,batteryAnalysis,phase,today,planner,ems}=c;
    const batteryText=batteryFleet.enabled?(batteryFleet.aggregate?.soc_pct==null?'vloot actief':`${spPct(batteryFleet.aggregate.soc_pct)} · ${spPower(batteryFleet.aggregate?.power_w)}`):(batteryAnalysis.enabled?'what-if actief':'niet gekoppeld');
    const managedNote=a.isolated_devices?.length?(a.isolated_reserve_w===0?'Toestelgegevens deels onbekend; het actuele netoverschot blijft leidend.':'Deel van de toestelgegevens ontbreekt; mogelijk verbruik wordt apart gereserveerd.'):`${a.energy_estimated?'deels geschat':'gemeten of teruggemeld'} · autoladen apart`;
    return `<section class="view overview-view">
      <div class="flowgrid">
        ${this._energyTile('pv',a)}
        ${this._energyTile('grid',a)}
        ${this._tile(a.isolated_devices?.length?'Bekend vermogen SolarPilot-toestellen':'Vermogen SolarPilot-toestellen',`${a.energy_estimated?'≈ ':''}${spPower(a.managed_w)}`,managedNote)}
        ${this._tile('Vrij overschot',spPower(a.free_w),`reserve ${spPower(a.reserve_w)}`)}
      </div>
      <p class="energy-legend">Zon: rood weinig → groen veel. Net: groen injectie → geel, oranje en rood bij afname. Kleur is geen foutmelding.</p>
      ${this._wallboxPriorityControl(c,'global')}
      ${this._decisionBoard(c)}
      ${this._waterSummary(c)}
      <details class="technical-overview" data-ui-key="overview:technical"><summary>Metingen, voorspellingen en technische details</summary>
      ${this._activeLoads(c)}<div class="summarygrid">
        ${this._tile('Wallbox',wb.enabled?`${spEscape(this._wallboxActivity(wb).label)} · ${spPower(this._wallboxActivity(wb).known?wb.power_w:null)}`:'niet gemonitord',wb.enabled?'De Wallbox bepaalt zelf het laden; SolarPilot leest de status.':'',wb.enabled&&this._wallboxActivity(wb).active?'active-tile':'')}
        ${this._tile('Batterij',batteryText,batteryFleet.reason||batteryAnalysis.note||'')}
        ${this._tile('Kwartierpiek',cap.enabled?(cap.current_average_w==null?'—':spPower(cap.current_average_w)):'uit',cap.enabled?`theoretisch kwartierbudget ${spPower(cap.optional_headroom_w)}`:'')}
        ${this._tile('Lokale PV-voorspelling',localPv.enabled?(localPv.corrected_power_w==null?'—':spPower(localPv.corrected_power_w)):'uit',localPv.enabled?`${Math.round(Number(localPv.confidence||0)*100)}% · ${localPv.reason||''}`:'')}
      </div></details>
      <div class="kpis">
        ${this._tile('Zelfconsumptie vandaag',today.self_consumption_pct==null?'—':spPct(today.self_consumption_pct),today.pv_coverage_note||'PV-meetdekking onbekend; indicatieve toerekening')}
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
  _wallboxPeriodHtml(event,key='',{ongoing=false}={}){
    const when=stamp=>{if(typeof stamp!=='number'||!Number.isFinite(stamp)||stamp<=0)return 'tijdstip onbekend';try{return new Intl.DateTimeFormat('nl-BE',{day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit',timeZone:this._hass?.config?.time_zone||'Europe/Brussels',timeZoneName:'shortOffset'}).format(new Date(stamp*1000));}catch{return 'tijdstip onbekend';}};
    const watts=value=>typeof value==='number'&&Number.isFinite(value)&&value>=0?spPower(value):'—',end=ongoing?'Nog geen stop bevestigd':event.stop_confirmed===true?'Stop waargenomen':'Einde onbekend / meetonderbreking',periodKey=key+':period:'+String(event.observed_start_at)+':'+String(event.observed_stop_at??event.unavailable_observed_at??'ongoing');
    return `<details class="wb-history-period" data-ui-key="${spEscape(periodKey)}"><summary>${spEscape(when(event.observed_start_at))} · ${end}</summary><div class="start-explanation"><p>${event.start_confirmed===true?'Begin waargenomen':'Bij eerste controle al aan het laden'}: ${spEscape(when(event.observed_start_at))}</p><p><b>${end}</b>${event.observed_stop_at!=null?' · '+spEscape(when(event.observed_stop_at)):''}</p><p>${spEscape(event.stop_reason||'Exacte stopoorzaak niet gemeld.')}</p>${event.cause_reported!==true?'<p class="note">De Wallbox heeft geen betrouwbare precieze stopoorzaak doorgegeven.</p>':''}<div class="start-facts"><span>Laatste laadrapport <b>${spEscape(when(event.last_charging_report_at))}</b></span><span>Vermogen bij laatste laadrapport <b>${spEscape(watts(event.previous_power_w))}</b></span><span>Eindrapport <b>${spEscape(when(event.stop_report_at))}</b></span><span>Vermogen bij eindrapport <b>${spEscape(watts(event.power_w))}</b></span><span>Statusrapport <b>${spEscape(when(event.status_report_at))}</b></span><span>Toen gemelde Wallbox-status <b>${spEscape(event.native_status||'Niet bewaard')}</b></span>${event.unavailable_observed_at!=null?`<span>Onderbreking waargenomen <b>${spEscape(when(event.unavailable_observed_at))}</b></span>`:''}</div><p class="note">Dit zijn afzonderlijke bewaarde rapporten bij de grenzen van deze laadperiode. Ze vormen geen continue vermogensreeks of berekend sessieverbruik. Het tijdstip is een waarneming in Home Assistant.</p></div></details>`;
  }
  _wallboxExplanation(wb,activity,key=''){
    const observation=wb.activity_details||{},current=observation.current||{},last=observation.last_stop;
    const periods=Array.isArray(observation.history)?observation.history:[],ongoing=observation.ongoing&&typeof observation.ongoing==='object'?observation.ongoing:null;
    const when=value=>{if(value==null||!Number.isFinite(Number(value))||Number(value)<=0)return 'tijdstip onbekend';try{return new Date(Number(value)*1000).toLocaleString('nl-BE',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit',timeZone:this._hass?.config?.time_zone||undefined});}catch{return 'tijdstip onbekend';}};
    const reason=!activity.known?'Een actuele, betrouwbare laadmeting ontbreekt; wachten of stoppen is niet bevestigd.':activity.active?'De auto laadt nu; er is geen actuele laadstop.':current.known?current.reason:'Nog geen actuele wachtreden ontvangen. De ingestelde laadmodus alleen verklaart niet waarom de auto wacht.';
    const stop=event=>event.stop_confirmed?`<p><b>Laadstop waargenomen: ${spEscape(when(event.observed_stop_at))}</b></p><p>Wallbox meldde toen: ${spEscape(event.stop_reason||'Exacte stopoorzaak niet gemeld.')}</p>${!event.cause_reported?'<p class="note">De laadstop is gezien, maar de exacte oorzaak is niet doorgegeven.</p>':''}`:`<p><b>Laadstop niet bevestigd</b> · metingen onderbroken op ${spEscape(when(event.unavailable_observed_at))}</p><p>${spEscape(event.stop_reason||'Het einde van de laadperiode is niet waargenomen.')}</p>`;
    const priority=wb.per_device_priority?wb.consumer_priority?.reason:wb.reason;
    return `<div class="start-explanation wb-wait"><strong>${activity.active?'Wat doet de Wallbox nu?':'Waarop wacht de Wallbox?'}</strong><p>${spEscape(reason)}</p>${activity.known&&current.known&&current.native_status?`<small>Door de Wallbox gemelde status: ${spEscape(current.native_status)}</small>`:''}<p><b>SolarPilot verdeelt de zonnestroom zo:</b> ${spEscape(priority||'Nog geen actuele verdelingsregel ontvangen.')}</p><small>Dit is de SolarPilot-regel voor andere toestellen, niet automatisch de oorzaak van een laadstop. De benodigde laadstroom en wachttijd staan hieronder bij Actuele verdeling.</small></div>
      <div class="start-explanation wb-stop"><strong>Laatste laadstop</strong>${last?stop(last):'<p>Nog geen laadstop waargenomen sinds deze registratie. Eerdere stops worden niet achteraf ingevuld.</p>'}<small>Het tijdstip is de waarneming in Home Assistant, niet het exacte fysieke stopmoment. Wie of wat de stop veroorzaakte is alleen bekend als de Wallbox dit meldt.</small></div>
      ${periods.length||ongoing?`<details class="wb-stop-history"${key?` data-ui-key="${spEscape(key)}"`:''}><summary>Laadgeschiedenis · ${periods.length+(ongoing?1:0)} bewaarde laadperioden</summary>${ongoing?this._wallboxPeriodHtml(ongoing,key||'wallbox:history',{ongoing:true}):''}${periods.map(event=>this._wallboxPeriodHtml(event,key||'wallbox:history')).join('')}<p class="note">Maximaal 30 afgesloten laadperioden en de laatste open waarneming bewaard. Een ontbrekende meting of herstart bewijst geen laadstop.</p></details>`:''}`;
  }
  _wallbox(c){
    const {wb}=c;if(!wb.enabled)return `<div class="empty">Wallbox-monitor is niet geconfigureerd.</div>`;
    const activity=this._wallboxActivity(wb);
    return `<section class="policy"><div class="row"><div class="grow"><h2>Auto laden in de gezamenlijke volgorde</h2><p>De volledige volgorde en de gevolgen voor autoladen staan op één plek.</p></div><button type="button" data-action="view" data-value="priorities">Naar Voorrang</button></div></section>
      <section class="external wallbox-device${activity.active?' on':''}"><div class="row"><div class="icon">EV</div><div class="grow"><h2>${spEscape(wb.name||'Wallbox')} <span class="runstate ${activity.active?'active':''}">${spEscape(activity.label)}</span> <span class="readonly">WALLBOX REGELT ZELF</span></h2><p>${spEscape((wb.per_device_priority?wb.consumer_priority?.reason:wb.reason)||'Extern geregeld')}</p></div><strong>${spPower(activity.known?wb.power_w:null)}</strong></div><p class="note">SolarPilot leest het werkelijke laden; de Wallbox kiest zelf de laadstroom. Een ingestelde laadmodus is geen bewijs dat de auto nu laadt.</p>${this._wallboxPriorityControl(c,'global')}${this._wallboxExplanation(wb,activity)}${this._wallboxProfile(wb)}${this._sourceHistoryButton('wallbox')}<div class="facts"><span>Ingestelde Wallbox-modus <b>${spEscape(spWallboxMode(wb.configured_mode||wb.reported_mode))}</b></span><span>Werkelijk gedetecteerde sessie <b>${spEscape(wb.session_value||(!wb.session_entity?'geen sessiesensor gekoppeld':spWallboxMode(wb.effective_mode)))}</b></span><span>Laadvermogen <b>${spPower(activity.known?wb.power_w:null)}</b></span><span>Wallbox-vermogen terugnemen <b>${wb.reclaim_allowed_now?'ja, nu bevestigd':'nee, nu niet beschikbaar'}</b></span>${wb.last_report_age_s!=null?`<span>Rapport <b>${Math.round(Number(wb.last_report_age_s))} s oud</b></span>`:''}</div><p class="note wb-session">${spEscape(wb.reclaim_reason||wb.session_reason||'Alleen werkelijk vrij zonneoverschot wordt gebruikt.')}</p>${wb.warning?this._notice(spEscape(wb.warning),true):''}</section>`;
  }
  _cycleReserveRelief(allocation){
    if(!allocation||typeof allocation!=='object')return null;
    const full=spNumber(allocation.protected_cycle_reserve_w),solar=spNumber(allocation.solar_cycle_reserve_w),relief=spNumber(allocation.solar_cycle_reserve_relief_w);
    if(full==null||solar==null||relief==null||full<0||solar<0||relief<=0||relief>full||solar>full||Math.abs(full-solar-relief)>0.5)return null;
    return {full,solar,relief};
  }
  _startAllocationFacts(allocation,cycleRelief=null){
    if(!allocation)return '';
    const rows=[],add=(key,label,{positive=false}={})=>{const value=spNumber(allocation[key]);if(value==null||positive&&value<=0)return;rows.push(`<span>${label} <b>${spPower(value)}</b></span>`);};
    add('filtered_free_w','Zonneoverschot na vermogensfilter');
    add('smoothing_hold_w','Tijdelijk achtergehouden door vermogensfilter',{positive:true});
    if(cycleRelief){
      add('protected_cycle_reserve_w','Reserve voor lopende beschermde cycli · elektrisch behouden',{positive:true});
      add('solar_cycle_reserve_w','Cyclusreserve afgetrokken van zonnestroom');
    }else add('protected_cycle_reserve_w','Reserve voor lopende beschermde cycli · komende pieken',{positive:true});
    add('isolated_reserve_w','Reserve voor toestellen met onzekere metingen',{positive:true});
    add('sg_unconfirmed_reserve_w','Reserve voor nog onbevestigde SG-opname',{positive:true});
    add('other_reserved_w','Andere bestaande vermogensreserve',{positive:true});
    add('locked_commitment_w','Reeds toegezegd extra vermogen',{positive:true});
    add('higher_allocated_w','Extra toegewezen aan hogere voorrangen',{positive:true});
    add('remaining_solar_w','Zonnebudget na reserves en eerdere toewijzingen');
    add('electrical_headroom_w','Actuele elektrische ruimte');
    add('remaining_cap_w','Elektrisch budget na reserves en eerdere toewijzingen');
    if(!['protected_cycle_reserve_w','isolated_reserve_w','sg_unconfirmed_reserve_w','other_reserved_w'].some(key=>spNumber(allocation[key])!=null))add('comfort_and_cycle_reserve_w','Reserve voor beschermd of onzeker verbruik',{positive:true});
    return rows.join('');
  }
  _startExplanation(d,mode,extra=[]){
    const diagnostics=d.start_diagnostics&&typeof d.start_diagnostics==='object'?d.start_diagnostics:null;
    const requirements=d.start_requirements&&typeof d.start_requirements==='object'?d.start_requirements:null;
    const retry=this._deviceAvailabilityRetry(d);
    const reason=retry?.reason||diagnostics?.summary||d.reason||'Nog geen actuele beslisreden ontvangen; de oorzaak is niet vastgesteld.';
    const retryNote=retry?`<p class="note device-availability-retry">${spEscape(retry.note)}</p>`:'';
    if(this._last?.attributes?.restored===true||['unknown','unavailable'].includes(String(this._last?.state||'').toLowerCase()))return '<div class="start-explanation"><strong>Toestelactiviteit nog niet bevestigd</strong><p>Actuele SolarPilot-status ontbreekt; eerdere toestelactiviteit is niet bevestigd.</p></div>';
    if(d.isolated)return `<div class="start-explanation"><strong>${spEscape(retry?.label||'Toestel tijdelijk apart gehouden')}</strong><p>${spEscape(retry?.reason||d.isolation_reason||reason)}</p>${retryNote}<p>${d.available===false?'De actuele activiteit is onbekend.':'Het toestel meldt zijn activiteit; het vermogen of andere benodigde gegevens zijn niet betrouwbaar.'} SolarPilot bedient dit toestel tijdelijk niet en controleert de gegevens automatisch opnieuw. Zodra ze betrouwbaar zijn, kan het toestel opnieuw meedoen met behoud van minimale looptijd, rusttijd en overige voorwaarden.</p>${Number(d.isolation_reserve_w)>0?`<p>Veiligheidsreserve voor mogelijk verbruik: <b>${spPower(d.isolation_reserve_w)}</b>. Dit is geen gemeten verbruik.</p>`:d.isolation_reserve_w===0?'<p>Voor deze ontbrekende toestelmeting wordt geen extra verbruiksreserve afgetrokken. De actuele netmeting bevat het werkelijke huisverbruik; het toestelvermogen blijft onbekend.</p>':''}</div>`;
    if(d.on&&d.available!==false)return `<div class="start-explanation"><strong>Waarom dit toestel nu actief is</strong><p>${spEscape(reason)}</p>${retryNote}<p class="start-ready">${d.kind==='dishwasher'?'Een lopende afwasbeurt wordt niet opnieuw gestart en niet onderbroken om stroom vrij te maken.':'Startvoorwaarden gelden voor een volgende start, niet voor het toestel dat al draait.'}</p><small>De actuele beslisreden komt rechtstreeks uit de regelaar.</small></div>`;
    const wait=s=>s==null||s===''||!Number.isFinite(Number(s))?'nog niet bekend':Number(s)<60?`${Math.max(0,Math.ceil(Number(s)))} s`:spDuration(s);
    const explain=(key,value={})=>({
      global_solar_mode:'Automatisch regelen staat niet aan.',
      recovery_clear:'De herstartcontrole voor dit toestel is nog bezig.',
      automatic_participation:'Dit toestel staat op Uitgesloten.',
      reliable_energy_measurement:'Een betrouwbare actuele energiemeting ontbreekt.',
      availability_and_fault:retry?retry.reason:!value.observed?'Nog geen actuele toestelstatus ontvangen.':value.fault?`Toestelfout: ${value.fault}`:'Toestel is niet beschikbaar.',
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
    const gridFallback=d.kind==='dishwasher'&&d.dishwasher?.deadline_due===true;
    const pool=gridFallback?null:power?.solar_start_pool,required=spNumber(power?.required_start_w);
    const allocation=power?.allocation;
    const cycleRelief=power?.measurement_valid===true&&d.available!==false&&['switch','number','script'].includes(d.kind)&&d.non_interruptible!==true?this._cycleReserveRelief(allocation):null;
    const available=allocation?spNumber(allocation.available_w):pool?spNumber(pool.available_solar_w):spNumber(power?.measured_free_w);
    if(!d.on&&power?.measurement_valid&&required!=null&&available!=null&&required>available&&/vermogen|prioriteit/i.test(reason)&&!(d.kind==='dishwasher'&&!pool)&&!diagnostics?.missing?.includes('allocated_start_power')){
      missing.push(`Nog ongeveer ${spPower(required-available)} beschikbaar startvermogen nodig na reserves en toewijzingen.`);
    }
    if(pool?.import_headroom_after_release_w!=null&&Number(pool.import_headroom_after_release_w)<Number(power.minimum_w))missing.push(`De ingestelde netafnamegrens laat momenteel ${spPower(pool.import_headroom_after_release_w)} extra verbruik toe; dit toestel vraagt minstens ${spPower(power.minimum_w)}.`);
    for(const [label,value,state] of extra){if(state!=='ok')missing.push(`${label}: ${value}.`);}
    missing=[...new Set(missing)];
    const sharing=(pool?`<span>Van autoladen beschikbaar <b>${spPower(pool.wallbox_solar_w)}</b></span>${Number(pool.lower_loads_releasable_w)>0?`<span>Van lagere toestellen vrij te maken <b>${spPower(pool.lower_loads_releasable_w)}</b></span>`:''}<span>Toegelaten zonnepot vóór eindtoewijzing <b>${spPower(pool.available_solar_w)}</b></span>`:'')+(allocation?this._startAllocationFacts(allocation,cycleRelief)+`<span>Beschikbaar voor dit toestel <b>${spPower(allocation.available_w)}</b></span>`:'');
    const powerFacts=power?`<div class="start-facts"><span>Benodigd voor start <b>${spPower(power.required_start_w)}</b></span>${gridFallback?'<span>Netstroom op deadline <b>toegestaan</b></span>':`<span>Vrije zonnestroom na huisreserve <b>${power.measurement_valid?spPower(power.measured_free_w):'niet betrouwbaar'}</b></span>`}${sharing}<span>Stabiel nodig <b>${stable?.remaining_s!=null?(stable.remaining_s>0?'nog '+wait(stable.remaining_s):'gereed'):stable?.configured_s!=null?(Number(stable.configured_s)>0?wait(stable.configured_s)+' vereist':'geen wachttijd'):'nog niet bekend'}</b></span></div><p class="power-note">${gridFallback?'Op de deadline is zonneoverschot niet nodig. Het beschikbare vermogen blijft begrensd door de actuele net-, fase- en cyclusruimte.':pool?'Het vermogen voor dit toestel telt toegelaten zonnestroom uit autoladen mee, na reserves en begrensd door de echte zonneopbrengst. De Wallbox regelt zelf terug; dit is geen extra netcapaciteit. Lagere toestellen moeten eerst veilig stoppen. Wachttijden en elektrische grenzen blijven gelden.':d.kind==='dishwasher'?'Vrije zonnestroom is niet het totale startvermogen. Toegelaten vermogen uit autoladen kan ook meetellen, zodra de toestelstatus en de laadgegevens betrouwbaar zijn.':''}${power.note?` ${spEscape(power.note)}`:''}</p>`:'';
    const cycleNote=cycleRelief?'<p class="power-note cycle-reserve-note">Dit onderbreekbare toestel mag het actuele resterende zonneoverschot gebruiken. De volledige reserve voor komende afwaspieken blijft elektrisch behouden. Dit telt geen extra zonnestroom of elektrische ruimte bij. Minimumlooptijden en beschermde cycli blijven gelden.</p>':'';
    const readyLabels={global_solar_mode:'Automatisch regelen staat aan.',recovery_clear:'Herstartcontrole afgerond.',automatic_participation:'Dit toestel mag automatisch meedoen.',reliable_energy_measurement:'Actuele energiemeting betrouwbaar.',availability_and_fault:'Toestel beschikbaar zonder gemelde fout.',release:'Vrijgavevoorwaarden zijn gehaald.',demand_or_time_window:'Startvraag of toegestaan tijdvenster aanwezig.',minimum_rest:'Minimale rusttijd afgerond.',non_interruptible_cycle_release:'Eén volledige beschermde cyclus vrijgegeven.',daily_maximum:'Dagmaximum laat deze start toe.',planner_start_block:'Planning houdt deze start niet tegen.',wallbox_start_block:'Autoladen houdt deze start niet tegen.',runtime_start_block:'Andere regelingen laten deze start toe.',general_increase_permission:'Veiligheidscontrole laat nieuwe starts toe.',allocated_start_power:'Voldoende vermogen aan dit toestel toegewezen.'};
    const ready=requirements?Object.entries(requirements).filter(([key,value])=>value?.met===true&&value.required!==false&&readyLabels[key]).map(([key])=>readyLabels[key]):[];
    const readyHtml=ready.length?`<div class="condition-group ready"><b>In orde</b><ul>${ready.map(text=>`<li>${spEscape(text)}</li>`).join('')}</ul></div>`:'';
    const missingHtml=missing.length?`<div class="start-missing"><b>Nog nodig</b><ul>${missing.map(text=>`<li>${spEscape(text)}</li>`).join('')}</ul></div>`:requirements?'<p class="start-ready">Geen ontbrekende startvoorwaarde gemeld; de beslisreden hierboven blijft leidend.</p>':'<p>De afzonderlijke startvoorwaarden zijn nog niet volledig ontvangen.</p>';
    return `<div class="start-explanation"><strong>${spEscape(retry?.label||(d.available===false?'Toestelactiviteit nog niet bevestigd':'Waarom dit toestel nog niet gestart is'))}</strong><p>${spEscape(reason)}</p>${retryNote}${powerFacts}${cycleNote}${missingHtml}${readyHtml}<small>De beslisreden komt rechtstreeks uit de regelaar. Een ontbrekende externe oorzaak wordt niet ingevuld.</small></div>`;
  }
  _deviceCard(d,mode){
    if(d.kind==='dishwasher')return this._dishwasherCard(d,mode);
    const activity=this._deviceActivity(d),physicalOn=activity.active, actuallyUsing=physicalOn&&Number(d.power_w||0)>10;
    const statusLabel=this._deviceAvailabilityRetry(d)?.label||activity.label;
    const stateClass=physicalOn?` on ${d.manual_forced?'manual':d.owned?'owned':'external-on'}`:'';
    const manualButton=d.manual_forced
      ?`<button class="mini manual active" data-action="manual_stop" data-id="${spEscape(d.id)}" ${d.isolated||!d.available?'disabled':''}>Manueel stoppen</button>`
      :`<button class="mini manual" data-action="manual_start" data-id="${spEscape(d.id)}" ${mode!=='solar'||!d.available||d.isolated?'disabled':''}>Manueel starten</button>`;
    return `<div class="device${stateClass}"><div class="row"><div class="icon">${d.kind==='number'?'↗':d.non_interruptible?'◷':'⏻'}</div><div class="grow"><strong>${spEscape(d.name)} <span class="runstate ${physicalOn?'active':''}">${statusLabel}</span>${actuallyUsing&&!d.isolated?` <span class="using">VERBRUIKT</span>`:''}${d.phase?.classification&&d.phase.classification!=='unknown'?` <span class="phasepill">${spEscape(d.phase.classification)} ${Math.round(Number(d.phase.confidence||0)*100)}%</span>`:''}</strong>${d.boost_seconds>0?`<small>Boost nog ${Math.ceil(d.boost_seconds/60)} min</small>`:''}${d.manual_stop_requested?'<small>Manuele stop wacht op minimale looptijd</small>':''}</div><strong class="devicepower">${activity.known&&!d.isolated?`${d.estimated?'≈ ':''}${spPower(d.power_w)}`:'onbekend'}</strong></div>${this._startExplanation(d,mode)}${this._wallboxPriorityControl(this._ctx(),`device:${d.id}`,{label:d.name,compact:true})}
      ${d.reclaim_block?this._notice(`Overname geblokkeerd: ${spEscape(d.reclaim_block)}`,true):''}${d.planner_hold?this._notice(`<strong>Planner wacht</strong><br>${spEscape(d.planner_reason||'Wacht op gunstiger zonne-uur')}`):''}
      <div class="meta">${d.wallbox_first?'Auto laden eerst · ':d.wallbox_precedence==='consumer_first'?'Dit toestel vóór Auto laden · ':''}${d.time_window_enabled?`Tijdvenster ${spEscape(String(d.time_window_start||'').slice(0,5))}–${spEscape(String(d.time_window_end||'').slice(0,5))}`:'Geen tijdvenster'}${Number(d.min_daily_runtime_s)>0?` · vandaag ${spDuration(d.daily_runtime_s)} / min ${spDuration(d.min_daily_runtime_s)}`:''}${Number(d.effective_nominal_w)>Number(d.configured_nominal_w||0)+1?` · planningswaarde ${spPower(d.effective_nominal_w)}`:''}${d.cycle_learning&&Number(d.cycle_learning.energy_kwh||0)>0?` · cyclus ${Number(d.cycle_learning.energy_kwh).toLocaleString('nl-BE',{maximumFractionDigits:2})} kWh / ${Math.round(Number(d.cycle_learning.duration_min||0))} min (${Math.round(Number(d.cycle_learning.confidence||0)*100)}%)`:''}</div>
      ${d.wallbox_power_reason?`<details><summary>Vermogensverdeling met de Wallbox</summary><p class="note">${spEscape(d.wallbox_power_reason)}</p><p class="note">Alleen bij bevestigde autonome zonneregeling. Bij manueel laden telt uitsluitend echte injectie; elektrische grenzen en minimumlooptijden blijven gelden.</p></details>`:''}
      ${d.deadline_urgent?this._notice(`<strong>Dagminimum heeft nu voorrang</strong><br>${d.deadline_grid_allowed?'Netstroom mag binnen de ingestelde grenzen worden gebruikt.':'Alleen beschikbare zonnestroom; deadline heft netblokkering niet op.'}`,d.deadline_grid_allowed):''}
      <div class="controls"><button type="button" data-action="view" data-value="priorities">Voorrang bekijken</button><button class="mini ${d.mode==='auto'?'active':''}" data-action="participate" data-id="${spEscape(d.id)}">${d.mode==='auto'?'Auto':'Uitgesloten'}</button>${manualButton}<span class="spacer"></span>${d.boost_seconds>0?`<button class="mini" data-action="cancel" data-id="${spEscape(d.id)}">Boost stoppen</button>`:`<button class="mini" data-action="boost" data-id="${spEscape(d.id)}" ${mode!=='solar'||d.mode!=='auto'||!d.available||d.isolated?'disabled':''}>Boost 30 min</button>`}<button class="mini" data-action="history" data-id="${spEscape(d.id)}" aria-label="Apparaatgeschiedenis ${spEscape(d.name)}">Geschiedenis${d.history?.on_s!=null?` · ${spDuration(d.history.on_s)} vandaag`:""}</button>${this._sourceHistoryButton('consumer',d.id,'Bronhistorie in HA')}<button class="mini" data-action="info" data-id="${spEscape(d.id)}">Info</button></div>
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
    const deadline=w.start_deadline?this._reasonTime(w.start_deadline):'';
    const ended=done?this._reasonTime(w.completion.ended_at_local):'';
    const badge=this._deviceAvailabilityRetry(d)?.label||(done?'KLAAR':w.airdry?'AIRDRY — NADROGEN':!d.available?'ONBEKEND':active?(d.owned?'PROGRAMMA ACTIEF':'EXTERN PROGRAMMA'):(w.app_request||w.ticket_armed)?'KLAARGEZET':'NIET KLAARGEZET');
    const rows=p?.stages?Object.entries(p.stages).map(([name,x])=>`<tr><td>${spEscape(name)}</td><td>${x.seconds>0?spPower(x.kwh*3600000/x.seconds):'—'}</td><td>${spPower(x.peak_w)}</td><td>${spDuration(x.seconds)}</td></tr>`).join(''):'';
    const gateChecks=this._dishwasherGates(w);
    return `<div class="device dishwasher${active?' on owned':''}"><div class="row"><div class="icon">◷</div><div class="grow"><strong>${spEscape(d.name)} <span class="runstate ${active?'active':''}">${badge}</span></strong></div><b class="power">${d.available&&!d.isolated?`${d.estimated?'≈ ':''}${spPower(d.power_w)}`:'onbekend'}</b></div>
      <div class="facts"><span>Programma <b>${spEscape(w.program||'Onbekend')}</b></span><span>Fase <b>${spEscape(activity.phase||'Onbekend')}</b></span><span>Vermogen <b>${!d.available||d.isolated?'onbekend':d.estimated?'geschat, geen eigen meting':'gemeten'}</b></span></div>
      ${this._startExplanation({...d,reason:d.reason||w.gate_reason},mode,gateChecks)}
      ${app?`<p class="note app-plan">${spEscape(w.app_message||'Klaarzetten met Delay Start / APP op de machine')}${deadline?` · Uiterlijk starten: <b>${spEscape(deadline)}</b>`:''}</p>`:''}
      ${w.start_requested_at||w.start_confirmed_at?this._reasonFacts([...(w.start_requested_at?[['Start aangevraagd',this._reasonTime(w.start_requested_at)]]:[]),...(w.start_confirmed_at?[['Start bevestigd',this._reasonTime(w.start_confirmed_at)]]:[])]) :''}
      ${done?`<p class="note dw-completed"><b>Afwasmachine klaar · beëindigd op ${spEscape(ended)}</b> — niet automatisch als leeggemaakt gemarkeerd.</p>`:''}
      ${w.cycle_status==='end_unconfirmed'?'<p class="note">Einde niet bevestigd; uit of onbereikbaar is geen succesvol einde.</p>':''}
      ${w.priority_policy?.configured?`<div class="note dw-priority"><strong>Warmtepompcomfort eerst · daarna afwasmachine</strong><br>Afwasmachine vóór Wallbox, lagere flexibele lasten en extra SG-zonneboost volgens de bewaarde volgorde. Minimumlooptijden en gewone comfortregeling blijven behouden.<br>${spEscape(w.priority_policy.ev_solar_priority?'Ook op zonnevermogen dat Full Solar nu gebruikt; tijdelijke netafname mogelijk tijdens terugregelen.':'Geen voorrangsstart op huidig EV-vermogen: alleen echt restoverschot vóór de deadline.')}${w.priority_policy.conditional_ev_w>0?`<br>Voorwaardelijk zonnevermogen uit EV: ${spPower(w.priority_policy.conditional_ev_w)} — geen extra netcapaciteit.`:''}${w.priority_policy.unmetered_reserve_w>0?`<br>Zonder exclusieve afwasmeter: ${spPower(w.priority_policy.unmetered_reserve_w)} extra ruimte gereserveerd voor nog komende verwarmpieken; conservatieve schatting.`:''}${w.priority_policy.ev_start_block?`<br><b>${spEscape(w.priority_policy.ev_start_block)}</b>`:''}${w.priority_policy.wallbox_response?.reason?`<br>${spEscape(w.priority_policy.wallbox_response.reason)}`:''}</div>`:''}
      <p class="note">${spEscape(w.power_source||'Handmatige schatting')} · geen onderbreking van een lopend programma.</p>
      <div class="controls"><button type="button" data-action="view" data-value="priorities">Voorrang bekijken</button><button class="mini ${d.mode==='auto'?'active':''}" data-action="participate" data-id="${spEscape(d.id)}">${d.mode==='auto'?'Auto':'Uitgesloten'}</button>
      ${(w.app_request||w.ticket_armed)?`<button class="mini" data-action="dishwasher_cancel" data-id="${spEscape(d.id)}">Klaarzetten annuleren</button>`:app?'':`<button class="mini" data-action="dishwasher_arm" data-id="${spEscape(d.id)}" ${!w.ready||w.attempted||active||!d.available||d.isolated?'disabled':''}>Eén beurt klaarzetten</button>`}
      <button class="mini" data-action="history" data-id="${spEscape(d.id)}">Geschiedenis${d.history?.on_s!=null?` · ${spDuration(d.history.on_s)} vandaag`:''}</button>${this._sourceHistoryButton('consumer',d.id,'Bronhistorie in HA')}<button class="mini" data-action="info" data-id="${spEscape(d.id)}">Info</button></div>
      ${mode!=='solar'&&w.ticket_armed?'<p class="note">Klaargezet, maar geen fysieke start zolang Automatisch regelen niet actief is.</p>':''}
      <details><summary>Vermogensprofiel · ${Number(w.profile_count||0)} volledig gemeten cycli</summary><p>${spEscape(w.profile_note||'Nog geen meting. Ontbrekende fasen zijn onbekend, niet 0 W.')}</p>${rows?`<p>Laatste complete cyclus ${spEscape(p.program)} · ${spKwh(p.energy_kwh)} · ${spDuration(p.duration_s)}</p><div style="overflow:auto"><table class="dw-profile-table" style="border-collapse:separate;border-spacing:10px 5px;text-align:left"><thead><tr><th>Fase</th><th>Gemiddeld</th><th>Piek</th><th>Duur</th></tr></thead><tbody>${rows}</tbody></table></div>`:''}<p class="note">Shelly uitsluitend als vermogensmeter. Een lage vermogensfase is geen voltooid programma. Nog onbekende fasen en schattingen worden niet als zeker of nul weergegeven.</p></details></div>`;
  }
  _loads(c){
    const {a,devices}=c,mode=a.mode||'observe';
    return `<section class="view"><div class="sectionhead"><h2>Toestellen</h2><button type="button" data-action="manage_devices">Toestellen beheren</button></div><p class="sub">Bij elk toestel zie je wat nodig is om te starten en waarom het nu wacht of draait. De gezamenlijke rangorde beheer je via Voorrang.</p>${this._heatpump(c,'loads')}${this._wallbox(c)}${this._wallboxPriority(c)}${!devices.length?'<div class="empty">Nog geen bestuurbare toestellen toegevoegd.</div>':devices.map(d=>this._deviceCard(d,mode)).join('')}</section>`;
  }
  _climateModeLabel(mode){return ({auto:'Automatisch',off:'Uit',heat:'Verwarmen',cool:'Koelen',heat_cool:'Automatisch'})[mode]||mode||'Onbekend';}
  _panasonicProgramLabel(program){return ({heating:'Verwarmen',cooling:'Koelen',off:'Uit',auto:'Automatisch',dhw:'Warm water',unknown:'Warmtepompprogramma onbekend'})[String(program||'').toLowerCase()]||'Warmtepompprogramma onbekend';}
  _freshObservation(stamp,stale=120){
    if(this._last?.attributes?.restored===true||['unknown','unavailable'].includes(String(this._last?.state||'').toLowerCase()))return false;
    if(typeof stamp!=='number'||!Number.isFinite(stamp)||stamp<=0||typeof stale!=='number'||!Number.isFinite(stale)||stale<=0)return false;
    const age=Date.now()/1000-stamp;
    return age>=-5&&age<=stale;
  }
  _panasonicSourceFresh(p,role){
    const stamps={power:p.power_observed_at??p.power_stamp,compressor:p.compressor_frequency_observed_at??p.compressor_stamp,received:p.sg_status_observed_at??p.sg_status_stamp,supply1:p.power_supply1_observed_at,supply2:p.power_supply2_observed_at,context:p.context_stamp,temperature:p.temperature_observed_at??p.temperature_stamp,target:p.target_observed_at??p.target_stamp};
    return this._freshObservation(stamps[role],p.source_stale_s??120);
  }
  _heatpumpGlobalOff(p){
    const task=p.native_task||{},limit=p.source_stale_s===undefined?120:p.source_stale_s,stale=task.stale_s===undefined?limit:task.stale_s,valid=value=>typeof value==='number'&&Number.isFinite(value)&&value>0;
    return task.verified_global_off===true&&task.inactive===true&&task.inactive_action==='off'&&task.inactive_scope==='global'&&task.source==='aquarea_poll'&&(task.independent_tank_on===undefined||task.independent_tank_on===false)&&(task.conflict===undefined||task.conflict===false)&&task.function==null&&valid(limit)&&valid(stale)&&this._freshObservation(task.observed_at,Math.min(stale,limit));
  }
  _heatpumpActivity(c){
    const p=c.panasonic||{},s=c.sgBoost||{},operation=p.operation||{};
    const idleProof=operation.evidence==='compressor_frequency'||operation.evidence==='native_action'&&this._heatpumpGlobalOff(p);
    const known=(operation.state==='active'||operation.state==='idle'&&idleProof)&&this._freshObservation(operation.observed_at,operation.stale_s);
    const linked=p.configured===true||s.configured===true;
    return {known,active:known&&operation.state==='active',state:known?operation.state:'unknown',evidence:known?operation.evidence:'none',
      label:known?(operation.label||(operation.state==='active'?'Warmtepomp in werking':'Geen actieve warmte- of koelactie')):linked?'Werking onbekend':'Nog niet gekoppeld',
      note:known&&operation.evidence==='compressor_frequency'?'Bevestigd met actuele compressorfrequentie.':known&&operation.evidence==='native_action'?(operation.state==='active'?'Panasonic meldt een actuele warmte- of koelactie; compressorfrequentie is niet gekoppeld.':'Panasonic meldt geen actieve warmte- of koelactie; compressorfrequentie is niet gekoppeld.'):known?'Panasonic meldt geen actieve warmte- of koelactie.':linked?'Actuele compressor- of toestelactie ontbreekt. Gemeten stroom of een circulatiepomp alleen bewijst geen warmteproductie.':'Koppel de warmtepompmetingen via Instellingen en details.'};
  }
  _meteredHeatpumpActivity(c){
    const p=c.panasonic||{},power=p.power_activity||{},supplies=Array.isArray(power.supplies)?power.supplies:[];
    const limit=power.stale_s??p.source_stale_s??120,validNumber=value=>typeof value==='number'&&Number.isFinite(value)&&value>=0;
    const validSupplies=supplies.filter(row=>row.valid===true),freshSupplies=validSupplies.filter(row=>validNumber(row.watts)&&this._freshObservation(row.observed_at,limit));
    const complete=power.complete===true;
    const supportFresh=complete?(supplies.length?supplies.length===validSupplies.length&&validSupplies.length===freshSupplies.length&&(p.power_scope!=='split'||supplies.some(row=>row.number===1)&&supplies.some(row=>row.number===2)):p.power_kind==='measured'&&this._freshObservation(p.power_observed_at??p.power_stamp,limit)):
      validSupplies.length>0&&validSupplies.length===freshSupplies.length&&this._freshObservation(power.observed_at,limit);
    const legacyPartialFresh=!supplies.length&&!complete&&p.power_kind==='measured'&&this._freshObservation(p.power_observed_at??p.power_stamp,limit);
    const degradedPartial=complete&&!supportFresh&&power.state==='active'&&power.active===true&&freshSupplies.some(row=>row.state==='active'&&row.watts>0);
    const partialActive=degradedPartial||!complete&&power.state==='partial'&&power.active===true&&(freshSupplies.some(row=>row.state==='active'&&row.watts>0)||legacyPartialFresh);
    const supported=supportFresh||legacyPartialFresh;
    const contextExpired=power.evidence==='metered_power_and_context'&&power.observed_at===power.context_observed_at&&!this._freshObservation(power.context_observed_at,limit);
    const summaryFresh=this._freshObservation(power.observed_at,limit)||contextExpired&&supported;
    const known=['metered_power','metered_power_and_context'].includes(power.evidence)&&(summaryFresh&&supported||degradedPartial)&&(complete&&!partialActive&&['active','basis','off'].includes(power.state)&&validNumber(power.total_w)||partialActive);
    const active=known&&(power.state==='active'||partialActive);
    const defrost=p.defrost||{},defrostActive=defrost.state==='active'&&['aquarea_entity','aquarea_poll'].includes(defrost.source)&&this._freshObservation(defrost.observed_at,defrost.stale_s??limit);
    const nativeTask=p.native_task||{},nativeTaskFresh=this._freshObservation(nativeTask.observed_at,nativeTask.stale_s??limit);
    const taskContext=p.task_context||{},contextCompatible=['native_program','native_mode','aquarea_entity'].includes(taskContext.source)&&
      taskContext.function===power.function&&taskContext.kind===power.function_kind&&taskContext.source===power.function_source&&
      this._freshObservation(taskContext.observed_at,taskContext.stale_s??limit);
    const activeMain=freshSupplies.some(row=>row.role==='main'&&row.state==='active'&&row.watts>0&&row.watts>=(validNumber(power.threshold_w)?power.threshold_w:200));
    const idleContextAllowed=nativeTask.function==null&&nativeTask.source==='aquarea_poll'&&nativeTask.inactive_action==='idle'&&
      ['selected_program','tank_route'].includes(power.function_kind)&&complete&&supportFresh&&activeMain&&contextCompatible;
    const tankCircuitAllowed=nativeTask.function==null&&nativeTask.source==='aquarea_poll'&&nativeTask.inactive_action==='off'&&
      nativeTask.inactive_scope==='space_circuit'&&nativeTask.independent_tank_on===true&&nativeTask.verified_global_off!==true&&
      power.function==='tapwater_heating'&&power.function_kind==='tank_route'&&complete&&supportFresh&&activeMain&&contextCompatible;
    const taskConflict=nativeTaskFresh&&(nativeTask.conflict===true&&['aquarea_entity','aquarea_poll','native_hvac_action','none'].includes(nativeTask.source)||
      nativeTask.inactive===true&&['aquarea_poll','native_hvac_action'].includes(nativeTask.source)&&!idleContextAllowed&&!tankCircuitAllowed);
    const routingInference=['selected_program','tank_route'].includes(power.function_kind);
    const functionName=active&&complete&&!partialActive&&!defrostActive&&!taskConflict&&(!routingInference||activeMain&&contextCompatible)&&power.activity_kind!=='heater'&&['tapwater_heating','space_heating','space_cooling'].includes(power.function)&&this._freshObservation(power.context_observed_at,limit)?power.function:null;
    const functions={tapwater_heating:'Boiler opwarmen',space_heating:'Verwarmen',space_cooling:'Koelen'};
    const activeFeeds=freshSupplies.filter(row=>row.state==='active').map(row=>row.number).join(' en ');
    const label=!known?'':partialActive?(activeFeeds?`Actief verbruik op voeding ${activeFeeds}`:'Actief verbruik op deelmeter'):functionName?functions[functionName]:active?(power.activity_kind==='heater'?'Elektrische bijverwarming actief':'Warmtepomp werkt'):power.state==='off'?'Geen elektrisch verbruik':'Basisverbruik';
    const functionProof=power.function_kind==='tank_route'?'de Panasonic-tankroute (geen afzonderlijke bevestiging van de actuele tankactie)':power.function_kind==='selected_program'?'de gekozen Panasonic-stand (geen afzonderlijke actiebevestiging)':functionName==='tapwater_heating'?'een actuele Panasonic-tankmelding':'een actuele Panasonic-bedrijfsmelding';
    const note=!known?'':partialActive?'Afgeleid uit gemeten verbruik op deze voeding; het totaal en de functie zijn niet vastgesteld.':functionName?
      `Afgeleid uit gemeten verbruik en ${functionProof}; compressorbedrijf en SG-reactie blijven afzonderlijke waarnemingen.`:
      power.activity_kind==='heater'&&active?'Afgeleid uit verbruik op de voeding voor elektrische bijverwarming; dit bevestigt geen compressorbedrijf, ruimte- of tankfunctie.':
      `Afgeleid uit gemeten elektrisch verbruik; de functie en compressorwerking zijn hiermee niet afzonderlijk bevestigd.`;
    return {known,active,state:known?(active?'active':power.state):'unknown',label,note,function:functionName,evidence:known?(functionName?'metered_power_and_context':'metered_power'):'none',total_w:complete&&!partialActive&&known?power.total_w:null};
  }
  _heatpumpResolvedTask(c){
    const display=this._heatpumpDisplayOperation(c);
    if(display)return {known:display.known,kind:display.taskKnown?(display.tier==='confirmed'?'native':'inferred'):'activity',function:display.taskKnown?display.function:null,symbol:display.taskKnown?(display.function==='defrost'?'space_cooling':display.function==='sterilization'?'tapwater_heating':display.function):'info',label:display.label};
    const task=this._heatpumpTaskEvidence(c),native=this._heatpumpActivity(c),meter=this._meteredHeatpumpActivity(c);
    const active=native.active||meter.active;
    if(task.known&&(task.kind==='action'||task.kind==='defrost'))return {known:true,kind:'native',function:task.function,symbol:task.kind==='defrost'?'space_cooling':task.function,label:task.label};
    if(meter.active&&meter.function)return {known:true,kind:'inferred',function:meter.function,symbol:meter.function,label:meter.label};
    if(active)return {known:true,kind:'activity',function:null,symbol:'info',label:meter.active?meter.label:'Warmtepomp werkt'};
    if(meter.known)return {known:true,kind:'activity',function:null,symbol:'info',label:meter.label};
    if(native.known)return {known:true,kind:'activity',function:null,symbol:'info',label:native.evidence==='compressor_frequency'?'Compressor staat stil':'Niet actief'};
    if(task.known&&task.kind==='idle'&&this._heatpumpGlobalOff(c.panasonic||{}))return {known:true,kind:'native',function:null,symbol:'info',label:'Niet actief'};
    return {known:false,kind:'none',function:null,symbol:'info',label:''};
  }
  _heatpumpPresentation(c){
    const native=this._heatpumpActivity(c),meter=this._meteredHeatpumpActivity(c),p=c.panasonic||{},task=this._heatpumpResolvedTask(c);
    const compressorRunning=native.known&&native.active&&native.evidence==='compressor_frequency'&&this._panasonicSourceFresh(p,'compressor')&&typeof p.compressor_frequency_hz==='number'&&p.compressor_frequency_hz>0;
    const supplies=this._heatpumpSupplies(c),main=supplies.find(row=>row.role==='main'),heater=supplies.find(row=>row.role==='heater');
    // Animation follows current main activity; it creates no compressor proof.
    const heaterOnly=p.power_activity?.activity_kind==='heater'||heater?.fresh===true&&heater.state==='active'&&!(main?.fresh===true&&main.state==='active');
    const fanActive=compressorRunning||!heaterOnly&&(native.active||main?.fresh===true&&main.state==='active');
    const display=this._heatpumpDisplayOperation(c),known=display?display.known:native.known||meter.known,active=display?display.active===true:native.active||meter.active;
    return {known,active,state:known?(active?'active':display?'idle':native.known?'idle':meter.state):'unknown',label:task.label,
      taskKind:task.kind,taskFunction:task.function,note:task.kind==='inferred'?'Afgeleid':task.kind==='native'?'':meter.known&&!native.active?'Afgeleid':active?'Actief':'',
      evidence:native.active?'nativelyconfirmed':meter.known?meter.evidence:native.known?'nativelyconfirmed':'none',compressorRunning,fanActive:known&&active&&fanActive};
  }
  _heatpumpDisplayOperation(c){
    const p=c.panasonic||{},value=p.operation_display;
    if(value===undefined)return null;
    const deadline=(stamp,until,limit)=>typeof until==='number'&&Number.isFinite(until)&&until> Date.now()/1000&&this._freshObservation(stamp,limit);
    const valid=value&&value.read_only===true&&value.model_eligible===false&&['confirmed','derived','inactive','unknown'].includes(value.tier);
    if(!valid)return {known:false,taskKnown:false,active:null,tier:'unknown',function:null,label:'Werking onbekend',support:{active:null}};
    const contract=p.source_contract||{},provider=contract.provider||{},compatibility=contract.compatibility||{},verifiedContract=provider.integration_domain==='aquarea'&&provider.library_distribution==='aioaquarea-ng'&&contract.provider_loaded===true&&contract.native_device_registered===true&&contract.schema===1&&contract.read_only===true&&contract.status==='verified'&&contract.contract_id==='aioaquarea_ng_1_3_1_special_status'&&contract.action_semantics==='special_status'&&compatibility.schema===1&&compatibility.contract==='aquarea_special_status_action_v1'&&compatibility.verified===true&&compatibility.basis==='loaded_source'&&typeof compatibility.fingerprint==='string'&&/^[0-9a-f]{64}$/.test(compatibility.fingerprint);
    const limit=value.stale_s??p.source_stale_s??120,taskSource=value.tier==='confirmed'?['aquarea_poll','native_hvac_action','aquarea_entity'].includes(value.source):['aquarea_entity','native_program','native_mode'].includes(value.source)||value.source==='aquarea_contract'&&value.kind==='coherent_native_context'&&value.source_contract_id===contract.contract_id&&verifiedContract,taskKnown=taskSource&&value.context===value.function&&['confirmed','derived'].includes(value.tier)&&['tapwater_heating','space_heating','space_cooling','defrost','sterilization'].includes(value.function)&&deadline(value.observed_at,value.valid_until,limit);
    const activeKnown=typeof value.active==='boolean'&&deadline(value.activity_observed_at,value.activity_valid_until,limit),active=activeKnown?value.active:null;
    const labels={tapwater_heating:'Boiler opwarmen',space_heating:'Verwarmen',space_cooling:'Koelen',defrost:'Ontdooien',sterilization:'Sterilisatie'};
    const support=value.support||{},supportKnown=typeof support.active==='boolean'&&deadline(support.observed_at,support.valid_until,limit);
    const wattsStamp=Object.hasOwn(support,'watts_observed_at')?support.watts_observed_at:support.observed_at,wattsUntil=Object.hasOwn(support,'watts_valid_until')?support.watts_valid_until:support.valid_until;
    const wattsKnown=deadline(wattsStamp,wattsUntil,limit),expiredPrimary=['confirmed','derived'].includes(value.tier)&&!taskKnown;
    return {known:taskKnown||activeKnown,taskKnown,active,tier:taskKnown?value.tier:activeKnown&&!active?'inactive':'unknown',function:taskKnown?value.function:null,
      label:taskKnown?labels[value.function]:activeKnown?active?'Actief · taak onbekend':value.label==='Basisverbruik'?'Basisverbruik':'Niet actief':'Werking onbekend',
      support:{active:supportKnown?support.active:null,watts:wattsKnown&&spNumber(support.watts)!=null&&spNumber(support.watts)>=0&&spNumber(support.watts)<=100000?spNumber(support.watts):null},reason:expiredPrimary?'De benodigde taakbronnen zijn niet meer actueel of hun broncontract is niet bevestigd.':typeof value.reason==='string'?value.reason.slice(0,600):'',reasonCode:expiredPrimary?'display_source_expired_or_unverified':typeof value.reason_code==='string'?value.reason_code.slice(0,80):'',action:expiredPrimary?'Wacht op nieuwe Panasonic-bronrapporten of controleer hun koppeling in deze diagnose.':typeof value.action==='string'?value.action.slice(0,600):''};
  }
  _heatpumpTaskEvidence(c){
    const p=c.panasonic||{},task=p.native_task||{},context=p.task_context||{},defrost=p.defrost||{};
    const functions={tapwater_heating:'Boiler opwarmen',space_heating:'Verwarmen',space_cooling:'Koelen'};
    const fresh=this._freshObservation(task.observed_at,task.stale_s??p.source_stale_s??120);
    const defrostActive=defrost.state==='active'&&['aquarea_entity','aquarea_poll'].includes(defrost.source)&&this._freshObservation(defrost.observed_at,defrost.stale_s??p.source_stale_s??120);
    const functionKnown=Object.hasOwn(functions,task.function)&&['aquarea_poll','native_hvac_action'].includes(task.source)&&fresh&&!defrostActive&&task.conflict!==true&&task.inactive!==true;
    const specialKnown=fresh&&task.function==null&&(task.inactive===true&&['aquarea_poll','native_hvac_action'].includes(task.source)||task.conflict===true&&['aquarea_entity','aquarea_poll','native_hvac_action','none'].includes(task.source));
    const known=defrostActive||functionKnown||specialKnown;
    const kind=defrostActive?'defrost':functionKnown?'action':specialKnown?(task.inactive?'idle':'conflict'):'none';
    const contextKnown=['aquarea_entity','native_program','native_mode'].includes(context.source)&&['tank_route','selected_program'].includes(context.kind)&&this._freshObservation(context.observed_at,context.stale_s??p.source_stale_s??120);
    return {known,kind,function:functionKnown?task.function:null,label:defrostActive?'Ontdooien':functionKnown?functions[task.function]:specialKnown?(task.label||(task.inactive?'Panasonic meldt rust':'Panasonic-taak niet eenduidig')):'',note:defrostActive?'Panasonic meldt ontdooien. Deze melding gaat vóór de warmte- of koelrichting; compressorbedrijf en SG-effect blijven afzonderlijke waarnemingen.':known?(task.note||'Panasonic meldt deze taak; dit is geen afzonderlijke bevestiging van compressorbedrijf of SG-effect.'):'',
      contextKnown,contextKind:contextKnown?context.kind:'none',contextFunction:contextKnown?context.function:null,contextLabel:contextKnown?(context.label||(context.kind==='tank_route'?'Tankroute sanitair water':functions[context.function]||'Gekozen Panasonic-stand')):'',contextNote:contextKnown?(context.note||'Dit is de gekozen stand of route; een actuele warmte- of koelactie is daarmee niet afzonderlijk bevestigd.'):''};
  }
  _heatpumpSupplies(c){
    const p=c.panasonic||{},power=p.power_activity||{},limit=power.stale_s??p.source_stale_s??120;
    const rows=Array.isArray(power.supplies)?power.supplies:[];
    return rows.map(row=>{
      const fresh=row.valid===true&&typeof row.watts==='number'&&Number.isFinite(row.watts)&&row.watts>=0&&this._freshObservation(row.observed_at,limit);
      const state=fresh?(row.watts===0?'off':['active','basis'].includes(row.state)?row.state:'known'):'unknown';
      return {...row,fresh,state};
    });
  }
  _heatpumpSupplyProblem(c,row){
    if(!row)return null;
    const p=c.panasonic||{},quality=p.power_source_quality?.[`supply${row.number}`]||row;
    const fresh=this._freshObservation(quality.source_reported_wall,p.power_activity?.stale_s??p.source_stale_s??120);
    const raw=quality.source_value,missing=raw==null||typeof raw==='string'&&['','unknown','unavailable','none'].includes(raw.trim().toLowerCase());
    const invalid=quality.valid===false&&fresh&&(['negative','out_of_range'].includes(quality.rejection_reason)||quality.rejection_reason==='invalid_value'&&!missing);
    return invalid?{state:'invalid',label:'Ongeldige meetwaarde'}:null;
  }
  _heatpumpSymbol(kind){
    const paths={tapwater_heating:'<path d="M12 3C9 7 6 10 6 14a6 6 0 0 0 12 0c0-4-3-7-6-11Z"/><path d="M9 15c0 2 1 3 3 3"/>',space_heating:'<path d="M5 11 12 5l7 6v9H5Z"/><path d="M9 12v5m3-7v7m3-5v5"/>',space_cooling:'<path d="M12 3v18M4 7l16 10M4 17 20 7M9 5l3 3 3-3M9 19l3-3 3 3M5 10l4-1-1-4M19 14l-4 1 1 4M5 14l4 1-1 4M19 10l-4-1 1-4"/>',heater:'<path d="M4 7h16M4 17h16M5 7v10l3-10 3 10 3-10 3 10 2-10"/><path d="m13 2-3 4h3l-2 4"/>',context:'<path d="M4 8h10l-3-3m3 3-3 3M20 16H10l3-3m-3 3 3 3"/>',info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-11v1"/>'};
    return `<svg class="heatpump-task-icon" viewBox="0 0 24 24" aria-hidden="true">${paths[kind]||paths.info}</svg>`;
  }
  _heatpumpBusiness(c){
    const task=this._heatpumpResolvedTask(c),supplies=this._heatpumpSupplies(c),heater=supplies.find(row=>row.role==='heater'),display=this._heatpumpDisplayOperation(c);
    const heaterActive=display?display.support.active===true:heater?.fresh===true&&heater.state==='active';
    const unavailableLabel=this._heatpumpSupplyProblem(c,heater)?.label||'Geen actuele meting';
    const heaterLabel=display?(display.support.active==null?unavailableLabel:display.support.active?'Aan':'Geen actief verbruik'):!heater||!heater.fresh?unavailableLabel:heater.state==='off'?'Geen verbruik':heaterActive?'Aan':heater.state==='basis'?'Basisverbruik':'Gemeten verbruik';
    const taskHtml=task.known?`<div class="heatpump-business-item" data-heatpump-task="${task.kind}">${this._heatpumpSymbol(task.symbol)}<div><span>Taak van de warmtepomp</span><strong>${spEscape(task.label)}</strong></div></div>`:'';
    return `<div class="heatpump-business" aria-label="Taak en elektrische bijverwarming">${taskHtml}<div class="heatpump-business-item ${heaterActive?'is-active':''}" data-heatpump-heater="${display?(display.support.active==null?'unknown':heaterActive?'active':'off'):heater?.state||'unknown'}" data-heater-inferred="${display?display.support.active!=null:heater?.fresh===true}">${this._heatpumpSymbol('heater')}<div><span>Elektrische bijverwarming</span><strong>${spEscape(heaterLabel)}</strong>${display?display.support.watts!=null?`<b>${spPower(display.support.watts)}</b>`:'':heater?.fresh?`<b>${spEscape(spPower(heater.watts))}</b>`:''}</div></div></div>`;
  }
  _heatpumpSourceContractDetails(c){
    const contract=c.panasonic?.source_contract;
    if(contract?.schema!==1||contract.read_only!==true)return '';
    const rows=[],add=(name,row,labels,{enabled=false}={})=>{
      if(!row||typeof row!=='object')return;
      const fresh=this._freshObservation(row.observed_at,row.stale_s??c.panasonic?.source_stale_s??120),key=String(enabled?row.enabled??'unknown':row.state??row.enabled??'unknown');
      rows.push([name,`${fresh?(labels[key]||'Onbekend'):'Verouderd of ontbrekend'} · bronrapport ${spProofClock(row.observed_at,this._hass?.config?.time_zone)}`]);
    };
    add('Waterpomp',contract.pump,{on:'Aan',off:'Uit',unknown:'Onbekend'});
    add('Panasonic-route',contract.direction,{PUMP:'Ruimtebedrijf',WATER:'Tankroute',IDLE:'Rust'});
    add('Gekozen Panasonic-programma',contract.program,{heating:'Verwarmen',cooling:'Koelen',off:'Uit'});
    add('Tank ingeschakeld',contract.tank,{true:'Ja',false:'Nee'},{enabled:true});
    (Array.isArray(contract.zones)?contract.zones:[]).slice(0,16).forEach((row,index)=>add(`Zone ${index+1} ingeschakeld`,row,{true:'Ja',false:'Nee'},{enabled:true}));
    if(typeof contract.raw_device_action==='string')rows.push(['Oorspronkelijke speciale status',contract.raw_device_action.slice(0,80)]);
    const provider=contract.provider||{},identity=[provider.integration_domain,provider.integration_version,provider.library_distribution,provider.library_version].filter(v=>typeof v==='string').map(v=>v.slice(0,80)).join(' · ');
    return `<details data-ui-key="panasonic-source-contract" data-panasonic-source-contract><summary>Panasonic-broncontract en oorspronkelijke status</summary><p>${contract.status==='verified'?'De gekoppelde bron heeft het geverifieerde statusformaat. De speciale status OFF is hier geen zelfstandige globale UIT-melding.':'Het statusformaat van de gekoppelde Panasonic-bron is nog niet bevestigd.'}</p>${identity?`<p>${spEscape(identity)}</p>`:''}${typeof contract.reason==='string'?`<p data-provider-compatibility-reason>${spEscape(contract.reason.slice(0,600))}</p>`:''}${typeof contract.action==='string'?`<p data-provider-compatibility-action>${spEscape(contract.action.slice(0,600))}</p>`:''}${this._reasonFacts(rows)}<p class="note">De route, gekozen stand, aanstatus en actuele gemeten activiteit worden samen beoordeeld. Deze afleiding verandert geen Panasonic-stand of SG-vrijgave.</p></details>`;
  }
  _heatpumpTechnicalDetails(c){
    const p=c.panasonic||{},task=this._heatpumpTaskEvidence(c),native=this._heatpumpActivity(c),meter=this._meteredHeatpumpActivity(c),resolved=this._heatpumpResolvedTask(c),display=this._heatpumpDisplayOperation(c),rows=[],profiledNative=p.native_task?.source==='aquarea_poll'&&p.source_contract?.schema===1&&p.source_contract.read_only===true;
    const add=(label,value)=>{if(value)rows.push([label,value]);};
    add('Taakweergave',resolved.known?`${resolved.label}${resolved.kind==='inferred'?' · afgeleid uit verbruik en Panasonic-context':resolved.kind==='native'?' · Panasonic-melding':''}`:'Geen actuele taak vastgesteld');
    if(display?.reason)add('Waarom deze herkenning?',display.reason);
    if(display?.action)add('Controle of volgende stap',display.action);
    add('Native taakmelding',profiledNative?'Deze providerstatus bevestigt de bedrijfsactie niet afzonderlijk.':task.known?task.label:'Geen actuele native taakmelding');
    if(task.known&&!profiledNative)add('Onderbouwing native taak',task.note);
    const rawDisplay=p.operation_display||{};
    if(spNumber(rawDisplay.context_report_skew_s)!=null)add('Tijdsafstand native bronrapporten',`${spNumber(rawDisplay.context_report_skew_s)} s${spNumber(rawDisplay.maximum_context_skew_s)!=null?' · grens '+spNumber(rawDisplay.maximum_context_skew_s)+' s':''}`);
    if(spNumber(rawDisplay.measurement_context_skew_s)!=null)add('Tijdsafstand voeding en native context',`${spNumber(rawDisplay.measurement_context_skew_s)} s · oorspronkelijke rapporttijden`);
    const rawTask=p.native_task||{};
    if(rawTask.inactive_action)add('Oorspronkelijke native actie',profiledNative?`${String(rawTask.inactive_action).toUpperCase()} · oorspronkelijke profielstatus; geen globale UIT-bevestiging`:`${rawTask.inactive_action.toUpperCase()} · ${({global:'gehele toestel bevestigd uit',space_circuit:'ruimtebedrijf uit; tank afzonderlijk actief',device_idle:'rustmelding',unknown:'bereik niet vastgesteld',mixed:'meldingen hebben verschillend bereik'})[rawTask.inactive_scope]||'bereik niet vastgesteld'}`);
    if(task.contextKnown)add(task.contextKind==='tank_route'?'Panasonic-route':'Gekozen Panasonic-stand',`${task.contextLabel}. ${task.contextNote}`);
    if(native.known&&(!profiledNative||native.evidence==='compressor_frequency'))add('Bedrijfsmelding',`${native.label}. ${native.note}`);
    if(meter.known)add('Vermogensafleiding',meter.note);
    const hz=p.compressor_frequency_hz;
    if(this._panasonicSourceFresh(p,'compressor')&&typeof hz==='number'&&Number.isFinite(hz))add('Compressorfrequentie',`${hz.toLocaleString('nl-BE',{maximumFractionDigits:1})} Hz`);
    const threshold=p.power_activity?.threshold_w;
    if(typeof threshold==='number'&&Number.isFinite(threshold)&&threshold>=0)add('Actief verbruik vanaf',spPower(threshold));
    for(const row of this._heatpumpSupplies(c)){
      const role=({main:'Hoofdvoeding: compressor, regeling en pompen',heater:'Elektrische ondersteuning: ruimte- of tankverwarming'})[row.role];
      if(role)add(`Functie voeding ${row.number}`,`${role}${row.role_assumed===true?' · Panasonic-voedingsprofiel (aanname)':''}`);
    }
    for(const [key,quality] of Object.entries(p.power_source_quality||{})){
      if(!quality||typeof quality!=='object')continue;
      const sourceLabel=key==='total'?(p.power_scope==='total'?'Totaalmeter':'Vermogensbron'):key==='supply1'?'Voeding 1':'Voeding 2';
      if(quality.reason)add(`${sourceLabel}: meetcontrole`,quality.reason);
      const raw=quality.source_watts,normalized=quality.valid===true&&quality.normalized===true&&quality.normalization_reason==='negative_as_zero'&&quality.watts===0&&typeof raw==='number'&&Number.isFinite(raw)&&raw<0&&raw>=-100000&&typeof quality.source_value==='string'&&['W','kW'].includes(quality.source_unit);
      if(normalized){
        const fresh=this._freshObservation(quality.source_reported_wall,p.power_activity?.stale_s??p.source_stale_s??120);
        add(`${sourceLabel}: normalisatie`,`Bron ${quality.source_value.slice(0,128)} ${quality.source_unit} → toegepast 0 W${fresh?'':' · bron niet actueel'}`);
      }
      if(typeof quality.source_reported_wall==='number'&&Number.isFinite(quality.source_reported_wall)){
        const age=Math.floor(Date.now()/1000-quality.source_reported_wall);
        const ageLabel=age<0?`rapportagetijd ${-age} s in de toekomst`:`${age} s geleden`;
        add(`${sourceLabel}: laatste bronrapport`,`${ageLabel} · ${quality.source_timestamp_kind||'bron'}${quality.source_unit?' · '+quality.source_unit:''}`);
      }
    }
    const goal=this._heatpumpCalculatedGoal(c,{diagnostic:true}),goalRow=p.sg_tank_goal||{};
    if(goal){add(goal.label,spTemp(goal.value));add('SG-tapwaterpercentage',spPct(goal.percent));add('Percentage lokaal bevestigd',spProofClock(goal.confirmedAt,this._hass?.config?.time_zone));add('Oorspronkelijk normaal doel',`${spTemp(goal.normal)} · ${spProofClock(goal.normalStamp,this._hass?.config?.time_zone)}`);}
    else if(goalRow.read_only===true)add('Berekend SG-doel',({profile_unconfirmed:'SG-tapwaterpercentage nog niet lokaal bevestigd',profile_invalid:'SG-tapwaterpercentage niet bruikbaar',profile_confirmation_invalid:'Lokale bevestiging ontbreekt of heeft geen geldig tijdstip',profile_source_unbound:'De lokale bevestiging hoort nog niet bij deze tankbron',normal_target_unavailable:'Normaal tankdoel ontbreekt of is niet actueel',calculated_target_out_of_range:'Berekend doel buiten het beschikbare weergavebereik'})[goalRow.reason]||'Geen actueel berekend SG-doel');
    return `<section data-heatpump-provenance><h3>Taak, metingen en herkomst</h3>${this._reasonFacts(rows)}${this._heatpumpSourceContractDetails(c)}<p class="note">Een berekend SG-doel is een weergave op basis van het normaal gemelde doel en het lokaal bevestigde percentage; Panasonic meldt het effectieve doel niet afzonderlijk. De ventilatoranimatie volgt bevestigd bedrijf of actueel hoofdverbruik. Animatie en elektrisch verbruik bevestigen geen draaiende compressor. De bijverwarming wordt afzonderlijk uit haar voeding afgeleid; Panasonic stuurt haar zelfstandig.</p></section>`;
  }
  _heatpumpTankObservation(c,key){
    const p=c.panasonic||{},tank=p.display_tank;
    const temperature=key==='temperature_c',role=temperature?'tank_temperature_entity':'tank_target_entity';
    if(tank&&tank.available===true&&this._freshObservation(tank[temperature?'temperature_stamp':'target_stamp'],p.source_stale_s??120))return{value:tank[key],entity:tank.entity_id,source:'display_tank',role,reportedAt:tank[temperature?'temperature_stamp':'target_stamp']};
    return this._panasonicSourceFresh(p,temperature?'temperature':'target')?{value:p[key],entity:p[temperature?'temperature_entity':'target_entity'],source:'configured',role,reportedAt:p[temperature?'temperature_stamp':'target_stamp']}: {value:null};
  }
  _heatpumpTankValue(c,key){return this._heatpumpTankObservation(c,key).value;}
  _heatpumpTankReading(c,key){const observation=this._heatpumpTankObservation(c,key);return spTankHistoryValue(observation.value,observation);}
  _heatpumpTankSummary(c){
    const goal=this._heatpumpCalculatedGoal(c),rows=[['Boilertemperatuur',this._heatpumpTankReading(c,'temperature_c')],['Ingesteld boilerdoel',this._heatpumpTankReading(c,'target_c')]];
    if(goal)rows.push([goal.label,spTemp(goal.value)]);
    return `<div class="heatpump-tank-summary" data-boiler-temperatures><div class="start-facts">${rows.map(([label,value])=>`<span>${spEscape(label)}<b>${value}</b></span>`).join('')}</div>${this._heatpumpGoalSetup(c)}</div>`;
  }
  _heatpumpGoalSetup(c){
    const row=c.panasonic?.sg_tank_goal;
    if(row?.read_only!==true||this._heatpumpCalculatedGoal(c))return '';
    const reason=({profile_unconfirmed:'Tapwaterpercentage en tankbron nog bevestigen.',profile_source_unbound:'Kies de tankbron die bij het bevestigde percentage hoort.',profile_invalid:'Controleer het ingestelde tapwaterpercentage.',profile_confirmation_invalid:'Bevestig het tapwaterpercentage opnieuw.',normal_target_unavailable:'Het normale boilerdoel ontbreekt of is niet actueel.',calculated_target_out_of_range:'Het berekende doel valt buiten het weergavebereik.'})[row.reason]||'Er is geen actueel berekend SG-doel beschikbaar.';
    return `<div data-sg-goal-setup><p class="note"><b>SG-doel:</b> ${spEscape(reason)} De getoonde ingestelde waarde is het normale Panasonic-doel.</p><button type="button" class="mini" data-action="configure" data-config-step="sg_sources">SG-doel voor weergave instellen</button></div>`;
  }
  _heatpumpCalculatedGoal(c,{diagnostic=false}={}){
    const p=c.panasonic||{},row=p.sg_tank_goal,tank=p.display_tank,goal=spCalculatedTankGoal(row,{stale:p.source_stale_s??120});
    if(!goal||tank?.available!==true||tank.target_c!==goal.normal||tank.target_stamp!==row.normal_target_reported_at||!this._freshObservation(tank.target_stamp,p.source_stale_s??120))return null;
    const state=this._sgDisplayStates(c).relay.state;
    return {...goal,label:state==='active'?'SG-doel · berekend':'SG-doel bij AAN · berekend'};
  }
  _heatpumpReason(c){
    const s=c.sgBoost||{};
    if(!s.configured)return 'Panasonic regelt zelfstandig; SG-zonneboost is nog niet gekoppeld.';
    if(!this._freshObservation(s.observed_at,s.relay_stale_s??120))return 'Wacht op actuele SolarPilot-status; de laatste SG-beslisreden is verouderd.';
    if(s.reason==='SG-contact actief; Panasonic-reactie niet afzonderlijk bevestigd'&&this._sgDisplayStates(c).received.state==='unknown')return 'SG-contact actief.';
    return s.reason||'Panasonic regelt zelfstandig.';
  }
  _heatpumpGraphic(c){
    const operation=this._heatpumpPresentation(c);
    if(!operation.known)return '';
    return `<div class="heatpump-operation is-${operation.state}" data-heatpump-operation="${operation.state}" data-evidence="${spEscape(operation.evidence)}" data-compressor-running="${operation.compressorRunning===true}" data-fan-active="${operation.fanActive===true}"><svg class="heatpump-icon" viewBox="0 0 48 48" aria-hidden="true"><rect x="4" y="4" width="40" height="40" rx="10"/><g class="heatpump-fan"><path d="M24 23C16 20 17 10 23 12C28 13 26 20 24 23ZM25 24C28 16 38 17 36 23C35 28 28 26 25 24ZM24 25C32 28 31 38 25 36C20 35 22 28 24 25ZM23 24C20 32 10 31 12 25C13 20 20 22 23 24Z"/></g><circle cx="24" cy="24" r="3"/></svg><div><strong>${spEscape(operation.label)}</strong>${operation.note?`<small>${spEscape(operation.note)}</small>`:''}</div></div>`;
  }
  _sgDisplayStates(c){
    const p=c.panasonic||{},s=c.sgBoost||{};
    const snapshotFresh=this._freshObservation(s.observed_at,s.relay_stale_s??120);
    const sessionElapsed=s.desired_on===true&&typeof s.remaining_s==='number'&&this._sgCountdown(s,'remaining_s')===0;
    const requestKnown=snapshotFresh&&typeof s.desired_on==='boolean'&&!sessionElapsed;
    const timerReported=s.relay_valid_until!=null;
    const contactTimerExpired=s.relay_on===true&&timerReported&&
      (typeof s.relay_valid_until!=='number'||!Number.isFinite(s.relay_valid_until)||Date.now()/1000>=s.relay_valid_until);
    const relayKnown=s.relay_confirmed===true&&typeof s.relay_on==='boolean'&&!contactTimerExpired&&this._freshObservation(s.relay_observed_at,s.relay_stale_s??120);
    const receivedKnown=p.sg_status_confirmed===true&&['active','inactive'].includes(p.sg_status)&&this._panasonicSourceFresh(p,'received');
    return {request:{state:requestKnown?(s.desired_on?'active':'inactive'):'unknown',label:requestKnown?(s.desired_on?'Aangevraagd':'Niet aangevraagd'):'Onbekend'},
      relay:{state:relayKnown?(s.relay_on?'active':'inactive'):'unknown',label:relayKnown?(s.relay_on?'Actief':'Open'):'Nog niet bevestigd'},
      received:{state:receivedKnown?p.sg_status:'unknown',label:receivedKnown?(p.sg_status==='active'?'Actief · afzonderlijk bevestigd':'Niet actief · afzonderlijk bevestigd'):'Onbekend'}};
  }
  _sgStatusStrip(c){
    const states=this._sgDisplayStates(c),s=c.sgBoost||{};
    const items=[['relay','SG-contact','Gemelde contactstand; deze is onafhankelijk van compressorbedrijf.']];
    if(states.received.state!=='unknown')items.push(['received','Ontvangen door Panasonic','Afzonderlijk bevestigd met een actuele ontvangen-SG-bron.']);
    const mismatch=states.request.state!=='unknown'&&states.relay.state!=='unknown'&&states.request.state!==states.relay.state;
    const warning=mismatch?states.request.state==='active'?'Zonneboost aangevraagd; het SG-contact staat nog open.':'Geen zonneboost aangevraagd; het SG-contact is nog actief.':'';
    return `<div class="sg-status-strip" aria-label="SG-contact en beschikbare ontvangstmelding">${items.map(([key,label,title])=>`<div class="sg-stage is-${states[key].state}" data-sg-stage="${key}" title="${spEscape(title)}"><span>${spEscape(label)}</span><strong>${spEscape(states[key].label)}</strong></div>`).join('')}</div>${warning?`<p class="note sg-signal-warning"><b>${spEscape(warning)}</b></p>`:''}<p class="note sg-policy">Zonneboost: <b>${s.enabled===true?'toegelaten':s.enabled===false?'uitgeschakeld':'onbekend'}</b></p>${this._sgManualControl(c)}${this._sgWaitBanner(c)}${this._sgMinimumBanner(c)}${this._sgCloudBanner(c)}`;
  }
  _sgManualState(c){
    const s=c.sgBoost||{},value=s.manual_control,object=value&&typeof value==='object'&&!Array.isArray(value);
    const fresh=this._freshObservation(s.observed_at,s.relay_stale_s??120),mode=object&&['auto','on','off'].includes(value.mode)?value.mode:null;
    const reason=fresh&&typeof value?.reason==='string'?value.reason.slice(0,600):'';
    if(!object||!fresh||!mode)return {mode:null,label:'Bedieningskeuze onbekend',remaining:null,duration:null,reason:''};
    if(mode==='auto')return {mode,label:'Automatisch',remaining:null,duration:null,reason};
    const duration=[1800,3600].includes(value.duration_s)?value.duration_s:null;
    const valid=duration!=null&&typeof value.expires_at==='number'&&Number.isFinite(value.expires_at)&&value.expires_at>0&&typeof value.remaining_s==='number'&&Number.isFinite(value.remaining_s)&&value.remaining_s>=0&&value.remaining_s<=duration&&value.expires_at-s.observed_at<=duration+1;
    const remaining=valid?Math.ceil(Math.max(0,Math.min(value.expires_at-Date.now()/1000,value.remaining_s-Math.max(0,Date.now()/1000-s.observed_at)))):null;
    return {mode,label:mode==='on'?'Handmatig AAN · aanvraag':'Handmatig UIT',remaining,duration,reason};
  }
  _sgManualControl(c){
    const s=c.sgBoost||{},state=this._sgManualState(c),value=s.manual_control;
    const supported=value&&typeof value==='object'&&!Array.isArray(value),admin=this._hass?.user?.is_admin===true;
    const ready=supported&&s.configured===true&&!!c.a?.config_entry_id&&typeof this._hass?.callService==='function'&&admin&&!this._busy;
    const choice=(mode,duration,label)=>`<button type="button" class="mini ${state.mode===mode&&(mode==='auto'||state.duration===duration)&&state.remaining!==0?'active':''}" data-action="sg_manual_control" data-sg-mode="${mode}"${duration?` data-sg-duration="${duration}"`:''} aria-pressed="${state.mode===mode&&(mode==='auto'||state.duration===duration)&&state.remaining!==0}" ${ready&&(mode!=='on'||s.enabled===true&&c.a.mode==='solar')?'':'disabled'}>${label}</button>`;
    const clock=state.mode==='on'||state.mode==='off'?state.remaining==null?'Resterende tijd onbekend':state.remaining===0?'Tijd verstreken · wacht op automatische beoordeling':`Nog ${this._sgWaitTime(state.remaining)} · daarna automatisch`:'';
    const blocked=state.mode==='on'&&this._freshObservation(s.observed_at,s.relay_stale_s??120)&&s.desired_on!==true;
    const reason=blocked?(state.reason||this._heatpumpReason(c)):'';
    return `<section class="sg-manual-control" data-sg-manual-control="${state.mode||'unknown'}" aria-label="Tijdelijke SG-bediening"><div class="sg-manual-head"><strong>SG-bediening ${this._question('dashboard','sg_manual_control','Tijdelijke SG-bediening')}</strong><span data-sg-control-mode>${spEscape(state.label)}</span></div>${clock?`<p class="note" data-sg-control-countdown>${spEscape(clock)}</p>`:''}<div class="sg-manual-actions">${choice('auto',null,'Automatisch')}${choice('on',1800,'Aan · 30 min')}${choice('on',3600,'Aan · 1 uur')}${choice('off',1800,'Uit · 30 min')}${choice('off',3600,'Uit · 1 uur')}</div>${this._sgManualBusy?'<p class="note" role="status">Bedieningskeuze versturen…</p>':''}${reason?`<p class="note sg-manual-blocked" data-sg-control-blocked><b>Aanvraag wacht:</b> ${spEscape(this._plainReason(reason))}</p>`:''}${!supported?'<p class="note">Tijdelijke bediening is nog niet beschikbaar; werk integratie en kaart samen bij.</p>':!admin?'<p class="note">Een Home Assistant-beheerder kan de SG-bediening wijzigen.</p>':s.enabled!==true?'<p class="note">Schakel zonneboost in om tijdelijk AAN te kunnen aanvragen.</p>':c.a.mode!=='solar'?'<p class="note">Kies Automatisch regelen om tijdelijk AAN te kunnen aanvragen.</p>':''}<small>Na afloop terug naar automatisch. Veiligheidsvoorwaarden blijven gelden.</small></section>`;
  }
  _sgCountdown(s,key){
    const value=s[key];
    if(typeof value!=='number'||!Number.isFinite(value)||!this._freshObservation(s.observed_at,s.relay_stale_s??120))return null;
    return Math.max(0,value-Math.max(0,Date.now()/1000-s.observed_at));
  }
  _sgWaitTime(value){const seconds=Math.max(0,Math.ceil(value)),minutes=Math.floor(seconds/60);return minutes?`${minutes} min${seconds%60?' '+seconds%60+' s':''}`:`${seconds} s`;}
  _sgWaitCountdown(s,key){
    const value=s[key],until=s[({start_remaining_s:'start_valid_until',start_cloud_remaining_s:'start_cloud_valid_until'})[key]||'reassessment_valid_until'];
    if(typeof value!=='number'||!Number.isFinite(value)||value<0||typeof until!=='number'||!Number.isFinite(until)||Date.now()/1000>until||!this._freshObservation(s.observed_at,s.relay_stale_s??120))return null;
    return Math.ceil(Math.max(0,value-Math.max(0,Date.now()/1000-s.observed_at)));
  }
  _sgRequestRest(c){
    const s=c.sgBoost||{},rearm=s.rearm_wait||{},raw=rearm.request_rest_remaining_s;
    const reported=Number.isInteger(raw)&&raw>=0?raw:s.rest_remaining_s;
    const fresh=this._freshObservation(s.observed_at,s.relay_stale_s??120)&&c.a?.restored!==true;
    const remaining=fresh&&typeof reported==='number'&&Number.isFinite(reported)&&reported>=0?Math.ceil(Math.max(0,reported-Math.max(0,Date.now()/1000-s.observed_at))):null;
    const replaceable=fresh&&remaining>0&&Number.isInteger(raw)&&raw>0&&rearm.request_rest_replaceable===true&&s.profile==='general'&&s.completion_hold===true&&s.policy_hold_reason==='response_unknown'&&s.desired_on===false&&s.manual_hold!==true&&!s.fault&&this._sgDisplayStates(c).relay.state==='inactive';
    return {remaining,replaceable,label:replaceable?`SG-herhaalwacht: nog ${this._sgWaitTime(remaining)}. Kan eerder vervallen na 5 min verse echte restinjectie, een bevestigd open SG-contact en alle actuele voorwaarden. Daarna geldt de gewone startvertraging.`:''};
  }
  _sgWaitProgress(c){
    const manual=this._sgManualState(c);if(['on','off'].includes(manual.mode)&&manual.remaining!==0)return null;
    const s=c.sgBoost||{},fresh=this._freshObservation(s.observed_at,s.relay_stale_s??120);
    const kinds={new_solar_period:'Nieuw zonneoverschot',fresh_native_context:'Gewijzigde Panasonic-context',fresh_residual_surplus:'Actueel restoverschot',solar_reset:'Zonneperiode resetten',native_reset:'Panasonic-context resetten'};
    if(s.completion_hold===true&&s.profile==='general'){
      const kind=kinds[s.reassessment_kind],required=s.reassessment_required_s;
      const valid=fresh&&s.reassessment_source_current===true&&kind&&s.reassessment_state==='confirming_'+s.reassessment_kind&&typeof required==='number'&&Number.isFinite(required)&&required>0&&typeof s.reassessment_remaining_s==='number'&&s.reassessment_remaining_s<=required;
      const remaining=valid?this._sgWaitCountdown(s,'reassessment_remaining_s'):null;
      const waitingNew=fresh&&s.reassessment_state==='waiting_new_evidence'&&s.reassessment_source_current===true;
      const residual=s.reassessment_kind==='fresh_residual_surplus',number=value=>typeof value==='number'&&Number.isFinite(value)&&value>=0;
      const residualProof=valid&&remaining!=null&&number(s.real_residual_surplus_w)&&number(s.residual_reassessment_threshold_w)?` Restoverschot ${spPower(s.real_residual_surplus_w)} · nodig ${spPower(s.residual_reassessment_threshold_w)}.`:'';
      const requestRest=this._sgRequestRest(c),restNote=requestRest.replaceable?' '+requestRest.label:'';
      return{phase:'reassessment',title:residual?'Nieuwe SG-sessie · restoverschot herbevestigen':'Nieuwe SG-sessie · herbevestiging',remaining,required:typeof required==='number'&&Number.isFinite(required)&&required>0?required:null,
        label:(remaining!=null?(remaining===0||s.reassessment_final_report_required===true?`${kind}: tijd verstreken · wacht op verse bevestiging.`:`${kind}: nog ${this._sgWaitTime(remaining)} van ${this._sgWaitTime(required)}.`):waitingNew?(s.residual_reassessment_available===true?'Wacht op voldoende actueel restoverschot, een nieuwe zonneperiode of gewijzigde Panasonic-context.':'Wacht op nieuwe zonneperiode of gewijzigde Panasonic-context.'):'Herbevestiging onbekend · wacht op actuele brongegevens.')+residualProof+restNote};
    }
    if((s.state==='waiting_surplus'||s.start_cloud_active===true)&&s.completion_hold!==true){
      const required=s.start_required_s,valid=typeof required==='number'&&Number.isFinite(required)&&required>=0&&typeof s.start_remaining_s==='number'&&Number.isFinite(s.start_remaining_s)&&s.start_remaining_s>=0&&s.start_remaining_s<=required;
      if(s.start_cloud_active===true){
        const kind=['cloud','measurement_gap'].includes(s.start_cloud_kind)?s.start_cloud_kind:null;
        const graceValid=fresh&&kind&&typeof s.start_cloud_remaining_s==='number'&&Number.isFinite(s.start_cloud_remaining_s)&&s.start_cloud_remaining_s>=0&&s.start_cloud_remaining_s<=300&&typeof s.start_cloud_valid_until==='number'&&Number.isFinite(s.start_cloud_valid_until)&&Date.now()/1000<=s.start_cloud_valid_until;
        const grace=graceValid?this._sgWaitCountdown(s,'start_cloud_remaining_s'):null;
        const remaining=graceValid&&valid?Math.ceil(Math.max(0,s.start_remaining_s-Math.max(0,Date.now()/1000-s.observed_at))):null;
        const title=kind==='cloud'?'Wolkendip · inschakelwachttijd loopt door':kind==='measurement_gap'?'Korte meetonderbreking · inschakelwachttijd loopt door':'Inschakelwachttijd · bronstatus onbekend';
        const wait=remaining==null?'Resterende inschakelwachttijd onbekend.':remaining===0?'Wachttijd verstreken · '+(kind==='cloud'?'wacht op voldoende zon.':'wacht op actuele meting.'):`Nog ${this._sgWaitTime(remaining)} inschakelwachttijd.`;
        const buffer=grace==null?'Resterende overbrugging onbekend.':grace===0?'Overbrugging verstreken · wacht op actuele beoordeling.':`Nog ${this._sgWaitTime(grace)} van maximaal 5 min overbrugging.`;
        return{phase:'start_gap',kind,title,remaining,required:valid?required:null,grace,label:wait+' '+buffer+' SG start pas bij actuele voldoende zon en veilige voorwaarden.'};
      }
      const remaining=valid?this._sgWaitCountdown(s,'start_remaining_s'):null;
      return{phase:'start',title:'SG-startvertraging',remaining,required:valid?required:null,label:remaining==null?'Resterende startvertraging onbekend · wacht op actuele brongegevens.':remaining===0?'Tijd verstreken · wacht op actuele beoordeling.':`Voldoende overschot bevestigen · nog ${this._sgWaitTime(remaining)} van ${this._sgWaitTime(required)}.`};
    }
    return null;
  }
  _sgWaitBanner(c){const wait=this._sgWaitProgress(c);return wait?`<p class="note sg-wait" data-sg-wait="${wait.phase}"><b>${spEscape(wait.title)}</b><br>${spEscape(wait.label)}</p>`:'';}
  _sgMinimumProgress(c){
    const manual=this._sgManualState(c);if(['on','off'].includes(manual.mode)&&manual.remaining!==0)return null;
    const s=c.sgBoost||{},number=value=>typeof value==='number'&&Number.isFinite(value)&&value>=0;
    if(s.desired_on!==true||!number(s.min_session_s))return null;
    const states=this._sgDisplayStates(c),required=number(s.effective_min_session_s)&&s.effective_min_session_s<=s.min_session_s?s.effective_min_session_s:null;
    const valid=states.request.state==='active'&&states.relay.state==='active'&&s.lease_confirmed===true&&s.owner==='solarpilot'&&this._sgCountdown(s,'lease_remaining_s')>0&&number(s.minimum_valid_until)&&Date.now()/1000<s.minimum_valid_until&&required!=null&&number(s.minimum_remaining_s)&&s.minimum_remaining_s<=Math.ceil(required)&&(s.minimum_remaining_s===0||s.minimum_active===true);
    const remaining=valid?Math.ceil(Math.max(0,s.minimum_remaining_s-Math.max(0,Date.now()/1000-s.observed_at))):null;
    return{configured:s.min_session_s,required,remaining,limited:s.minimum_limited_by_max===true,importHold:remaining>0&&s.minimum_import_hold===true,
      label:remaining==null?'Resterende minimumduur onbekend · wacht op actuele SG-status.':remaining===0?'Minimum verstreken · actuele regeling bepaalt het vrijgeven.':`Nog ${this._sgWaitTime(remaining)} · alleen de SG-aanvraag.`};
  }
  _sgMinimumBanner(c){
    const minimum=this._sgMinimumProgress(c);if(!minimum)return '';
    return `<p class="note sg-minimum" data-sg-minimum><b>Minimum SG-aanvraagduur${minimum.required==null?'':` · ${spEscape(this._sgWaitTime(minimum.required))}`}</b><br>${spEscape(minimum.label)}${minimum.importHold?'<br>Tijdelijke netafname: minimum SG-aanvraagduur loopt nog.':''}${minimum.limited?'<br>De bestaande maximale sessieduur begrenst het minimum.':''}<br>Na het minimum kan SG doorgaan zolang de normale voorwaarden kloppen.<br>Panasonic bepaalt zelf de compressorlooptijd; beveiligingen kunnen SG eerder vrijgeven.</p>`;
  }
  _sgCloudProgress(c){
    const manual=this._sgManualState(c);if(['on','off'].includes(manual.mode)&&manual.remaining!==0)return null;
    const s=c.sgBoost||{},number=value=>typeof value==='number'&&Number.isFinite(value)&&value>=0;
    if(s.desired_on!==true||!number(s.import_threshold_w)||!number(s.stop_delay_s))return null;
    const states=this._sgDisplayStates(c),current=states.request.state==='active'&&states.relay.state==='active'&&s.lease_confirmed===true&&s.owner==='solarpilot'&&this._sgCountdown(s,'lease_remaining_s')>0&&number(s.cloud_valid_until)&&Date.now()/1000<s.cloud_valid_until;
    const remaining=current&&number(s.cloud_remaining_s)&&s.cloud_remaining_s<=Math.ceil(s.stop_delay_s)&&(s.cloud_active===true||s.cloud_remaining_s===0)?Math.ceil(Math.max(0,s.cloud_remaining_s-Math.max(0,Date.now()/1000-s.observed_at))):null;
    const idle=current&&s.cloud_active===false&&s.cloud_remaining_s===null;
    return{threshold:s.import_threshold_w,required:s.stop_delay_s,remaining,idle,
      label:remaining!=null?(remaining===0?'Wolkenbuffer verstreken · actuele regeling bepaalt het vrijgeven.':`Netafname boven ${spPower(s.import_threshold_w)} · nog ${this._sgWaitTime(remaining)}.`):idle?'Geen lopende importbuffer.':'Resterende wolkenbuffer onbekend · wacht op actuele net- en SG-status.'};
  }
  _sgCloudBanner(c){
    const cloud=this._sgCloudProgress(c);if(!cloud)return '';
    return `<p class="note sg-cloud" data-sg-cloud><b>Wolkenbuffer · ${spEscape(spPower(cloud.threshold))} / ${spEscape(this._sgWaitTime(cloud.required))}</b><br>${spEscape(cloud.label)}<br>Minimumduur en wolkenbuffer lopen tegelijk; harde beveiligingen kunnen SG eerder vrijgeven.</p>`;
  }
  _heatpumpDisplaySignature(c){
    const p=c.panasonic||{};
    return JSON.stringify([this._heatpumpCalculatedGoal(c,{diagnostic:true}),this._heatpumpDisplayOperation(c),this._heatpumpActivity(c),this._heatpumpPresentation(c),this._heatpumpTaskEvidence(c),this._heatpumpSupplies(c).map(row=>[row.number,row.fresh,row.state,this._heatpumpSupplyProblem(c,row)]),(c.panasonic?.power_activity?.supplies||[]).map(row=>this._freshObservation(row.observed_at,c.panasonic?.power_activity?.stale_s??120)),this._sgDisplayStates(c),this._sgManualState(c),this._sgWaitProgress(c),this._sgMinimumProgress(c),this._sgCloudProgress(c),this._sgCoolingState(c),this._electricalLimits(c),[p.history?.recording,p.history?.storage_available,p.history?.revision,p.history?.recording_error],['power','supply1','supply2','compressor','context','temperature','target'].map(role=>this._panasonicSourceFresh(p,role)),(p.display_zones||p.zones||[]).map(zone=>this._freshObservation(zone.observed_at,p.source_stale_s??120)),['temperature_stamp','target_stamp','observed_at'].map(key=>this._freshObservation(p.display_tank?.[key],p.source_stale_s??120)),['lease_remaining_s','remaining_s','rest_remaining_s'].map(key=>Math.ceil((this._sgCountdown(c.sgBoost||{},key)??-1)/10))]);
  }
  _sgConfirmation(s,p={}){
    const states=this._sgDisplayStates({sgBoost:s,panasonic:p});
    const owner=this._freshObservation(s.observed_at,s.relay_stale_s??120)?(({solarpilot:'SolarPilot',manual:'Handmatige overname',none:'Geen',unknown:'Onbekend'})[s.owner]||(s.manual_hold===true?'Handmatige overname':'Onbekend')):'Onbekend';
    const remaining=this._sgCountdown(s,'lease_remaining_s');
    const lease=s.lease_confirmed===true&&states.relay.state==='active'&&remaining!=null?(remaining>0?this._remainingTime(remaining):'Verlopen; nieuwe bevestiging ontbreekt'):'Niet bevestigd';
    const facts=[['SolarPilot-aanvraag',states.request.label],['Eigenaar SG-aanvraag',owner],['SG-contact',states.relay.label],['Bevestigde lokale toestemming',lease]];
    if(states.received.state!=='unknown')facts.push(['Ontvangen SG-status',states.received.label]);
    return this._reasonFacts(facts);
  }
  _sgObservation(c){
    const p=c.panasonic||{},states=this._sgDisplayStates(c),fresh=this._panasonicSourceFresh(p,'compressor');
    const compressor=fresh&&p.compressor_running===true?' · compressor draait':fresh&&p.compressor_running===false?' · compressor stil':'';
    const frequency=fresh&&typeof p.compressor_frequency_hz==='number'&&Number.isFinite(p.compressor_frequency_hz)?` · ${p.compressor_frequency_hz.toLocaleString('nl-BE',{maximumFractionDigits:1})} Hz`:'';
    const parts=p.power_scope==='split'?` · voeding 1 ${this._supplyPower(p,1)} · voeding 2 ${this._supplyPower(p,2)}`:'';
    return `${states.relay.state==='active'?'SG-contact actief':states.relay.state==='inactive'?'SG-contact open':'SG-contact nog niet bevestigd'}${compressor}${frequency}${parts}`;
  }
  _supplyPower(p,number){
    const value=p[`power_supply${number}_w`];
    return p[`power_supply${number}_valid`]===true&&typeof value==='number'&&Number.isFinite(value)&&value>=0&&this._panasonicSourceFresh(p,`supply${number}`)?spPower(value):'onbekend';
  }
  _heatpumpPower(c){
    const p=c.panasonic||{},s=c.sgBoost||{},power=p.power_activity||{};
    const value=p.power_w??s.power_w,kind=p.power_kind??s.power_kind,scope=p.power_scope??s.power_scope;
    const supplyRows=this._heatpumpSupplies(c);
    const completeFeedsFresh=!supplyRows.length||supplyRows.every(row=>row.valid===true&&typeof row.watts==='number'&&Number.isFinite(row.watts)&&row.watts>=0&&this._freshObservation(row.observed_at,power.stale_s??p.source_stale_s??120));
    const known=typeof value==='number'&&Number.isFinite(value)&&value>=0&&['measured','estimated'].includes(kind)&&this._panasonicSourceFresh(p,'power')&&(scope!=='split'||p.power_complete===true&&completeFeedsFresh);
    const labels={total:'Totaal warmtepomp',heat_pump:'Totaal warmtepomp',split:known&&p.power_complete===true?'Totaal voeding 1 + voeding 2':'Totaal onbekend · deelmeting onvolledig',supply_1:'Alleen voeding 1 · gedeeltelijke meting',supply1:'Alleen voeding 1 · gedeeltelijke meting',supply_2:'Alleen voeding 2 · gedeeltelijke meting',supply2:'Alleen voeding 2 · gedeeltelijke meting',heater:'Alleen elektrische ondersteuning',unknown:'Dekking onbekend',unconfirmed:'Dekking nog niet bevestigd'};
    const supplies=scope==='split'||supplyRows.length?supplyRows.length?supplyRows.map(row=>{
      const fresh=row.fresh;
      const title=`Voeding ${row.number}${row.role==='main'?' · warmtepomp':row.role==='heater'?' · elektrische bijverwarming':''}`;
      const problem=this._heatpumpSupplyProblem(c,row),missingLabel=problem?.label||'Geen actuele meting';
      const state=fresh?row.watts===0?'Geen verbruik':({active:'Actief verbruik',basis:'Basisverbruik'})[row.state]||'Gemeten verbruik':'Geen actuele meting';
      const feedState=fresh?(row.watts===0?'off':['active','basis'].includes(row.state)?row.state:'known'):'unknown';
      return `<div class="heatpump-supply" data-supply-number="${spEscape(row.number)}" data-supply-state="${feedState}" data-supply-quality="${fresh?'valid':problem?.state||'unknown'}"><span><b>${spEscape(title)}</b></span><span><strong>${fresh?spPower(row.watts):spEscape(missingLabel)}</strong>${fresh?`<small>${spEscape(state)}</small>`:''}</span></div>`;
    }).join(''):`<small>Voeding 1: ${this._supplyPower(p,1)} · Voeding 2: ${this._supplyPower(p,2)}</small>`:'';
    const budget=this._electricalLimits(c),estimate=spNumber(s.estimated_power_w);
    const optionalMeter=!known&&s.configured===true&&this._freshObservation(s.observed_at,s.relay_stale_s??120)&&estimate!=null&&estimate>0&&spNumber(budget?.sg_residual_solar_w)!=null&&budget.sg_residual_solar_w>=0;
    return `<div class="reason-power"><b>${known?spPower(value):'Vermogen nog niet bekend'}</b><small>${spEscape(p.power_label||labels[scope]||'Dekking onbekend')}${known?(kind==='estimated'?' · geschat':' · gemeten'):''}</small>${supplies}${optionalMeter?`<small data-sg-optional-meter>SG gebruikt actuele P1/PV-metingen en ${spPower(estimate)} geraamde extra opname. Warmtepompbijdrage blijft onbekend.</small>`:''}</div>`;
  }
  _electricalLimits(c){
    const value=c.ems?.electrical_limits;
    if(!value)return null;
    const fresh=value.source_valid===true&&this._freshObservation(value.source_observed_at,value.source_stale_s??120);
    const solarFresh=value.sg_solar_valid===true&&this._freshObservation(value.sg_solar_observed_at,value.source_stale_s??120);
    return {...value,instantaneous_headroom_w:fresh?value.instantaneous_headroom_w:null,
      sg_eligible_solar_w:solarFresh?value.sg_eligible_solar_w:null,
      sg_hp_solar_w:solarFresh?value.sg_hp_solar_w:null,
      sg_residual_solar_w:solarFresh?value.sg_residual_solar_w:null};
  }
  _sgCoolingState(c){
    const s=c.sgBoost||{},p=c.panasonic||{},value=s.cooling_diagnostic?.schema===1?s.cooling_diagnostic:p.cooling_context_diagnostic;
    if(!value||value.schema!==1||value.read_only!==true||!Array.isArray(value.sources))return null;
    const untilCurrent=(stamp,until,stale)=>this._freshObservation(stamp,stale)&&typeof until==='number'&&Number.isFinite(until)&&Date.now()/1000<=until;
    const rows=value.sources.slice(0,16).filter(row=>row&&typeof row==='object').map(row=>({...row,
      current:row.fresh===true&&untilCurrent(row.observed_at,row.valid_until,row.stale_s??value.stale_s??120),
      nativeCurrent:row.native_fresh===true&&untilCurrent(row.native_observed_at,row.native_valid_until,row.native_stale_s??value.stale_s??120)}));
    const expired=rows.some(row=>row.fresh===true&&!row.current||['auto','heat_cool'].includes(String(row.mode||'').toLowerCase())&&row.native_fresh===true&&!row.nativeCurrent)||value.code==='heating_only_confirmed'&&!untilCurrent(value.context_observed_at,value.valid_until,value.stale_s??120);
    const code=expired?'context_expired':String(value.code||'native_context_unknown');
    const summary=expired?'De Panasonic-koelcontext is verouderd; een actuele bronmelding ontbreekt.':String(value.summary||'De Panasonic-koelcontext is niet bekend.');
    const action=expired?'Controleer of de Panasonic-integratie nieuwe meldingen ontvangt.':String(value.action||'Controleer de gekoppelde Panasonic-ruimtes en het actuele programma.');
    const condition=s.profile==='dhw_only'?(s.profile_confirmed===true?'Koelvoorwaarde niet vereist voor het lokaal bevestigde tapwaterprofiel':'Tapwaterprofiel nog niet lokaal bevestigd'):s.profile!=='general'?'SG-profiel nog niet bekend':s.cooling_protection_confirmed===true?'Condens-/dauwpuntbeveiliging lokaal bevestigd':code==='heating_only_confirmed'?'Koeling uitgesloten door actuele gekoppelde bronnen':'Koelvoorwaarde wacht op betrouwbare context of bevestigde fysieke beveiliging';
    return {code,summary,action,condition,rows,sourceCount:value.source_count,truncated:value.sources_truncated===true};
  }
  _sgCoolingDetails(c){
    const value=this._sgCoolingState(c);if(!value)return '';
    const sourceLabels={zone_source_missing:'Entiteit ontbreekt',zone_source_unavailable:'Entiteit niet beschikbaar',zone_source_stale:'Bronmelding verouderd of ongeldig'};
    const rows=value.rows.map(row=>{
      const status=row.current?'Actuele bronmelding':sourceLabels[row.source_code]||'Bronmelding verouderd of ongeldig';
      const facts=[['Entiteit',row.entity_id||'Niet bekend'],['Bronstatus',status],['Gemelde stand',this._climateModeLabel(String(row.mode||'').toLowerCase())],['Gemelde actie',row.action||'Niet gemeld'],['Laatste bronmelding',this._reasonTime(row.observed_at)||'Niet bekend'],['Werkelijk Panasonic-programma',row.nativeCurrent?this._panasonicProgramLabel(row.native_program):'Niet actueel bevestigd'],['Oorspronkelijk programma',row.native_raw_mode||'Niet gemeld'],['Programmabron',row.native_source||'Niet beschikbaar'],['Laatste programmamelding',this._reasonTime(row.native_observed_at)||'Niet bekend']];
      if(!row.nativeCurrent&&row.native_reason)facts.push(['Programmabron wacht op',row.native_reason]);
      return `<div class="sg-cooling-source"><strong>${spEscape(row.name||'Panasonic-ruimte')}</strong>${this._reasonFacts(facts)}</div>`;
    }).join('');
    return `<section class="sg-cooling-diagnostic" data-sg-cooling-code="${spEscape(value.code)}"><h3>Koelcontext en SG-vrijgave</h3><p><b>${spEscape(value.condition)}</b></p><p>${spEscape(value.summary)}</p><p><b>Actie:</b> ${spEscape(value.action)}</p>${rows||'<p>Geen Panasonic-ruimtes gekoppeld als SG-leesbron.</p>'}${value.truncated?`<p>${spEscape(value.sourceCount)} gekoppelde bronnen; de eerste 16 staan hier.</p>`:''}<p class="note">Een lokale bevestiging hoort bij de werkelijke condens-/dauwpuntbeveiliging van de installatie. Tankopwarming en sterilisatie wijzigen deze koelvoorwaarde niet.</p><button type="button" class="mini" data-action="configure" data-config-step="sg_boost">SG-leesbronnen bekijken</button></section>`;
  }
  _sgTransportDetails(c,scope){
    const s=c.sgBoost||{},stop=s.last_session,current=s.transport_evidence,previous=stop?.transport;
    if(!current&&!previous)return '';
    const zone=this._hass?.config?.time_zone;
    return `<details data-ui-key="sg:${spEscape(scope)}:transport"><summary>SG-stopbesluit en transport</summary><dl class="investigation-metrics"><div><dt>Laatste stopbesluit</dt><dd>${stop?spEscape(spProofClock(stop.ended_at,zone)+' · '+String(stop.reason||'Reden onbekend').slice(0,240)):'Onbekend'}</dd></div><div><dt>Transport bij die stop</dt><dd>${spEscape(spTransportProof(previous))} · ${spEscape(spProofClock(previous?.observed_at,zone))}</dd></div><div><dt>Laatste transportstap</dt><dd>${spEscape(spTransportProof(current))} · ${spEscape(spProofClock(current?.observed_at,zone))}</dd></div></dl><p class="note">Dit zijn afzonderlijke geregistreerde momenten. Een latere geslaagde lezing bevestigt geen eerdere UIT-opdracht. Contactstand en Panasonic-ontvangst behouden hun eigen bronbewijs.</p></details>`;
  }
  _sgDetails(c,scope='comfort'){
    const s=c.sgBoost||{},p=c.panasonic||{},zones=Array.isArray(p.display_zones)?p.display_zones:Array.isArray(p.zones)?p.zones:[];
    const profile=({general:'Algemene SG-boost',dhw_only:'Uitsluitend tapwater'})[s.profile]||'Niet bekend';
    const context=p.context_reliable===true&&this._panasonicSourceFresh(p,'context')?p.status||'Betrouwbare bedrijfscontext beschikbaar':'Bedrijfscontext onbekend of verouderd';
    const cooling=s.profile==='dhw_only'?(s.profile_confirmed===true?'Niet vereist voor bevestigd tapwaterprofiel':'Tapwaterprofiel nog niet bevestigd'):s.profile==='general'?(s.cooling_protection_confirmed===true?'Lokaal bevestigd':'Niet bevestigd · geen extra SG in koelbedrijf of onzekere koelcontext'):'SG-profiel onbekend';
    const facts=[['Toepassingsbereik',profile],['Profiel lokaal bevestigd',s.profile_confirmed===true?'Ja':'Nee'],['Extra-koelbeveiliging',cooling],['Tanktemperatuur',spTemp(this._heatpumpTankValue(c,'temperature_c'))],['Gemeld tankdoel',spTemp(this._heatpumpTankValue(c,'target_c'))],['Startdrempel',spPower(s.start_threshold_w)],['Voorlopige vermogensraming',spPower(s.estimated_power_w)],['Resterende sessie',this._remainingTime(this._sgCountdown(s,'remaining_s'))],['SG-herhaalwacht',this._remainingTime(this._sgRequestRest(c).remaining)]];
    const provenance=s.active_session_provenance||s.last_session?.session_provenance;
    if(provenance?.schema===1)facts.push(['Vastgelegde sessieversie',provenance.release||'Onbekend'],['Sessieregels',typeof provenance.policy_hash==='string'?provenance.policy_hash.slice(0,16):'Onbekend']);
    const rearm=s.rearm_wait;
    if(rearm){facts.push(['Oorspronkelijke stopreden',rearm.original_stop_reason||'Niet vastgelegd'],['Actuele herstartvoorwaarde',rearm.current_condition||'Nog niet bekend']);}
    const wait=this._sgWaitProgress(c);
    facts.push(['Ingestelde startvertraging',typeof s.start_required_s==='number'&&Number.isFinite(s.start_required_s)&&s.start_required_s>=0?this._sgWaitTime(s.start_required_s):'nog niet bekend']);
    facts.push(['Ingesteld SG-minimum',typeof s.min_session_s==='number'&&Number.isFinite(s.min_session_s)&&s.min_session_s>=0?this._sgWaitTime(s.min_session_s):'nog niet bekend'],['Effectief SG-minimum',typeof s.effective_min_session_s==='number'&&Number.isFinite(s.effective_min_session_s)&&s.effective_min_session_s>=0?this._sgWaitTime(s.effective_min_session_s):'nog niet bekend']);
    const minimum=this._sgMinimumProgress(c);if(minimum)facts.push(['Resterende minimumduur',minimum.label]);
    facts.push(['Drempel netafname wolkenbuffer',typeof s.import_threshold_w==='number'&&Number.isFinite(s.import_threshold_w)&&s.import_threshold_w>=0?spPower(s.import_threshold_w):'nog niet bekend'],['Aaneengesloten bufferduur',typeof s.stop_delay_s==='number'&&Number.isFinite(s.stop_delay_s)&&s.stop_delay_s>=0?this._sgWaitTime(s.stop_delay_s):'nog niet bekend']);
    const cloud=this._sgCloudProgress(c);if(cloud)facts.push(['Resterende wolkenbuffer',cloud.label]);
    if(wait)facts.push([wait.phase==='reassessment'?'Herbevestiging nieuwe SG-sessie':'Resterende startvertraging',wait.label]);
    if(wait?.phase==='reassessment')facts.push(['Vereiste herbevestiging',wait.required==null?'nog niet bekend':this._sgWaitTime(wait.required)],['Verse bronmeldingen',wait.remaining!=null&&Number.isInteger(s.reassessment_reports)&&s.reassessment_reports>0?String(s.reassessment_reports):'nog niet bekend']);
    const electrical=this._electricalLimits(c);
    if(electrical){
      facts.push(['Zonnevermogen voor SG-drempel',spPower(electrical.sg_eligible_solar_w)],['Warmtepompbijdrage aan startdrempel (afgeleid)',spPower(electrical.sg_hp_solar_w)],['Resterende vrije zonnestroom',spPower(electrical.sg_residual_solar_w)],['Elektrische ruimte nu',spPower(electrical.instantaneous_headroom_w)]);
      if(electrical.sg_protected_ev_headroom_w!=null)facts.push(['Stabiele ruimte na Wallbox',spPower(electrical.sg_protected_ev_headroom_w)]);
      if(electrical.quarter_enabled)facts.push(['Theoretisch kwartierbudget',spPower(electrical.quarter_theoretical_headroom_w)]);
    }
    if(p.power_scope==='split')facts.push(['Voeding 1',this._supplyPower(p,1)],['Voeding 2',this._supplyPower(p,2)]);
    const blocks=Array.isArray(s.blocked_reasons)?s.blocked_reasons:[];
    const sg=this._sgDisplayStates(c);
    return `${this._sgConfirmation(s,p)}${this._sgTransportDetails(c,scope)}${this._heatpumpTechnicalDetails(c)}${this._sgCoolingDetails(c)}${this._reasonFacts(facts)}${electrical?'<p class="note">Zonnestroom die de warmtepomp al gebruikt telt mee voor de SG-startdrempel bij een compleet actueel bevestigd totaal. Dit geeft geen extra net- of faseruimte. De vermogensraming voor bijkomende SG-opname, echte vrije zonnestroom, voorrang en wachttijden blijven afzonderlijk gelden. Het theoretische kwartierbudget verruimt de vaste net- en fasegrenzen nooit.</p>':''}${blocks.length?`<div class="condition-group waiting"><b>Nog nodig</b><ul>${blocks.map(x=>`<li>${spEscape(this._plainReason(typeof x==='string'?x:x.reason))}</li>`).join('')}</ul></div>`:''}${s.uptake_diagnostic&&this._freshObservation(s.observed_at,s.relay_stale_s??120)?`<p class="note">${spEscape(s.uptake_diagnostic)}</p>`:''}<p class="note">Een normaal tankdoel in de app bewijst niet welk effectief SG-doel Panasonic gebruikt. Compressorbedrijf bewijst geen extra verbruik door SG.</p><details data-ui-key="sg:${spEscape(scope)}:monitor"><summary>Panasonic en ruimtes · alleen uitlezen</summary><p>${spEscape(context)}</p><p>${spEscape(this._panasonicSourceFresh(p,'context')?(p.program_label||this._panasonicProgramLabel(p.program)):'Warmtepompprogramma onbekend')}</p><p class="sub">${spEscape(this._sgObservation(c))}</p>${p.power_reason?`<p>${spEscape(p.power_reason)}</p>`:''}${zones.map(z=>{const fresh=z.available!==false&&this._freshObservation(z.observed_at,p.source_stale_s??120);return `<div class="zone"><span><b>${spEscape(z.name||'Ruimte')}</b><small>Gewenst ${spTemp(fresh?(z.target??z.target_c):null)}</small></span><b>${spTemp(fresh?(z.current??z.temperature_c):null)}</b><em>${spEscape(fresh?this._climateModeLabel(String(z.mode||'').toLowerCase()):'Onbekend of verouderd')}${fresh&&z.action_valid!==false&&z.action?` · ${spEscape(({heating:'verwarmt',cooling:'koelt',idle:'niet actief',off:'niet actief'})[z.action]||z.action)}`:''}</em></div>`}).join('')||'<p>Geen betrouwbare ruimtemetingen beschikbaar.</p>'}<p class="note">Panasonic regelt comfort, verwarmen/koelen, elektrische ondersteuning en sterilisatie. SolarPilot schrijft geen tankdoel of kamerstand. Het gemeten verbruik kan na het vrijgeven van SG blijven doorlopen.</p></details>`;
  }
  _heatpump(c,scope='comfort'){
    const s=c.sgBoost||{},p=c.panasonic||{},operation=this._heatpumpPresentation(c);
    const switchEntity=s.enabled_entity,ready=!!switchEntity&&!this._busy;
    const manual=s.manual_hold===true||s.state==='manual_hold';
    return `<section class="heatpump-sg is-${operation.state}" data-activity="${operation.active?'active':operation.known?'inactive':'unknown'}"><div class="sectionhead"><div><h2>Warmtepomp — Panasonic-regeling / SG-zonneboost</h2></div><button type="button" role="switch" aria-checked="${s.enabled===true}" aria-label="Automatische zonneboost" class="toggle ${s.enabled===true?'active':''}" data-action="sg_boost_enabled" ${ready?'':'disabled'}>${s.enabled===true?'Aan':'Uit'}</button></div>${this._heatpumpGraphic(c)}${this._heatpumpBusiness(c)}${this._sgStatusStrip(c)}<div class="heatpump-readings">${this._tile('Boilertemperatuur',this._heatpumpTankReading(c,'temperature_c'),'Panasonic-meting')}${this._tile('Ingesteld boilerdoel',this._heatpumpTankReading(c,'target_c'),'Gemeld tankdoel')}${this._heatpumpCalculatedGoal(c)?this._tile(this._heatpumpCalculatedGoal(c).label,spTemp(this._heatpumpCalculatedGoal(c).value),'Lokaal bevestigd SG-percentage'):''}${this._heatpumpPower(c)}</div>${this._heatpumpGoalSetup(c)}<p><b>${spEscape(this._plainReason(this._heatpumpReason(c)))}</b></p>${this._wallboxPriorityControl(c,'dhw_extra',{label:'extra SG-zonneboost',compact:true})}${this._heatpumpHistoryButton(c)}${manual?`<p class="note">Handmatige bediening blijft behouden.</p><button type="button" class="mini" data-action="sg_boost_resume" ${!s.resume_entity||this._busy?'disabled':''}>Automatische zonneboost hervatten</button>`:''}<details data-ui-key="sg:${spEscape(scope)}:details"><summary>Details en voorwaarden</summary>${this._sgDetails(c,scope)}<button type="button" class="mini" data-action="configure" data-config-step="sg_boost">Zonneboost instellen</button></details></section>`;
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
        ${this._tile('Gezamenlijke planning',p.optimisation?.applied?'betere combinatie gevonden':p.optimisation?.enabled?'basisplanning behouden':'uit',p.optimisation?.status==='budget'?'beste resultaat binnen rekengrens':'dagdoelen en cyclusvoorwaarden behouden')}

      </div>
      ${(p.warnings||[]).length?this._notice((p.warnings||[]).map(x=>spEscape(x)).join('<br>'),true):''}
      ${(p.findings||[]).length?`<div class="advice"><strong>Bevindingen</strong>${p.findings.map(x=>`<p>${spEscape(x)}</p>`).join('')}</div>`:''}
      <details class="planned-cost"><summary>Uitsplitsing verwachte energiekost · planhorizon</summary><div class="summarygrid">
        ${this._tile('Verwachte netafnamekost',spEuro(p.cost_breakdown?.import_cost_eur),'toekomstige afname × tarief per planblok')}
        ${this._tile('Verwachte injectievergoeding',spEuro(p.cost_breakdown?.export_revenue_eur),'al afgetrokken van de geschatte energiekost')}
        ${this._tile('Verwachte lokaal gebruikte zon',spKwh(p.predicted_self_use_kwh),p.cost_breakdown?.storage_advisory?'inclusief batterijadvies':'niet ingekocht van het net')}
      </div><p class="note">${spEscape(p.cost_breakdown?.note||'Nog geen plan beschikbaar.')}</p></details>
      ${this._todayCost(c)}
      <details class="joint-planning"><summary>Gezamenlijke optimalisatie en batterijadvies</summary><p class="note">De ingebouwde planner vergelijkt combinaties met dezelfde geplande energie per toestel. Alleen een geldige betere combinatie wordt overgenomen. Dit is een begrensde zoekoptimalisatie, geen bewezen globaal optimum of gemeten besparing. De piekvermijdingsstraf is geen berekening van je capaciteitstarieffactuur.</p>${p.battery_advice?.status==='planned'?`<p class="note">Batterijadvies volgt de tijdvolgorde, met ${Math.round(Number(p.battery_advice.round_trip_efficiency||0)*100)}% aangenomen rondrendement en aparte laad-/ontlaadgrenzen. Begin ${Number(p.battery_advice.initial_soc_pct||0).toLocaleString('nl-BE',{maximumFractionDigits:1})}% · einde ${Number(p.battery_advice.final_soc_pct||0).toLocaleString('nl-BE',{maximumFractionDigits:1})}% in dit scenario. Geen batterijbediening; het advies volgt na de toestelplanning.</p>`:'<p class="note">Geen bruikbaar batterijscenario in dit plan.</p>'}</details>
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
    const electrical=this._electricalLimits(c);
    return `<section class="view ems"><h2>Energie, net & voorspelling</h2><p class="sub">Actuele meters zijn leidend; forecast en leren verfijnen alleen de planning.</p><div class="summarygrid">
      ${this._tile('Kwartierpiek',cap.enabled?(cap.current_average_w==null?'—':spPower(cap.current_average_w)):'uit',cap.enabled?`theoretisch kwartierbudget ${spPower(cap.optional_headroom_w)}`:'')}
      ${electrical?this._tile('Elektrische ruimte nu',spPower(electrical.instantaneous_headroom_w),`netafnamegrens ${spPower(electrical.fixed_import_limit_w)} · na bestaande reserves`):''}
      ${this._tile('Fasebewaking',phase.enabled?(phase.headroom_w==null?'—':`${spPower(phase.headroom_w)} vrij`):'uit',phase.reason||'')}
      ${this._tile('Zonnevoorspelling',forecast.enabled?(forecast.remaining_today_kwh==null?'—':`${Number(forecast.remaining_today_kwh).toLocaleString('nl-BE',{maximumFractionDigits:1})} kWh resterend`):'uit',forecast.tomorrow_kwh==null?'':`morgen ${Number(forecast.tomorrow_kwh).toLocaleString('nl-BE',{maximumFractionDigits:1})} kWh`)}
      ${this._tile('Lokale PV-correctie',localPv.enabled?(localPv.corrected_power_w==null?'—':spPower(localPv.corrected_power_w)):'uit',localPv.enabled?`${Math.round(Number(localPv.confidence||0)*100)}% · ${localPv.reason||''}`:'')}
      ${this._tile('Planner',planner.enabled?(planner.held_devices?.length?`${planner.held_devices.length} start(s) wachten`:'geen uitstel'):'uit',planner.early_grid_devices?.length?`netfallback: ${planner.early_grid_devices.join(', ')}`:'zonnestroom eerst')}
      ${this._tile('Waarde eigen zon',economy.enabled?`€ ${Number(economy.self_use_value_eur_kwh||0).toLocaleString('nl-BE',{maximumFractionDigits:3})}/kWh`:'—',economy.enabled?`afname €${Number(economy.import_eur_kwh||0).toLocaleString('nl-BE',{maximumFractionDigits:3})} · injectie €${Number(economy.export_eur_kwh||0).toLocaleString('nl-BE',{maximumFractionDigits:3})}`:'')}
    </div>${electrical?`<p class="note">Het theoretische kwartierbudget is een energieberekening voor het piekdoel. Elektrische ruimte nu is begrensd door de vaste netafnamegrens, actieve fasecontrole en het kwartierdoel. Onbetrouwbare bronnen blijven onbekend. Zonnestroom, toestelvoorwaarden en wachttijden worden afzonderlijk beoordeeld.</p>`:''}
    ${phaseAttribution.enabled?`<details open><summary>Faseverdeling & herkende toestellen</summary><p class="note">P1-fasen zijn netto. Herkend toestelvermogen is bruto; batterijbijdrage is getekend. De restwaarde is geen exact onbekend verbruik.</p><div class="phaselist">${(phaseAttribution.phases||[]).map((x,idx)=>{const hist=historicalPhase.stats?.['L'+(idx+1)+' max W']||{};return `<div class="phaserow"><div><strong>${spEscape(x.name)}</strong><small>netto ${spPower(x.net_w)} · herkend ${spPower(x.known_device_w)}${Number(x.battery_net_w||0)?` · batterij ${(Number(x.battery_net_w)>=0?'+':'−')}${spPower(Math.abs(Number(x.battery_net_w)))}`:''}</small></div><b>rest ${spPower(x.residual_net_w)}</b><p>${(x.devices||[]).slice(0,5).map(d=>`${spEscape(d.name)} ${spPower(d.power_w)}`).join(' · ')||'Nog geen apparaten betrouwbaar herkend'}${hist.p95_import_w!=null?` · historisch P95 ${spPower(hist.p95_import_w)}`:''}</p></div>`}).join('')}</div></details>`:''}
    <details class="learning"><summary>Leren & modelkwaliteit</summary><div class="row"><div class="grow"><strong>Toestelvermogen en Wallbox-respons leren</strong><p>Deze schakelaar geldt alleen voor toestelvermogens en Wallbox-respons. Andere modellen hebben hun eigen instellingen; veiligheidsgrenzen worden nooit automatisch versoepeld.</p></div><button role="switch" class="toggle ${learning.enabled?'active':''}" data-action="learning" ${!learning.switch_entity?'disabled':''}>${learning.enabled?'Aan':'Uit'}</button></div><div class="facts"><span>Wallbox-overdrachten <b>${Number(learning.successes||0)}</b></span><span>Fase-events <b>${Number(phaseLearning.accepted_events||0)}</b></span><span>PV-model <b>${localPv.enabled?Math.round(Number(localPv.confidence||0)*100)+'%':'uit'}</b></span></div>${learning.reset_entity?'<button class="mini" data-action="reset_learning">Apparaat-, lokale PV-, fase- en activiteitsleerdata wissen</button>':''}</details>
    ${this._savings(c)}
    ${this._todayCost(c)}
    <div class="kpis">${this._tile('Site-import vandaag',`${Number(today.site_import_kwh||0).toLocaleString('nl-BE',{maximumFractionDigits:2})} kWh`)}${this._tile('Site-export vandaag',`${Number(today.site_export_kwh||0).toLocaleString('nl-BE',{maximumFractionDigits:2})} kWh`)}${this._tile('PV vandaag',`${Number(today.pv_kwh||0).toLocaleString('nl-BE',{maximumFractionDigits:2})} kWh`)}</div></section>`;
  }
  _storage(c){
    const {batteryFleet,batteryAnalysis}=c;
    return `<section class="view"><h2>Thuisbatterijen</h2><p class="sub">Analyse kan nu al. Fysieke aansturing blijft afzonderlijk en expliciet opt-in.</p>${batteryFleet.enabled?`<section class="battery"><div class="sectionhead"><div><h2>Batterijvloot</h2><p>${spEscape(batteryFleet.reason||'')}</p></div><span class="badge">${batteryFleet.control_enabled?'BEDIENING TOEGESTAAN':'READ-ONLY'}</span></div><div class="flowgrid three">${this._tile('Gemiddelde SoC',spPct(batteryFleet.aggregate?.soc_pct))}${this._tile('Vermogen',spPower(batteryFleet.aggregate?.power_w))}${this._tile('Capaciteit',batteryFleet.aggregate?.capacity_kwh==null?'—':`${Number(batteryFleet.aggregate.capacity_kwh).toLocaleString('nl-BE',{maximumFractionDigits:1})} kWh`)}</div>${(batteryFleet.batteries||[]).map(b=>`<div class="batteryrow ${b.valid===true&&typeof b.power_w==='number'&&Number.isFinite(b.power_w)&&b.power_w!==0?'is-active':''}"><span>${b.valid===true&&typeof b.power_w==='number'&&Number.isFinite(b.power_w)&&b.power_w!==0?`<i class="battery-activity" aria-hidden="true">${b.power_w>0?'↗':'↙'}</i> `:''}${spEscape(b.name)}<small>${spEscape(b.phase_hint||'unknown')} · ${b.controllable?'bestuurbaar':'read-only'}</small>${this._sourceHistoryButton('battery',b.id,'Bronhistorie in HA')}</span><b>${spPct(b.soc_pct)} · ${spPower(b.power_w)}</b></div>`).join('')}${batteryFleet.faults&&Object.keys(batteryFleet.faults).length?this._notice(Object.values(batteryFleet.faults).map(x=>spEscape(x)).join('<br>'),true):''}</section>`:'<div class="empty">Nog geen echte thuisbatterij gekoppeld.</div>'}${batteryAnalysis.enabled?`<details open><summary>Batterijscenario’s · what-if</summary><p class="note"><b>${Number(batteryAnalysis.roundtrip_loss_pct??20).toLocaleString('nl-BE',{maximumFractionDigits:1})}% totaal round-trip verlies</b> · batterij/omvormerconversie. ${spEscape(batteryAnalysis.note||'')}</p>${(batteryAnalysis.scenarios||[]).filter(x=>Math.abs(Number(x.power_kw)-5)<.01).map(x=>`<div class="scenario"><span>${Number(x.capacity_kwh).toLocaleString('nl-BE')} kWh · ${Number(x.power_kw).toLocaleString('nl-BE')} kW</span><b>${Number(x.avoided_import_kwh||0).toLocaleString('nl-BE',{maximumFractionDigits:0})} kWh vermeden afname*</b></div>`).join('')}<p class="note">* Technische simulatie op historie + live data; geen jaarprognose of koopadvies.</p></details>`:''}</section>`;
  }
  _guide(c){
    const g=c.guide, removal=c.a.removal||{};
    if(!g.solar_pilot_guide)return `<section class="view"><div class="empty">Actuele uitleg wordt geladen. Herlaad de pagina als SolarPilot net is toegevoegd.</div></section>`;
    const removeBox=`<details open><summary>Installatie & volledig verwijderen</summary><p>SolarPilot is zelfvoorzienend: de frontend zit in dezelfde integratiemap. Voor verwijderen laat je SolarPilot eerst alle eigen regelingen veilig vrijgeven.</p><div class="notice ${removal.ready?'':'warn'}"><strong>${spEscape(removal.status||'Niet voorbereid')}</strong>${(removal.blockers||[]).length?`<br>${(removal.blockers||[]).map(x=>spEscape(x)).join('<br>')}`:'<br>SolarPilot bezit geen actieve regeling meer.'}</div>${c.a.prepare_remove_entity?`<button data-action="prepare_remove" ${this._busy?'disabled':''}>Verwijderen voorbereiden</button>`:''}<p class="note">Daarna: Instellingen → Apparaten & diensten → SolarPilot → Verwijderen. Bij handmatige installatie verwijder je tenslotte /config/custom_components/solar_pilot en herstart je Home Assistant. Gekoppelde apparaten worden niet verwijderd.</p></details>`;
    return `<section class="view guide"><div class="guidehero"><h2>${spEscape(g.title||'SolarPilot · Actuele werking')}</h2><p>${spEscape(g.intro||'')}</p><small>Versie ${spEscape(g.version||'')} · bijgewerkt ${spEscape(g.updated||'')}</small></div>${removeBox}${(g.sections||[]).map((s,i)=>`<details ${i===0?'open':''}><summary>${spEscape(s.title)}</summary>${(s.paragraphs||[]).map(p=>`<p>${spEscape(p)}</p>`).join('')}${(s.bullets||[]).length?`<ul>${s.bullets.map(b=>`<li>${spEscape(b)}</li>`).join('')}</ul>`:''}</details>`).join('')}</section>`;
  }
  _goExport(){this._uiHistory.view('export');}
  _analysisBanner(a){
    const count=Number(a.learning_insights?.open_questions||0);
    if(!(count>0))return '';
    const admin=this._analysisAdministrator();
    return `<div class="advice analysis-needed"><strong>Analyse nodig</strong><p>SolarPilot heeft ${count} bevindingen voor analyse. Het bestand bevat bronbewijs en de beschikbare historie.</p><div class="controls"><button type="button" data-action="analysis_download" ${admin?'':'disabled'}>Maak analysebestand</button><button type="button" data-action="analysis_feedback_upload" ${admin?'':'disabled'}>Antwoord uploaden</button></div></div>`;
  }
  _analysisAdministrator(){return this._hass?.user?.is_admin===true;}
  async _loadAnalysisFeedback(){
    const entry=this._last?.attributes?.config_entry_id;
    if(!this._analysisAdministrator()||!entry||this._analysisFeedbackEntry===entry||this._analysisFeedbackBusy||this._analysisFeedbackReading)return;
    this._analysisFeedbackEntry=entry;await this._analysisFeedbackAction('status');
  }
  async _analysisFeedbackAction(action,content){
    const entry=this._last?.attributes?.config_entry_id;
    if(!this._analysisAdministrator()||!entry||this._analysisFeedbackBusy)return false;
    const seq=(this._analysisFeedbackSeq||0)+1;this._analysisFeedbackSeq=seq;this._analysisFeedbackBusy=true;
    this._analysisFeedbackError='';this._analysisFeedbackMessage=action==='import'?'Antwoord wordt gecontroleerd…':action==='remove'?'Adviesrapport wordt verwijderd…':'Adviesrapport laden…';this._render();
    try{
      const answer=await this._hass.callWS({type:'solar_pilot/analysis_feedback',config_entry_id:entry,action,...(action==='import'?{content}:{})});
      if(seq!==this._analysisFeedbackSeq||entry!==this._last?.attributes?.config_entry_id)return false;
      this._analysisFeedbackReport=answer;
      this._analysisFeedbackMessage=action==='import'?'Antwoord opgeslagen. Het gaat automatisch mee in een volgende analyse-export.':action==='remove'?'Adviesrapport verwijderd.':'';
      return true;
    }catch(err){if(seq===this._analysisFeedbackSeq)this._analysisFeedbackError=err?.message||'Adviesrapport kon niet worden verwerkt. Probeer opnieuw.';return false;}
    finally{if(seq===this._analysisFeedbackSeq){this._analysisFeedbackBusy=false;this._render();}}
  }
  async _importAnalysisFeedback(file){
    if(!file||this._analysisFeedbackBusy||this._analysisFeedbackReading||!this._analysisAdministrator())return;
    this._analysisFeedbackError='';
    if(typeof file.size!=='number'||!Number.isFinite(file.size)||file.size<=0||file.size>1048576){this._analysisFeedbackError='Kies een niet-leeg JSON-adviesrapport van maximaal 1 MiB.';this._render();return;}
    const entry=this._last?.attributes?.config_entry_id,userId=this._hass?.user?.id,readSeq=(this._analysisFeedbackReadSeq||0)+1;this._analysisFeedbackReadSeq=readSeq;this._analysisFeedbackReading=true;this._render();
    try{
      const content=await file.text();
      if(readSeq!==this._analysisFeedbackReadSeq||userId!==this._hass?.user?.id||entry!==this._last?.attributes?.config_entry_id||!this._analysisAdministrator())return;
      const report=JSON.parse(content);
      if(!report||Array.isArray(report)||report.schema!=='solarpilot.analysis_feedback'||report.schema_version!==1)throw new Error('Dit bestand is geen ondersteund SolarPilot-adviesrapport. Gebruik het sjabloon uit de analyse-export.');
      await this._analysisFeedbackAction('import',content);
    }catch(err){this._analysisFeedbackError=err instanceof SyntaxError?'Het bestand bevat geen geldige JSON. Vraag hier om een SolarPilot-adviesrapport volgens het meegeleverde sjabloon.':err?.message||'Het geselecteerde bestand kon niet worden gelezen.';}
    finally{if(readSeq===this._analysisFeedbackReadSeq){this._analysisFeedbackReading=false;this._render();}}
  }
  _analysisLogicUpdate(item,status,index){
    if(item.category!=='logic_update')return '';
    const row=Array.isArray(status?.logic_updates)?status.logic_updates.find(value=>value.recommendation_index===index&&value.proposal_id===item.proposal_id):null;
    const state=row&&['pending','implemented'].includes(row.status)?row.status:'untracked';
    const labels={implemented:'Opgenomen in de geïnstalleerde versie',pending:'Nog niet in deze versie opgenomen',untracked:'Nog niet gekoppeld aan een softwarewijziging'};
    return `<div class="analysis-logic-status" data-logic-update-status="${state}"><b>${spEscape(labels[state])}</b><small>Geïnstalleerd: ${spEscape(row?.installed_release||status?.current_release||'niet beschikbaar')}${row?.introduced_release?` · versie van de wijziging: ${spEscape(row.introduced_release)}`:''}</small>${row?.reason==='proposal_content_changed'?'<small>De inhoud van dit advies verschilt van de geregistreerde wijziging.</small>':''}<small>Deze status komt uit de geïnstalleerde software; een geüpload advies voert geen update uit.</small></div>`;
  }
  _analysisRecommendationKind(item){
    const labels={warmtepomp_setting:'Advies over instellingen',solarpilot_setting:'Advies over instellingen',observation:'Waarneming · geen softwarewijziging'};
    if(typeof item.category!=='string'||!Object.hasOwn(labels,item.category))return '';
    return `<div class="analysis-logic-status" data-recommendation-kind="${spEscape(item.category)}"><b>${labels[item.category]}</b><small>${item.category==='observation'?'Dit is een waarneming uit het adviesrapport; de huidige toestand staat bij Automatisch onderzoek.':'Het rapport bevestigt niet dat deze instelling is toegepast. Automatisch onderzoek beoordeelt actuele gekoppelde metingen afzonderlijk.'}</small></div>`;
  }
  _investigationHtml(c){return spInvestigationHtml(c.a.learning_insights?.investigation,{current:this._activityObservationsCurrent(),timeZone:this._hass?.config?.time_zone});}
  _analysisQuestionReview(answer,status){
    const row=Array.isArray(status?.question_review)?status.question_review.find(value=>value.question_id===answer.question_id&&value.revision===answer.revision):null;
    const labels={reviewed:'Deze bevinding is voor de analyse beoordeeld.',needs_more_data:'De bevinding blijft open: meer gegevens nodig.',ignored_unverified:'Bronkoppeling ontbreekt; de bevinding blijft open.',ignored_stale:'De bevinding is gewijzigd; dit antwoord rondt haar niet af.'};
    return row&&Object.hasOwn(labels,row.status)?`<small data-question-review-status="${spEscape(row.status)}">${spEscape(labels[row.status])}</small>`:'<small>Dit is de beoordeling in het rapport; afronding van de huidige bevinding is niet bevestigd.</small>';
  }
  _analysisFeedbackHtml(status){
    const report=status?.report;
    if(!report)return '<p class="note">Nog geen antwoord geüpload. Laat het analysebestand hier beoordelen en vraag om een JSON-adviesrapport volgens het meegeleverde sjabloon.</p>';
    const categories={warmtepomp_setting:'Warmtepompinstelling',solarpilot_setting:'SolarPilot-instelling',logic_update:'Softwarelogica',observation:'Waarneming'};
    const confidence={low:'Beperkt bewijs',medium:'Redelijk bewijs',high:'Sterk bewijs'};
    const matched=status.association?.state==='matched';
    const recommendations=Array.isArray(report.recommendations)?report.recommendations:[],answers=Array.isArray(report.question_answers)?report.question_answers:[];
    const list=values=>Array.isArray(values)&&values.length?`<ul>${values.map(value=>`<li>${spEscape(value)}</li>`).join('')}</ul>`:'';
    return `<div class="analysis-feedback-report"><div class="notice ${matched?'':'warn'}" data-analysis-association="${matched?'matched':'unverified'}"><strong>${matched?'Gekoppeld aan een lokaal analysebestand':'Bronkoppeling niet bevestigd'}</strong><p>${spEscape(status.association?.reason||'De herkomst kon niet met een lokaal analysebestand worden vergeleken.')}</p><small>Analysebron: ${spEscape(report.source_export?.release||'niet beschikbaar')} · geïnstalleerd: ${spEscape(status.current_release||'niet beschikbaar')}</small><small>Een overeenkomende bron bevestigt alleen de herkomst; de aanbevelingen blijven adviezen.</small>${status.source_release_matches_current===false?'<p><b>Dit rapport hoort bij een andere SolarPilot-versie.</b> Maak een nieuw analysebestand voor de huidige versie.</p>':''}</div><h3>Samenvatting</h3><p class="analysis-feedback-text">${spEscape(report.summary)}</p>${list(report.limitations)}${answers.length?`<h3>Beoordeelde bevindingen</h3>${answers.map(answer=>`<article class="analysis-recommendation"><strong>${spEscape(answer.question_id)} · ${answer.outcome==='reviewed'?'Beoordeeld in het rapport':'Meer gegevens nodig'}</strong><p>${spEscape(answer.answer)}</p>${this._analysisQuestionReview(answer,status)}</article>`).join('')}`:''}<h3>Aanbevelingen · ${recommendations.length}</h3>${recommendations.map((item,index)=>`<article class="analysis-recommendation"><span>${spEscape(categories[item.category]||'Advies')} · ${spEscape(confidence[item.confidence]||'Bewijs niet aangeduid')}</span><p>${spEscape(item.text)}</p>${this._analysisLogicUpdate(item,status,index)}${this._analysisRecommendationKind(item)}${item.evidence?.length?`<details><summary>Onderbouwing</summary>${list(item.evidence)}</details>`:''}${item.limitations?.length?`<details><summary>Beperkingen</summary>${list(item.limitations)}</details>`:''}</article>`).join('')||'<p>Dit rapport bevat geen afzonderlijke aanbevelingen.</p>'}<p class="note">Het rapport wijzigt geen instellingen of software en schakelt geen toestel. De aanbevelingen kun je hier verder bespreken.</p></div>`;
  }
  _openPriorities(){
    this._uiHistory.prepare();
    if(!this._priorityDialog){this._priorityDialog=document.createElement(spDialogTag('solar-pilot-priority-dialog',SP_PRIORITY_DIALOG_TAG));this.shadowRoot.append(this._priorityDialog);this._priorityDialog.addEventListener('priority-saved',()=>{this._error='';});this._priorityDialog.addEventListener('priority-closed',()=>requestAnimationFrame(()=>this._content.querySelector('[data-action=priority_edit]')?.focus({preventScroll:true})));}
    this._priorityDialog.open(this._hass,this._last?.attributes?.config_entry_id);this._uiHistory.track(this._priorityDialog,()=>this._priorityDialog.open(this._hass,this._last?.attributes?.config_entry_id));
  }
  _priorities(c){
    const b=c.a.priority_board;
    if(!b)return `<section><h2>Voorrang</h2><p class="note">De centrale lijst is nog niet ontvangen. Controleer of integratie én kaart op dezelfde nieuwe versie staan.</p></section>`;
    const wallboxPosition=(b.rows||[]).find(r=>r.id==='wallbox')?.position??0,powerOutcome=r=>String(r?.power_label||'Niet vastgesteld').replace(/^Wallbox-vermogen:\s*/i,'');
    const fixed=(b.protected||[]).map(r=>`<div class="priority-row fixed"><div class="priority-number">Vast<small aria-hidden="true">🔒</small></div><div><b>${spEscape(r.name)}</b><small>${spEscape(r.active?'Actief':'Niet ingesteld of niet actief')}</small><p>Mag de auto minder laden? <strong>${spEscape(powerOutcome(r))}</strong></p><small>${spEscape(r.reason||'')}</small></div></div>`).join('');
    const rows=(b.rows||[]).map(r=>{const before=!!r.device_id&&Number(r.position)<Number(wallboxPosition);const relation=!r.device_id?powerOutcome(r):!r.wallbox_power?'Nee · alleen werkelijk vrij zonneoverschot':before?'Ja · toestel staat vóór Auto laden':'Nee · Auto laden staat hoger';const savedPermission=r.device_id&&r.wallbox_power&&!before?'<small>Toestemming is bewaard; wordt gebruikt als je dit toestel boven Auto laden zet.</small>':'';return `<div class="priority-row"><div class="priority-number">${r.position}</div><div><b>${spEscape(r.name)}</b><small>${spEscape(r.status||(r.active?'Ingesteld':'Niet actief'))}</small><p>Mag de auto minder laden? <strong>${spEscape(relation)}</strong></p>${savedPermission}${r.device_id?`<small>Nu uitvoerbaar: ${spEscape(powerOutcome(r))}</small>`:''}<small>${spEscape(r.reason||'')}</small>${this._wallboxPriorityControl(c,r.device_id?`device:${r.device_id}`:r.id==='dhw_extra'?'dhw_extra':'',{label:r.name,compact:true})}</div></div>`}).join('');
    return `<section><div class="sectionhead"><div><h2>Voorrang en autoladen</h2><p>Van boven naar beneden staat wie als eerste energie krijgt.</p></div><button type="button" data-action="priority_edit" ${this._hass?.user?.is_admin===true?'':'disabled'}>Voorrang instellen</button></div><p class="note">${spEscape(b.note)}</p>${this._wallboxPriorityControl(c,'global')}<div class="priority-stack" aria-label="Volledige voorrangslijst">${fixed}${rows}</div><p class="note">Bescherming en noodzakelijk comfort staan vast. Apparaten, Auto laden en extra SG-zonneboost kun je binnen de veilige grenzen verplaatsen. Een nieuw toestel start nooit vanzelf.</p><button type="button" class="mini" data-action="manage_devices">Toestellen beheren</button></section>`;
  }
  _export(c){
    const findings=Array.isArray(c.a.learning_insights?.findings)?c.a.learning_insights.findings:[],admin=this._analysisAdministrator(),report=admin?this._analysisFeedbackReport:null;
    return `<section class="analysis-export"><h2>Analyse en advies</h2><p class="sub">Eén analysepakket voor hier: download het bestand, laat het beoordelen en upload eventueel het antwoord.</p>${this._investigationHtml(c)}<div class="export-grid"><div><strong>Meetkwaliteit & historie</strong><p>Voeding 1 en 2, Panasonic-taak, tank, ruimtes en SG naast bewaarde meetpunten. Gaten en ontbrekende bronnen blijven zichtbaar.</p></div><div><strong>Instellingen & beslissingen</strong><p>Actuele instellingen, voorrang, bekende wijzigingen en start- of wachtredenen. Het pakket onderscheidt instellingen, waarnemingen en afgeleide informatie.</p></div><div><strong>Vragen voor de analyse</strong><p>Open bevindingen, bronbewijs en een sjabloon voor een terug te uploaden adviesrapport. Een eerder geüpload rapport gaat automatisch mee.</p></div></div>${findings.length?`<section class="analysis-findings"><h3>Bevindingen voor analyse · ${findings.length}</h3>${findings.map(item=>`<article class="analysis-recommendation"><strong>${spEscape(item.title)}</strong><p>${spEscape(item.message)}</p>${item.answer_note?`<small>${spEscape(item.answer_note)}</small>`:''}</article>`).join('')}</section>`:Number(c.a.learning_insights?.open_questions||0)>0?`<p>${Number(c.a.learning_insights.open_questions)} bevindingen gaan mee in het analysebestand.</p>`:''}<p class="note">De laatste 7 dagen worden meegenomen voor zover ze werkelijk zijn bewaard. Namen en entiteiten krijgen consistente codes. Controleer het bestand voordat je het hier deelt.</p><button type="button" data-action="analysis_download" ${admin?'':'disabled'}>Maak analysebestand</button><p class="note">Eén gecomprimeerd bestand (.json.gz). Exporteren verstuurt niets automatisch en verandert geen instellingen. Dit is een analysepakket, geen Home Assistant-back-up.</p><section class="analysis-feedback"><h3>Antwoord uploaden</h3><p class="sub">Kies het JSON-adviesrapport dat je hier terugkrijgt. Alleen tekst en bronverwijzingen worden opgeslagen; niets wordt automatisch toegepast.</p><input type="file" accept=".json,application/json" data-analysis-feedback-file hidden aria-label="JSON-adviesrapport kiezen"><div class="controls"><button type="button" data-action="analysis_feedback_upload" ${admin&&!this._analysisFeedbackBusy&&!this._analysisFeedbackReading?'':'disabled'}>Antwoord uploaden</button><button type="button" data-action="analysis_feedback_reload" ${admin&&!this._analysisFeedbackBusy&&!this._analysisFeedbackReading?'':'disabled'}>Rapport vernieuwen</button>${report?.report?`<button type="button" data-action="analysis_feedback_remove" ${admin&&!this._analysisFeedbackBusy&&!this._analysisFeedbackReading?'':'disabled'}>Adviesrapport verwijderen</button>`:''}</div>${!admin?'<p class="note">Meld je aan als Home Assistant-beheerder om een analysebestand te downloaden of een antwoord te beheren.</p>':''}${this._analysisFeedbackError?`<p class="error" role="alert">${spEscape(this._analysisFeedbackError)}</p>`:''}<p class="note" role="status" aria-live="polite">${spEscape(this._analysisFeedbackMessage||'')}</p>${this._analysisFeedbackHtml(report)}</section></section>`;
  }
  _viewHtml(c){return ({overview:()=>this._overview(c),loads:()=>this._loads(c),comfort:()=>this._comfort(c),water:()=>this._water(c),planning:()=>this._planning(c),energy:()=>this._energy(c),storage:()=>this._storage(c),priorities:()=>this._priorities(c),export:()=>this._export(c),guide:()=>this._guide(c)}[this._view]||(()=>this._overview(c)))();}
  _render(){
    const uiState=this._captureUiState();
    const c=this._ctx(),a=c.a;
    this._content.innerHTML=`<style>
      .wallbox-device.on,.active-tile,.active-load{border-color:var(--primary-color,#287c59);box-shadow:inset 4px 0 0 var(--primary-color,#287c59);background:var(--secondary-background-color,#f3f5f7)}.wallbox-device.on .icon{background:var(--primary-color,#287c59);color:var(--text-primary-color,#fff)}.active-loads,.savings-summary{margin:15px 0;border:1px solid var(--divider-color,#dce1e7);border-radius:14px;padding:13px}.active-loads h2,.savings-summary h2{margin:0}.active-list{display:grid;gap:8px;margin-top:10px}.active-load{display:flex;align-items:center;gap:10px;padding:11px 12px;border:1px solid var(--primary-color,#287c59);border-radius:11px;min-width:0}.active-load strong{font-size:13px;overflow-wrap:anywhere}.active-load small{display:block;font-size:11px;color:var(--secondary-text-color,#697485);line-height:1.45;margin-top:4px}.active-power{flex:0 0 auto;text-align:right;font-size:14px}.active-power small{max-width:110px}.savings-summary p{font-size:12px;line-height:1.55}.savings-summary .tile strong{font-variant-numeric:tabular-nums}@media(max-width:420px){.active-load{align-items:flex-start;flex-wrap:wrap}.active-load>.grow{flex-basis:100%}.active-power{text-align:left}.active-power small{max-width:none}.active-loads .sectionhead{align-items:flex-start;flex-wrap:wrap}}
      .priority-stack{margin:12px 0;border:1px solid var(--divider-color,#dce1e7);border-radius:13px;overflow:hidden}.priority-stack .priority-row{grid-template-columns:42px minmax(0,1fr);padding:13px}.priority-stack .priority-row:first-child{border-top:0}.priority-stack .priority-row.fixed{background:var(--secondary-background-color,#f5f7f8)}.priority-stack .priority-number{text-align:center}.priority-stack .priority-number small{font-size:11px}.priority-stack .priority-row.fixed .priority-number{font-size:10px;line-height:1.4;text-transform:uppercase}
      .start-explanation{margin:10px 0;padding:11px 12px;border-radius:11px;background:var(--secondary-background-color,#f3f5f7);border-left:3px solid var(--primary-color,#287c59)}.start-explanation>strong{font-size:12px}.start-explanation>p{font-size:12px;line-height:1.5;margin:5px 0}.start-facts{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;margin:9px 0}.start-facts span{font-size:10px;line-height:1.4;padding:7px;border-radius:8px;background:var(--card-background-color,#fff)}.start-facts b{display:block;font-size:12px;margin-top:2px}.start-missing{font-size:11px;line-height:1.5;margin:8px 0}.start-missing ul{margin:4px 0 0;padding-left:18px}.start-ready{font-size:11px!important}.start-explanation>small{display:block;color:var(--secondary-text-color,#697485);font-size:10px;line-height:1.45}@media(max-width:420px){.start-facts{grid-template-columns:1fr}}
      .wallbox-priority-control{border:1px solid var(--divider-color,#dce1e7);border-radius:12px;padding:12px;margin:12px 0;min-width:0}.wallbox-priority-head{display:flex;align-items:center;justify-content:space-between;gap:10px}.wallbox-priority-head>div{min-width:0;flex:1}.wallbox-priority-control strong{font-size:13px;line-height:1.4;overflow-wrap:anywhere}.wallbox-priority-control small{display:block;font-size:11px;line-height:1.5;color:var(--secondary-text-color,#697485);overflow-wrap:anywhere;margin-top:4px}.wallbox-priority-head button{flex-shrink:0;min-height:40px;max-width:45%;white-space:normal;overflow-wrap:anywhere}.wallbox-priority-clock{font-size:12px;font-variant-numeric:tabular-nums;font-weight:650;margin:8px 0;line-height:1.4;overflow-wrap:anywhere}.wallbox-priority-control.compact{padding:10px}.wallbox-priority-control .controls{margin-top:6px}.wallbox-priority-control [data-wallbox-priority-mixed]{color:var(--warning-color,#a76e00)}
      .sg-manual-control{margin:12px 0;padding:11px;border:1px solid var(--divider-color,#dce1e7);border-radius:12px;min-width:0}.sg-manual-head{display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;font-size:11px}.sg-manual-head span{font-weight:700;overflow-wrap:anywhere}.sg-manual-actions{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px;margin-top:8px}.sg-manual-actions button{min-width:0;min-height:40px;white-space:normal;overflow-wrap:anywhere}.sg-manual-actions button[data-sg-mode=auto]{grid-column:1/-1}.sg-manual-control .note{margin:7px 0;font-size:11px;line-height:1.45}.sg-manual-control>small{display:block;margin-top:8px;font-size:10px;line-height:1.45;color:var(--secondary-text-color,#697485)}.heatpump-sg{border:1px solid var(--divider-color,#dce1e7);border-radius:16px;padding:16px;margin:12px 0;min-width:0}.heatpump-sg.is-active{border-color:#03a9f4;box-shadow:inset 4px 0 0 #03a9f4}.heatpump-sg .sectionhead{align-items:flex-start;flex-wrap:wrap}.heatpump-sg .sectionhead>div{flex:1;min-width:180px}.heatpump-sg p{font-size:12px;line-height:1.5;overflow-wrap:anywhere}.heatpump-operation{display:flex;align-items:center;gap:12px;padding:12px 0}.heatpump-operation>div{min-width:0}.heatpump-operation strong{display:block;font-size:14px;line-height:1.4;overflow-wrap:anywhere}.heatpump-operation small{display:block;margin-top:4px;color:var(--secondary-text-color,#697485);font-size:11px;line-height:1.45}.heatpump-icon{width:48px;height:48px;flex:0 0 auto;fill:none;stroke:var(--secondary-text-color,#697485);stroke-width:2}.heatpump-fan{fill:var(--secondary-text-color,#697485);stroke:none;transform-origin:24px 24px}.heatpump-operation.is-active .heatpump-icon{stroke:#03a9f4}.heatpump-operation.is-active .heatpump-fan{fill:#03a9f4}.heatpump-operation.is-active[data-fan-active=true] .heatpump-fan{animation:sp-heatpump-turn 3s linear infinite}@keyframes sp-heatpump-turn{to{transform:rotate(360deg)}}.heatpump-operation.is-unknown .heatpump-icon>rect{stroke-dasharray:3 3}.sg-status-strip{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,180px),1fr));gap:7px;margin:8px 0}.sg-stage{min-width:0;padding:10px;border:1px solid var(--divider-color,#dce1e7);border-radius:10px;background:var(--secondary-background-color,#f5f7f8)}.sg-stage span{display:block;color:var(--secondary-text-color,#697485);font-size:10px;line-height:1.4;overflow-wrap:anywhere}.sg-stage strong{display:block;font-size:12px;line-height:1.4;margin-top:4px;overflow-wrap:anywhere}.sg-stage.is-active{border-color:#03a9f4;box-shadow:inset 0 3px 0 #03a9f4}.sg-stage.is-unknown{border-style:dashed}.sg-policy{margin-top:5px}.heatpump-supply{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:8px 0;border-top:1px solid var(--divider-color,#dce1e7);font-size:12px}.heatpump-supply>span{min-width:0;overflow-wrap:anywhere}.heatpump-supply>span:first-child{flex:1}.heatpump-supply>span:last-child{flex:0 0 auto;max-width:45%;overflow-wrap:normal;word-break:normal;text-align:right}.heatpump-supply strong{font-size:13px}.heatpump-supply small{display:block;font-size:10px;color:var(--secondary-text-color,#697485);line-height:1.4;margin-top:3px}.heatpump-supply[data-supply-state=active]{border-left:3px solid #03a9f4;padding-left:8px}.heatpump-readings{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:12px 0}.heatpump-readings>.reason-power{grid-column:1/-1;min-width:0;border:1px solid var(--divider-color,#dce1e7);border-radius:13px;padding:11px;margin:0}.heatpump-readings .reason-power>b{font-size:17px;line-height:1.2;overflow-wrap:anywhere}.heatpump-readings .reason-power>small{display:block;font-size:10px;line-height:1.5;color:var(--secondary-text-color,#697485);overflow-wrap:anywhere}.heatpump-sg .start-facts{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.heatpump-sg .start-facts span{font-size:11px;color:var(--secondary-text-color,#697485);overflow-wrap:anywhere}.heatpump-sg .start-facts b{display:block;color:var(--primary-text-color,#202735);margin-top:3px}.version-info{width:100%;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}@media(prefers-reduced-motion:reduce){.heatpump-operation.is-active[data-fan-active=true] .heatpump-fan{animation:none}}@media(max-width:420px){.sg-status-strip{grid-template-columns:1fr}.sg-stage{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.1fr);align-items:center;gap:8px;padding:8px 10px}.sg-stage strong{margin-top:0}.sg-stage.is-active{box-shadow:inset 3px 0 0 #03a9f4}.heatpump-readings{grid-template-columns:1fr}.heatpump-sg .start-facts{grid-template-columns:1fr}}
      .analysis-feedback{margin-top:22px;border-top:1px solid var(--divider-color,#dce1e7);padding-top:12px}.analysis-recommendation{border:1px solid var(--divider-color,#dce1e7);border-radius:12px;padding:12px;margin:10px 0;min-width:0}.analysis-recommendation p,.analysis-feedback-text{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.55;font-size:12px}.analysis-recommendation strong,.analysis-recommendation span,.analysis-recommendation small{display:block;overflow-wrap:anywhere;font-size:12px}.analysis-feedback li{font-size:12px;line-height:1.5;overflow-wrap:anywhere}.analysis-feedback .notice p{font-size:12px;margin:7px 0}.analysis-feedback h3,.analysis-findings h3{font-size:14px}.analysis-logic-status{padding:8px;border-left:3px solid var(--primary-color,#009ec2);background:var(--secondary-background-color,#f5f7f8);margin:8px 0}.analysis-logic-status b,.analysis-logic-status small{display:block;overflow-wrap:anywhere;font-size:11px;line-height:1.5}.sg-signal-warning{border-left:3px solid var(--warning-color,#d8a34f);padding-left:9px}
      .sg-cooling-diagnostic{min-width:0;margin:14px 0;font-size:12px;line-height:1.5;overflow-wrap:anywhere}.sg-cooling-diagnostic h3{font-size:14px}.sg-cooling-source{min-width:0;padding:10px 0;border-top:1px solid var(--divider-color)}.sg-cooling-source .start-facts{grid-template-columns:repeat(2,minmax(0,1fr))}.sg-cooling-source b{overflow-wrap:anywhere}@media(max-width:540px){.sg-cooling-source .start-facts{grid-template-columns:1fr}}.heatpump-business{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px;margin:8px 0 12px}.heatpump-business-item{display:flex;align-items:flex-start;gap:9px;min-width:0;padding:12px;border:1px solid var(--divider-color,#dce1e7);border-radius:12px;background:var(--secondary-background-color,#f5f7f8)}.heatpump-business-item>div{min-width:0}.heatpump-business-item span,.heatpump-business-item small{display:block;color:var(--secondary-text-color,#697485);font-size:10px;line-height:1.45;overflow-wrap:anywhere}.heatpump-business-item strong{display:block;margin:4px 0;font-size:14px;line-height:1.4;overflow-wrap:anywhere}.heatpump-business-item b{display:block;font-size:12px;margin:5px 0}.heatpump-business-item small+small{margin-top:5px}.heatpump-business-item .heatpump-task-proof{font-weight:700;color:var(--primary-text-color,#202735)}.heatpump-task-icon{flex:0 0 auto;width:28px;height:28px;fill:none;stroke:var(--secondary-text-color,#697485);stroke-width:1.7;stroke-linecap:round;stroke-linejoin:round}.heatpump-business-item.is-active{border-color:#03a9f4}.heatpump-business-item.is-active .heatpump-task-icon{stroke:#03a9f4;animation:sp-device-activity 1.8s ease-in-out infinite}ha-card[data-observations-current=true] .reason-row.is-active:not([data-reason-key="overview:sg"])>.row>.badge::before{content:"";display:inline-block;width:6px;height:6px;border-radius:50%;margin-right:5px;background:currentColor;animation:sp-device-activity 1.8s ease-in-out infinite}ha-card[data-observations-current=true] .device.on .icon,ha-card[data-observations-current=true] .external.on .icon,ha-card[data-observations-current=true] .batteryrow.is-active .battery-activity{animation:sp-device-activity 1.8s ease-in-out infinite}@keyframes sp-device-activity{50%{opacity:.48}}@media(prefers-reduced-motion:reduce){.heatpump-business-item.is-active .heatpump-task-icon,.reason-row.is-active>.row>.badge::before,.device.on .icon,.external.on .icon,.batteryrow.is-active .battery-activity{animation:none!important}}@media(max-width:580px){.heatpump-business{grid-template-columns:1fr}}
      .priority-row{display:grid;grid-template-columns:30px minmax(0,1fr);gap:10px;padding:13px 0;border-top:1px solid var(--divider-color,#dce1e7)}.priority-row b{font-size:14px}.priority-row p{font-size:12px;margin:5px 0;line-height:1.55}.priority-row small{display:block;font-size:11px;color:var(--secondary-text-color,#697485)}.priority-number{font-weight:750;font-size:18px}.priority-protected{padding:13px;border-radius:12px;background:var(--secondary-background-color,#f5f7f8);margin:12px 0}.priority-protected p{font-size:12px;line-height:1.5}.export-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin:14px 0}.export-grid>div{padding:14px;background:var(--secondary-background-color,#f5f7f8);border-radius:12px}.export-grid strong{font-size:13px}.export-grid p{font-size:12px;line-height:1.5}.option-question{border-radius:50%;width:28px;min-width:28px;min-height:28px;padding:0;margin:3px 5px;font-weight:800;vertical-align:middle}.comfort-new{padding:16px;border:1px solid var(--divider-color);border-radius:14px;margin:14px 0}.comfort-new h3{margin:0 0 10px}.charging-profile{margin:12px 0;font-size:13px;line-height:1.6}.charging-profile small{display:block;color:var(--secondary-text-color)}:host{display:block;color:var(--primary-text-color,#202735);font-family:var(--paper-font-body1_-_font-family,system-ui,sans-serif)}*{box-sizing:border-box}ha-card{display:block;border-radius:20px;overflow:hidden;background:var(--ha-card-background,var(--card-background-color,#fff));border:1px solid var(--divider-color,#e0e4e9);box-shadow:none}.head{padding:20px 20px 10px;display:flex;align-items:center;gap:12px}.logo{width:42px;height:42px;display:grid;place-items:center;border-radius:13px;background:var(--secondary-background-color,#f1f4f6);font-size:23px}.grow{flex:1;min-width:0}.head h1{font-size:22px;margin:0;letter-spacing:-.6px}.head p,h2+p,.sub{margin:4px 0 0;color:var(--secondary-text-color,#697485);font-size:12px;line-height:1.5}.tag{font-size:10px;font-weight:750;color:var(--secondary-text-color,#697485);text-align:right}.body{padding:0 20px 18px}.modes{display:flex;gap:6px;margin:8px 0 10px}.modes button{flex:1}.restart-policy{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:8px 0;font-size:11px}.restart-policy>span{min-width:0;line-height:1.4}.restart-policy small{display:block;margin-top:2px;font-size:10px;color:var(--secondary-text-color,#697485)}.restart-policy>button{flex:0 0 auto}.nav{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;padding:8px 0 13px}.nav button{white-space:normal;border-radius:999px;padding:8px 7px;min-height:38px;line-height:1.15}.nav button.active{background:var(--primary-color,#287c59);color:var(--text-primary-color,#fff);border-color:transparent}button,input{font:inherit;color:inherit}button{cursor:pointer;border:1px solid var(--divider-color,#dce1e7);background:var(--card-background-color,#fff);border-radius:10px;padding:8px 11px;font-size:12px;font-weight:650;min-height:39px}button:hover{background:var(--secondary-background-color,#f3f5f7)}button.active,.toggle.active{background:var(--primary-color,#287c59);color:var(--text-primary-color,#fff);border-color:transparent}button:disabled{opacity:.45;cursor:default}button:focus-visible,input:focus-visible,summary:focus-visible{outline:3px solid var(--primary-color,#287c59);outline-offset:2px}.view{}h2{font-size:15px;margin:16px 0 2px}.flowgrid,.summarygrid,.kpis{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin:10px 0}.flowgrid.three{grid-template-columns:repeat(3,minmax(0,1fr))}.tile{border:1px solid var(--divider-color,#e0e4e9);border-radius:13px;padding:11px;min-width:0}.tile span,.tile small{display:block;color:var(--secondary-text-color,#697485);font-size:10px;line-height:1.35}.tile strong{display:block;font-size:17px;line-height:1.2;margin:5px 0 3px;overflow-wrap:anywhere}.tile small{overflow-wrap:anywhere}.energy-tile{border-color:hsl(var(--energy-hue) 65% 45%);box-shadow:inset 4px 0 0 hsl(var(--energy-hue) 65% 45%);background:linear-gradient(110deg,hsl(var(--energy-hue) 70% 50% / .14),hsl(var(--energy-hue) 70% 50% / .025))}.energy-unknown{border-color:var(--divider-color,#e0e4e9);box-shadow:none;background:none}.energy-scale{height:6px;margin:12px 5px 3px;border-radius:6px;position:relative}.solar-scale{background:linear-gradient(90deg,#dc4545,#e98525,#e4c82f,#a2c92f,#369b47)}.grid-scale{background:linear-gradient(90deg,#369b47,#a2c92f,#e4c82f,#e98525,#dc4545)}.energy-scale i{position:absolute;top:-3px;width:5px;height:12px;border-radius:3px;transform:translateX(-50%);background:var(--primary-text-color,#202735);box-shadow:0 0 0 2px var(--card-background-color,#fff)}.energy-legend{font-size:10px;line-height:1.5;color:var(--secondary-text-color,#697485);margin:5px 0 14px}.notice{padding:11px 12px;margin:10px 0;border-radius:11px;background:var(--secondary-background-color,#f3f5f7);font-size:12px;line-height:1.5;border-left:3px solid var(--primary-color,#287c59)}.notice.warn{border-left-color:var(--warning-color,#bf810e)}.error{color:var(--error-color,#b3261e);font-size:12px;margin:8px 0}.advice{padding:12px;border-radius:13px;background:var(--secondary-background-color,#f3f5f7);margin:10px 0}.advice p{font-size:11px;margin:5px 0}.inlinefacts,.facts{display:flex;gap:8px 14px;flex-wrap:wrap;font-size:11px;color:var(--secondary-text-color,#697485);margin:10px 0}.inlinefacts b,.facts b{color:var(--primary-text-color,#202735)}.row,.sectionhead{display:flex;align-items:center;gap:10px}.sectionhead{justify-content:space-between}.sectionhead h2{margin-top:0}.sectionhead p{margin:3px 0}.policy,.external,.device,.dhw,.climate,.battery{border:1px solid var(--divider-color,#e0e4e9);border-radius:14px;padding:13px;margin:10px 0}.device.on{border-color:var(--primary-color,#287c59);box-shadow:inset 4px 0 0 var(--primary-color,#287c59);background:var(--secondary-background-color,#f3f5f7)}.device.on.manual{box-shadow:inset 4px 0 0 var(--warning-color,#bf810e)}.device.on .icon{background:var(--primary-color,#287c59);color:var(--text-primary-color,#fff)}.device.on.manual .icon{background:var(--warning-color,#bf810e)}.devicepower{font-variant-numeric:tabular-nums}.runstate,.using{display:inline-block;font-size:9px;font-weight:800;letter-spacing:.35px;padding:3px 6px;border-radius:999px;background:var(--secondary-background-color,#eef2f3);color:var(--secondary-text-color,#697485);vertical-align:middle}.runstate.active{background:var(--primary-color,#287c59);color:var(--text-primary-color,#fff)}.device.manual .runstate.active{background:var(--warning-color,#bf810e);color:#fff}.using{background:var(--primary-color,#287c59);color:#fff}.mobile-menu{display:none;align-items:center;justify-content:center;width:42px;height:42px;padding:0;font-size:22px;border-radius:12px;flex:0 0 auto}.policy{background:var(--secondary-background-color,#f7f8f9)}.toggle{border-radius:999px;white-space:nowrap}.external .icon,.device .icon{width:34px;height:34px;border-radius:10px;display:grid;place-items:center;background:var(--secondary-background-color,#eef2f3);font-size:12px;font-weight:750;flex:0 0 auto}.readonly,.badge,.phasepill{display:inline-block;font-size:9px;font-weight:800;letter-spacing:.35px;padding:3px 6px;border-radius:999px;background:var(--secondary-background-color,#eef2f3);color:var(--secondary-text-color,#697485);vertical-align:middle}.external h2{margin:0;font-size:14px}.external p,.device p{margin:3px 0;color:var(--secondary-text-color,#697485);font-size:11px;line-height:1.4}.meta,.note{font-size:10px;line-height:1.5;color:var(--secondary-text-color,#697485);margin:8px 0}.controls{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-top:9px}.controls label{font-size:10px;color:var(--secondary-text-color,#697485);display:flex;align-items:center;gap:5px}.controls input,.formgrid input{width:58px;min-height:36px;text-align:center;border:1px solid var(--divider-color,#dce1e7);border-radius:9px;background:var(--card-background-color,#fff)}.spacer{flex:1}.mini{min-height:34px;padding:6px 9px;font-size:10px}.linkbtn{border:0;background:none;text-decoration:underline;padding:5px 0;min-height:28px;color:var(--secondary-text-color,#697485)}.empty{padding:14px;border:1px dashed var(--divider-color,#dce1e7);border-radius:13px;color:var(--secondary-text-color,#697485);font-size:12px;margin:10px 0}.formgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:10px 0}.formgrid label{font-size:10px;color:var(--secondary-text-color,#697485)}.formgrid label span{display:flex;align-items:center;gap:4px;margin-top:4px;color:var(--primary-text-color,#202735)}.settings-panel{padding:0 12px 14px}.settings-shell{border:1px solid var(--divider-color,#e0e4e9);border-radius:16px;margin-top:14px;overflow:hidden;background:var(--card-background-color,#fff)}.settings-shell>summary{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:14px 16px;background:var(--secondary-background-color,#f3f5f7);cursor:pointer;border:0}.settings-shell>summary span{display:flex;flex-direction:column;gap:2px}.settings-shell>summary small{font-weight:500;color:var(--secondary-text-color,#697485)}.settings-shell>summary em{font-size:9px;font-style:normal;color:var(--secondary-text-color,#697485);text-transform:uppercase}.settinglist{display:grid;gap:8px;margin:10px 0}.settingrow{display:grid;grid-template-columns:minmax(0,1fr) minmax(150px,220px);gap:12px;padding:12px;border:1px solid var(--divider-color,#e0e4e9);border-radius:12px}.settingcopy p{font-size:11px;line-height:1.45;margin:4px 0;color:var(--secondary-text-color,#697485)}.settingcopy small{display:block;font-size:10px;line-height:1.5;color:var(--secondary-text-color,#697485);margin-top:6px}.settingadvice{font-size:10px;line-height:1.45;padding:7px 8px;border-radius:8px;background:var(--secondary-background-color,#f3f5f7);margin-top:7px}.settingcontrol{display:flex;flex-direction:column;gap:6px;align-items:stretch;justify-content:flex-start}.settingcontrol>small{font-size:9px;color:var(--secondary-text-color,#697485)}.settinginput{display:flex;align-items:center;gap:5px}.settinginput input{width:100%;min-width:80px;min-height:38px;border:1px solid var(--divider-color,#dce1e7);border-radius:9px;padding:5px;background:var(--card-background-color,#fff)}.settinginput span{font-size:10px;color:var(--secondary-text-color,#697485)}.setting-switch{display:flex;gap:8px;align-items:center;font-size:11px;min-height:38px}.setting-switch input{width:18px;height:18px}.entityselect{width:100%;min-height:38px;border:1px solid var(--divider-color,#dce1e7);border-radius:9px;padding:5px;background:var(--card-background-color,#fff);color:var(--primary-text-color,#202735);font-size:10px}.entityselect.multi{min-height:76px}.resetsetting{min-height:30px;padding:4px 7px}.zone>span{min-width:0;overflow-wrap:anywhere}.zone>em{max-width:40%;text-align:right;overflow-wrap:anywhere}details{border-top:1px solid var(--divider-color,#e0e4e9);padding:11px 0;margin-top:8px}summary{cursor:pointer;font-weight:700;font-size:12px}.log{font-size:10px;line-height:1.5;padding:6px 0;border-top:1px solid var(--divider-color,#e0e4e9)}.log time{color:var(--secondary-text-color,#697485);margin-right:5px}.phaserow,.batteryrow,.scenario,.zone{padding:9px 0;border-top:1px solid var(--divider-color,#e0e4e9);font-size:11px}.phaserow>div,.batteryrow,.scenario,.zone{display:flex;align-items:center;justify-content:space-between;gap:8px}.phaserow small,.batteryrow small,.zone small{display:block;color:var(--secondary-text-color,#697485);font-size:9px;margin-top:3px}.phaserow p{margin:5px 0 0;color:var(--secondary-text-color,#697485);font-size:10px}.zone em{font-size:10px;color:var(--secondary-text-color,#697485);font-style:normal}.guidehero{padding:14px;border-radius:13px;background:var(--secondary-background-color,#f5f7f8)}.guidehero h2{margin:0}.guidehero p,.guide details p,.guide li{font-size:12px;line-height:1.55}.guidehero small{font-size:10px;color:var(--secondary-text-color,#697485)}.guide ul{padding-left:18px}.footer{display:flex;justify-content:space-between;align-items:center;gap:10px;border-top:1px solid var(--divider-color,#e0e4e9);margin-top:15px;padding-top:12px}.footer span{font-size:9px;color:var(--secondary-text-color,#697485)}a{color:var(--primary-color,#287c59);font-size:11px;text-decoration:none}@media(max-width:699px){.mobile-menu{display:flex}.head{padding-left:12px}.body{padding-inline:14px}.controls{gap:5px}.controls .spacer{display:none}.device .controls{align-items:stretch}.device .controls button{flex:1 1 auto}}@media(max-width:560px){.settingrow{grid-template-columns:1fr}.settingcontrol{align-items:stretch}}@media(max-width:370px){.body{padding-inline:14px}.head{padding-inline:14px}.nav{grid-template-columns:repeat(2,minmax(0,1fr))}.flowgrid.three{grid-template-columns:1fr}.formgrid{grid-template-columns:1fr}.tag{display:none}}@media(min-width:700px){.nav{grid-template-columns:repeat(auto-fit,minmax(90px,1fr))}.summarygrid{grid-template-columns:repeat(3,minmax(0,1fr))}.kpis{grid-template-columns:repeat(3,minmax(0,1fr))}.flowgrid{grid-template-columns:repeat(4,minmax(0,1fr))}}
    ${SP_INVESTIGATION_STYLE}</style><ha-card data-observations-current="${this._activityObservationsCurrent()}"><div class="head"><button class="mobile-menu" data-action="ha_menu" aria-label="Home Assistant-menu openen" title="Menu">☰</button><div class="logo">☀</div><div class="grow"><h1>${spEscape(this._config?.title||'SolarPilot')}</h1><p>Slim zonne-energie verdelen zonder comfort te verliezen</p></div><div class="tag">${spEscape(a.integration_version||'versie onbekend')}<br>LOKAAL EMS</div></div><div class="body">${this._modeBar(a)}${this._globalAlerts(c)}${this._analysisBanner(a)}${this._nav()}${this._view==='planning'?this._pvSummary(c):''}${this._viewHtml(c)}<div class="footer" style="flex-wrap:wrap" aria-label="Onderzoek en instellingen"><strong style="width:100%;font-size:12px">Instellingen & controle</strong><button type="button" class="linkbtn" data-action="manage_devices">Toestellen beheren</button><button type="button" class="linkbtn" data-action="pv_diagnostics">Zon · PV-diagnose</button><button type="button" class="linkbtn" data-action="learning_hub">Meetkwaliteit</button><button type="button" class="linkbtn" data-action="export_hub">Export</button><span>Geen elektrische beveiliging · actuele uitleg is release-gebonden</span><span class="version-info">Integratie: ${spEscape(a.integration_version||'onbekend')} · geladen kaart: ${SP_CARD_VERSION}</span><button type="button" class="linkbtn" data-action="configure">Instellingen & uitleg</button> <a href="/config/integrations/integration/solar_pilot">HA-instellingen ↗</a></div></div></ha-card>`;
    this._observationSignature=JSON.stringify([this._heatpumpDisplaySignature(c),this._wallboxActivity(c.wb||{})]);
    this._restoreUiState(uiState);
    this._installHelpButtons();
    this._lastRenderedView=this._view;
    this._renderSignature=this._viewRenderSignature();
    if(this._view==='export')Promise.resolve().then(()=>this._loadAnalysisFeedback());
  }
  async _loadOptionHelpers(){
    if(!customElements.get(SP_OPTION_HELP_TAG)){
      if(!this._optionLoad)this._optionLoad=import(`/solar_pilot_static/option-help.js?v=${SP_CARD_VERSION}`).catch(e=>{this._optionLoad=null;throw e;});
      await this._optionLoad;
    }
  }
  async _openHelp(step,key,title){
    this._uiHistory.prepare();
    try{await this._loadOptionHelpers();if(!this.isConnected)return;if(!this._helpDialog){this._helpDialog=document.createElement(spDialogTag('solar-pilot-option-help-dialog',SP_OPTION_HELP_TAG));this.shadowRoot.append(this._helpDialog);}const opened=this._helpDialog.open(step,key,title);this._uiHistory.track(this._helpDialog,()=>this._helpDialog.open(step,key,title));await opened;}
    catch(e){this._error='Uitleg niet geladen: '+(e.message||String(e));this._render();}
  }
  async _openDevices(){
    this._uiHistory.prepare();
    try{await this._loadOptionHelpers();if(!this.isConnected)return;
      if(!this._deviceManager){this._deviceManager=document.createElement(spDialogTag('solar-pilot-device-manager-dialog',SP_DEVICE_MANAGER_TAG));this.shadowRoot.append(this._deviceManager);this._deviceManager.addEventListener('device-options',e=>this._openOptions(e.detail.step,e.detail.id,e.detail.section));this._deviceManager.addEventListener('device-history',e=>this._openHistory(e.detail));}
      this._deviceManager.open(this._hass,this._last?.attributes?.device_management);this._uiHistory.track(this._deviceManager,()=>this._deviceManager.open(this._hass,this._last?.attributes?.device_management));
    }catch(e){this._error=e.message||String(e);this._render();}
  }
  async _openOptions(step=null,deviceId=null,section=null){
    this._uiHistory.prepare();
    try{
      await this._loadOptionHelpers(); if(!this.isConnected)return;
      const entryId=this._last?.attributes?.config_entry_id;
      if(!entryId){this._error='Config entry ontbreekt; open de HA-instellingen.';this._render();return;}
      if(!this._optionsDialog){this._optionsDialog=document.createElement(spDialogTag('solar-pilot-options-dialog',SP_OPTIONS_DIALOG_TAG));this._optionsDialog.uiHistory=this._uiHistory;this.shadowRoot.append(this._optionsDialog);}
      const hub=['sg_boost','sg_sources','sg_advanced','panasonic_monitor','comfort'].includes(step)?'comfort_hub':'loads_hub';
      const route=step==='water'?[{next_step_id:'water'}]:step?[{next_step_id:hub},{next_step_id:step}]:[];
      if(deviceId)route.push({device_id:deviceId,...(section?{section}:{})});
      await this._optionsDialog._spClosingPromise;if(!this.isConnected)return;const opened=this._optionsDialog.open(this._hass,entryId,route);this._uiHistory.track(this._optionsDialog,()=>this._optionsDialog.open(this._hass,this._last?.attributes?.config_entry_id));await opened;
    }catch(e){this._error='Configuratie niet geladen: '+(e.message||String(e));this._render();}
  }
  _question(step,key,title){return `<button type="button" class="option-question" data-action="option_help" data-help-step="${spEscape(step)}" data-help-key="${spEscape(key)}" data-help-title="${spEscape(title||key)}" title="Uitleg bij ${spEscape(title||key)}" aria-label="Uitleg bij ${spEscape(title||key)}">?</button>`;}
  _installHelpButtons(root=this._content){
    for(const el of root.querySelectorAll('[data-planner-setting],[data-priority]')){
      const step=el.dataset.plannerSetting?'planner':'device';
      const key=el.dataset.plannerSetting||'priority';
      const span=document.createElement('span');span.innerHTML=this._question(step,key,key);el.after(span.firstElementChild);
    }
    const actions={priority_edit:['dashboard','priority_board'],learning_hub:['dashboard','learning_hub'],analysis_export:['dashboard','analysis_export'],dishwasher_arm:['dashboard','dishwasher_arm'],dishwasher_cancel:['dashboard','dishwasher_cancel'],sg_boost_enabled:['sg_boost','enabled'],others_first:['dashboard','others_first'],participate:['dashboard','participation'],manual_start:['dashboard','manual_start'],manual_stop:['dashboard','manual_stop'],boost:['dashboard','boost']};
    for(const [action,[step,key]] of Object.entries(actions))for(const el of root.querySelectorAll(`[data-action="${action}"]`)){const span=document.createElement('span');span.innerHTML=this._question(step,key,el.textContent);el.after(span.firstElementChild);}
    for(const b of root.querySelectorAll('[data-action=option_help]')){
      const explain=async()=>{try{await this._loadOptionHelpers();const data=await customElements.get(spDialogTag('solar-pilot-option-help-dialog',SP_OPTION_HELP_TAG)).catalog();const row=data.entries[`${b.dataset.helpStep}.${b.dataset.helpKey}`];if(row){b.title=row.short;b.dataset.helpTitle=row.title;}}catch(_){}};
      b.addEventListener('pointerenter',explain,{once:true});b.addEventListener('focus',explain,{once:true});
    }
  }
  _wallboxProfile(wb){const p=wb.charging_profile;if(!p)return '';return `<div class="charging-profile"><strong>${Number(p.phases)} fase${p.phases===1?'':'n'} · max. ${Number(p.max_current_a).toLocaleString('nl-BE')} A · ≈ ${spPower(p.maximum_power_w)}</strong>${this._question('wallbox','profile_auto','Automatisch laadprofiel')}<small>Stroom: ${spEscape(p.current_source)} · Fasen: ${spEscape(p.phase_source)}</small>${p.warning?`<small>${spEscape(p.warning)}</small>`:''}<small>Panasonic-comfort blijft beschikbaar; extra SG-zonneboost gebruikt alleen toegestaan restoverschot zonder beschermd autoladen weg te nemen.</small></div>`;}
  async _perform(domain,service,data,successMessage=''){if(this._busy)return false;this._busy=true;this._error="";this._feedback="";this._render();try{await this._hass.callService(domain,service,data);this._feedback=successMessage;return true;}catch(err){this._error=err?.message||String(err);return false;}finally{this._busy=false;this._render();}}
  _invalidateWallboxPriorityRequest(){
    this._wallboxPriorityRequestSeq=(this._wallboxPriorityRequestSeq||0)+1;this._wallboxPriorityBusy=false;this._wallboxPriorityDialog?.close(true);
    this._wallboxPriorityObserved=null;this._wallboxPriorityReceivedAt=null;
  }
  _openWallboxPriority(target){
    const c=this._ctx(),choice=this._wallboxPriorityChoice(c,target);
    if(this._busy||this._wallboxPriorityBusy||this._hass?.user?.is_admin!==true||choice?.eligible!==true||!this._activityObservationsCurrent())return;
    const label=target==='global'?'Alle beschikbare toestellen':target==='dhw_extra'?'Extra SG-zonneboost':c.devices.find(d=>`device:${d.id}`===target)?.name||'Toestel';
    this._uiHistory.prepare();if(!this._wallboxPriorityDialog){this._wallboxPriorityDialog=document.createElement(SP_WALLBOX_PRIORITY_DIALOG_TAG);this.shadowRoot.appendChild(this._wallboxPriorityDialog);}
    const open=()=>this._wallboxPriorityDialog.open(this,target,label);open();this._uiHistory.track(this._wallboxPriorityDialog,open);
  }
  async _setWallboxPriority(target,option){
    const c=this._ctx(),choice=this._wallboxPriorityChoice(c,target),entry=c.a?.config_entry_id;
    if(this._busy||this._wallboxPriorityBusy)return false;
    if(this._hass?.user?.is_admin!==true||!entry||choice?.eligible!==true||!this._activityObservationsCurrent()||typeof this._hass?.callService!=='function'||!['auto',...SP_WALLBOX_PRIORITY_OPTIONS.map(([key])=>key)].includes(option))return false;
    const hass=this._hass,user=hass.user.id,seq=(this._wallboxPriorityRequestSeq||0)+1;this._wallboxPriorityRequestSeq=seq;this._wallboxPriorityBusy=true;this._error='';this._feedback='';let timer;
    const current=()=>seq===this._wallboxPriorityRequestSeq&&this._hass?.user?.id===user&&this._last?.attributes?.config_entry_id===entry;
    try{await Promise.race([hass.callService('solar_pilot','wallbox_priority_control',{config_entry_id:entry,target,option}),new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error('Geen bevestiging ontvangen')),15000);})]);
      if(!current())return false;this._feedback='Voorrang verstuurd; de actuele SolarPilot-status bevestigt de keuze.';return true;
    }catch(error){if(current())this._error='Voorrang niet bevestigd: '+(error?.message||String(error))+'. Controleer de actuele status voordat je opnieuw kiest.';return false;
    }finally{clearTimeout(timer);if(seq===this._wallboxPriorityRequestSeq){this._wallboxPriorityBusy=false;this._render();}}
  }
  _invalidateSgManualRequest(){if(this._sgManualBusy){this._sgManualRequestSeq=(this._sgManualRequestSeq||0)+1;this._sgManualBusy=false;this._busy=false;}}
  async _setSgManualControl(c,mode,duration){
    const s=c.sgBoost||{},entry=c.a?.config_entry_id;
    if(this._busy)return false;
    if(this._hass?.user?.is_admin!==true||!entry||s.configured!==true||!s.manual_control||typeof s.manual_control!=='object'||Array.isArray(s.manual_control)||typeof this._hass?.callService!=='function'){this._error='De tijdelijke SG-bediening is niet beschikbaar voor dit account.';this._render();return false;}
    if(!['auto','on','off'].includes(mode)||mode==='auto'&&duration!==undefined||mode!=='auto'&&![1800,3600].includes(duration)){this._error='Kies automatisch of een tijdelijke SG-bediening van 30 minuten of 1 uur.';this._render();return false;}
    if(mode==='on'&&(s.enabled!==true||c.a.mode!=='solar')){this._error=s.enabled!==true?'Schakel zonneboost eerst in.':'Kies eerst Automatisch regelen.';this._render();return false;}
    const hass=this._hass,user=hass.user.id,seq=(this._sgManualRequestSeq||0)+1;this._sgManualRequestSeq=seq;
    const current=()=>seq===this._sgManualRequestSeq&&this._hass?.user?.id===user&&this._last?.attributes?.config_entry_id===entry;
    const data={config_entry_id:entry,mode};if(mode!=='auto')data.duration_s=duration;
    this._busy=true;this._sgManualBusy=true;this._error='';this._feedback='';this._render();let timer;
    try{await Promise.race([hass.callService('solar_pilot','sg_manual_control',data),new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error('Geen bevestiging ontvangen')),15000);})]);
      if(current())this._feedback='Bedieningskeuze verstuurd; wacht op de actuele SolarPilot-status.';return true;
    }catch(error){if(current())this._error='SG-bediening niet bevestigd: '+(error?.message||String(error))+'. Controleer de actuele bedieningskeuze voordat je opnieuw kiest.';return false;}
    finally{clearTimeout(timer);if(seq===this._sgManualRequestSeq){this._busy=false;this._sgManualBusy=false;this._render();}}
  }
  _device(id){return this._last?.attributes?.devices?.find(d=>d.id===id);}
  async _click(ev){
    const b=ev.target.closest("button[data-action]"); if(!b||b.disabled||this._busy)return;
    const c=this._ctx(),a=c.a,d=this._device(b.dataset.id),action=b.dataset.action;
    if(action==='wallbox_priority_duration')return this._openWallboxPriority(b.dataset.priorityTarget);
    if(action==='wallbox_priority_auto')return this._setWallboxPriority(b.dataset.priorityTarget,'auto');
    if(action==='wallbox_priority_toggle'){
      const choice=this._wallboxPriorityChoice(c,b.dataset.priorityTarget);if(choice?.eligible!==true)return;
      return choice.active===true?this._setWallboxPriority(b.dataset.priorityTarget,'auto'):this._openWallboxPriority(b.dataset.priorityTarget);
    }
    if(action==='source_history'){return this._openSourceHistory(b.dataset.historyKind,b.dataset.id);}
    if(action==='heatpump_source_history'){return this._openSourceHistory('heatpump',undefined,{role:b.dataset.historyRole,source:b.dataset.historySource,expectedEntity:b.dataset.historyEntity});}
    if(action==='heatpump_history'){return this._openHeatpumpHistory();}
    if(action==='water_history'){return this._openWaterHistory();}
    if(action==='learning_hub'){return this._openLearning();}
    if(action==='export_hub'){return this._goExport();}
    if(action==='priority_edit'){return this._openPriorities();}
    if(action==='analysis_export'){return this._openAnalysis();}
    if(action==='analysis_download'){if(this._analysisAdministrator())return this._openAnalysis(true);return;}
    if(action==='analysis_feedback_upload'){if(!this._analysisAdministrator())return;if(this._view!=='export')this._goExport();this._content.querySelector('[data-analysis-feedback-file]')?.click();return;}
    if(action==='analysis_feedback_reload'){return this._analysisFeedbackAction('status');}
    if(action==='analysis_feedback_remove'){return this._analysisFeedbackAction('remove');}
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
    if(action==='sg_manual_control'){return this._setSgManualControl(c,b.dataset.sgMode,b.dataset.sgDuration===undefined?undefined:Number(b.dataset.sgDuration));}
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
    if(ev.target.matches?.('[data-analysis-feedback-file]'))return this._importAnalysisFeedback(ev.target.files?.[0]);
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
const spPanelTag = `solar-pilot-panel-${SP_CARD_VERSION.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'')}`;
if(!customElements.get(spPanelTag))customElements.define(spPanelTag,class extends SolarPilotCard {});
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
