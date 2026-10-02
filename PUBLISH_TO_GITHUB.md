# SolarPilot beta.42 publiceren — bestaande GitHub/HACS-repository

Dit pakket is de volledige cumulatieve bron van **1.0.0-beta.42**. Gebruik uitsluitend de bestaande repository `Stevenva007/solarpilot-home-assistant`; maak geen nieuwe repository, force-push of verplaatste oude tags. Publiceer beta.42 als nieuwe prerelease; wijzig de reeds geregistreerde beta.41- of eerdere tags niet.

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
git commit -m "SolarPilot 1.0.0-beta.42 - safe resume and bounded learning reset"
git push origin main
```

De workflow **Validate** start alleen op `main`, pull requests naar `main` of handmatig. Er is geen dagelijkse schedule meer. Een nieuwere run op dezelfde ref annuleert een oudere lopende run.

Controleer vóór de release dat `docs/TESTRESULTATEN_BETA42.md` uitsluitend werkelijk uitgevoerde resultaten vermeldt en dat alle vereiste software-/releasecontroles definitief groen zijn. Publiceer niet op basis van voorlopige of afgeleide aantallen.

Na groene repositorytests, pytest, HACS-validatie en Hassfest leest dezelfde workflow de manifestversie. Wanneer `v1.0.0-beta.42` nog niet bestaat, maakt ze één tag, beide releasepakketten (`local` en `GitHub-HACS`) en één prerelease. De workflow voegt de installatiehandleiding en het testverslag van de actuele manifestversie als release-assets toe. Een tagpush start dus geen tweede automatische Validate-/Release-keten.

**Manual Release** is alleen de noodroute voor een bestaande tag die nog geen GitHub-release heeft.

## Home Assistant

Maak vóór update een back-up. Installeer de nieuwe release en herstart Home Assistant. Een lopende afwascyclus wordt niet onderbroken. De bewezen live basis is beta.41 op Home Assistant Core 2026.9.4; controleer na update afzonderlijk dat Home Assistant werkelijk `1.0.0-beta.42` heeft geladen en vernieuw de browser geforceerd als alleen de kaart nog oud is. Controleer daarna:

- DHW-Hervat buiten Automatisch regelen, zonder directe temperatuurwrite en geblokkeerd bij een wachtende opdracht;
- bewaarde én effectieve Voorrang, waarbij een opgeslagen Ja onder Auto laden zichtbaar effectief Nee blijft;
- de begrensde leerreset zonder wijziging van instellingen, operationele klimaatveiligheid of fysieke bediening;
- de actuele Wallbox-sessiebron met bronversheid/heartbeat; gestopt zonder EV-krediet is live bewezen, zonne-auto en manueel worden nog doorlopen en de Wallbox blijft read-only;
- behoud van een handmatig OFF gezette klimaatzone en DHW-eigendom uit beta.41;
- de afzonderlijke globale en per-toestelactivering voordat fysieke regeling wordt toegestaan.

De begrensde beta.40-AEG-recovery blijft cumulatief aanwezig. Geef haar zo nodig maximaal tien minuten om laat geladen template-/AEG-entiteiten te zien. De migratie verstuurt geen START. Voor een nieuwe afwasaanvraag moet APP/remote-start een nieuwe overgang naar exact `Enabled` maken; als APP al aan stond bij startup, eerst uit en opnieuw aan.

Een echte actieve koelcyclus en een echte AEG-belading zijn nog geen bewezen beta.42-liveacceptatie en mogen niet als uitgevoerd worden vermeld.

Zie `docs/BETA42_INSTELLEN.md`, `docs/TESTRESULTATEN_BETA42.md` en `docs/ACTUELE_WERKING.md`.
