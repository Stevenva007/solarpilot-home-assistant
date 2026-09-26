# SolarPilot eenmalig publiceren op GitHub voor HACS

Deze map is de publieke **SolarPilot 1.0.0-beta.21** repositorybron en kan zowel voor een eerste publicatie als voor een update van `StevenVa007/solarpilot-home-assistant` worden gebruikt. Persoonlijke historische data, woning-specifieke entity-ID-defaults, Python-cachebestanden en Home Assistant-opslag horen er niet in.

## Aanbevolen repository

Gebruik bij voorkeur:

```text
solarpilot-home-assistant
```

Dat maakt duidelijk dat dit de Home Assistant-integratie is. De repository moet **Public** zijn voor HACS Custom Repositories.

## 1. GitHub-eigenaar invullen

Voer in deze uitgepakte map uit:

```powershell
py tools\configure_repository.py JOUW_GITHUB_GEBRUIKERSNAAM solarpilot-home-assistant
```

Dit vult `documentation`, `issue_tracker` en `codeowners` in `manifest.json` in en voegt de directe HACS-link toe aan de README.

## 2. Licentie kiezen

Lees `LICENSE_OPTIONS.md` en voeg vóór de publieke release een GitHub-herkenbare softwarelicentie toe als `LICENSE`, `LICENSE.txt` of `LICENSE.md`. SolarPilot kiest deze juridische toestemming bewust niet automatisch voor jou.

## 3A. Automatisch uploaden op Windows

Als **Git**, **GitHub CLI (`gh`)** en Python aanwezig zijn en `gh auth status` werkt:

```powershell
powershell -ExecutionPolicy Bypass -File tools\publish_github_windows.ps1 -GitHubOwner JOUW_GITHUB_GEBRUIKERSNAAM -License mit
```

Vervang `mit` desgewenst door `apache-2.0` of `gpl-3.0`. Met die parameter maak jij expliciet de licentiekeuze; het script haalt daarna de officiële licentietekst via GitHub op. Vervolgens finaliseert het de repository, voert het de lokale preflight uit, maakt indien nodig de publieke GitHub-repository aan, pusht `main`, zet de description, schakelt Issues in en voegt de HACS-topics toe. Het maakt bewust **nog geen release-tag**.

## 3B. Handmatig via github.com

Maak een publieke repository en upload de **inhoud van deze map** naar de root. De root moet onder andere `.github/`, `custom_components/`, `docs/`, `tools/`, `README.md` en `hacs.json` bevatten; upload dus niet alleen de ZIP en maak geen extra mapniveau.

Repository description:

```text
SolarPilot - local Home Assistant EMS for PV surplus, flexible loads, heat pumps, EV charging coexistence and batteries.
```

Zet **Issues** aan en voeg deze topics toe:

```text
home-assistant, hacs, energy-management, ems, solar, photovoltaics, heat-pump, battery
```

## 4. GitHub Actions eerst groen

Onder **Actions** moeten minstens deze controles slagen:

- `repository-checks` — publicatie/privacy, versie/documentatie en Python-syntax;
- `validate-hacs` — officiële HACS Action;
- `hassfest` — officiële Home Assistant hassfest-validatie.

De HACS-validator kan daarnaast GitHub-metadata controleren die pas na publicatie bestaat. Corrigeer zulke meldingen vóór je de eerste release maakt.

## 5. Eerste prerelease maken

Maak pas na groene Actions de tag en push hem:

```powershell
git tag -a v1.0.0-beta.21 -m "SolarPilot 1.0.0-beta.21"
git push origin v1.0.0-beta.21
```

De meegeleverde `.github/workflows/release.yml` maakt van de gepushte tag automatisch een GitHub Release en markeert beta/alpha/rc-tags automatisch als **prerelease**.

## 6. Testen via HACS

Voeg de publieke repository in Home Assistant toe via **HACS → ⋮ → Custom repositories**, kies type **Integration**, download SolarPilot en herstart Home Assistant. Voeg daarna SolarPilot toe via **Instellingen → Apparaten & diensten**.

De frontend zit in de integratie zelf; er is geen losse `/config/www`-kaart of Lovelace-resource nodig.
