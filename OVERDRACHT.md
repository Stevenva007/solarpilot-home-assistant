<!-- solarpilot-handoff-schema: 1 -->
<!-- solarpilot-handoff-version: 1.0.0-beta.46 -->

# OVERDRACHT — SolarPilot

Laatst bijgewerkt: **3 oktober 2026**
Actuele ontwikkelde bron: **v1.0.0-beta.46**, op de bestaande beta.45-hoofdbranch `9cddb043f4e6b1547eaa9487e057692ffb1d1a5b`. Deze release corrigeert de onnodige extra-DHW-blokkering door algemene taak-/AUTO-informatie bij betrouwbare native `aquarea`-actie `idle/off`. De definitieve softwaregate behaalt **1813 geslaagde Python-tests in 6.79 s**; uitleg-hash **`787cd40eaad0b73a`**, **432 optieshulpvelden** en alle lokale release-/syntaxcontroles zijn groen. Publicatiecontrole staat bij de beta.46-release en Validate-workflow op GitHub; zie `docs/TESTRESULTATEN_BETA46.md`. De vóór deze werksessie bevestigde installatie is beta.45; beta.46 is hier niet live geïnstalleerd of fysiek getest. Dit dossier beschrijft uitsluitend de actuele werking; releasehistoriek staat in `CHANGELOG.md`, Git en oudere releasedocumenten.

## 1. Projectdoel in gewone taal

SolarPilot verdeelt zonnestroom tussen autonoom autoladen, warmtepomp/tapwater en flexibele verbruikers. Het verbindt actuele P1/PV, fasebelasting, voorspellingen, kosten, lokaal leren en planning in één Home Assistant-regeling met begrijpelijke bediening en controleerbare beslisredenen.

## 2. Actuele basis

De absolute codebasis is de bestaande beta.45-hoofdbranch op commit `9cddb043f4e6b1547eaa9487e057692ffb1d1a5b`. De laatst vóór deze werksessie gecontroleerde gepubliceerde en geladen release is [beta.45](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.45), onveranderlijke tag op commit `507f74183f51b3517b077d05a455e4f169824f69`. Gebruik deze release of een gecontroleerde volledige back-up voor rollback.

Beta.46 verandert de voorrang tussen klimaatbewijs en algemene taakinfo voor de optionele warmwaterbuffer. De exact geregistreerde native `aquarea`-klimaatactie is leidend wanneer zij actueel en betrouwbaar is. De oudere `panasonic_cc`-AUTO-ambiguïteit blijft beschermd. De beta.45-vertraagde tankdoelbevestiging blijft intact: exact `aquarea`/`panasonic_cc`, minstens tien seconden en een passende nieuwe HA-rapportage; geen onmiddellijke optimistische echo. Een eerdere ACK of geladen versienummer bewijst geen nieuwe latere ACK of fysieke opwarming.

In deze werksessie is geen live Home Assistant-toegang. Softwaregate, GitHub-publicatie, pakketten, HACS-bestanden, geladen backend/kaart, doelbevestiging en fysieke opwarming zijn afzonderlijke bewijslagen. Bestaande gebruikersinstellingen, leerdata, toestellen en prioriteiten blijven behouden.

## 3. Absolute ontwerpregels die niet stilzwijgend mogen wijzigen

- Behoud werkende functies, gebruikersinstellingen, leerdata en bestaande koppelingen. Veilige eenduidige migraties mogen geen nieuwe fysieke opdracht geven.
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
- Handmatig of extern OFF gezette klimaatzones zijn geen SolarPilot-eigendom. Gewone AUTO/herstel/verwijderen mag alleen eigen coast-zones vrijgeven; een harde comfortgrens mag uitsluitend de werkelijk overschrijdende zone naar AUTO zetten.
- DHW-hysterese mag alleen een bewezen door SolarPilot uitgegeven en teruggemeld hoog doel vasthouden. Handmatige/fabrikantbediening blijft leidend; echte netafname of koeling mag luxe-doelen niet kunstmatig vasthouden.
- Realtime P1/PV en fysieke grenzen gaan altijd vóór forecast en aangeleerde schattingen. Ontbrekende data is niet nul.
- Geen geheimen, ruwe privédata, adressen of private installatie-identiteiten in publieke bron, pakketten of dit dossier.
- Codewijziging betekent dezelfde release ook tests, changelog, actuele gebruikersuitleg, installatie/upgrade, rollback, pakket en dit dossier bijwerken.

## 4. Actuele werking

### Bediening en uitleg

Dagelijkse modi: **Alleen bekijken**, **Automatisch regelen**, **Pauze**. Dashboardgroepen: Overzicht, Voorrang, Toestellen, Warmte & comfort, Planning, Energie, Batterij, Export en Uitleg. Het configuratiecentrum bevat ook **Auto & batterij**. `current_guide.py` is de enige actuele gebruikersuitlegbron; dezelfde tekst staat in Home Assistant en beide `ACTUELE_WERKING.md`-bestanden. Opties hebben releasegebonden hulp. Browser Terug/Vooruit herstelt SolarPilot-schermen en beschermt onopgeslagen formulieren zonder acties te herhalen.

### Centrale voorrang en toestellen

De verticale lijst bevat vaste beschermde regels en verplaatsbare flexibele toestellen, Auto laden en extra warm water. De positie bepaalt de echte volgorde. Wallbox-toestemming toont bewaarde keuze én effectieve uitkomst. Centrale schema's beschermen de volgorde tegen oude toestelwizardvelden.

De samenvatting per toestel blijft de actuele engine-`result.reason`. De startuitleg toont invoer, benodigd vermogen en effectieve toewijzing na hogere prioriteiten, comfort, lopende cycli en toezeggingen. Ruwe injectie is apart zichtbaar; een complete checklist is geen zelfstandige startgarantie. Minimumlooptijden en beschermde cycli blijven intact. Geschiedenis toont geregistreerde start-/stoptijden, draaitijd en afzonderlijke Startreden/Stopreden; ontbrekende externe oorzaken, meetgaten en oude sessies blijven onbekend.

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

Nieuwe optionele verhogingen vereisen bestaande zonnestabiliteit en rust tussen doelopdrachten (standaard 300 s en 1800 s). Nachtbeperking blokkeert extra buffers maar verlaagt het normale doel niet. Ochtendcontrole en begrensde avondvoorraad zijn apart opt-in en gebruiken voorzichtig tankleren; het gewone doel wordt niet hoger om een native start af te dwingen. Gewoon comfort staat vóór Wallbox. De avondvoorraad mag uitsluitend actuele, expliciet bevestigde Full Solar-lading krediet geven: verbonden, vragend, minstens 50 W, sessie en vermogen maximaal 120 s oud. Extra 60 °C krijgt geen EV-krediet.

Voor extra 60 °C worden huisreserve, batterijontlading, nog niet gebruikte toesteltoezeggingen en een lopende AEG zonder exclusieve meter conservatief afgetrokken. Actuele/gefilterde net- en PV-ruimte begrenzen de toewijzing; kwartierpiek- en fasegrenzen blijven gelden. Een passend startklare AEG krijgt eerst één startkans. Een lopende beurt blokkeert niet categorisch als er na alle reserves genoeg echt overschot blijft.

Doelterugvalhysterese vereist bewezen SolarPilot-eigendom. Echte netafname boven de grens, actieve koeling en onbeheerde/onbevestigde 60 °C slaan gewone terugvalvertraging over. Manual hold, pending opdrachten, fabrikantbeveiliging en hygiëne blijven schrijfguards. De gerichte **Hervat** beëindigt alleen de manual hold, uitsluitend buiten Automatisch regelen en zonder pending opdracht; zij schrijft geen doel en start geen cyclus.

### Klimaat, PV, fasen, kosten en leren

Panasonic blijft eigenaar van HEAT/COOL. Klimaatcoast/herstel bewaakt eigendom per zone en echte comfortoverschrijdingen. Bij onvoldoende modelzekerheid blijft automatisch coast conservatief uit en wordt de ingestelde reactievertraging als fallback getoond. Warmtepompleren blijft gescheiden van gewone huishoudbasislast; modellen leren uitsluitend uit voldoende echte meetdagen/cycli.

PV gebruikt werkelijk geconfigureerd paneelvermogen, omvormerlimiet, lokale schaduw en kalibratie; actuele PV blijft waarheid. Fase- en plannerregels verzinnen geen capaciteit. De planner combineert horizon, deadlines, gemeten of verklaarbaar geschat vermogen en conservatieve cyclusreserves. Ontbrekende duur-/fasemetingen worden niet optimistisch ingevuld.

Kosten tonen netto afname/injectie, directe PV en dag-/horizonwaarden met meetdekking. De aparte automatische-voordeelregistratie bewaart maximaal negentig dagen en is een opportunity-value-schatting, geen bewezen extra besparing die nogmaals van de kosten af mag. Batterijscenario's zijn adviserend; fysieke batterijregeling blijft aparte dubbele opt-in met eigenaarschap. Analyse-export benoemt werkelijke dekking, gaten, bootstrap, live leerdata, modellen en besluiten; export wordt niet automatisch geüpload.

### Wallbox

Een expliciete effectieve-sessiebron onderscheidt zonne-auto laden/wachten, manueel en gestopt; geen hardcoded installatie-entity-id. **Zonne-auto · wacht op auto** wordt standaard herkend. Alleen een exact oude standaardwaardelijst wordt compatibel uitgebreid, nooit een eigen lijst. Native Full Solar en actuele sessievoorwaarden blijven nodig. Een verse geldige lage laadkracht heft reservering alleen op bij expliciet geen laadvraag, geen verbonden auto of bekende inactieve status. Oud/restored/onbekend/strijdig blijft fail-closed.

De read-only historie bewaart maximaal dertig laadperioden. Native stopreden wordt alleen aan een aantoonbaar nieuwe tijdgecorreleerde rapportage gekoppeld; gaten/herstarts/oud bewijs blijven onbekend. Geen start/stop/modus-/stroom-/faseopdracht.

## 5. Configuratie, integraties en belangrijke entiteiten

Generieke bronnen: Home Assistant, P1/HomeWizard, PV/Forecast.Solar, Panasonic Aquarea, Wallbox, flexibele toestellen en toekomstige batterijprofielen. Exacte entity_ids en apparaatidentiteiten altijd uit actuele lokale configuratie lezen en nooit publiek hardcoden.

Voor DHW: tankmeting, native tankdoel, geregistreerde doeladapter, klimaatbronnen, optionele native taakbron, handmatige/fabrikant-hygiënebronnen en eventueel een exclusieve elektrische tank-W-meter. Een gedeelde warmtepompmeter is geen tankmeter. Vertrouwen in `aquarea` vereist exacte registratieherkomst, geen naamheuristiek.

AEG-rollen zijn same-device; optionele cyclephase/starttijd/alarm mogen alleen met passende semantiek gekoppeld worden. Device-id wordt uitsluitend fingerprinted in publieke status. Wallbox: effectieve sessie, native Full Solar, laadvraag/verbinding en vermogen. Bestaande lokale privébundel kan lege werkelijk bestaande koppelingen aanvullen; HACS bewaart `userfiles`.

## 6. Belangrijke ontwerpbeslissingen + waarom

- **Werkelijk bestaande beta.45-bron als basis** voorkomt regressie door een oudere export.
- **Native klimaatactie vóór algemene taakinfo** voorkomt een onnodige DHW-blokkering bij betrouwbaar idle zonder echte koel-/verwarmprioriteit te versoepelen.
- **Exacte adapterherkomst** beperkt vertrouwen tot `aquarea`; oudere `panasonic_cc` AUTO blijft beschermd. Geen algemene claim dat elke Panasonic-adapter dezelfde actiebetrouwbaarheid heeft.
- **Onbekend is geen bewezen koeling** behoudt onmiddellijke bescherming zonder fictief koelverleden en extra wachttijd na bronherstel.
- **Guard en leren afzonderlijk** laat optionele DHW betrouwbaar beslissen zonder PUMP als normale of gemeten compressoractie aan te leren.
- **Latere doelrapportage** sluit optimistische lokale echo uit maar claimt geen onafhankelijke fysieke ACK of opwarming.
- **Eigendom per zone en DHW-doel** beschermt handmatige/fabrikantbediening tegen algemene herstelopdrachten en valse hysterese.
- **Same-device unieke AEG-mapping en APP-latch** voorkomt verkeerde actuatoren en ongewenste starts na upgrade. Begrensde retry vangt late setup op zonder permanente autoconfiguratie.
- **Echte engine-reden en toewijzing** voorkomt dat een UI-checklist een tweede startalgoritme wordt.
- **Afzonderlijke opgeslagen/effectieve toestemming** houdt centrale volgorde begrijpelijk zonder actuatorrechten stil te verruimen.
- **Begrensde leerreset** wist alleen bedoelde afgeleide modellen, geen configuratie, operationele klimaatveiligheid, bootstrap of andere cyclus-/DHW-modellen; reset stuurt geen actuator.

## 7. Automatische processen

- Start/reload reconcilieert bestaande opslag en echte toestanden vóór nieuwe opdrachten; geen dubbele START of doelwrite.
- Migraties behouden prioriteit/configuratie/leerdata; éénmalige veilige analyse-activering overschrijft latere gebruikerskeuzes niet.
- Legacy-AEG-herstel/reparatie blijft idempotent, gemarkeerd en beperkt; post-start listeners stoppen na succes/timeout/unload.
- De actuele regelcyclus bewaakt bronversheid, klimaat-/koelbewijs, eigendom, pending ACK, hygiëne, reserves, minimumlooptijden en elektrische ruimte.
- Native taakdata wordt alleen gelezen. Optionele DHW-vrijgave verandert de ruwe taak-/leerinformatie niet.
- Voor exact herkende doeladapters vereist ACK een passende latere HA-rapportage na minstens tien seconden. Timeout en manual hold geven geen blinde retry of automatisch hervatten.
- Historiek, modellen, afwasaanvragen, koeltijd en planner blijven lokaal/persistent met bestaande begrensde bewaartermijnen. Geen automatische export-upload.

## 8. Geheimenbeleid

Nooit wachtwoorden, tokens, API-sleutels, private keys, exacte adressen, ruwe privé-analyses of private device-identiteiten in Git/release/OVERDRACHT. Lokale privébundels en HA-back-ups blijven buiten publieke bron/pakketten. Publieke preflight moet groen zijn vóór publicatie.

## 9. Testprocedure + actuele teststatus

De definitieve volledige samengestelde beta.46-suite is groen met **1813 geslaagde Python-tests in 6.79 s**. De bestaande beta.45-basis werd vooraf lokaal gecontroleerd met 1773 tests in 6.69 s; veertig nieuwe gerichte regressies zijn vervolgens opgenomen in de volledige beta.46-suite. Geen afgeleid totaal uit losse suites.

Actuele-uitlegcontrole (hash **`787cd40eaad0b73a`**, **432 optieshulpvelden**), handoff, repositoryvalidatie, publieke preflight, Pythoncompile, beide JavaScript-syntaxcontroles en diffcontrole zijn groen. Gerichte dekking: aquarea-AUTO/HEAT_COOL idle/off tegenover PUMP/oude/ongemapte taak, echte koeling/verwarming, restored/stale/missing klimaat, oudere panasonic_cc-ambiguïteit, koeltimerherstel, bewaarde oude koeltijden, conservatief leren en alle bestaande ACK-/comfort-/AEG-/Wallboxgrenzen. Volledig verslag: `docs/TESTRESULTATEN_BETA46.md`.

In deze omgeving is geen Chromium beschikbaar en de browserdownload leverde een afgebroken ZIP. De veertien historische browserresultaten zijn niet als beta.46-browserresultaat herhaald. JavaScript-syntax en Python-/UI-structuurcontroles zijn wel geslaagd. Er is geen live Home Assistant-toegang; geen fysieke opdrachten, installatie, compressorstart of bereikte tanktemperatuur zijn in deze werksessie bevestigd. Externe publicatie en pakketverificatie worden afzonderlijk bij de onveranderlijke GitHub-release/workflow gecontroleerd.

## 10. Bekende problemen / beperkingen

- Niet live bevestigd dat de taak-/AUTO-blokkering de enige oorzaak van het getoonde warmwaterprobleem is. Andere bestaande geldige wachtredenen kunnen extra warmte nog uitstellen.
- Een actuele native idle/off-actie geeft geen fysieke compressor- of tankenergiegarantie; `PUMP/WATER` meldt slechts een taak.
- Latere HA/cloud-doelrapportage is geen onafhankelijke fysieke ACK. Een nieuwe natuurlijke latere doelbevestiging en tankopwarming blijven installatieacceptatie.
- De oudere `panasonic_cc` AUTO/HEAT_COOL-mapping blijft zonder expliciete actuele taakinfo ambigu.
- Geen Chromium/browsergate uitgevoerd in deze werksessie; geen live klimaat-/koelroute of beta.46-opwarming getest.
- Een 50 °C-doel met -5 °C-differentie kan 46 °C niet garanderen; het profiel is geen hygiënegarantie.
- Zonder exclusieve afwas-/tankmeter blijven vermogen en programmafasen conservatief geschat; geen fictieve gemeten cycli.
- Onvolledige/ambigue AEG-mapping en een bewust onbetrouwbare alarmbron blijven fail-closed. De retry eindigt na tien minuten.
- Lage modelzekerheid is geen toestemming om comfort te versoepelen. Batterijbediening blijft zonder hardware/eigenaarschap adviserend.

## 11. Concrete openstaande ontwikkeling

- Publicatiecontrole staat op GitHub bij de onveranderlijke beta.46-tag/release en Validate-workflow; beide gepubliceerde pakketten moeten tegen de exacte tag worden gecontroleerd.
- Gebruiker installeert beta.46 en controleert geladen backend/kaart en actuele native klimaatactie naast taakdata. In deze werksessie is geen live HA-toegang.
- Observeer een volgende natuurlijke toegestane doelopdracht met passende latere rapportage en werkelijke tankrespons; forceer geen doel, Powerful, APP-aanvraag of START voor bewijs.
- Eventueel de veertien browsercontroles later opnieuw uitvoeren in een omgeving met Chromium.
- Exclusieve Shelly-afwasmeting toevoegen wanneer hardware beschikbaar is; tot dan fasen/energie niet verzinnen.
- Thermische/PV/faseprofielen uit echte meetdagen laten verbeteren; actieve koelroute, fysieke terugval en eventuele ontbrekende cyclus-eindregistratie afzonderlijk controleren.

## 12. Installatie/upgrade en rollback

Zie `START_HIER.md` en `docs/BETA46_INSTELLEN.md`: actuele volledige back-up, beschermde cyclus afwerken, exact beta.46 via HACS/lokaal pakket, volledige HA-herstart, backend én vernieuwde kaart controleren, bron-/reviewcontrole in Alleen bekijken/Pauze en pas daarna gewone regeling hervatten. Bestaande instellingen, leerdata, APP-tickets en `userfiles` blijven behouden. Een bestaande manual hold wordt niet automatisch gewist.

Rollback: **Pauze → beschermde cycli afwerken → onveranderlijke beta.45 of gecontroleerde volledige back-up herstellen → Home Assistant herstart → backend/kaart, eigendom, bronnen en beveiligingen controleren**. Beta.45 behoudt de vertraagde `aquarea`-ACK maar bevat nog de te brede taak-/AUTO-blokkering. Geen STOPRESET vanuit SolarPilot, extra APP-aanvraag, Powerful of Wallbox-opdracht om upgrade/rollback te forceren.

## 13. Belangrijkste bestanden

- `dhw.py`, `dhw_runtime.py`: klimaat-/koel-/doelbeleid, eigendom, veilige terugval en ACK.
- `runtime.py`: bronregistratie/versheid, fysieke commandoroute, DHW-Hervat en begrensde leerreset.
- `heatpump_learning.py`, `thermal_climate.py`, `thermal_runtime.py`: taak-/responsleren en eigendom per klimaatzone.
- `dishwasher.py`, `dishwasher_app.py`, `dishwasher_recovery.py`: native startveiligheid, APP-ticket, deadlines, einde en begrensde recovery.
- `priority_board.py`, `wallbox_policy.py`, `wallbox_activity.py`: centrale voorrang, read-only sessiebeleid en begrensde waarnemingshistoriek.
- `savings.py`, planner/PV/fasemodules: schattingen, dekking en begrensd lokaal leren.
- `current_guide.py`, `option_help.py`, translations en gegenereerde uitleg/help: één releasegebonden gebruikersbeschrijving.
- `tests/`, `tools/check_*.py`, `tools/validate_repository.py`: regressies, consistentie en openbare releasechecks.
- `CHANGELOG.md`, `START_HIER.md`, `docs/BETA46_INSTELLEN.md`, `docs/TESTRESULTATEN_BETA46.md` en dit dossier: huidige release; oudere releasedocumenten blijven historie.

## 14. Release-checklist

1. Actuele handoff lezen en absolute beta.45-basis bevestigen.
2. Manifest, const, current guide en beide frontendversies gelijk aan beta.46 houden.
3. Actuele uitleg/optiehulp genereren en alle relevante lokale gates uitvoeren; werkelijke beperkingen opnemen.
4. Code, changelog, gebruikersuitleg, installatie/rollback, testverslag en OVERDRACHT samen actualiseren.
5. Publieke preflight en diffcontrole groen; geen caches/private data in commit/pakket.
6. Alleen na geslaagde gate naar de bestaande repository uploaden. Nieuwe beta.46-tag/workflow/release; oude tags en assets onveranderd laten.
7. Beide gepubliceerde ZIP's downloaden, inhoud tegen exact tag vergelijken en werkelijke grootte/SHA-256 vastleggen.
8. Publicatie niet gelijkstellen aan HACS-installatie, geladen backend/kaart, ACK of fysieke opwarming.

## 15. AI-handoff

Werk voort op de bestaande beta.45-hoofdbranch `9cddb043f4e6b1547eaa9487e057692ffb1d1a5b` en de hier ontwikkelde beta.46. De gebruiker heeft de herstelling én upload naar de bestaande GitHub-repository na testen uitdrukkelijk gevraagd. Vraag geen herhaalde uploadtoestemming; voltooi eerst de softwaregate en pakket-/documentconsistentie.

De kernregel is een juiste bewijshiërarchie: actuele native `aquarea`-actie voor de optionele DHW-guard, algemene taakinfo apart voor diagnostiek/leren, oudere `panasonic_cc` AUTO conservatief, werkelijk ontbrekende klimaatdata beschermd en alleen bewezen koeling in de koeltimer. Behoud alle ACK-, manual hold-, eigendoms-, hygiëne-, AEG-, prioriteits-, temperatuur- en Wallboxgrenzen. Maak geen nieuw 55 °C-tussenprofiel of automatisch force-commando.

Gebruik uitsluitend aangetoonde software-/publicatieresultaten in `TESTRESULTATEN_BETA46.md`. In deze werksessie zijn browserproeven en live HA-/hardwareacceptatie niet uitgevoerd. Geen fysieke proefopdracht of leerreset gebruiken om een diagnoseveld te vullen; installatie-/opwarmbewijs blijft afzonderlijk.
