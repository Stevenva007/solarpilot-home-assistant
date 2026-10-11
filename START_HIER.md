# SolarPilot beta.75 — installatie en upgrade

Beta.75 voegt lokaal automatisch onderzoek toe voor bestaande warmtepompmeters, Wallboxsessiebron, PV-voorspelling en toestelmetingen. Per onderwerp staan bewijs, mogelijke oorzaken, voorstellen en een volgende actie. De afzonderlijke SG-beoordeling benoemt wat nog ontbreekt om de regeling te beoordelen. De SG-regeling van 600 W gedurende vijf continue minuten met minimum twintig minuten, alle guards, instellingen en geschiedenis blijven behouden.

**Begin met [BETA75_INSTELLEN.md](docs/BETA75_INSTELLEN.md).** Daar staan de onderzoeksgrenzen, upgrade, behoud van de SG-regeling en rollback. Volledige werking: [ACTUELE_WERKING.md](docs/ACTUELE_WERKING.md) en **SolarPilot → Uitleg**. Software-/publicatiebewijs: [TESTRESULTATEN_BETA75.md](docs/TESTRESULTATEN_BETA75.md).

## Bestaande installatie bijwerken

1. Maak een volledige privé HA-back-up met instellingen, eigen opslag, modellen, tickets, geschiedenis en userfiles. Bewaar gecontroleerde beta.74-code.
2. Geef vóór codevervanging een eigen SG-aanvraag vrij en controleer contact/lokale afloop. Onderbreek geen beschermde apparaatcyclus.
3. Update via HACS naar exact `1.0.0-beta.75` na publicatie. Herstart HA volledig en herlaad browser/app volledig.
4. Controleer backend- en kaartversie apart. Behoud dezelfde entry, bindings, volgorde en geldige SG-/profiel-/split-/koelbevestigingen.
5. Bekijk **Meetkwaliteit → Automatisch onderzoek** of dezelfde sectie onder **Export → Analyse en advies**, bestaande dekking, SG-lagen en geschiedenis. Bestaande import-/zonne-resetgrenzen, minimum/maximum en korte leases blijven staan.

Onderzoek blijft lokaal en read-only. Alleen nieuwe werkelijke bruikbare bronrapporten leveren nieuwe meterwaarnemingen. Meer meetgegevens nodig, Controle nodig, Bron of functie niet ingesteld en Geen afwijking in deze metingen beschrijven het beschikbare bewijs; zij bewijzen geen fysieke installatie of toegepaste instelling. De export neemt de beschikbare onderzoeksstatus en voorstellen mee. Delen blijft een bewuste beheerderactie.

Lokaal vervang je uitsluitend `custom_components/solar_pilot`, met behoud van userfiles en HA-opslag. Verwijder of hermaak de entry niet. Geen algemene herbevestiging of nieuwe verplichte bron. Het onderzoek repareert geen meter, koppelt geen sensor en wijzigt geen instelling of Panasonic-programma.

## Vijf continue minuten en minimum twintig minuten

Alleen netafname strikt boven de ingestelde buffer begint de tekorttimer. Bij 600 W of lager wordt de standaardtimer gewist. Beginnend tekort in minuut 18 kan pas in minuut 23 gewone vrijgave geven. Zijn vijf minuten al vóór minuut 20 voltooid en blijft het tekort aanhouden, dan kan de actuele beoordeling bij het minimum meteen vrijgeven. Zonder tekort hoeft de aanvraag na twintig minuten niet te stoppen.

De minimumduur betreft de SG-aanvraag. Harde bron-/elektrische-/batterij-/koel-/voorrangsgrenzen, handmatige overname, geverifieerde native beëindiging, fouten en het behouden maximum kunnen eerder beëindigen. Panasonic bepaalt zelf compressorbedrijf; geen gegarandeerde compressorlooptijd of levensduur.

Korte lokale toestemming blijft standaard 300 s, veilig vernieuwd iedere 60 s tijdens geldige minimum- en wolkenwachttijd. Geen UIT/AAN-cyclus of lokale twintigminutentimer. Bij uitval kan zij eerder vervallen. Renewal/reload maken geen nieuw minimum of AAN-recht. Korter hardmax en bevestigingsreserve blijven leidend.

Ontbreekt de nieuwe importoptie bij de oude standaardcombinatie 300 W/60 s, dan gebruikt de runtime effectief 600 W/300 s zonder automatische opslagwrite. Andere oude expliciete beleidscombinaties en aanwezige nieuwe importwaarden blijven behouden. De zonne-resetgrens blijft afzonderlijk, standaard 300 W.

## Gegevens en rollback

Alle apparaten, gebruikerswaarden, modellen, tickets en geschiedenis blijven behouden. Panasonic-percentages, koelwaarden en programma's blijven ongewijzigd. Warmtepompgeschiedenis behoudt dertig lokale kalenderdagen apart van 1/24/168 rollende analyse-uren, met volledige geregistreerde kalenderdagtotalen en expliciete grensdagen, zonder backfill.

Voor rollback: geef de eigen SG-aanvraag vrij, controleer lokale afloop, stop beta.75 en herstel gecontroleerde beta.74-code. Behoud entry, opslag en userfiles. Dezelfde SG-regeling blijft gelden; Automatisch onderzoek vervalt. Code terugzetten corrigeert geen meter of fysieke toestand. Exact herstel vraagt code én passende volledige privéback-up; bewaar gewenste nieuwe historie eerst. Geen twee runtimes tegelijk. Volledige stappen: [BETA75_INSTELLEN.md](docs/BETA75_INSTELLEN.md).
