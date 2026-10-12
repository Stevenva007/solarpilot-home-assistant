# SolarPilot beta.77 — installatie en upgrade

Beta.77 verbetert de lokale PV-kalibratie en uitleg van namiddagafwijkingen. De bestaande zonnestand-/seizoensvakken blijven gelden; er is geen vaste 16:00-regel. Snelle overgangen worden uitsluitend als kandidaat bewaard na een volledig vers, geldig kwartier zonder clipping. Pas herhaling op voldoende verschillende vergelijkbare dagen kan een begrensde empirische factor ondersteunen. Een overgang bewijst geen boomschaduw of afwezigheid van bewolking.

**Begin met [BETA77_INSTELLEN.md](docs/BETA77_INSTELLEN.md).** Geen extra installatie, sensor, solver of parallelle regelaar. Volledige werking: [ACTUELE_WERKING.md](docs/ACTUELE_WERKING.md) en **SolarPilot → Uitleg**. Actueel software-/publicatiebewijs: [TESTRESULTATEN_BETA77.md](docs/TESTRESULTATEN_BETA77.md). Oudere tests bewijzen geen geslaagde beta.77-release.

## Bestaande installatie bijwerken

1. Maak een volledige privé HA-back-up met instellingen, eigen opslag, PV-factoren, modellen, tickets, geschiedenis en userfiles. Bewaar gecontroleerde beta.76-code.
2. Geef vóór codevervanging een eigen SG-aanvraag vrij en controleer contact/lokale afloop. Onderbreek geen beschermde apparaatcyclus.
3. Update via HACS naar exact `1.0.0-beta.77` nadat releasegates en publicatie zijn geslaagd. Herstart HA volledig en herlaad browser/app volledig.
4. Controleer backend- en kaartversie apart. Behoud dezelfde entry, bindings, volgorde en geldige SG-/profiel-/split-/koelbevestigingen.
5. Bekijk **PV-diagnose**, vooral de kwartieren van 15:00–18:00. Daar staan factor, relevante vergelijkbare dagen en de concrete reden voor toepassen of behouden van de ruwe voorspelling. Controleer daarnaast Planning, Meetkwaliteit en geschiedenis.

Lokaal vervang je uitsluitend `custom_components/solar_pilot`, met behoud van userfiles en HA-opslag. Verwijder of hermaak de entry niet. Geen instellingenreset, nieuwe verplichte bron of algemene herbevestiging.

## Leren en behouden regeling

Alleen bestaande ingeschakelde automatische kalibratie mag factoren aanpassen. Uitgeschakelde PV-functies, presets en bewuste keuzes blijven gerespecteerd. Normaal gelden minimaal vijf vergelijkbare dagen en maximaal ±0,05 per leerdag; de factorondergrens blijft 0,35. Een globaal totaal aan leerdagen is geen bewijs voor ieder kwartier. Nieuwe overgangskandidaten hebben nieuw vergelijkbaar dagbewijs nodig; oude historie wordt niet teruggevuld of gereset.

De ingebouwde gezamenlijke toestelplanner, chronologisch batterijadvies, lokaal onderzoek, exports, adviesrapporten en geschiedenis uit beta.76 blijven behouden. De planner gebruikt de volledige gecorrigeerde curve binnen zijn bestaande horizon. Geen extra integratie, dienst of handmatige dependency-installatie.

Panasonic blijft native geregeld met uitsluitend het bestaande toegewezen SG-contact; Wallbox blijft autonoom en read-only. SG600 W gedurende vijf continue minuten, minimum twintig minuten, korte leases en alle harde guards blijven staan. Bestaande PV-/SG-instellingen en globale net-/fase-/vermogensgrenzen worden niet gewijzigd. Een betere voorspelling geeft geen nieuwe actuator- of netafnametoestemming.

## Gegevens en rollback

Voor rollback: geef de eigen SG-aanvraag vrij, controleer lokale afloop, stop beta.77 en herstel gecontroleerde beta.76-code. Behoud entry, opslag en userfiles. Beta.76 negeert de nieuwe optionele overgangskandidaten en behoudt de bestaande ondersteunde PV-factoren en overige gegevens. Exact herstel vraagt code én de passende volledige privéback-up; bewaar gewenste nieuwe historie eerst. Geen twee runtimes tegelijk. Volledige stappen: [BETA77_INSTELLEN.md](docs/BETA77_INSTELLEN.md).
