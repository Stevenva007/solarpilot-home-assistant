# SolarPilot beta.44 publiceren — bestaande GitHub/HACS-repository

Dit pakket is de volledige cumulatieve bronkandidaat van **1.0.0-beta.44**. Gebruik uitsluitend de bestaande repository `Stevenva007/solarpilot-home-assistant`; maak geen nieuwe repository, force-push of verplaatste oude tags. Publiceer beta.44 als nieuwe prerelease; wijzig de gepubliceerde beta.43- of eerdere tags en assets niet.

De definitieve lokale softwarecontrole op 2 oktober 2026 is groen: **1760 Python-tests in 11.68 s**, **veertien browsercontroles** met nul actuatoroproepen en alle lokale releasechecks. De actuele-uitlegcontrole heeft hash `65b54c9797e55bb4`. Dit is geen claim dat beta.44 al gepubliceerd, geïnstalleerd of werkelijk geladen is; de bewezen live basis blijft beta.43 op Home Assistant Core 2026.9.4. GitHub-CI, nieuwe tag/assets, pakketcontrole, HACS-installatie en geladen backend/kaart moeten afzonderlijk worden bevestigd.

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

Beoordeel de diff en neem uitsluitend beoordeelde SolarPilot-releasewijzigingen op. Behoud eventuele niet-gerelateerde gebruikerswijzigingen. Maak bij voorkeur **één** releasecommit; dit beperkt GitHub Actions- en e-mailruis.

```powershell
git add -A
git diff --cached --stat
git commit -m "SolarPilot 1.0.0-beta.44 - safe allocation and truthful boiler feedback"
git push origin main
```

De workflow **Validate** start alleen op `main`, pull requests naar `main` of handmatig. Er is geen dagelijkse schedule meer. Een nieuwere run op dezelfde ref annuleert een oudere lopende run.

Controleer vóór de release dat `docs/TESTRESULTATEN_BETA44.md` uitsluitend werkelijk uitgevoerde resultaten vermeldt en dat alle vereiste software-/releasecontroles definitief groen zijn. Een nieuwe bronwijziging vereist passende hercontrole; leid geen nieuw totaal af door losse testtellingen op te tellen. Laat de historische beta.43-documenten intact.

Na groene repositorytests, pytest, HACS-validatie en Hassfest leest dezelfde workflow de manifestversie. Wanneer `v1.0.0-beta.44` nog niet bestaat, maakt ze één tag, beide releasepakketten (`local` en `GitHub-HACS`) en één prerelease. De workflow voegt de installatiehandleiding en het testverslag van de actuele manifestversie als release-assets toe. Een tagpush start dus geen tweede automatische Validate-/Release-keten.

**Manual Release** is alleen de noodroute voor een bestaande tag die nog geen GitHub-release heeft.

Download na publicatie beide beta.44-ZIP's en controleer hun werkelijke SHA-256, padveiligheid, manifestversie, afwezigheid van private/cachebestanden en inhoud tegenover de nieuwe tag. Een groene workflow bewijst op zichzelf niet dat Home Assistant die bron heeft geïnstalleerd of geladen.

## Home Assistant

Maak vóór update een volledige back-up. De bestaande versleutelde NAS-back-up is om 16:19 gereed gemeld; dit is geen uitgevoerde herstelproef. Plan de update buiten een actieve beschermde cyclus en laat een lopende cyclus veilig afwerken zonder STOPRESET. De bewezen live basis is beta.43 op Home Assistant Core 2026.9.4. Installeer exact de nieuwe beta.44-release via HACS, herstart Home Assistant en controleer afzonderlijk dat backend én kaart werkelijk `1.0.0-beta.44` tonen. Vernieuw de browser geforceerd als alleen de kaart nog oud is. Begin de controles in **Alleen bekijken** of **Pauze**. Controleer daarna:

- **Nu actief** op werkelijke status, met zichtbaar gemeten of geschat vermogen en zonder SolarPilot-/PV-oorzaakclaim;
- read-only Wallbox-wachtuitleg en maximaal dertig waargenomen laadperiodes, waarbij oude, ontbrekende of niet tijdgecorreleerde native status geen bevestigde stopoorzaak wordt;
- veilige browsernavigatie binnen SolarPilot, inclusief bevestiging bij niet-opgeslagen werk en blokkering tijdens opslaan/lopende acties;
- de voorwaartse automatische-voordeelweergave als maximaal negentig dagen opportunity value, los van elektriciteitskost en zonder historische reconstructie;
- de optionele maandagdeadline: leeg betekent gewone 13:00, `10:00` geldt alleen maandag, en alleen expliciet toepassen op huidig verzoek herberekent dezelfde dag zonder START;
- de beschermde avondvoorraad tot maximaal de ingestelde 55 °C-limiet: alleen bevestigde native Full Solar, connected+demand, minstens 50 W en status plus vermogen hoogstens 120 seconden oud mag EV-zonnevermogen meewegen; extra 60 °C en manueel/onbekend/oud laden krijgen geen EV-krediet;
- behoud van bestaande tickets bij update/herstart en geen APP-ticket wanneer APP bij startup al `Enabled` is;
- de afzonderlijke globale en per-toestelactivering voordat fysieke regeling wordt toegestaan.
- geen EV-reservering bij verse geldige lage laadkracht én expliciet geen laadvraag, geen verbonden auto of een bekende inactieve status; laag vermogen alleen is onvoldoende;
- dezelfde effectieve toesteltoewijzing in de startuitleg als in het enginebesluit, afzonderlijk van ruwe vrije injectie;
- proportionele AEG-/60 °C-reservering in plaats van een algemeen veto, uitsluitend met echte resterende net-/PV-ruimte en zonder Wallboxkrediet voor extra 60 °C;
- gerapporteerd boilerdoel, voorgesteld doel en beschermende pauze afzonderlijk zichtbaar; de onmiddellijke optimistische Panasonic-terugmelding geldt niet als opdrachtbevestiging;
- de expliciet gekoppelde, verse native warmtepomptaak als read-only bron: `PUMP` houdt de extra zonnebuffer tegen, terwijl `WATER` een gerapporteerde tapwatertaak is en geen compressor-/elektrisch bewijs. Zonder betrouwbare taakbron is Panasonic AUTO met `hvac_action=off/idle` geen bewijs van afwezig ruimtebedrijf. Onbekende of tegenstrijdige gegevens blijven beschermd;
- de geïntegreerde optieswizard kan benoemde velden opslaan zonder afhankelijkheid van `form.elements`; opslaan verleent geen nieuw fysiek recht.

De boilerregeling stond na de afwijkende terugmelding rond 15:45 opnieuw in beschermende pauze. Een bewuste handmatige wijziging is niet bevestigd. Na installatie en controle is een gerichte review toegestaan, maar nog niet uitgevoerd. Controleer tankmeting, gerapporteerd doel, hygiëne-/krachtige-/handmatige functies en wachtende opdrachten; gebruik pas daarna buiten **Automatisch regelen** de bestaande hervatknop. Deze schrijft zelf geen temperatuur en start geen regelcyclus. Herstel **Automatisch regelen** pas nadat alle actuele koppelingen en beveiligingen kloppen; de update mag geen bestaande overname stil wissen.

Powerful wordt niet automatisch als boilerboost gebruikt: de gecontroleerde Panasonic K T-CAP-servicehandleiding beschrijft ruimteverwarming, niet een bewezen tapwaterboost. Ook de afzonderlijke installateursinstelling DHW capacity blijft ongewijzigd. Het logo in het Home Assistant/HACS-updatevenster is reeds bij beta.43 bevestigd via ondersteunde lokale brandsproxy-customisatie; dat vereist geen warmtepompcommando of HACS-codepatch. De maandagdeadline 10:00 blijft een nog afzonderlijk toe te passen en te bevestigen keuze.

De begrensde beta.40-AEG-recovery blijft cumulatief aanwezig. Geef haar zo nodig maximaal tien minuten om laat geladen template-/AEG-entiteiten te zien. De migratie verstuurt geen START. Voor een nieuwe afwasaanvraag moet APP/remote-start een nieuwe overgang naar exact `Enabled` maken; als APP al aan stond bij startup, eerst uit en opnieuw aan.

Een echte actieve koelcyclus en een nieuwe fysieke AEG-belading zijn geen vooraf bewezen beta.44-liveacceptatie en mogen niet als uitgevoerd worden vermeld. Gebruik geen fysieke proefstart, APP-herarming, leerreset, Powerful of Wallbox-opdracht om acceptatie af te dwingen. De Wallbox blijft zonder start-, stop-, laadstroom-, fase- of modusrecht.

## Rollback

Zet SolarPilot op **Pauze**, laat een lopende beschermde cyclus veilig afwerken en herstel de onveranderlijke beta.43-release of de volledige back-up. Herstart Home Assistant en bevestig backend en kaart beta.43. Controleer APP-ticket, Voorrang, maandagdeadline, klimaat-/DHW-eigendom en Wallbox fail-closed gedrag vóór opnieuw **Automatisch regelen**. Een lopende afwasbeurt wordt niet met STOPRESET beëindigd.

Zie `docs/BETA44_INSTELLEN.md`, `docs/TESTRESULTATEN_BETA44.md` en `docs/ACTUELE_WERKING.md`. De beta.43-handleidingen en testresultaten blijven onveranderde releasehistorie.
