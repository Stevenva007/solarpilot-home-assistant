# SolarPilot 1.0.0-beta.46 — testresultaten

Datum: **2026-10-03**

> **Definitieve softwaregate geslaagd:** de volledige samengestelde beta.46-bron behaalde **1813 geslaagde Python-tests in 6.79 s**. De actuele uitleg, optieshulp, handoff, repositoryvalidatie, publieke preflight, Pythoncompile, beide JavaScript-syntaxcontroles en diffcontrole zijn groen. Browserproeven zijn in deze omgeving niet opnieuw uitgevoerd; live installatie en fysieke opwarming zijn niet bevestigd.

## Bronbasis en onderzochte fout

De bestaande beta.45-hoofdbranch op commit `9cddb043f4e6b1547eaa9487e057692ffb1d1a5b` is de absolute codebasis. De gepubliceerde beta.45-tag op `507f74183f51b3517b077d05a455e4f169824f69` blijft onveranderd. Historische beta.45-testaantallen worden niet als beta.46-resultaat overgenomen.

Beta.45 kon een algemene `PUMP`-taak en de Panasonic AUTO/HEAT_COOL-behandeling boven betrouwbare native `aquarea`-actie `idle/off` plaatsen. Dat verklaart softwarematig een klimaatblokkering ondanks bruikbaar overschot. Zonder actuele Home Assistant-brontoegang is niet bevestigd dat dit de enige oorzaak in de getoonde installatie is.

## Definitieve softwaregate

- Volledige samengestelde Python-regressiesuite: **1813 geslaagd in 6.79 s**, geen afgeleid totaal uit losse suites.
- De bestaande beta.45-basis werd vóór wijzigingen lokaal apart gecontroleerd: **1773 geslaagd in 6.69 s**. De veertig nieuwe gerichte beta.46-regressies slaagden afzonderlijk in **0.18 s** en zijn daarna in het volledige resultaat hierboven opgenomen.
- Actuele-uitlegcontrole is groen: versie **1.0.0-beta.46**, uitleg-hash **`787cd40eaad0b73a`**. Alle **432 optieshulpvelden** zijn opnieuw gegenereerd; Nederlandse native veldbeschrijvingen en beide gebundelde actuele-uitlegbestanden zijn consistent.
- Handoffcontrole, repositoryvalidatie en publieke preflight zijn groen.
- Pythoncompile, beide JavaScript-syntaxcontroles en `git diff --check` zijn groen.
- De veertien bestaande browsercontroles zijn **niet opnieuw uitgevoerd**: Chromium ontbreekt en de Playwright-browserdownload gaf een afgebroken/truncated ZIP. Historische browserresultaten zijn niet als beta.46-resultaat overgenomen. Python-/UI-structuurtests en syntaxcontroles zijn wel geslaagd.

De nieuwe regressies dekken:

- Exact geregistreerde `aquarea` in AUTO/HEAT_COOL met verse `idle/off`, ook naast `PUMP` en oude of niet herkende optionele taakdata.
- Behoud van echte koeling en ruimtecomfortvoorrang voor `heating/preheating/defrosting`.
- Bescherming bij werkelijk ontbrekende, oude, restored, onbeschikbare of onbetrouwbare klimaatbron.
- Oudere `panasonic_cc` AUTO-ambiguïteit en uitsluitend actuele expliciete `IDLE/WATER`-vrijgave.
- Onbekend bewijs blokkeert nu maar start of verlengt geen koeluitloop; herstel met betrouwbaar idle krijgt geen nieuw verzonnen halfuur wachttijd.
- Vóór beta.46 opgeslagen koel-/onzekerheidstijden blijven conservatief behouden; de upgrade wist geen mogelijk echt koelverleden.
- Ruwe taakdiagnostiek en conservatief leren blijven intact; `PUMP` wordt geen normale rustsample.
- Behoud van beta.45-vertraagde doelbevestiging, timeout/manual hold/eigendom, normaal 50 °C/comfortgrens 46 °C, 60 °C-plafond, autonome sterilisatie, AEG-reserves en geen Wallboxkrediet voor extra 60 °C.
- Behoud van algemene taakbescherming voor andere adapters; vertrouwen op idle/off wordt niet naar alle klimaatkoppelingen verbreed.

## Publicatie en installatie

De publicatiecontrole staat bij de [beta.46-release](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.46) en [Validate-workflow](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml). De workflow publiceert pas na geslaagde repository-, HACS- en Hassfest-jobs onder een nieuwe onveranderlijke tag. De gedownloade releasepakketten worden afzonderlijk tegen die exacte tag gecontroleerd; deze brontekst claimt geen reeds uitgevoerde externe pakketcontrole. Er is in deze werksessie geen live Home Assistant-toegang. HACS-installatie, werkelijk geladen beta.46-backend/kaart, nieuwe latere doelbevestiging en fysieke opwarming zijn niet uitgevoerd of bevestigd.

Een geslaagde softwaretest bewijst geen compressorstart of bereikte tanktemperatuur. Er worden geen fysieke AEG-START/STOP, Wallbox-opdracht, Powerful, geforceerde 60 °C-opwarming of leerreset gebruikt om acceptatie te claimen.

Zie `BETA46_INSTELLEN.md` voor upgrade, broncontrole en rollback.
