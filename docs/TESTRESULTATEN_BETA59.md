# SolarPilot 1.0.0-beta.59 — testresultaten

Datum: **2026-10-06**

## Bronbasis en bewijsgrenzen

De absolute codebasis en rollbackbasis zijn gepubliceerde beta.58 op commit `5920c3f3156cd62f508559ee5a860e1bec9e9c9a`, tree `3a8838c63897285b32f1829b0ccf59b96fe59e3c`, annotatietagobject `b385d59109de64f1e7da0367f01baadb88d49547`. De onveranderlijke [beta.58-release](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.58), release-ID `404666467`, workflow `37461351451` en alle vier gepubliceerde assets zijn gecontroleerd. Beide ZIP-pakketten zijn inhoudelijk en met SHA-256 tegen de exacte gepubliceerde bron vergeleken. Lokaal behaalde beta.58 3561 tests in 41,68 s; CI behaalde 3561 tests in 52,14 s. Dit is basisbewijs, geen beta.59-test-/publicatiebewijs.

De latere gebruikerslogs melden een leerattribuutpakket dat de Recorder-limiet overschrijdt en een trage fase-sensoropbouw. De gebruiker vraagt databehoud. Het onderstaande onderscheidt Recorderkopieën, volledige eigen modelopslag en beschikbare ruwe analysehistorie.

De gebruikersvraag betreft ook een terugkerende interne Pauze na expliciet kiezen van Automatisch regelen, naast de twee actuele energietegels, Zonnepanelen en Net. De kleurenschaal is een read-only weergave van actuele metingen; zij kiest geen modus, actuatoractie of nieuwe elektrische grens. Regressies gebruiken fictieve gegevens, zonder privé-export of installatie-identiteit.

## Concrete fout en bewijs

De concrete codefout zat in `dhw_runtime._comfort_forecast`: het pad voor zonnevoorraad gebruikte `timedelta` terwijl de module alleen `datetime` importeerde. Een bruikbare zonnige forecast en ingeschakelde avondvoorraad konden daarom `NameError` veroorzaken; de algemene runtime-foutbescherming zette de regeling naar een interne foutpauze. Beta.59 importeert de gebruikte tijdsduurklasse en toetst het actieve forecast-/avondvoorraadpad. Het screenshot zonder bijbehorende traceback is geen bewijs dat precies dit defect de live pauze veroorzaakte. Geen algemene exception-slikker, automatische foutreset of verruimde fysieke vrijgave.

De twee gerichte regressies in `tests/test_dhw_forecast59.py` reproduceren vóór de reparatie respectievelijk de `NameError` en de interne Pauze in een echte runtime-ronde met fictieve HA-bronnen. Na de importreparatie slagen beide. De brede gerichte selectie behaalde 230 tests in 2,27 s. Dit is gerichte software-evidentie, afzonderlijk van de opnieuw uit te voeren uitgebreide eindgate hieronder en live installatieacceptatie.

## Recorder en presentatiecache

De Home Assistant Recorder-limiet voor één attribuutpakket is 16 KiB; meer schijfruimte vergroot die limiet niet. De ontbrekende grote attributen `pv_model`, `thermal_model`, `learning_insights`, `removal`, `pv_forecast`, `savings` en `electricity_today` worden toegevoegd aan de bestaande `_unrecorded_attributes`. Hun volledige actuele inhoud blijft in de native sensorattributes staan. De eigen `_snapshot`-opslag en de directe analyse-/exportmodellen blijven behouden, met dezelfde bestaande bewaartermijnen en bron-/aantallimieten. Alleen de herhaalde Recorder-kopie van grote detailpakketten valt weg; geen gebruikersdatareset, leerreset, verwijdering van oude opslag of volledige-meetgeschiedenisgarantie. Reeds ontbrekende Recorder-records worden niet achteraf aangevuld.

`runtime.sensor_overview(name)` bewaart uitsluitend presentatieoverzichten voor EMS en leren binnen één publicatieronde. `publish` bouwt eerder aangevraagde overzichten één keer opnieuw vóór listenerupdates, zodat meerdere sensoren hetzelfde pakket gebruiken. Controllers en analyse/export vragen hun directe live-overzichten nog steeds zelf op; de weergavecache geeft geen nieuwe actuatorvrijgave en verandert geen besturingsbronversheid. Een gemelde trage fase-sensoropbouw is geen bewijs dat de fysieke fasebewaking uitgevallen is; de herhaalde presentatieopbouw wordt gericht verminderd.

## Softwaregate

**Geslaagd na de definitieve Recorder-/presentatiecachewijziging: 3569 tests in 44,55 s.** De volledige suite draaide met `PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider`. De twee nieuwe forecastregressies toetsen het echte zonnige avondvoorraadpad en de algemene runtime-ronde. Zes nieuwe sensorregressies toetsen de Recordergrootte, één presentatieberekening voor negen fasesensors, verse volgende publicaties, gedeelde leerstatus, actuele directe EMS-reads en behoud van configuratie, opgeslagen modellen en de volledige beschikbare analyse-export. De sensorselectie behaalde zes tests in 0,44 s; de bredere selectie van sensor-, runtime-, herstart- en forecasttests behaalde 112 tests in 1,92 s. Daarnaast slaagden 69 bestaande UI-/sensorregressies in 4,70 s. De bestaande sensorfixture neemt de nieuwe pure `energy_display`-helper op bij haar AST-extractie; haar eerdere energie-/reserveasserties blijven behouden.

Handmatige pure-Python-bronproeven zijn geslaagd voor alle import-/exportsignalen, ontbrekende/oude/geschatte/toekomstige bronnen en eenheden. Node-proeven renderden de echte kaart en toetsten kleurverloop, indicator, bronvaliditeit en read-only gedrag. Dit gebruikt software-/DOM-doubles; er is geen Playwright- of live browseracceptatie geclaimd.

Publieke preflight, alle 15 handoffsecties, actuele uitleg/versie/441 hulpvelden (regel-hash `f41f8e940b597b27`), repositorystructuur, gelijke installatiekopieën en `git diff --check` zijn geslaagd. AST controleerde 67 Python-bestanden; JSON-controle 4 bestanden; `node --check` controleerde beide frontendbestanden. De fictieve voorbeeldpagina is opnieuw gegenereerd. De bron-/kleurproeven, publieke preflight, repositorystructuur, versie-/uitleg-/handoff- en installatiekopiechecks zijn na de laatste uitbreiding opnieuw geslaagd. De beta.58-resultaten hierboven zijn uitsluitend bewijs van de bronbasis.

| Onderdeel | Getoetst contract |
| --- | --- |
| Recorder | Alleen herhaalde grote detailattributen uitgesloten; normale samenvatting blijft recordbaar, live attrs/eigen modellen/export behouden |
| Presentatiecache | Meerdere sensoren per publish één overview-build; nieuwe publish bouwt opnieuw, controllers/export blijven live |
| Gegevensbehoud | Geen reset/verwijdering/opslaginkorting; bestaande bewaartermijnen en werkelijke dekking behouden |
| Avondvoorraadforecast | Bruikbare zonnige forecast en ingeschakelde avondvoorraad doorlopen het echte pad zonder ontbrekende tijdsduurklasse of interne foutpauze |
| Foutbescherming | Echte andere interne-/opdrachtfouten blijven beschermd; geen algemene reset of replay |
| PV-kleur | Continue rode/oranje/gele/lichtgroene/groene schaal op actuele productie ten opzichte van ingestelde AC-omvormergrens |
| P1-kleur | Injectie groen; nul lichtgroen; stijgende import via geel/oranje naar rood |
| Schaalreferenties | Geen Wp/forecast als PV-schaal; positieve netafnamegrens of omvormergrens alleen als visuele importreferentie |
| Bronbewijs | Ontbrekende, stale, restored, ongeldige en toekomstige metingen blijven grijs/ onbekend |
| Leesbaarheid | Vermogen, eenheid, afname/injectie en kleine legenda blijven zichtbaar; blauw toestelactiviteit blijft afzonderlijk |
| Read-only | Geen bediening, configuratiemigratie of gewijzigde besturingsdrempel door rendering |
| Cumulatieve regeling | Beta.58-hervatting en alle eerdere warmwater-/klimaat-/prioriteits-/reserve-/exportregressies behouden |
| Uitleg en repository | Versie59, één canonieke uitleg/hulp, gelijke installatiekopieën, 15 handoffsecties en openbare preflight |

## Betekenis en beperkingen

Een eerder opgeslagen interne foutpauze hervat niet automatisch. Na de codeherstelling kan de gebruiker één keer Automatisch regelen kiezen; een succesvolle expliciete moduskeuze wist de pauzeoorzaak zonder algemene reset. Een afzonderlijke herstart-/DHW-beoordeling kan die moduskeuze blokkeren en vraagt dan de bestaande controle; ook gemelde conflicterende regelaars behouden hun bestaande vrijgavevoorwaarden. Andere echte opdrachtfouten blijven hun modulebescherming houden. Een nieuwe interne fout vraagt haar lokale tijdstip en SolarPilot-traceback; geen blinde herhaling van toestelopdrachten.

Meer rood betekent minder zonneproductie of meer netafname op de betreffende schaal; het is geen storing, veiligheidsoordeel of bewijs van foutieve besturing. Netinjectie is groen en een nacht met nul productie kan rood tonen terwijl de installatie normaal werkt. Ontbrekende meetinformatie is geen nulmeting.

Geen live Home Assistant- of fysieke toestelacceptatie is uitgevoerd. HA-/DOM-doubles en gerenderde voorbeelddata toetsen softwaregedrag, geen daadwerkelijk geladen app, compressoractie of voorspelnauwkeurigheid. De beleidsregels en elektrische/fabrikantbescherming blijven behouden; de vastlopende berekening wordt gericht hersteld. Recorder-uitleg en cachetests zijn geen bewijs dat de volledige fysieke fasebewaking live sneller draait; eerdere ontbrekende Recorder-historie wordt niet gereconstrueerd.

## Publicatie en installatie

De eigen [beta.59-release](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.59) moet een annotated tag op exact de geteste commit, vier geslaagde workflowjobs, twee ZIP-pakketten en twee beta.59-documenten hebben. Download alle vier assets, controleer SHA-256 en vergelijk beide volledige ZIP-inhouden met de exacte tagbron. Eerdere releases blijven onveranderd. Deze afzonderlijke publicatiegegevens worden pas afgeleid uit de werkelijke nieuwe release; de softwaregate claimt ze niet vooraf.

Installatie en rollback staan in `BETA59_INSTELLEN.md`. Na installatie Home Assistant herstarten, app/webpagina opnieuw openen en backend-/kaartversie controleren. Rollbackbasis beta.58 behoudt automatisch hervatten maar bevat het herstelde avondvoorraaddefect nog; beta.59 heeft geen nieuwe opslagmigratie. Publicatie is geen installatieacceptatie.
