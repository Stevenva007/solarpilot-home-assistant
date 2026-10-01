# Changelog

## 1.0.0-beta.37 — 2026-10-01

- Dashboard en configuratie hernoemd in gewone taal: Alleen bekijken, Automatisch regelen, Toestellen, Warmte & comfort, Auto & batterij, Voorrang en Export.
- Centrale voorrangslijst is nu de eenduidige dagelijkse bron voor flexibele zonne-energie. De bestaande beta.36-volgorde blijft behouden; nieuwe gewone toestellen komen standaard onderaan en kunnen daarna hoger/lager worden gezet.
- Wallbox-regel verduidelijkt én runtime gelijkgetrokken met de zichtbare lijst: alleen een toestel bóven Auto laden (Wallbox) én met expliciete toestemming mag tijdens een bevestigde Full Solar-sessie zonnevermogen van de auto benutten. Onder de Wallbox blijft de toestemming opgeslagen maar inactief.
- Afgesproken volgorde blijft beschermd: noodzakelijk warmtepompcomfort boven flexibele lasten; AEG-afwasmachine vóór Wallbox; Wallbox vóór ontvochtiger; extra warm water tot 60 °C als lagere luxe-zonbuffer.
- Duplicerende oude Wallbox-prioriteitsweergave verdwijnt zodra de centrale lijst actief is. Per rij staat in begrijpelijke taal of Wallbox-zonnevermogen mag worden gebruikt.
- Export vereenvoudigd tot één hoofdactie voor een compleet analysebestand voor periodieke controle in ChatGPT; standaard zeven dagen en gepseudonimiseerde namen.
- Eénmalig beta.37-startprofiel activeert beschikbare analyse-, planner- en leermodules. Bronafhankelijke fase-, Wallbox-, klimaat- en DHW-regels worden alleen geactiveerd als de vereiste bestaande koppelingen en bevestigingen aanwezig zijn.
- Leren & vragen schakelt naar gemeten sampling, begrensde automatische adaptatie en Home Assistant-meldingen. De eenmalige migratie stuurt niet meteen een notificatie en overschrijft latere gebruikerskeuzes niet.
- Analyse kan live aan/uit zonder volledige integratieherlading; logregistratie volgt die instelling direct.
- Nieuwe fysieke toestelrechten, ontbrekende entiteiten, DHW-veiligheidsbevestiging en batterij-eigenaarschap worden nooit automatisch verzonnen of toegekend.
- GitHub-validatie is beperkt tot `main`, pull requests naar `main` en handmatige starts. Werkbranch-pushes, tags en de vroegere dagelijkse schedule starten geen extra Validate-run meer. Overlappende runs op dezelfde ref worden automatisch geannuleerd. Na één volledig groene `main`-validatie maakt dezelfde workflow alleen bij een nieuwe manifestversie de ontbrekende tag en GitHub-prerelease; de aparte Release-workflow is alleen nog een handmatige noodroute. Daardoor verdwijnen de vroegere dubbele Validate/Release-runs grotendeels.

## 1.0.0-beta.36 — 2026-10-01

- Basislastleren scheidt duidelijke Panasonic-ruimteverwarming, -koeling, tapwater en sterilisatie van gewone huishoudlast. Zonder aparte W-meter wordt alleen uit stabiele P1+PV-start/stops een begrensde planningsschatting geleerd; realtime elektrische ruimte blijft uitsluitend op echte metingen gebaseerd.
- Wallbox-sessieherkenning uitgebreid: ingestelde modus, effectieve sessie, laadvermogen en actuele terugnametoestemming zijn afzonderlijk zichtbaar. Een kandidaat-sessiesensor wordt alleen voorgesteld bij voldoende bewijs op hetzelfde Wallbox-apparaat; er wordt nooit een entity_id verzonnen.
- Centrale prioriteitenlijst wordt bij beta.35 → beta.36 automatisch leidend met behoud van de bestaande effectieve volgorde. Beschermd: elektrische/fabrikantbeveiliging en legionella, noodzakelijk warmwatercomfort en noodzakelijk ruimtecomfort. Flexibele standaardvolgorde blijft Wallbox → ontvochtiger → extra boilerwarmte 60 °C. Wallbox-rang en per-toesteltoestemming om laadvermogen terug te nemen zijn afzonderlijke instellingen.
- Ontvochtiger en andere binaire lasten krijgen geen dubbele turn_on wanneer alleen hun geleerde/planningsvermogen wijzigt. Bestaande minimumlooptijden en anti-pendelregels blijven gelden.
- DHW gebruikt één persistente configuratiebron. De afgesproken 50 °C normaal, 46 °C bewaakte comfortgrens, -5 °C Panasonic-differentie, 50 °C zonnebuffer, 60 °C extra PV-buffer, 50 °C maximum bij actieve koeling en Panasonic 62 °C-sterilisatie blijven behouden. Configuratie, inschakeling, veiligheidsbevestiging, regeltoestemming, SolarPilot-doelbezit, Panasonic-autonomie en handmatige override zijn afzonderlijk zichtbaar.
- Klimaatbetrouwbaarheid opgesplitst in passieve temperatuurverandering, zonnewinst, verwarmingsrespons, koelrespons, reactievertraging, weerscorrectie en coast/off-feedback. Ontbrekende onderdelen worden als Nog niet geleerd/Eerste metingen/Voorlopig getoond en kunnen geen 100%-vertrouwen veroorzaken.
- PV-kalibratie behoudt minimum vijf geldige dagen, 13.800 Wp, 10.000 W omvormerlimiet, lokale schaduwdetectie en realtime-PV als waarheid. Diagnostiek toont voortaan ook bias en fout per ochtend/middag/namiddag.
- Faseherkenning onderscheidt geleerd, voldoende betrouwbaar, gebruikt voor advies en werkelijk vrijgegeven voor regeling; de expliciete regelvrijgave blijft vereist.
- Analyse-export schema 2 toont aangevraagde periode, beschikbare ruwe periode, werkelijk gedekte meettijd, dekking, eerste/laatste bruikbare meting, herstarts, offline/gat-tijd en fast telemetry. Bootstrapdata, live leerdata, berekende profielen en actuele metingen worden afzonderlijk benoemd; planberekeningen zijn geen leerdagen.
- Kwaliteitspagina herwerkt naar begrijpelijke secties Metingen, Zonnevoorspelling, Huishoudelijk verbruik, Toestellen, Klimaat en concrete aanbevolen acties; geen losse misleidende totaalscore bovenaan.
- Bestaande AEG-afwasmachinebeveiligingen blijven behouden: kort End Of Cycle event-driven opslaan, Off/Unavailable/Disconnected niet als bewezen einde, AirDry niet als einde, exact Remote Control Enabled voor start en maximaal één start per aanvraag.
- Migratie bewaart gekoppelde entiteiten, prijzen, Wallboxinstellingen, apparaten, leerdata, fase/PV/klimaat/boilerdata, bevestigingen en prioriteitsvolgorde. Incompatibele warmtepompleerdata reset alleen dat model.

## 1.0.0-beta.35 — 2026-09-30

- Cumulatief op de aangeleverde beta.34, zonder automatische herordening of reset van instellingen/leerdata.
- Nieuwe centrale tab Voorrang, stabiele editor met slepen en toetsenbord-/mobielvriendelijke pijlen, per-toesteltoestemming om autoladen te verminderen, expliciete bevestiging en conflictcontrole.
- Bestaande regeling blijft leidend tot een echte centrale wijziging. Daarna volgen realtime toestelallocatie, planner, Wallbox-relaties en afwas-afbouw dezelfde gekozen rangorde.
- Comfort, hygiëne, minimale looptijden en gestarte programma's blijven beschermd. Extra boilerwarmte is sorteerbaar tussen lagere lasten maar blijft na Wallbox en voorkeur-afwas; geen EV-vermogen voor die buffer.
- Nieuwe verbruikers komen automatisch in de lijst zonder nieuwe startrechten. Oude numerieke/globale controles kunnen een actieve centrale lijst niet overschrijven.
- Eén Export-pagina met bestaande privacy-/tijdsvensterkeuze en uitgebreid compleet analysebestand; geen upload en geen vervanging van een back-up.
- Negen tabbladen, duidelijkere verwijzingen, actuele volledige uitleg en veldhulp in dezelfde release. Native instellingen tijdens Zonnestroom, APP-/deadlinegedrag, PV-correctie en fabrikantsturing blijven behouden.
- Software- en browsertests gebruiken lokale testdubbels/voorbeelddata. Geen fysieke installatie, GitHub-publicatie of HACS-release uitgevoerd.

## 1.0.0-beta.34 — 2026-09-30

- Cumulatief op de rechtstreeks aangeleverde beta.33; alle bestaande PV-, Wallbox-, AEG- en warmwaterregels behouden.
- Configuratie toegankelijk in Zonnestroom; finale bevestiging met live/deferred overzicht. Gewone opties zonder volledige herlading, zelfde runtime, timers en statuslisteners.
- Gevoelige wijzigingen per toestel opgeslagen tot veilige vrijgave; effectieve oude koppelingen blijven ook na herstart leidend. Voorstellen individueel annuleerbaar.
- Deadline/nettoestemming: expliciete keuze huidige APP-aanvraag of alleen volgende beurten; geplande dag en eenmalige toestemming behouden.
- Toestellen beheren: toevoegen, instellingen, koppelingen, planning, historie en vervangen. Categorie en technische adapter afzonderlijk.
- Vervangen krijgt nieuw ID, geen oude koppelingen, meetprofielen, APP-vrijgave of automatische deelname. Oud profiel gearchiveerd; bestaande bewaartermijn blijft gelden.
- Native virtuele entiteiten dynamisch toevoegen/verwijderen zonder bronapparaten te wijzigen; archiefhistorie en analyse-export uitgebreid.
- Optimistische samenvoeging, bronduplicaat- en opslagfoutcontroles; vraagtekens en één actuele release-uitleg bijgewerkt.
- Geen nieuwe generieke merkintegratie voor wasmachine/droogkast; geen wijziging van de fysieke installatie of publicatie uitgevoerd.

## 1.0.0-beta.33 — 2026-09-29

- Cumulatief bovenop beta.32: instelbare automatische EV-zonneverdeling voor geschikte voorrangsverbruikers, met behouden compressor-minimumtijden.
- Effectieve Wallbox-sessie naast ingestelde Full Solar; manueel/onbekend laden geeft geen EV-credit. Optionele 60 °C terugval; gewoon Panasonic-comfort en sterilisatie blijven beschermd.
- Forecast.Solar-registerdetectie en guarded lokale coordinatoradapter, geen nieuwe HTTP-oproepen. Eén primaire PV-configuratie, expliciete fallbackbronnen.
- Robuuste 15-minutenkalibratie per zonnestand/seizoen, 13,8 kWp/10 kW-clippingbewaking, startup/cloud/outlierfilters, gradual bounded multi-day learning en persistente modelversie.
- Ruwe/gecorrigeerde horizon, kWh-integratie, 14 sensoren, admin PV-diagnose met grafiek/dagtabel en bevestigde PV-only reset; analyse-export uitgebreid.
- Opgeruimde Planning-samenvatting, Onderzoek & instellingen en nieuwe concrete leervragen; geen modals sluiten bij telemetrie.
- AEG APP/13:00/next-day en event-einde, prioriteiten, 50/46-DHW zonder52-herstel en bestaande leerdata blijven behouden. Geen nieuwe fasegewijze afwasoptimalisatie zonder Shelly.
- Zie docs/BETA33_INSTELLEN.md voor migratie, sessiebron en beperkingen; tests staan in het bijgevoegde testverslag.

## 1.0.0-beta.32 — afwasmachinevoorrang onder warmtepompcomfort

- Standaard voorkeursprofiel: gewone warmwater-/vloerregeling en noodzakelijke avondvoorraad eerst; daarna AEG-afwas vóór Wallbox, ontvochtiger en extra 60 °C.
- Afzonderlijke beschermde zonnestart met bestaand EV-zonnevermogen, zonder Wallbox-opdrachten of uitbreiding van elektrische ruimte. Nieuwe actieve status en netto balans worden gecontroleerd; geen afwas-rollback. Tijdelijke netafname mogelijk.
- Alleen benodigde lagere, eigen, gemeten lasten na stabiliteit vrijgeven; compressor-minimumlooptijd en verse bevestiging/P1 blijven vereist.
- Klaar voor morgen reserveert vandaag niets. Deadline verandert geen comfort- of elektrische grens.
- Zonder Shelly conservatieve nominale reservering; volledige faseprofielplanning blijft expliciet voor de latere Shelly-update.
- Vraagtekens, voorrangskaart, analysevelden, herstelmelding en actuele uitleg in dezelfde release.
- Bestaande AEG-profielen krijgen de twee voorkeurskeuzes standaard aan; bestaande Auto/Uitgesloten, mapping en fysieke APP-vrijgave blijven ongewijzigd. Keuzes kunnen uit.

## 1.0.0-beta.31 — APP-start, volgende dag standaard en betrouwbare eindeherkenning

- Nieuw AEG-profiel: fysieke Delay Start/APP-vrijgave, exact Enabled; geen native timer of extra klaarzetknop.
- Vóór 13:00 vandaag; op/na 13:00 standaard volgende kalenderdag. Instelbaar alternatief dezelfde dag.
- Uiterlijk 13:00 op de geplande dag met expliciete nettoestemming; nooit elektrische limieten of apparaatvoorwaarden omzeilen.
- Vast schema over herstart; één belading maximaal één START; geen retry van onzekere opdrachten.
- Kort End Of Cycle direct vastleggen en onthouden, ook na Off/Disconnected/herstart. AirDry blijft nadrogen.
- Aparte Cycle phase-meting en AEG-technische alarmvlagcontrole, geen oordeel op enkel Alerts-teller.
- APP-plan/eindstatus zichtbaar in kaart, uitleg bij elke nieuwe optie en volledige analyse-export.
- Cumulatief: behoudt beta.30 leren/vragen, beta.29 analyse-export en alle bestaande warmwater-/Wallbox-/historiefuncties.
- Bestaande fysieke rechten en handmatige AEG-profielen worden niet stilzwijgend aangepast.

## 1.0.0-beta.30 — Leren, toetsen en gerichte vragen

- Nieuw: Leren & vragen-popup met echte meetbasis voor alle bestaande modellen, gerichte keuzes, antwoordgeschiedenis, optionele HA-meldingen en admin-only API.
- Restverbruik leren tijdens Wallbox/eigen lasten waar actuele, aparte meters een betrouwbare balans geven; geen schattingen, hiaten of dubbele meters als leerwaarheid. Afwijzingsredenen en beschermde boilercontext apart geregistreerd.
- Recente basislastvariant in de achtergrond vergelijken op latere dagen; uitsluitend na jouw toestemming en aantoonbare verbetering binnen ±25% toepassen. Bij slechter bewijs terug naar gewoon profiel. Geen versoepeling van fysieke regels.
- Eerlijke labels: basislastvertrouwen is geen totaal huisvertrouwen. Aparte daglicht-PV-fout, bias, kalenderdagen en nieuwe meetdekking; geen reconstructie van oude dekking.
- Inclusief modellen, vragen en antwoorden in bestaande analyse-export; begrensd lokaal, geen automatische upload.
- Geen nieuwe AEG APP-start-/deadline-logica in deze release; bestaande beta.29 adapter behouden. Alle boiler-/Wallbox- en eerder vrijgegeven functies cumulatief behouden.

## 1.0.0-beta.29 — AEG-start en volledige analyse-export

- Toegevoegd: afzonderlijk AEG/Electrolux-start-only profiel met echte START-knop, gereedmelding, verbinding, remote-start, deur en geselecteerd programma.
- Per geladen afwasbeurt een bevestigde eenmalige klaarzettoestemming; pas native START bij actuele zonne-/plannervoorwaarden. Nieuwe koppelingen blijven Uitgesloten.
- Geen plugrelais, STOPRESET, PAUSE of RESUME. Een lopende cyclus blijft beschermd bij netafname, Pauze, uitsluiting en Wallbox-voorrang. Geen blinde herhaalstart na een onzekere opdracht/herstart.
- Voorbereid op exclusieve Shelly W/kW-meting; complete cyclus-/faseprofielen per programma, onbemeten fasen blijven onbekend. Oude geschatte fasen worden niet als echte meting geïmporteerd.
- Toegevoegd: admin Analyse-export-popup (JSON, 1h/24h/7d) met alle module-instellingen, bronwaarden/attributen/versheid, modellen, beslissingen, eigen foutlogs, verbruikershistorie, energiekosten en beschikbare tijdreeksen.
- Lokale begrensde registratie, configureerbaar; namen standaard gepseudonimiseerd, gevoelige velden gefilterd, geen automatische upload. Exportopbouw buiten de event loop. Private exports worden door public-preflight geweigerd.
- Nieuwe configuratieopties hebben release-gebonden vraagtekenuitleg. Bestaande beta.28-warmwatersturing en eerdere cumulatieve functies blijven behouden.
- Geen live HA- of GitHub-wijzigingen door het pakket; zie docs/AFWASMACHINE_EN_ANALYSE.md voor activering en testgrenzen.

## 1.0.0-beta.28 — 2026-09-28

- Onafhankelijk normaal boilerdoel (nieuw 50 °C) en bewaakte comfortgrens (nieuw 46 °C). Geen afgeleide tijdelijke verhoging om de Panasonic-differentie te omzeilen.
- Ochtendcontrole herstelt uitsluitend het normale doel; oude ochtend-/noodboost-latches worden niet afgespeeld. Geen Force DHW of mode-/compressoropdrachten.
- Expliciete waarschuwing: 50 °C met -5 °C differentie laat nominale herstart rond 45 °C toe. Geen minimumtemperatuur- of hygiënegarantie.
- Begrensde avondvoorraad uit echt beschikbare zon: één berekende reserve per dag, geen opkruipend setpoint om starten af te dwingen, behoud voltooiing na herstart.
- Extra zonne-opwarming wacht standaard bij bezige/onbekende ruimteklimaatactie en 30 minuten tussen extra verhogingen. Normale doelherstelling en beschermende verlaging blijven beschikbaar.
- Bestaande normale doelen, bronnen, rechten en leerdata blijven behouden via expliciete migratie; 50/46-profiel bewust kiezen bij bestaande installaties.
- Dashboard, actuele uitleg, optie-vraagtekens, native beschrijvingen en instelhandleiding tegelijk bijgewerkt. Nieuwe software- en browserregressies.

## 1.0.0-beta.27 — 2026-09-28

- Release-bound Nederlandse optie-uitleg voor alle wizardvelden en directe klimaat/planner/boileropties, onafhankelijke toegankelijke hulpdialogen en native HA-beschrijvingen.
- Geïntegreerde configuratiewizard gebruikt HA's bestaande admin-only optiesflow; bewaarde velden en hulp overleven live dashboardupdates.
- Alleen-lezen Wallbox-laadprofiel met same-device herkenning, expliciete fasebron of handmatige 1-/3-fasenkeuze, huidige25-A-terugval, bronactualiteit en ICP-uitsluiting.
- Optionele nachtrust tot stabiele zon, gemeten ochtenddoel45 °C om09:00 en beperkte avondvoorraad uit laatste bruikbare zon. Begrensd tankleren en expliciete aannames; geen temperatuurgarantie.
- Gewoon warmtepompcomfort vóór autonoom EV-laden; extra60 °C uitsluitend echt residuale injectie. Geen opdrachten naar Wallbox.
- Koeluitloop aanbevolen30 minuten en optionele voorspellende koelblokkering met bestaande thermische/weerdata. Nacht-/ochtend- en fabrikantbeveiligingen blijven gescheiden.
- Standaard zonne-stabiliteit300/300 seconden; bestaande opgeslagen wachttijden blijven behouden.
- Stabiel DHW-eigenaarschap blokkeert ruimteklimaat niet permanent; pending/fout-/hygiënebescherming blijft.
- Vaste testklok voor twee bestaande DHW-tests voorkomt afhankelijkheid van een echte maandagse hygiëneperiode. Nieuwe regres­sietests voor koude start, hele-gradenmetingen, DST, bescherming, EV-prioriteit, profielbronnen en UI.


## 1.0.0-beta.26 — Mobiele navigatie, manuele bediening, automatische herstartreconciliatie en 20% batterijverlies

- Mobiel SolarPilot-dashboard krijgt een eigen menuknop die het normale Home Assistant-zijmenu opent; desktopnavigatie blijft ongewijzigd.
- Verbruikers tonen fysiek AAN, SolarPilot-eigenaarschap, externe activiteit, werkelijk gemeten verbruik en manuele toestand visueel duidelijker.
- Nieuwe expliciete **Manueel starten**- en **Manueel stoppen/vrijgeven**-acties met bevestiging. Manuele start mag binnen de softwaregrenzen netstroom gebruiken; minimumrust, minimumlooptijd, vrijgave, fouten en overige beveiligingen blijven gelden.
- Na een Home Assistant/SolarPilot-herstart worden bekende echte AAN/UIT-toestanden automatisch gereconcilieerd. Een eerder door SolarPilot beheerd toestel hoeft niet eerst uit; de opgeslagen modus kan daarna automatisch hervatten zonder oude opdrachten te herhalen. Alleen onbeschikbare/onzekere status blijft handmatige controle vragen.
- Voor deze installatie is het voorlopige eenfasige Full Solar-minimum voor Wallbox-voorrang standaard **1380 W**; de waarde blijft instelbaar.
- Batterij-what-if gebruikt standaard **80% round-trip efficiëntie = 20% totaal batterij-/omvormerverlies**. Live simulatie verwerkt dit fysiek over laad- en ontlaadpad; historische bootstrapresultaten worden conservatief naar dezelfde efficiëntie omgerekend wanneer hun bronaanname afwijkt.
- Cumulatief bovenop beta.25; beta.22–beta.25 hoeven niet afzonderlijk gepubliceerd of geïnstalleerd te worden.

## 1.0.0-beta.25 — Dagoverzicht en sessiehistoriek per verbruiker

- Nieuwe Dagoverzicht-knop per verbruiker: totale ingeschakelde/actieve tijd per dag, 7/30-dagenkeuze, tijdlijn en sessies met start- en stopredenen.
- Alleen bevestigde statusovergangen worden starts/stops; externe bediening en onbekende beginsituaties worden duidelijk onderscheiden. Herstarts, meetgaten en gemiste bevestigingen leveren geen verzonnen draaitijd of stop op.
- Lokale, begrensde opslag met dagopsplitsing rond middernacht en zomer-/wintertijd. Behoud bij gewone updates; eigen historieopslag wordt bij definitieve verwijdering meegenomen.
- Authentieke alleen-lezen Home Assistant-WebSocket-query met controle van leesrechten, alleen voor het gekozen toestel en de gekozen dag. Ondersteunt de schema-engine van zowel oudere als nieuwere HA-WebSocket-API's.
- De aparte popup behoudt DOM, datum, scroll en open details tijdens vijfsecondenupdates. Volledige sessies staan niet in de gewone statusattributen en worden alleen opgevraagd zolang nodig.
- Nieuwe model-, runtime-, permissie- en browsercontroles; complete actuele uitleg in Home Assistant en documentatie bijgewerkt. Geen versoepeling van veiligheids- of schakelregels.
- Cumulatief: bevat ook beta.22–beta.24; tussenliggende publicaties/installaties zijn niet nodig.

## 1.0.0-beta.24 — dagkosten en Wallbox-voorrang per verbruiker

- Cumulatief: bevat de batterij-starttimingfix van beta.22 en stabiele uitklappers/browserrefresh van beta.23.
- Behoud van de bestaande netto planningskost met zichtbare import/export/PV-uitsplitsing; aparte dagkost uit gemeten P1/PV, meetdekking, prijswijzigingen en herstartbehoud.
- Voorkeur per verbruiker: globale keuze volgen / dit toestel eerst / Wallbox eerst met gebruik van klein overschot.
- Wallbox blijft alleen-lezen. Minimum zonnelaadvermogen expliciet bevestigen; laadvraag, hysterese, veilige compressorvrijgave, begrensde startwachttijd en terugval zonder herhaaljagen.
- Leeg dagdoel blokkeert geen realtime flexlast meer via forecastuitstel.
- Nieuwe regressietests; actuele uitleg in Home Assistant en documentatie bijgewerkt.

## 1.0.0-beta.23 — Rustige live-interface en cumulatieve update

- Bevat alle fixes uit beta.22; beta.22 hoeft niet afzonderlijk geïnstalleerd of gepubliceerd te worden wanneer rechtstreeks vanaf beta.21 naar beta.23 wordt bijgewerkt.
- Bewaart opengeklapte dashboardsecties tijdens live SolarPilot-updates, zodat details niet meer om de vijf seconden dichtklappen.
- Verwijdert de fade-animatie bij gewone telemetrie-updates; tabwissels en bediening blijven direct reageren zonder zichtbare volledige kaartrefresh.
- De Uitleg-tab slaat een herbouw over wanneer alleen niet-zichtbare realtime meetwaarden veranderen.
- De 5-seconden regelcyclus en veiligheidslogica blijven ongewijzigd; deze release optimaliseert vooral de browserweergave en verandert geen toestelbeslissingen.

## 1.0.0-beta.22 — Deterministische batterij-opstarttiming

- Herstelt een platformafhankelijke timingfout waarbij de allereerste toekomstige batterijopdracht op een pas opgestarte Linux/GitHub-runner ten onrechte door het minimuminterval kon worden geblokkeerd.
- Een verse batterij-runtime gebruikt nu expliciet 'nog geen eerdere opdracht' in plaats van monotone tijd 0 als impliciete vorige opdracht.
- Het minimuminterval blijft ongewijzigd gelden na een echte batterijopdracht en na een herstart/reconciliatie.
- Voegt een regressietest toe die een host met slechts 5 seconden monotone uptime simuleert.
- Geen wijziging aan de huidige ontvochtiger-, Wallbox-, boiler- of klimaatregeling.

## 1.0.0-beta.21 — Runtime-fix na eerste flexlast

- Herstelt een `NameError` in het toesteloverzicht (`i` → toestel-ID) waardoor de hoofdstatussensor en daardoor de SolarPilot-config entry konden mislukken zodra een flexlast was toegevoegd.
- Voegt een regressietest toe zodat een toesteloverzicht met cyclusprofiel niet opnieuw op deze fout kan stuklopen.
- Corrigeert Home Assistant-statistiekmetadata voor energie-entiteiten: dagzonne-energie gebruikt `total_increasing`; de batterij-what-if energie gebruikt `total`.
- Verplaatst lezen/verwijderen van de privébundel en historische bootstrap uit de Home Assistant event loop naar executor-werk, zodat de `read_text` blocking-call waarschuwing verdwijnt.
- Werking en veiligheidslogica blijven verder ongewijzigd; bestaande configuratie, privébundel, leerdata en toegevoegde verbruikers blijven behouden.

## 1.0.0-beta.20 — Public HACS/GitHub release

- Publieke HACS-build opgeschoond: geen woning- of installatie-specifieke entity-ID's meer in first-install defaults.
- Eerste installatie laat de gebruiker net/PV en overige bronentiteiten expliciet kiezen; alleen universele `sun.sun` mag veilig worden voorgesteld.
- `hacs.json` rendert de README expliciet in HACS.
- GitHub-validatie uitgebreid met HACS Action, Home Assistant hassfest, syntax-, documentatie- en privacy/preflightchecks.
- Releasehulpmiddelen aangepast aan de ingebouwde frontend onder `custom_components/solar_pilot/frontend`.
- Zowel de rootdocumentatie als de in Home Assistant meegeleverde actuele uitleg worden voortaan uit dezelfde bron gegenereerd en gecontroleerd.
- Python/test-cachebestanden worden niet meer in de publicatie-ZIP opgenomen.
- Windows-publicatiescript toegevoegd voor GitHub CLI, met preflight vóór de push en zonder automatische release vóór CI groen is.

## 1.0.0-beta.18 — HACS-ready

- HACS wordt de aanbevolen installatie- en updatemethode.
- Repositorystructuur voldoet aan HACS-integratievereisten: één integratie onder `custom_components/solar_pilot`.
- `hacs.json`, HACS-validatie-workflow en tag-release-workflow toegevoegd.
- Brand-assets toegevoegd voor Home Assistant/HACS.
- Frontend blijft ingebouwd in dezelfde integratie; geen aparte Lovelace-resource nodig.
- Configuratie en leerdata blijven in Home Assistant opgeslagen en worden niet door HACS-updates vervangen.
- Veilige verwijderprocedure behouden: eerst `Verwijderen voorbereiden`, daarna config-entry verwijderen en vervolgens HACS-uninstall.
- Custom-integrationvertalingen komen uit `translations/`; verouderde `strings.json` is uit het HACS-pakket verwijderd.
- Publicatiehulpmiddel toegevoegd om GitHub owner/repository éénmalig in manifest en README in te vullen.
