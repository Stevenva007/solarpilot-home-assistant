# SolarPilot beta.40 publiceren — bestaande GitHub/HACS-repository

Dit pakket is de volledige cumulatieve bron van **1.0.0-beta.40**. Gebruik uitsluitend de bestaande repository `Stevenva007/solarpilot-home-assistant`; maak geen nieuwe repository, force-push of verplaatste oude tags.

## Voor publicatie

Gebruik de GitHub/HACS-ZIP als bron en controleer lokaal:

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

## Eén commit naar main

Beoordeel de diff en maak bij voorkeur **één** releasecommit. Dit beperkt GitHub Actions- en e-mailruis.

```powershell
git add -A
git diff --cached --stat
git commit -m "SolarPilot 1.0.0-beta.40 - bounded post-start dishwasher recovery"
git push origin main
```

De workflow **Validate** start alleen op `main`, pull requests naar `main` of handmatig. Er is geen dagelijkse schedule meer. Een nieuwere run op dezelfde ref annuleert een oudere lopende run.

Vervang vóór de release alle velden `NOG UIT TE VOEREN` in `docs/TESTRESULTATEN_BETA40.md` door de werkelijk uitgevoerde resultaten. Publiceer niet op basis van voorlopige of afgeleide aantallen.

Na groene repositorytests, pytest, HACS-validatie en Hassfest leest dezelfde workflow de manifestversie. Wanneer `v1.0.0-beta.40` nog niet bestaat, maakt ze één tag, beide releasepakketten (`local` en `GitHub-HACS`) en één prerelease. De workflow voegt de installatiehandleiding en het testverslag van de actuele manifestversie als release-assets toe. Een tagpush start dus geen tweede automatische Validate-/Release-keten.

**Manual Release** is alleen de noodroute voor een bestaande tag die nog geen GitHub-release heeft.

## Home Assistant

Maak vóór update een back-up. Installeer de nieuwe release en herstart Home Assistant. Een lopende afwascyclus wordt niet onderbroken. Controleer dat Home Assistant werkelijk `1.0.0-beta.40` heeft geladen en geef de begrensde recovery maximaal tien minuten om laat geladen template-/AEG-entiteiten te zien. Controleer daarna de AEG-afwasmachine, de centrale Voorrang en `dishwasher_setup`. De migratie verstuurt geen START. Voor een nieuwe afwasaanvraag moet APP/remote-start een nieuwe overgang naar exact `Enabled` maken; als APP al aan stond bij startup, eerst uit en opnieuw aan.

Zie `docs/BETA40_INSTELLEN.md`, `docs/TESTRESULTATEN_BETA40.md` en `docs/ACTUELE_WERKING.md`.
