# SolarPilot beta.92 — test- en publicatieverslag

Versie: **1.0.0-beta.92** · 15 oktober 2026

Bouwbasis: gepubliceerde beta.91-commit `394e021eeaf731834bbfe178e5a7fc424f0803ee`. Deze update verwijdert uitsluitend de algemene analysemeldingsroute en werkt de bijbehorende uitleg bij. Er zijn geen private exports of lokale bronidentiteiten opgenomen.

## Gedrag

- Nieuwe of gewijzigde gewone bevindingen maken geen HA-melding, ook na meerdere dagen en met de oude voorkeur ingeschakeld. Meetkwaliteit en Export blijven de bevindingen tonen.
- Een oude analysemelding wordt uitsluitend onder haar eigen meldings-ID opgeruimd. Een mislukte poging wordt herhaald; een geaccepteerde verwijdering wordt niet herhaald wanneer alleen de ontvangstregistratie nog moet worden opgeslagen.
- Ontbrekende meldingsservice en meldings-/opslagtransportfouten maken geen nieuwe regelingsfout of fysieke opdracht.
- Een bestaande urgente toestelmelding overleeft het opruimen en verdwijnt pas na het normale herstel. De bestaande Aquarea-compatibiliteitsreporter blijft behouden.
- De online upstreamcontrole bevestigt ongewijzigde defaultbranch- en stabiele releasecommits voor Aquarea 1.5.4 en aioaquarea-ng 1.3.1.

## Validatie

Lokaal zijn **150 gerichte regressies geslaagd**, waaronder nieuwe meerdaagse stilte, oude voorkeur, upgrade-opruiming, tijdelijk ontbrekende meldingsservice, transportverlies, opslagfout en behoud van urgente meldingen. Actuele uitleg/mirrors, overdracht, repositorystructuur, publieke privacycontrole, SG-commandogrens, Python-syntax, beide JavaScript-syntaxcontroles en diffcontrole zijn geslaagd. De online upstreamcontrole is geslaagd.

De volledige lokale Python-suite is geslaagd: **6915 tests in 466,13 seconden**. Ook alle vijf CI-gates op PR-head `eff5e1910541aced5bc6a4f66b806fe9159c5d2b` en de oorspronkelijke main-commit `f92272a2560052e963783f323d938d47b965390f` zijn geslaagd. De definitieve verpakkingscorrectie voegt de vereiste bytegelijke componentkopie van dit testverslag toe; zij wijzigt geen Python- of JavaScript-regellogica. De nieuwe main-publicatie vereist opnieuw alle vijf CI-gates. Eerdere beta.91-totalen worden niet als beta.92-resultaat gebruikt. De repository-checks, HACS, Hassfest, echte Home Assistant-startup en Chromium moeten alle vijf op dezelfde definitieve bron slagen voordat de publicatiejob draait. Het gepubliceerde runresultaat is het brongebonden bewijs voor die controles.

## Publicatie

De [Validate-workflow](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml) maakt na alle geslaagde main-gates de nieuwe onveranderlijke annotated tag en vier assets:

- `SolarPilot-v1.0.0-beta.92-GitHub-HACS.zip`
- `SolarPilot-v1.0.0-beta.92-local.zip`
- `BETA92_INSTELLEN.md`
- `TESTRESULTATEN_BETA92.md`

De publicatiejob downloadt de vier assets terug en controleert exacte bronbytes, bestandsgrootte en SHA-256. Een bestaande tag of releaseasset wordt niet overschreven. Brongebonden CI en terugdownload bewijzen softwarepublicatie; zij bevestigen geen installatie in de woning.
