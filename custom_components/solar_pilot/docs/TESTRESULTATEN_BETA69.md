# SolarPilot 1.0.0-beta.69 — testresultaten

Datum: **2026-10-11**. Bouwbasis: gepubliceerde beta.68, commit `bb8852d6516fd6df4b79a5dac79263648b2e4499`. Oudere releaseuitslagen zijn geen nieuwe validatie. Alle fixtures zijn fictief; de private analysegegevens worden niet gepubliceerd.

## Actuele validatie

| Lokale controle | Werkelijk resultaat |
| --- | --- |
| Volledige beta.69 pytest, Python 3.12 | **3829 geslaagd in 60,40 s**. |
| Nieuwe regressies ten opzichte van beta.68 | **179 extra cases**, onderdeel van de volledige suite. |
| Guide/hash/help en documentmirrors | **Geslaagd**, guidehash `7f82db61e5b8d185`. |
| Privacy-/publieke repositorypreflight | **Geslaagd**; geen persoonlijke exportidentiteiten in wijzigingen. |
| Handoff, SG-bevoegdheidsgrens, structuur en diff | **Geslaagd**. |
| JavaScript-syntax en Python-AST | **Geslaagd**, alle 72 productie-Pythonbestanden geparsed. |
| Exacte vertrouwde voorstelvingerafdrukken | Vier exacte logische voorstellen herkennen beta.69 als geïmplementeerd. |

De eerste gewijzigde full-suite gaf één verouderde frontend-helperversiekop aan; die is gecorrigeerd en de hierboven genoemde volledige run slaagt. Gerichte suites en scenario's worden niet opnieuw bij de full-suite opgeteld. De baseline was afzonderlijk 3650 cases; dat is geen beta.69-validatie. Lokale pytestdoubles zijn geen echte Home Assistant Core-entryproef; die is een aparte CI-gate.

De gerichte nieuwe regressies toetsen SG-eligibiliteit inclusief complete gemeten HP-bijdrage, fysiek restoverschot, PV-cap, import/batterij/reserves, single/split/nul/overlap/stale, EV-prioriteit, definitieve dispatch en behoud van lokale toestemming. Zij toetsen daarnaast onafhankelijk tankbereik bij native OFF, globaal UIT, conflicten/ontdooien, heater-only/partiële bronnen, exacte bronafkeur, native versus afgeleid leren, archiefbehoud en frontend/exportprovenance. Een test met meerdere scenario's blijft één pytestcase.

## CI en publicatiegates

De bestaande workflow toetst vijf gates: repository/full suite, HACS, Hassfest, echte Home Assistant Core 2026.10 setup/reload/unload en echte browser op 320/390/768/1280 px. Pas na vijf geslaagde actuele gates kan de bestaande main-workflow publiceren. GitHub Actions registreert de exacte SHA en afzonderlijke gateuitslagen bij [Actions](https://github.com/Stevenva007/solarpilot-home-assistant/actions).

Publicatie bouwt beide ZIPs uit de exacte commit, maakt alleen een nieuwe annotated tag en controleert alle vier assets vóór en na upload op ledenlijst, bronbytes, grootte en SHA-256. De [beta.69-release](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.69) bestaat pas na deze gates. Dit verslag claimt geen toekomstige uitvoering daarvan.

## Grenzen van het bewijs

Geen live huishoudelijke Home Assistant-installatie of fysieke SG-/Panasonicproef is uitgevoerd. Tests/CI bewijzen geen werkelijke klepstand, warmteproductie, COP, meterbedrading, condensveiligheid, extra SG-verbruik of causale oorzaak van historische tankafkoeling/stilstand. De automatische schema-/modelbehoudproeven vervangen geen volledige privéback-up. `via_device`-compatibiliteit vóór HA 2027.8 blijft een afzonderlijk open punt.

Native Panasonic-regeling blijft read-only; één bestaande toegewezen SG-uitgang blijft de warmtepompactuator. Bestaand HP-verbruik verlaagt de aparte conservatieve extra-vraagraming niet en geeft geen elektrische headroom of EV-credit. Rapportimport blijft bron-/revisiegebonden informatie. Installatie en rollback: `BETA69_INSTELLEN.md`.
