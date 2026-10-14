# Openbaar upstream-bronregister

Laatst gecontroleerd: **14 oktober 2026**. Dit register beschrijft openbare broncontracten die voor SolarPilot relevant zijn. Een upstream-release is geen bewijs dat die versie lokaal is geïnstalleerd; een open pull request is geen gepubliceerde correctie. Gegevens uit privé-installaties, exports en automatiseringsidentiteiten horen niet in dit register.

## Gepinde bronnen

| Bron | Gecontroleerde versie en commit | Betekenis voor SolarPilot |
|---|---|---|
| [Aquarea Smart Cloud](https://github.com/wpatrik14/home-assistant-aquarea/releases/tag/v1.5.3) | v1.5.3, gepubliceerd **14 oktober 2026 11:12:02 UTC**; commit `8a61af19e2efa94f8df74188759b9fa58280b5c0` | De native tankentiteit combineert waterrichting met pompstatus. Het manifest gebruikt nog `aioaquarea-ng>=1.3.1`; deze release corrigeert niet automatisch de library-mapping van globale bedrijfstoestand. |
| [Aquarea-basis vóór deze tankcorrectie](https://github.com/wpatrik14/home-assistant-aquarea/releases/tag/v1.5.2) | v1.5.2; commit `88abea3b6b42b30ec9b9f4f2d1eb4a5ff9eb2baa` van **10 oktober 2026** | Oudere tankweergave kan alleen waterrichting als opwarmcontext gebruiken. Vergelijk beide vaste bronversies; behandel een lokaal geselecteerd programma niet als nieuw actie- of compressorbewijs. |
| [aioaquarea-ng](https://github.com/wpatrik14/aioaquarea/releases/tag/v1.3.1) | v1.3.1, gepubliceerd **10 oktober 2026 11:49:16 UTC**; commit `d859f3727556c8a07964affd61a038edfd2d353a` | De parser koppelt globale `operation_status` nog aan `specialStatus`; `current_action` beoordeelt die OFF eerst. Verse afzonderlijke zone-/tank-/richting-/pompvelden hebben daarom een andere betekenis dan deze afgeleide globale OFF. |

Concrete code op vaste commits:

- [Aquarea manifest v1.5.3](https://github.com/wpatrik14/home-assistant-aquarea/blob/8a61af19e2efa94f8df74188759b9fa58280b5c0/custom_components/aquarea/manifest.json), [tankentiteit](https://github.com/wpatrik14/home-assistant-aquarea/blob/8a61af19e2efa94f8df74188759b9fa58280b5c0/custom_components/aquarea/water_heater.py) en [klimaatentiteit](https://github.com/wpatrik14/home-assistant-aquarea/blob/8a61af19e2efa94f8df74188759b9fa58280b5c0/custom_components/aquarea/climate.py).
- [aioaquarea parser v1.3.1](https://github.com/wpatrik14/aioaquarea/blob/d859f3727556c8a07964affd61a038edfd2d353a/aioaquarea/device_manager.py), [gegevenssemantiek en current_action](https://github.com/wpatrik14/aioaquarea/blob/d859f3727556c8a07964affd61a038edfd2d353a/aioaquarea/data.py) en [zonebediening](https://github.com/wpatrik14/aioaquarea/blob/d859f3727556c8a07964affd61a038edfd2d353a/aioaquarea/entities.py). SolarPilot gebruikt deze bediening niet.

## Gevolgde correcties

| Wijziging | Gecontroleerde status op 14 oktober 2026 | Vervolg |
|---|---|---|
| [Aquarea PR 129](https://github.com/wpatrik14/home-assistant-aquarea/pull/129): tankopwarming en pompstatus | Gemerged **10:43:00 UTC**, mergecommit `47c2327d2f8f92366b6f0ed64b59c469f0de0c52`; opgenomen in v1.5.3 | Bij WATER telt de tank alleen als heating wanneer pompstatus actief is; ontbrekende pompstatus behoudt upstream de oudere richtingsfallback. SolarPilot moet die fallback niet als afzonderlijk compressorbewijs behandelen. |
| [Aquarea PR 130](https://github.com/wpatrik14/home-assistant-aquarea/pull/130): release 1.5.3 | Gemerged **11:11:56 UTC**, mergecommit `8a61af19e2efa94f8df74188759b9fa58280b5c0`; release gepubliceerd | Release en daadwerkelijk lokaal geladen provider afzonderlijk controleren. Geen automatische providerupdate vanuit SolarPilot. |
| [aioaquarea PR 12](https://github.com/wpatrik14/aioaquarea/pull/12): globale toestand uit zones en tank | **Open, niet gemerged**; head `ebe561274e1d79160814474c175cfdb3469f61e5` | Een toekomstige gepubliceerde parsercorrectie opnieuw tegen SolarPilot-contracten testen. De huidige SolarPilot-presentatiecorrectie maakt geen upstream-programmabediening, leerbevestiging of SG-veiligheidsvrijgave. |
| [Aquarea PR 125](https://github.com/wpatrik14/home-assistant-aquarea/pull/125): cloud-UTC-dagen voor energiesensoren | **Open, niet gemerged**; head `458d5113aa3fcc063cdc271837dbba59a2a8ef6b` | Dag-/maandgrenzen, zomertijd en bestaande Recorderstatistiek afzonderlijk beoordelen. Geen cloud-energie herdateren of met SolarPilot-voedingsintegralen verwisselen zonder gevalideerd contract. |

## Aanvullend bronbewijs voor beta.86

De display-only correctie voor vernieuwde getypeerde status naast oudere zoneobjecten is gecontroleerd tegen de bestaande publieke contracten, zonder upstream-object of native-/koelcontrole te wijzigen:

| Publieke bron | Gecontroleerde Git-blob |
|---|---|
| [Aquarea v1.5.2 coordinator](https://github.com/wpatrik14/home-assistant-aquarea/blob/v1.5.2/custom_components/aquarea/coordinator.py) | `608f6312eb273e15399e363446263c781214f18e` |
| [aioaquarea-ng v1.3.1 entities](https://github.com/wpatrik14/aioaquarea/blob/v1.3.1/aioaquarea/entities.py) | `1da1832f657e14eb631b25b7499e9f90925d3650` |
| [aioaquarea-ng v1.3.1 data](https://github.com/wpatrik14/aioaquarea/blob/v1.3.1/aioaquarea/data.py) | `331db7801729f9e15f225b7394f47b37e1b0cda1` |
| [aioaquarea-ng v1.3.1 core](https://github.com/wpatrik14/aioaquarea/blob/v1.3.1/aioaquarea/core.py) | `564abc7a2391f0dc44056ad0d8dbe1cf825a2493` |

De provider-eigenschap `device_info` is in zowel Aquarea v1.5.2 als v1.5.3 gecontroleerd. Er is geen onbewezen fallback naar andere objectvormen. Een offline proef met ongewijzigde klassefuncties en synthetische A/B-statussen bevestigt dat eerdere zoneobjecten hun momentopname kunnen behouden terwijl de laatste getypeerde status is vervangen. SolarPilot gebruikt uitsluitend voor presentatie de huidige vaste poll met getypeerde waarden, geverifieerde binding en verse HA-overeenkomst. Deze proef bevat geen woninggegevens en certificeert geen lokale installatie, fysieke meetkwaliteit of SG-koelvrijgave. Afzonderlijke vendor-/probe-bestanden worden niet gepubliceerd.

## Onderhoud en publicatie

Een afzonderlijke, door de gebruiker geautoriseerde **ChatGPT-taak** controleert vanaf **21 oktober 2026** wekelijks op woensdag rond **19:00 Europe/Brussels** de relevante publieke GitHub-bronnen. Zij kan een relevante SolarPilot-correctie onderzoeken, bouwen, testen en publiceren volgens de normale releaseprocedure. Dit is een extern ontwikkelproces; de geïnstalleerde integratie bevat geen AI die op de achtergrond nieuwe software ontwikkelt of apparaten verandert.

Bij iedere controle worden release, commit, afhankelijkheid en PR-status opnieuw opgehaald. Een gewijzigd upstream-label zonder relevante codewijziging vereist geen nieuwe SolarPilot-release. Een relevante wijziging vraagt een vastgepinde bron, concrete regressie, behoud van gegevens en actuatorgrenzen, actuele guide/help/overdracht/installatie/rollback, volledige suite en alle vijf CI-gates op dezelfde bron. Pas daarna volgen de nieuwe tag en bytecontrole van de vier gepubliceerde assets. Open PR's, mislukte checks en onzeker bronbewijs worden niet als afgehandelde implementatie gepresenteerd.

De taak publiceert uitsluitend generieke code, tests en documentatie. Zij wijzigt geen lokale Home Assistant-installatie, provider, sensorkoppelingen, native Panasonic-instellingen of apparaten. Privé-exports en lokale analysefeedback blijven buiten GitHub. De brongebonden analyse van nieuwe door de gebruiker gedeelde exports blijft een afzonderlijk onderzoekspad.
