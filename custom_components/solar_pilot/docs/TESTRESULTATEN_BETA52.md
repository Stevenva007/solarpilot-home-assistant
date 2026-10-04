# SolarPilot 1.0.0-beta.52 — testresultaten

Datum: **2026-10-04**

## Bronbasis en gebruikersbewijs

Beta.51 op commit `89fbec5148a759a8b961c158d494104402419fbf`, tree `fe5b74446ee3991ed8fa478355c0307181b55bfb` is de codebasis. Haar publicatie en beide pakketten zijn gecontroleerd: workflow `37210746110`, alle vier jobs geslaagd, vier release-assets, HACS-archief 311 bestanden en lokaal pakket 112 bestanden tegen de exacte tag gecontroleerd. Oudere tags en releasebestanden blijven onveranderd; beta.51-resultaten zijn geen beta.52-testbewijs.

De gebruikersbeelden tonen een geopende beta.51-interface, eerst herstartwacht, daarna een foutmelding en tijdelijk herstelde automatische regeling. De eerdere analyse-export toont brononderbreking zonder opgeslagen pending opdracht of opdrachtfout. De live configuratie was read-only; de oude export markeerde de configuratie onterecht als niet-ondersteund en selecteerde daardoor niet alle expliciete bronentiteiten. Deze feiten bewijzen de diagnose-/exportdefecten, maar niet de fysieke oorzaak van de toestelverbindingsstoring of de oorzaak van een later screenshot dat na de export is gemaakt.

## Softwaregate

De definitieve volledige beta.52-suite behaalt **2558 geslaagde tests in 22.09 s**, nul fouten en nul overgeslagen tests, uitgevoerd met Python 3.12.14. Dit omvat alle behouden regressies en 37 nieuwe gevallen: 19 runtimegevallen, zes mapping/exportgevallen en twaalf UI-gevallen. De afzonderlijke gerichte uitvoering behaalt **37 geslaagd in 2.19 s**. Python-bronsyntax van **65 productiemodules**, JSON-syntax van **vier bestanden** en syntax van **beide JavaScript-bestanden** zijn geslaagd. `check_public_repository.py`, `check_handoff.py`, `check_current_explanation.py`, `validate_repository.py` en `git diff --check` zijn geslaagd.

De runtimegevallen controleren onderscheid tussen tijdelijke bronwacht, verkeerde vereiste broneigenschappen/koppelingen en echte opdrachtfouten, automatisch bronherstel en accurate weigering van een reset zonder resetrecord. Zij bewaken bestaande fysieke opdrachten, bronversheid, beschermde cycli en minimumlooptijden. UI-gevallen controleren automatische broncontrole zonder resetknop, gerichte configuratiemelding zonder resetknop, herstartmelding met bestaande voorrang en behoud van echte/legacy foutcontrole met veilig ge-escapete tekst. Mappinggevallen controleren effectieve read-only configuratie, recursieve expliciete entiteitsselectie, bronlimieten en bestaande privacy-/pseudonimiseringsregels.

Actuele uitleg en beide documentmirrors hebben hash `84be3bf69de3232c`; optiehulp bevat **432 velden** voor beta.52. Het offline `SolarPilot-voorbeeld.html` is opnieuw uit beta.52 opgebouwd met fictieve gegevens, zonder HA-contact of toestelopdracht. De volledige browsergate is niet uitgevoerd; HA-API-/DOM-doubles bewijzen geen echte browser-HTTP-levering of fysieke toestelverbinding. Er is geen live Home Assistant- of hardwaretest uitgevoerd.

## Publicatie en installatie

De afzonderlijke publicatiecontrole staat bij de [beta.52-release](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.52) en [Validate-workflow](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml). De workflow publiceert pas na geslaagde repository-, HACS- en Hassfest-jobs onder een nieuwe onveranderlijke tag. Beide pakketten worden afzonderlijk tegen die exacte tag gecontroleerd; beta.51-publicatiebewijs is geen beta.52-publicatiebewijs.

Geen live Home Assistant-installatie of fysieke toestelactie is in deze werksessie uitgevoerd. Alle eerdere boiler-, paneel- en veiligheidsregels blijven behouden. Een softwaregate wordt niet gelijkgesteld aan een fysieke verbindingsreparatie, geladen nieuw appbestand of aantoonbaar verdwijnen van elke latere foutmelding.
