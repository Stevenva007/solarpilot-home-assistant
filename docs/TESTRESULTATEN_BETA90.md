# SolarPilot beta.90 — brongebonden test- en releaseverslag

Versie: **1.0.0-beta.90** · 15 oktober 2026

Bouwbasis: gepubliceerde beta.89-commit `18a052933a6178b2772022fac57e6d29dc70d5d5`, tree `3855933360b4924990a9e37011f96e2a1cdb2408`. Die eerdere release is herkomstbewijs en geen beta.90-validatie.

## Wijziging en bewijsgrenzen

Tijdelijke gewone toestelonbereikbaarheid geeft bron- of opdrachtwacht met een hercontrole na 300 seconden. Global Automatisch regelen is kiesbaar wanneer uitsluitend een afzonderlijk toestel op bronherstel of verzoening wacht; de keuze verleent geen fysieke vrijgave. Gezonde lasten houden hun actuele bron-, vraag-, timing-, prioriteits-, eigendoms- en harde elektrische voorwaarden.

Een tijdelijk geïsoleerd offline toestel krijgt geen extra hypothetische verbruiksreserve: werkelijk P1-overschot is leidend. Ontbrekende terugmelding wordt geen gemeten nul, bevestigde UIT of eigen-vermogenskrediet. Eigendom en al geprobeerd/onzeker resultaat blijven als metadata beschikbaar. Een oude offline ON-status van een afwasmachine geeft geen actuele toekomstige piekreserve. Werkelijk nu betrouwbare actieve afwasstatus houdt de bestaande beta.89-piekbegroting; de afzonderlijke SG-reserve en SG-/batterijbevoegdheden blijven ongewijzigd.

Nieuwe passende oorspronkelijke terugmelding ná een onzekere opdracht is nodig voor verzoening; er is geen actie-replay of fysieke bereikbaarheidstest. Bij een geldige duurzame eerdere eigen AAN-poging en passende nieuwe AAN-terugmelding blijft het toestel AAN zonder redundante AAN- of verplichte UIT-opdracht; de volledige minimumlooptijd begint bij herstel. Een willekeurig extern AAN-toestel zonder eigen opdrachtbewijs wordt niet overgenomen. Een reeds geprobeerd afwas-START blijft verbruikt. Een klok, herstart of terugkerende bron maakt geen nieuwe APP-aanvraag, tweede START of ruimere deadline. Alleen exact herkende oude gewone transport-/timeout-/terugmeldfouten worden brongebonden herstelwacht. Echte configuratie-, authenticatie-, toestemmings-, interne, maximumlooptijd- en fysieke fouten blijven zichtbaar.

Publieke fixtures zijn fictief. Softwaretests bewijzen geen bereikbare gebruikersinstallatie, fysieke start, werkelijk apparaatverbruik of gerealiseerde besparing.

## Uitvoering

De implementatie is op **15 oktober 2026** gecontroleerd in [Validate-run 38740723321](https://github.com/Stevenva007/solarpilot-home-assistant/actions/runs/38740723321), exacte PR-head `18b46369d541e04317fb1037007a6d67473c89e9`. Alle vijf vereiste validatiejobs zijn geslaagd. Er is geen lokale executoruitvoering of fysieke gebruikersinstallatie geclaimd.

| Controle | Vastgesteld resultaat op die bron |
|---|---|
| Volledige Python-testsuite | **6.562 geslaagd**, 100,19 seconden |
| 300s bron-/opdrachtwacht, globale Auto bij offline toestel, geen extra offline-reserve | Nieuwe en behouden regressies geslaagd in de volledige suite |
| Terugkeer terwijl AAN, passend nieuw post-pogingbewijs, geen blinde retry of tweede afwas-START | Regressies geslaagd; geen verplichte UIT-stap voor een geldige eerdere eigen opdracht |
| Echte fouten, SG-/batterijgrenzen, minimumtijden, eigendom en harde elektrische guards | Regressies en SG-bevoegdheidscontrole geslaagd |
| Privacy/structuur, overdracht, actuele gids/optiehulp/mirrors | Alle repository-preflights geslaagd |
| Publisherfoutgrenzen | 29 echte PowerShell/native regressies geslaagd met fictieve opdrachten, zonder netwerk of echte repositorymutatie |
| Python-syntax | Compileall geslaagd |
| HACS en Hassfest | Beide jobs geslaagd |
| Home Assistant Core 2026.10.0 | Productiesetup, herladen en afsluiten geslaagd voor beide fixtures; configuratie behouden; `physical_service_calls: 0` |
| Chromium | Volledige browserjob geslaagd; nieuwe herstelcontrole bij vier breedtes met vijfminutentermijnen, onbekend vermogen, geen extra offline-reserve, globale Auto, echte foutzichtbaarheid en behoud van hulp/focus/details; één expliciete moduskeuze, nul toestelopdrachten |
| Annotated tag en vier teruggedownloade releasebestanden | Nog te bewijzen door de publicatiejob op main; geen PR-publicatie uitgevoerd |

Deze resultatentekst en de bijbehorende overdracht worden na de geslaagde run toegevoegd. Die laatste wijziging betreft alleen verslaglegging; de definitieve exacte PR-head moet de vijf gates opnieuw doorstaan. Na samenvoegen herhaalt de main-pushrun de controles en volgt pas de publicatiecontrole.

De nieuwe canonieke gids heeft SHA-256 `1d16898220e480bd3f7a67c67d52950c7f9a46efe74c9f19f0d5eb91f5a2b501`; de Python-gids-/mirrorconsistentiecheck is geslaagd. Dit is bronconsistentiebewijs en geen bewijs van een fysieke installatie.

## Vereiste regressiegrenzen

- Tijdelijke bron- of transportuitval blijft per toestel en veroorzaakt geen blijvende generieke foutmelding; hercontrole elke 300 seconden zonder snelle retrylus.
- Herstel volgt huidige modus, vraag, voorrang, interlocks, minimumtijden en net-/fase-/kwartierruimte; nieuwe context tijdens await kan een inmiddels ongeldige opdracht voorkomen.
- Geen extra hypothetische verbruiksreserve voor source-isolatie, ook niet bij oude offline afwas-ON; geen fictief eigen krediet of gemeten nul. Werkelijk actuele beschermde afwaspiek en afzonderlijke SG-reserve blijven bestaan.
- Voor mogelijk verstuurde opdrachten passende nieuwe oorspronkelijke post-pogingterugmelding; geen replay, tweede START, herarmde APP-aanvraag of gewiste eigendomsoverdracht.
- Globaal Automatisch regelen kunnen kiezen met één offline toestel, zonder diens eigen blokkering of de gedeelde harde guards te omzeilen; echte interne foutpauze blijft beschermd.
- Configuratie-, authenticatie-, toestemmings-, max-runtime- en fysieke fouten blijven actionable; legacyclassificatie is exact en eindig.
- UI-aftelling blijft presentatie; open details/focus en bestaande UI-ACL blijven intact. Herstart herstelt geen oude actieve retryopdracht of verse brontijd.

## CI en pakketbewijs

De vijf gates van [Validate](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml) moeten op dezelfde exacte releasebron slagen: repository/tests/PowerShell, HACS, Hassfest, echte Core en Chromium. De workflow publiceert pas daarna de nieuwe immutable annotated tag.

Alle vier assets worden vóór upload en na terugdownload bytegelijk met dezelfde bron-SHA gecontroleerd:

- `SolarPilot-v1.0.0-beta.90-GitHub-HACS.zip`
- `SolarPilot-v1.0.0-beta.90-local.zip`
- `BETA90_INSTELLEN.md`
- `TESTRESULTATEN_BETA90.md`

Publicatie is pas bevestigd nadat **Download and verify published four assets against the exact tag** slaagt met `download_verified: true`. Dit verslag verzint geen toekomstig run-ID of geslaagde gate. Controleer tagcommit en push-run bij [release beta.90](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.90).

Upgrade en rollback naar beta.89: [BETA90_INSTELLEN.md](BETA90_INSTELLEN.md).
