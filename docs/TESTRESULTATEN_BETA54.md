# SolarPilot 1.0.0-beta.54 — testresultaten

Datum: **2026-10-04**

## Bronbasis en gebruikersbewijs

Beta.53 op commit `de4e7f364789ec486447b2c6ee5dce4cbabcbdb3`, tree `ea793e13fa35b8327c269f6754a76ef4c561ed72` is de codebasis. Haar publicatie en beide pakketten zijn gecontroleerd: workflow `37215861144`, alle vier jobs geslaagd, vier release-assets, HACS-archief 327 bestanden en lokaal pakket 116 bestanden tegen de exacte tag gecontroleerd. Haar volledige softwaregate behaalde 2671 geslaagde tests lokaal in 24.56 s en in CI in 20.31 s. Deze eerdere resultaten zijn geen beta.54-testbewijs.

De gebruikersbeelden tonen twee native UIT-zones, een wintercontext met Panasonic beschikbaar laten, en de melding dat de gebruiker zelf AUTO moet kiezen. De gebruiker vraagt dat SolarPilot iedere ruimte automatisch tussen AUTO en UIT regelt, onnodig ruimtebedrijf voorkomt, forecasts en echte woningrespons leert, en uitsluitend een dashboardschakelaar gebruikt voor bewuste handmatige bediening. Het getoonde leerpercentage bewijst geen gekalibreerde voorspelnauwkeurigheid of bouwschilrespons.

## Softwaregate

De definitieve volledige beta.54-suite behaalt **2877 geslaagde tests in 30.62 s**, uitgevoerd met Python 3.12. Dit omvat alle behouden regressies en **206 nieuwe beta.54-gevallen**: 64 modelgevallen, 58 runtimegevallen, 44 dashboardgevallen, 29 integratiegevallen en elf servicegevallen. Geen eerdere releasegate wordt als beta.54-bewijs gebruikt.

De beta.54-regressies controleren actuele en voorspellende per-zone behoefte, eerste native UIT zonder handmatige AUTO-fiets, onafhankelijkheid van zones, dashboardoverride en herstart, tijdelijke externe bescherming, relevante warm-/koelrespons, echte forecastdekking, eerlijke leer-/foutweergave en bescherming van pending/onzekere opdrachten. Aanvullende crash-/opslagregressies controleren dat een mislukte gerichte klimaatreview, tussentijdse native wijziging en mislukte tweede opslag de echte opdrachtbescherming over herstart behouden zonder actuatoraanroep. Alle behouden beta.53-isolatie-, reserve-, fase-, boiler-, afwas-, Wallbox- en levenscyclusgevallen blijven onderdeel van de samengestelde suite.

Python-bronsyntax van **65 productiemodules**, JSON-syntax van **vier bestanden** en syntax van **beide JavaScript-bestanden** zijn geslaagd. `check_public_repository.py`, `check_handoff.py`, `check_current_explanation.py`, `validate_repository.py` en `git diff --check` zijn geslaagd.

De actuele uitleg en beide documentmirrors hebben hash `3ddf7ab674c56053`; optiehulp bevat **437 velden** voor beta.54. Het offline `SolarPilot-voorbeeld.html` is na bronfreeze opnieuw uit beta.54 opgebouwd met fictieve gegevens, zonder HA-contact of toestelopdracht. Het voorbeeld is een lokale gegenereerde weergave, geen hardwaretest.

De volledige browsergate en live Home Assistant-/hardwaretest zijn niet uitgevoerd. HA-API-/DOM-doubles bewijzen geen fysieke thermische respons, compressoractie, echte browser-HTTP-levering of nieuwe installatieacceptatie. Bewuste bouwschilvoorconditionering over twee dagen wordt niet als fysiek geleerd of gegarandeerd geclaimd.

## Publicatie en installatie

De afzonderlijke publicatiecontrole staat bij de [beta.54-release](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.54) zodra gepubliceerd en de [Validate-workflow](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml). De workflow publiceert pas na geslaagde repository-, HACS- en Hassfest-jobs onder een nieuwe onveranderlijke tag. Beide pakketten worden afzonderlijk tegen die exacte tag gecontroleerd; beta.53-publicatiebewijs is geen beta.54-publicatiebewijs.

Bestaande instellingen, geldige leerdata, boilerbeleid, beschermde programma’s en volledig read-only Wallbox blijven behouden. Publicatie is geen bewijs van geïnstalleerde of geladen nieuwe appcode en geen fysieke acceptatietest.
