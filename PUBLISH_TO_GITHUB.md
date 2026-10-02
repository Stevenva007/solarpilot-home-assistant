# SolarPilot beta.45 publiceren — bestaande GitHub/HACS-repository

Beta.45 is softwarematig klaar voor publicatie met **1773 geslaagde Python-tests in 10.05 s** en **veertien geslaagde browsercontroles**, met nul fysieke actuatoroproepen. De exacte ACK-adaptercorrectie herkent de live Aquarea Smart Cloud 1.0.61-koppeling (`aquarea`) en `panasonic_cc` via geregistreerde herkomst, zonder naamheuristiek. Beta.45 is nog niet gepubliceerd of geïnstalleerd; nieuwe pakketten en latere live-doelrapportage moeten afzonderlijk worden bevestigd.

Gebruik uitsluitend de bestaande repository `Stevenva007/solarpilot-home-assistant`. Maak geen nieuwe repository, force-push of verplaatste oude tags. Een nieuwe release krijgt tag `v1.0.0-beta.45`; beta.44 en alle oudere tags, ZIP-assets en release-documentassets blijven onveranderd.

## Bewezen live basis

Beta.44 is gepubliceerd onder tag `v1.0.0-beta.44`, commit `5bbfa16cbc9453a818fb825fe16c447792ed63a2`. Validate `37022762657`, ZIP-verificatie, HACS-installatie en geladen backend/kaart zijn bevestigd op Core 2026.9.4. De 1760 Python-tests en veertien browsercontroles horen bij beta.44, niet bij beta.45.

Native taakbron, afzonderlijke maandagdeadline en gerichte review zijn via normale bediening gecontroleerd zonder APP-ticket/herarming/START. Een vroege `ha_state` vóór tien seconden was geen bewijs van de bedoelde guard; de installatie is voor beta.45-controle gepauzeerd. Er worden geen persoonlijke bedientijden, temperatuurwaarden of huishoudschema's gepubliceerd. Gemeten afwascyclusleren blijft uit zonder geschikte exclusieve W-meter.

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

Download beide nieuwe beta.45-ZIP's. Controleer werkelijke SHA-256, manifestversie, padveiligheid, private/cachebestanden en inhoud tegenover de nieuwe tag. Een groene workflow bewijst geen geladen Home Assistant-versie. Vervang geen bestaande tag, ZIP-asset of release-documentasset.

## Installatie en livecontrole

Maak een actuele volledige back-up; de eerder bevestigde versleutelde NAS-back-up vóór beta.44 is geen herstelproef en bevat niet vanzelf later opgeslagen instellingen. Laat een beschermde cyclus afwerken zonder STOPRESET. Installeer exact beta.45 via HACS en herstart Home Assistant volledig. Bevestig backend en vernieuwde kaart afzonderlijk.

Houd **Alleen bekijken** of **Pauze** tijdens broncontrole. Controleer native adapterherkomst, tankmeting, gemeld doel, handmatige/krachtige functies, hygiëne, koeling/ruimteactie, P1/PV en pending opdrachten. Een gerichte review werkt alleen buiten Auto en schrijft zelf geen temperatuur. Herstel Auto pas na veilige installatiecontrole.

De eerste lokale optimistische echo is voor de exact herkende adapters geen ACK. Een passende latere HA-rapportage na minstens tien seconden moet afzonderlijk worden gezien. Ook `delayed_ha_state` blijft HA/cloudinformatie en geen onafhankelijk LIVE apparaat- of opwarmbewijs; forceer geen doelwijziging alleen om dit veld te vullen.

De native taakbron blijft read-only. PUMP meldt ruimtebedrijf, WATER een tapwatertaak, geen HEAT/COOL of elektrisch vermogen. De geïnstalleerde Aquarea-klimaatbron gebruikt gepatchte `current_action`; zij wordt niet als altijd verkeerde AUTO-weergave beschreven. Alle beta.44-prioriteits-, AEG-, comfort-, koel-, hygiëne-, eigendoms- en elektrische grenzen blijven behouden.

Powerful wordt niet automatisch als boilerboost gebruikt; ook DHW capacity blijft ongewijzigd. Geen fysieke proefstart, APP-herarming, Wallbox-opdracht, 60 °C-proef of leerreset voor acceptatie.

## Rollback

Kies Pauze, laat beschermde cycli afwerken en herstel onveranderlijke beta.44/back-up. Herstart en bevestig backend/kaart. Beta.44 mist nog de `aquarea`-ACK-herkenning; beschouw een vroege `ha_state` niet als guardbewijs en hervat Auto niet onbeoordeeld.

Zie `docs/BETA45_INSTELLEN.md`, `docs/TESTRESULTATEN_BETA45.md` en `docs/ACTUELE_WERKING.md`.
