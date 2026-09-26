# Changelog

## 1.0.0-beta.21 — Runtime-fix na eerste flexlast

- Herstelt een `NameError` in het toesteloverzicht (`i` → toestel-ID) waardoor de hoofdstatussensor en daardoor de SolarPilot-config entry konden mislukken zodra een flexlast was toegevoegd.
- Voegt een regressietest toe zodat een toesteloverzicht met cyclusprofiel niet opnieuw op deze fout kan stuklopen.
- Corrigeert Home Assistant-statistiekmetadata voor energie-entiteiten: dagzonne-energie gebruikt `total_increasing`; de batterij-what-if energie gebruikt `total`.
- Verplaatst lezen/verwijderen van de privébundel en historische bootstrap uit de Home Assistant event loop naar executor-werk, zodat de `read_text` blocking-call waarschuwing verdwijnt.
- Werking en veiligheidslogica blijven verder ongewijzigd; bestaande configuratie, privébundel, leerdata en toegevoegde verbruikers blijven behouden.

## 1.0.0-beta.20 — Public HACS/GitHub release

- Publieke HACS-build opgeschoond: geen woning- of installatie-specifieke entity-ID's meer in first-install defaults.
- Eerste installatie laat de gebruiker net/PV en overige bronentiteiten expliciet kiezen; alleen universele `sun.sun` mag veilig worden voorgesteld.
- `hacs.json` rendert de README expliciet in HACS.
- GitHub-validatie uitgebreid met HACS Action, Home Assistant hassfest, syntax-, documentatie- en privacy/preflightchecks.
- Releasehulpmiddelen aangepast aan de ingebouwde frontend onder `custom_components/solar_pilot/frontend`.
- Zowel de rootdocumentatie als de in Home Assistant meegeleverde actuele uitleg worden voortaan uit dezelfde bron gegenereerd en gecontroleerd.
- Python/test-cachebestanden worden niet meer in de publicatie-ZIP opgenomen.
- Windows-publicatiescript toegevoegd voor GitHub CLI, met preflight vóór de push en zonder automatische release vóór CI groen is.

## 1.0.0-beta.18 — HACS-ready

- HACS wordt de aanbevolen installatie- en updatemethode.
- Repositorystructuur voldoet aan HACS-integratievereisten: één integratie onder `custom_components/solar_pilot`.
- `hacs.json`, HACS-validatie-workflow en tag-release-workflow toegevoegd.
- Brand-assets toegevoegd voor Home Assistant/HACS.
- Frontend blijft ingebouwd in dezelfde integratie; geen aparte Lovelace-resource nodig.
- Configuratie en leerdata blijven in Home Assistant opgeslagen en worden niet door HACS-updates vervangen.
- Veilige verwijderprocedure behouden: eerst `Verwijderen voorbereiden`, daarna config-entry verwijderen en vervolgens HACS-uninstall.
- Custom-integrationvertalingen komen uit `translations/`; verouderde `strings.json` is uit het HACS-pakket verwijderd.
- Publicatiehulpmiddel toegevoegd om GitHub owner/repository éénmalig in manifest en README in te vullen.
