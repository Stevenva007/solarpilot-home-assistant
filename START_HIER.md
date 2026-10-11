# SolarPilot beta.73 — installatie en upgrade

Beta.73 maakt de SG-aanvraag rustiger bij wolken: gewone actueel gemeten netafname moet standaard continu boven 600 W blijven gedurende vijf minuten. Die tijd loopt samen met het minimum van twintig minuten. Korte leases blijven tijdens de geldige wachttijd veilig vernieuwd, ook na het minimum; harde guards blijven leidend.

**Begin met [BETA73_INSTELLEN.md](docs/BETA73_INSTELLEN.md).** Daar staan afzonderlijke import-/zonne-resetgrenzen, upgrade, minimum en korte leases. Volledige werking: [ACTUELE_WERKING.md](docs/ACTUELE_WERKING.md) en **SolarPilot → Uitleg**. Software-/publicatiebewijs: [TESTRESULTATEN_BETA73.md](docs/TESTRESULTATEN_BETA73.md).

## Bestaande installatie bijwerken

1. Maak een volledige privé HA-back-up met instellingen, eigen opslag, modellen, tickets, geschiedenis en userfiles. Bewaar gecontroleerde beta.72-code.
2. Geef vóór codevervanging een eigen SG-aanvraag vrij en controleer contact/lokale afloop. Onderbreek geen beschermde apparaatcyclus.
3. Update via HACS naar exact `1.0.0-beta.73` na publicatie. Herstart HA volledig en herlaad browser/app volledig.
4. Controleer backend- en kaartversie apart. Behoud dezelfde entry, bindings, volgorde en geldige SG-/profiel-/split-/koelbevestigingen.
5. Controleer **Toegestane netafname vóór stopvertraging (W)**, **Netafname moet continu aanhouden (s)** en de aparte zonne-resetgrens, naast het behouden minimum/maximum.

Ontbreekt de nieuwe importoptie bij de oude standaardcombinatie 300 W/60 s, dan gebruikt de runtime effectief 600 W/300 s zonder automatische opslagwrite. Andere oude expliciete beleidscombinaties en aanwezige nieuwe importwaarden blijven behouden. Nieuwe configuratie gebruikt 600 W/300 s. De zonne-resetgrens blijft afzonderlijk, standaard 300 W.

Lokaal vervang je uitsluitend `custom_components/solar_pilot`, met behoud van userfiles en HA-opslag. Verwijder of hermaak de entry niet. Geen algemene herbevestiging of nieuwe verplichte bron.

## Vijf continue minuten en minimum twintig minuten

Alleen netafname strikt boven de ingestelde buffer begint de tekorttimer. Bij 600 W of lager wordt de standaardtimer gewist. Beginnend tekort in minuut 18 kan pas in minuut 23 gewone vrijgave geven. Zijn vijf minuten al vóór minuut 20 voltooid en blijft het tekort aanhouden, dan kan de actuele beoordeling bij het minimum meteen vrijgeven. Zonder tekort hoeft de aanvraag na twintig minuten niet te stoppen.

De minimumduur betreft de SG-aanvraag. Harde bron-/elektrische-/batterij-/koel-/voorrangsgrenzen, handmatige overname, geverifieerde native beëindiging, fouten en het behouden maximum kunnen eerder beëindigen. Panasonic bepaalt zelf compressorbedrijf; geen gegarandeerde compressorlooptijd of levensduur.

Korte lokale toestemming blijft standaard 300 s, veilig vernieuwd iedere 60 s tijdens geldige minimum- en wolkenwachttijd. Geen UIT/AAN-cyclus of lokale twintigminutentimer. Bij uitval kan zij eerder vervallen. Renewal/reload maken geen nieuw minimum of AAN-recht. Korter hardmax en bevestigingsreserve blijven leidend.

## Gegevens en rollback

Alle apparaten, gebruikerswaarden, modellen, tickets en geschiedenis blijven behouden. Panasonic-percentages, koelwaarden en programma's blijven ongewijzigd. Beta.71-wachtfasen en kalenderdag-export blijven behouden, met dertig dagen retentie apart van 1/24/168 uur en volledige grensdagtotalen zonder backfill.

Voor rollback: geef de eigen SG-aanvraag vrij, controleer lokale afloop, stop beta.73 en herstel gecontroleerde beta.72-code. Behoud entry, opslag en userfiles. Beta.72 kent de nieuwe importbuffer/leasevernieuwing tijdens wolkenwachttijd na het minimum niet; code alleen herstelt geen oude instellingenwaarden. Exact herstel vraagt code én passende volledige privéback-up; bewaar gewenste nieuwe historie eerst. Geen twee runtimes tegelijk. Volledige stappen: [BETA73_INSTELLEN.md](docs/BETA73_INSTELLEN.md).
