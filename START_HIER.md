# SolarPilot beta.76 — installatie en upgrade

Beta.76 voegt gezamenlijke toestelplanning toe binnen dezelfde SolarPilot-integratie. De planner vergelijkt verschuivingen en uitwisselingen op de geraamde huishoudelijke energiekost plus een zachte piekpenalty. Alleen een geldige verbetering wordt overgenomen; de bestaande ingeplande energie, prioriteiten en lopende beschermde cycli blijven behouden. Batterijadvies wordt daarna chronologisch doorgerekend met SoC, verliezen en aparte laad-/ontlaadgrenzen. Het is adviserend, zonder netladen of energie uit de toekomst.

**Begin met [BETA76_INSTELLEN.md](docs/BETA76_INSTELLEN.md).** Geen aparte EMHASS-installatie, solver, add-on of dienst. Volledige werking: [ACTUELE_WERKING.md](docs/ACTUELE_WERKING.md) en **SolarPilot → Uitleg**. Actueel software-/publicatiebewijs: [TESTRESULTATEN_BETA76.md](docs/TESTRESULTATEN_BETA76.md). Oudere tests bewijzen geen geslaagde beta.76-release.

## Bestaande installatie bijwerken

1. Maak een volledige privé HA-back-up met instellingen, eigen opslag, modellen, tickets, geschiedenis en userfiles. Bewaar gecontroleerde beta.75-code.
2. Geef vóór codevervanging een eigen SG-aanvraag vrij en controleer contact/lokale afloop. Onderbreek geen beschermde apparaatcyclus.
3. Update via HACS naar exact `1.0.0-beta.76` nadat de releasegates en publicatie zijn geslaagd. Herstart HA volledig en herlaad browser/app volledig.
4. Controleer backend- en kaartversie apart. Behoud dezelfde entry, bindings, volgorde en geldige SG-/profiel-/split-/koelbevestigingen.
5. Bekijk Planning, bestaande meetdekking, Automatisch onderzoek, SG-lagen en geschiedenis. Gezamenlijke toestelplanning (`joint_optimisation`) staat standaard aan. Uitschakelen laat de bestaande planner en actuele guards werken.

Lokaal vervang je uitsluitend `custom_components/solar_pilot`, met behoud van userfiles en HA-opslag. Verwijder of hermaak de entry niet. Er is geen nieuwe verplichte bron, algemene herbevestiging of handmatige dependency-installatie.

## Bestaande regeling blijft gelden

Panasonic blijft eigenaar van comfort, warm water, compressor, pompen, kleppen, ondersteuning en sterilisatie. SolarPilot gebruikt voor de warmtepomp uitsluitend het bestaande toegewezen SG-contact. De Wallbox blijft autonoom en read-only. De planner omzeilt geen actuele P1/PV-, fase-, net-, bron-, apparaat- of commandobescherming.

De SG-netafnamebuffer blijft standaard **strikt boven 600 W gedurende vijf continue minuten**, tegelijk met de **minimale SG-aanvraagduur van twintig minuten**. Bij 600 W of lager vervalt de tekorttimer. Een tekort vanaf minuut 18 kan bij aanhouden pas in minuut 23 gewone vrijgave geven. Zonder tekort is twintig minuten geen verplichte stop. De zonne-resetgrens blijft apart, standaard 300 W. Afwijkende behouden instellingen blijven gelden.

Korte lokale toestemming blijft standaard 300 s, veilig vernieuwd iedere 60 s tijdens geldige minimum- en wolkenwachttijd. Harde guards, handmatige overname, geverifieerde native beëindiging, fouten en hardmaximum mogen eerder vrijgeven. Renewal/reload creëren geen nieuw aanvraagrecht. Het minimum betreft de SG-aanvraag, geen gegarandeerde compressorlooptijd.

Onderzoek, historische gegevens en antwoordrapporten blijven behouden. Een adviesupload past geen instelling of code toe. Gezamenlijke planning bewijst geen werkelijke besparing en bevat geen actieve thermische regeling of gezamenlijke batterijoptimalisatie.

## Gegevens en rollback

Voor rollback: geef de eigen SG-aanvraag vrij, controleer lokale afloop, stop beta.76 en herstel gecontroleerde beta.75-code. Behoud entry, opslag en userfiles; planner en batterijadvies gebruiken opnieuw de beta.75-werking. Exact herstel vraagt code én de passende volledige privéback-up; bewaar gewenste nieuwe historie eerst. Geen twee runtimes tegelijk. Volledige stappen: [BETA76_INSTELLEN.md](docs/BETA76_INSTELLEN.md).
