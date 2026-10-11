# SolarPilot beta.72 — installatie en upgrade

Beta.72 voegt een minimale SG-aanvraagduur toe, standaard twintig minuten. Gewone aanhoudende netafname geeft de aanvraag pas na dit effectieve minimum vrij. Harde guards, handmatige overname, geverifieerde native voltooiing en het behouden sessiemaximum kunnen eerder beëindigen. Panasonic bepaalt zelfstandig zijn compressorlooptijd.

**Begin met [BETA72_INSTELLEN.md](docs/BETA72_INSTELLEN.md).** Daar staan minimum/maximum, veilige korte leases, behoud en rollback naar beta.71. Volledige werking: [ACTUELE_WERKING.md](docs/ACTUELE_WERKING.md) en **SolarPilot → Uitleg**. Software-/publicatiebewijs: [TESTRESULTATEN_BETA72.md](docs/TESTRESULTATEN_BETA72.md).

## Bestaande installatie bijwerken

1. Maak een volledige privé HA-back-up met instellingen, eigen opslag, modellen, tickets, geschiedenis en userfiles. Bewaar gecontroleerde beta.71-code.
2. Geef een eigen SG-aanvraag vóór codevervanging vrij en controleer contact/lokale afloop. Onderbreek geen beschermde apparaatcyclus.
3. Update via HACS naar exact `1.0.0-beta.72` na publicatie. Herstart HA volledig en herlaad browser/app volledig.
4. Controleer backend- en kaartversie afzonderlijk. Behoud entry, bindings, volgorde en geldige SG-/profiel-/split-/koelbevestigingen.
5. Controleer **Minimale SG-aanvraagduur (s)** naast het behouden maximum. Alleen een ontbrekende minimumoptie krijgt standaard 1200 s; expliciete waarden, ook nul, blijven staan. Een korter bestaand maximum wordt niet verhoogd.

Lokaal vervang je uitsluitend `custom_components/solar_pilot`, met behoud van userfiles en HA-opslag. Verwijder of hermaak de entry niet. Er is geen algemene herbevestiging bij een ongewijzigde upgrade.

## Duur van de SG-aanvraag

Het minimum begint na bevestigde contact-AAN. De bestaande gewone tekortvertraging loopt intussen door: bij twintig minuten kan al bevestigd tekort meteen tot vrijgave leiden. Zonder tekort hoeft de aanvraag dan niet te stoppen. De bij bevestigde AAN nog beschikbare harde maximumtijd begrenst het effectieve minimum.

De lokale toestemming blijft kort, standaard 300 s met vernieuwing elke 60 s. Tijdens uitsluitend de minimumwacht op zachte tekortvrijgave kan vernieuwing veilig doorgaan; harde guards blijven leidend. De Shelly-timer wordt niet 1200 s. Leasevernieuwing reset het minimum niet; reload geeft geen nieuw minimum of AAN-recht. Bij uitval kan lokaal eerder worden vrijgegeven.

De minimumduur betreft alleen de SG-aanvraag. Geverifieerde native voltooiing, bevestigd geen extra opname, bron-/elektrische-/batterij-/koel-/voorrangsgrenzen, handmatige overname, Pauze en fouten behouden vroege vrijgave. Panasonic-percentages, koelwaarden, programma's en native beveiligingen blijven ongewijzigd.

## Geschiedenis en export behouden

Warmtepomp- en gewone geschiedenis, modellen en tickets blijven staan. De beta.71-wachtfasen en kalenderdag-export blijven behouden: dertig lokale dagen retentie apart van 1/24/168 rollende uren, alle overlappende datums, volledige geregistreerde dagtotalen en expliciete grensdatums/meetdekking. Geen backfill of energie naar rato.

## Rollback naar beta.71

Geef de eigen SG-aanvraag vrij, controleer contact/lokale afloop, stop beta.72 en herstel gecontroleerde beta.71-code. Behoud entry, opslag en userfiles. Beta.71 kent het nieuwe minimum niet en kan gewone aanhoudende netafname weer volgens de oude stopvertraging vrijgeven. Voor exact herstel gebruik je code én de passende volledige privéback-up; bewaar gewenste nieuwe historie eerst. Geen twee runtimes tegelijk. Volledige stappen: [BETA72_INSTELLEN.md](docs/BETA72_INSTELLEN.md).
