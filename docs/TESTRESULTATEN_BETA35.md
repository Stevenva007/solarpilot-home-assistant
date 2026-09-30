# SolarPilot beta.35 — lokaal testverslag

**Release:** 1.0.0-beta.35  
**Datum:** 30 september 2026  
**Basis:** het aangeleverde SolarPilot-v1.0.0-beta.34-GitHub-HACS.zip  
**Omgeving:** Python 3.13.5, pytest 9.0.2, Node.js-syntaxiscontrole en Playwright met lokale Chromium.

## Resultaat

**1.404 softwaretests geslaagd:** de 1.314 bestaande tests plus 90 nieuwe tests voor de centrale voorrang, migratie, toestemming en bescherming. De laatste volledige uitvoering eindigde met `1404 passed in 8.18s`.

**Elf browsercontroles geslaagd.** Deze laden de werkelijk meegeleverde kaart en helpercode uit de offline voorbeeldpagina en gebruiken expliciete fictieve Home Assistant-antwoorden. De nieuwe voorrangseditor is onder meer met echte drag/drop-gebeurtenissen, pijlen en mobiele breedtes gecontroleerd.

Dit zijn lokale software- en browsertests met testdubbels, **geen volledige Home Assistant Core-integratietest en geen praktijktest op een warmtepomp, Wallbox, afwasmachine of ander elektrisch toestel**. Er zijn geen echte toestelcommando's verstuurd. Geen publicatie, echte installatie, GitHub Actions-run, officiële HACS-validator of Hassfest-run is uitgevoerd.

## Nieuwe softwarecontroles

De 90 nieuwe tests controleren dat openen en ongewijzigd opslaan de bestaande regeling niet activeren of herschrijven; een echte opslag bewaart de oude toestelconfiguratie, modus, statusobjecten, timers en leer-/opslagobjecten; en een herstart de opgeslagen lijst opnieuw gebruikt. De API weigert niet-beheerders, verkeerde integraties, onvolledige lijsten, dubbels, onbekende toestellen, ongeldige toestemmingen en bevestigingen die geen letterlijke boolean zijn.

Een normale meting wijzigt het revisienummer niet; een andere instellingenwijziging wel. Een oudere editor mag daarna niet stilzwijgend opslaan. Reeds verzonden opdrachten en lopende overnames blokkeren een nieuwe lijst totdat ze afgehandeld zijn. Oude numerieke/globale bediening en een oude open wizard kunnen een actieve centrale lijst niet overschrijven; gewone naam-/categoriewijzigingen blijven wel mogelijk.

Voorrang vóór de auto, expliciete toestemming en geschikte meting zijn afzonderlijke voorwaarden. De planner en realtime toestelconfiguratie krijgen dezelfde centrale rangorde. De legacy-groepsrangorde blijft intact zolang de centrale lijst niet actief is. Minimumlooptijden en beschermde programma's blijven boven een herordening staan. De afwasroute mag een hoger geplaatste last niet laten wijken.

De extra boilerbuffer blijft na de Wallbox en een voorkeur-afwasmachine. Een passend hoger gewoon toestel kan een nieuwe extra warmtevraag laten wachten; een lager bestaand programma wordt niet gestopt. Een inactieve tank boven de bestaande herstartdrempel reserveert niet eindeloos alleen wegens een hoog setpoint. Andere boilerstadia dan werkelijk goedgekeurde extra zonnewarmte reserveren geen nieuw zonnevenster op grond van de centrale lijst.

Nieuwe identiteiten verschijnen zonder geërfde Auto-deelname. De export bevat de centrale lijst, behoudt consistente verwijzingen onder pseudoniemen en verstuurt geen fysieke opdracht.

## Browsercontroles

| Controle | Resultaat |
|---|---|
| `check_card.py` — Volledige kaart: negen tabbladen, status, klimaat, planner, bediening en escaping | Geslaagd |
| `check_options_ui.py` — Native instellingenwizard, uitleg, payloads, fouten en behoud tijdens 80 updates | Geslaagd |
| `check_consumer_history_ui.py` — Historiepopup, dagen, scroll, race-antwoorden, sluiten en focus | Geslaagd |
| `check_dhw_gentle_ui.py` — 50/46-profiel, fabrikantdifferentiatie, waarschuwingen en uitleg | Geslaagd |
| `check_dishwasher_analysis_ui.py` — AEG-kaart en exportbestandsopbouw, privacykeuze en download | Geslaagd |
| `check_dishwasher_app_ui.py` — APP-vrijgave, morgen/deadline, AirDry en bewaard programma-einde | Geslaagd |
| `check_dishwasher_priority_ui.py` — Bestaande afwasvoorrang en voorwaardelijke EV-/meteruitleg | Geslaagd |
| `check_learning_ui.py` — Leren & vragen, beleidsbevestiging, revisies, fouten en updatebestendigheid | Geslaagd |
| `check_live_options_ui34.py` — Live toestelbeheer, routekeuze, aanvraagbereik, wachtende wijzigingen en archief | Geslaagd |
| `check_pv_ui33.py` — PV-diagnose, grafiek/dagen, bevestigde reset, bronuitleg en race-antwoorden | Geslaagd |
| `check_priority_ui35.py` — Centrale editor: drag/drop, pijlen, toestemming, bevestiging, conflicten, annuleren en Export | Geslaagd |

De nieuwe editor bewaart conceptvolgorde, toestemming, bevestiging, scrollpositie en dezelfde dialog-DOM tijdens 100 live updates. Een opslagfout behoudt het concept en vraagt een nieuwe bevestiging. Een nog niet afgeronde leesaanvraag kan worden gesloten; een later antwoord heropent het venster niet. Niet-opgeslagen wijzigingen weggooien vraagt bevestiging. Namen met HTML worden als tekst getoond. De nieuwe pagina/editor is op 320, 390, 768 en 1360 pixels gecontroleerd; andere regressiecontroles omvatten ook 1280 en 1440 pixels.

De bestaande browsertestverwachtingen voor zeven tabbladen, de oude globale voorrangsschakelaar en de vroegere directe exportknop zijn aangepast aan de bedoelde nieuwe navigatie. De controles op overige bediening, toestelfuncties, privacy, responsieve breedtes en escaping zijn behouden.

## Releasecontroles

Python-syntaxis via `compileall` en JavaScript-syntaxis via `node --check` zijn gecontroleerd. `tools/check_current_explanation.py` controleert gelijke versies van manifest, integratie, kaart en canonieke uitleg, de twee gegenereerde Markdown-kopieën en de gegenereerde veldhulp. Er zijn 429 hulpitems gegenereerd voor deze release.

`tools/check_public_repository.py` controleert de meegeleverde repositorystructuur, verplichte metadata/licentie, de bewaarde userfiles-map en de aanwezigheid van uitgesloten privé-/cachebestanden. Tijdelijke bytecode en caches worden vóór verpakken verwijderd. De uiteindelijke ZIP wordt opnieuw geopend, op paden/caches gecontroleerd en met een CRC-controle gelezen.

## Zelf opnieuw uitvoeren

Voer vanuit de uitgepakte repository eerst de softwaretests uit:

```sh
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider
PYTHONDONTWRITEBYTECODE=1 python tools/check_current_explanation.py
PYTHONDONTWRITEBYTECODE=1 python tools/check_public_repository.py
node --check custom_components/solar_pilot/frontend/solar-pilot-card.js
node --check custom_components/solar_pilot/frontend/option-help.js
```

De browserscripts hebben Playwright en een lokale Chromium-installatie nodig. Bijvoorbeeld:

```sh
PYTHONDONTWRITEBYTECODE=1 python tools/check_priority_ui35.py
PYTHONDONTWRITEBYTECODE=1 python tools/check_card.py
```

De voorbeeldpagina en screenshots bevatten fictieve gegevens. Na installatie blijven een controle van de echte bronkoppelingen, huidige prioriteiten, fysieke toestemming en daaropvolgende beslissingen noodzakelijk. Tests geven geen garantie op foutloos gedrag met iedere externe integratie of hardwareversie.
