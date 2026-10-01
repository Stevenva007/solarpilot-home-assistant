# SolarPilot beta.41 publiceren — bestaande GitHub/HACS-repository

Dit pakket is de volledige cumulatieve bron van **1.0.0-beta.41**. Gebruik uitsluitend de bestaande repository `Stevenva007/solarpilot-home-assistant`; maak geen nieuwe repository, force-push of verplaatste oude tags. Publiceer beta.41 als nieuwe prerelease; wijzig de reeds geregistreerde beta.40-tag niet.

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
git commit -m "SolarPilot 1.0.0-beta.41 - clear controls and safe runtime boundaries"
git push origin main
```

De workflow **Validate** start alleen op `main`, pull requests naar `main` of handmatig. Er is geen dagelijkse schedule meer. Een nieuwere run op dezelfde ref annuleert een oudere lopende run.

Vervang vóór de release alle velden `NOG UIT TE VOEREN` in `docs/TESTRESULTATEN_BETA41.md` door de werkelijk uitgevoerde resultaten. Publiceer niet op basis van voorlopige of afgeleide aantallen.

Na groene repositorytests, pytest, HACS-validatie en Hassfest leest dezelfde workflow de manifestversie. Wanneer `v1.0.0-beta.41` nog niet bestaat, maakt ze één tag, beide releasepakketten (`local` en `GitHub-HACS`) en één prerelease. De workflow voegt de installatiehandleiding en het testverslag van de actuele manifestversie als release-assets toe. Een tagpush start dus geen tweede automatische Validate-/Release-keten.

**Manual Release** is alleen de noodroute voor een bestaande tag die nog geen GitHub-release heeft.

## Home Assistant

Maak vóór update een back-up. Installeer de nieuwe release en herstart Home Assistant. Een lopende afwascyclus wordt niet onderbroken. Controleer dat Home Assistant werkelijk `1.0.0-beta.41` heeft geladen en vernieuw de browser geforceerd als alleen de kaart nog oud is. Controleer daarna:

- één centrale Voorrang zonder dubbele toestelvelden;
- per toestel de beslisreden, startvoorwaarden en afzonderlijke Startreden/Stopreden;
- behoud van een handmatig OFF gezette klimaatzone bij een gewone AUTO-beslissing;
- directe terugval van een door SolarPilot beheerd extra DHW-doel bij actieve koeling of echte netafname;
- de effectieve Wallbox-sessiebron met zonne-auto-, manueel- en gestoptstatussen, zonder Wallbox-bediening;
- de afzonderlijke globale en per-toestelactivering voordat fysieke regeling wordt toegestaan.

De begrensde beta.40-AEG-recovery blijft cumulatief aanwezig. Geef haar zo nodig maximaal tien minuten om laat geladen template-/AEG-entiteiten te zien. De migratie verstuurt geen START. Voor een nieuwe afwasaanvraag moet APP/remote-start een nieuwe overgang naar exact `Enabled` maken; als APP al aan stond bij startup, eerst uit en opnieuw aan.

Zie `docs/BETA41_INSTELLEN.md`, `docs/TESTRESULTATEN_BETA41.md` en `docs/ACTUELE_WERKING.md`.
