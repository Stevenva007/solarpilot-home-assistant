# SolarPilot beta.85 — brongebonden test- en releaseverslag

Versie: **1.0.0-beta.85** · 14 oktober 2026

Bouwbasis: gepubliceerde beta.84-commit `e83bc7027454af1366a490977ddcac70f37a215d`, tree `8f20df320827c54cb43d6d643cf93e95137da91b`. Die eerdere release is herkomstbewijs en geen beta.85-validatie.

## Gerichte wijziging

Een vroege lease-capreturn vóór plaatsing van de tijdelijke dispatchhook liet `callback` leeg. De cleanup kon daardoor de nog oorspronkelijke `before_on`-controle verwijderen, waarna volgende regelrondes een ontbrekend-attribuutfout kregen. De fix ruimt alleen een niet-lege hook op die door dezelfde aanroep is geplaatst en nog aan die aanroep toebehoort. De bestaande finale controle blijft intact.

Regressies moeten de capreturn vóór hookinstallatie, behoud van het originele attribuut op volgende rondes, werkelijke plaatsing/opruiming en finale native guard toetsen. Alle beta.84-temporarymode-/deadline-/restart-/startbuffer-/bron-/lease-/hardmax-/prioriteits-/API-/UI-regressies blijven vereist. Geen nieuwe policy, native writer, automatische fout-dismiss of opslagreset.

Een bestaande interne foutpauze blijft beschermd en vraagt na volledige HA-herstart een concrete controle, Controle afronden en daarna expliciet Automatisch regelen. Bestandsinhoud, backend- en geladen kaartversie zijn afzonderlijke bewijssoorten; dit verslag claimt geen bewezen lokale installatieoorzaak of gemengde modules. Alle publieke fixtures zijn fictief; privé-exports, entiteits-ID's, woningwaarden en logs zijn uitgesloten.

## Lokale uitvoering

De definitieve lokale beta.85-suite is geslaagd: **5888 tests, 0 mislukt, 124,73 seconden**, Python 3.12.14 / pytest 9.1.1. Dit omvat **15 nieuwe regressies** ten opzichte van beta.84: 8 backendgevallen, 6 onafhankelijke auditgevallen en 1 exacte catalogusbetekenis. Eerder beta.84-bewijs wordt niet als beta.85-resultaat overgenomen.

| Controle | Resultaat |
|---|---|
| Volledige definitieve beta.85-suite | 5888 geslaagd; 0 mislukt; 124,73 s |
| Gereproduceerde capreturn/cleanup en intacte finale controle | 8 backend- en 6 onafhankelijke nieuwe gevallen geslaagd |
| Oude cleanupconditie opnieuw gebruikt in geïsoleerde proef | 2 fouten / 4 geslaagd: regressies onderscheiden aantoonbaar de oude fout |
| Exact vertrouwd generiek voorstelregister | Nieuwe beta.85-betekenis getest; gerichte catalogusgroep 30 geslaagd |
| Behouden SG- en overige regressies | Geslaagd binnen volledige suite; gerichte groep 211 geslaagd |
| Guide/help/mirrors en overdracht | Actueel beta.85; 349 helpvelden; guidehash `b3f630b7a852a461` |
| Privacy/repository en SG-grens | Geslaagd |
| Beide frontendmodules en fictief voorbeeld | Node-syntax en opnieuw bouwen geslaagd |
| Component-Python en JSON | 86 Python-bestanden en 4 JSON-bestanden parsebaar |
| Diffcontrole en onafhankelijke review | Geslaagd; geen open blokkerende bevindingen |

De gerichte groepen overlappen de volledige suite en elkaar; hun aantallen worden niet opgeteld. De geïsoleerde proef met de oude cleanupconditie is uitsluitend tegenbewijs voor de gereproduceerde softwarefout, geen live-apparaatproef. Het vertrouwde register koppelt `sp.sg.native-callback-lifecycle.v1` alleen aan de exacte geïmplementeerde betekenis en beta.85; een adviesupload verleent geen nieuwe softwarestatus of apparaatpermission.

Echte Home Assistant Core 2026.10.0, Chromium en PowerShell zijn lokaal niet uitgevoerd. Hun vijf gezamenlijke releasegates, nieuwe tag en controle van vier teruggedownloade assets blijven open tot werkelijk brongebonden bewijs.

Echte Home Assistant Core 2026.10.0, Chromium en PowerShell zijn afzonderlijke CI-gates. Lokale doubles en oude releasechecks vervangen die niet. Softwaretests bewijzen geen geladen code, fysiek Shelly-timergedrag, compressorlooptijd, levensduurwinst of extra SG-warmteopname.

## CI en pakketbewijs

De vijf gates van [Validate](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml) moeten op dezelfde exacte releasebron slagen: repository/tests/PowerShell, HACS, Hassfest, echte Core en Chromium met de SG-bedieningsstap. Niet uitgevoerde gates blijven open. De workflow publiceert pas daarna de nieuwe immutable annotated tag.

Alle vier assets worden vóór upload en na terugdownload bytegelijk met dezelfde bron-SHA gecontroleerd:

- `SolarPilot-v1.0.0-beta.85-GitHub-HACS.zip`
- `SolarPilot-v1.0.0-beta.85-local.zip`
- `BETA85_INSTELLEN.md`
- `TESTRESULTATEN_BETA85.md`

Publicatie is pas bevestigd nadat **Download and verify published four assets against the exact tag** slaagt met `download_verified: true`. Dit verslag verzint geen toekomstig run-ID of geslaagde gate. Controleer de exacte tagcommit en push-run bij [release beta.85](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.85).

Upgrade, behoud en rollback naar beta.84: [BETA85_INSTELLEN.md](BETA85_INSTELLEN.md). Beta.84 behoudt de SG-bediening maar bevat deze gerepareerde fout.
