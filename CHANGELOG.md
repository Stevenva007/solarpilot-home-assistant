# Changelog

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
