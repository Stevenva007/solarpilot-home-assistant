# SolarPilot 1.0.0-beta.77 — testresultaten

Datum: **12 oktober 2026**. Bouwbasis: gepubliceerde beta.76, commit `da26ee3c5b4920b3d6526a2138dca1e839484264`, tree `f552cc3a9ea63cd758d96a34fe7eace52613e5e4`. Haar vijf gates en publicatie slaagden in main-run `38218561471`; vier assets zijn in die workflow werkelijk teruggedownload en gecontroleerd. Dit is basisbewijs, geen beta.77-validatie.

## Wijziging en grenzen

Beta.77 behoudt de bestaande automatische PV-kalibratie en haar expliciete uitschakelkeuzes. Een volledig geldig kwartier met één scherpe, stabiele overgang kan nu kandidaatbewijs leveren. Rustige delen vóór/na, minstens twaalf onafhankelijke verse metingen, elf minuten spreiding, begrensde gaten en geen clipping/outlier zijn vereist. Verschillende vergelijkbare dagen moeten richting, timing en verhoudingen bevestigen. Normaal begint toepassing na minimaal vijf consistente dagen met voldoende vertrouwen; hogere instellingen/langzamere presets blijven gelden.

De overgangsfactor gebruikt de geïntegreerde werkelijk/ruw-energieverhouding van het kwartier, niet de mediaan van de twee vermogensplateaus. Geïntegreerde waarden gebruiken alleen voldoende gedekte meetintervallen en hoogstens 120 seconden rustige endpointverlenging. Normale kwartieren behouden hun bestaande mediane leerroute. Factorgrenzen 0,35–1,25 en de normale dagstap van maximaal 0,05 blijven staan. Vertrouwde kandidaatmetingen worden pas bij voldoende gezamenlijk bewijs modelinvoer; oude historiekrijen blijven ongewijzigd met hun oorspronkelijke factor en leerbesluit.

Zonnestand plus seizoensgroep blijft leidend, met seizoenskwartierfallback. Een wisselend geometrieprofiel kan alleen wijken voor aantoonbaar sterker terugkerend bewijs in het tijdvak; gewone klokmetingen kunnen de bestaande betrouwbaarheidsgrens niet omzeilen. Er is geen vaste 16:00-regel, bewezen boomdetectie, cloud-AI, extra dependency of nieuwe hardwarebediening.

`factor_details` toont werkelijke passende dagen, benodigd minimum, reden, factor en overgangsbewijs voor ieder tijdstip. De bestaande tuple-API houdt de oorspronkelijke gevalideerde nulwaarden vóór het minimum. Het on-demand namiddagprofiel toont twaalf lokale kwartieren van 15:00 tot 17:45. Ontbrekende forecastdekking blijft onbekend; modelzekerheid is geen fysiek oorzaakbewijs.

## Definitieve lokale uitvoering

| Controle | Uitgevoerd beta.77-resultaat |
| --- | --- |
| Volledige pytest, Python 3.12.14 | **4711 geslaagd in 87,23 s**, zonder bytecode of pytestcache. |
| Nieuwe gerichte tests | **76 cases**: 22 core, 49 adversarieel en 5 forecast-/diagnose-integratie. Allemaal onderdeel van de volledige suite, geen extra opgetelde suite. |
| Python-productiesyntax | AST-parse van alle **79** productiemodules geslaagd. |
| JavaScript-syntax | Kaart en optiehulp geslaagd voor Node-controle; bestaande UI-regressies onderdeel van pytest. |
| Canonieke guide en mirrors | Geslaagd; guidehash `bc77ca94c89c89fb`, **345** optiehulpvelden. |
| Overdracht, SG-bevoegdheidsgrens, publieke preflight en diff | Geslaagd. |
| Werkelijke PV-browserproef | Nieuwe brongebonden CI-uitvoering verplicht; het bestaande echte PV-script is uitgebreid en toegevoegd aan de browsergate. Nog geen lokaal browserresultaat geclaimd. |

## Betekenisvolle proeven

- Herhaalde scherpe daling én herstel worden pas na voldoende verschillende volledige dagen geleerd. Eén dag, herstarts op dezelfde datum, alternerende wolken, uiteenlopende timing/richting en afwijkende verhoudingen geven geen nieuw recht op correctie.
- Verouderde, geschatte, onvolledige, geclipte of ongeldige bronnen kunnen geen kandidaatbewijs vormen. Twaalf losse metingen met onvoldoende spreiding, te grote binnen-/endpointgaten of een foute afzonderlijke meting blijven afgewezen.
- Een overgang midden in een kwartier gebruikt de energieverhouding van het hele kwartier; de mediaan mag niet één plateau als volledig kwartier behandelen.
- Opgeslagen versie-1-factoren blijven behouden. Nieuw kandidaatbewijs is gebonden aan dezelfde broncontext, eindig, begrensd, gesaneerd en seizoensgebonden. Ongebonden restore, toekomstige/aliased datums en gewijzigde bron kunnen geen incompatibel bewijs hergebruiken.
- Historische datumreplay kan de dagelijkse leerstap niet opnieuw zetten. Winter-/zomerprofielen, bestaande factorvloer, minimum/presets en uitschakeling blijven beschermd.
- Drie passende dagen worden als 3/5 getoond, zonder voortijdige correctie; totale leerdagen zijn niet het bewijs voor ieder afzonderlijk tijdvak.
- Het kwartierprofiel blijft read-only en houdt lokale tijd bij wintertijd correct. Zonder oorspronkelijke broncurve worden ruwe/gecorrigeerde watts niet als nul of fictieve historie ingevuld.

## CI, release en fysieke grens

Op het schrijfmoment van deze immutable bronbijlage waren de nieuwe GitHub-gates en release nog niet uitgevoerd. Actuele status: [Validate Actions](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml). Vereist: repositorysuite, HACS, officiële Hassfest, echte Core **2026.10.0** setup/reload/unload en browser. De browsergate bevat nu tevens de echte PV-diagnoseproef op mobiele/brede vensters, naast alle bestaande warmtepomp- en historieproeven. De main-workflow publiceert alleen na alle vijf gates en controleert vier assets vóór en na upload tegen de exacte commit.

Dit verslag voorspelt geen run-ID of toekomstige uitslag. Softwareproeven bewijzen geen actuele schaduw van een specifieke boom, verbeterde thuisforecast of fysieke compressorwerking. Bestaande oude kwartiermedianen missen het overgangsverloop en worden niet achteraf nieuw kandidaatbewijs; nieuwe vergelijkbare metingen zijn nodig. Realtime P1/PV, Panasonic/Wallbox en alle bestaande SG-/fase-/vermogensgrenzen blijven behouden. Installatie en rollback: [BETA77_INSTELLEN.md](BETA77_INSTELLEN.md).
