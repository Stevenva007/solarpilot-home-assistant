# Openbaar upstream-bronregister

## Hercontrole beta.106 — 24 oktober 2026

Defaultbranches, HEADs, laatste stabiele releases en tagcommits zijn opnieuw online gecontroleerd en ongewijzigd. Zie [UPSTREAM_BETA106.md](UPSTREAM_BETA106.md). De inhoudelijke beta.105-beoordeling hieronder blijft van toepassing.

## Actuele aanvullende broncontrole beta.105 — 23 oktober 2026

Aquarea **1.9.0** op `d3867f4143f7e2c15b84ed67c6e7ace2561f5f96` en SDK **1.5.0** op `55da9428ddf43ed26f2386d79c43d50cf4d9da0c` zijn inhoudelijk beoordeeld vanaf de hieronder bewaarde beta.103-bronnen. De wijzigingen betreffen authenticatie/appversieherstel; mislukte polls blijven ongeldige waarnemingen. De actuele pinned bronstand staat in `upstream_review.json`; vergelijking, impact en bewijsgrenzen staan in [de aanvullende bronbeoordeling](UPSTREAM_BETA105.md). Geen nieuw actuatorrecht of claim van lokale installatiecompatibiliteit.

## Historisch register tot en met beta.103

Laatst gecontroleerd: **21 oktober 2026 om 12:44:56 UTC**. Dit register beschrijft openbare broncontracten die voor SolarPilot relevant zijn. Een upstream-release is geen bewijs dat die versie lokaal is geïnstalleerd; een open pull request is geen gepubliceerde correctie. Gegevens uit privé-installaties, exports en automatiseringsidentiteiten horen niet in dit register.

Actueel: Aquarea **1.8.1** is in de aanvullende broncontrole voor beta.103 beoordeeld op zijn gewijzigde maandwissel. De SDK blijft **1.4.0**; de in beta.98 verwerkte status-/pollcontracten blijven afzonderlijk gelden. De controle van 21 oktober om 08:07:03 UTC beschrijft de toenmalige stand vóór publicatie van Aquarea 1.8.1 om 08:38:43 UTC. SDK PR12 is op 18 oktober 2026 gesloten zonder merge; de relevante statuscorrectie is via PR16 gepubliceerd. Onderstaande oudere bronpins en releasebeoordelingen behouden hun historische betekenis.

## Gepinde bronnen

| Bron | Gecontroleerde versie en commit | Betekenis voor SolarPilot |
|---|---|---|
| [Aquarea Smart Cloud](https://github.com/wpatrik14/home-assistant-aquarea/releases/tag/v1.8.1) | v1.8.1, gepubliceerd **21 oktober 2026 08:38:43 UTC**; commit `6717d82ccfb14708abb4a66f494b97418ad80863` | Voltooit eerst de oude cloudmaand en verwerkt daarna de nieuwe maand. De maandmeters bewaren de werkelijk getoonde bronmaand in hun native periode; statistieken resetten aan de nieuwe UTC-maandgrens. SolarPilot blijft de waargenomen periode projecteren en leidt geen bronmaand of meetdekking af uit de capturetijd. Status-/pollcontract, SDK en bedieningsrechten veranderen niet. |
| [Aquarea Smart Cloud](https://github.com/wpatrik14/home-assistant-aquarea/releases/tag/v1.8.0) | v1.8.0, gepubliceerd **18 oktober 2026 17:05:16 UTC**; commit `8722cf22e5a5752406aea1ba79b2cf48d4deedf3` | Vereist SDK ≥1.4.0, verwijdert niet-bestaande placeholderzones en voegt uitleesdiagnostiek/zonesensoren toe. Energie-/UTC-periodecontract blijft gelijk. SolarPilot controleert de nieuwe geladen bronbetekenis afzonderlijk. |
| [aioaquarea-ng](https://github.com/wpatrik14/aioaquarea/releases/tag/v1.4.0) | v1.4.0, gepubliceerd **18 oktober 2026 13:41:20 UTC**; commit `893065a81c014cb9aa1d3350446d61c01bccf3b9` | Scheidt eco/comfort-preset van operation_status, parseert via helpers en bouwt zones per apparaat opnieuw. De werkelijke getypeerde LIVE/CACHED-kwaliteit blijft bepalend; succesvolle cachefetch is geen actueel bewijs. De nieuwe native writes worden door SolarPilot niet gebruikt. |
| [Aquarea Smart Cloud](https://github.com/wpatrik14/home-assistant-aquarea/releases/tag/v1.7.0) | v1.7.0, gepubliceerd **18 oktober 2026 09:49:22 UTC**; commit `3151d7f196e45b671f3136c9220244fb8c10f2df` | Additief `auto_mode`-attribuut met de gekozen AUTO-richting, ook tijdens stilstand. Geen nieuwe actieve taak, native poll, compressor- of SG-vrijgave. Status-/actiemapping, consumptieroute en SDK blijven gelijk aan het vorige checkpoint. |
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

## Broncontrole voor beta.97 — 18 oktober 2026

De actuele Aquarea-defaultbranch en stabiele v1.7.0 zijn gecontroleerd op `3151d7f196e45b671f3136c9220244fb8c10f2df`. De daadwerkelijke diff sinds beta.96 voegt uitsluitend `auto_mode` voor AUTO_HEAT/AUTO_COOL toe, met documentatie, tests en versie. `hvac_mode`, `hvac_action`, coordinatorpoll, energie en SDK-afhankelijkheid veranderen niet. De SDK-main en stabiele v1.3.1 blijven `d859f3727556c8a07964affd61a038edfd2d353a`; PR12 is nog open. Zes gerichte regressies bewaken dat het additieve attribuut compatibel blijft en geen getypeerde poll, geladen semantiek, werkelijk actief bedrijf of SG-recht vervangt. Zie [vaste bronvergelijking en beoordeling](AQUAREA_UPSTREAM_REVIEW_BETA97.md) en `upstream_review.json`. Dit wijzigt geen provider of fysieke instelling.

## Broncontrole voor beta.98 — 18 oktober 2026, avond

De actuele defaultbranches en stabiele releases zijn opnieuw gecontroleerd op Aquarea `8722cf22e5a5752406aea1ba79b2cf48d4deedf3` en SDK `893065a81c014cb9aa1d3350446d61c01bccf3b9`. De parser verplaatst naar `parse_device_status`, met aparte `_device_operation_status`, presetparser en zoneopbouw. SpecialStatus is nu presetinformatie; de hoofdstatus kan uit expliciete operationStatus of ingeschakelde zones/tank komen. Die status is geen onafhankelijke compressor- of warmtevraagmeting.

SolarPilot gebruikt een afzonderlijke capture-time capability `aquarea_operation_status_action_v1`, broncontract `aioaquarea_ng_split_operation_status_v1` en `action_semantics=operation_status`. De oudere specialStatus-contracten blijven onder hun eigen oorspronkelijke bewijs bestaan. De negen gecontroleerde uitvoerbare functie-/helperbodies zijn onafhankelijk vergeleken met de gepinde primaire bron. Ook de werkelijk gepubliceerde SDK 1.4.0-wheel is geïsoleerd geladen en door de nieuwe inspecteur als deze capability herkend, zonder netwerk- of apparaatopdracht.

De getypeerde `DeviceStatus.data_mode` moet LIVE zijn. Een geslaagde coordinatorpoll met CACHED-data kan geen programma-, actie-, broncontract- of gekoppeld tankbewijs vernieuwen. Onafhankelijke daadwerkelijke vermogens- of generieke temperatuurbronnen blijven onder hun eigen gewone voorwaarden beschikbaar. Dit verruimt geen SG-/koelvoorwaarde en creëert geen native Panasonic-write.

Aquarea's EnergyConsumptionSensor (intervaldelta), EnergyAccumulatedConsumptionSensor, oorspronkelijke UTC-periode, metadata en maandfetch blijven in deze vergelijking gelijk. De SDK behoudt de Consumption-lijst als bestaande terugkeerwaarde via het nieuwe rijke rapport. SolarPilot leest uitsluitend de geregistreerde passende HA-bron en neemt nieuwe rapportmetadata, diagnostiek of zonesensoren niet automatisch over als extra bewijs of instelling. Zie de [volledige bronbeoordeling](https://github.com/Stevenva007/solarpilot-home-assistant/blob/main/docs/AQUAREA_UPSTREAM_REVIEW_BETA98.md) en `upstream_review.json`.

## Broncontrole voor beta.99 — 18 oktober 2026

Om **18:42:20 UTC** zijn via de officiële GitHub-bronnen alle acht checkpointgegevens opnieuw gecontroleerd: de defaultbranch, actuele HEAD, laatste gepubliceerde stabiele release en opgeloste releasetag van beide repositories. Aquarea blijft **1.8.0**, met `main` en tag op `8722cf22e5a5752406aea1ba79b2cf48d4deedf3`; de SDK blijft **1.4.0**, met `main` en tag op `893065a81c014cb9aa1d3350446d61c01bccf3b9`. Er zijn geen nieuwe upstreamverschillen sinds de inhoudelijke verwerking in beta.98. Het bijgewerkte checkpoint gebruikt daarom voor beide bronnen `reviewed_base_commit = head_commit` en `review_result = no_additional_changes`.

De bestaande afzonderlijke statuscontracten, LIVE/CACHED-controle, bronbinding en oorspronkelijke rapporttijden blijven gelden. De historische [beta.98-bronbeoordeling](https://github.com/Stevenva007/solarpilot-home-assistant/blob/main/docs/AQUAREA_UPSTREAM_REVIEW_BETA98.md) blijft behouden. Deze controle verandert geen provider, apparaatinstelling of actuatorrecht; de publicatiegate controleert de upstreamstand opnieuw vóór een release.

## Broncontrole voor beta.100 — 18 oktober 2026

Om **23:31:17 UTC** zijn via de GitHubconnector de acht officiële API-bronnen opnieuw gecontroleerd: repositorymetadata, actuele defaultbranch-HEAD, laatste gepubliceerde stabiele release en de opgeloste releasetag van beide repositories. Beide publieke repositories hebben nog `main` als defaultbranch. Beide releases hebben `draft=false`, `prerelease=false` en `target_commitish=main`; de tagverwijzingen wijzen rechtstreeks naar een commit.

| Bron | Actuele HEAD en opgeloste tagcommit | Laatste gepubliceerde stabiele release |
|---|---|---|
| [Aquarea main](https://api.github.com/repos/wpatrik14/home-assistant-aquarea/branches/main) | `8722cf22e5a5752406aea1ba79b2cf48d4deedf3`; [tagreferentie](https://api.github.com/repos/wpatrik14/home-assistant-aquarea/git/ref/tags/v1.8.0) | [v1.8.0](https://github.com/wpatrik14/home-assistant-aquarea/releases/tag/v1.8.0), gepubliceerd 18 oktober 2026 om 17:05:16 UTC |
| [SDK main](https://api.github.com/repos/wpatrik14/aioaquarea/branches/main) | `893065a81c014cb9aa1d3350446d61c01bccf3b9`; [tagreferentie](https://api.github.com/repos/wpatrik14/aioaquarea/git/ref/tags/v1.4.0) | [v1.4.0](https://github.com/wpatrik14/aioaquarea/releases/tag/v1.4.0), gepubliceerd 18 oktober 2026 om 13:41:20 UTC |

Alle checkpointvelden komen exact overeen met beta.99; er zijn geen nieuwe upstreamverschillen sinds de inhoudelijke verwerking in beta.98. Daarom blijven `reviewed_base_commit = head_commit`, `review_result = no_additional_changes` en `compatibility_claim = false` behouden. De afzonderlijke statuscontracten, LIVE/CACHED-controle, bronbinding en oorspronkelijke historische betekenis worden niet aangepast. Dit bronbewijs bevestigt de actualiteit van de beoordeelde publieke bronnen; het certificeert geen lokaal geladen provider, runtimecompatibiliteit of fysieke installatie. De publicatiegate controleert de upstreamstand opnieuw vóór een release.

## Broncontrole voor beta.101 — 19 oktober 2026

Om **18:30:51 UTC** zijn de acht officiële GitHub-records opnieuw vergeleken met het beta.100-checkpoint: repositorymetadata, actuele defaultbranch-HEAD, nieuwste gepubliceerde stabiele release en opgeloste releasetag van beide bronnen. Aquarea blijft **v1.8.0**, met `main` en tag op `8722cf22e5a5752406aea1ba79b2cf48d4deedf3`; de SDK blijft **v1.4.0**, met `main` en tag op `893065a81c014cb9aa1d3350446d61c01bccf3b9`. Beide publicatietijden, publieke repository-identiteiten, `main`-defaultbranches en stabiele releasestatus komen exact overeen. Er zijn geen aanvullende upstreamverschillen te verwerken; beide records behouden `reviewed_base_commit = head_commit` en `review_result = no_additional_changes`.

De bestaande Aquarea-statuscontracten, LIVE/CACHED-controle, oorspronkelijke tijden en actuatorgrenzen blijven behouden. De aanvullende uitsluitend uitlezende waterfunctie gebruikt bestaande gekozen HA-bronnen. De generieke officiële onderbouwing voor meterstand, debiet, lekindicatie en MQTT-actualiteit staat in [Waterbronnen beta.101](https://github.com/Stevenva007/solarpilot-home-assistant/blob/main/docs/WATER_BRONNEN_BETA101.md). Bronlabels of nominale publicatiecadans bewijzen geen oorspronkelijke fysieke meettijd en een lekindicatie is geen opdracht voor een waterklep. Dit brononderzoek bevat geen privébronidentiteiten en certificeert geen lokale installatie. De publicatiegate vergelijkt het checkpoint opnieuw vóór publicatie.

## Broncontrole voor beta.102 — 20 oktober 2026

Om **13:19:24 UTC** zijn de acht officiële GitHub-API-records opnieuw vergeleken met het beta.101-checkpoint: repositorymetadata, actuele defaultbranch-HEAD, nieuwste gepubliceerde stabiele release en opgeloste releasetag van beide bronnen. Aquarea blijft **v1.8.0**, met `main` en tag op `8722cf22e5a5752406aea1ba79b2cf48d4deedf3`; de SDK blijft **v1.4.0**, met `main` en tag op `893065a81c014cb9aa1d3350446d61c01bccf3b9`. Beide publieke identiteiten, defaultbranches, publicatietijden en stabiele releasestatus komen exact overeen. Beide tagreferenties wijzen rechtstreeks naar de genoemde commit. Er zijn geen aanvullende upstreamverschillen te verwerken; `reviewed_base_commit = head_commit`, `review_result = no_additional_changes` en `compatibility_claim = false` blijven behouden.

De afzonderlijke statuscontracten, LIVE/CACHED-controle, bronbinding en oorspronkelijke historische betekenis blijven van toepassing. Deze broncontrole bevestigt uitsluitend de actualiteit van het publieke checkpoint. Zij geeft geen nieuw bewijs van lokale runtimecompatibiliteit, sensoractualiteit, fysieke installatie of actuatorbevoegdheid. De historische beta.98-bronbeoordeling en beta.101-waterbronnen blijven behouden; de publicatiegate controleert de upstreamstand opnieuw vóór publicatie.

## Broncontrole voor beta.103 — 21 oktober 2026

Om **08:07:03 UTC** zijn de acht officiële GitHub-API-records opnieuw vergeleken met het beta.102-checkpoint: repositorymetadata, actuele defaultbranch-HEAD, nieuwste gepubliceerde stabiele release en opgeloste releasetag van beide bronnen. Aquarea blijft **v1.8.0**, met `main` en tag op `8722cf22e5a5752406aea1ba79b2cf48d4deedf3`; de SDK blijft **v1.4.0**, met `main` en tag op `893065a81c014cb9aa1d3350446d61c01bccf3b9`. Publieke identiteiten, defaultbranches, publicatietijden en stabiele releasestatus zijn ongewijzigd; beide tags wijzen rechtstreeks naar de genoemde commit. Er zijn geen aanvullende upstreamverschillen te verwerken. Beide records behouden `reviewed_base_commit = head_commit`, `review_result = no_additional_changes` en `compatibility_claim = false`.

De frontendcorrectie voor statusweergave in beta.103 geeft geen nieuwe provider- of actuatorbevoegdheid. De bestaande statuscontracten, LIVE/CACHED-controle, bronbinding en oorspronkelijke rapporttijden blijven afzonderlijke voorwaarden. Gelijke bron-SHA's zijn geen garantie voor lokale runtimecompatibiliteit, sensoractualiteit of fysieke installatie. Eerdere bronbeoordelingen blijven historisch behouden; de publicatiegate controleert de upstreamstand opnieuw vóór publicatie.

## Aanvullende broncontrole voor beta.103 — 21 oktober 2026, 12:44:56 UTC

De acht officiële GitHub-API-records tonen inmiddels Aquarea **v1.8.1**: `main` en de rechtstreeks opgeloste releasetag staan op `6717d82ccfb14708abb4a66f494b97418ad80863`, gepubliceerd om **08:38:43 UTC**. De SDK blijft **v1.4.0** op `893065a81c014cb9aa1d3350446d61c01bccf3b9`, gepubliceerd op 18 oktober om 13:41:20 UTC. Beide repositories zijn publiek, gebruiken `main` als defaultbranch en hebben een gepubliceerde stabiele release met `draft=false`, `prerelease=false` en `target_commitish=main`.

De [volledige Aquarea-vergelijking vanaf v1.8.0](https://github.com/wpatrik14/home-assistant-aquarea/compare/8722cf22e5a5752406aea1ba79b2cf48d4deedf3...6717d82ccfb14708abb4a66f494b97418ad80863) omvat drie commits en veertien bestanden. De relevante productieverschillen zitten in de maandkeuze van de coordinator (`_monthly_month_due` en `consumption_month`), de werkelijk getoonde maandperiode van `EnergyAccumulatedConsumptionSensor` en de uurstatistiekcorrectie met de nieuwe UTC-periodegrens als referentie voor de later geregistreerde reset. Daarnaast zijn versie, merkiconen, documentatie en tests aangepast. SDK-afhankelijkheid, statusmapping, klimaat-/tankentiteiten en de getypeerde statuspoll veranderen niet.

Bij de gebruikelijke maandwissel kan na **03:00 UTC** eerst nog de laatste oude maand worden opgehaald; de volgende maandfetch, gewoonlijk in het volgende uur, verwerkt de nieuwe maand. Een mislukte fetch behoudt de oude bronmaand. De native `period_being_processed` volgt de werkelijk verwerkte maand en wordt niet achteraf naar de capturemaand verplaatst.

De bestaande SolarPilot-projectie leest deze eigen native sensorperiode. Een bewaarde oude bronmaand blijft daarom die oude maand, met `period_contains_capture=false` wanneer het capturemoment erbuiten valt. De bekende kalenderperiode levert geen volledige meetdekking op: `coverage_complete=false` en ontbrekende `coverage_start/end` blijven onbekend. Oorspronkelijke fetch-/rapporttijden en historische punten krijgen geen nieuwe maand of bronversheid achteraf. De gerichte regressies in `tests/test_aquarea_rollover103.py` behandelen deze maandwissel en periodegrenzen; deze bronbeoordeling bevat geen testuitslag.

Het Aquarea-checkpoint gebruikt de eerdere `8722cf22e5a5752406aea1ba79b2cf48d4deedf3` als `reviewed_base_commit` en `review_result=relevant_changes_processed`. De ongewijzigde SDK houdt `reviewed_base_commit = head_commit` en `review_result=no_additional_changes`. `compatibility_claim=false` blijft voor de gehele beoordeling gelden. Deze verwerking geeft geen aanvullende beschikbaarheidsclaim, native schrijfbevoegdheid, SG-/koelvrijgave of installatieacceptatie; de publicatiegate controleert de actuele bronstand opnieuw.
