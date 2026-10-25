<!-- solarpilot-handoff-schema: 1 -->
<!-- solarpilot-handoff-version: 1.0.0-beta.108 -->

# OVERDRACHT — SolarPilot

Laatst bijgewerkt: **25 oktober 2026**. Actuele bron: **v1.0.0-beta.108**. Bouwbasis: gepubliceerde beta.107 `3c375dc1a34ecf33e5c80b00f8b64a5c1a555a88`. Installatie en rollback: `docs/BETA108_INSTELLEN.md`. Softwarebewijs en publicatievoorwaarden: `docs/TESTRESULTATEN_BETA108.md`.

## 1. Projectdoel in gewone taal

SolarPilot verdeelt beschikbare zonnestroom lokaal tussen flexibele toestellen, een beschermde afwasmachine en een optionele SG-zonneboost. De autonoom regelende Wallbox gebruikt standaard het overschot dat overblijft. Panasonic regelt zelfstandig ruimtecomfort, normaal warm water, koeling en sterilisatie. Home Assistant toont actuele activiteit, de reden om te wachten en geregistreerde historie. Modellen en voorspellingen helpen plannen; actuele metingen bepalen wat fysiek mag.

## 2. Actuele basis

Beta.108 laat SG vóór een lager geplaatste bevestigde autonome zonnelaadsessie van de Wallbox tijdig haar zonnevermogen gebruiken. De laadpaal regelt zelfstandig en mag vertraagd reageren. Alleen de softwarematige totale netgrens krijgt een afzonderlijke begrensde uitzondering. De bijdrage is hoogstens het minimum van actueel coherent laadvermogen, de geraamde SG-opname en max_takeover_w; standaard begrenst die laatste waarde tot 2500 W. De eerste bijdrage blijft het plafond voor dezelfde episode.

De bestaande handover_s geeft standaard 240 seconden reactietijd, voor SG hoogstens 600 seconden. Een episode begint bij het eerste bruikbare P1-rapport boven de softwaregrens tijdens een bevestigde lopende SG-aanvraag of een exact actueel waargenomen extern AAN-contact binnen zijn oorspronkelijke vijftien minuten. De oorspronkelijke absolute eindtijd blijft na herstart staan. Alleen aantoonbaar herstel naar de ruwe SG-importdrempel, standaard 600 W, gedurende handover_confirm_s, standaard vijftien seconden, en minstens twee verschillende nieuwe rapporten maakt een volgende episode mogelijk. Een onbekende herstart begint zonder verse uitzondering.

De beta.107-startcoherentie en oorspronkelijke brontelemetrie blijven behouden. Centrale voorrang, expliciet opgeslagen gebruikersvolgorde en beschermde afwasvoorrang blijven leidend. Een exact passend actueel extern AAN-contact mag binnen de oorspronkelijke vijftien minuten dezelfde begrensde EV-reactietijd voor behoud gebruiken, zonder eigendom, ON-opdracht, leasevernieuwing of verse minimumduur. De oorspronkelijke vijftienminutendeadline en daaropvolgende ruwe importbeoordeling blijven ongewijzigd. De canonieke actuele uitleg en optiehulp blijven één declaratieve bron met gegenereerde mirrors.

## 3. Absolute ontwerpregels

- Panasonic-entiteiten zijn read-only. Alleen de bewust toegewezen bestaande fysieke SG-uitgang heeft een aparte gecontroleerde schrijfroute. Geen tank-/kamertemperatuur-, programma-, AUTO/OFF-, heater-, Powerful-/Force- of tweede-Shelly-besturing toevoegen. Bestaande lokaal ingestelde SG-capaciteiten blijven behouden.
- Wallbox blijft read-only, ook bij uitgeschakelde monitoring en via inspecteerbare indirecte scripts. Een hogere last kan de laadpaal uitsluitend indirect laten terugregelen. Geen laadcommando of verzonnen laadvermogen.
- Alleen met SG vóór Auto laden mag actuele betrouwbare gemeten laadruimte uit een bevestigde autonome zonnelaadsessie voor SG meetellen. Dit blijft voorwaardelijk vermogen, afzonderlijk van echte P1-injectie. Handmatige, onbekende, oude, ontbrekende of fysiek tegenstrijdige laadsessiegegevens geven geen credit. De coherentiecontrole verleent geen nieuwe actuele meettijd en begrenst uitsluitend de voorwaardelijke SG-bijdrage; zij creëert geen werkelijk gemeten vrije injectie. Een hogere Wallbox houdt de bestaande voorrang; een al toegelaten SG-aanvraag krijgt niet opnieuw een startreserve vanwege een lager geplaatste Wallbox.
- De softwarematige totale netgrens kent uitsluitend de expliciet geautoriseerde begrensde SG-/Wallbox-reactie-uitzondering. Ruwe P1 wordt niet aangepast. Resterend kwartierbudget, passende afzonderlijke fasegrenzen, batterijontlading, bronactualiteit, interlocks, gebruikerskeuze, beschermde cycli en lopende opdrachten blijven onafhankelijk leidend. Ook na opslag- of transport-awaits worden de relevante gegevens opnieuw gecontroleerd.
- De Wallbox-reactie-episode krijgt één oorspronkelijke absolute eindtijd en begrensde eerste bijdrage. Polls, uitlezen, leasevernieuwing, gewijzigde koppelingen of herstart verlengen die niet. Geen nieuw episodebudget door alleen onder de softwaregrens te schommelen; werkelijk herstel op of onder de SG-importdrempel vraagt bevestigingstijd en minstens twee nieuwe rapporten. Verlies van actuele geschikte EV-bronnen trekt de uitzondering in.
- Een waargenomen extern AAN geeft geen eigendom. De oorspronkelijke vijftienminutentijd blijft na herstart staan. Voortzetting vraagt nieuwe actuele voorwaarden en bevestiging van de korte lokale timer. Een handmatige UIT, gewijzigde koppeling, onzekere opdracht of defecte terugval geeft geen blind replay. Een volledige eigen bevestigde lease mag uitsluitend onder haar bestaande herstartcontract voortgezet worden.
- Externe SG-overname vraagt ook voldoende actuele startbijdrage; lage netafname zonder zon geeft geen nachtboost. Voor de extra elektrische ruimte is een al ingeschakeld passend contact geen nieuwe extra belasting. De oorspronkelijke sessietijd telt mee in het harde maximum.
- Tijdelijke gewone bron-/transportonbereikbaarheid is een afzonderlijke source_wait/command_wait met hercontrole, geen algemene UIT-voorwaarde of foutpauze. Onzekere werkelijk verzonden opdrachten behouden hun eigen gerichte herstelvoorwaarden. Geen andere toestellen blokkeren omdat een bron ontbreekt.
- Afwasmeteractiviteit is alleen presentatie/historie: geen START-confirmatie, programma-einde, ticketverbruik of volledig cyclusleerbewijs. Een native lopende/gepauzeerde cyclus houdt bescherming. Energie wordt niet over reset, herstart, bronwissel, gat of middernacht geïnterpoleerd.
- Ontbrekend, restored, boolean, NaN, oneindig, toekomstig of beschadigd bewijs wordt geen actuele nul. Uitlezen, formatteren, re-renderen en metadatahercontrole vernieuwen geen oorspronkelijke meettijd.
- Warmtepompafleiding blijft herkenbaar als afgeleid en levert geen nieuw model- of actuatorrecht. De geverifieerde geladen Aquarea-semantiek, bindingen en oorspronkelijke bewijstijden blijven vereist; een versienummer is geen bewijs.
- Huidige en geregistreerde historische bronrechten blijven van toepassing. Private ACL-bronnen en installatie-identiteiten worden niet openbaar gemaakt. Onleesbare bestaande opslag wordt niet stil overschreven; onbekende oudere velden behouden hun historische betekenis.
- Iedere software-update werkt de volledige actuele uitleg, changelog en dit dossier bij. Controleer ook actuele Aquarea/SDK-defaultbranches en stabiele tagcommits. Publiceer uitsluitend na de vijf bestaande commitgebonden CI-gates en de assetvergelijking.

## 4. Actuele werking

De runtime leest P1/PV, eventuele batterij- en fasegegevens en bestaande toestelbronnen. Werkelijk restoverschot, al gebruikt warmtepompvermogen en voorwaardelijk overdraagbaar autonoom laadvermogen blijven apart. De centrale rangorde en individuele voorwaarden bepalen de kandidaat; finale dispatch herleest de benodigde actuele gegevens.

Gewone toestellen behouden start-/stopbuffers en minimumtijden. De afwasroute houdt eenmalige appvrijgave, deur/remote/verbinding, deadlines en bescherming van een gestarte cyclus. Een onafhankelijke meterwaarneming verleent geen startrecht.

SG gebruikt een afzonderlijke lokale lease, minimumduur, wolkenbuffer, herbeoordelingsregels en een hard sessiemaximum. De gewone wolkenbuffer blijft standaard 600 W gedurende vijf minuten en gebruikt de ruwe P1-netafname. De begrensde Wallbox-reactietijd loopt parallel; zij geeft geen nieuwe tekorttimer en wordt niet door het SG-minimum verlengd. Alleen binnen een actuele bewezen overdracht mag de softwarematige totale netgrens tijdelijk worden overschreden. Fase-, kwartier-, batterij- en bronvoorwaarden kunnen eerder vrijgeven. Zonder geldige uitzondering of bij verlopen eindtijd geldt de gewone netgrens weer.

Extern handmatig AAN krijgt eerst vijftien minuten waarneming en daarna de bestaande actuele overnamebeoordeling. Binnen de oorspronkelijke externe periode mag de begrensde EV-reactietijd alleen een exact passend actueel AAN-contact behouden; de deadline en daarna de ruwe import-/zonnebeoordeling blijven ongewijzigd. Een fysieke handmatige UIT wordt niet automatisch teruggezet. Tijdelijk Aan/Uit voor 30/60 minuten blijft beschikbaar. Panasonic blijft eigenaar van comfort en compressorregeling; de Wallbox krijgt geen opdracht.

## 5. Configuratie, integraties en belangrijke entiteiten

Alle installatie-specifieke entiteiten en bronkoppelingen blijven in de privé-config-entry, SolarPilot-opslag en userfiles. Geen export, installatie-URL, huisadres, token, echte privé-entiteitslijst of recorderbestand in de repository opnemen.

De integratie gebruikt bestaande Home Assistant-bronnen en de apart gevalideerde lokale Shelly-SG-uitgang. Native Aquarea-uitlezing blijft afhankelijk van geladen semantiek, actuele providerpoll en passende HA-rapporten. PV/omvormervermogen, tarieven, capaciteit en apparaatramingen zijn configuratie; nieuwe software herschrijft die niet op basis van een exportvermoeden.

## 6. Belangrijke ontwerpbeslissingen + waarom

Alleen voorrang bij de start werkte niet samen met een autonoom regelende laadpaal die later terugschakelt. Beta.108 maakt die vertraagde reactie mogelijk binnen een expliciete beperkte software-uitzondering. De totale P1-netafname blijft zichtbaar en wordt voor de gewone wolkenbuffer, fasebewaking en kwartiercontrole niet met toekomstig EV-vermogen verlaagd. De uitzondering is dus geen bewijs van fysieke nulimport of bevestigd terugregelen.

Een episode blijft begrensd na een kleine dip rond de softwaregrens. Pas ruwe netafname op of onder de gewone SG-importdrempel met meerdere nieuwe rapporten en bevestigingstijd herstelt een nieuwe overdrachtsmogelijkheid. Absolute opslag en conservatieve herstart voorkomen steeds nieuwe gratis reactietijd. Verlies of wijziging van de bron-/beleids-/voorrangskoppeling geeft geen nieuwe toestemming.

Een laatste cloudrapport kan binnen de ouderdomsgrens vallen terwijl de laadpaal al anders verbruikt. Daarom blijft de beta.107-coherentiecontrole voor de voorwaardelijke bijdrage behouden. Onafhankelijk gemeten export blijft bruikbaar. De nieuwe reactietijd verandert geen Panasonic-capaciteit, SG-mapping, fysieke Shelly-terugval, normale externe waarneming of beveiligingsinstelling.

## 7. Automatische processen

De lokale regelcyclus, bronhercontrole, analysecollectie, metergeschiedenis, planner en modelopslag blijven actief volgens hun eigen configuratie. Bronwachten blokkeren andere bruikbare toestellen niet. De externe SG-deadline wordt alleen door een echte nieuwe waarneming aangemaakt en niet door uitlezen of herstart verlengd.

SolarPilot verstuurt geen exports automatisch en voert geen AI-code of providerupdate op de installatie uit. GitHub Validate publiceert op main alleen wanneer alle vijf jobs slagen. Een eerder gepubliceerde tag of asset wordt niet overschreven.

## 8. Geheimenbeleid

Gebruik uitsluitend fictieve bronidentiteiten in tests en browserfixtures. Diagnosebestanden blijven buiten Git. Publieke repositorycontrole en diffreview blijven verplicht. Privé-modellen, userfiles en historie horen niet in release-ZIP's. Logs en testmeldingen mogen geen tokens, headers of geheime foutbodies bevatten.

## 9. Testprocedure + actuele teststatus

De definitieve beta.108-bron slaagt lokaal met 8828 tests zonder fouten of skips, waaronder 121 nieuwe overdrachts-, runtime-, transport-, UI- en diagnoseregressies. Drie opstartregressies uit een vroege volledige loop zijn opgelost door pas na geladen opslag te observeren/bewaren; de oorspronkelijke en aanvullende opslagtests slagen in de volledige herhaling. Actuele uitleg, veldhulp, overdracht, privacy/structuur, SG-grens en beide JavaScript-syntaxcontroles zijn gecontroleerd. De online upstreamhercontrole bevestigt ongewijzigde officiële HEADs en stabiele tagcommits. Exacte CI-gates en downloadvergelijking blijven vereist; zie docs/TESTRESULTATEN_BETA108.md.

Alle vijf bestaande CI-gates blijven verplicht: repository/full-suite, HACS, Hassfest, Chromium en echte Home Assistant-startup. De browsercontrole behoudt de bestaande prioriteitsbediening en SG-/bronweergave. Een lokale ontbrekende browser rechtvaardigt geen overgeslagen remote gate.

## 10. Bekende problemen / beperkingen

Softwaretests certificeren geen bekabeling, werkelijke SG-respons, kalibratie of daadwerkelijke Wallbox-terugregeling. De nieuwe software-uitzondering staat bewust tijdelijk extra totale netafname toe binnen haar bewijs-, vermogens- en tijdgrenzen; zij verhoogt geen fysieke aansluitcapaciteit. De lokale korte SG-terugval blijft een afzonderlijk mechanisme. Het vierminutenvenster betreft actieve HA-softwarepolicy. Een bestaande eigen lokale lease is standaard 300 seconden; bij HA-uitval is fysieke UIT exact op 240 seconden dus niet gegarandeerd. Extern AAN krijgt door de beperkte bewaarexceptie geen nieuw lokaal timerrecht.

Een ongeschikte, oude, handmatige of tegenstrijdige EV-bron geeft geen uitzondering. Na een onbekende herstart moet eerst nieuw herstelbewijs komen; een aantoonbaar lopende bewaarde episode krijgt alleen haar oorspronkelijke resterende tijd. Onafhankelijke fase-, kwartier-, batterij- of contactvoorwaarden kunnen SG nog steeds eerder vrijgeven. Een groter wolkenvenster is geen vervanging voor deze regeling. PV-voorspelling en ontbrekende exclusieve meters blijven afzonderlijke onderwerpen.

## 11. Concrete openstaande ontwikkeling

Laat na installatie de normale SG-/Wallboxreactie met oorspronkelijke brontelemetrie vastleggen. Beoordeel of de berekende reactietijd, werkelijke P1 en laadsessierapporten overeenkomen; geen geforceerde warmte- of laadproef uitvoeren als publicatiestap. PV-voorspelling en ontbrekende exclusieve meters vragen hun eigen bewijs. Geen extra hardwarebediening of Panasonic-writer toevoegen.

## 12. Installatie/upgrade en rollback

Update via HACS naar beta.108, herstart Home Assistant volledig en herlaad app/browser. Controleer backend-/kaartversie en de effectieve centrale volgorde. SG moet vóór de Wallbox staan voor de nieuwe overdracht. Bestaande handover_s en max_takeover_w blijven bewaard. Maak vooraf een volledige privéback-up, inclusief userfiles en aanvullende historie.

Rollback naar beta.107 behoudt centrale voorrang, externe overname, coherentie en brontelemetrie, maar verwijdert deze begrensde netgrensuitzondering. SG kan bij een netpiek dan opnieuw direct openen terwijl de Wallbox nog laadt. Geef de eigen SG-aanvraag waar betrouwbaar mogelijk veilig vrij en behoud entry en gegevens. Zie docs/BETA108_INSTELLEN.md.

## 13. Belangrijkste bestanden

- runtime.py: orchestratie en finale elektrische/broncontroles.
- priority_board.py: centrale volgorde, expliciete opslaanvalidatie en eenmalige defaultmigratie.
- sg_boost.py / sg_transport.py: waarneming, oorspronkelijke deadlines, lease-eigendom en lokale SG-transportgrens.
- heatpump_budget.py / house_first.py: aparte gemeten en voorwaardelijke zonnebijdragen, SG-startcoherentie en stabiliteit.
- sg_wallbox_transfer.py: begrensde reactie-episode, oorspronkelijk plafond en eindtijd, herstelbewijs en conservatieve herstart.
- analysis_export.py: snelle brontelemetrie met actuele overdracht; oorspronkelijk overdrachtbegin/eindtijd en broncontext bij begrensde toestandsovergangen en SG-overgangen. Herstel wist dit eerdere bewijs binnen de maximaal zevendaagse gebeurtenisretentie niet; geen aftelseconde-eventstroom of controlrecht.
- frontend/solar-pilot-card.js: editor, SG-stand en afteller.
- current_guide.py / option_help.py: canonieke actuele uitleg en veldhulp.
- tests/test_sg_coherence107.py / tests/test_sg_priority_reason107.py / tests/test_analysis_fast107.py: nieuwe regressies; bestaande voorrangs-, audit- en herstarttests behouden hun overige assertions.
- tools/check_priority_external_ui106.py: echte kaartinteracties met fictieve data.

## 14. Release-checklist

Volledige suite; actuele uitleg; handoff; repositoryprivacy/structuur; SG-grens; online upstreamreview; beide JavaScript-syntaxcontroles; diffreview. Daarna vijf groene exacte CI-gates: repository/full-suite, HACS, Hassfest, Chromium, echte Home Assistant-startup. Pas daarna main. Main herhaalt de gates en publiceert tag, HACS-ZIP, lokale ZIP en beide beta.108-documenten. Vergelijk de vier gedownloade assets opnieuw met de exacte tag/bron-SHA. Geen manual-release-omweg, force-push of verplaatste oude tag.

## 15. AI-handoff

Begin bij de actuele bron en dit dossier. De gebruiker heeft expliciet toegestaan dat SG zonnestroom van een lager geplaatste autonoom regelende Wallbox overneemt en dat die vertraagd terugschakelt. De softwarematige totale netgrens krijgt daarom uitsluitend de beschreven begrensde overdrachtuitzondering; beschrijf haar niet meer als een altijd onmiddellijke SG-stop. Houd de ruwe P1 en onafhankelijke fase-, kwartier-, batterij-, bron-, eigendoms- en sessievoorwaarden intact.

Lees de concrete volgende vraag en verleng geen episode door uitlezen, herstart of hetzelfde meetbewijs. Maak geen handmatige/unknown EV-sessie tot bevestigde zonnelaadvraag. Behoud expliciete volgorde, SG-capaciteiten, beschermde afwascyclus en fysieke UIT. Werk actuele uitleg en overdracht bij iedere wijziging bij. Publiceer geen privé-export of huishouddetails en claim geen fysieke installatieproef die niet is uitgevoerd.
