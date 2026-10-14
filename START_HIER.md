# SolarPilot beta.83 — installatie en upgrade

Beta.83 corrigeert uitsluitend de weergave van de bekende Aquarea-bronsemantiek en maakt een berekend tapwater-SG-doel mogelijk met een lokaal bevestigd percentage. Werkelijke contactstand, gewone doelbron en oorspronkelijke tijden blijven apart. Onderzoek houdt eerdere beoordeling en actuele bron coherent; vooruit-PV-scores scheiden daglicht en nacht. Leren, SG-regeling, elektrische grenzen, instellingen en oude historie blijven behouden.

**Begin met [BETA83_INSTELLEN.md](docs/BETA83_INSTELLEN.md).** Geen extra installatie, sensor, solver of parallelle regelaar. Volledige werking: [ACTUELE_WERKING.md](docs/ACTUELE_WERKING.md) en **SolarPilot → Uitleg**. Uitgevoerde checks en publicatiestatus: [TESTRESULTATEN_BETA83.md](docs/TESTRESULTATEN_BETA83.md). Auditdekking en concrete bevindingen: [AUDIT_BETA79.md](docs/AUDIT_BETA79.md). Oudere resultaten bewijzen geen geslaagde beta.83-release.

## Bestaande installatie bijwerken

1. Maak een volledige privé HA-back-up met instellingen, eigen opslag, PV-factoren, modellen, tickets, geschiedenis en userfiles. Bewaar gecontroleerde beta.82-code.
2. Geef vóór codevervanging een eigen SG-aanvraag vrij en controleer contact/lokale afloop. Onderbreek geen beschermde apparaatcyclus.
3. Update via HACS naar exact `1.0.0-beta.83` nadat releasegates en publicatie zijn geslaagd. Herstart HA volledig en herlaad browser/app volledig.
4. Controleer backend- en kaartversie apart. Behoud dezelfde entry, bindings, volgorde en geldige SG-/profiel-/split-/koelbevestigingen.
5. Controleer actuele taakherkenning, ondersteuning, SG-contactbalk en actuele/ingestelde boilerwaarden. Voor een berekend SG-doel kies je onder Warmtepomp — uitleesbronnen de bestaande geregistreerde native tankbron voor de vergelijking, vul je het op Panasonic ingestelde tapwaterpercentage in en bevestig je de overeenkomst lokaal; de update vult dit niet automatisch als bevestigd in. Bekijk daarnaast beslisredenen, de oorspronkelijke AEG-aanvraag/deadline, Planning, PV-diagnose, Meetkwaliteit, kosten en geschiedenis. Een update maakt geen nieuwe belading en geeft geen tweede START vrij.
6. Bij onbekende of beschadigde oude opslag blijft de oorspronkelijke opslag behouden. Een concrete laadfout kan nieuwe duurzame registratie of adviesimport tegenhouden; wis daarvoor geen gegevens. Oude verbruikershistoriek zonder betrouwbare bronherkomst blijft voor beheerders zichtbaar.

Lokaal vervang je uitsluitend `custom_components/solar_pilot`, met behoud van userfiles en HA-opslag. Verwijder of hermaak de entry niet. Geen instellingenreset, nieuwe verplichte bron of algemene herbevestiging.

## Wat behouden blijft

Panasonic regelt comfort, warm water, verwarmen/koelen, ondersteuning en sterilisatie zelfstandig. Het toegewezen SG-contact blijft de enige warmtepompactuator; geen setpoint-, programma- of heaterwrite. Wallbox blijft autonoom en read-only, ook wanneer SolarPilot-monitoring uit staat. AEG krijgt maximaal één native START per geldige nieuwe belading en mag afwerken.

SG behoudt 600 W netafname gedurende vijf continue minuten, minimum twintig minuten en korte leases; expliciete geldige gebruikerswaarden en harde guards blijven leidend. De bestaande AEG-deadline/grace, PV-factoren, gezamenlijke planner, batterijadvies, onderzoeken, exports en historie blijven behouden. Een softwarematige netgrens is geen fysieke beveiliging.

## Nieuwe installatie

Voeg `https://github.com/Stevenva007/solarpilot-home-assistant` toe in **HACS → Custom repositories** als **Integration**, download SolarPilot en herstart HA. Voeg de integratie toe onder **Instellingen → Apparaten & diensten**. Selecteer betrouwbare lokale bronnen en begin met **Alleen bekijken**. SG staat standaard uit en vraagt zijn bestaande afzonderlijke gecontroleerde ingebruikname. De meegeleverde kaart wordt automatisch geregistreerd.

## Rollback

Geef de eigen SG-aanvraag vrij, controleer contact/lokale afloop, stop beta.83 en herstel gecontroleerde beta.82-code met behoud van entry, actuele opslag en userfiles. Beta.82 behoudt taak-/ondersteuningsweergave, SG-contactbalk en gewone temperatuurhistorie, maar mist de specifieke bronsemantiekcorrectie, berekende SG-doelen en nieuwe diagnose-/PV-presentatie. Aanvullende nieuwe velden kunnen bij een opslagwrite door oudere code verdwijnen; bewaar nieuwe historie en een volledige privéback-up vooraf. Code terugzetten maakt geen verbruikte of onzekere START opnieuw beschikbaar.

Exact herstel vraagt code én de passende volledige privéback-up; bewaar gewenste nieuwe historie eerst. Herstel geen oude onverbruikte ticketback-up bij een inmiddels gestart of afgerond programma. Laat nooit twee runtimes tegelijk werken. Zie [BETA83_INSTELLEN.md](docs/BETA83_INSTELLEN.md).


Openbare broncontrole en de afzonderlijke geautoriseerde wekelijkse ontwikkeltaak staan in [UPSTREAM_BRONNEN.md](docs/UPSTREAM_BRONNEN.md). De taak verandert geen lokale Home Assistant-installatie of apparaten.
