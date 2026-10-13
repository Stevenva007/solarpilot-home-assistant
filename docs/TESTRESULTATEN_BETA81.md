# SolarPilot beta.81 — brongebonden test- en releaseverslag

Versie: **1.0.0-beta.81** · 13 oktober 2026

Bouwbasis: gepubliceerde beta.80-commit `cc700aa26bc26e35d310225e24b4737498230901`, tree `720fd147702d4db5635c1267772c7457a64f9268`. Die eerdere release is herkomstbewijs en geen beta.81-validatie.

## Concrete wijzigingen en bewijsgrenzen

De echte runtime-hook normaliseert een vertrouwd timezone-aware recorder-tijdstip uitsluitend voor SG-onderzoek naar eindige Unix-seconden. De datumvorm voor bestaande warmtepompgeschiedenis blijft intact. Een regressie via die werkelijke runtime-hook voorkomt dat afzonderlijke observer-tests deze grens opnieuw missen.

Een begrensd historisch checkpoint bewaart onderbroken SG-onderzoek als onvolledig en niet vergelijkbaar. Hij herstelt geen actuele cursor, bronzekerheid, eigendom, lease, contactclaim of opdracht. Controllerafsluiting, gemeld contact en transportfase worden afzonderlijk vastgelegd zonder transportgedrag, retries of SG-policy te veranderen.

Aanvullend bronbewijs onderscheidt originele rapporttijden van lokale observatie, onbekend van gemeten nul, en tijdscheefheid van een bewezen meterdefect. PV-kwartierafkeur en vooruit vastgelegde forecastcontext blijven diagnostisch; bestaande modelcriteria en realtime veiligheidsgrenzen blijven leidend. Tank-/programmatijdlijn en korte elektrische activiteitsweergave behouden de ruwe historie, meetgaten en bestaande historische leesrechten.

Alle publieke fixtures zijn fictief. Privé-export, CSV, analysefeedback, woninglabels en bronidentiteiten maken geen deel uit van repository, testdata of pakketten. Alleen generieke voorstel-ID's en de digest van hun betekenis horen in het vertrouwde implementatieregister, na daadwerkelijke implementatie en tests.

## Lokale uitvoering

De lokale volledige sweep is geslaagd: **5399 tests in 166,95 seconden**, Python 3.12.14 / pytest 9.1.1. Na de laatste uitleg-/presentatieafwerking en één aanvullende regressie zijn **120 gerichte tests** opnieuw geslaagd; ook de **19 optiehulp-/first-install-tests** slagen. Deze groepen overlappen en worden niet bij het volledige testaantal opgeteld. De definitieve verzameling bevat **5400 tests**; de CI voert die volledige verzameling op dezelfde exacte releasecommit uit.

| Controle | Lokaal resultaat |
|---|---|
| Volledige regressiesweep | 5399 geslaagd; 0 mislukt |
| Laatste uitleg, historie, onderzoeksweergave, dialogs en register | 120 geslaagd |
| Optiehulp en openbaar first-install-pakket | 19 geslaagd |
| Beide meegeleverde frontendmodules | Node-syntax geslaagd; Node v24.19.0 |
| Python en component-JSON | 307 Python-bestanden / 6 JSON-bestanden parsebaar |
| Guide, optiehulp en mirrors | Actueel beta.81; 345 optievelden |
| Overdracht, privacy-preflight en SG-opdrachtgrens | Geslaagd |
| Diffcontrole | Geslaagd |

**153 nieuwe regressiegevallen** ten opzichte van de beta.80-verzameling toetsen de echte recorder/runtime-hook, UTC/non-UTC/ongeldige tijden, checkpoints en bronverlies, transportfasen en latere readback, originele templateafhankelijkheden, tijdscheve net/PV, opslagrichting en onbekende inventaris, PV-afkeur/duplicaten/conflicten, vooruit bewaarde targets en restore, native tijdlijn/leesrechten/retentie, elektrische segmenten en veilige frontendweergave. Alleen de generieke voorstel-ID's en onafhankelijk gecontroleerde betekenisdigests zijn aan beta.81 gekoppeld. Privé export-ID's, hashes, metingen en woningcontext zijn niet gekopieerd.

De oorspronkelijke Forecast.Solar-uitgiftetijd blijft onbekend omdat de actuele HA-adapter haar niet levert; lokale vastlegging vóór het doel is afzonderlijk bewijs. Ook effectief native hygiënedoel en native voltooiing blijven onbekend zonder passende bron. De template-inspectie gebruikt uitsluitend de exact gekoppelde geladen state-template en haar succesvolle getypeerde RenderInfo; dynamische/brede of niet ondersteunde afhankelijkheden blijven begrensd/onvolledig. De relevante contractbestanden zijn gelijk voor Core 2026.10.0 en .1; de echte-Core-gate toetst de werkelijke typen en verzekert dat diagnostiek geen template rendert of ververst.

De aanvullende PV-browserproef gebruikt semantische detailsleutels en toetst vooraf vastgelegde waarden, afgekeurd kwartierbewijs, escape en behoud van open secties wanneer het kwartieraantal verandert. De optionele ingebouwde templatecomponent staat als after_dependency vermeld; bestaande templates worden uitsluitend geïnspecteerd, niet gerenderd of opnieuw ingesteld.

Nog niet uitgevoerde proeven worden niet als geslaagd voorgesteld. De onafhankelijke diffreview is akkoord; fysieke apparaatacceptatie valt buiten deze softwareproeven.

## CI en publicatie op dezelfde exacte bron

Alle vijf gates van [Validate](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml) moeten op dezelfde exacte releasebron slagen:

1. Repositorycontroles, volledige suite, syntax en native PowerShell-publisherproeven.
2. HACS-validatie.
3. Hassfest.
4. Echte Home Assistant Core 2026.10.0: setup, platforms, reload, unload, immutable configuratie en optionele bronselectoren.
5. Echte Chromium: alle behouden browserproeven en de nieuwe bewijsweergaven, met oorspronkelijke tijden, ontbrekende waarden, escape en behoud van invoer en open popup.

Chromium, PowerShell en de echte Core-uitvoering zijn afzonderlijke CI-proeven; lokale doubles vervangen die niet. Oudere CI-resultaten vormen geen nieuw beta.81-bewijs. De bestaande workflow publiceert pas na de vijf gates en maakt daarna een nieuwe immutable annotated tag.

## Pakketbewijs

De workflow vergelijkt vóór upload en na terugdownload alle vier assets bytegelijk met dezelfde bron-SHA:

- `SolarPilot-v1.0.0-beta.81-GitHub-HACS.zip`
- `SolarPilot-v1.0.0-beta.81-local.zip`
- `BETA81_INSTELLEN.md`
- `TESTRESULTATEN_BETA81.md`

Publicatie is pas bevestigd wanneer **Download and verify published four assets against the exact tag** slaagt met `download_verified: true`. Dit bronverslag bevat geen vooraf verzonnen toekomstig run-ID. Bekijk de exacte tagcommit en gekoppelde push-run bij [release beta.81](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.81).

Instellingen, bronbindings, prioriteiten, modellen, historie en APP-aanvragen blijven behouden. Panasonic blijft SG-only, Wallbox read-only en AEG start-only. De gekozen 600 W/300 s/minimum 1200 s en alle harde guards veranderen niet. Upgrade en rollback naar beta.80 staan in [BETA81_INSTELLEN.md](BETA81_INSTELLEN.md).
