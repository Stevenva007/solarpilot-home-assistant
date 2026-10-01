# SolarPilot beta.37 publiceren — bestaande GitHub/HACS-repository

Dit is de volledige cumulatieve bron van **1.0.0-beta.37**. Het pakket publiceert
niets zelf. Gebruik de bestaande repository en de bestaande licentie. Maak geen
nieuwe repository, verplaats geen oude release-tags en voer geen force-push uit.

## Bestanden overzetten

Pak de ZIP uit. Kopieer de **inhoud** van de map waarin `custom_components/`,
`docs/`, `tools/`, `.github/` en `README.md` staan over je bestaande lokale
Git-repository. Kopieer geen extra versiemap binnen de repository. Bewaar `.git`.
Publiceer geen privébundel, Home Assistant-back-up, `.storage` of analyse-export.

Open PowerShell in die bestaande Git-repository. Voer de controles afzonderlijk
uit en stop bij een fout:

```powershell
$env:PYTHONUTF8="1"
$env:PYTHONDONTWRITEBYTECODE="1"
py -m pytest -q -p no:cacheprovider
py tools\check_current_explanation.py
py tools\validate_repository.py
py tools\check_public_repository.py
git -c core.autocrlf=false diff --check
git status --short
```

Beoordeel de te publiceren bestanden, voeg ze toe en maak één commit. De volgende
regels zijn afzonderlijke opdrachten; niet aan elkaar plakken.

```powershell
git add -A
git diff --cached --stat
git commit -m "SolarPilot 1.0.0-beta.37 - usability, central priorities and safe defaults"
git push origin main
```

Werkbranches starten in beta.37 niet langer automatisch een Validate-run. Dat voorkomt een
stroom GitHub Actions-meldingen tijdens tussenstappen. De automatische Validate-workflow draait
alleen bij een push naar `main` of bij een pull request naar `main`; handmatig starten blijft
mogelijk vanuit GitHub Actions.

Controleer na de ene definitieve push naar `main` de nieuwe **Validate**-run voor precies die
commit. Ga niet verder met een oude groene run of een run van een andere commit.
`gh run list --workflow Validate --limit 5` toont de runs; `gh run watch` laat je de juiste
lopende run kiezen.

## Alleen na groene validatie van die commit

```powershell
git tag -a v1.0.0-beta.37 -m "SolarPilot 1.0.0-beta.37"
git push origin v1.0.0-beta.37
gh run list --limit 5
```

Wacht op de **Release**-run voor `v1.0.0-beta.37`. De Validate-workflow draait bewust niet
nogmaals voor de tag; de commit op `main` is dan al volledig gevalideerd. Een bestaande tag is
geen reden om hem te verwijderen of te verplaatsen: controleer eerst wat al gepubliceerd is.
De bestaande Release-workflow maakt de prerelease.

## Home Assistant

Maak een back-up, zet SolarPilot op Pauze en laat eigen lasten veilig vrijgeven.
Een afwasprogramma wordt niet onderbroken. Werk bij voorkeur bij wanneer de beurt
klaar is. Installeer de nieuwe release via HACS, herstart Home Assistant en volg
[de actuele uitleg](docs/ACTUELE_WERKING.md). Tussenliggende releases
hoeven niet afzonderlijk geïnstalleerd te worden. Er is geen losse frontend-resource.
