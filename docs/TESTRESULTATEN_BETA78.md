# SolarPilot 1.0.0-beta.78 — testresultaten

Datum: **12 oktober 2026**. Basis: gepubliceerde beta.77, commit `1e40d95632c6c301ac9fb88cf44cd08a4df73ed4`, tree `22a945a9a26595b9734e40f351916aec19cdcb96`. Haar vijf gates en publicatie slaagden in main-run `38225306484`, inclusief het werkelijk terugdownloaden en controleren van vier release-assets. Dit basisbewijs vervangt de nieuwe beta.78-controles niet.

## Wijziging

Een vaste APP-startdeadline betekent nu altijd netfallback zodra de ontbrekende zon moet worden aangevuld. Oude `dishwasher_deadline_grid_allowed=False` en `request.grid_allowed=False` kunnen deze deadline niet uitstellen. Een lage batterij-SoC of Wallbox-zonnevoorkeur verhindert die netstart niet; batterijmetingen moeten wel geldig blijven. De vaste plandag, deadline, bronidentiteit en begrensde vervaltermijn blijven staan. Alleen een nieuwe geldige APP-vrijgave geeft toestemming voor één belading.

Net-, fase- en kwartiergrenzen, reeds toegezegd vermogen, beschermde cycli, deur/programma/remote, geldige bronnen, Pauze, deelname en opdrachtserialisatie blijven leidend. Geen nieuwe Wallbox- of Panasonic-bediening. Een fysieke start op exact het deadline-tijdstip wordt niet gegarandeerd wanneer zulke voorwaarden of de apparaatverbinding blokkeren.

De deadlineweergave gebruikt de werkelijk geldende nettoekenning en fasegrenzen, zonder zonnestartmarge of obsolete EV-wachtreden. Een afgewezen deadlineplan behoudt zijn concrete reden. De laatste controle vóór START leest opnieuw P1, kwartierbudget, fasen, native vrijgave en bestaande verbruiksreserves. Na de duurzame intentopslag worden dezelfde bronnen en de onveranderde configuratie, aanvraagidentiteit en het programma opnieuw gecontroleerd. Een aantoonbaar niet verstuurde intent mag zijn boekhouding veilig terugnemen; een werkelijk verstuurde of onzekere START wordt nooit automatisch herhaald.

Een blokkering na de deadline wordt éénmaal gemeld. Een geselecteerde maar niet verstuurde START kan deze melding niet blijven verbergen. Een echte START-aanvraag met onzekere uitkomst houdt de bestaande afzonderlijke opdrachtfout. Alleen een passende, eindige native Running-bevestiging voor dezelfde aanvraag ruimt de deadlineblokkering op. Dashboard en toestelkaart behouden verbruikte aanvraagcontext en tonen startaanvraag en bevestiging afzonderlijk, zonder een tweede vrijgave of verzonnen fysieke starttijd.

## Definitieve lokale uitvoering

| Controle | Uitgevoerd beta.78-resultaat |
| --- | --- |
| Volledige pytest, Python 3.12.14 | **4796 geslaagd in 86,75 s**, zonder bytecode of pytestcache. |
| Nieuwe regressies | **85 cases**: 33 APP-lifecycle en 52 runtime. Zij zijn onderdeel van de volledige suite, geen extra opgetelde suite. |
| Python-productiesyntax | AST-parse van alle **79** productiemodules en het nieuwe browserscript geslaagd. |
| JavaScript | Syntax van de actuele kaart geslaagd. Brongebonden preview opnieuw opgebouwd. |
| Canonieke uitleg en mirrors | Geslaagd; guidehash `a6346f80cf8d0dd1`, **345** optiehulpvelden. |
| Overdracht, publieke preflight, SG-bevoegdheidsgrens en diff | Geslaagd. |
| Browser | Runtimefixtures en script-syntax lokaal gecontroleerd; echte Playwright/Chromium-uitvoering toegevoegd aan de bestaande CI-browsergate. Geen lokaal browserresultaat geclaimd. |

## Betekenisvolle proeven

- Zonder zon blijft een vrijgegeven beurt vóór de deadline wachten en start hij op de deadline éénmaal met netstroom, ook bij oude uitgeschakelde vlaggen en geldige lage SoC. Ongeldige batterijsensoren blijven blokkeren.
- Onvoldoende net-, kwartier- of faseruimte voorkomt START. Een geldig eigen faseprofiel kan starten op zijn beschikbare fase wanneer een andere fase druk is; een onbekende fasekaart maakt geen ruimte. Een beschermde cyclus mag later opnieuw haar toegezegde piek gebruiken.
- Lagere onderbreekbare lasten wijken pas veilig, met behouden minimumlooptijd en nieuwe bevestigde meterdata vóór de afwasstart. Wallbox-watts worden geen extra netruimte.
- Tijdens opslag gewijzigde P1, deur, programma, bronkoppeling, toestelvermogen, vaste aanvraag of Pauze voorkomen de nog niet verstuurde START. Terugnemen bewaart een werkelijk ingetrokken aanvraag als ingetrokken en herstelt eigen timers, ticket, eigenaarschap en Wallbox-/SG-monitorboekhouding.
- Verse metingen van andere beschermde lasten blijven bij de eindcontrole bepalend voor hun toekomstige vermogensreserve. Onbekend of geschat vermogen kan die reserve niet opheffen. Herhaald eindcontrole-uitstel geeft één concrete melding en geen fysieke opdracht.
- Een native Running-report verbruikt de aanvraag en behoudt deadlinecontext. Herhaalde reports verschuiven de eerste bevestiging niet. Polling of een opstartwaarneming krijgt geen verzonnen exacte start. Beta.77-context wordt alleen met aantoonbaar passend ticket-/cyclusbewijs hersteld; een volgende handmatige cyclus erft geen oude deadline.
- Onbekende, ongerelateerde, ongeldige of toekomstige bevestiging ruimt geen melding op. Verbindingsverlies, timeout en onzekere echte START geven geen tweede druk op de startknop.

Alle nieuw opgenomen fixtures zijn fictieve HA-doubles. De echte browserproef gebruikt zulke brongebonden fixtures in Overzicht en Toestellen, op 320/390/768/1440 pixels, met behoud van Details over 80 updates, onbekende/ongeldige tijden, veilige tekstweergave en nul browsernetwerk- of bedieningsoproepen.

## CI, publicatie en praktische grens

Op het schrijfmoment van deze immutable bronbijlage waren de nieuwe CI/publicatiegates nog niet uitgevoerd. Actuele brongebonden status: [Validate Actions](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml). Vereist: repositorysuite, HACS, officiële Hassfest, echte HA Core **2026.10.0** setup/reload/unload en browser. De bestaande PV-, warmtepomp- en historie-browserproeven blijven verplicht naast de nieuwe deadlineproef. Alleen een geslaagde main-run mag publiceren; vier assets worden vóór upload en na werkelijk terugdownloaden tegen de exacte tag/commit gecontroleerd.

Softwareproeven bewijzen geen actuele installatie, fysieke starttijd of oorzaak van een gemiste thuisdeadline. Alleen screenshots onderscheiden de actuele netgrens, kwartierbudget, reserve, opdrachtchronologie en native/cloudlatentie niet volledig. Ze worden niet als ruwe huisgegevens in deze publieke bron opgenomen. Bestaande instellingen en leerdata blijven behouden, afgezien van de expliciet gewijzigde betekenis van de APP-netfallback op de deadline. Installatie en rollback: [BETA78_INSTELLEN.md](BETA78_INSTELLEN.md). Actuele volledige werking: [ACTUELE_WERKING.md](ACTUELE_WERKING.md).
