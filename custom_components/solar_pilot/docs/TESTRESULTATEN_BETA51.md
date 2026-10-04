# SolarPilot 1.0.0-beta.51 — testresultaten

Datum: **2026-10-04**

## Bronbasis en gebruikersbewijs

Beta.50 op commit `5348ecaedd75326debc3b60764ab711882adf446`, tree `e67da41e0928a25b73893216edf34be6ff0ce5bc` is de codebasis. Beta.50 is werkelijk gepubliceerd en haar pakketten zijn gecontroleerd; oudere tags en releasebestanden blijven onveranderd. De historische 2511 beta.50-tests worden niet als nieuwe beta.51-uitvoering opgevoerd.

Het aangeleverde scherm toont een **Unable to load custom panel**-melding voor de beta.50-kaart-URL. Dit is geen bewijs van de exacte live HTTP-status, bestandsinhoud of WebView-oorzaak. De codeaudit toont twee afzonderlijke problemen bij herladen: herhaalde klassieke scriptlading van verschillende release-URL's botst op globale declaraties, terwijl modules afzonderlijke scopes hebben; nieuwe module-URL's konden dubbele SolarPilot-catalogusitems toevoegen. Die bevindingen bewijzen niet dat zij de specifieke aangeleverde laadmelding veroorzaakten.

## Softwaregate

De definitieve volledige beta.51-suite behaalt **2521 geslaagde tests in 18.76 s**, nul fouten en nul overgeslagen tests, uitgevoerd met Python 3.12.14. Dit omvat de tien nieuwe module-/frontendregistratiegevallen en alle behouden beta.50-regressies. Python-bronsyntax van **65 productiemodules**, JSON-syntax van **vier bestanden** en syntax van **beide JavaScript-bestanden** zijn geslaagd.

`check_public_repository.py`, `check_handoff.py`, `check_current_explanation.py`, `validate_repository.py` en `git diff --check` zijn geslaagd. Actuele uitleg en beide documentmirrors hebben hash **`7f0c9817f8b1c53a`**; optiehulp bevat **432 velden** voor beta.51. Het offline `SolarPilot-voorbeeld.html` is opnieuw uit beta.51 opgebouwd met fictieve gegevens, zonder HA-contact of toestelopdracht. De volledige browsergate is niet uitgevoerd: de benodigde Chromium-executable ontbreekt. Er is geen live Home Assistant- of client-HTTP-test uitgevoerd.

Vijf gevallen evalueren de echte kaartbron als ES module met Node DOM-doubles: eenmalig laden, herhaald evalueren van dezelfde module, een volgende module-URL, klassieke legacykaart gevolgd door een module en gericht opruimen van eigen bestaande catalogusduplicaten. Zij controleren enkelvoudige custom-elementregistratie, behoud van de gedeelde catalogus en andere integraties, paneelconstructie via directe HA-properties, listeners bij verbinden/loskoppelen en nul fysieke serviceaanroepen. Dezelfde module opnieuw evalueren modelleert een reeds geladen modulerecord; het is geen HTTP-cachetest.

Vijf frontendregistratiegevallen gebruiken de echte Python-module met HA-API-doubles. Zij controleren registratie van het gebundelde bestand vóór publicatie van dezelfde kaart-/paneelmodule-URL, aanwezigheid van het juiste releasebestand en hulpbestanden, herhaald registreren zonder dubbele static route of extra module, definitieve verwijdering met behoud van andere integraties en veilig opnieuw proberen na een mislukte static registratie. Dit is softwarebewijs; geen volledige browser, echte client-HTTP-levering, WebView-cache of live Home Assistant-installatie.

## Publicatie en installatie

De afzonderlijke publicatiecontrole staat bij de [beta.51-release](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.51) en [Validate-workflow](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml). De workflow publiceert pas na geslaagde repository-, HACS- en Hassfest-jobs onder een nieuwe onveranderlijke tag. Beide pakketten worden afzonderlijk tegen die exacte tag gecontroleerd; beta.50-publicatiebewijs is geen beta.51-publicatiebewijs.

Geen live Home Assistant-installatie, geladen beta.51-appkaart of fysieke toestelactie is in deze werksessie uitgevoerd. Alle beta.50-boiler- en veiligheidsregels blijven behouden. De softwaregate wordt niet gelijkgesteld aan de bewezen specifieke oorzaak of het verdwijnen van de aangeleverde live laadmelding.
