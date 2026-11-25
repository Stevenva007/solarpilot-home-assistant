# SolarPilot beta.120 — softwarevalidatie

## Gedrag en bewijsgrenzen

De regressies bouwen fictieve Home Assistant-registry-, config-entry-, device-, coordinator- en SDK-objecten voor het officiële `aquarea_smart_cloud`-domein. Zij toetsen dezelfde gesloten read-only LIVE-, identiteit-, waarde- en rapporttijdvoorwaarden als voor `aquarea`. Een gemengde registry-identiteit en twee gelijktijdig geladen providerdomeinen moeten gesloten blijven. De bestaande cloud-energieperiode behoudt haar oorspronkelijke UTC-grenzen.

De publieke broncontrole onderscheidt stabiele Aquarea v2.0.1, prerelease v3.0.0, de actuele defaultbranch na de revert, de ongewijzigde SDK v1.6.0 en niet-publiek bewijsbare lokaal geïnstalleerde software. Zij installeert of selecteert geen provider en verleent geen actuatorrecht.

## Lokale controles

Op 25 november 2026 slaagden **657 gerichte Aquarea-, native bronmetadata-, taakweergave- en energieperioderegressies in 4,61 seconden**. Daarna slaagde de volledige lokale suite met **9624 tests in 250,84 seconden** onder Python 3.12. Repositorystructuur/privacy, overdracht, actuele uitleg en optiehulp, online upstreamcheckpoint, SG-opdrachtgrens, Python- en JavaScript-syntax en de actuele voorbeeldbuild slaagden eveneens. De PowerShell-publicatieaudit is lokaal niet uitgevoerd omdat PowerShell hier niet aanwezig is; de gelijknamige GitHub-gate blijft verplicht.

## Verplichte publicatiecontrole

Alle vijf Validate-gates moeten op de exacte PR-HEAD slagen: repository en volledige testsuite, HACS, Hassfest, Chromium-interacties en echte Home Assistant-startup. Main herhaalt alle gates, maakt vervolgens tag en vier assets en vergelijkt de teruggedownloade pakketten met die exacte broncommit.

Een mislukte gate wordt niet met een los installatiepakket omzeild. Dit softwarebewijs bevat geen fysieke SG-/warmtepompproef en bewijst niet welke Aquarea- of SDK-versie op een woninginstallatie geladen is.
