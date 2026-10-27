<!-- solarpilot-handoff-schema: 1 -->
<!-- solarpilot-handoff-version: 1.0.0-beta.109 -->

# OVERDRACHT â€” SolarPilot

Laatst bijgewerkt: **27 oktober 2026**. Actuele bron: **v1.0.0-beta.109**. Bouwbasis: gepubliceerde beta.106 `8193c183e293b5bb02809930cf3a46fa35ee8a41`. Installatie en rollback: `docs/BETA109_INSTELLEN.md`. Softwarebewijs en publicatievoorwaarden: `docs/TESTRESULTATEN_BETA109.md`.

## 1. Projectdoel in gewone taal

SolarPilot verdeelt beschikbare zonnestroom lokaal tussen flexibele toestellen, een beschermde afwasmachine en een optionele SG-zonneboost. De autonoom regelende Wallbox gebruikt standaard het overschot dat overblijft. Panasonic regelt zelfstandig ruimtecomfort, normaal warm water, koeling en sterilisatie. Home Assistant toont actuele activiteit, de reden om te wachten en geregistreerde historie. Modellen en voorspellingen helpen plannen; actuele metingen bepalen wat fysiek mag.

## 2. Actuele basis

Beta.108 voorkomt te grote recorderattributen bij Wallbox-sensoren. De vermogenssensor publiceert alleen power_w; de statussensor behoudt live diagnostiek maar sluit vier grote velden uit de recorder uit. Dit geeft geen nieuwe bronmeetmomenten, apparaatopdrachten of gewijzigde regelinstellingen. Regressies gebruiken uitsluitend fictieve gegevens.

Beta.107 weigert voorwaardelijke EV-startbijdrage voor SG wanneer het recente Wallboxrapport samen met de complete actuele warmtepompmeting niet binnen de uit actuele PV, getekende P1 en batterijontlading afgeleide totale belasting past, met 250 W tolerantie. Werkelijk restoverschot en een al toegelaten SG-aanvraag behouden hun bestaande betekenis. Voorrangsteksten volgen de effectieve volgorde. Snelle analyse en nieuwe SG-toestandsovergangen bewaren afzonderlijk oorspronkelijk net-/PV-/Wallboxbronbewijs. Geen ingestelde netgrens of wolkenbuffer is verhoogd.

Beta.106 verwijdert de vaste Wallbox-vÃ³Ã³r-SG-beperking uit backend en editor. De centrale volgorde is ook voor SG leidend. Gegenereerde oude defaults krijgen eenmaal de Wallbox achteraan; een bewust opgeslagen eigen volgorde wordt niet herschreven. Nieuwe gewone toestellen komen vÃ³Ã³r een laatst geplaatste Wallbox. De afwasmachine houdt de beschermde plaats vÃ³Ã³r SG.

Een extern AAN-contact wordt in Automatisch regelen waargenomen met een oorspronkelijke absolute vijftienminutendeadline. Dit is nog geen SolarPilot-eigendom of bewezen lokale lease. Na afloop volgt uitsluitend bij actuele passende zonne-, net-, koel-, prioriteits- en elektrische voorwaarden een bevestigde korte lokale toestemming, zonder UIT-puls. Anders volgt gerichte vrijgave. Alleen bekijken/Pauze nemen het externe contact niet over. Een fysieke handmatige UIT blijft beschermd.

De canonieke gebruikersuitleg is Ã©Ã©n declaratieve `current_guide.py`; `docs/ACTUELE_WERKING.md`, de ingebedde mirror en optiehulp worden daaruit gegenereerd. Oude append-/override-lagen zijn samengevoegd. De overige bronisolatie, afwasmeterwaarneming, historie, modellen, onderzoek en export/antwoordcontracten blijven behouden.

## 3. Absolute ontwerpregels

- Panasonic-entiteiten zijn read-only. Alleen de bewust toegewezen bestaande fysieke SG-uitgang heeft een aparte gecontroleerde schrijfroute. Geen tank-/kamertemperatuur-, programma-, AUTO/OFF-, heater-, Powerful-/Force- of tweede-Shelly-besturing toevoegen. Bestaande lokaal ingestelde SG-capaciteiten blijven behouden.
- Wallbox blijft read-only, ook bij uitgeschakelde monitoring en via inspecteerbare indirecte scripts. Een hogere last kan de laadpaal uitsluitend indirect laten terugregelen. Geen laadcommando of verzonnen laadvermogen.
- Alleen met SG vÃ³Ã³r Auto laden mag actuele betrouwbare gemeten laadruimte uit een bevestigde autonome zonnelaadsessie voor SG meetellen. Dit blijft voorwaardelijk vermogen, afzonderlijk van echte P1-injectie. Handmatige, onbekende, oude, ontbrekende of fysiek tegenstrijdige laadsessiegegevens geven geen credit. De coherentiecontrole verleent geen nieuwe actuele meettijd en past uitsluitend de voorwaardelijke SG-startbijdrage aan. Een hogere Wallbox houdt de bestaande voorrang; een al toegelaten SG-aanvraag krijgt niet opnieuw een startreserve vanwege een lager geplaatste Wallbox.
- Netgrens, resterend kwartierbudget, passende afzonderlijke fasegrenzen, batterijontlading, bronactualiteit, interlocks, gebruikerskeuze, beschermde cycli en lopende opdrachten blijven onafhankelijk leidend. Ook na opslag- of transport-awaits worden de relevante gegevens opnieuw gecontroleerd.
- Een waargenomen extern AAN geeft geen eigendom. De oorspronkelijke vijftienminutentijd blijft na herstart staan. Voortzetting vraagt nieuwe actuele voorwaarden en bevestiging van de korte lokale timer. Een handmatige UIT, gewijzigde koppeling, onzekere opdracht of defecte terugval geeft geen blind replay. Een volledige eigen bevestigde lease mag uitsluitend onder haar bestaande herstartcontract voortgezet worden.
- Externe SG-overname vraagt ook voldoende actuele startbijdrage; lage netafname zonder zon geeft geen nachtboost. Voor de extra elektrische ruimte is een al ingeschakeld passend contact geen nieuwe extra belasting. De oorspronkelijke sessietijd telt mee in het harde maximum.
- Tijdelijke gewone bron-/transportonbereikbaarheid is een afzonderlijke source_wait/command_wait met hercontrole, geen algemene UIT-voorwaarde of foutpauze. Onzekere werkelijk verzonden opdrachten behouden hun eigen gerichte herstelvoorwaarden. Geen andere toestellen blokkeren omdat een bron ontbreekt.
- Afwasmeteractiviteit is alleen presentatie/historie: geen START-confirmatie, programma-einde, ticketverbruik of volledig cyclusleerbewijs. Een native lopende/gepauzeerde cyclus houdt bescherming. Energie wordt niet over reset, herstart, bronwissel, gat of middernacht geÃ¯nterpoleerd.
- Ontbrekend, restored, boolean, NaN, oneindig, toekomstig of beschadigd bewijs wordt geen actuele nul. Uitlezen, formatteren, re-renderen en metadatahercontrole vernieuwen geen oorspronkelijke meettijd.
- Warmtepompafleiding blijft herkenbaar als afgeleid en levert geen nieuw model- of actuatorrecht. De geverifieerde geladen Aquarea-semantiek, bindingen en oorspronkelijke bewijstijden blijven vereist; een versienummer is geen bewijs.
- Huidige en geregistreerde historische bronrechten blijven van toepassing. Private ACL-bronnen en installatie-identiteiten worden niet openbaar gemaakt. Onleesbare bestaande opslag wordt niet stil overschreven; onbekende oudere velden behouden hun historische betekenis.
- Iedere software-update werkt de volledige actuele uitleg, changelog en dit dossier bij. Controleer ook actuele Aquarea/SDK-defaultbranches en stabiele tagcommits. Publiceer uitsluitend na de vijf bestaande commitgebonden CI-gates en de assetvergelijking.

## 4. Actuele werking

De runtime leest P1/PV, eventuele batterij- en fasegegevens en bestaande toestelbronnen. Zij houdt werkelijk restoverschot, al verbruikt warmtepompvermogen en voorwaardelijk overdraagbaar autonoom laadvermogen apart. De centrale rangorde en individuele voorwaarden bepalen het voorstel. De finale dispatch herleest de benodigde actuele gegevens; een plan alleen is geen toestemming.

Gewone toestellen houden start-/stopbuffers en minimumtijden. De afwasroute behoudt eenmalige appvrijgave, deur/remote/verbinding, deadlines en bescherming van een gestarte cyclus. Een onafhankelijke meter kan een extern gestarte elektrische activiteit registreren zonder startrecht te verlenen.

SG gebruikt een afzonderlijke lokale lease, met minimumduur, wolkenbuffer, rest-/herbeoordelingsregels en een hard sessiemaximum. De wolkenbuffer blijft standaard 600 W gedurende vijf minuten. De apart ingestelde maximale totale netafname blijft een directe vrijgavevoorwaarde, ook wanneer de lager geplaatste Wallbox nog laadt. Een langere buffer omzeilt die grens niet. De regeling kan de read-only laadpaal niet dwingen eerst te stoppen. Extern handmatig AAN krijgt eerst vijftien minuten waarneming. Daarna kan dezelfde actuele AAN zonder UIT-puls overgaan naar automatisch, mits alle actuele voorwaarden gelden. Een externe UIT wordt niet automatisch opnieuw aangezet. Tijdelijk Aan/Uit voor 30/60 minuten blijft beschikbaar; een bewuste keuze kan het gecontroleerde externe AAN-contact direct benoemen.

## 5. Configuratie, integraties en belangrijke entiteiten

Alle installatie-specifieke entiteiten en bronkoppelingen blijven in de privÃ©-config-entry, SolarPilot-opslag en userfiles. Geen export, installatie-URL, huisadres, token, echte privÃ©-entiteitslijst of recorderbestand in de repository opnemen.

De integratie gebruikt bestaande Home Assistant-bronnen en de apart gevalideerde lokale Shelly-SG-uitgang. Native Aquarea-uitlezing blijft afhankelijk van geladen semantiek, actuele providerpoll en passende HA-rapporten. PV/omvormervermogen, tarieven, capaciteit en apparaatramingen zijn configuratie; nieuwe software herschrijft die niet op basis van een exportvermoeden.

## 6. Belangrijke ontwerpbeslissingen + waarom

Een laatste HA-cloudrapport kan nog binnen zijn ouderdomsgrens liggen terwijl de fysieke laadpaal al heeft teruggeregeld. Een incoherente vermogenscombinatie levert daarom geen EV-startcredit; onafhankelijk gemeten export blijft bruikbaar. De controle is conservatief bij ongelijktijdige meters en is geen kalibratie. Zij verlengt geen lopende buffer of lease en maakt geen bestaande SG-stop later.

Een SG-stop boven de vaste totale netgrens is geen verlopen wolkenbuffer. Die grens ongemerkt uitstellen of vergroten zou haar bestaande betekenis veranderen. Beta.107 verduidelijkt het besluit en bewaart betere brongegevens voor vervolgonderzoek. Een gesloten contact of lage warmtepompwatts bewijst geen extra SG-opname; een langzame EV-/PV-reactie blijft zonder passend gelijktijdig bewijs een hypothese.

De vorige vaste Wallbox-vÃ³Ã³r-SG-regel veroorzaakte de gemelde onwerkende verplaatsingen en kon geldige SG-starts blijven blokkeren. De bestaande HouseFirstGuard wordt nu ook voor SG gebruikt wanneer de centrale volgorde dat vraagt. Dit hergebruikt stabiliteits- en meetbeleid en houdt de laadpaal autonoom.

Een permanente manual_hold voor iedere externe AAN paste niet bij de gewenste automatische terugkeer. Externe waarneming heeft nu een aparte kleine bewaarde toestand met vaste deadline. Eigendom ontstaat pas na een geslaagde actuele gecontroleerde timeropdracht. OFF is geen noodzakelijke tussenstap voor een geldige overname.

Drie ongebruikte helpers zijn verwijderd; de echte planner toetst nog steeds volledige slots tegen venster/deadline. Handleiding en optiehulp hebben ieder Ã©Ã©n actuele declaratie. README en startinstructie verwijzen naar de huidige werking; releasehistorie blijft in CHANGELOG en Git. De oude Manual Release-workflow is verwijderd; uitsluitend de bestaande volledige Validate-publicatieroute blijft over.

## 7. Automatische processen

De lokale regelcyclus, bronhercontrole, analysecollectie, metergeschiedenis, planner en modelopslag blijven actief volgens hun eigen configuratie. Bronwachten blokkeren andere bruikbare toestellen niet. De externe SG-deadline wordt alleen door een echte nieuwe waarneming aangemaakt en niet door uitlezen of herstart verlengd.

SolarPilot verstuurt geen exports automatisch en voert geen AI-code of providerupdate op de installatie uit. De echte HA-startupjob gebruikt Ubuntu 24.04 voor Python 3.14.2. GitHub Validate publiceert op main alleen wanneer alle vijf jobs slagen. Een eerder gepubliceerde tag of asset wordt niet overschreven.

## 8. Geheimenbeleid

Gebruik uitsluitend fictieve bronidentiteiten in tests en browserfixtures. Diagnosebestanden blijven buiten Git. Publieke repositorycontrole en diffreview blijven verplicht. PrivÃ©-modellen, userfiles en historie horen niet in release-ZIP's. Logs en testmeldingen mogen geen tokens, headers of geheime foutbodies bevatten.

## 9. Testprocedure + actuele teststatus

De beta.109-teststatus wordt vastgelegd in docs/TESTRESULTATEN_BETA109.md. De vijf commitgebonden CI-gates en de vergelijking van de gepubliceerde assets blijven verplicht; een eerdere groene release vervangt deze niet.

Alle vijf bestaande CI-gates blijven verplicht: repository/full-suite, HACS, Hassfest, Chromium en echte Home Assistant-startup. De browsergate behoudt onder andere pijltjes, slepen, bevestigen, opslaan, mobiele weergave en externe SG-afteller. Een lokaal ontbrekende browser geeft geen reden om de vereiste remote browsergate over te slaan.

## 10. Bekende problemen / beperkingen

Softwaretests certificeren geen fysieke bekabeling, SG-respons, sensorkalibratie of werkelijk terugregelen van een Wallbox. Voorwaardelijke overdracht kan kort netafname veroorzaken; harde grenzen blijven bewaakt. Daardoor kan SG ook met een nog ladende Wallbox direct worden vrijgegeven. Beta.107 belooft niet dat dit fysieke gedrag verdwijnt. De coherentiecontrole kan bij ongelijktijdige meters een nieuwe start uitstellen; ze bewijst geen defecte meter of laadpaal. Een bestaande PV-voorspelfout of ontbrekende afzonderlijke meter is niet door het corrigeren van voorrang opgelost. Bronproblemen vragen bewijs en bewuste koppeling; geen sensoren gokken.

Nieuwe external_control-opslag is aanvullend op schema 1. Beta.105 negeert deze toestand en kent de nieuwe deadline niet. Een nieuwe SG-vÃ³Ã³r-Wallbox-volgorde kan in een oude versie anders worden geÃ¯nterpreteerd. Onzekerheid wordt niet als bewezen UIT of fysieke reparatie voorgesteld.

## 11. Concrete openstaande ontwikkeling

Na installatie met de nieuwe oorspronkelijke brontelemetrie observeren of de natuurlijke SG-/Wallboxreactie en actuele stopgrenzen overeenkomen met de software-uitkomst. Dit is een installatiecontrole, geen reden om vooraf een geforceerde warmte-/laadproef uit te voeren. PV-voorspelling en ontbrekende exclusieve meters blijven afzonderlijke analyseonderwerpen. Geen extra comfortregelingen of hardwareopdrachten toevoegen zonder nieuwe gebruikersvraag.

## 12. Installatie/upgrade en rollback

Update via HACS naar beta.107, herstart Home Assistant volledig en herlaad app/browser. Controleer backend-/kaartversie en de centrale volgorde. Maak vooraf een volledige privÃ©back-up, inclusief aanvullende meterhistorie en userfiles.

Rollback naar beta.106 behoudt de centrale volgorde en externe overname, maar mist de nieuwe coherentiecontrole en aanvullende diagnose. Geef een eigen SG-aanvraag waar betrouwbaar mogelijk veilig vrij, controleer lokale afloop en zet code terug met behoud van entry en gegevens. Geen tweede runtime of verwijder/herinstallatie als migratiemethode. Zie docs/BETA109_INSTELLEN.md.

## 13. Belangrijkste bestanden

- runtime.py: orchestratie en finale elektrische/broncontroles.
- priority_board.py: centrale volgorde, expliciete opslaanvalidatie en eenmalige defaultmigratie.
- sg_boost.py / sg_transport.py: waarneming, oorspronkelijke deadlines, lease-eigendom en lokale SG-transportgrens.
- heatpump_budget.py / house_first.py: aparte gemeten en voorwaardelijke zonnebijdragen, SG-startcoherentie en stabiliteit.
- analysis_export.py: snelle brontelemetrie en bewaard broncontext bij nieuwe SG-toestandsovergangen.
- frontend/solar-pilot-card.js: editor, SG-stand en afteller.
- current_guide.py / option_help.py: canonieke actuele uitleg en veldhulp.
- tests/test_sg_coherence107.py / tests/test_sg_priority_reason107.py / tests/test_analysis_fast107.py: nieuwe regressies; bestaande voorrangs-, audit- en herstarttests behouden hun overige assertions.
- tools/check_priority_external_ui106.py: echte kaartinteracties met fictieve data.

## 14. Release-checklist

Volledige suite; actuele uitleg; handoff; repositoryprivacy/structuur; SG-grens; online upstreamreview; beide JavaScript-syntaxcontroles; diffreview. Daarna vijf groene exacte CI-gates: repository/full-suite, HACS, Hassfest, Chromium, echte Home Assistant-startup. Pas daarna main. Main herhaalt de gates en publiceert tag, HACS-ZIP, lokale ZIP en beide beta.107-documenten. Vergelijk de vier gedownloade assets opnieuw met de exacte tag/bron-SHA. Geen manual-release-omweg, force-push of verplaatste oude tag.

## 15. AI-handoff

Begin bij de actuele bron en dit dossier; gebruik historische releasebeschrijvingen niet als huidige regeling. Een directe netgrensstop wordt niet opgelost door alleen de wolkenbuffer langer te maken. Bewaar de grens en onderscheid gemeten, afgeleide en onbekende oorzaak; de Wallbox blijft read-only. Lees de concrete nieuwe gebruikersvraag en preserveer onafhankelijke beschermingen. Een nieuwe externe AAN wordt vijftien minuten waargenomen; een externe UIT blijft gerespecteerd. De Wallbox staat standaard achteraan, maar een expliciet opgeslagen andere volgorde blijft een echte keuze. Iedere wijziging aan deze grenzen vraagt zinvolle regressies en bijgewerkte actuele uitleg. Publiceer geen privÃ©-export of huishouddetails en claim geen live-installatietest die niet is uitgevoerd.
