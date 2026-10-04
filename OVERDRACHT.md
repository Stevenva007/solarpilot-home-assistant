<!-- solarpilot-handoff-schema: 1 -->
<!-- solarpilot-handoff-version: 1.0.0-beta.51 -->

# OVERDRACHT — SolarPilot

Laatst bijgewerkt: **4 oktober 2026**
Actuele ontwikkelde bron: **v1.0.0-beta.51**, op gepubliceerde beta.50-commit `5348ecaedd75326debc3b60764ab711882adf446`. Deze release laat paneel en automatisch beschikbare kaart via dezelfde module-route laden en voorkomt dubbele eigen kaartcatalogusitems. Alle beta.50-boilerstabiliteit, opdrachtrust, uitvoeringswachtreden, instellingen, geldige leerdata en eerdere veiligheidsregels blijven behouden. De software-/publicatiestatus staat in `docs/TESTRESULTATEN_BETA51.md`. De specifieke live oorzaak van de aangeleverde laadmelding, geladen beta.51-appkaart en fysieke toestelrespons zijn hier niet vastgesteld. Dit dossier beschrijft de actuele werking; releasehistoriek staat in `CHANGELOG.md`, Git en oudere releasedocumenten.

## 1. Projectdoel in gewone taal

SolarPilot verdeelt zonnestroom tussen autonoom autoladen, warmtepomp/tapwater en flexibele verbruikers. Het verbindt actuele P1/PV, fasebelasting, voorspellingen, kosten, lokaal leren en planning in één Home Assistant-regeling met begrijpelijke bediening en controleerbare beslisredenen.

## 2. Actuele basis

De absolute codebasis is gepubliceerde beta.50 op commit `5348ecaedd75326debc3b60764ab711882adf446`, tree `e67da41e0928a25b73893216edf34be6ff0ce5bc`. De onveranderlijke [beta.50-release](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.50) en haar werkelijk geslaagde publicatie-/pakketverificatie zijn de rollbackbasis. Gebruik geen oudere export als ontwikkelbasis.
Beta.46 verandert de voorrang tussen klimaatbewijs en algemene taakinfo voor de optionele warmwaterbuffer. De exact geregistreerde native `aquarea`-klimaatactie is leidend wanneer zij actueel en betrouwbaar is. De oudere `panasonic_cc`-AUTO-ambiguïteit blijft beschermd. De beta.45-vertraagde tankdoelbevestiging blijft intact: exact `aquarea`/`panasonic_cc`, minstens tien seconden en een passende nieuwe HA-rapportage; geen onmiddellijke optimistische echo. Een eerdere ACK of geladen versienummer bewijst geen nieuwe latere ACK of fysieke opwarming.

In deze werksessie is geen live Home Assistant-toegang. Softwaregate, GitHub-publicatie, pakketten, HACS-bestanden, geladen backend/kaart, doelbevestiging en fysieke opwarming zijn afzonderlijke bewijslagen. Bestaande gebruikersinstellingen, geldige leerdata, toestellen en prioriteiten blijven behouden. Alleen ongeldige opgeslagen leerregels en oudere gecontroleerde fasewaarnemingen zonder isolatiebewijs worden gericht niet hergebruikt; geen algemene leerreset.

## 3. Absolute ontwerpregels die niet stilzwijgend mogen wijzigen

- Behoud werkende functies, gebruikersinstellingen, leerdata en bestaande koppelingen. Veilige eenduidige migraties mogen geen oude fysieke opdracht herhalen. Een gewone herstartcontrole vereist geen gebruikersbevestiging; zij wacht automatisch op betrouwbaar actueel bewijs.
- De opgeslagen hervatkeuze blijft persistent over herstarts en tijdelijke Observe. Een bewuste latere Alleen bekijken/Pauze-keuze vervangt haar. Alleen oude opslag zonder hervatmarker en met aantoonbaar onderbroken beheerstatus mag de verloren Auto-keuze éénmalig herstellen.
- Echte fouten, manual hold, veranderd tankdoel en onduidelijke START-uitkomst blijven beschermd. Er is geen algemene automatische foutreset of tweede AEG-START.
- Fabrikantbeveiliging, autonome Panasonic-sterilisatie, elektrische grenzen en noodzakelijk comfort gaan vóór energieoptimalisatie.
- De centrale flexibele prioriteitenlijst is de enige leidende rangorde. Nieuwe gewone toestellen komen onderaan tot de gebruiker ze verplaatst. Veiligheid en noodzakelijk comfort zijn niet versleepbaar.
- Een toestel mag autozonnevermogen meewegen alleen vóór **Auto laden (Wallbox)** én met afzonderlijke toestemming. Een bewaarde Ja onder Auto laden blijft bewaard maar geldt effectief als Nee. De toestelwizard mag geen tweede rangorde terugschrijven.
- De Wallbox blijft volledig read-only; geen start/stop, laadstroom, laadmodus of faseopdracht. EV-krediet verzint geen elektrische capaciteit.
- Een voorkeurs-AEG staat vóór de Wallbox als die regel actief is. Een gestarte beschermde cyclus wordt nooit onderbroken; maximaal één native START per belading en geen blinde retry.
- Extra warm water tot 60 °C is een flexibele zonnebuffer en krijgt nooit Wallboxkrediet. Een lopende AEG is geen algemeen veto; alleen werkelijk restoverschot na alle conservatieve reserves mag de buffer vrijgeven.
- Afzonderlijke avondvoorraad blijft maximaal de ingestelde limiet en 55 °C en mag alleen bevestigde actuele autonome Full Solar-lading als vrijmaakbaar zonnevermogen meewegen. Manueel/oud/onbekend laden telt niet.
- Panasonic kiest HEAT/COOL. SolarPilot introduceert geen agressieve modusswitching, automatische Powerful, Force DHW, Force Heater of wijziging van DHW capacity.
- Betrouwbare actuele native `aquarea` idle/off gaat voor de optionele DHW-guard vóór algemene PUMP-taakinfo. Echte koeling wint altijd; actieve ruimteverwarming/preheating/defrosting behoudt de ingestelde voorrang. Ontbrekende betrouwbare klimaatdata blijft beschermd.
- Alleen bewezen koeling start of verlengt de koeluitloop. Onbekend bewijs blokkeert zolang het ontbreekt, maar maakt na bronherstel geen nieuwe halfuurwachttijd. De strengere geconfigureerde COOL-modusdetectie behoudt haar bestaande betekenis.
- Ruwe taakinfo blijft leerinformatie: PUMP is geen HEAT/COOL-/compressorbewijs en wordt niet als een normale rustsample aangeleerd door deze DHW-vrijgave.
- Handmatig of extern OFF gezette klimaatzones blijven onbeperkt OFF tot de gebruiker zelf AUTO kiest. Ook harde comfortoverschrijding, verlopen rusttijd, herstart of verwijderen mag die keuze niet overrulen. Comfort geeft dan een waarschuwing, geen inschakelopdracht. Alleen bewezen SolarPilot-eigen OFF/coast-zones mogen automatisch naar AUTO worden vrijgegeven.
- Klimaatopdrachten worden bij pending of onzekere uitkomst niet herhaald. Nieuwe betrouwbare terugmelding, actuele bronversheid en eigendom per zone blijven vereist; onbekende acties zijn geen idle-leerbewijs.
- De coastvrijgave gebruikt zekerheid voor werkelijk benodigde voorspelde respons. Ontbrekende ongebruikte koelervaring mag een voldoende geleerd verwarmingspad niet blokkeren; benodigde passieve/zon-/respons-/vertragingsgegevens moeten wel betrouwbaar zijn. Oude complete confidence blijft aparte vergelijkingsinformatie.
- Deze update bewaart geldige data en instellingen en vraagt geen algemene leerreset. Oud gecontroleerd fasebewijs zonder bewezen stabiele andere meters wordt niet opnieuw vertrouwd; geldige passieve/nieuwe geïsoleerde waarnemingen en handmatige hints blijven behouden. Winter-/zomercoast blijft opt-in en standaard uit; weerscontext is geen bewijs van actieve klimaatvraag.
- Zonnestabiliteit en de minimumtijd sinds de laatste werkelijk verstuurde DHW-doelopdracht lopen afzonderlijk. Een voltooide geldige stabiliteitskandidaat wordt niet gewist alleen vanwege die opdrachtrust; echt verlies van geldig bewijs/koeling/meetgaten blijven beschermd. Een onuitgevoerd voorstel krijgt geen eigendom of start-hysterese alsof het doel al is toegepast. Ook een geweigerd of op andere dispatch wachtend 55 °C-voorstel mag niet via de lagere PV-vasthouddrempel alsnog starten; een passend eigen werkelijk 55 °C-doel behoudt zijn legitieme hold.
- DHW-hysterese mag alleen een bewezen door SolarPilot uitgegeven en teruggemeld hoog doel vasthouden. Handmatige/fabrikantbediening blijft leidend; echte netafname of koeling mag luxe-doelen niet kunstmatig vasthouden.
- Realtime P1/PV en fysieke grenzen gaan altijd vóór forecast en aangeleerde schattingen. Ontbrekende data is niet nul.
- Geen geheimen, ruwe privédata, adressen of private installatie-identiteiten in publieke bron, pakketten of dit dossier.
- Codewijziging betekent dezelfde release ook tests, changelog, actuele gebruikersuitleg, installatie/upgrade, rollback, pakket en dit dossier bijwerken.

## 4. Actuele werking

### Bediening en uitleg

Dagelijkse modi: **Alleen bekijken**, **Automatisch regelen**, **Pauze**. Dashboardgroepen: Overzicht, Voorrang, Toestellen, Warmte & comfort, Planning, Energie, Batterij, Export en Uitleg. Het configuratiecentrum bevat ook **Auto & batterij**. `current_guide.py` is de enige actuele gebruikersuitlegbron; dezelfde tekst staat in Home Assistant en beide `ACTUELE_WERKING.md`-bestanden. Opties hebben releasegebonden hulp. Alleen bekijken wordt bij nog actief/pending beheer geweigerd: eerst Pauze en veilige vrijgave. Pauze mag uitsluitend bewezen eigen climateOFF naar AUTO teruggeven en een ACKed eigen numeriek batterijdoel neutraliseren zolang het actuele doel exact past; manualOFF, overgenomen/onbekende/foutieve doelen en willekeurige scripts blijven beschermd; ontbrekend eigendom-/bronbewijs is geen vrijgave. Browser Terug/Vooruit herstelt SolarPilot-schermen en beschermt onopgeslagen formulieren zonder acties te herhalen.

### Frontendregistratie en opnieuw laden

`frontend.py` registreert dezelfde versiegebonden `_CARD_URL` voor de extra kaartmodule en het zijbalkpaneel; `_panel_custom.module_url` vervangt de klassieke `js_url`-route. De [officiële HA-paneldocumentatie](https://www.home-assistant.io/integrations/panel_custom/) onderscheidt beide loaders. Een klassieke scriptcontext deelt globale declaraties bij verschillende release-URL's; modules hebben afzonderlijke scope. De kaart registreert custom elements enkelvoudig. `window.customCards` wordt in dezelfde array bijgewerkt: de eerste eigen catalogusplaats wordt actueel, alleen eigen duplicaten verdwijnen; vreemde kaarten, hun objecten en onderlinge volgorde blijven behouden.

Een open pagina kan eerdere constructorregistraties vasthouden. Na upgrade: volledige HA-herstart en webpagina opnieuw laden; Android-app volledig stoppen/heropenen, iOS-weergave verversen. De [officiële Companion FAQ](https://companion.home-assistant.io/docs/troubleshooting/faqs/#something-in-home-assistant-doesnt-work-the-same-way-it-does-on-my-desktop) ondersteunt die frontendcontrole en vergelijking met een browser. Geen tweede dashboardresource, configuratiereset of wijziging van boilerinstellingen. De getoonde Unable-to-load-melding bewijst geen specifieke live HTTP-/WebView-oorzaak; bestandslevering en daadwerkelijke clientfout blijven afzonderlijk te controleren.

### Automatisch herstel na herstart

Eerder beheerde toestellen worden tegen de echte betrouwbare status gereconcilieerd. Bekend ON wordt zonder herstelopdracht opnieuw herkend; bekend OFF laat eigendom los. Numerieke actuatoren worden alleen bij een passende actuele instelling opnieuw als eigendom herkend. Een veranderd numeriek doel laat eigendom los en houdt de bestaande handmatige rusttijd aan, zonder herstelwrite of onmiddellijke overschrijving. Minimum aan-/uittijden starten conservatief bij de nieuwe waarneming; daarna blijven gewone zon-, fase-, piek- en veiligheidsbesluiten gelden.

Ontbrekende, restored of onbeschikbare status laat de herstartcontrole wachten en opnieuw proberen tijdens elke normale regelronde (`interval_s`). Er wordt geen blinde OFF/START verstuurd. De gewone globale modus wacht totdat de betrokken leaseherstelcontroles klaar zijn; lopende beschermde programma's worden niet onderbroken. Daarna hervat de opgeslagen gebruikersmodus. De hervatkeuze is afzonderlijk persistent (`restart_requested_mode`), zodat tijdelijke Observe tijdens wachten haar niet verliest; een bewuste later gekozen Observe/Pause of verwijderen wist die hervatkeuze.

Alleen oudere opslag zonder `restart_requested_mode`, in Observe en zonder echte fout/manual hold/needs_review kan de verloren Auto-keuze éénmalig herstellen: er moet een onderbroken lease van een bekend, geconfigureerd Auto-toestel of een schoon routine-DHW-hersteljournal bestaan. Een nieuw opgeslagen veld, inclusief null, voorkomt latere afleiding bij bewuste gebruikersmodus. Gewone eerste installatie zonder onderbroken beheer blijft Alleen bekijken.

Voor AEG wordt een onzekere eerdere START niet herhaald. Alleen een nieuwe betrouwbare lopende of voltooide fase-terugmelding van ná START kan de specifiek gemarkeerde herstartonzekerheid oplossen; een oude Washing/Finished-stand, Idle of onduidelijkheid blijft beschermd. Een bevestigde lopende of voltooide AEG-cyclus verbruikt ook de bestaande APP-aanvraag; later Idle kan die oude belading niet herarmen. Andere fouten blijven bewaard en vereisen hun bestaande controle. Nieuwe beta.47-routineherstelmeldingen worden na geslaagd herstel automatisch opgeruimd zonder algemene foutmeldingen weg te vegen. Een oude beta.46-melding kan cosmetisch blijven staan; zij is zelf geen regelblokkering en mag na bevestigd herstel gesloten worden. Het overzicht toont tijdens gewone bronwacht **Automatische herstartcontrole** met automatische wachtreden, zonder resetknop. Alleen `restart_recovery_pending=true` verbergt die bediening; echte fouten/START-onzekerheid behouden hun waarschuwing en controle.

De boiler heeft een read-only `restart_recovery`-journal dat een gewone same-binding herstart automatisch afwerkt. Het doel, de tankmeting, bronversheid en handmatige/hygiënebronnen moeten bruikbaar zijn. Een passend beheerd doel wordt zonder doelwrite herkend. Een pending opdracht wordt niet opnieuw verstuurd en vereist een nieuwe rapportage ná de actuele herstart en ná de bestaande adapterwachttijd. Een veranderd doel wordt manual hold; echte fout of bewuste handmatige overname blijft beschermd. Fabrikantsterilisatie, krachtige bediening en native OFF behouden hun doel zonder SolarPilot-write. Routine-DHW-herstel wacht modulelokaal en geeft geen blijvende globale herstartblokkering. `restart_recovery_pending/reason` maken dit zichtbaar; een echte `needs_review` blijft afzonderlijk. Een open boilerjournal telt als busy bij veilig verwijderen, zodat onduidelijk herstel niet als vrijgegeven wordt getoond.

### Centrale voorrang en toestellen

De verticale lijst bevat vaste beschermde regels en verplaatsbare flexibele toestellen, Auto laden en extra warm water. De positie bepaalt de echte volgorde. Wallbox-toestemming toont bewaarde keuze én effectieve uitkomst. Centrale schema's beschermen de volgorde tegen oude toestelwizardvelden.

De samenvatting per toestel blijft de actuele engine-`result.reason`. De startuitleg toont invoer, benodigd vermogen en effectieve toewijzing na hogere prioriteiten, comfort, lopende cycli en toezeggingen. Ruwe injectie is apart zichtbaar; een complete checklist is geen zelfstandige startgarantie. Ook handmatige gewone toestelvraag kan een fout of interlock niet overrulen. Minimumlooptijden en beschermde cycli blijven intact. Geschiedenis toont geregistreerde start-/stoptijden, draaitijd en afzonderlijke Startreden/Stopreden; ontbrekende externe oorzaken, meetgaten en oude sessies blijven onbekend.

### Batterijopdrachten en gedeeld bronbewijs

Een pending batterijopdracht blokkeert gewone laststarts/verhogingen, AEG-deadline-START en nieuwe vermogensoverdracht. Veilige gewone lastreductie behoudt normale rustregels; beschermde afwascycli blijven afwerken. Klimaatvrijgave bij verwijderen wacht eveneens op batterijbevestiging. Commandointentie wordt vóór actuatie duurzaam opgeslagen. Direct vóór call worden native doel/eenheid/bounds, mapping, expliciete toestemming en Wallboxgrens opnieuw gecontroleerd; tussentijdse wijziging breekt af met duurzaam opgeslagen controlefout zonder fysieke aanroep of wijziging van handmatig doel. Alleen passende verse batterijpower van ná issue en een passend numeriek doel bewijzen HA-bevestiging; daarna moeten nieuw P1-bewijs en de bestaande wachttijd beschikbaar zijn. Oude P1-ruimte wordt niet hergebruikt.

Native SoC-sensoren vereisen %, eindige 0..100 en echte verse rapportage; geldige input_number-helpers mogen onveranderd zijn, maar niet restored/toekomstig/ongeldig. input_number-doelen gebruiken hun correcte domein. Native numeriek bereik en stap moeten exact neutraal nul ondersteunen; anders blijft het profiel read-only. Wallbox-gebonden actuatoren/geselecteerde scripts worden geweigerd; willekeurige scriptinhoud blijft door de gebruiker te controleren. Verwijderen vraagt verse neutrale power en bij numerieke aansturing exact nul als werkelijk doel; stilte bij niet-neutraal doel is geen vrijgave. Ontbrekende power/fout geeft geen retry of onterechte klaarstatus; bekend neutraal kan read-only worden afgehandeld. Een vervangend laad-/ontlaaddoel verrekenen met de werkelijk aanwezige eigen gestuurde flow voorkomt dubbel tellen en 0↔flow-pendelen in de berekening. Read-only/foutprofielen behouden hun gemeten residual zonder nieuw bedieningsrecht; native actuatorgrenzen voorkomen herhaalde afgekapte writes.

### AEG-afwasmachine

Een nieuwe overgang naar exact **Enabled** maakt één APP-aanvraag; startup met APP al aan doet dat niet. Vóór de gewone deadline: vandaag; vanaf die grens: volgende kalenderdag. Gewone standaarddeadline is 13:00. Een optionele maandagdeadline valt leeg terug op die gewone deadline. Bestaande tickets blijven bevroren tenzij de gebruiker expliciet dezelfde plandag laat herberekenen; dat maakt geen ticket, herarming of START. Netaanvulling vereist de bestaande toestemming.

START gebruikt uitsluitend de bevestigde native START-knop. Geen STOPRESET/PAUSE/RESUME/programmakeuze of stekkerrelais. Een onzekere START wordt niet blind herhaald. End Of Cycle blijft eventgestuurd en persistent; AirDry/Ado Drying is geen einde. Beschermde fasen omvatten Running, Washing, Prewash, Pre wash, Main wash, Rinsing, Drying, Ado Drying en Paused.

ConnectivityState is de actuele bereikbaarheidsheartbeat. Statische veiligheidswaarden zoals Ready To Start, exact Enabled, deur en programma mogen tijdens wachten ongewijzigd blijven. Unknown/unavailable/restored of onveilige waarden blokkeren. Een native cloud-pushbron zonder periodieke heartbeat heeft een echte statusopvraag nodig; kunstmatig bijgewerkte templates geven geen veiligheid. Een installatie-specifieke heartbeatautomatisering behoort niet tot de publieke bron.

De éénmalige legacy-recovery blijft na SolarPilot-start maximaal tien minuten gericht actief op relevante events en begrensde controles. Alleen één complete eenduidige same-device mapping wordt opgeslagen/live toegepast; listeners stoppen na succes/timeout/unload. Mapping vereist START, ApplianceState, ConnectivityState, RemoteControl, DoorState en programma. Een numerieke Alerts-teller zonder technische veiligheidssemantiek wordt niet automatisch gekozen. Een bewust verwijderd herstelprofiel komt niet stil terug; handmatige profielen/modi blijven behouden. Recovery geeft geen APP-aanvraag of START. Zonder exclusieve W-meter blijven cyclusvermogen en fasen conservatieve schattingen; geen fictieve leercycli.

### Warm water en klimaatbewijs

Normaal DHW-doel standaard 50 °C, bewaakte comfortgrens 46 °C, fysieke Panasonic-differentie -5 °C. Dit bewaakt comfort maar garandeert geen 46 °C: Panasonic kan bij een normaal 50 °C-doel rond 45 °C herstarten. Geen deadbandcompensatie of herstelboost naar 52 °C. Gewoon zonnedoel standaard 50 °C; extra restoverschot maximaal 60 °C. Actieve/onzekere koeling begrenst extra doelen standaard op 50 °C. De autonome 62 °C-sterilisatie blijft beschermd.

Voor exact geregistreerde native `aquarea` geldt actuele betrouwbare `hvac_action=idle/off` ook in AUTO/HEAT_COOL als geen actieve ruimteactie voor de optionele DHW-guard. Een algemene PUMP-taak, of oude/niet herkende optionele taakdata, overschrijft die actie niet. De ruwe taak en `space_activity_status` blijven zichtbaar; de oorspronkelijke `space_activity_source.space_busy` blijft conservatieve taak-/leerinformatie.

Voor oudere `panasonic_cc` blijft AUTO/HEAT_COOL idle/off onduidelijk tenzij een actuele expliciete IDLE/WATER-taak deze ambiguity opheft. PUMP geeft daar geen vrijgave. Geen taakmelding vervangt een ontbrekende, restored, oude of onbeschikbare klimaatbron. Echte cooling heeft altijd voorrang; heating/preheating/defrosting laat een nieuwe extra buffer wachten wanneer `respect_space_climate` aanstaat. Een al hoger aangevraagd doel wordt niet alleen wegens nieuwe verwarming afgebroken. De guardstatus `space_climate_busy` weerspiegelt het voor optionele DHW bruikbare klimaatbewijs; zij verzint geen compressorvermogen.

Alleen bewezen koeling legt nieuw koelverleden vast in `last_cooling`/`cooling_wall` voor de ingestelde uitloop (standaard 1800 s). Een native warmwatertaak kan een bestaande recente koelbescherming vasthouden. Unknown blokkeert nu maar schrijft geen nieuw koelverleden. Vóór beta.46 opgeslagen koel-/onzekerheidstijden blijven conservatief behouden: de oorspronkelijke oorzaak is niet betrouwbaar te reconstrueren. Een bestaande uitloop of bescherming tijdens een native warmwatertaak kan dus nog tijdelijk gelden; de upgrade wist geen mogelijk echte koeling. Een teruggekeerde betrouwbare idle-bron wacht uitsluitend nog op eventuele uitloop van echt eerder bewezen koeling en overige bestaande voorwaarden. De ingestelde strengere COOL-modusdetectie blijft behouden.

Nieuwe optionele verhogingen vereisen bestaande zonnestabiliteit en rust tussen doelopdrachten (standaard 300 s en 1800 s). De opdrachtrust begint bij de laatste werkelijk verstuurde doelopdracht, ook normaal herstel of verlaging; dit beginpunt en de ingestelde tijd worden niet verruimd. Een afgeronde stabiliteitscontrole blijft tijdens die rust geldig zolang de actuele kandidaatvoorwaarden geldig blijven. Het overzicht en de warmwaterdetailkaart tonen de werkelijke runtime-status, zodat gunstig beleidsadvies geen uitvoeringswachtreden verbergt; ook wachten op andere opdrachten en ongeschikte native doelgrenzen blijven zichtbaar. `remaining_s` blijft de stabiliteitswachttijd; `optional_raise_remaining_s` benoemt de afzonderlijke resterende opdrachtrust zodra een rijpe extra verhoging daarop wacht. Voorstel, native doel en tankmeting blijven afzonderlijk; voorstel is geen dispatch-/ACK-/opwarmbewijs. Nachtbeperking blokkeert extra buffers maar verlaagt het normale doel niet. Ochtendcontrole en begrensde avondvoorraad zijn apart opt-in en gebruiken voorzichtig tankleren; het gewone doel wordt niet hoger om een native start af te dwingen. Gewoon comfort staat vóór Wallbox. De avondvoorraad mag uitsluitend actuele, expliciet bevestigde Full Solar-lading krediet geven: verbonden, vragend, minstens 50 W, sessie en vermogen maximaal 120 s oud. Extra 60 °C krijgt geen EV-krediet.

Voor extra 60 °C worden huisreserve, batterijontlading, nog niet gebruikte toesteltoezeggingen en een lopende AEG zonder exclusieve meter conservatief afgetrokken. Actuele/gefilterde net- en PV-ruimte begrenzen de toewijzing; kwartierpiek- en fasegrenzen blijven gelden. Een passend startklare AEG krijgt eerst één startkans. Een lopende beurt blokkeert niet categorisch als er na alle reserves genoeg echt overschot blijft.

Doelterugvalhysterese vereist bewezen SolarPilot-eigendom. Echte netafname boven de grens, actieve koeling en onbeheerde/onbevestigde 60 °C slaan gewone terugvalvertraging over. Manual hold, pending opdrachten, fabrikantbeveiliging en hygiëne blijven schrijfguards. De gerichte **Hervat** beëindigt alleen de manual hold, uitsluitend buiten Automatisch regelen en zonder pending opdracht; zij schrijft geen doel en start geen cyclus.

### Klimaat, PV, fasen, kosten en leren

Panasonic blijft eigenaar van HEAT/COOL. Handmatige OFF-zones blijven uit totdat de gebruiker zelf AUTO kiest, inclusief harde comfortoverschrijding; alleen eigen coast-zones mogen automatisch worden vrijgegeven. Klimaatcoast/herstel bewaakt eigendom en persistent handmatige bescherming per zone. Pending/onzekere opdrachten worden niet herhaald en unknown/restored/onbeschikbare acties niet als idle geleerd. Een nieuwe OFF wacht bij onbekende niet-OFF-actie; terugkeer van bewezen eigen coast naar AUTO blijft apart mogelijk. De per-zone manual OFF, tijdelijke holds, expected ownership en pending opdrachtgegevens zijn persistent. Een matching HA-modebericht telt pas na minstens tien seconden na opdracht of actuele herstart; een lokale echo is geen bevestiging. Timeout na 180 seconden behoudt de feitelijke stand, maakt een zichtbare fout en beschermt werkelijk OFF zonder automatische replay. Interne context_id blijft buiten de UI; HA-terugmelding is geen onafhankelijk fysieke ACK. Als een expliciete gebruikers-OFF een pending SolarPilot-AUTO annuleert, herstelt een latere native/contextloze AUTO-terugmelding nooit de controle, ongeacht verstreken tijd. Alleen expliciete gebruikers-AUTO in HA heft die uitsluiting op; geen blinde corrigerende OFF. Controleer bij vertraagde rapportage de actuele native stand.

De coastbeoordeling gebruikt passieve respons plus zonnewinst wanneer gebruikt; bij voorspelde ondergrens verwarmrespons en bestaande reactievertraging, bij bovengrens koelrespons en reactievertraging en bij beide richtingen beide responses. Zonder voorspelde overschrijding is een ongebruikte actieve respons geen verplichte gate. Handmatige OFF-zones vallen buiten automatisch plannen; hun ontbrekende modelbewijs blokkeert niet op zichzelf een vrijgegeven AUTO-zone. Iedere concrete opdracht wordt vlak voor verzenden opnieuw met actuele zones en guards beoordeeld. Alleen opeenvolgende actuele/toekomstige forecasturen met passende weer-/PV-tijdposities geven nieuwe coastvrijgave. Bij ontbrekende forecast mag alleen bewezen eigen coast veilig AUTO hervatten zonder gewone daglimiet/minimumvasthoudtijd; manualOFF, vaste HEAT/COOL en gebruikersrust blijven beschermd. Coastfeedback start/telt uitsluitend na latere minimaal-tienseconden-HA-bevestiging van alle targetzones; mislukte/onbevestigde opdrachten leveren geen episode op en worden na herstart niet gereconstrueerd. Zonebindingwijzigingen wachten op veilig afronden van eigen coast/pending zodat beheer niet stil verweesd wordt. De legacy volledige confidence blijft apart beschikbaar. De bestaande reactievertraging blijft gedeelde historische leerervaring; geen afzonderlijk bewezen vertraging per richting uit oude samples afleiden. Modelstatus, relevante zekerheid en echte samples/dagen/episodes zijn zichtbaar; ontbrekend relevant bewijs houdt coast conservatief uit. Winter-/zomercontext beschrijft weer ten opzichte van binnendoel, geen actuele vraag; winter-/zomercoast blijft standaard uit. De ingestelde reactievertraging blijft als fallback zichtbaar waar nog niet geleerd. Warmtepompleren blijft gescheiden van gewone huishoudbasislast; modellen leren uitsluitend uit voldoende echte meetdagen/cycli.

PV gebruikt werkelijk geconfigureerd paneelvermogen, omvormerlimiet, lokale schaduw en kalibratie; actuele PV blijft waarheid. Ontbrekende forecaststaart/gaten blijven onbekend en worden geen nulbewijs of kunstmatig lage forecastfout. Een volledig gemeenschappelijk weer-/PV-venster mag worden gebruikt wanneer het de nodige coastvoorspelling dekt; ontbrekende staart wordt niet ingevuld, interne gaten blokkeren. Ontbrekend actueel PV-vermogen geeft geen thermisch 0W-leerbewijs. Met zonnewinst ingeschakeld moeten beide interval-eindpunten bekende PV hebben; ontbrekend bewijs onderbreekt slechts het interval en behoudt geldige opgeslagen modellen. Zonder expliciet ingeschakelde zonnewinst mag leren zonder PV en zonder aftrek van een zonnecoëfficiënt doorgaan. Plan-/forecaststappen volgen verstreken UTC-tijd met lokale labels/deadlines. Replay vraagt volledige lokale dagen van 92/96/100 werkelijk gedekte kwartieren; partiale dagen geven geen volledige-dagprestatieclaim. Fase- en plannerregels verzinnen geen capaciteit. De planner combineert horizon, deadlines, gemeten of verklaarbaar geschat vermogen en conservatieve cyclusreserves. Ontbrekende duur-/fasemetingen worden niet optimistisch ingevuld. Gecontroleerde fasewaarnemingen vereisen bruikbare beginmetingen en stabiele andere gekoppelde meters. Oude gecontroleerde waarnemingen zonder dit opgeslagen isolatiebewijs worden bij upgrade niet hergebruikt; geldige passieve/nieuwe geïsoleerde waarnemingen en handmatige hints blijven behouden. Malformed opgeslagen leerregels worden afzonderlijk overgeslagen zonder geldige andere regels te wissen.

Kosten tonen netto afname/injectie, directe PV en dag-/horizonwaarden met meetdekking. Onbeschikbare, restored, toekomstige of meer dan 36 uur oude dynamische prijsbronnen vallen terug op het ingestelde vaste tarief. Ontbrekende rijen verschuiven de tijdposities niet; ontbrekende tijd/prijs wordt geen verzonnen reekswaarde. Geldige nulprijzen blijven nul. Booleans en niet als eindig getal te verwerken prijzen en ongeldige tijden worden niet als gratis tarief herinterpreteerd en gebruiken vaste fallback. De aparte automatische-voordeelregistratie bewaart maximaal negentig dagen en is een opportunity-value-schatting, geen bewezen extra besparing die nogmaals van de kosten af mag. Batterijscenario's zijn adviserend; fysieke batterijregeling blijft aparte dubbele opt-in met eigenaarschap. Analyse-export benoemt werkelijke dekking, gaten, bootstrap, live leerdata, modellen en besluiten; export wordt niet automatisch geüpload. Pseudoniemen behouden consistente IDs/verwijzingen en korte/historische labels, met schema-/sleutel-/eenheids-/enumbehoud. Setup/unload sluiten oude callbacks en taken af; startafbreking schrijft geen gedeeltelijk geladen toestand over goede opslag. Ongeldige afzonderlijke pending-/optie-/archiefrecords houden geldige siblings intact. Klimaatdeactivatie en bindingswijziging wachten ook bij onbereikbare eigen OFF/pending-zones.

### Wallbox

Een expliciete effectieve-sessiebron onderscheidt zonne-auto laden/wachten, manueel en gestopt; geen hardcoded installatie-entity-id. **Zonne-auto · wacht op auto** wordt standaard herkend. Alleen een exact oude standaardwaardelijst wordt compatibel uitgebreid, nooit een eigen lijst. Native Full Solar en actuele sessievoorwaarden blijven nodig. Een verse geldige lage laadkracht heft reservering alleen op bij expliciet geen laadvraag, geen verbonden auto of bekende inactieve status. Oud/restored/onbekend/strijdig blijft fail-closed. Ongeldige, toekomstige en niet-eindige operationele rapportagetijden geven geen vrijgave; native verse bronnen kunnen zonder Wallbox-write weer worden herkend.

De read-only historie bewaart maximaal dertig laadperioden. Native stopreden wordt alleen aan een aantoonbaar nieuwe tijdgecorreleerde rapportage gekoppeld; gaten/herstarts/oud bewijs blijven onbekend. Geen start/stop/modus-/stroom-/faseopdracht.

## 5. Configuratie, integraties en belangrijke entiteiten

Generieke bronnen: Home Assistant, P1/HomeWizard, PV/Forecast.Solar, Panasonic Aquarea, Wallbox, flexibele toestellen en toekomstige batterijprofielen. Exacte entity_ids en apparaatidentiteiten altijd uit actuele lokale configuratie lezen en nooit publiek hardcoden.

Voor DHW: tankmeting, native tankdoel, geregistreerde doeladapter, klimaatbronnen, optionele native taakbron, handmatige/fabrikant-hygiënebronnen en eventueel een exclusieve elektrische tank-W-meter. Een gedeelde warmtepompmeter is geen tankmeter. Vertrouwen in `aquarea` vereist exacte registratieherkomst, geen naamheuristiek.

AEG-rollen zijn same-device; optionele cyclephase/starttijd/alarm mogen alleen met passende semantiek gekoppeld worden. Device-id wordt uitsluitend fingerprinted in publieke status. Wallbox: effectieve sessie, native Full Solar, laadvraag/verbinding en vermogen. Bestaande lokale privébundel kan lege werkelijk bestaande koppelingen aanvullen; HACS bewaart `userfiles`.

## 6. Belangrijke ontwerpbeslissingen + waarom

- **Werkelijk gepubliceerde beta.50-bron als basis** voorkomt regressie door een oudere export.
- **Eén module-route voor kaart en paneel** voorkomt de klassieke/module-loadercombinatie; idempotente eigen catalogusregistratie behoudt kaarten van andere integraties. Dit geeft geen extra actuatorrecht en bewijst geen specifieke live HTTP-oorzaak.
- **Native klimaatactie vóór algemene taakinfo** voorkomt een onnodige DHW-blokkering bij betrouwbaar idle zonder echte koel-/verwarmprioriteit te versoepelen.
- **Exacte adapterherkomst** beperkt vertrouwen tot `aquarea`; oudere `panasonic_cc` AUTO blijft beschermd. Geen algemene claim dat elke Panasonic-adapter dezelfde actiebetrouwbaarheid heeft.
- **Onbekend is geen bewezen koeling** behoudt onmiddellijke bescherming zonder fictief koelverleden en extra wachttijd na bronherstel.
- **Guard en leren afzonderlijk** laat optionele DHW betrouwbaar beslissen zonder PUMP als normale of gemeten compressoractie aan te leren.
- **Onafhankelijke stabiliteit en opdrachtrust** voorkomt steeds opnieuw beginnen bij blijvend voldoende zon zonder de minimumtijd sinds de laatste echte doelopdracht te verkorten. Een wachtend voorstel geeft geen eigendoms-/hystereserechten; de UI toont de actuele uitvoeringswachtreden.
- **Latere doelrapportage** sluit optimistische lokale echo uit maar claimt geen onafhankelijke fysieke ACK of opwarming.
- **Eigendom per zone en DHW-doel** beschermt handmatige/fabrikantbediening tegen algemene herstelopdrachten en valse hysterese. Manual OFF blijft uit tot gebruikers-AUTO, zodat comfortbewaking een bewuste uitschakeling niet ongedaan maakt.
- **Relevante responsconfidence** voorkomt dat ontbrekende ongebruikte koelervaring het verwarmingspad blokkeert, zonder passief/zon-/werkelijk benodigd responsbewijs als geleerd te verzinnen.
- **Same-device unieke AEG-mapping en APP-latch** voorkomt verkeerde actuatoren en ongewenste starts na upgrade. Begrensde retry vangt late setup op zonder permanente autoconfiguratie.
- **Echte engine-reden en toewijzing** voorkomt dat een UI-checklist een tweede startalgoritme wordt.
- **Afzonderlijke opgeslagen/effectieve toestemming** houdt centrale volgorde begrijpelijk zonder actuatorrechten stil te verruimen.
- **Begrensde leerreset** wist alleen bedoelde afgeleide modellen, geen configuratie, operationele klimaatveiligheid, bootstrap of andere cyclus-/DHW-modellen; reset stuurt geen actuator.

## 7. Automatische processen

- Start/reload reconcilieert bestaande opslag en echte toestanden zonder oude opdrachten te herhalen. Tijdelijk ontbrekende status wordt bij gewone volgende ticks opnieuw gecontroleerd; hervatkeuze en echte fouten blijven persistent.
- De boiler controleert een routineherstart automatisch read-only; pending doelen vereisen nieuw postrestart bronbewijs. Echte manual hold/fout/veranderd doel blijft beschermd.
- Migraties behouden prioriteit/configuratie/leerdata; éénmalige veilige analyse-activering overschrijft latere gebruikerskeuzes niet.
- Legacy-AEG-herstel/reparatie blijft idempotent, gemarkeerd en beperkt; post-start listeners stoppen na succes/timeout/unload.
- De actuele regelcyclus bewaakt bronversheid, klimaat-/koelbewijs, eigendom, pending ACK, hygiëne, reserves, minimumlooptijden en elektrische ruimte.
- Native taakdata wordt alleen gelezen. Optionele DHW-vrijgave verandert de ruwe taak-/leerinformatie niet.
- Voor exact herkende doeladapters vereist ACK een passende latere HA-rapportage na minstens tien seconden. Timeout en manual hold geven geen blinde retry of automatisch hervatten.
- Historiek, modellen, afwasaanvragen, koeltijd en planner blijven lokaal/persistent met bestaande begrensde bewaartermijnen. Geen automatische export-upload.

## 8. Geheimenbeleid

Nooit wachtwoorden, tokens, API-sleutels, private keys, exacte adressen, ruwe privé-analyses of private device-identiteiten in Git/release/OVERDRACHT. Lokale privébundels en HA-back-ups blijven buiten publieke bron/pakketten. Publieke preflight moet groen zijn vóór publicatie.

## 9. Testprocedure + actuele teststatus

De definitieve volledige beta.51-suite behaalt **2521 geslaagde tests in 18.76 s**, nul fouten en nul overgeslagen tests, met Python 3.12.14. De tien nieuwe gevallen en alle behouden beta.50-regressies zijn hierin werkelijk uitgevoerd. Python-bronsyntax van 65 productiemodules, JSON-syntax van vier bestanden en beide JavaScript-syntaxcontroles zijn geslaagd. Publieke preflight, handoff, actuele uitleg (hash `7f0c9817f8b1c53a`), repositoryvalidatie en diffcontrole zijn groen. Het offline `SolarPilot-voorbeeld.html` is opnieuw opgebouwd met fictieve gegevens, zonder HA-contact of toestelopdracht. Volledig verslag: `docs/TESTRESULTATEN_BETA51.md`.

Vijf nieuwe Node-gevallen evalueren de werkelijke kaartbron als ES module met DOM-doubles, inclusief herhaalde module-evaluatie, volgende URL, legacy classic gevolgd door module en gericht opruimen van eigen bestaande catalogusduplicaten. Zij bewaken enkelvoudige custom-elementregistratie, behoud van de gedeelde catalogusarray en vreemde kaarten, directe HA-paneelproperties zonder Lovelace-setConfig, verbinden/loskoppelen van listeners en nul fysieke serviceaanroepen. Vijf frontendregistratie-/static-path-contractgevallen controleren de Python-route afzonderlijk. Alle beta.50-boiler-, UI- en veiligheidsregressies blijven behouden.

Geen live Home Assistant-toegang, geladen beta.51-appkaart of fysieke toestelrespons in deze werksessie. Volledige browserproeven zijn niet opnieuw uitgevoerd. Node DOM-doubles en registratiecontracten bewijzen geen werkelijke browser-HTTP-levering, WebView-cache of specifieke oorzaak van de laadmelding. Publicatie en pakketverificatie blijven afzonderlijke bewijslagen; hun controle staat bij de onveranderlijke GitHub-release en workflow.

## 10. Bekende problemen / beperkingen

- De aangeleverde beta.50-laadmelding toont de geweigerde paneellading, maar geen exacte HTTP-status, bestandsinhoud of WebView-fout. Loader-/registratiefouten zijn afzonderlijk softwarematig bewezen; live verdwijnen van de melding is niet vastgesteld. De behouden beta.50-boilerreparatie blijft onder regressiecontrole, zonder nieuwe fysieke opwarmclaim.
- Een actuele native idle/off-actie geeft geen fysieke compressor- of tankenergiegarantie; `PUMP/WATER` meldt slechts een taak.
- Latere HA/cloud-doelrapportage is geen onafhankelijke fysieke ACK. Een nieuwe natuurlijke latere doelbevestiging en tankopwarming blijven installatieacceptatie.
- De oudere `panasonic_cc` AUTO/HEAT_COOL-mapping blijft zonder expliciete actuele taakinfo ambigu.
- Geen browsergate of live herstart-/klimaat-/koelroute in deze werksessie bevestigd; geen fysieke beta.51-acceptatie.
- Een 50 °C-doel met -5 °C-differentie kan 46 °C niet garanderen; het profiel is geen hygiënegarantie.
- Zonder exclusieve afwas-/tankmeter blijven vermogen en programmafasen conservatief geschat; geen fictieve gemeten cycli.
- Onvolledige/ambigue AEG-mapping en een bewust onbetrouwbare alarmbron blijven fail-closed. De retry eindigt na tien minuten.
- Lage modelzekerheid is geen toestemming om comfort te versoepelen. Batterijbediening blijft zonder hardware/eigenaarschap adviserend.

## 11. Concrete openstaande ontwikkeling

- Beta.50-publicatie en beide pakketten zijn werkelijk gecontroleerd. Gebruik voor de afzonderlijke beta.51-publicatie-/pakketcontrole de exacte onveranderlijke tag, GitHub-release en Validate-workflow; hun actuele bewijs staat daar. Een eerdere releasecontrole bewijst geen latere publicatie.
- Gebruiker installeert beta.51, herstart HA en opent de frontend opnieuw. Controleer backend/kaart en paneel afzonderlijk; blijft de melding bestaan, lees werkelijk kaartantwoord en clientfout uit. Automatisch routineherstel, afzonderlijke boilerwachttijden en native klimaatactie behouden hun bestaande acceptatiecontrole. In deze werksessie is geen live HA-toegang.
- Observeer een volgende natuurlijke toegestane doelopdracht met passende latere rapportage en werkelijke tankrespons; forceer geen doel, Powerful, APP-aanvraag of START voor bewijs.
- Eventueel de veertien browsercontroles later opnieuw uitvoeren in een omgeving met Chromium.
- Exclusieve Shelly-afwasmeting toevoegen wanneer hardware beschikbaar is; tot dan fasen/energie niet verzinnen.
- Thermische/PV/faseprofielen uit echte meetdagen laten verbeteren; actieve koelroute, fysieke terugval en eventuele ontbrekende cyclus-eindregistratie afzonderlijk controleren.

## 12. Installatie/upgrade en rollback

Zie `START_HIER.md` en `docs/BETA51_INSTELLEN.md`: actuele volledige back-up, beschermde cyclus afwerken, exact beta.51 via HACS/lokaal pakket, volledige HA-herstart, webpagina/app opnieuw openen, backend én geladen kaart/paneel controleren, bron-/reviewcontrole in Alleen bekijken/Pauze en pas daarna gewone regeling hervatten. Bestaande instellingen, leerdata, APP-tickets en `userfiles` blijven behouden. Een gewone herstartcontrole rondt automatisch af; echte manual hold/fout of gewijzigd doel wordt niet automatisch gewist.

Rollback: **Pauze → beschermde cycli afwerken → onveranderlijke beta.50 of gecontroleerde volledige back-up herstellen → Home Assistant herstart → webpagina/app opnieuw openen → backend/kaart, eigendom, bronnen en beveiligingen controleren**. Beta.50 behoudt de boilerreparatie en eerdere veiligheidsregels, maar bevat nog de klassieke/module-loadercombinatie en mogelijke dubbele eigen catalogusitems die beta.51 herstelt. Geen STOPRESET vanuit SolarPilot, extra APP-aanvraag, Powerful of Wallbox-opdracht om upgrade/rollback te forceren.

## 13. Belangrijkste bestanden

- `frontend.py`, `frontend/solar-pilot-card.js`: gebundelde static-path-, module-/paneelregistratie, eigen kaartcatalogus en rendercode.
- `dhw.py`, `dhw_runtime.py`: klimaat-/koel-/doelbeleid, eigendom, veilige terugval en ACK.
- `runtime.py`: bronregistratie/versheid, fysieke commandoroute, DHW-Hervat en begrensde leerreset.
- `heatpump_learning.py`, `thermal_climate.py`, `thermal_runtime.py`: taak-/responsleren en eigendom per klimaatzone.
- `dishwasher.py`, `dishwasher_app.py`, `dishwasher_recovery.py`: native startveiligheid, APP-ticket, deadlines, einde en begrensde recovery.
- `priority_board.py`, `wallbox_policy.py`, `wallbox_activity.py`: centrale voorrang, read-only sessiebeleid en begrensde waarnemingshistoriek.
- `savings.py`, planner/PV/fasemodules: schattingen, dekking en begrensd lokaal leren.
- `current_guide.py`, `option_help.py`, translations en gegenereerde uitleg/help: één releasegebonden gebruikersbeschrijving.
- `tests/`, `tools/check_*.py`, `tools/validate_repository.py`: regressies, consistentie en openbare releasechecks.
- `CHANGELOG.md`, `START_HIER.md`, `docs/BETA51_INSTELLEN.md`, `docs/TESTRESULTATEN_BETA51.md` en dit dossier: huidige release; oudere releasedocumenten blijven historie.

## 14. Release-checklist

1. Actuele handoff lezen en absolute gepubliceerde beta.50-basis bevestigen.
2. Manifest, const, current guide en beide frontendversies gelijk aan beta.51 houden.
3. Actuele uitleg/optiehulp genereren en alle relevante lokale gates uitvoeren; werkelijke beperkingen opnemen.
4. Code, changelog, gebruikersuitleg, installatie/rollback, testverslag en OVERDRACHT samen actualiseren.
5. Publieke preflight en diffcontrole groen; geen caches/private data in commit/pakket.
6. Alleen na geslaagde gate naar de bestaande repository uploaden. Nieuwe beta.51-tag/workflow/release; oude tags en assets onveranderd laten.
7. Beide gepubliceerde ZIP's downloaden, inhoud tegen exact tag vergelijken en werkelijke grootte/SHA-256 vastleggen.
8. Publicatie niet gelijkstellen aan HACS-installatie, geladen backend/kaart, ACK of fysieke opwarming.

## 15. AI-handoff

Werk voort op gepubliceerde beta.50-commit `5348ecaedd75326debc3b60764ab711882adf446` en de hier ontwikkelde beta.51. De gebruiker heeft de herstelling én upload naar de bestaande GitHub-repository na testen uitdrukkelijk gevraagd. Vraag geen herhaalde uploadtoestemming; voltooi eerst de softwaregate en pakket-/documentconsistentie.

Beta.51 behoudt alle beta.50-regels voor boilerstabiliteit/opdrachtrust, manual OFF, geen onzekere opdrachtreplay, relevante modelzekerheid, batterij-/P1-serialisatie, forecast-/DST-/replaybewijs, exportstructuur en levenscyclus-/opslagveiligheid. De paneelregistratie gebruikt module_url gelijk aan de extra kaartmodule; eigen catalogusitems blijven idempotent, andere integraties behouden hun catalogus. Een loader-/registratiereparatie bewijst niet de specifieke live HTTP-/WebView-oorzaak van een screenshotmelding. De boilerstabiliteitskandidaat blijft geldig tijdens de bestaande opdrachtrust zolang actuele voorwaarden blijven passen; een onuitgevoerd voorstel krijgt geen eigendoms-/hystereserechten. Verlies van geldig zonnebewijs, echte koeling en meetgaten blijven beschermd. Toon de actuele uitvoeringswachtreden bij het gemelde doel; gunstig beleidsadvies mag haar niet verbergen, zonder extra fysieke toestemming of kortere interval. Geen algemene datareset, verruimde actuatortoestemming of fysieke ACK claimen.

De behouden beta.47-regels hervatten gewone herstartcontrole automatisch op basis van nieuwe echte bronwaarnemingen, met persistent gebruikersintentie en modulelokale routine-DHW-controle. Dit herhaalt geen fysieke opdrachten en wist geen echte manual hold/fouten. Oudere opslag zonder intentiemarker heeft uitsluitend bij onderbroken beheertaken een eenmalige reparatie; nieuwe expliciete keuzes blijven beschermd.

De behouden kernregel is een juiste bewijshiërarchie: actuele native `aquarea`-actie voor de optionele DHW-guard, algemene taakinfo apart voor diagnostiek/leren, oudere `panasonic_cc` AUTO conservatief, werkelijk ontbrekende klimaatdata beschermd en alleen bewezen koeling in de koeltimer. Behoud alle ACK-, manual hold-, eigendoms-, hygiëne-, AEG-, prioriteits-, temperatuur- en Wallboxgrenzen. Maak geen nieuw 55 °C-tussenprofiel of automatisch force-commando.

Gebruik uitsluitend aangetoonde software-/publicatieresultaten in `TESTRESULTATEN_BETA51.md`. In deze werksessie zijn browserproeven en live HA-/hardwareacceptatie niet uitgevoerd. Geen fysieke proefopdracht of leerreset gebruiken om een diagnoseveld te vullen; installatie-/opwarmbewijs blijft afzonderlijk.
