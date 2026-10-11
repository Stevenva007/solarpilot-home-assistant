# SolarPilot beta.70 — test- en publicatiestatus

Bouwbasis: gepubliceerde beta.69, main en annotated tag `99249a68863432bec3e0a86081a5c218ed7ad400`, tree `32a1847b4c92551ca89c1080035715e984c49040`. De beta.69 Actions-run [38134201918](https://github.com/Stevenva007/solarpilot-home-assistant/actions/runs/38134201918) slaagde met vijf gates en publicatie; de vier gedownloade release-assets zijn exact met die bron vergeleken. Dat is bewezen bronherkomst, geen beta.70-validatie.

## Actuele beta.70-validatie

| Controle | Status |
| --- | --- |
| Volledige beta.70 pytest | Lokaal **3974 geslaagd in 61,19 s**, Python 3.12.14 en Node 24.19.0, zonder testcache/bytecode. |
| Nieuwe geschiedenis-/runtime-/API-/UI-regressies | **145 nieuwe cases**: 47 model, 90 runtime/API en 8 UI; onderdeel van de 3974, geen extra optelling. |
| Guide/hash/help en exacte documentmirrors | Geslaagd; guidehash `839bc3ba3619b35a`, drie exacte documentmirrors en bestaande helpcontroles. |
| Privacy, handoff, SG-grens, structuur, syntax en diff | Lokale controles geslaagd; geen huishoudelijke brondata in de publieke bestanden. |
| Vijf CI-gates op de exacte beta.70-SHA | Afzonderlijk uitvoeringsbewijs in [Actions](https://github.com/Stevenva007/solarpilot-home-assistant/actions); alle vijf zijn verplicht vóór publicatie. |
| Annotated tag en vier gepubliceerde assets | Afzonderlijke bron-/downloadcontrole in de publicatierun; de [release](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.70) wordt pas na de vijf gates aangemaakt. |

De beta.69-baseline had lokaal 3829 geslaagde cases in 60,40 s en in CI 3829 in 50,09 s. Die uitslagen worden niet als beta.70-testbewijs opgevoerd. Gerichte suites of meerdere scenario's binnen één test worden niet bovenop de volledige suite geteld. Alle nieuwe fixtures gebruiken fictieve bronnen en metingen.

## Getoetste nieuwe dekking

- Gescheiden lokale 30-dagenopslag, bewaren/laden/herstart en veilige behandeling van onleesbare of onbekende schema's zonder overschrijven.
- Native versus afgeleide activiteit/taken, onbekende grenzen, starts/stops, meetgaten, bronwijziging en lokale middernacht/DST.
- Gehele warmtepompenergie alleen tussen complete verse bevestigde exclusieve metingen met maximaal dertig seconden waarnemingsafstand; W/kW/nul, partial/stale/overlap/negatief/geschat en herhaalde echte brontijden.
- Afzonderlijke eigen SG-aanvraag, gemeld contact en ontvangen SG, zonder causale extra-kWh- of compressorlooptijdclaim.
- Alleen-lezen API met normale HA-bronleesrechten, entryvalidatie en geen fysieke opdrachten of instellingenwrites.
- Popup/dagselectie, 7/30-dagenbalken, taaklijnen, ontbrekende dagen, meetdekking, veilig ge-escapete tekst, stabiele verversing en mobiele browserlayout.
- Behoud van gewone verbruikerhistorie, modellen, tickets, analyse, beta.69-SG-startcredit, lease-/commandobescherming en bestaande apparaatfuncties.

## CI en publicatiegates

De bestaande vijf onafhankelijke gates blijven: repository/full suite, HACS, Hassfest, echte Home Assistant Core 2026.10 setup/reload/unload en echte browser op 320/390/768/1280 px. De nieuwe warmtepompgeschiedenis-browserproef komt bij de bestaande warmtepomp-/verbruikerhistorieproeven in dezelfde browsergate. Ze gebruikt fictieve data en de daadwerkelijk geleverde frontend.

Alle vijf gates moeten op dezelfde exacte beta.70-bron slagen voordat de bestaande main-workflow publiceert. Publicatie bouwt twee ZIPs uit de exacte commit en controleert de vier assets vóór upload en na geïsoleerde download op leden, bronbytes, grootte en SHA-256. Een nieuwe annotated tag mag geen bestaande release/tag vervangen. [Actions](https://github.com/Stevenva007/solarpilot-home-assistant/actions) levert het afzonderlijke SHA-/uitvoeringsbewijs.

## Grenzen van het bewijs

Lokale doubles en browserfixtures zijn geen live huishoudelijke HA-installatie of fysieke SG-/Panasonicproef. Een geregistreerde activiteit of native taak is geen aparte compressorlooptijd. Geïntegreerde totale elektrische meetenergie is geen warmteproductie, COP, energie per taak of causale SG-besparing. Het automatische voedingsprofiel bewijst geen bedrading of fysieke heaterverdeling. Ontvangen SG vereist zijn eigen actuele passende bron.

Echte fabrikant-/condensbeveiliging, timerafloop, externe writers en historische stilstandsoorzaak blijven afzonderlijke lokale bewijssoorten. De `via_device`-compatibiliteit vóór HA 2027.8 blijft een open punt. Installatie, behoud en rollback naar beta.69 staan in `BETA70_INSTELLEN.md`.
