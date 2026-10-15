# SolarPilot 1.0.0-beta.90 — automatisch herbeoordelen na tijdelijke onbereikbaarheid

Een tijdelijk onbereikbaar toestel krijgt een **informatieve herstelwacht**. SolarPilot beoordeelt die situatie elke **vijf minuten** opnieuw en gebruikt daarna de voorwaarden die op dat moment gelden. De update maakt geen fysieke proefopdracht en verandert geen sensorkoppeling of apparaatinstelling.

## Wat verandert

Een onbereikbaar gewoon toestel blijft afzonderlijk wachten. **Automatisch regelen** is als globale modus kiesbaar wanneer één toestel offline is of op bronherstel wacht. Die keuze omzeilt geen apparaatvoorwaarde: gezonde andere lasten kunnen alleen verder bij betrouwbare gedeelde metingen, hun eigen toestemming en voldoende actuele net-/fase-/kwartierruimte.

Voor een tijdelijk geïsoleerd offline toestel wordt **geen extra hypothetische verbruiksreserve** afgehouden. Het werkelijke actuele P1-overschot bepaalt de beschikbare zonne-energie, naast de behouden filtering, huisreserve en overige actuele voorwaarden. Onbekend toestelvermogen wordt niet als gemeten 0 W voorgesteld en levert geen geschat eigen-vermogenskrediet. Een oude ON-status van een offline afwasmachine geeft evenmin een nieuwe toekomstige piekreserve. De bestaande afwaspiek blijft wel gelden wanneer de afwasmachine werkelijk nu betrouwbaar actief is; de afzonderlijke SG-reserve blijft onder haar bestaande strengere beleid vallen.

## Hercontrole is geen blinde herhaalopdracht

- Bij **bronwacht** wordt bereikbaarheid elke 300 seconden opnieuw beoordeeld. Een vanzelf terugkerend nieuw bruikbaar bronbericht kan eerder passief worden waargenomen; er is geen actieve actuatorpoll of proefschakeling.
- Bij **opdrachtwacht** blijft een mogelijk al uitgevoerde opdracht onzeker. Alleen passende verse oorspronkelijke terugmelding ná die poging kan de toestand verzoenen. Eigendom, poging en mogelijke belasting blijven als metadata beschikbaar, zonder extra offline-verbruiksreserve of blind retryrecht.
- Na herstel beslist de gewone planner opnieuw over vraag, voorrang, minimumtijden, start-/stopbuffers, modus, eigenaarschap en actuele elektrische ruimte. Een gemist oud AAN- of UIT-commando wordt niet afgespeeld.
- Een al geprobeerd of onzeker **afwas-START blijft verbruikt**. De vijfminutencontrole verstuurt geen tweede START, maakt geen nieuwe APP-aanvraag en verlengt geen deadline of bestaande hersteltermijn. Een lopend beschermd programma wordt niet onderbroken.
- Exact herkende oude gewone transport-, timeout- en terugmeldfouten kunnen naar deze herstelwacht overgaan. Een oud opgeslagen bericht na upgrade is geen nieuw herstelbewijs. Echte configuratie-, authenticatie-, toestemmings-, interne, maximumlooptijd- of fysieke fouten blijven gerichte controle vragen.

## Wat je op de kaart ziet

Bij tijdelijke onbereikbaarheid verschijnt een wachtstatus met de eerstvolgende hercontrole, in plaats van een blijvende opdrachtfout waarvoor je telkens bevestiging moet geven. Ontbrekend vermogen blijft onbekend. Andere echte fouten en SG-/batterijproblemen worden niet verborgen. De klok geeft de volgende beoordeling aan, geen gegarandeerd startmoment.

## Bestaande installatie bijwerken

1. Maak een volledige privé Home Assistant-back-up inclusief instellingen, SolarPilot-opslag, modellen, APP-aanvragen, historie en userfiles. Bewaar gecontroleerde beta.89-code.
2. Geef vóór codevervanging een eigen SG-aanvraag veilig vrij waar betrouwbaar mogelijk en controleer contact of lokale afloop. Onderbreek geen beschermde cyclus en herhaal geen onzekere opdracht.
3. Update via HACS naar exact `1.0.0-beta.90` nadat releasecontroles en publicatie zijn geslaagd. Lokaal vervang je uitsluitend `custom_components/solar_pilot`, met behoud van userfiles en HA-opslag.
4. **Herstart Home Assistant volledig** en herlaad browser/app volledig. Controleer backend- en kaartversie afzonderlijk. Verwijder of hermaak de entry niet.
5. Controleer bij een offline toestel de herstelwacht en de volgende beoordeling. Automatisch regelen kiezen bedient het wachtende toestel niet. Gezonde lasten moeten hun eigen vrijgave blijven volgen.
6. Bij vanzelf terugkerende status hoort een nieuwe beoordeling van de huidige omstandigheden. Maak voor een softwarecontrole geen extra afwasaanvraag en stuur geen tweede onzekere START.

Een bestaande echte interne foutpauze blijft beschermd. Beoordeel de concrete fout en kies na herstel bewust **Controle afronden** en **Automatisch regelen**. Deze update wist geen onbekende fout om de regeling geforceerd te hervatten.

## Wat behouden blijft

De restzonverdeling naast een betrouwbaar actieve onbemeterde afwasbeurt uit beta.89 blijft behouden. Algemene en individuele Wallbox-voorkeuren en oorspronkelijke eindtijden, minimumtijden, beschermde cycli, vraag/interlocks, instellingen, sensorkoppelingen, rangorde, modellen en historie blijven staan. Er komt geen nieuwe verplichte sensor of instelling bij.

Panasonic blijft eigenaar van haar native comfort, tank, compressor, ondersteuning en sterilisatie. SolarPilot heeft alleen haar bestaande begrensde SG-bevoegdheid. Wallbox blijft read-only. Batterij- en SG-opdrachten krijgen geen nieuwe retryroute of verruimde grenzen.

## Rollback naar beta.89

Bewaar eerst een actuele volledige privéback-up en geef de eigen SG-aanvraag veilig vrij waar betrouwbaar mogelijk; controleer de lokale afloop. Stop beta.90 en herstel gecontroleerde beta.89-code met behoud van entry, opslag en userfiles. Herstart HA volledig en herlaad browser/app. Gebruik nooit twee runtimes tegelijk.

Beta.89 behoudt de restzonverdeling en Wallbox-voorkeuren maar herstelt het eerdere fout-/herstel- en reserveringsgedrag bij offline toestellen; dat kan opnieuw gerichte controle of een grotere reserve vragen. Een onzekere opdracht of verbruikte APP-aanvraag wordt niet veilig door codewissel opnieuw uitvoerbaar. Exact herstel vraagt code én een passende volledige privéback-up. Herstel nooit een oude onverbruikte aanvraag nadat dezelfde belading al gestart is.

Actuele werking: [ACTUELE_WERKING.md](ACTUELE_WERKING.md). Software-/CI-/pakketbewijs: [TESTRESULTATEN_BETA90.md](TESTRESULTATEN_BETA90.md). Privé-exports en woninggegevens horen niet op GitHub.
