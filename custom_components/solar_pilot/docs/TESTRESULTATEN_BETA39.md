# SolarPilot 1.0.0-beta.39 — testresultaten

Datum: 2026-10-01

## Geautomatiseerde regressiesuite

- `pytest -q`: **1434 passed**.
- Gerichte afwasmachinetests: **133 passed** voor basisadapter, beta.38→beta.39-recovery/migratie en APP/deadline/end-eventlogica.
- Nieuwe regressietest bewijst dat een APP-aanvraag langer dan vijf minuten op zon mag wachten wanneer de statische veilige AEG-statussen onveranderd blijven maar ConnectivityState actueel wordt gehouden.
- Nieuwe recoverytests bewijzen dat alleen een door beta.38 automatisch hersteld profiel wordt gerepareerd, de volledige lopende faselijst terugkomt en een onbewezen automatisch gekozen alarmbron wordt verwijderd.
- Handmatig geconfigureerde afwasmachineprofielen blijven door de beta.39-reparatiemigratie onaangeroerd.

## Releasecontroles

- `tools/check_current_explanation.py`: geslaagd voor 1.0.0-beta.39.
- `tools/check_handoff.py`: geslaagd voor 1.0.0-beta.39.
- `tools/validate_repository.py`: geslaagd.
- `tools/check_public_repository.py`: geslaagd op cachevrije bronboom.
- Python compileall: geslaagd met bytecodecache buiten de bronboom.
- De oude Playwright-browserchecks (`check_card.py`, `check_options_ui.py`, `check_dishwasher_app_ui.py`, `check_dishwasher_priority_ui.py`, `check_priority_ui35.py`) konden vanuit de geregistreerde beta.38 releasebron niet worden gestart omdat hun verwachte ontwikkelfixture `SolarPilot-voorbeeld.html` niet in die releasebron aanwezig is. De scripts stoppen met FileNotFound vóór browser/UI-uitvoering; hiervoor wordt geen vals groen resultaat genoteerd.

## Niet fysiek uitvoerbaar in de bouwomgeving

De echte AEG-cloud en fysieke vaatwasser kunnen vanuit deze bouwomgeving niet daadwerkelijk worden gestart. De commandoroute, voorwaarden, wachttijden, eenmalige START en state-overgangen zijn met Home Assistant-testdubbels gedekt. Na installatie blijft één gecontroleerde echte nieuwe belading de noodzakelijke praktijktest; zie `BETA39_INSTELLEN.md`.
