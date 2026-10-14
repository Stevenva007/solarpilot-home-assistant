# SolarPilot beta.86 — installatie en upgrade

Beta.86 voegt alleen binnen het lokaal bevestigde algemene SG-profiel een gecontroleerde herbeoordeling toe bij onbekende eerdere SG-reactie: na bestaande rust vijf minuten verse werkelijk resterende zon, minstens twee nieuwe rapporten en genoeg overschot voor startdrempel én volledige conservatieve extra-vraagraming. Daarna geldt de gewone startvertraging. Ontbrekende warmtepompwatts geven geen krediet; de noodzakelijke net-/PV-/batterij-/fase-/koel-/contactvoorwaarden blijven vereist.

Beta.85 herstelt de tijdelijke SG-dispatchopruiming: een vroege terugkeer mag geen bestaande finale controle verwijderen. **Herstart Home Assistant volledig** na de update en herlaad browser/app. Een bestaande interne foutpauze blijft beschermd; controleer de melding, kies **Controle afronden** en daarna bewust **Automatisch regelen** zodra de actuele voorwaarden dit toelaten.

Beta.84 voegt tijdelijke SG-bediening toe: **Aan of Uit voor 30/60 minuten**, daarna terug naar **Automatisch**. De absolute eindtijd wordt bewaard. Een echte HA-herstart kan een passende nog actieve eigen beta.84-sessie onder verse geldige voorwaarden zonder onnodige contactwissel voortzetten. Het oorspronkelijke harde sessiemaximum, alle harde grenzen en de korte lokale timer blijven leidend.

**Begin met [BETA86_INSTELLEN.md](docs/BETA86_INSTELLEN.md).** Geen extra installatie, sensor, solver of parallelle regelaar. Volledige werking: [ACTUELE_WERKING.md](docs/ACTUELE_WERKING.md) en **SolarPilot → Uitleg**. Uitgevoerde checks en publicatiestatus: [TESTRESULTATEN_BETA86.md](docs/TESTRESULTATEN_BETA86.md). Auditdekking: [AUDIT_BETA79.md](docs/AUDIT_BETA79.md). Oudere resultaten bewijzen geen beta.86-release.

## Bestaande installatie bijwerken

1. Maak een volledige privé HA-back-up met instellingen, eigen opslag, PV-factoren, modellen, tickets, geschiedenis en userfiles. Bewaar gecontroleerde beta.85-code.
2. Geef vóór codevervanging een eigen SG-aanvraag veilig vrij en controleer contact/lokale afloop. Onderbreek geen beschermde apparaatcyclus.
3. Update via HACS naar exact `1.0.0-beta.86` nadat releasegates en publicatie zijn geslaagd. Herstart HA volledig en herlaad browser/app volledig.
4. Controleer backend- en kaartversie afzonderlijk. Behoud dezelfde entry, bindings, volgorde en geldige SG-/profiel-/split-/koelbevestigingen.
5. Controleer de nieuwe SG-bediening en haar resterende tijd, echte contactstand en lokale timer. Een oude beta.83-sessie mist het nieuwe checkpointbewijs en kan bij deze eerste upgrade nog één veilig contactvrijgavemoment krijgen. Pas een volledig bevestigd beta.84-checkpoint kan het nieuwe herstartpad gebruiken.
6. Controleer daarnaast actuele taak, ondersteuning, boilerwaarden, oorspronkelijke AEG-aanvraag/deadline, Planning, PV-diagnose, Meetkwaliteit, kosten en geschiedenis. Een update maakt geen nieuwe belading of tweede START. Onleesbare oude opslag blijft behouden; wis daarvoor geen gegevens.

Lokaal vervang je uitsluitend `custom_components/solar_pilot`, met behoud van userfiles en HA-opslag. Verwijder of hermaak de entry niet. Geen instellingenreset, nieuwe verplichte bron of algemene herbevestiging.

De inschakelklok kan maximaal vijf minuten doorlopen bij een korte zondip of tijdelijk ontbrekende/verouderde meting. AAN wacht altijd op opnieuw verse betrouwbare voldoende zonnebijdrage en harde vrijgave. Een voltooide klok tijdens de dip betekent wachten op herstel; ontbrekend is geen nul of bewezen wolk. Bij een langere onderbreking of harde-/modus-/bindingblokkering begint de opbouw opnieuw.

## Tijdelijke SG-bediening

Kies naast de SG-contactstand **Aan 30 min**, **Aan 1 uur**, **Uit 30 min** of **Uit 1 uur**, in Overzicht of op het warmtepomptabblad. Na afloop wordt **Automatisch** gekozen; je kunt dat tussentijds ook kiezen. Tijdelijk Aan vervangt de zonne- en zachte wachtvoorwaarden, met mogelijke netafname binnen harde grenzen. Alleen bekijken, Pauze, bronverlies, fouten, onvoldoende elektrische ruimte, ongeldige profiel-/koelvrijgave en voorrang blijven leidend. Een lopende sessie krijgt geen nieuw maximum door een tijdelijke keuze.

Tijdelijk Uit onderdrukt alleen de eigen SG-aanvraag; Panasonic mag zelfstandig verder werken. Bij terugkeer naar Automatisch besluit de actuele gewone policy: een geldig al AAN-contact hoeft niet uit/aan, een nieuwe start na Uit krijgt geen automatische vrijstelling. De native HA-select **SG-bediening** biedt dezelfde vijf keuzes. De uitgebreide service- en herstartvoorwaarden staan in de installatiehandleiding.

## Wat behouden blijft

Panasonic regelt comfort, warm water, verwarmen/koelen, ondersteuning en sterilisatie zelfstandig. Het toegewezen SG-contact blijft de enige warmtepompactuator; geen setpoint-, programma- of heaterwrite. Wallbox blijft read-only. AEG krijgt maximaal één native START per geldige nieuwe belading en mag afwerken.

Gewone automatische SG behoudt 600 W netafname gedurende vijf continue minuten, minimum twintig minuten en het bestaande harde maximum. De lokale toestemming blijft standaard 300 seconden, met vernieuwing iedere 60 seconden; zij wordt bij een half uur of uur Aan niet tot die duur verlengd. Expliciete geldige gebruikerswaarden en harde guards blijven leidend. De bron-/doelweergave, PV-factoren, planner, batterijadvies, onderzoeken, exports en historie uit beta.83 blijven behouden.

## Nieuwe installatie

Voeg `https://github.com/Stevenva007/solarpilot-home-assistant` toe in **HACS → Custom repositories** als **Integration**, download SolarPilot en herstart HA. Voeg de integratie toe onder **Instellingen → Apparaten & diensten**. Selecteer betrouwbare lokale bronnen en begin met **Alleen bekijken**. SG staat standaard uit en vraagt gecontroleerde ingebruikname. De meegeleverde kaart wordt automatisch geregistreerd.

## Rollback

Geef de eigen SG-aanvraag veilig vrij en controleer contact/lokale afloop. Bewaar een actuele volledige privéback-up, stop beta.86 en herstel gecontroleerde beta.85-code met behoud van entry, opslag en userfiles. Beta.85 behoudt de callbackfix, tijdelijke bediening, startklokbuffer en bevestigde herstart, maar mist de nieuwe herbeoordeling bij onbekende reactie op verse restzon. Laat nooit twee runtimes tegelijk werken. Code terugzetten mag geen tweede START of oude AAN-replay vrijgeven. Zie [BETA86_INSTELLEN.md](docs/BETA86_INSTELLEN.md).

Openbare broncontrole en de afzonderlijke geautoriseerde wekelijkse ontwikkeltaak staan in [UPSTREAM_BRONNEN.md](docs/UPSTREAM_BRONNEN.md). De taak verandert geen lokale Home Assistant-installatie of apparaten.
