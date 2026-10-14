# SolarPilot beta.84 — brongebonden test- en releaseverslag

Versie: **1.0.0-beta.84** · 14 oktober 2026

Bouwbasis: gepubliceerde beta.83-commit `39b52464ec14d22f61be888c828c2db2fc989774`, tree `0403a7678f933494405a8815937a3a1788d410c0`. Die eerdere release is herkomstbewijs en geen beta.84-validatie.

## Concrete wijzigingen en bewijsgrenzen

Beta.84 introduceert een tijdelijke SG-keuze: Aan of Uit met uitsluitend 1800 of 3600 seconden, gevolgd door Automatisch. De absolute eindtijd wordt duurzaam bewaard; herstart begint de keuze niet opnieuw. Tijdelijk Aan is een expliciete gebruikersvraag die zonne-start, startvertraging, rust, anti-herhaalbeleid en zachte importstop vervangt. Harde elektrische-, bron-, profiel-, koel-, prioriteits-, lokale timer-, eigendoms- en globale modusvoorwaarden blijven vereist. Een reeds actieve sessie houdt haar oorspronkelijke hardmaximum, minimum en startanker.

De aanvankelijk geldig gestarte inschakelklok kan maximaal 300 s doorlopen tijdens een zachte zondip of tijdelijk ontbrekende/verouderde meting. Er volgt geen fysieke AAN zonder opnieuw verse volledige vrijgave. Nul resterend tijdens de onderbreking betekent wachten op herstel; binnen het venster geeft herstel geen volledige nieuwe vertraging. Bekende harde blokkering, gewijzigde modus/binding en langer interval resetten; ontbrekend is geen nul of bewezen wolk.

Een nieuw volledig bevestigd beta.84-checkpoint kan na een echte HA-herstart een matching nog gemeld AAN-contact onder verse passende voorwaarden voortzetten. Opgeslagen oude metingen, een onbekende of onzekere opdracht, een verlopen of gewijzigde timer en een oude beta.83-journal krijgen geen voortzettingsrecht. Normale unload en verwijderen blijven veilige vrijgave. Geen oude AAN-replay, lokale dertig-/zestigminutentimer, native Panasonic-write, fysieke compressorclaim of model-/gegevensreset.

Bij tijdelijk ontbrekende opstartbronnen kan uitsluitend de bestaande matching lokale timer onvernieuwd blijven lopen; bekende harde blokkeringen vragen veilige vrijgave. Een nog niet verlopen same-binding bewuste Aan-intentie kan na vervallen oude lease opnieuw onder volledige verse voorwaarden worden beoordeeld, zonder originele hardmaxreset of herstel van verlopen eigendom. Terugkeer van Aan naar Auto bewaart de oorspronkelijke continue-importtimer; zij koopt geen nieuwe vijf minuten.

De kaart en native HA-select bieden dezelfde vijf keuzes. Tijdelijke keuze, deadline, concrete blokkering, daadwerkelijk contact en lokale timer blijven apart; verlopen bediening keert terug naar Automatisch. API/service controleert beheerdersrecht, exacte entry, mode en duur; een late actie op afgesloten of vervangen runtime mag geen oude toestemming uitvoeren. Alle publieke fixtures zijn fictief; privé exports, woninglabels en bronidentiteiten maken geen deel uit van code, tests of pakketten.

## Lokale uitvoering

De definitieve lokale volledige regressiesuite is geslaagd: **5873 tests, 0 mislukt, 115,42 seconden**, Python 3.12.14 / pytest 9.1.1. De onafhankelijke review heeft geen open blokkerende bevindingen. Oudere releaseaantallen worden niet als beta.84-bewijs overgenomen.

| Controle | Lokaal resultaat |
|---|---|
| Volledige regressiesuite op definitieve beta.84-bron | 5873 geslaagd; 0 mislukt; 115,42 s |
| Tijdelijke Aan/Uit, absolute eindtijd, expiry naar Auto en onveranderde sessiegrenzen | Geslaagd binnen de volledige suite |
| Startklok bij korte zondip/brononderbreking, herstel met verse vrijgave en hard-/300 s-reset | Geslaagd binnen de volledige suite |
| Fresh restart, matching timer/binding/policy, bronverlies en legacy release-only | Geslaagd binnen de volledige suite |
| API/service/select-rechten, duurvalidatie en late runtimeactie | Geslaagd binnen de volledige suite |
| Kaart, status, duurkeuze, foutmeldingen en popupbehoud | Lokale regressies geslaagd; echte Chromium blijft afzonderlijke CI-gate |
| Guide, optiehulp en embedded mirrors | Actueel beta.84; 349 helpvelden; guidehash `111e4e4cbbd3111e` |
| Overdracht, privacy, repository en SG-opdrachtgrens | Geslaagd |
| Beide frontendmodules | Node-syntax geslaagd; fictief voorbeeld opnieuw gebouwd |
| Python en component-JSON | 86 component-Python-bestanden en 4 JSON-bestanden parsebaar |
| Diffcontrole en onafhankelijke review | Geslaagd |


De geslaagde regressies dekken beide tijdelijke duren, eindtijd over reload/herstart, expliciete Automatisch, originele hardmax/minimum en geen callback/replay na afsluiten. Restartregressies onderscheiden bewezen eigen ON met nieuwe verse gegevens van pending, onzeker, oud, extern gewijzigd, reeds OFF of verlopen bewijs. Veiligheids-, mode-, profiel-, koel-, bron- en prioriteitsgrenzen blijven afzonderlijk te testen. AUTO-expiry met goede voorwaarden mag geen UIT/AAN-puls veroorzaken; slechte voorwaarden moeten de gewone release volgen. OFF onderdrukt start alleen tot haar vastgelegde eindtijd, waarna de gewone fresh policy beslist.

Gerichte controlegroepen zijn afzonderlijk uitgevoerd: 156 native-/SG-/auditregressies, 1285 verzamelde SG-regressies plus 67 nieuwe/auditgevallen, 106 interface-/platform-/lifecyclegevallen en 54 nieuwe kaartgevallen. Deze groepen overlappen de volledige suite en elkaar; hun aantallen worden niet opgeteld. Zij bewaken onder meer oorspronkelijke importtimer bij terugkeer naar Auto, externe overname, veilig expliciet Uit, opslaan vóór dispatch, echte entry-/rechtencontrole, late acties en onbekende/ongeldige metadata.

**Echte Chromium, Home Assistant Core 2026.10.0 en PowerShell zijn in deze lokale ronde niet uitgevoerd.** Zij blijven afzonderlijke CI-proeven; lokale doubles vervangen die niet. Software-uitvoering bewijst geen geïnstalleerde HA-code, echt Shelly-timergedrag, compressorlooptijd, levensduurwinst, daadwerkelijk ontvangen SG of causale extra warmteopname.

## CI en publicatie op dezelfde exacte bron

Alle vijf gates van [Validate](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml) moeten op dezelfde exacte releasebron slagen:

1. Repositorycontroles, volledige suite, syntax en native PowerShell-publisherproeven.
2. HACS-validatie.
3. Hassfest.
4. Echte Home Assistant Core 2026.10.0: setup, platforms, reload, unload, immutable configuratie en de echte admin-/select-/servicegrens voor tijdelijke SG-bediening.
5. Echte Chromium: behouden browserproeven plus de afzonderlijke `tools/check_sg_ui.py`-stap voor tijdelijke SG-bediening en status op mobiele/brede schermen, met escape en behoud van open popup. Het meegeleverde voorbeeld gebruikt fictieve bronnen.

Niet uitgevoerde gates blijven open. Oudere CI-resultaten vormen geen beta.84-bewijs. De bestaande workflow publiceert pas na alle vijf gates en maakt daarna een nieuwe immutable annotated tag. Dit bronverslag bevat geen vooraf verzonnen run-ID of toekomstige geslaagde status.

## Pakketbewijs

De workflow vergelijkt vóór upload en na terugdownload alle vier assets bytegelijk met dezelfde bron-SHA:

- `SolarPilot-v1.0.0-beta.84-GitHub-HACS.zip`
- `SolarPilot-v1.0.0-beta.84-local.zip`
- `BETA84_INSTELLEN.md`
- `TESTRESULTATEN_BETA84.md`

Publicatie is pas bevestigd wanneer **Download and verify published four assets against the exact tag** slaagt met `download_verified: true`. Bekijk na publicatie de exacte tagcommit en gekoppelde push-run bij [release beta.84](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.84).

Instellingen, bronbindings, prioriteiten, modellen, historie en APP-aanvragen blijven behouden. Panasonic blijft SG-only, Wallbox read-only en AEG start-only. Gewone automatische SG-policy behoudt 600 W/300 s/minimum 1200 s; harde grenzen gelden ook voor tijdelijk Aan. Upgrade en rollback naar beta.83 staan in [BETA84_INSTELLEN.md](BETA84_INSTELLEN.md).
