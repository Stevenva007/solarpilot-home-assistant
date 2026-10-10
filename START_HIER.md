# SolarPilot beta.63 — installatie en upgrade

Panasonic regelt zelfstandig de warmtepomp. SolarPilot kan alleen een gecontroleerde extra zonneboost via één SG-contact aanvragen. De oude tank-/klimaatbediening is verwijderd. Andere bestaande apparaatfuncties en privédata blijven behouden.

**Begin met [BETA63_INSTELLEN.md](docs/BETA63_INSTELLEN.md).** Daar staan back-up, migratie, lokale ingebruikname en rollback. De volledige actuele werking staat in [ACTUELE_WERKING.md](docs/ACTUELE_WERKING.md) en identiek binnen Home Assistant onder **SolarPilot → Uitleg**. Test-/publicatiestatus: [TESTRESULTATEN_BETA63.md](docs/TESTRESULTATEN_BETA63.md).

## Herstellen na een mislukte beta.62-start

Installeer beta.63 en herstart Home Assistant volledig. Wis geen gegevens en verwijder de bestaande SolarPilot-integratie niet. De fout bij het lezen van onveranderbare HA-opties is hersteld; geldige opgeslagen instellingen worden meegenomen. SG krijgt hierdoor geen extra toestemming.

## Voor de upgrade

1. Maak een volledige privé Home Assistant-back-up, inclusief SolarPilot-configuratie, opslag en userfiles.
2. Bewaar de gecontroleerde beta.61-release als codebasis voor rollback, samen met die passende back-up.
3. Controleer de gewenste native Panasonic-tank-/zone-/programma-instellingen; de nieuwe runtime schrijft niets terug.
4. Laat automatische SG uit tot de juiste bestaande uitgang, contactmapping, native reactie, één eigenaar en lokale aflooptimer werkelijk zijn bevestigd.

Een lopende beschermde afwascyclus wordt niet onderbroken en de update maakt geen nieuwe APP-aanvraag. De globale keuze **Na herstart automatisch hervatten** blijft behouden; zij bevestigt geen SG-ingebruikname.

## Installeren

Voeg bij eerste gebruik de GitHub-repository aan HACS toe als **Integration**, installeer exact `1.0.0-beta.63` zodra gepubliceerd en herstart Home Assistant. Heropen browser/app en controleer backend- en kaartversie afzonderlijk. Voeg bij een nieuwe installatie SolarPilot toe via **Instellingen → Apparaten & diensten** en controleer P1/PV eerst met **Alleen bekijken**.

De frontend verschijnt automatisch. Er is geen aparte Lovelace-resource, dashboard-YAML of www-kopie nodig. Lokale installatie vervangt alleen `custom_components/solar_pilot`; bewaar userfiles en eigen HA-opslag.

## Na laden

De versiegebonden migratie archiveert oude uitvoerings-/modelinformatie zonder fysieke opdrachten. SG start standaard niet. **Warmtepomp — Panasonic-regeling** toont één reden, tanktemperatuur en bekende watts/dekking. Uitklapbare Details onderscheidt aanvraag, SG-contact en Panasonic-reactie; onbekend blijft onbekend.

Configureer de bestaande uitgang en metingen onder de warmtepompinstellingen. Zonder echte lokale timerproef blijft automatisch SG geblokkeerd; de rest van SolarPilot kan onder haar eigen voorwaarden werken. Proefdraaien in de woning gebeurt uitsluitend na expliciete toestemming. De korte ingebruiknamecontrole vereist geen meting in geopende elektrische apparatuur.

Een SG-sessie duurt standaard maximaal één uur. Na rust kan betrouwbare tankafkoeling ten opzichte van de verse eindmeting een nieuwe zonbeoordeling toestaan. Zonder bruikbaar bewijs blijft zij wachten; bewust **Automatisering hervatten** is mogelijk na controle. Rusttijd of een herstart alleen heft de sessiegrens niet op.

Gerichte resterende controlefouten verschijnen ook onder **Home Assistant → Meldingen → SolarPilot: controle nodig**. Een gewone wachttijd/rusttijd is geen fout. Oude boilercontrole-/AUTO-knoppen horen bij eerdere versies en bestaan hier niet meer.

## Rollback

Geef eerst de eigen SG-aanvraag vrij en bevestig het geopende contact/lokale terugval. Stop de nieuwe SG-runtime voordat beta.61-writers terugkomen. Herstel beta.61-code én de volledige passende privéback-up van vóór migratie. Een oudere ZIP alleen herstelt de opslag niet. Laat nooit de oude Panasonic-regelaar en nieuwe SG-regelaar tegelijk werken.
