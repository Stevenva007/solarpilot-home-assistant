# Openbaar upstream-bronregister

Laatst gecontroleerd: **17 oktober 2026**. Dit register beschrijft openbare broncontracten die voor SolarPilot relevant zijn. Een upstream-release is geen bewijs dat die versie lokaal is geïnstalleerd; een open pull request is geen gepubliceerde correctie. Gegevens uit privé-installaties, exports en automatiseringsidentiteiten horen niet in dit register.

## Gepinde bronnen

| Bron | Gecontroleerde versie en commit | Betekenis voor SolarPilot |
|---|---|---|
| [Aquarea Smart Cloud](https://github.com/wpatrik14/home-assistant-aquarea/releases/tag/v1.6.0) | v1.6.0, gepubliceerd **17 oktober 2026 19:29:31 UTC**; commit `f127489774c61c1e97ee5eb5097257748d55d510` | De vroegere dagsensoren zijn intervaldelta’s sinds de vorige uurgegevensfetch, zonder ENERGY-deviceclass of native dagperiode. Deze vormen geen dagelijks energie- of periodebewijs. Maandmeters, getypeerde statuspoll en `aioaquarea-ng>=1.3.1` blijven behouden; consumptie-interval standaard/minimaal 15 minuten. |
| [Aquarea Smart Cloud](https://github.com/wpatrik14/home-assistant-aquarea/releases/tag/v1.5.4) | v1.5.4, gepubliceerd **15 oktober 2026 09:52:26 UTC**; commit `4b5f7f3d2ad8c284fae5ff8c165707f69443a0fa` | Dag-/maandenergie volgt de UTC-cloudgrens. De getypeerde statuspoll, klimaat-/tankentiteiten en dependency `aioaquarea-ng>=1.3.1` houden hun bestaande taaksemantiek. SolarPilot controleert afzonderlijk de werkelijk geladen SDK 1.3.1 en de oorspronkelijke bronnen. |
| [Aquarea Smart Cloud](https://github.com/wpatrik14/home-assistant-aquarea/releases/tag/v1.5.3) | v1.5.3, gepubliceerd **14 oktober 2026 11:12:02 UTC**; commit `8a61af19e2efa94f8df74188759b9fa58280b5c0` | De native tankentiteit combineert waterrichting met pompstatus. Het manifest gebruikt nog `aioaquarea-ng>=1.3.1`; deze release corrigeert niet automatisch de library-mapping van globale bedrijfstoestand. |
| [Aquarea-basis vóór deze tankcorrectie](https://github.com/wpatrik14/home-assistant-aquarea/releases/tag/v1.5.2) | v1.5.2; commit `88abea3b6b42b30ec9b9f4f2d1eb4a5ff9eb2baa` van **10 oktober 2026** | Oudere tankweergave kan alleen waterrichting als opwarmcontext gebruiken. Vergelijk beide vaste bronversies; behandel een lokaal geselecteerd programma niet als nieuw actie- of compressorbewijs. |
| [aioaquarea-ng](https://github.com/wpatrik14/aioaquarea/releases/tag/v1.3.1) | v1.3.1, gepubliceerd **10 oktober 2026 11:49:16 UTC**; commit `d859f3727556c8a07964affd61a038edfd2d353a` | De parser koppelt globale `operation_status` nog aan `specialStatus`; `current_action` beoordeelt die OFF eerst. Verse afzonderlijke zone-/tank-/richting-/pompvelden hebben daarom een andere betekenis dan deze afgeleide globale OFF. |

Concrete code op vaste commits:

- [Aquarea manifest v1.5.3](https://github.com/wpatrik14/home-assistant-aquarea/blob/8a61af19e2efa94f8df74188759b9fa58280b5c0/custom_components/aquarea/manifest.json), [tankentiteit](https://github.com/wpatrik14/home-assistant-aquarea/blob/8a61af19e2efa94f8df74188759b9fa58280b5c0/custom_components/aquarea/water_heater.py) en [klimaatentiteit](https://github.com/wpatrik14/home-assistant-aquarea/blob/8a61af19e2efa94f8df74188759b9fa58280b5c0/custom_components/aquarea/climate.py).
- [Aquarea vergelijking v1.5.3–v1.5.4](https://github.com/wpatrik14/home-assistant-aquarea/compare/8a61af19e2efa94f8df74188759b9fa58280b5c0...4b5f7f3d2ad8c284fae5ff8c165707f69443a0fa), [v1.5.4 coordinator](https://github.com/wpatrik14/home-assistant-aquarea/blob/4b5f7f3d2ad8c284fae5ff8c165707f69443a0fa/custom_components/aquarea/coordinator.py), [energiesensoren](https://github.com/wpatrik14/home-assistant-aquarea/blob/4b5f7f3d2ad8c284fae5ff8c165707f69443a0fa/custom_components/aquarea/sensor.py) en [UTC-cloudcontract](https://github.com/wpatrik14/home-assistant-aquarea/blob/4b5f7f3d2ad8c284fae5ff8c165707f69443a0fa/custom_components/aquarea/statistics.py).
- [aioaquarea parser v1.3.1](https://github.com/wpatrik14/aioaquarea/blob/d859f3727556c8a07964affd61a038edfd2d353a/aioaquarea/device_manager.py), [gegevenssemantiek en current_action](https://github.com/wpatrik14/aioaquarea/blob/d859f3727556c8a07964affd61a038edfd2d353a/aioaquarea/data.py) en [zonebediening](https://github.com/wpatrik14/aioaquarea/blob/d859f3727556c8a07964affd61a038edfd2d353a/aioaquarea/entities.py). SolarPilot gebruikt deze bediening niet.

## Gevolgde correcties

| Wijziging | Gecontroleerde status op 15 oktober 2026 | Vervolg |
|---|---|---|
| [Aquarea PR 129](https://github.com/wpatrik14/home-assistant-aquarea/pull/129): tankopwarming en pompstatus | Gemerged **10:43:00 UTC**, mergecommit `47c2327d2f8f92366b6f0ed64b59c469f0de0c52`; opgenomen in v1.5.3 | Bij WATER telt de tank alleen als heating wanneer pompstatus actief is; ontbrekende pompstatus behoudt upstream de oudere richtingsfallback. SolarPilot moet die fallback niet als afzonderlijk compressorbewijs behandelen. |
| [Aquarea PR 130](https://github.com/wpatrik14/home-assistant-aquarea/pull/130): release 1.5.3 | Gemerged **11:11:56 UTC**, mergecommit `8a61af19e2efa94f8df74188759b9fa58280b5c0`; release gepubliceerd | Release en daadwerkelijk lokaal geladen provider afzonderlijk controleren. Geen automatische providerupdate vanuit SolarPilot. |
| [aioaquarea PR 12](https://github.com/wpatrik14/aioaquarea/pull/12): globale toestand uit zones en tank | **Open, niet gemerged**; head `ebe561274e1d79160814474c175cfdb3469f61e5` | Een toekomstige gepubliceerde parsercorrectie opnieuw tegen SolarPilot-contracten testen. De huidige SolarPilot-presentatiecorrectie maakt geen upstream-programmabediening, leerbevestiging of SG-veiligheidsvrijgave. |
| [Aquarea PR 125](https://github.com/wpatrik14/home-assistant-aquarea/pull/125): cloud-UTC-dagen voor energiesensoren | Gemerged **15 oktober 09:49:32 UTC**, mergecommit `30a645d82e028dcb2f467d49a0e5c204477b74d1`; opgenomen in v1.5.4 | Alleen de werkelijk waargenomen eigen sensorperiode beschrijft de cloudaggregatie. De publieke `period_being_processed` kan bij upgrade nog een oude lokale periode bevatten. Geen grens afleiden uit exporttijd, naam, watts of alleen UTC-versielabel; geen cloudenergie met lokale voedingsintegralen verwisselen zonder gelijke uren, scope en meetdekking. |

## Aanvullend bronbewijs voor beta.86

De display-only correctie voor vernieuwde getypeerde status naast oudere zoneobjecten is gecontroleerd tegen de bestaande publieke contracten, zonder upstream-object of native-/koelcontrole te wijzigen:

| Publieke bron | Gecontroleerde Git-blob |
|---|---|
| [Aquarea v1.5.2 coordinator](https://github.com/wpatrik14/home-assistant-aquarea/blob/v1.5.2/custom_components/aquarea/coordinator.py) | `608f6312eb273e15399e363446263c781214f18e` |
| [aioaquarea-ng v1.3.1 entities](https://github.com/wpatrik14/aioaquarea/blob/v1.3.1/aioaquarea/entities.py) | `1da1832f657e14eb631b25b7499e9f90925d3650` |
| [aioaquarea-ng v1.3.1 data](https://github.com/wpatrik14/aioaquarea/blob/v1.3.1/aioaquarea/data.py) | `331db7801729f9e15f225b7394f47b37e1b0cda1` |
| [aioaquarea-ng v1.3.1 core](https://github.com/wpatrik14/aioaquarea/blob/v1.3.1/aioaquarea/core.py) | `564abc7a2391f0dc44056ad0d8dbe1cf825a2493` |

De provider-eigenschap `device_info` is in zowel Aquarea v1.5.2 als v1.5.3 gecontroleerd. Er is geen onbewezen fallback naar andere objectvormen. Een offline proef met ongewijzigde klassefuncties en synthetische A/B-statussen bevestigt dat eerdere zoneobjecten hun momentopname kunnen behouden terwijl de laatste getypeerde status is vervangen. SolarPilot gebruikt uitsluitend voor presentatie de huidige vaste poll met getypeerde waarden, geverifieerde binding en verse HA-overeenkomst. Deze proef bevat geen woninggegevens en certificeert geen lokale installatie, fysieke meetkwaliteit of SG-koelvrijgave. Afzonderlijke vendor-/probe-bestanden worden niet gepubliceerd.

## Aanvullend bronbewijs voor beta.91

De vergelijking met v1.5.4 verandert uitsluitend de energiedatum-/statistiekroute, het manifest en bijhorende documentatie/tests. De bestaande coordinatorstatusroute blijft `get_device` gevolgd door `refresh_data`; `climate.py` en `water_heater.py` veranderen niet. De exacte combinatie **Aquarea 1.5.4 + werkelijk geladen aioaquarea-ng 1.3.1** gebruikt daarom hetzelfde begrensde read-only displaycontract. Ruwe `specialStatus` 0, 1 en 2 worden in de SDK respectievelijk `OperationStatus.OFF`, `ON`, `UNKNOWN`; `current_action` toetst OFF eerst en kiest anders op richting. Dit maakt een presetwaarde geen onafhankelijke hoofd-AAN/UIT-meting. Oorspronkelijke ruwe acties, bronbinding, vijf seconden maximale onderlinge native rapportafstand, ontbrekende/oude/toekomstige bronwaarden en conflictregels blijven behouden. De nieuwe versie verleent geen conservatief leerbewijs of SG-/koelvrijgave.

| Publieke bron v1.5.4 | Gecontroleerde Git-blob |
|---|---|
| [coordinator.py](https://github.com/wpatrik14/home-assistant-aquarea/blob/4b5f7f3d2ad8c284fae5ff8c165707f69443a0fa/custom_components/aquarea/coordinator.py) | `ef6341ab550d767c5c2e4f459897cedf6de4832b` |
| [sensor.py](https://github.com/wpatrik14/home-assistant-aquarea/blob/4b5f7f3d2ad8c284fae5ff8c165707f69443a0fa/custom_components/aquarea/sensor.py) | `1527f9a68c18e09a0c53ae11f52d1c048d4c03ac` |
| [statistics.py](https://github.com/wpatrik14/home-assistant-aquarea/blob/4b5f7f3d2ad8c284fae5ff8c165707f69443a0fa/custom_components/aquarea/statistics.py) | `cb28190bb47781d22adc43b7110df971e7728544` |

Nieuwe actuele exportpunten kunnen provider, bronsoort, scope, oorspronkelijke native sensorperiode, UTC-kalendergrenzen en afzonderlijke echte bronfetch-/HA-rapporttijd bewaren. Uitsluitend exact geregistreerde eigen providerentiteiten tellen mee. Niet beschikbare native periode of een herstelde lokale middernacht blijft expliciet onbekend. Een kalendergrens is geen gemeten dekkingsgrens: `coverage_start/end` blijven onbekend en `coverage_complete` blijft false. Lokale SolarPilot-dagen worden niet met ongelijke clouduren vergeleken, herverdeeld of geschaald; historische samples krijgen geen huidige providergegevens achteraf. Regressies dekken UTC/lokale middernacht, maand-/jaarwisseling, schrikkelmaand en beide Belgische tijdwissels.

## Onderhoud en publicatie

Een afzonderlijke, door de gebruiker geautoriseerde **ChatGPT-taak** controleert vanaf **21 oktober 2026** wekelijks op woensdag rond **19:00 Europe/Brussels** de relevante publieke GitHub-bronnen. Zij kan een relevante SolarPilot-correctie onderzoeken, bouwen, testen en publiceren volgens de normale releaseprocedure. Dit is een extern ontwikkelproces; de geïnstalleerde integratie bevat geen AI die op de achtergrond nieuwe software ontwikkelt of apparaten verandert.

Bij iedere controle worden release, commit, afhankelijkheid en PR-status opnieuw opgehaald. Een gewijzigd upstream-label zonder relevante codewijziging vereist geen nieuwe SolarPilot-release. Een relevante wijziging vraagt een vastgepinde bron, concrete regressie, behoud van gegevens en actuatorgrenzen, actuele guide/help/overdracht/installatie/rollback, volledige suite en alle vijf CI-gates op dezelfde bron. Pas daarna volgen de nieuwe tag en bytecontrole van de vier gepubliceerde assets. Open PR's, mislukte checks en onzeker bronbewijs worden niet als afgehandelde implementatie gepresenteerd.

De taak publiceert uitsluitend generieke code, tests en documentatie. Zij wijzigt geen lokale Home Assistant-installatie, provider, sensorkoppelingen, native Panasonic-instellingen of apparaten. Privé-exports en lokale analysefeedback blijven buiten GitHub. De brongebonden analyse van nieuwe door de gebruiker gedeelde exports blijft een afzonderlijk onderzoekspad.

## Verplichte bronreview bij iedere SolarPilot-update

Iedere nieuwe SolarPilot-update controleert de actuele Aquarea-defaultbranch, laatste gepubliceerde release en werkelijke SDK-bron. Vergelijk met docs/upstream_review.json, beoordeel alle relevante nieuwe verschillen en verwerk noodzakelijke wijzigingen met regressies in dezelfde release. tools/check_upstream_review.py blokkeert publicatie bij onbeoordeelde bronwijzigingen of mislukte controle. Een open PR of prerelease wordt niet automatisch geïnstalleerd.

Op 15 oktober 2026 zijn beide actuele defaultbranch-heads en laatste stabiele releasetags opnieuw gecontroleerd: Aquarea `4b5f7f3d2ad8c284fae5ff8c165707f69443a0fa` / v1.5.4; aioaquarea `d859f3727556c8a07964affd61a038edfd2d353a` / v1.3.1. Er zijn geen nieuwe onbeoordeelde commits ten opzichte van deze pins. SDK PR12 blijft open en is geen geïnstalleerde correctie. Het machineleesbare checkpoint is `docs/upstream_review.json`.

Runtimecompatibiliteit gebruikt een begrensde inspectie van daadwerkelijk geladen parser-/gettersemantiek, geen vaste versie-allowlist. Een gelijkblijvend bewezen contract blijft bij toekomstige versies bruikbaar. Een gewijzigd contract wordt gericht gemeld en via de normale geteste herstelprocedure bijgewerkt; onvoorzienbare toekomstige wijzigingen kunnen niet vooraf worden gegarandeerd. Historisch opgeslagen exact-versiebewijs wordt niet met huidige metadata opgewaardeerd. De bestaande onderhoudstaak is uitgebreid met deze vaste releasevoorwaarde en zelfstandige herstelpublicatie; zij installeert geen software op Home Assistant en ontvangt geen lokale meldingen.

## Broncontrole voor beta.92

De online bronreviewgate is op 15 oktober 2026 opnieuw uitgevoerd. Beide actuele defaultbranch-HEADs en laatste gepubliceerde stabiele releasetags/commits komen exact overeen met het bestaande checkpoint: Aquarea 1.5.4 en aioaquarea-ng 1.3.1. Er zijn geen nieuwe relevante verschillen te verwerken. Beta.92 wijzigt uitsluitend algemene analysemeldingen en hun uitleg; geladen semantiek, bronactualiteit en bedieningsgrenzen blijven gelijk. Het bijbehorende reviewtijdstip staat in `upstream_review.json`.

## Broncontrole voor beta.93

Op 16 oktober 2026 zijn beide actuele defaultbranch-HEADs en laatste stabiele releasecommits opnieuw online gecontroleerd. Aquarea 1.5.4 en aioaquarea-ng 1.3.1 zijn ongewijzigd tegenover het beoordeelde checkpoint. Er zijn geen nieuwe upstreamverschillen te verwerken. Beta.93 corrigeert de kortstondige metadata-invalidatie tijdens de periodieke achtergrondinspectie en isoleert ontbrekende Wallbox-telemetrie van werkelijk gemeten P1-restinjectie voor andere lasten. Echte polls, bronactualiteit, geladen semantische identiteit en actuator-/leerrechten blijven gescheiden; onbekende EV-data creëert geen vermogenskrediet.

## Broncontrole voor beta.94

Op 16 oktober 2026 zijn beide actuele defaultbranch-HEADs en de laatste stabiele releasecommits opnieuw online gecontroleerd. Aquarea 1.5.4 en aioaquarea-ng 1.3.1 zijn ongewijzigd tegenover het beoordeelde checkpoint. Er zijn geen nieuwe upstreamverschillen te verwerken. Beta.94 bewaart uitsluitend de bevestigde UIT-tijd van gewone verbruikers voor rusttijdherstel na een herstart. Deze tijd geeft geen actuatorrecht of bronactualiteit en verandert geen Aquarea-semantiek, native bediening of SG-bevoegdheid.

## Controle voor beta.95

Op 17 oktober 2026 om 13:49:03 UTC zijn beide actuele defaultbranch-HEADs en laatste stabiele releasetags opnieuw gecontroleerd en opgelost naar de bovenstaande commits. Beide vergelijkingen bevatten nul nieuwe commits of bestanden. SDK PR12 blijft open, niet gemerged en ongewijzigd; er is geen nieuwe gepubliceerde implementatie over te nemen. De verplichte publicatiegate controleert dit checkpoint opnieuw. De vier SolarPilot-correcties veranderen geen parser-/taaksemantiek of native schrijfrecht.

## Broncontrole voor beta.96 — 17 oktober 2026

Aquarea v1.6.0 (`f127489774c61c1e97ee5eb5097257748d55d510`, gepubliceerd 19:29:31 UTC) is vergeleken met v1.5.4. De vier vroegere dagsensoren worden intervallen sinds de vorige cloudfetch, zonder ENERGY-deviceclass of period_being_processed. Maandmeters blijven bestaan; het standaard/minimale consumptie-interval wordt 15 minuten. De getypeerde statuspoll en klimaat-/tanksemantiek veranderen niet. De werkelijk gepubliceerde SDK blijft v1.3.1. SolarPilot weigert de gewijzigde intervallen al als dagperiodebewijs; `test_aquarea_160_interval_delta_is_not_relabelled_as_daily_energy` borgt dit. Dit is geen geïnstalleerde providerupdate en geen claim van hardwareacceptatie.

Beta.96 deelt uitsluitend presentatieberekeningen per publicatie en gebruikt geregistreerde HA-hub-id's op moderne Core-versies. Directe regelingslezingen, oorspronkelijke tijden, apparaatidentiteiten en de oude HA-terugval blijven behouden. De publicatie volgt uitsluitend na alle vijf brongebonden CI-gates; dit is geen automatische providerupdate.
