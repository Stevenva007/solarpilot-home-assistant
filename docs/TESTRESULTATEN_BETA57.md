# SolarPilot 1.0.0-beta.57 — testresultaten

Datum: **2026-10-06**

## Bronbasis en bewijsgrenzen

Basis is de gecontroleerde gepubliceerde beta.56: commit `cdc17f3a18d82c30a30967b044565a2819439f42`, tree `dc282d67a4cefcfed2854d83687cab9f5bcce039`, annotated tagobject `422c51978a102578e753f779bd0cd0e3a6627172`. Release `403742027`, workflow `37316780333`, vier geslaagde jobs en vier release-assets zijn gecontroleerd. Beide ZIP-pakketten zijn byte voor byte met de tagbron vergeleken. Haar 3244 tests zijn basisbewijs, geen beta.57-resultaat.

De actuele gebruikersinformatie corrigeert de eerdere veronderstelling over sterilisatieplanning en verandert de gewenste voorrang en zonne-AUTO-regeling. Dit bewijst niet achteraf iedere fysieke actie-uitkomst. Regressies en voorbeelden gebruiken fictieve gegevens. Geen privé-export, installatie-identiteit of echte huishoudelijke entiteit wordt gepubliceerd.

## Softwaregate

**Geslaagd: 3474 tests in 39,47 s**, na de laatste functionele wijziging en de consistente fysieke bronfixtures. Uitgevoerd met Python 3.12.14, pytest 9.1.1 en `PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider`. De volledige suite omvat oude regressies, nieuwe regelgevallen en uitvoerende Node/DOM-controles.

Ook geslaagd: publieke repository-preflight, alle 15 handoffsecties, actuele-uitleg/versiecontrole (regel-hash `af177ba7450ae65b`, 440 hulpvelden), repositorystructuur, AST-syntax van 67 component-Pythonbestanden, parsing van 4 JSON-bestanden, Node-syntax van beide frontendbestanden en `git diff --check`. Het fictieve voorbeeld is opnieuw opgebouwd. Er zijn geen Python-caches of privébestanden in de publicatie.

De nieuwe regressies dekken ook bronwijzigingen tijdens het duurzaam opslaan van een nog niet verstuurde opdracht. Een geannuleerde stop herstelt het eerdere eigendom, de vorige vermogensguards en het journal zonder blinde retry of fictief vrijgemaakt vermogen. Faseruimte reserveert ook mogelijke terugkeer van geïsoleerde lasten en nog niet verbruikte toezeggingen.

| Onderdeel | Geslaagd contract |
| --- | --- |
| Sterilisatieplanning | Geen tijd-only doelwriteblokkering; echte hygiene/manual/unknown blijft beschermd |
| Warm water | 3000 W inclusief grens, normale rise-/opdrachtrust, eigendom en echte doelbevestiging |
| Centrale prioriteit | Marker57 éénmalig bij geconfigureerde DHW, Wallbox/afwas vóór EXTRA, gewone lasten eronder, latere save en opgeslagen permission behouden |
| DHW-reclaim | Alleen veilig eigen lager interruptibel gemeten vermogen; minimum/boost/deadline/manual/sourceguard; OFF-ACK, nieuwe P1 en verse PV vóór start |
| Eén fysieke warmtepomp | Maximaal één gezamenlijke meter/reserve, scope heleHP versus exclusieve tank; gedeelde meter geen DHW-opwarmbewijs |
| Zonne-AUTO | 2500 W/60 s/nieuw P1+PV; bekende verse programmacontext, modelonafhankelijk; eigen 2000 W-hold met eenmaal echteHP/maxPV |
| Bestaand comfortpad | Passende richtingsvraag, zachte bevestiging, relevante modellen; dashboardoverride/externalhold/minONOFF/pendingfout beschermd |
| Elektrische ruimte | Batterij niet als zon, geen fictieve fase/piekruimte, postcommand nieuwe P1, verse PV en settle |
| Echte frontend | Doorlopend actief versus gestippeld beschikbaar/werkelijk hoog doel; proposal/stale/sharedmeter geen fictieve warmte |
| Uitleg en repository | Versie57, 440 hulpvelden, gelijke canonieke uitleg en installatiekopieën, handoff/preflight, syntax en diff |

## Betekenis en beperkingen

Een bekende klokplanning is geen actuele fysieke sterilisatiemelding. Panasonic kan haar interne 62 °C-cyclus uitvoeren zonder het gewone HA/display-doel te verhogen. Een normale 60 °C-vraag verandert die cyclus niet. Werkelijk gekoppelde hygiene/manual/native-onzekerheid houdt afzonderlijke bescherming.

Zonne-AUTO is bewuste beschikbaarheid bij echte restzon, geen bewijs van warmtevraag, koeling of compressorstart. Het gewone comfortpad blijft richtingsgebonden. HA AUTO/UIT kan upstream globaal worden vertaald; SolarPilot garandeert geen behoud van het oorspronkelijke programma en wijzigt geen ruimtedoel of directe HEAT/COOL-instelling.

P1 bevat werkelijk gezamenlijk warmtepompverbruik al eenmaal. Een gedeelde W-meter bewijst niet dat de tank opwarmt. Reclaim gebruikt mogelijke stopruimte alleen om veilig vrijmaken te beoordelen; pas echte bevestiging en nieuwe metingen maken haar inzetbaar. Geen afwascyclus, klimaatlast of Wallbox wordt voor extra DHW gestopt.

Geen live Home Assistant- of fysieke toestelacceptatie is uitgevoerd. HA-/DOM-doubles toetsen softwaregedrag, geen geladen telefoonapp, daadwerkelijke compressoractie, tankrespons of thermische voorspelnauwkeurigheid.

## Publicatie en installatie

De CI/publicatie is afzonderlijk te controleren bij de [beta.57-release](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.57) en [Validate-workflow](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml). Vereist zijn vier geslaagde jobs, een annotated tag op de geteste commit, twee ZIP-pakketten en twee beta.57-documenten. De afsluitende controle downloadt alle vier assets, controleert SHA-256 en vergelijkt beide volledige ZIP-inhouden met de exacte tagbron. Eerdere releases blijven onveranderd.

Installatie en rollback staan in `BETA57_INSTELLEN.md`. Na installatie Home Assistant herstarten, app/webpagina opnieuw openen en backend-/kaartversie controleren. Programmabestanden terugzetten maakt de gemigreerde opgeslagen prioriteit of meterscope niet vanzelf ongedaan; controleer de effectieve waarden of herstel een passende volledige back-up. Publicatie is geen bewijs dat de update al op een installatie geladen is.
