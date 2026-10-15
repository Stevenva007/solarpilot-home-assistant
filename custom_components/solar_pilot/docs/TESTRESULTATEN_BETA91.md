# SolarPilot beta.91 — test- en releaseverslag

Versie: **1.0.0-beta.91** · 15 oktober 2026

Bouwbasis: gepubliceerde beta.90 `ab872c236516e2121535f073380a6363aee228a5`. Eerdere versieresultaten zijn geen beta.91-validatie. Privé-export, bronidentiteiten en woningwaarden staan buiten publieke bron en pakketten; alle fixtures zijn fictief.

## Concrete correcties

- Een geldig opgeslagen lager number-doel wordt bij herstart behouden, zodat een passende echte instelling niet ten onrechte als externe overname wordt afgewezen. Ongeldige doelen blijven conservatief; een werkelijk gewijzigde fysieke instelling wordt niet overgenomen.
- Natuurlijke SG-timerafloop en externe eigendomsoverdracht leggen het einde van de passende sessie vast zonder een niet-verzonden UIT-opdracht te claimen. Oorspronkelijke regels en bronrapporten blijven bij hun eigen opdracht.
- Aquarea 1.5.4 wordt alleen onder het gecontroleerde aioaquarea-ng 1.3.1-contract toegelaten voor presentatie. Ontbrekend/oud/strijdig/foreign bewijs blijft onbekend; leer- en SG-veiligheidsrechten worden niet verruimd.
- Een geldige berekende SG-doelvergelijking vereist geen bekende relaisstand of native terugmelding van het berekende doel. Geldig percentage, exacte lokale doelbinding en oorspronkelijke doelactualiteit blijven noodzakelijk.
- Normale leerstabilisatie is een tijdgebonden informatieve wacht; langdurige warmtepompcontextuitsluiting staat afzonderlijk.
- PV-selectie wordt vooraf per horizon vastgelegd; gedeelde oorspronkelijke meterwaarnemingen blijven herkenbaar afhankelijk. Geen legacy-backfill, factorwijziging of bewezen besparing.
- Exports scheiden fysieke waarneming, planning, eigendom en herstelminimumtijd en verdelen bewijs per verzamelende release/bron. Cloudperiodegrenzen komen uit de geverifieerde native sensor, niet uit exporttijd of een daglabel.

## Gerichte verificatie

De gezamenlijke nieuwe backendregressies zijn lokaal uitgevoerd: **159 geslaagd**. De finale catalogus-/Node-/SG-doelweergavegroep: **64 geslaagd**. De nieuwe echte Chromium-gate is lokaal geslaagd met vier breedtes en nul toestelopdrachten. Gerichte sets overlappen; hun aantallen worden niet opgeteld tot een totaalsuite.

| Controle | Uitvoering vóór publicatie |
|---|---|
| Aquarea-binding/ruwe status/conflict/actualiteit en UTC-cloudperiodes | Gerichte backendregressies uitgevoerd; exacte brede CI blijft vereist |
| Herstel terwijl AAN, volledige minimumduur en stop erna, number-doel | 153 gerichte tests geslaagd; uitgebreide afzonderlijke nieuwe regressies 17 geslaagd |
| PV-opslag/restore, termijnen, oorspronkelijke meting, kalender/API/kalibratie | 321 gerichte tests geslaagd |
| SG-regels/transport/herstart/minimum/import en nieuwe herkomst | 347 gerichte tests geslaagd; finale suite toetst definitieve bron |
| Leerwacht en UI-contracten | 137 gerichte regressies geslaagd; volledige suite en browsergate op definitieve bron vereist |
| Volledige Python-suite, privacy/structuur, overdracht, guide/help/mirrors, SG-grens, syntax | Worden door repository-checks op de exacte PR-/mainbron uitgevoerd |
| HACS en Hassfest | Afzonderlijke verplichte CI-jobs |
| Home Assistant Core 2026.10.0 | Afzonderlijke verplichte lifecycle-/immutable-config-job; geen fysieke servicecall |
| Chromium met 320/390/768/1440px, XSS, detailbehoud en nul toestelopdrachten | Afzonderlijke verplichte browserjob met nieuwe beta.91-gate |
| Immutable annotated tag en vier assets | Pas bevestigd na de main-publicatiejob met terugdownload en bytevergelijking |

Lokale tests en de vijf verplichte CI-gates zijn softwarebewijs. Zij tonen geen uitgevoerde gebruikersinstallatie, fysieke ontvochtigerstop of Panasonic-reactie. De toegevoegde herstelregressie test wel het softwarepad over de volledige beschermde minimumlooptijd en één stop onder de dan ongunstige voorwaarden.

## Publicatiecontrole

De [Validate-workflow](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml) vereist repository/tests/PowerShell, HACS, Hassfest, echte Core en Chromium op dezelfde bron vóór publicatie. Alleen een geslaagde main-run maakt de nieuwe immutable annotated tag en release. Dit verslag bevat geen voorspeld run-ID of verzonnen toekomstig resultaat.

De publicatiejob controleert vóór upload en na terugdownload grootte, SHA-256 en exacte bronbytes van vier assets:

- `SolarPilot-v1.0.0-beta.91-GitHub-HACS.zip`
- `SolarPilot-v1.0.0-beta.91-local.zip`
- `BETA91_INSTELLEN.md`
- `TESTRESULTATEN_BETA91.md`

Controleer de definitieve commit, de vijf jobresultaten en **Download and verify published four assets against the exact tag** (`download_verified: true`) bij [release beta.91](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.91). Geen bestaande tag of asset wordt overschreven.

Upgrade en rollback: [BETA91_INSTELLEN.md](BETA91_INSTELLEN.md).
