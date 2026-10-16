# SolarPilot beta.94 — test- en publicatieverslag

Versie: **1.0.0-beta.94** · 16 oktober 2026

Bouwbasis: gepubliceerde beta.93-commit `0ff89ed72a982e1b16e84885cb977cf28a1e23dc`. De wijziging bewaart uitsluitend betrouwbare UIT-timing voor de minimale rusttijd van gewone verbruikers. Privé-installatiegegevens en echte apparaatopdrachten worden niet in tests of publieke bestanden gebruikt.

## Gereproduceerde oorzaak

De runtime maakte bij elke constructie een nieuwe `last_off` op de huidige monotonic-klok. De gewone opslag bevatte geen oorspronkelijke UIT-tijd. Een al lang uitgeschakeld toestel kreeg daardoor na herstart opnieuw een volledige minimale rusttijd. In een onafhankelijke reproductie ging een reeds verstreken rusttijd terug naar 1800 seconden. In een tweede reproductie werd een resterende rusttijd van 600 seconden opnieuw 1800 seconden; op de oorspronkelijke deadline bleef het toestel nog 1200 seconden wachten ondanks voldoende synthetisch overschot.

## Correctie en bewijsgrenzen

Een afzonderlijk privécheckpoint bewaart de bevestigde absolute UIT-tijd met passende toestel-/bronkoppeling. De tijd wordt na een geldige actuele UIT-controle naar de nieuwe monotonic-klok vertaald. De oorspronkelijke tijd blijft behouden bij herhaalde herstarts en de tijd tijdens een herstart telt mee. De huidige ingestelde minimale rusttijd blijft leidend.

Een bewaarde tijd is geen bewijs dat een toestel nu UIT staat en geeft geen startrecht. Ontbrekende of herstelde placeholders, onzekere opdrachten, gewijzigde bronnen, corrupte of toekomstige tijdgegevens en ongeschikte actieve herstelgegevens geven geen verkorting. Een echte nieuwe uitschakeling begint een nieuwe rusttijd. Herstel van een mogelijk opnieuw gestarte AAN-last behoudt de volledige minimumlooptijd.

Beta.93 en ouder hebben geen bruikbaar nieuw checkpoint. Bij de eerste upgrade kan daarom eenmaal de volledige rusttijd gelden. Er wordt geen eerdere UIT-tijd verzonnen of uit historische schermbeelden afgeleid. De afzonderlijke buffer voor stabiel zonneoverschot wordt opnieuw op echte actuele metingen beoordeeld.

## Verificatie

Alle **17 nieuwe functionele regressies** en **36 onafhankelijke grenscontroles** zijn geslaagd. Zij controleren verstreken en gedeeltelijke rusttijd, herstarttijd, herhaalde herstarts, echte nieuwe UIT-overgang en behoud van de actuele minimuminstelling. Tegenproeven controleren onbruikbare bronnen, gewijzigde koppelingen, tijdproblemen, onzekere opdrachtuitkomsten, afgewezen startintenties en behoud van de huidige P1-voorwaarden. Ook een vervangen bron tijdens asynchrone intentopslag krijgt geen fysieke start en behoudt de volledige rusttijd.

De brede gerichte route behaalde **461 geslaagde tests**; de afzonderlijke definitieve onafhankelijke groep behaalde 36 geslaagde tests. Deze groepen overlappen en worden niet tot een verzonnen onafhankelijke totaalscore opgeteld. De volledige suite wordt op de definitieve bron uitgevoerd; oude releasetotalen zijn geen beta.94-testbewijs.

De verificatiewatermark verandert uitsluitend door een werkelijke controle, niet door het alleen opvragen van een snapshot of diagnostiek. Een lege journal heeft geen fictieve uitleestijd. De nieuwe automatische checkpointopslag wacht totdat bestaande runtimeopslag is geladen; een vroege waarneming overschrijft geen nog te herstellen voorkeuren of leases. Bestaande onveranderlijkheids- en herstartregressies blijven ongewijzigd.

De actuele Aquarea- en SDK-defaultbranches en laatste stabiele releasecommits zijn online opnieuw gecontroleerd: geen nieuwe relevante wijzigingen tegenover Aquarea 1.5.4 en aioaquarea-ng 1.3.1. Beide releasedocumenten hebben een bytegelijke componentmirror.

## Definitieve releasegates

Alle vijf verplichte jobs moeten op dezelfde definitieve bron slagen: repository-/privacy-/documentatiecontroles met de volledige Python-suite en PowerShell-regressies, HACS, Hassfest, echte Home Assistant-startup/reload/unload en Chromium. De [Validate-workflow](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml) bevat het brongebonden uitvoeringsbewijs.

Daarna maakt de publicatiejob een nieuwe annotated tag en vier assets en downloadt ze terug om bronbytes, grootte en SHA-256 te controleren:

- `SolarPilot-v1.0.0-beta.94-GitHub-HACS.zip`
- `SolarPilot-v1.0.0-beta.94-local.zip`
- `BETA94_INSTELLEN.md`
- `TESTRESULTATEN_BETA94.md`

Een bestaande tag of releaseasset wordt niet overschreven. Softwaretests en pakketcontrole bevestigen geen installatie in de woning. De gekozen toestelinstellingen, bronactualiteit en elektrische grenzen blijven zelfstandig vereist.
