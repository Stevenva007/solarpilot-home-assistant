# SolarPilot 1.0.0-beta.63 — testresultaten

Datum: **2026-10-10**.

## Bronbasis en gerichte fout

Bouwbasis: [beta.62](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.62), commit `8e49c21ee03d3bd70a7d3460c2104628a43772f2`, tree `7314c163b156f4df18dfe5ab31b88aae6a188865`. De oude tag en assets blijven ongewijzigd.

Home Assistant biedt `ConfigEntry.options` als onveranderbare mapping aan. Beta.62 probeert die in de runtimeconstructor rechtstreeks te deepcopyen. De afzonderlijke echte Core-baseline reproduceert bij de ongewijzigde beta.62-productiebron `TypeError: cannot pickle 'mappingproxy' object` in de runtimeconstructor. De entry krijgt `SETUP_ERROR`, voordat runtime.start, de SolarPilot-migratiearchivering en de eerste SolarPilot-Store-write worden bereikt. De oorspronkelijke opties en Store-inhoud blijven in die proef exact ongewijzigd; fysieke servicecalls: 0. De bestaande dict-only migratie zou bij een losse constructorfix alsnog opties verliezen. Beta.63 herstelt beide grenzen: eerst een lokale dictionarykopie, daarna verliesvrije mappingacceptatie in de migratie.

## Lokale softwaregate

**Definitieve volledige lokale suite: 2815 tests geslaagd in 32,24 seconden.** Uitvoering: `PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider`. Deze volledige run omvat de twee productiefixes, zes nieuwe startup-/mappingregressiegevallen en releasegebonden versies/uitleg. De afzonderlijke echte Core-startupproef hieronder telt niet als extra pytest-test.

Gerichte regressies controleren onveranderbare opties, geneste instellingen, migratiearchief en de oorspronkelijke HA-opties. De behouden volledige suite omvat SG-only commandobescherming, lokale lease, bronkwaliteit, fase-/kwartiergrenzen, voorrang, AEG, read-only Wallbox, andere toestellen, batterijen, export, Recorder en modellen. Er zijn voor deze hotfix geen bestaande contracttests verwijderd.

| Controle | Vastgelegd resultaat |
| --- | --- |
| Volledige toepasselijke pytest-suite | 2815 geslaagd in 32,24 s. |
| Handoff, actuele guide en beide mirrors | Geslaagd; beta.63 en guidehash `186004d313d8e50a`. |
| Releasegebonden optiehulp | 331 huidige entries; gerichte document-/help-/meldings-/diagnostiekset 72 geslaagd in 0,59 s. |
| Publieke repositorypreflight | Geslaagd. |
| SG-grens en repositorystructuur | Geslaagd. |
| Python-/JS-/JSON-syntax en diff | 70 Python-bestanden via AST en 5 JSON-bestanden gecontroleerd; beide JavaScript-bestanden via Node syntaxcontrole, `git diff --check` schoon. |

De volledige suite gebruikt voor HA-protocolgedrag opzettelijk testdoubles. De volgende afzonderlijke echte Core-gate is aanvullend daadwerkelijk uitgevoerd en geslaagd; zij maakt geen deel uit van de pytest-teller.

## Echte Home Assistant Core-entrytest

Omgeving: **Home Assistant Core 2026.10.0 en Python 3.14.2**, geïsoleerd lokaal, met uitsluitend fictieve entiteiten/configuratie en een tijdelijke Store. Opdracht: `python tools/check_real_ha_startup.py`; voor de exacte ongewijzigde beta.62-baseline dezelfde checker met `--source-root` op die bron en `--expect-mappingproxy-failure`.

| Proef | Werkelijk resultaat |
| --- | --- |
| Ongewijzigde beta.62 | Verwachte productie-startfout gereproduceerd: `SETUP_ERROR` en `TypeError: cannot pickle 'mappingproxy' object`; originele opties/Store exact gelijk en 0 fysieke servicecalls. |
| Beta.63 productie-entry setup | Geslaagd: de echte Core laadt SolarPilot via `async_setup_entry`, met echte onveranderbare `ConfigEntry`-mappings. |
| Zes echte platformen | Sensor, binary sensor, select, number, button en switch geladen; 58 registry-entiteiten met actuele states. |
| Configuratie en migratiearchief | Geldige overige instellingen behouden, archief exact gelijk aan de fictieve oorspronkelijke opties en Store; SG uit zonder verzonnen switchbinding. |
| Core reload en unload | Beide geslaagd; oude runtime gesloten, nieuwe geladen en privéarchief ongewijzigd. |
| Fout-/apparaatgrens | Geen opgevangen exceptions in de definitieve beta.63-proef en 0 fysieke servicecalls. |

De checker vervangt uitsluitend HTTP bind/start en source-IP discovery voor offline uitvoering. De SolarPilot-constructor, migratie, Store, platforms en entiteiten zijn niet gepatcht. Home Assistant opent in deze proef geen HTTP-listener en er wordt geen fysiek apparaat benaderd. De fictieve gebruikersmodus is Alleen bekijken en SG blijft uit.

De nieuwe CI-job **real-ha-startup** gebruikt dezelfde pinned Core-/Pythonversies, controleert deze bekende beta.62-baseline en de nieuwe productie-entry. Publicatie vereist naast de bestaande repository-, HACS- en Hassfest-gates ook een geslaagde real-ha-startup-job. De aangepaste publicatieworkflow/package-regressies zijn afzonderlijk herhaald: **13 geslaagd in 0,66 s**.

## Bewijsgrenzen en upgrade

De echte HA-proef is lokaal geïsoleerd uitgevoerd, zonder verbinding met de installatie van de gebruiker, gebruikersopslag of fysieke apparaten. Zij bewijst de configuratiegrens en productie-entry setup/reload/unload; geen feitelijke huishoudconfiguratie, geladen mobiele frontend of fysieke Shelly/Panasonic-reactie. De generieke screenshotmelding alleen bevat geen traceback; een afzonderlijke fout kan een andere oorzaak hebben.

Een normale upgrade naar beta.63 met volledige Home Assistant-herstart is de herstelroute. Verwijder SolarPilot niet en wis geen instellingen, modellen, archief of opslag. SG-only beleid en vereiste bewuste lokale ingebruikname veranderen niet. SG wordt niet geactiveerd door het herstellen van laden. Dit werk bevat geen live toestelbediening of gegevensreset.

## Publicatie en pakketten

Nieuwe PR-/main-workflowruns, annotated tag en prerelease worden na de lokale gates op de exacte bron gecontroleerd. `tools/check_release_packages.py` vergelijkt beide ZIP-inhouden byte voor byte met Git, inclusief versies, ledenlijst en documentmirrors. De publicatieworkflow controleert vooraf en daarna opnieuw alle vier werkelijk gedownloade assets, met bron-SHA, grootte en SHA-256. Een bestaande tag, afwijkende of ontbrekende asset wordt niet overschreven.

Publieke bewijsplaats: [Actions](https://github.com/Stevenva007/solarpilot-home-assistant/actions) en [beta.63-release](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.63). Deze brongebonden tekst claimt geen toekomstige upload of CI-succes. Exacte publicatiebewijzen worden in de betreffende workflow en oplevering geregistreerd, zonder de immutable release achteraf te wijzigen.

Installatie, ingebruikname en rollback staan in `BETA63_INSTELLEN.md`. Actuele werking staat in de uit `current_guide.py` gegenereerde `ACTUELE_WERKING.md`-mirrors en binnen Home Assistant onder **SolarPilot → Uitleg**.
