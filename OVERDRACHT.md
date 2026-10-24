<!-- solarpilot-handoff-schema: 1 -->
<!-- solarpilot-handoff-version: 1.0.0-beta.106 -->

# OVERDRACHT — SolarPilot

Laatst bijgewerkt: **24 oktober 2026**. Actuele bron: **v1.0.0-beta.106**. Bouwbasis: gepubliceerde beta.105 `e88b209`. Installatie en rollback: `docs/BETA106_INSTELLEN.md`. Softwarebewijs en publicatievoorwaarden: `docs/TESTRESULTATEN_BETA106.md`.

## 1. Projectdoel in gewone taal

SolarPilot verdeelt beschikbare zonnestroom lokaal tussen flexibele toestellen, een beschermde afwasmachine en een optionele SG-zonneboost. De autonoom regelende Wallbox gebruikt standaard het overschot dat overblijft. Panasonic regelt zelfstandig ruimtecomfort, normaal warm water, koeling en sterilisatie. Home Assistant toont actuele activiteit, de reden om te wachten en geregistreerde historie. Modellen en voorspellingen helpen plannen; actuele metingen bepalen wat fysiek mag.

## 2. Actuele basis

Beta.106 verwijdert de vaste Wallbox-vóór-SG-beperking uit backend en editor. De centrale volgorde is ook voor SG leidend. Gegenereerde oude defaults krijgen eenmaal de Wallbox achteraan; een bewust opgeslagen eigen volgorde wordt niet herschreven. Nieuwe gewone toestellen komen vóór een laatst geplaatste Wallbox. De afwasmachine houdt de beschermde plaats vóór SG.

Een extern AAN-contact wordt in Automatisch regelen waargenomen met een oorspronkelijke absolute vijftienminutendeadline. Dit is nog geen SolarPilot-eigendom of bewezen lokale lease. Na afloop volgt uitsluitend bij actuele passende zonne-, net-, koel-, prioriteits- en elektrische voorwaarden een bevestigde korte lokale toestemming, zonder UIT-puls. Anders volgt gerichte vrijgave. Alleen bekijken/Pauze nemen het externe contact niet over. Een fysieke handmatige UIT blijft beschermd.

De canonieke gebruikersuitleg is één declaratieve `current_guide.py`; `docs/ACTUELE_WERKING.md`, de ingebedde mirror en optiehulp worden daaruit gegenereerd. Oude append-/override-lagen zijn samengevoegd. De overige bronisolatie, afwasmeterwaarneming, historie, modellen, onderzoek en export/antwoordcontracten blijven behouden.

## 3. Absolute ontwerpregels

- Panasonic-entiteiten zijn read-only. Alleen de bewust toegewezen bestaande fysieke SG-uitgang heeft een aparte gecontroleerde schrijfroute. Geen tank-/kamertemperatuur-, programma-, AUTO/OFF-, heater-, Powerful-/Force- of tweede-Shelly-besturing toevoegen. Bestaande lokaal ingestelde SG-capaciteiten blijven behouden.
- Wallbox blijft read-only, ook bij uitgeschakelde monitoring en via inspecteerbare indirecte scripts. Een hogere last kan de laadpaal uitsluitend indirect laten terugregelen. Geen laadcommando of verzonnen laadvermogen.
- Alleen met SG vóór Auto laden mag actuele betrouwbare gemeten laadruimte uit een bevestigde autonome zonnelaadsessie voor SG meetellen. Dit blijft voorwaardelijk vermogen, afzonderlijk van echte P1-injectie. Handmatige, onbekende, oude of ontbrekende laadsessiegegevens geven geen credit. Een hogere Wallbox houdt de bestaande voorrang; een al toegelaten SG-aanvraag krijgt niet opnieuw een startreserve vanwege een lager geplaatste Wallbox.
- Netgrens, resterend kwartierbudget, passende afzonderlijke fasegrenzen, batterijontlading, bronactualiteit, interlocks, gebruikerskeuze, beschermde cycli en lopende opdrachten blijven onafhankelijk leidend. Ook na opslag- of transport-awaits worden de relevante gegevens opnieuw gecontroleerd.
- Een waargenomen extern AAN geeft geen eigendom. De oorspronkelijke vijftienminutentijd blijft na herstart staan. Voortzetting vraagt nieuwe actuele voorwaarden en bevestiging van de korte lokale timer. Een handmatige UIT, gewijzigde koppeling, onzekere opdracht of defecte terugval geeft geen blind replay. Een volledige eigen bevestigde lease mag uitsluitend onder haar bestaande herstartcontract voortgezet worden.
- Externe SG-overname vraagt ook voldoende actuele startbijdrage; lage netafname zonder zon geeft geen nachtboost. Voor de extra elektrische ruimte is een al ingeschakeld passend contact geen nieuwe extra belasting. De oorspronkelijke sessietijd telt mee in het harde maximum.
- Tijdelijke gewone bron-/transportonbereikbaarheid is een afzonderlijke source_wait/command_wait met hercontrole, geen algemene UIT-voorwaarde of foutpauze. Onzekere werkelijk verzonden opdrachten behouden hun eigen gerichte herstelvoorwaarden. Geen andere toestellen blokkeren omdat een bron ontbreekt.
- Afwasmeteractiviteit is alleen presentatie/historie: geen START-confirmatie, programma-einde, ticketverbruik of volledig cyclusleerbewijs. Een native lopende/gepauzeerde cyclus houdt bescherming. Energie wordt niet over reset, herstart, bronwissel, gat of middernacht geïnterpoleerd.
- Ontbrekend, restored, boolean, NaN, oneindig, toekomstig of beschadigd bewijs wordt geen actuele nul. Uitlezen, formatteren, re-renderen en metadatahercontrole vernieuwen geen oorspronkelijke meettijd.
- Warmtepompafleiding blijft herkenbaar als afgeleid en levert geen nieuw model- of actuatorrecht. De geverifieerde geladen Aquarea-semantiek, bindingen en oorspronkelijke bewijstijden blijven vereist; een versienummer is geen bewijs.
- Huidige en geregistreerde historische bronrechten blijven van toepassing. Private ACL-bronnen en installatie-identiteiten worden niet openbaar gemaakt. Onleesbare bestaande opslag wordt niet stil overschreven; onbekende oudere velden behouden hun historische betekenis.
- Iedere software-update werkt de volledige actuele uitleg, changelog en dit dossier bij. Controleer ook actuele Aquarea/SDK-defaultbranches en stabiele tagcommits. Publiceer uitsluitend na de vijf bestaande commitgebonden CI-gates en de assetvergelijking.

## 4. Actuele werking

De runtime leest P1/PV, eventuele batterij- en fasegegevens en bestaande toestelbronnen. Zij houdt werkelijk restoverschot, al verbruikt warmtepompvermogen en voorwaardelijk overdraagbaar autonoom laadvermogen apart. De centrale rangorde en individuele voorwaarden bepalen het voorstel. De finale dispatch herleest de benodigde actuele gegevens; een plan alleen is geen toestemming.

Gewone toestellen houden start-/stopbuffers en minimumtijden. De afwasroute behoudt eenmalige appvrijgave, deur/remote/verbinding, deadlines en bescherming van een gestarte cyclus. Een onafhankelijke meter kan een extern gestarte elektrische activiteit registreren zonder startrecht te verlenen.

SG gebruikt een afzonderlijke lokale lease, met minimumduur, wolkenbuffer, rest-/herbeoordelingsregels en een hard sessiemaximum. Extern handmatig AAN krijgt eerst vijftien minuten waarneming. Daarna kan dezelfde actuele AAN zonder UIT-puls overgaan naar automatisch, mits alle actuele voorwaarden gelden. Een externe UIT wordt niet automatisch opnieuw aangezet. Tijdelijk Aan/Uit voor 30/60 minuten blijft beschikbaar; een bewuste keuze kan het gecontroleerde externe AAN-contact direct benoemen.

## 5. Configuratie, integraties en belangrijke entiteiten

Alle installatie-specifieke entiteiten en bronkoppelingen blijven in de privé-config-entry, SolarPilot-opslag en userfiles. Geen export, installatie-URL, huisadres, token, echte privé-entiteitslijst of recorderbestand in de repository opnemen.

De integratie gebruikt bestaande Home Assistant-bronnen en de apart gevalideerde lokale Shelly-SG-uitgang. Native Aquarea-uitlezing blijft afhankelijk van geladen semantiek, actuele providerpoll en passende HA-rapporten. PV/omvormervermogen, tarieven, capaciteit en apparaatramingen zijn configuratie; nieuwe software herschrijft die niet op basis van een exportvermoeden.

## 6. Belangrijke ontwerpbeslissingen + waarom

De vorige vaste Wallbox-vóór-SG-regel veroorzaakte de gemelde onwerkende verplaatsingen en kon geldige SG-starts blijven blokkeren. De bestaande HouseFirstGuard wordt nu ook voor SG gebruikt wanneer de centrale volgorde dat vraagt. Dit hergebruikt stabiliteits- en meetbeleid en houdt de laadpaal autonoom.

Een permanente manual_hold voor iedere externe AAN paste niet bij de gewenste automatische terugkeer. Externe waarneming heeft nu een aparte kleine bewaarde toestand met vaste deadline. Eigendom ontstaat pas na een geslaagde actuele gecontroleerde timeropdracht. OFF is geen noodzakelijke tussenstap voor een geldige overname.

Drie ongebruikte helpers zijn verwijderd; de echte planner toetst nog steeds volledige slots tegen venster/deadline. Handleiding en optiehulp hebben ieder één actuele declaratie. README en startinstructie verwijzen naar de huidige werking; releasehistorie blijft in CHANGELOG en Git. De oude Manual Release-workflow is verwijderd; uitsluitend de bestaande volledige Validate-publicatieroute blijft over.

## 7. Automatische processen

De lokale regelcyclus, bronhercontrole, analysecollectie, metergeschiedenis, planner en modelopslag blijven actief volgens hun eigen configuratie. Bronwachten blokkeren andere bruikbare toestellen niet. De externe SG-deadline wordt alleen door een echte nieuwe waarneming aangemaakt en niet door uitlezen of herstart verlengd.

SolarPilot verstuurt geen exports automatisch en voert geen AI-code of providerupdate op de installatie uit. GitHub Validate publiceert op main alleen wanneer alle vijf jobs slagen. Een eerder gepubliceerde tag of asset wordt niet overschreven.

## 8. Geheimenbeleid

Gebruik uitsluitend fictieve bronidentiteiten in tests en browserfixtures. Diagnosebestanden blijven buiten Git. Publieke repositorycontrole en diffreview blijven verplicht. Privé-modellen, userfiles en historie horen niet in release-ZIP's. Logs en testmeldingen mogen geen tokens, headers of geheime foutbodies bevatten.

## 9. Testprocedure + actuele teststatus

De ongewijzigde beta.105-basis slaagde lokaal met 8638 tests. De nieuwe gerichte SG-/voorrangs-/tijdelijke-bedieningscontrole slaagde met 47 tests; de bredere gerichte bron-/transport-/herstartcontrole met 191 tests. De volledige bijgewerkte softwarebron slaagde lokaal met 8667 tests. De definitieve bron moet daarnaast alle vijf CI-gates halen. Exact bewijs en beperkingen staan in docs/TESTRESULTATEN_BETA106.md; eerdere totalen zijn geen uitslag van een latere commit.

De nieuwe browsergate bedient de gemelde vier rijen met pijltjes, slepen, bevestigen en opslaan en controleert de SG-overnameafteller op smalle schermen. Lokale Chromium-installatie leverde geen bruikbaar downloadarchief; geen lokale visuele uitslag claimen. De verplichte Chromium- en echte Core-startupjobs blijven vereist vóór publicatie.

## 10. Bekende problemen / beperkingen

Softwaretests certificeren geen fysieke bekabeling, SG-respons, sensorkalibratie of werkelijk terugregelen van een Wallbox. Voorwaardelijke overdracht kan kort netafname veroorzaken; harde grenzen blijven bewaakt. Een bestaande PV-voorspelfout of ontbrekende afzonderlijke meter is niet door het corrigeren van voorrang opgelost. Bronproblemen vragen bewijs en bewuste koppeling; geen sensoren gokken.

Nieuwe external_control-opslag is aanvullend op schema 1. Beta.105 negeert deze toestand en kent de nieuwe deadline niet. Een nieuwe SG-vóór-Wallbox-volgorde kan in een oude versie anders worden geïnterpreteerd. Onzekerheid wordt niet als bewezen UIT of fysieke reparatie voorgesteld.

## 11. Concrete openstaande ontwikkeling

Na installatie observeren of de natuurlijke externe SG-overname en autonome laadreactie bij de echte installatie overeenkomen met de software-uitkomst. Dit is een installatiecontrole, geen reden om vooraf een geforceerde warmte-/laadproef uit te voeren. PV-voorspelling en ontbrekende exclusieve meters blijven afzonderlijke analyseonderwerpen. Geen extra comfortregelingen of hardwareopdrachten toevoegen zonder nieuwe gebruikersvraag.

## 12. Installatie/upgrade en rollback

Update via HACS naar beta.106, herstart Home Assistant volledig en herlaad app/browser. Controleer backend-/kaartversie en de centrale volgorde. Maak vooraf een volledige privéback-up, inclusief aanvullende meterhistorie en userfiles.

Rollback naar beta.105 behoudt de oude regeling maar brengt de oude Wallbox-vóór-SG-beperking en externe manual_hold terug. Geef een eigen SG-aanvraag waar betrouwbaar mogelijk veilig vrij, controleer lokale afloop en zet code terug met behoud van entry en gegevens. Geen tweede runtime of verwijder/herinstallatie als migratiemethode. Zie docs/BETA106_INSTELLEN.md.

## 13. Belangrijkste bestanden

- runtime.py: orchestratie en finale elektrische/broncontroles.
- priority_board.py: centrale volgorde, expliciete opslaanvalidatie en eenmalige defaultmigratie.
- sg_boost.py / sg_transport.py: waarneming, oorspronkelijke deadlines, lease-eigendom en lokale SG-transportgrens.
- heatpump_budget.py / house_first.py: aparte gemeten en voorwaardelijke zonnebijdragen en stabiliteit.
- frontend/solar-pilot-card.js: editor, SG-stand en afteller.
- current_guide.py / option_help.py: canonieke actuele uitleg en veldhulp.
- tests/test_priority106.py / tests/test_sg_external106.py: nieuwe regressies; bestaande audit-/herstarttests behouden hun andere harde assertions.
- tools/check_priority_external_ui106.py: echte kaartinteracties met fictieve data.

## 14. Release-checklist

Volledige suite; actuele uitleg; handoff; repositoryprivacy/structuur; SG-grens; online upstreamreview; beide JavaScript-syntaxcontroles; diffreview. Daarna vijf groene exacte CI-gates: repository/full-suite, HACS, Hassfest, Chromium, echte Home Assistant-startup. Pas daarna main. Main herhaalt de gates en publiceert tag, HACS-ZIP, lokale ZIP en beide beta.106-documenten. Vergelijk de vier gedownloade assets opnieuw met de exacte tag/bron-SHA. Geen manual-release-omweg, force-push of verplaatste oude tag.

## 15. AI-handoff

Begin bij de actuele bron en dit dossier; gebruik historische releasebeschrijvingen niet als huidige regeling. Lees de concrete nieuwe gebruikersvraag en preserveer onafhankelijke beschermingen. Een nieuwe externe AAN wordt vijftien minuten waargenomen; een externe UIT blijft gerespecteerd. De Wallbox staat standaard achteraan, maar een expliciet opgeslagen andere volgorde blijft een echte keuze. Iedere wijziging aan deze grenzen vraagt zinvolle regressies en bijgewerkte actuele uitleg. Publiceer geen privé-export of huishouddetails en claim geen live-installatietest die niet is uitgevoerd.
