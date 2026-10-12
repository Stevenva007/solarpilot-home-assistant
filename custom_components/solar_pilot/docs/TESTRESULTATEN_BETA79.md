# SolarPilot beta.79 — brongebonden test- en releaseverslag

Versie: **1.0.0-beta.79** · 12 oktober 2026

Alle **79 productie-Pythonmodules** en beide frontendmodules zijn nagekeken. De definitieve lokale volledige suite is geslaagd: **5125 tests in 102.98 seconden**, waaronder **329 nieuwe auditregressies**. Concrete bevindingen en de volledige moduledekking staan in [AUDIT_BETA79.md](AUDIT_BETA79.md).

## Definitieve lokale controles

| Controle | Resultaat |
|---|---|
| Volledige pytest-suite | 5125 geslaagd; 0 mislukt; Python 3.12.14 |
| Uitvoerbare frontendproeven | Node v24.19.0; meegenomen in de volledige suite, inclusief oude popupaliassen, verouderde waarnemingen, async races, native detach/heropenen van beide popupconstructors en werkelijk toegewezen startbudget |
| Python-/JSON-syntax | Alle productie-Pythonmodules, Python-tools en component-JSON parsebaar |
| Beide frontend-JavaScriptmodules | `node --check` geslaagd |
| Repositorystructuur en publieke privacy-preflight | Geslaagd; geen eigen exports, runtimegegevens, huislabels of caches opgenomen |
| SG-/native opdrachtgrens | Geslaagd; oude Panasonic-writers afwezig, centrale controle op gewone/batterijopdrachten en afzonderlijke SG-RPC-route |
| Actuele uitleg en overdrachtsdossier | Geslaagd; versie 1.0.0-beta.79 en gegenereerde spiegels gelijk |
| Optiehulp | 345 velden; dezelfde release en canonical guide |
| Canonical guide-hash | `346b1b82e61cc0e3b84af1ca52ffe6eaa78b29d7c760c5869c0c3cb4926adc5d` |
| Diffcontrole | `git diff --check` geslaagd |

Uitgevoerd met `python -B -m pytest -q -p no:cacheprovider`. Testgegevens zijn fictief. Werkelijke screenshots en woningexports zijn niet naar tests of openbare releasebestanden gekopieerd.

## Nieuwe regressies per bestand

| Bestand | Cases |
|---|---:|
| `tests/test_audit_api_config79.py` | 34 |
| `tests/test_audit_battery_physical79.py` | 27 |
| `tests/test_audit_dispatch79.py` | 67 |
| `tests/test_audit_native79.py` | 89 |
| `tests/test_audit_planner79.py` | 34 |
| `tests/test_audit_storage79.py` | 48 |
| `tests/test_audit_tooling79.py` | 2 |
| `tests/test_audit_ui79.py` | 28 |

De tests toetsen onder meer één toekomstreserve voor een lopende onbemeten AEG-cyclus, nieuwe net-/fase-/Wallbox-/zongrenzen tijdens intent-opslag, beschikbare startruimte na voorrang, native START-eigendom, SG-annulering/lease-eigendom, batterij-importgrenzen, plannerslots, modelherkomst, meetdekking, onbekende opslag, historische leesrechten en late browser-/API-antwoorden. Finiete maar niet als UTC-epoch bruikbare APP-tijden blijven afzonderlijk privé bewaard en laten geldige buurrecords intact.

## CI op exact dezelfde bron

Lokale unitproeven gebruiken HA-doubles. De onderstaande echte browser-/Core-/PowerShellcontroles worden na vastleggen van deze bron in GitHub Actions uitgevoerd; hun actuele brongebonden resultaat is de afzonderlijke run van de releasecommit, niet een oudere geslaagde versie:

- Repositorychecks: privacy, handoff, uitleg, opdrachtgrens, volledige suite en Python-syntax. Bovendien 29 geïsoleerde publisher-scenario’s met daadwerkelijke native mockprocessen in PowerShell. Lokaal ontbreekt PowerShell; die 29 zijn hier dus niet als lokaal uitgevoerd geteld.
- HACS-validatie en Hassfest.
- Echte Chromium-browser met fictieve gegevens: warmtepompoverzicht/-historie, gewone historie, PV-diagnose, afwasdeadline, verloop van metingen, popup-lifecycle, actuele releaseconstructors en gereserveerd versus toegewezen startvermogen op mobiel.
- Echte Home Assistant Core 2026.10.0 / Python 3.14.2: setup, platforms, reload, unload, bestaande SG-bronconfiguratie en twee daadwerkelijke HA-selectors/schema’s voor het wissen van meervoudige optionele bronvelden.

Workflow: [Validate](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml). De exacte bron is de commit waar dit verslag deel van uitmaakt, later benoemd door de immutable annotated tag `v1.0.0-beta.79`. Bekijk de SHA van die tag en de bijhorende push-run; resultaten van andere commits vormen geen bewijs voor deze release.

## Publicatie- en pakketbewijs

Publicatie wacht op alle vijf CI-gates. De workflow vergelijkt vóór upload de volledige bronbytes en documenten met dezelfde Git-commit. Na publicatie downloadt hij de onderstaande vier assets opnieuw en vergelijkt ieder bestand, de bron-SHA, bestandsset en SHA-256. Succes vereist de stap **Download and verify published four assets against the exact tag** met `download_verified: true`.

1. `SolarPilot-v1.0.0-beta.79-GitHub-HACS.zip`
2. `SolarPilot-v1.0.0-beta.79-local.zip`
3. `BETA79_INSTELLEN.md`
4. `TESTRESULTATEN_BETA79.md`

[Release beta.79](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.79) bevat pas publicatiebewijs wanneer die exacte tag, brongebonden run en gedownloade assets gecontroleerd zijn. Dit bronverslag declareert vooraf geen toekomstige run-ID of succesvolle hardwaretest.

## Behouden werking en bewijsgrenzen

Bestaande geldige instellingen, prioriteiten, koppelingen, modellen, tickets en historie blijven behouden. De APP-deadline staat zo nodig netstroom toe zonder zonnevoorwaarde, binnen actuele elektrische grenzen en native toestelvoorwaarden. Een ontbrekende meter maakt een latere afwaspiek niet tot gemeten verbruik; één conservatieve toekomstige cyclusreserve blijft nodig. Het dashboard noemt dat gereserveerde vermogen expliciet en verwart een fase-/reservebeperking niet met ontbrekende zonneproductie.

Panasonic blijft SG-only, Wallbox read-only en AEG één native START per geldige belading. Geen extra solver/add-on/controller of dependency voor de gebruiker. Nieuwe fysieke woningopdrachten, bedrading, native cloudcommunicatie en werkelijke SG-energieopname zijn niet met deze fictieve tests geverifieerd. De audit garandeert niet dat iedere mogelijke fout of externe oorzaak uitgesloten is.

Bouwbasis is afzonderlijk de gepubliceerde beta.78, commit `8fadcad54d2b7f9d792f2d09d0e107c44c8ffae5`, tree `e72d89f67aa10087eda9b8aaf8b3fb85feb81eec`, main-run `38231547557`. Dit is alleen herkomstbewijs; de beta.79-controles horen bij de nieuwe bron.
