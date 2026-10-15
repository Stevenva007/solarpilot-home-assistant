# SolarPilot beta.89 — brongebonden test- en releaseverslag

Versie: **1.0.0-beta.89** · 15 oktober 2026

Bouwbasis: gepubliceerde beta.88-commit `cd334cc779f78634e24aa4244128eacd4fad4040`, tree `956e2ae8558db13c908fcac032a0c043932541d7`. Die eerdere release is herkomstbewijs en geen beta.89-validatie.

## Wijziging en bewijsgrenzen

Gewone onderbreekbare `switch`-, `number`- en gecontroleerde `script`-lasten mogen werkelijk resterende zon benutten zonder de volledige toekomstige afwaspiek nogmaals van hun zachte zonnebudget af te trekken. Dit vereist een betrouwbare actuele actieve native afwasstatus, geen gekoppelde afwasvermogensmeter en geen bronisolatie. Een gekoppelde maar onbruikbare meter, onbekende status of beschermd doel geeft geen versoepeling. De conservatievere actuele/gefilterde P1-zonnepot na huisreserve en batterijontlading blijft leidend.

De volledige toekomstige piekraming blijft binnen de totale elektrische net-/kwartierberekening gereserveerd. Bestaande fasecontroles veranderen niet en geven zonder meting geen bekend toekomstig faseprofiel. Andere comfort-/isolatie-/onbevestigde SG-reserves blijven staan. SG, beschermde en niet-onderbreekbare lasten behouden hun bestaande strengere zonneberekening. Bronbewijs en beschikbare ruimte worden vóór en na wachtende opdrachtopslag opnieuw beoordeeld. Minimumtijden, start-/stopbuffers, voorrangsregels, APP-ticket/deadline en maximaal één START blijven gelden. Er ontstaat geen Wallbox-, Panasonic- of afwas-stoprecht.

De kaart onderscheidt de gehele toekomstige piek, het voor dit toestel versoepelde zonnedeel, de werkelijk toegepaste zonnedekking en elektrische ruimte. Een geraamde afwaspiek wordt geen gemeten actueel verbruik. Een latere verwarmingspiek kan tijdens bestaande minimumtijd/stopbuffer tijdelijk netafname geven; geen nulimportgarantie.

Publieke fixtures zijn fictief. Geen privé-exports, woningwaarden, entiteiten of logs worden toegevoegd. Softwaretests bewijzen geen geladen gebruikersinstallatie, fysieke afwasfase, werkelijke start, zekeringbeveiliging of gerealiseerde besparing.

## Uitvoering

De volledige lokale beta.89-suite is op de bevroren productiecode uitgevoerd: **6470 geslaagd, 0 mislukt, 533,61 s**, met procesuitgang 0. Deze run omvat de behouden 6375 gevallen en 95 nieuwe backend-, onafhankelijke en UI-gevallen. De laatste nieuwe fixtures gebruiken zelfstandig gekozen fictieve waarden en geen woninggegevens. Latere verslagcorrecties veranderen uitsluitend resultaatproza; de definitieve exacte PR-head moet nog alle vijf CI-gates doorstaan.

| Controle | Werkelijk lokaal resultaat |
|---|---|
| Volledige beta.89-testsuite | **6470 geslaagd; 0 mislukt; 533,61 s; procesuitgang 0** |
| Laatste nieuwe backendselectie met definitieve fictieve fixtures | 22 geslaagd; 0 mislukt; 0,65 s |
| Laatste onafhankelijke negatieve/race-/grensgevallen | 40 geslaagd; 0 mislukt; 1,66 s |
| Eerdere gecombineerde allocatie-/dispatch-/bronselectie | 261 geslaagd; 0 mislukt; 18,89 s. Inclusief nieuwe backend- en auditgevallen; niet bij de volledige suite optellen. |
| Definitieve UI-selectie | 140 geslaagd; 0 mislukt; 140,61 s. 33 nieuwe reservegevallen, 28 bestaande audit-, 29 overzichtdetail- en 50 Wallbox-voorkeursgevallen. |
| Canonieke gids, optiehulp, spiegels en overdracht | 20 gids-/helptests geslaagd; 0 mislukt; 0,47 s. Generatie/consistentie en drie bytegelijke documentparen gecontroleerd; 351 helpvelden; guidehash `8b0d496ee6271935`. |
| Privacy/repository en Panasonic-/SG-opdrachtgrens | Geslaagd |
| Beide frontendmodules, Python-/JSON-parse en diff | Geslaagd; 89 componentmodules en 4 JSON-bestanden; Node kaart/optiehulp en diffcontrole. |
| HACS, Hassfest, echte Core en Chromium op exacte PR-head | Nog open; vereist vóór merge |
| Annotated tag en vier teruggedownloade releasebestanden | Nog open |

De eerdere kleinere UI-selectie gaf 61 geslaagd in 31,23 s; de definitieve 140-selectie en volledige suite vervangen die als laatste uitvoeringsbewijs. Gerichte overlappende groepen worden niet opgeteld bij 6470. Oudere beta.88-resultaten worden niet als beta.89-validatie gepresenteerd.

**Echte Core, Chromium en PowerShell zijn lokaal niet uitgevoerd.** De nieuwe browsercontrole voor deze reserve-uitleg en de bestaande controles moeten afzonderlijk in de vereiste CI-gates slagen. Lokale doubles en Node-tests vervangen die niet. Softwaretests bewijzen geen fysieke afwasfase, daadwerkelijke gebruikersinstallatie of nulimport.

## Vereiste regressiegrenzen

- Voldoende echte restzon voor een geschikte gewone last, maar behoud van de gehele toekomstige piek binnen de totale elektrische ruimte.
- Geen versoepeling bij oude/onbekende/geïsoleerde afwasstatus, gekoppelde maar onbruikbare afwasmeter, onbetrouwbare P1/PV, verkeerde bindings of ongeldige waarden.
- Geen extra zonnecredit voor batterijontlading, eerdere toewijzingen, onbekende apparaten, SG of andere beschermde reserves.
- Onveranderde minimumtijden, start-/stopbuffers, vraag/interlock/eigenaarschap, Wallbox-voorrang, beschermde afwascyclus en deadline.
- Nieuwe bron-/status-/ruimtewijziging tijdens opslag voorkomt een inmiddels ongeldige, aantoonbaar niet-verzonden start; een onzekere verzonden opdracht krijgt geen blind retry.
- Dezelfde backendvelden dragen kaart, export en diagnose; geschatte piek en gemeten verbruik blijven onderscheiden.

## CI en pakketbewijs

De vijf gates van [Validate](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml) moeten op dezelfde exacte releasebron slagen: repository/tests/PowerShell, HACS, Hassfest, echte Core en Chromium. De workflow publiceert pas daarna de nieuwe immutable annotated tag.

Alle vier assets worden vóór upload en na terugdownload bytegelijk met dezelfde bron-SHA gecontroleerd:

- `SolarPilot-v1.0.0-beta.89-GitHub-HACS.zip`
- `SolarPilot-v1.0.0-beta.89-local.zip`
- `BETA89_INSTELLEN.md`
- `TESTRESULTATEN_BETA89.md`

Publicatie is pas bevestigd nadat **Download and verify published four assets against the exact tag** slaagt met `download_verified: true`. Dit verslag verzint geen toekomstig run-ID of geslaagde gate. Controleer tagcommit en push-run bij [release beta.89](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.89).

Upgrade en rollback naar beta.88: [BETA89_INSTELLEN.md](BETA89_INSTELLEN.md).
