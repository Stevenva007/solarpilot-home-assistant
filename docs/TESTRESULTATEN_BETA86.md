# SolarPilot beta.86 — brongebonden test- en releaseverslag

Versie: **1.0.0-beta.86** · 14 oktober 2026

Bouwbasis: gepubliceerde beta.85-commit `c9b3a1cce40fa60301d6e7a3bced4351a6b9f8cf`, tree `166ca0498702ed2f1657880cc29da86ddcb920f7`. Die eerdere release is herkomstbewijs en geen beta.86-validatie.

## Gerichte wijziging en bewijsgrenzen

Uitsluitend een lokaal bevestigd GENERAL-profiel met `response_unknown` krijgt aanvullend `fresh_residual_surplus`: na bestaande rust (default 900 s), over 300 s minstens twee nieuwe originele verse bruikbare rapporten met daadwerkelijk resterend overschot vanaf `max(threshold_w, expected_power_w)`, daarna de normale startvertraging (default 120 s). Geen warmtepompcredit, parallel rustkrediet, oude herlezen samples of herstart als nieuw bewijs.

`no_uptake`, `native_completed`, `session_limit`, `profile_changed`, DHW-only en echte manual/transport/safety-holds behouden hun bestaande voorwaarden. Optionele HP-watts geven bij ontbreken, partial, stale of invalid geen credit, totale energie of nul; de volledige conservative expected-extra blijft gereserveerd. Essential net/PV/battery/phase/cooling/contact/timerproof moet actueel en bruikbaar blijven. Terugkerende bronnen worden op hun nieuwe kwaliteit beoordeeld; geen permanente skip, terugvullen of automatische tekenomkering. Verse negatieve watts blijven ongeldig en geven geen bewezen fysieke meterafwezigheid of oorzaak.

Een aanvullende uitsluitend voor presentatie bedoelde Aquarea-contractcorrectie gebruikt de actuele getypeerde providerstatus/-tank wanneer door dubbele fetch oudere zoneobjecten naar een eerdere momentopname blijven wijzen. Getypeerde huidige waarden, vastgelegde poll, gecontroleerde registrybindingen en verse HA-bronovereenkomst blijven vereist. Onbekend of conflict wordt niet vertrouwd. Native uitlezing, `_legacy_status`, `read()`, SG-koelguards, andere bediening en historische classificaties veranderen niet; providerobjecten worden niet gemuteerd.

De beta.85-callbackfix, beta.84-manual30/60-/deadline-/Auto-/restart-/startgap300-regels, min20/import600/300, hardmax, lokale lease en alle overige apparaten/gegevens blijven behouden. Geen nieuwe quota, configuratie, native writer, fout-dismiss of causaal warmtebewijs. Publieke fixtures zijn fictief; geen privé-exports, woningwaarden, entities of logs.

## Lokale uitvoering

De definitieve lokale beta.86-suite is geslaagd: **6012 tests, 0 mislukt, 122,53 seconden**, Python 3.12.14 / pytest 9.1.1. Dit omvat **124 nieuwe regressies** ten opzichte van de 5888 beta.85-gevallen: 20 backend, 33 onafhankelijke SG-audit, 40 kaart, 4 Aquarea-broncontract, 25 onafhankelijke Aquarea-audit en 2 exacte catalogusbetekenissen. Oudere resultaten worden niet als beta.86-validatie overgenomen.

| Controle | Resultaat |
|---|---|
| Volledige definitieve beta.86-suite | 6012 geslaagd; 0 mislukt; 122,53 s |
| Alleen GENERAL/response_unknown, rust → verse restzon → gewone startvertraging | Geslaagd binnen de volledige suite |
| Twee originele rapporten, tijd/bronactualiteit, tekort/binding-reset | Geslaagd binnen de volledige suite |
| Optionele HP-watts zonder credit, terugkeer en essential/hardguards | Geslaagd binnen de volledige suite |
| Actuele getypeerde Aquarea-poll versus oude zoneobjecten, binding/overeenkomst en strict unknown | Eigen en onafhankelijke regressies geslaagd |
| Behoud andere holds en alle beta.85-/beta.84-regressies | Geslaagd binnen de volledige suite |
| Onaangeroerde native-/koel-/controlegrens | 11 beschermde methoden AST-gelijk aan bouwbasis |
| Bronproef met ongewijzigde upstreamklassefuncties | Offline en synthetisch geslaagd; geen apparaat- of netwerkproef |
| Vertrouwde generieke catalogus | 2 nieuwe exacte betekenissen getest; gerichte groep 32 geslaagd |
| Guide/help/mirrors en overdracht | Actueel beta.86; 349 helpvelden; guidehash `df4fbe0028f67012` |
| Privacy/repository en SG-grens | Geslaagd |
| Beide frontendmodules, fictief voorbeeld en componentparse | Node2, voorbeeldbuild, 86 Python / 4 JSON geslaagd |
| Diffcontrole en onafhankelijke review | Geslaagd; geen open blokkerende bevindingen |

Gerichte groepen zijn afzonderlijk uitgevoerd: 1416 SG-, 386 UI-, 403 native-, 183 onafhankelijke native- en 32 catalogusgevallen. Deze groepen overlappen de volledige suite en elkaar; hun aantallen worden niet opgeteld.

De offline bronproef gebruikt ongewijzigde upstreamklassefuncties met uitsluitend synthetische invoer: een ouder zoneobject behoudt A-waarden terwijl de laatste getypeerde status B-waarden draagt. De oude verifier verwerpt deze vernieuwde B-snapshot; de nieuwe uitsluitend voor presentatie bedoelde reader gebruikt de actuele B-velden met dezelfde gecontroleerde bewijsgrenzen. De afzonderlijke vendor-/probe-bestanden worden niet gepubliceerd. Vastgepinde publieke herkomst staat in [UPSTREAM_BRONNEN.md](UPSTREAM_BRONNEN.md). Geen geval levert fysieke warmte-, meter- of compressoracceptatie.

De kaartregressies onderscheiden de 300 s restzonbevestiging van gewone startvertraging, nul resterend zonder vers eindbewijs, werkelijk gemeten nul van verse negatieve/ongeldige bron, oorspronkelijke afkeurreden/tijd en verval van uitleg of bewijs. Echte Chromium blijft de afzonderlijke CI-gate.

**Echte Core 2026.10.0, Chromium en PowerShell zijn lokaal niet uitgevoerd.** De vijf CI-gates, tag en controle van vier teruggedownloade assets blijven open tot daadwerkelijk brongebonden bewijs.

Echte Core 2026.10.0, Chromium en PowerShell zijn afzonderlijke CI-gates. Lokale doubles en oudere releasechecks vervangen die niet. Softwaretests bewijzen geen geladen HA-code, Shelly-timergedrag, fysiek goede meteraansluiting, compressorlooptijd, levensduurwinst of extra SG-warmteopname.

## CI en pakketbewijs

De vijf gates van [Validate](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml) moeten op dezelfde exacte releasebron slagen: repository/tests/PowerShell, HACS, Hassfest, echte Core en Chromium met SG-bediening. Niet uitgevoerde gates blijven open. De workflow publiceert pas daarna de nieuwe immutable annotated tag.

Alle vier assets worden vóór upload en na terugdownload bytegelijk met dezelfde bron-SHA gecontroleerd:

- `SolarPilot-v1.0.0-beta.86-GitHub-HACS.zip`
- `SolarPilot-v1.0.0-beta.86-local.zip`
- `BETA86_INSTELLEN.md`
- `TESTRESULTATEN_BETA86.md`

Publicatie is pas bevestigd nadat **Download and verify published four assets against the exact tag** slaagt met `download_verified: true`. Dit verslag verzint geen toekomstig run-ID of geslaagde gate. Controleer tagcommit en push-run bij [release beta.86](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.86).

Upgrade, noodzakelijke/aanvullende bronnen en rollback naar beta.85: [BETA86_INSTELLEN.md](BETA86_INSTELLEN.md).
