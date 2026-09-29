# SolarPilot 1.0.0-beta.33 — lokale publicatiecontrole

Datum: 29 september 2026. Bron: het aangeleverde volledige beta.33-pakket.

## Resultaten

- Windows, Python 3.12.14, pytest 9.1.1 en pytest-asyncio 1.4.0.
- Volledige suite: **1240 tests geslaagd** (`pytest -q -p no:cacheprovider`).
- Actuele uitleg: **1.0.0-beta.33**, hashprefix **d9d84237b3bf6e5c**.
- Repositorystructuur en public repository preflight: OK.
- Alle 56 Pythonbestanden van de integratie geparseerd: OK.
- JavaScript-syntaxis van `solar-pilot-card.js` en `option-help.js`: OK.

De Windows-proef toonde een precisieverschil tussen `datetime` en `time.time()`
in de gesimuleerde boilerterugmelding. De testservice wacht nu 1 milliseconde,
zodat de terugmelding na de opdracht valt, zoals bij een asynchroon apparaat.
De testverwachtingen en de boilerbesturing zijn hiervoor niet gewijzigd.
Verouderde versieverwijzingen in de publicatie- en installatie-instructies zijn
bijgewerkt; het Windows-publicatiescript leest de versie voortaan uit het manifest.

## Grenzen

De tests gebruiken Home Assistant-testdubbels. Er is tijdens deze publicatiecontrole
geen echte Home Assistant-installatie of fysiek apparaat bediend en geen volledige
browserregressiesuite uitgevoerd. GitHub Actions voert na het pushen afzonderlijk
de Python 3.13-testset, HACS-validatie en hassfest uit. De releasetag wordt pas
aangemaakt als die controles voor de te publiceren commit geslaagd zijn.
