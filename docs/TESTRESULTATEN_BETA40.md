# SolarPilot 1.0.0-beta.40 — testresultaten

Datum: 2026-10-01

> **Status: finaal groen.** Onderstaande aantallen en controles komen uit de werkelijk uitgevoerde beta.40-bronboom.

## Geautomatiseerde regressiesuite

- Volledige `pytest -q -p no:cacheprovider`: **1445 passed**.
- Gerichte afwasmachine-/recovery-/runtime-set: **353 passed**.
- Home Assistant-testdubbels bevestigen:
  - markers en AEG-entiteiten die pas na SolarPilot-setup verschijnen leveren exact één profiel op;
  - de migratie doet geen button-, switch- of scriptservicecall;
  - een late recovery wordt persistent en live toegepast en verschijnt in Toestellen en Voorrang;
  - tijdelijke listeners stoppen na succes, timeout en unload;
  - dubbele events maken geen dubbel profiel;
  - ontbrekende of ambigue verplichte rollen verlenen geen startrecht;
  - een eerder hersteld en later verwijderd profiel wordt niet opnieuw aangemaakt;
  - Auto geldt alleen voor de exacte eenmalige legacy-recovery zonder eerdere gebruikersmodus;
  - handmatige profielen en bestaande gebruikerskeuzes blijven onaangeroerd.

## Releasecontroles

- `tools/check_current_explanation.py`: **geslaagd** voor `1.0.0-beta.40`.
- `tools/check_handoff.py`: **geslaagd** voor `1.0.0-beta.40`.
- `tools/validate_repository.py`: **geslaagd**.
- `tools/check_public_repository.py`: **geslaagd** op de opgeschoonde bronboom.
- Python compileall met bytecodecache buiten de bronboom: **geslaagd**.
- JavaScript-syntaxcontrole voor kaart en veldhulp: **geslaagd**.
- `git diff --check`, cachecontrole en gelijkheid van de vier ingebedde documentkopieën: **geslaagd**.

## Live diagnose vóór installatie

- Home Assistant draaide werkelijk **Core 2026.9.4**, Supervisor **2026.09.3**, OS **18.3** en Frontend **20260826.7**.
- De werkelijk geladen SolarPilot-integratie meldde zowel in Home Assistant als in `sensor.solarpilot_status` versie **1.0.0-beta.39**.
- `dishwasher_setup` stond op `not_applicable` met reden dat geen oudere dashboardkoppeling was gevonden.
- Op hetzelfde live systeem waren daarna beide legacy-markers én alle zes verplichte AEG-rollen op één Home Assistant-apparaat aanwezig. Dit bevestigt de opstartvolgordefout; de START-bron was de unieke actuele native START en niet PAUSE, RESUME, STOPRESET of starttijd.

## Niet fysiek uitgevoerd in de bouwomgeving

De echte AEG-cloud en fysieke afwasmachine worden tijdens de migratie- en softwaretests niet gestart. Na installatie blijft één gecontroleerde nieuwe belading nodig om live te bevestigen:

- werkelijk geladen SolarPilot-versie `1.0.0-beta.40`;
- herstel binnen het begrensde post-startvenster;
- zichtbaarheid onder Toestellen en Voorrang;
- nieuwe APP-overgang naar exact `Enabled`;
- maximaal één native START;
- beschermd verloop tot End Of Cycle.

Zie `BETA40_INSTELLEN.md` voor de gecontroleerde live-installatie en rollback.
