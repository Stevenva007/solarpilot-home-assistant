# SolarPilot beta.90 — brongebonden test- en releaseverslag

Versie: **1.0.0-beta.90** · 15 oktober 2026

Bouwbasis: gepubliceerde beta.89-commit `18a052933a6178b2772022fac57e6d29dc70d5d5`, tree `3855933360b4924990a9e37011f96e2a1cdb2408`. Die eerdere release is herkomstbewijs en geen beta.90-validatie.

## Wijziging en bewijsgrenzen

Tijdelijke gewone toestelonbereikbaarheid geeft bron- of opdrachtwacht met een hercontrole na 300 seconden. Global Automatisch regelen is kiesbaar wanneer uitsluitend een afzonderlijk toestel op bronherstel of verzoening wacht; de keuze verleent geen fysieke vrijgave. Gezonde lasten houden hun actuele bron-, vraag-, timing-, prioriteits-, eigendoms- en harde elektrische voorwaarden.

Een tijdelijk geïsoleerd offline toestel krijgt geen extra hypothetische verbruiksreserve: werkelijk P1-overschot is leidend. Ontbrekende terugmelding wordt geen gemeten nul, bevestigde UIT of eigen-vermogenskrediet. Eigendom en al geprobeerd/onzeker resultaat blijven als metadata beschikbaar. Een oude offline ON-status van een afwasmachine geeft geen actuele toekomstige piekreserve. Werkelijk nu betrouwbare actieve afwasstatus houdt de bestaande beta.89-piekbegroting; de afzonderlijke SG-reserve en SG-/batterijbevoegdheden blijven ongewijzigd.

Nieuwe passende oorspronkelijke terugmelding ná een onzekere opdracht is nodig voor verzoening; er is geen actie-replay of fysieke bereikbaarheidstest. Een reeds geprobeerd afwas-START blijft verbruikt. Een klok, herstart of terugkerende bron maakt geen nieuwe APP-aanvraag, tweede START of ruimere deadline. Alleen exact herkende oude gewone transport-/timeout-/terugmeldfouten worden brongebonden herstelwacht. Echte configuratie-, authenticatie-, toestemmings-, interne, maximumlooptijd- en fysieke fouten blijven zichtbaar.

Publieke fixtures zijn fictief. Softwaretests bewijzen geen bereikbare gebruikersinstallatie, fysieke start, werkelijk apparaatverbruik of gerealiseerde besparing.

## Uitvoering

Beta.90-uitvoering is bij opstellen van dit verslag **nog open**. Er zijn in deze bronwerkronde geen lokale executorresultaten vastgesteld. Oudere beta.89-testtellingen worden niet overgenomen als beta.90-bewijs. De definitieve exacte PR-head moet de volledige controles en alle vijf vereiste CI-gates doorstaan.

| Controle | Vastgestelde status |
|---|---|
| Nieuwe 300s bron-/opdrachtwachttests en oude regressies | Nog open |
| Globale Auto-keuze bij één offline toestel; gezonde andere lasten | Nog open |
| Geen extra offline-reserve; geen onbekend-als-nul of fictief krediet | Nog open |
| Passend nieuw terugmeldbewijs; geen blind retry of tweede afwas-START | Nog open |
| Behoud echte fouten, SG-/batterijgrenzen, minimumtijden en bescherming | Nog open |
| Canonieke gids, optiehulp, mirrors, handoff en versie | Nog open; oorspronkelijke gidsreconstructie vooraf exact bewezen |
| Volledige suite, syntax, privacy/repository en opdrachtgrenzen | Nog open |
| HACS, Hassfest, echte Core en Chromium op exacte PR-head | Nog open |
| Annotated tag en vier teruggedownloade releasebestanden | Nog open |

De bestaande gids is vóór aanpassing exact gereconstrueerd uit haar gegenereerde Markdown. Canonieke Python-JSON-serialisatie gaf SHA-256 `8b0d496ee62719358f03b087d06985915cdf2baf80eeecd3c8641cf4a23bc5ac`; her-renderen was bytegelijk met het bestaande bestand. Dat bewijst de equivalentie van de documentgeneratiebasis, geen uitgevoerde beta.90-softwaretest. De nieuwe gids en mirrors blijven aan de normale Python-consistentiechecks onderworpen.

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
