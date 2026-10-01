# SolarPilot 1.0.0-beta.38 — testresultaten

Datum: 2026-10-01

## Geautomatiseerde regressiesuite

- `pytest -q`: **1429 passed**.
- Nieuwe afwasmachinehersteltests: ontbrekend legacy-profiel wordt veilig hersteld; geen herstel zonder installatiemarkering; bestaand profiel wordt nooit overschreven; incomplete mapping verleent geen rechten.
- Beta.37-activeringsprofiel opnieuw expliciet getest: reeds gekoppelde veilige modules mogen éénmalig activeren; ontbrekende bronnen/veiligheidsbevestigingen worden niet verzonnen; latere gebruikerskeuzes blijven behouden.
- Centrale voorrangstests aangepast aan de zichtbare leidende volgorde: Wallbox-vermogen vereist zowel positie boven de Wallbox als expliciete toestemming.

## Release- en repositorycontroles

- `tools/check_handoff.py`: geslaagd voor het versiegebonden overdrachtsdossier.
- `tools/check_current_explanation.py`: geslaagd voor 1.0.0-beta.38.
- `tools/check_public_repository.py`: geslaagd na verwijderen van testcaches.
- Python compileall: geslaagd met cache buiten de bronboom.
- `git diff --check`: geslaagd.
- Browsercheck van het echte Control Center: geslaagd op 320/390/768/1280 en met veilige actierouting/escaping.
- Beta.37 release-infrastructuur behouden: geen dagelijkse Validate-schedule, concurrency-annulering van oudere runs, één main-validatieketen en automatische publicatie van local + GitHub/HACS-pakket na groen HACS/Hassfest.
- Verouderde browserverwachting voor een verwijderde losse planner-totaalscore gecorrigeerd; de echte uitvoeringsmeting blijft getest.

## Niet fysiek getest in deze releasebouw

De automatische AEG-start is niet tegen de echte vaatwasser uitgevoerd vanuit de bouwomgeving. De code test de voorwaarden en commandoroute met Home Assistant-testdubbels. Na installatie moet daarom één gecontroleerde nieuwe belading worden getest zoals beschreven in `BETA38_INSTELLEN.md`.
