# SolarPilot beta.88 — brongebonden test- en releaseverslag

Versie: **1.0.0-beta.88** · 15 oktober 2026

Bouwbasis: gepubliceerde beta.87-commit `a16a3f368149cf631cf7fb9a74247322e8f99232`, tree `9e03dbc6dd8368c2defaf270b7066dbbcf0d4c56`. Die eerdere release is herkomstbewijs en geen beta.88-validatie.

## Wijziging en bewijsgrenzen

Algemene en individuele Wallbox-voorrang gebruiken 30 min, 1/2/3/4/5 uur of een blijvende uitzondering tot Automatisch. Een algemene keuze kopieert naar bestaande ondersteunde flexibele toestellen en optionele SG; latere individuele wijziging blijft mogelijk. Algemeen Auto, handmatig of door afloop, wist alle individuele uitzonderingen. Individuele afloop is lokaal. De opgeslagen rangorde wordt niet herschreven. De afwasmachine heeft geen nieuwe schakelaar of voorkeursblokkering; haar bestaande startrecht en guards blijven gelden.

Absolute eindtijden blijven na reload/herstart staan en verlopen tijd krijgt geen volledige nieuwe duur. Oneindig toont uitsluitend tot ik terug op automatisch zet. De voorkeur volgt bestaande EV-vraag/hysterese/kleinoverschot/overdracht en verleent geen Wallbox-, native Panasonic- of batterijwrite, geen EV-credit voor SG en geen ruimere capaciteit of verkorte gewone minimumtijd. Alleen de nieuwe tijdelijke SG-voorkeursroute respecteert bij lopende aanvraag de bestaande oorspronkelijke bevestigde minimumduur en blokkeert een nieuwe start direct. Bestaande Wallbox-/EV-/harde-/koel-/bron-/manualOFF-/transport-/afwasguards blijven ongewijzigd en kunnen eerder vrijgeven. Bestaande SG-Aan/Uit, 20 min voor zachte import- en nieuwe voorkeursvrijgave, 600 W/300 s, leases en harde guards blijven vereist.

Publieke fixtures zijn fictief; geen privé-exports, woningwaarden, entiteiten of logs. Softwaretests bewijzen geen werkelijk aangesloten auto, geladen HA-code, fysieke start, compressorlooptijd, levensduurwinst of gerealiseerde besparing.

## Lokale uitvoering

De eerste volledige lokale beta.88-run eindigde met **6365 geslaagd, 10 mislukt, 627,02 seconden**. Dit is geen geslaagde volledige suite. De tien afwijkingen zijn herleid tot testfixtures: zeven bestaande constructorverwachtingen namen het nieuwe prioriteitsdialoogvenster nog niet mee; drie countdownverwachtingen gebruikten de echte lopende klok en verschilden daardoor één à twee seconden. De fixtures zijn aangepast aan het bedoelde dialoogvenster en een gedeelde vaste testklok; een oude bronleeftijd wordt aan dezelfde testklok verankerd. De productielogica is hiervoor niet gewijzigd. De laatste gerichte hercontrole is geslaagd: **128 tests, 0 mislukt, 51,75 s**. Zij omvat de gecorrigeerde negatieve-bronweergave, SG-wolken-/reset-/wacht-/minimumgevallen en panelgevallen.

De definitieve volledige suite moet vóór merge opnieuw slagen op de exacte PR-bron in CI. Een gerichte hercontrole vervangt die volledige suite niet. Eerdere beta.87-aantallen worden niet als beta.88-resultaat overgenomen.

| Controle | Status |
|---|---|
| Eerste volledige lokale beta.88-run | 6365 geslaagd; 10 mislukt; 627,02 s |
| Fixtureherstel; laatste gerichte hercontrole | 128 geslaagd; 0 mislukt; 51,75 s |
| Geselecteerde UI-/panelgevallen, inclusief 50 nieuwe voorkeursgevallen | 454 gevallen over gerichte runs afgedekt; geen claim van één volledige 454-pass-run |
| Definitieve volledige beta.88-suite op exacte PR-bron | Open; vereist vóór merge |
| Alle duren, countdown, blijvende tekst en algemene/individuele keuzes | Onderdeel van de vereiste volledige hercontrole |
| Absolute eindtijden bij reload/herstart en verlopen herstel | Onderdeel van de vereiste volledige hercontrole |
| Afwas uitgesloten; APP/deadline, gewone minimumtijden en bestaande SG-vrijgavegronden | Onderdeel van de vereiste volledige hercontrole |
| Opgeslagen volgorde, instellingen en read-only grenzen | Onderdeel van de vereiste volledige hercontrole |
| Guide/help/mirrors en overdracht | Geslaagd; 351 helpvelden; guidehash `61bd84d1b5795984` |
| Werkelijke UI-projectie, anonieme gekwalificeerde exportkeys en Recorder-grens | Onderdeel van de vereiste volledige hercontrole |
| Privacy/repository en SG-opdrachtgrens | Geslaagd |
| Beide frontendmodules, componentparse en diff | Geslaagd; Node 2, AST 88 Python / 3 JSON, diffcontrole |

De gids en beide spiegels volgen dezelfde bevroren productiesemantiek. De nieuwe tijdelijke SG-voorkeur blokkeert een nieuwe start en respecteert de oorspronkelijke bevestigde lopende minimumduur; bestaande vroege vrijgavegronden blijven gelden. Gerichte of overlappende testgroepen worden niet bij het volledige aantal opgeteld. De eerdere bredere selectie bevatte 453 geslaagde UI-/panelgevallen plus één resterende testklokafwijking; die afwijking is gecorrigeerd en zit in de geslaagde 128-hercontrole. Daarmee zijn de 454 geselecteerde gevallen over de gerichte runs afgedekt, inclusief 50 nieuwe Wallbox-voorkeursgevallen. Dit wordt niet voorgesteld als één foutloze run van 454 of een geslaagde volledige lokale suite.

**Echte Core 2026.10.0, Chromium en PowerShell zijn lokaal niet uitgevoerd.** Lokale doubles en oude releasechecks vervangen deze afzonderlijke CI-gates niet.

## CI en pakketbewijs

De vijf gates van [Validate](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml) moeten op dezelfde exacte releasebron slagen: repository/tests/PowerShell, HACS, Hassfest, echte Core en Chromium. Niet uitgevoerde gates blijven open. De workflow publiceert pas daarna de nieuwe immutable annotated tag.

Alle vier assets worden vóór upload en na terugdownload bytegelijk met dezelfde bron-SHA gecontroleerd:

- `SolarPilot-v1.0.0-beta.88-GitHub-HACS.zip`
- `SolarPilot-v1.0.0-beta.88-local.zip`
- `BETA88_INSTELLEN.md`
- `TESTRESULTATEN_BETA88.md`

Publicatie is pas bevestigd nadat **Download and verify published four assets against the exact tag** slaagt met `download_verified: true`. Dit verslag verzint geen toekomstig run-ID of geslaagde gate. Controleer tagcommit en push-run bij [release beta.88](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.88).

Upgrade en rollback naar beta.87: [BETA88_INSTELLEN.md](BETA88_INSTELLEN.md).
