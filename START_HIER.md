# SolarPilot beta.81 — installatie en upgrade

Beta.81 herstelt de SG-onderzoeksregistratie op de werkelijke runtime-grens en voegt controleerbaar bron-/sessie-/forecast-/tankbewijs toe. De bestaande regeling, instellingen, modellen en geschiedenis blijven behouden. Onbekende metingen worden niet automatisch gecorrigeerd; de beta.80-providerherkenning en koelguards blijven actief.

**Begin met [BETA81_INSTELLEN.md](docs/BETA81_INSTELLEN.md).** Geen extra installatie, sensor, solver of parallelle regelaar. Volledige werking: [ACTUELE_WERKING.md](docs/ACTUELE_WERKING.md) en **SolarPilot → Uitleg**. Uitgevoerde checks en publicatiestatus: [TESTRESULTATEN_BETA81.md](docs/TESTRESULTATEN_BETA81.md). Auditdekking en concrete bevindingen: [AUDIT_BETA79.md](docs/AUDIT_BETA79.md). Oudere resultaten bewijzen geen geslaagde beta.81-release.

## Bestaande installatie bijwerken

1. Maak een volledige privé HA-back-up met instellingen, eigen opslag, PV-factoren, modellen, tickets, geschiedenis en userfiles. Bewaar gecontroleerde beta.80-code.
2. Geef vóór codevervanging een eigen SG-aanvraag vrij en controleer contact/lokale afloop. Onderbreek geen beschermde apparaatcyclus.
3. Update via HACS naar exact `1.0.0-beta.81` nadat releasegates en publicatie zijn geslaagd. Herstart HA volledig en herlaad browser/app volledig.
4. Controleer backend- en kaartversie apart. Behoud dezelfde entry, bindings, volgorde en geldige SG-/profiel-/split-/koelbevestigingen.
5. Controleer actuele beslisredenen, de oorspronkelijke AEG-aanvraag/deadline, Planning, PV-diagnose, Meetkwaliteit, kosten en geschiedenis. Een update maakt geen nieuwe belading en geeft geen tweede START vrij.
6. Bij onbekende of beschadigde oude opslag blijft de oorspronkelijke opslag behouden. Een concrete laadfout kan nieuwe duurzame registratie of adviesimport tegenhouden; wis daarvoor geen gegevens. Oude verbruikershistoriek zonder betrouwbare bronherkomst blijft voor beheerders zichtbaar.

Lokaal vervang je uitsluitend `custom_components/solar_pilot`, met behoud van userfiles en HA-opslag. Verwijder of hermaak de entry niet. Geen instellingenreset, nieuwe verplichte bron of algemene herbevestiging.

## Wat behouden blijft

Panasonic regelt comfort, warm water, verwarmen/koelen, ondersteuning en sterilisatie zelfstandig. Het toegewezen SG-contact blijft de enige warmtepompactuator; geen setpoint-, programma- of heaterwrite. Wallbox blijft autonoom en read-only, ook wanneer SolarPilot-monitoring uit staat. AEG krijgt maximaal één native START per geldige nieuwe belading en mag afwerken.

SG behoudt 600 W netafname gedurende vijf continue minuten, minimum twintig minuten en korte leases; expliciete geldige gebruikerswaarden en harde guards blijven leidend. De bestaande AEG-deadline/grace, PV-factoren, gezamenlijke planner, batterijadvies, onderzoeken, exports en historie blijven behouden. Een softwarematige netgrens is geen fysieke beveiliging.

## Nieuwe installatie

Voeg `https://github.com/Stevenva007/solarpilot-home-assistant` toe in **HACS → Custom repositories** als **Integration**, download SolarPilot en herstart HA. Voeg de integratie toe onder **Instellingen → Apparaten & diensten**. Selecteer betrouwbare lokale bronnen en begin met **Alleen bekijken**. SG staat standaard uit en vraagt zijn bestaande afzonderlijke gecontroleerde ingebruikname. De meegeleverde kaart wordt automatisch geregistreerd.

## Rollback

Geef de eigen SG-aanvraag vrij, controleer contact/lokale afloop, stop beta.81 en herstel gecontroleerde beta.80-code met behoud van entry, actuele opslag en userfiles. Beta.80 behoudt de provideruitlezing, koelguards en eerdere auditcorrecties, maar mist de SG-onderzoeksinnamefix en de aanvullende bewijsgegevens. Code terugzetten maakt geen verbruikte of onzekere START opnieuw beschikbaar.

Exact herstel vraagt code én de passende volledige privéback-up; bewaar gewenste nieuwe historie eerst. Herstel geen oude onverbruikte ticketback-up bij een inmiddels gestart of afgerond programma. Laat nooit twee runtimes tegelijk werken. Zie [BETA81_INSTELLEN.md](docs/BETA81_INSTELLEN.md).
