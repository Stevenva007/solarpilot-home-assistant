# SolarPilot 1.0.0-beta.47 — testresultaten

Datum: **2026-10-03**

> **Definitieve softwaregate geslaagd:** de volledige samengestelde beta.47-bron behaalde **1884 geslaagde Python-tests in 5.67 s**. Dit omvat 71 nieuwe herstartregressies. Drie echte JavaScript-rendergevallen via Node VM zijn groen; de volledige browserproeven zijn niet uitgevoerd. Live Home Assistant-installatie en fysieke toestelactie zijn niet bevestigd.

## Bronbasis

Beta.46 op commit `c9ea80de746d0f0f25f5b127bcafaaf88f624b65` is de absolute codebasis. Beta.46 en oudere tags en releasebestanden blijven onveranderd. Historische testaantallen worden niet als beta.47-resultaten gebruikt.

## Definitieve softwaregate

- Volledige samengestelde regressiesuite: **1884 geslaagd in 5.67 s**, geen afgeleid totaal uit losse suites.
- Nieuwe herstartdekking: **71 regressies** — 35 gewone runtime-/modus-/leasegevallen en 36 boilergevallen. Deze zijn opgenomen in het volledige resultaat hierboven.
- Actuele-uitlegcontrole: versie **1.0.0-beta.47**, uitleg-hash **`e0f26acd2b5c961e`**, **432 gegenereerde optieshulpvelden**; native Nederlandse veldbeschrijvingen en beide actuele-uitlegbestanden consistent.
- Pythoncompile: **65 bestanden** geslaagd. Beide JavaScript-syntaxcontroles zijn groen.
- Drie uitgevoerde Node VM-rendergevallen gebruiken de echte `_globalAlerts`-methode: automatisch bronwachten zonder resetknop, echte fout met controlebediening en veilig ge-escapete fallback-toestelnamen.
- De volledige veertien browsercontroles zijn **niet uitgevoerd**. Er is hier geen werkende Chromium-installatie; Node VM-rendering en Python-/UI-structuurtests vervangen geen browseracceptatie.
- Handoff, repositoryvalidatie, publieke preflight en diffcontrole horen bij de eindgate; externe pakketverificatie volgt afzonderlijk op GitHub-publicatie.

De regressies omvatten automatisch herstartherstel bij later geladen/unknown/unavailable/restored bronnen, persistent hervatintentie over een volgende herstart, bewuste Observe/Pauze-keuzes, nauw begrensde oude opslagreparatie, numerieke instellingen die tijdens herstart veranderen, behouden minimumlooptijden en geen opdrachtreplay. Voor AEG zijn lopende/voltooide cyclus, verbruiken van APP-aanvragen en geen herarming door later Idle gedekt; een onduidelijke eerdere START krijgt geen tweede START en echte fouten blijven bestaan.

Boilerdekking omvat routineherstel met passend doel, tijdelijk ontbrekende temperatuur-/doel-/beschermingsdata, nieuwe postrestart rapportage voor pending opdrachten, adapterwachttijd, gewijzigd doel/manual hold/fouten, beschermde fabrikantdoelen, persisted hersteljournal over een volgende herstart en busy-status bij veilig verwijderen. Alle behouden beta.46-klimaat-/koel-/ACK-, prioriteits-, AEG-, temperatuur- en Wallboxgrenzen blijven onderdeel van de volledige suite.

## Publicatie en installatie

De publicatiecontrole staat bij de [beta.47-release](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.47) en [Validate-workflow](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml). De workflow publiceert pas na geslaagde repository-, HACS- en Hassfest-jobs onder een nieuwe onveranderlijke tag. Pakketverificatie wordt afzonderlijk tegen die exacte tag uitgevoerd.

Geen live Home Assistant-installatie of fysieke toestelactie is in deze werksessie uitgevoerd. Softwaretests bewijzen geen compressorstart of bereikte tanktemperatuur. Er worden geen AEG-START/STOP, Wallbox-opdrachten, Powerful, geforceerde tankopwarming of leerreset uitgevoerd om testacceptatie te claimen.
