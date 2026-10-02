# SolarPilot beta.43 publiceren — bestaande GitHub/HACS-repository

Dit pakket is de volledige cumulatieve bron van **1.0.0-beta.43**. Gebruik uitsluitend de bestaande repository `Stevenva007/solarpilot-home-assistant`; maak geen nieuwe repository, force-push of verplaatste oude tags. Publiceer beta.43 als nieuwe prerelease; wijzig de reeds geregistreerde beta.42- of eerdere tags niet.

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
git commit -m "SolarPilot 1.0.0-beta.43 - truthful activity and safe Monday deadline"
git push origin main
```

De workflow **Validate** start alleen op `main`, pull requests naar `main` of handmatig. Er is geen dagelijkse schedule meer. Een nieuwere run op dezelfde ref annuleert een oudere lopende run.

Controleer vóór de release dat `docs/TESTRESULTATEN_BETA43.md` uitsluitend werkelijk uitgevoerde resultaten vermeldt en dat alle vereiste software-/releasecontroles definitief groen zijn. Publiceer niet op basis van voorlopige of afgeleide aantallen.

Na groene repositorytests, pytest, HACS-validatie en Hassfest leest dezelfde workflow de manifestversie. Wanneer `v1.0.0-beta.43` nog niet bestaat, maakt ze één tag, beide releasepakketten (`local` en `GitHub-HACS`) en één prerelease. De workflow voegt de installatiehandleiding en het testverslag van de actuele manifestversie als release-assets toe. Een tagpush start dus geen tweede automatische Validate-/Release-keten.

**Manual Release** is alleen de noodroute voor een bestaande tag die nog geen GitHub-release heeft.

## Home Assistant

Maak vóór update een volledige back-up. Plan de update buiten een actieve beschermde cyclus en laat een lopende cyclus veilig afwerken zonder STOPRESET. De bewezen live basis is beta.42 op Home Assistant Core 2026.9.4. Installeer de nieuwe release, herstart Home Assistant en controleer afzonderlijk dat backend én kaart werkelijk `1.0.0-beta.43` tonen. Vernieuw de browser geforceerd als alleen de kaart nog oud is. Controleer daarna:

- **Nu actief** op werkelijke status, met zichtbaar gemeten of geschat vermogen en zonder SolarPilot-/PV-oorzaakclaim;
- read-only Wallbox-wachtuitleg en maximaal dertig waargenomen laadperiodes, waarbij oude, ontbrekende of niet tijdgecorreleerde native status geen bevestigde stopoorzaak wordt;
- veilige browsernavigatie binnen SolarPilot, inclusief bevestiging bij niet-opgeslagen werk en blokkering tijdens opslaan/lopende acties;
- de voorwaartse automatische-voordeelweergave als maximaal negentig dagen opportunity value, los van elektriciteitskost en zonder historische reconstructie;
- de optionele maandagdeadline: leeg betekent gewone 13:00, `10:00` geldt alleen maandag, en alleen expliciet toepassen op huidig verzoek herberekent dezelfde dag zonder START;
- de beschermde avondvoorraad tot maximaal de ingestelde 55 °C-limiet: alleen bevestigde native Full Solar, connected+demand, minstens 50 W en status plus vermogen hoogstens 120 seconden oud mag EV-zonnevermogen meewegen; extra 60 °C en manueel/onbekend/oud laden krijgen geen EV-krediet;
- behoud van bestaande tickets bij update/herstart en geen APP-ticket wanneer APP bij startup al `Enabled` is;
- de afzonderlijke globale en per-toestelactivering voordat fysieke regeling wordt toegestaan.

De begrensde beta.40-AEG-recovery blijft cumulatief aanwezig. Geef haar zo nodig maximaal tien minuten om laat geladen template-/AEG-entiteiten te zien. De migratie verstuurt geen START. Voor een nieuwe afwasaanvraag moet APP/remote-start een nieuwe overgang naar exact `Enabled` maken; als APP al aan stond bij startup, eerst uit en opnieuw aan.

Een echte actieve koelcyclus en een nieuwe fysieke AEG-belading zijn geen vooraf bewezen beta.43-liveacceptatie en mogen niet als uitgevoerd worden vermeld. De Wallbox blijft zonder start-, stop-, laadstroom-, fase- of modusrecht.

Zie `docs/BETA43_INSTELLEN.md`, `docs/TESTRESULTATEN_BETA43.md` en `docs/ACTUELE_WERKING.md`.
