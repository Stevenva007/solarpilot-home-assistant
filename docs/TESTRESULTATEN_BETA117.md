# SolarPilot beta.117 — softwarevalidatie

## Gedrag dat wordt getoetst

De nieuwe regressies bootsen de gepubliceerde Aquarea v2.0.1-migratie na: dezelfde native unique-id en apparaatbinding verhuizen van `sensor` naar `binary_sensor`, terwijl richting als kleine enumwaarde verschijnt. SolarPilot moet na een werkelijk nieuwe passende poll dezelfde read-only taakcontext kunnen vormen. Een gelijktijdige oude en nieuwe pompstatus mag niet automatisch worden gekozen. De historische sensorvorm blijft ondersteund.

Geen test maakt een cloudverzoek of apparaatopdracht. De Aquarea v2.0.1- en SDK v1.6.0-bronnen zijn exact op hun publieke releasecommits beoordeeld. De SDK-taakparser en LIVE/CACHED-semantiek zijn ongewijzigd; de nieuwe consumptierapportopties en Aquarea lifetime/vandaag-energie krijgen geen nieuwe SolarPilot-bronrol. Zie [UPSTREAM_BETA117.md](UPSTREAM_BETA117.md).

## Uitgevoerde lokale controles

Op 11 november 2026 slaagden **103 gerichte tests** voor Aquarea v2-entiteitsmigratie, oude/nieuwe broncontracten, pollkwaliteit, conflicten, energieperioden en oorspronkelijke tijden. Daarna slaagde de volledige lokale suite met **9561 tests** in 260,49 seconden. Ook actuele uitleg, handoff, publieke-repositorycontrole, SG-opdrachtgrens, offline én online upstreamgate, JavaScript-syntaxis en `git diff --check` slaagden. De exacte CI-commit blijft het publicatiebewijs voor de vijf GitHub-gates.

## Commitgebonden validatie en publicatie

Publicatie vereist op de exacte PR-HEAD vijf groene Validate-gates: repository en volledige testsuite, HACS, Hassfest, echte Chromium-interacties en echte Home Assistant-startup. Na samenvoegen herhaalt main dezelfde gates en maakt daarna pas tag en vier assets. De teruggedownloade HACS-ZIP, lokale ZIP en twee releasedocumenten worden tegen de exacte tag en bron-SHA vergeleken.

De bronreviewgate moet dezelfde Aquarea v2.0.1- en SDK v1.6.0-pins online bevestigen. Een open issue, oude groene commit of lokale gerichte run vervangt geen actuele gate. Geen fysieke warmtepomp-, SG- of providerinstallatieproef uitgevoerd; softwarepublicatie bewijst geen lokale installatie.
