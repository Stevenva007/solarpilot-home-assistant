# SolarPilot beta.87 — brongebonden test- en releaseverslag

Versie: **1.0.0-beta.87** · 14 oktober 2026

Bouwbasis: gepubliceerde beta.86-commit `d1e64c816b5ed4ebb2ccc866ef7efa949185fc23`, tree `fd936c26b37bce51fa0ec7754a59596bfcd0177d`. Die eerdere release is herkomstbewijs en geen beta.87-validatie.

## Gerichte wijziging en bewijsgrenzen

Alleen toegewezen HP-consumptionmeters krijgen na gewone bron-/eenheids-/actualiteits-/quality-/range-/overlap-/dekkingscontrole negatieve-naar-nulnormalisatie. Verse finite W/kW-negatief binnen het bestaande plausibele bereik wordt 0 W bruikbaar; oorspronkelijke `source_value`, ruwe watts en normalisatiemarkering blijven diagnostisch beschikbaar.

Missing/stale/future/NaN/infinite/estimated/restored/overlap/incomplete of verkeerde eenheid blijft unknown. Eén ontbrekende voeding maakt het totale paar niet compleet. P1/net/export/PV/battery/phase worden niet geclipt of omgetekend. Geen historiek-/exportrewrite, bewezen calibratie/wiring of causale warmteclaim. De nul is expliciet gebruikersbeleid voor verbruiksinterpretatie.

Alle beta.86-GENERAL/response_unknown-restzon-/SDK-display-/andere holds/koelguards, beta.85-callbackfix en beta.84-manual/deadline/Auto/startgap/restart/lease/min20/import600/300 blijven vereist. Geen nieuw actuatorrecht, native writer, configuratiereset of faultdismiss. Publieke fixtures zijn fictief; geen privé-exports, woningwaarden, entities of logs.

## Lokale uitvoering

De definitieve lokale beta.87-suite is geslaagd: **6109 tests, 0 mislukt, 126,22 seconden**, Python 3.12.14 / pytest 9.1.1. Dit omvat **97 nieuwe gevallen** ten opzichte van de 6012 beta.86-gevallen: 29 backend, 46 onafhankelijke audit, 21 kaart en 1 exacte catalogusbetekenis. Eerder beta.86-bewijs wordt niet als beta.87-resultaat overgenomen.

| Controle | Resultaat |
|---|---|
| Volledige definitieve beta.87-suite | 6109 geslaagd; 0 mislukt; 126,22 s |
| HP-negatief W/kW→nul na gewone validatie; raw en marker behouden | Geslaagd binnen volledige suite |
| Echt ontbrekend/ongeldig en incomplete dekking blijven unknown | Geslaagd binnen volledige suite |
| Net/export/PV/battery/phase tekens en overige guards behouden | Geslaagd binnen volledige suite |
| Historie/exports niet teruggevuld en alle behouden regressies | Geslaagd binnen volledige suite |
| Onderzoeksuitleg met geïnterpreteerde nul en originele bronfeiten | Geslaagd binnen volledige suite |
| Exact generiek voorstelregister | Nieuw beta.87-geval geslaagd binnen volledige suite |
| Guide/help/mirrors en overdracht | Actueel beta.87; 349 helpvelden; guidehash `72874ff73ad5d56e` |
| Privacy/repository en SG-grens | Geslaagd |
| Beide frontendmodules, componentparse en diff | Node2, 86 Python / 4 JSON en diffcontrole geslaagd |

De 97 nieuwe gevallen zijn onderdeel van het volledige aantal; overlappende gerichte groepen worden niet opgeteld. Kaartgevallen tonen alleen geldig door de backend genormaliseerde nul, met `normalized` en `normalization_reason=negative_as_zero`. Details bewaren oorspronkelijke `source_value`, eenheid en oorspronkelijke rapporttijd. Verlopen bronbewijs verbergt compact nul en houdt de oorspronkelijke diagnose als niet actueel; missing/rejected krijgt geen normalisatieclaim. De frontend voert geen zelfstandige signflip uit. Het onderzoeksopschrift onderscheidt geïnterpreteerde nul van originele ruwe bronfeiten.

**Echte Core 2026.10.0, Chromium en PowerShell zijn lokaal niet uitgevoerd.** Vijf CI-gates, tag en vier teruggedownloade assets blijven open tot daadwerkelijk brongebonden bewijs.

Echte Core 2026.10.0, Chromium en PowerShell zijn afzonderlijke CI-gates. Lokale doubles en oude releasechecks vervangen die niet. Softwaretests bewijzen geen geladen HA-code, Shelly-timergedrag, goede fysieke meteraansluiting, compressorlooptijd, levensduurwinst of extra SG-warmteopname.

## CI en pakketbewijs

De vijf gates van [Validate](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml) moeten op dezelfde exacte releasebron slagen: repository/tests/PowerShell, HACS, Hassfest, echte Core en Chromium met SG-bediening. Niet uitgevoerde gates blijven open. De workflow publiceert pas daarna de nieuwe immutable annotated tag.

Alle vier assets worden vóór upload en na terugdownload bytegelijk met dezelfde bron-SHA gecontroleerd:

- `SolarPilot-v1.0.0-beta.87-GitHub-HACS.zip`
- `SolarPilot-v1.0.0-beta.87-local.zip`
- `BETA87_INSTELLEN.md`
- `TESTRESULTATEN_BETA87.md`

Publicatie is pas bevestigd nadat **Download and verify published four assets against the exact tag** slaagt met `download_verified: true`. Dit verslag verzint geen toekomstig run-ID of geslaagde gate. Controleer tagcommit en push-run bij [release beta.87](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.87).

Upgrade en rollback naar beta.86: [BETA87_INSTELLEN.md](BETA87_INSTELLEN.md).
