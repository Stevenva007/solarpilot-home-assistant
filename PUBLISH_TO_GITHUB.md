# SolarPilot beta.45 publiceren — bestaande GitHub/HACS-repository

Beta.45 is gepubliceerd op onveranderlijke tag `v1.0.0-beta.45`, commit `507f74183f51b3517b077d05a455e4f169824f69`; [Validate 37029502122](https://github.com/Stevenva007/solarpilot-home-assistant/actions/runs/37029502122) is geslaagd met alle vier jobs. De softwaregate behaalde **1773 Python-tests in 10.05 s** en **veertien browsercontroles**, nul fysieke actuatoroproepen. De exacte ACK-adaptercorrectie herkent Aquarea Smart Cloud 1.0.61 (`aquarea`) en `panasonic_cc` via geregistreerde herkomst, zonder naamheuristiek. Gedownloade pakketten, HACS-installatie, geladen backend/kaart beta.45 en gecontroleerd hervatten van Auto zijn afzonderlijk bevestigd; een nieuwe latere live-doelrapportage blijft open.

Gebruik uitsluitend de bestaande repository `Stevenva007/solarpilot-home-assistant`. Maak geen nieuwe repository, force-push of verplaatste oude tags. Beta.45 en alle oudere tags, ZIP-assets en release-documentassets blijven onveranderd. Deze latere documentbijwerking op de hoofdbranch vervangt geen releasebestand; een volgende bronrelease vereist een nieuw versienummer.

## Bewezen live basis

Na HACS-installatie en normale volledige herstart op Core **2026.9.4** zijn backend/actuele uitleg én kaart afzonderlijk als **1.0.0-beta.45** bevestigd. De boilerstatus meldt exact `target_adapter_domains=['aquarea']`, `ack_poll_min_s=10` en contract `later_ha_report_at_or_after_adapter_delay`. Native taakbron en beveiligingen zijn gecontroleerd; gemeld ruimtebedrijf houdt de extra zonnebuffer beschermd. Powerful, Force DHW en Force Heater stonden uit. Zonder review/manual hold, fout of wachtende opdracht was geen extra review nodig; **Automatisch regelen** is via normale bediening hervat en teruggelezen.

Er is geen nieuwe doelopdracht afgedwongen. De bewaarde laatste succesvolle opdracht is nog de oudere beta.44-`ha_state`, geen nieuwe `delayed_ha_state`. Een volgende natuurlijke opdracht en passende latere rapportage blijven afzonderlijk te observeren, zonder fysieke proefstart of geforceerde opwarming. Native taakbron en afzonderlijke maandagdeadline zijn via de normale wizard gecontroleerd zonder APP-ticket/herarming/START. Er worden geen persoonlijke bedientijden, temperatuurwaarden of huishoudschema's gepubliceerd. Gemeten afwascyclusleren blijft uit zonder geschikte exclusieve W-meter.

Beta.44 blijft historische basis onder tag `v1.0.0-beta.44`, commit `5bbfa16cbc9453a818fb825fe16c447792ed63a2`, geslaagde Validate `37022762657`, 1760 tests/veertien browsercontroles. Die resultaten zijn geen beta.45-testtotaal.

## Lokale controle vóór publicatie

De lokale softwaregate is groen: volledige suite, veertien browsercontroles, actuele uitleg (`8eb8458f093da416`, 432 optieshulpvelden), handoff, repositoryvalidatie, publieke preflight, beide JavaScript-syntaxcontroles en diffcontrole. Beoordeel de complete beta.45-diff en behoud niet-gerelateerde gebruikerswijzigingen. Herhaal deze controles wanneer de werkelijk samengestelde bron nog verandert:

```powershell
$env:PYTHONUTF8="1"
$env:PYTHONDONTWRITEBYTECODE="1"
py -m pytest -q -p no:cacheprovider
py tools\check_handoff.py
py tools\check_current_explanation.py
py tools\validate_repository.py
py tools\check_public_repository.py
git -c core.autocrlf=false diff --check
git status --short
```

Behoud de werkelijk uitgevoerde resultaten in `docs/TESTRESULTATEN_BETA45.md`; leid geen nieuw totaal af uit losse suites. Laat beta.44-historie en bestaande releasebestanden intact.

## Eén beoordeelde releasecommit

Neem uitsluitend beoordeelde SolarPilot-releasewijzigingen op. Maak bij voorkeur één releasecommit om dubbele workflow-/e-mailruis te beperken.

```powershell
git diff --cached --stat
git commit -m "SolarPilot 1.0.0-beta.45 - recognise actual Aquarea delayed acknowledgement"
git push origin main
```

De workflow **Validate** draait op main, pull requests naar main of handmatig; een nieuwere run op dezelfde ref annuleert een oudere. Na groene repositorytests, pytest, HACS en Hassfest leest de publish-job de manifestversie. Alleen wanneer `v1.0.0-beta.45` niet bestaat, maakt zij de nieuwe tag, beide ZIP's en één prerelease, inclusief beta.45-installatie- en testdocumenten. Een tagpush start geen tweede automatische keten. **Manual Release** is alleen de noodroute voor een bestaande tag zonder release.

## Pakketcontrole na publicatie

Beide beta.45-ZIP's zijn daadwerkelijk gedownload en tegen de exacte tag gecontroleerd: verifier `errors=[]`, **254 repositorybestanden** en **100 integratiebestanden**, bytegelijk aan de tag. Manifestversie, padveiligheid en afwezigheid van private/cachebestanden zijn gecontroleerd.

- GitHub/HACS-ZIP: **1797247 bytes**; SHA-256 `d4e81596b92b164e646db5e7a0f904c389c837de98bb5a5cfb35d31fa7a1d32e`.
- Lokale ZIP: **709748 bytes**; SHA-256 `0ec3b6bdb19584bd55c4068306ca98c3c9463beda13c3cf6660332deda525916`.

De [beta.45-prerelease](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.45) is gepubliceerd op **2 oktober 2026 om 15:48:55 UTC**. Een groene workflow en pakketcontrole bewijzen geen geladen Home Assistant-versie. Vervang geen bestaande tag, ZIP-asset of release-documentasset.

## Installatie en livecontrole

Een nieuwe versleutelde volledige Home Assistant-back-up op de toegestane NAS voor beta.45 is gereed bevestigd. Dit is geen herstelproef; maak bij latere wijzigingen opnieuw een actuele back-up. Laat een beschermde cyclus afwerken zonder STOPRESET. Installeer exact beta.45 via HACS en herstart Home Assistant volledig. Bevestig backend en vernieuwde kaart afzonderlijk.

Houd **Alleen bekijken** of **Pauze** tijdens broncontrole. Controleer native adapterherkomst, tankmeting, gemeld doel, handmatige/krachtige functies, hygiëne, koeling/ruimteactie, P1/PV en pending opdrachten. Een gerichte review werkt alleen buiten Auto en schrijft zelf geen temperatuur. Herstel Auto pas na veilige installatiecontrole.

De eerste lokale optimistische echo is voor de exact herkende adapters geen ACK. Een passende latere HA-rapportage na minstens tien seconden moet afzonderlijk worden gezien. Ook `delayed_ha_state` blijft HA/cloudinformatie en geen onafhankelijk LIVE apparaat- of opwarmbewijs; forceer geen doelwijziging alleen om dit veld te vullen.

De native taakbron blijft read-only. PUMP meldt ruimtebedrijf, WATER een tapwatertaak, geen HEAT/COOL of elektrisch vermogen. De geïnstalleerde Aquarea-klimaatbron gebruikt gepatchte `current_action`; zij wordt niet als altijd verkeerde AUTO-weergave beschreven. Alle beta.44-prioriteits-, AEG-, comfort-, koel-, hygiëne-, eigendoms- en elektrische grenzen blijven behouden.

Powerful wordt niet automatisch als boilerboost gebruikt; ook DHW capacity blijft ongewijzigd. Geen fysieke proefstart, APP-herarming, Wallbox-opdracht, 60 °C-proef of leerreset voor acceptatie.

## Rollback

Kies Pauze, laat beschermde cycli afwerken en herstel onveranderlijke beta.44/back-up. Herstart en bevestig backend/kaart. Beta.44 mist nog de `aquarea`-ACK-herkenning; beschouw een vroege `ha_state` niet als guardbewijs en hervat Auto niet onbeoordeeld.

Zie `docs/BETA45_INSTELLEN.md`, `docs/TESTRESULTATEN_BETA45.md` en `docs/ACTUELE_WERKING.md`.
