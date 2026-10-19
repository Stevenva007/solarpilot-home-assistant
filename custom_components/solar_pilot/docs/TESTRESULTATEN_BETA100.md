# SolarPilot beta.100 — test- en publicatieverslag

Versie: **1.0.0-beta.100** · 19 oktober 2026

Bouwbasis: gepubliceerde beta.99 `7d68ca9e15632ed41701a8806fd016c060687b0b`, tree `caeea7ce6362f051e7eacfc99848e31dc2b6f542`. Alle regressies gebruiken fictieve toestellen, bronnen en waarnemingen. Privélogboeken, installatiegegevens en persoonlijke bronidentiteiten worden niet opgenomen.

## Gerichte correctie en bewijsgrens

De drie getters voor beschikbaarheid, huidige keuze en attributen van `SGManualControl` vroegen elk het volledige SG-overzicht op. Dat volledige overzicht berekent ook Panasonic-informatie die deze select niet nodig heeft. Beta.100 leest beschikbaarheid via de bestaande `configured`-eigenschap en stand/duur/afloop via `SGBoostManager.manual_control_overview()`. Deze lichte publieke helper hergebruikt `_manual_overview()` met de huidige klok.

Elk van deze drie getters roept het volledige SG-/Panasonic-overzicht niet meer aan. Het aantal getteraanroepen per werkelijke HA-publicatie is niet gemeten; er wordt daarom geen vast aantal bespaarde berekeningen per publicatie of gemeten versnelling in seconden voor een gebruikersinstallatie geclaimd. De wijziging bevat geen SG-/controllercache, wijzigt geen actuele actiecontrole en bewijst geen oplossing voor andere statussensorvertragingen of externe integratiefouten.

## Te bewaken gedrag

- Beschikbaarheid blijft afhankelijk van geladen data, actieve entiteit/runtime en de bestaande geconfigureerde SG-koppeling.
- Automatisch en Aan/Uit voor 30/60 minuten behouden dezelfde keuzemapping. Ongeldige of onbekende keuzedata krijgt geen nieuwe geldige stand.
- Resterende duur volgt de huidige klok en dezelfde oorspronkelijke absolute eindtijd. Een uitlezing of nieuwe publicatie verlengt de keuze niet, wijzigt geen opslag en creëert geen nieuwe aanvraag.
- De bestaande expiry- en uitvoeringsroute houdt haar eigen betekenis. De lichte projectie geeft geen contactbevestiging, bronactualiteit, timerlease of actuatorrecht.
- De getters vragen geen volledig SG-/Panasonic-overzicht of fysieke apparaatopdracht. Handmatige bediening en bestaande actuele uitvoeringsvoorwaarden blijven afzonderlijk getest.
- Bronrechten, callback-/cachebewijs, SG-/Panasonic-bevoegdheden, minimum-/maximumtijden, profiel/koelguards, lokale timer, AEG-tickets, overige apparaten en bestaande datasets blijven behouden.
- Alle beta.99-historiefuncties en de bronvolgordecorrectie blijven onder de bestaande regressies vallen. Er is geen schemawijziging of datamigratie.

## Actuele upstreamcontrole

Op 18 oktober 2026 om **23:31:17 UTC** zijn alle acht GitHub-records opnieuw gecontroleerd. Aquarea v1.8.0/main/tag `8722cf22e5a5752406aea1ba79b2cf48d4deedf3` en SDK v1.4.0/main/tag `893065a81c014cb9aa1d3350446d61c01bccf3b9` zijn ongewijzigd sinds beta.99. Het nieuwe checkpoint vergelijkt dezelfde commits en vermeldt `no_additional_changes`. Daarna is ook de echte onlinecontrole `python -B tools/check_upstream_review.py` geslaagd. De historische inhoudelijke review blijft afzonderlijk bewaard; het actuele checkpoint staat in `UPSTREAM_BRONNEN.md` en `upstream_review.json`. Dezelfde onlinegate wordt vóór publicatie opnieuw in CI uitgevoerd; bronactualiteit geeft op zichzelf geen compatibiliteits- of installatiebewijs.

## Uitgevoerde validatie

- Gerichte code- en regressiecontrole: **180 tests geslaagd**, waaronder **19 nieuwe tests** voor deze correctie. De codewijziging is onafhankelijk nagekeken. Deze gerichte set vervangt de volledige suite en releasegates niet.
- Release-identiteit, gegenereerde gids-/optiehulp-/mirrors en overdrachtsdossier: **geslaagd** met `python -B tools/check_current_explanation.py` en `python -B tools/check_handoff.py`. Actuele gids: **36baa24f6491dc89**. Beide nieuwe releasedocumenten hebben bytegelijke componentmirrors. `git diff --check` is schoon.
- Privacy/structuur, Panasonic-/SG-grenzen, de actuele online-upstreamcontrole en Python-syntaxis van **94 componentbestanden**: **geslaagd**. De syntaxiscontrole schrijft geen bytecode.
- De volledige lokale suite onder Python 3.12.14 bleef zonder eindresultaat wachten en is onderbroken; dit is geen geslaagde volledige run. Een begrensde vergelijking met een schoon git-archive van beta.99 reproduceert dezelfde blokkade na dezelfde 29 geslaagde tests, bij het afsluiten van de standaardexecutor in de asyncio-fixtureteardown. Dit is geen nieuwe regressie van deze patch, maar verklaart niet welke executoractiviteit blijft wachten. De voorgeschreven volledige suite onder Python 3.13, PowerShell, echte Home Assistant Core 2026.10.0/Python 3.14.2, Chromium, HACS en Hassfest worden door de ongewijzigde Validate-workflow op deze bron uitgevoerd. De 7737 geslaagde tests van beta.99 zijn uitsluitend historisch bewijs.

## Publicatievoorwaarden en status

Dit verslag registreert het lokale bewijs vóór de CI-run. De brongebonden [Validate-uitvoer](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml) registreert de aanvullende resultaten; de [beta.100-release](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.100) verschijnt pas na geslaagde publicatie. Alle vijf Validate-gates moeten op de definitieve PR-bron slagen vóór merge: repository/privacy/documentatie, PowerShell en volledige testsuite; HACS; Hassfest; echte Home Assistant setup/reload/unload; Chromium. Dezelfde main-bron doorloopt de gates opnieuw vóór automatische publicatie.

De immutable annotated tag `v1.0.0-beta.100` moet naar de geteste main-commit wijzen. Vier releasebestanden worden vóór upload en na opnieuw downloaden bytegelijk met die bron gecontroleerd, inclusief grootte en SHA-256:

- `SolarPilot-v1.0.0-beta.100-GitHub-HACS.zip`
- `SolarPilot-v1.0.0-beta.100-local.zip`
- `BETA100_INSTELLEN.md`
- `TESTRESULTATEN_BETA100.md`

PR-/main-gates, tag en vier assetcontroles zijn alleen voltooid wanneer de gekoppelde runs dat voor de betreffende bron bevestigen; dit vooraf opgeslagen verslag loopt daarop niet vooruit. Bestaande tags en assets worden niet overschreven. De HACS-bewaarmap `userfiles`, bestaande configuratie-entry en eigen HA-opslag blijven behouden. Softwaretests en publicatie bewijzen geen live HA-installatie, fysieke Panasonic-/Shelly-reactie of werkelijk behaalde snelheid. Deze bewijssoorten worden afzonderlijk gerapporteerd.
