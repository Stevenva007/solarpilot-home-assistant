# SolarPilot 1.0.0-beta.53 — testresultaten

Datum: **2026-10-04**

## Bronbasis en gebruikersbewijs

Beta.52 op commit `80402cd03b213334608d4ca0956ce662c5021216`, tree `d1cb08369429a66773ad226c2642baac86aecf46` is de codebasis. Haar publicatie en beide pakketten zijn gecontroleerd: workflow `37212817359`, alle vier jobs geslaagd, vier release-assets, HACS-archief 318 bestanden en lokaal pakket 114 bestanden tegen de exacte tag gecontroleerd. Haar volledige softwaregate behaalde 2558 geslaagde tests lokaal in 22.09 s en in CI in 17.72 s. Deze eerdere resultaten zijn geen beta.53-testbewijs.

De actuele gebruikersbeelden tonen de beta.52-interface in Alleen bekijken, een herstartcontrole die wacht op een toestel en dat toestel als onbeschikbaar in HA. De gebruiker vraagt de overige regeling te laten hervatten en het toestel bij betrouwbare bronterugkeer automatisch opnieuw te regelen. Dit bewijst het zichtbare wachten en de toestelonbeschikbaarheid, niet hun fysieke oorzaak.

## Softwaregate

De definitieve volledige beta.53-suite behaalt **2671 geslaagde tests in 24.56 s**, nul fouten en nul overgeslagen tests, uitgevoerd met Python 3.12.14. Dit omvat alle behouden regressies en **113 nieuwe gevallen**: 35 runtime-/terugkeer-/opdrachtgrensgevallen, 23 faseveiligheidsgevallen, 31 warmwater-/batterij-/reservegevallen en 24 UI-/statusgevallen (19 kaartgevallen en vijf sensor-/exportgevallen).

De runtimegevallen controleren afzonderlijke herstartwacht en latere bronuitval, leasebehoud over opnieuw opslaan/herstarten, automatische terugkeer op echte adapterstatus, ON/OFF en gewijzigde numerieke doelen, minimumlooptijden, latere gebruikersmoduskeuze, echte opdrachtfouten en de actuele veilige opdrachtgrens. Reservegevallen controleren dat onbekende huidige of toekomstige lasten geen fictieve P1-, PV-, EV-, fase- of batterijruimte opleveren. Fasegevallen behouden actieve elektrische begrenzing bij onvolledig of ongeldig bewijs en veranderen advies-/uitgeschakelde modi niet in fysieke regeling. UI-/statusgevallen controleren de gerichte automatische melding zonder resetknop, onbekend in plaats van 0 W, afzonderlijke reserveringsinformatie en veilige tekstweergave.

Python-bronsyntax van **65 productiemodules**, JSON-syntax van **vier bestanden** en syntax van **beide JavaScript-bestanden** zijn geslaagd. `check_public_repository.py`, `check_handoff.py`, `check_current_explanation.py`, `validate_repository.py` en `git diff --check` zijn geslaagd.

De actuele uitleg en beide documentmirrors hebben hash `edf7d3b110363702`; optiehulp bevat **432 velden** voor beta.53. Het offline `SolarPilot-voorbeeld.html` is na bronfreeze opnieuw uit beta.53 opgebouwd met fictieve gegevens, zonder HA-contact of toestelopdracht. Het voorbeeld is een lokale gegenereerde weergave, geen hardwaretest.

De volledige browsergate en live Home Assistant-/hardwaretest zijn niet uitgevoerd. HA-API-/DOM-doubles bewijzen geen fysieke toestelverbinding, echte browser-HTTP-levering of nieuwe installatieacceptatie. De softwarewijziging claimt geen reparatie van de onderliggende verbindingsstoring.

## Publicatie en installatie

De afzonderlijke publicatiecontrole staat bij de [beta.53-release](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.53) en [Validate-workflow](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml). De workflow publiceert pas na geslaagde repository-, HACS- en Hassfest-jobs onder een nieuwe onveranderlijke tag. Beide pakketten worden afzonderlijk tegen die exacte tag gecontroleerd; beta.52-publicatiebewijs is geen beta.53-publicatiebewijs.

Bestaande instellingen, geldige leerdata, boilerbeleid, beschermde programma’s en volledig read-only Wallbox blijven behouden. Publicatie is geen bewijs van geïnstalleerde of geladen nieuwe appcode en geen fysieke acceptatietest.
