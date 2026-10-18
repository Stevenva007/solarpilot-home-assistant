# SolarPilot beta.97 — minder onnodige SG-herhaalwacht

Versie: **1.0.0-beta.97** · 18 oktober 2026

Een aantoonbaar eigen beëindigde algemene SG-aanvraag met onbekend effect hoeft niet meer altijd eerst vijftien minuten te wachten. Vijf minuten nieuw voldoende werkelijk restoverschot kunnen de resterende SG-herhaalwacht vervangen, mits het contact opnieuw bevestigd UIT is en alle huidige voorwaarden passen. Daarna volgt de gewone startvertraging, standaard twee minuten. Andere voltooiingsredenen en onzekere situaties houden hun afzonderlijke bescherming.

## Bijwerken

1. Bewaar een actuele volledige privéback-up van Home Assistant.
2. Installeer beta.97 via HACS na geslaagde controles en publicatie. Behoud de integratie-entry, instellingen, userfiles, opslag, modellen en historie.
3. Herstart Home Assistant volledig en herlaad browser/app volledig. Controleer de backend- en geladen kaartversie afzonderlijk.
4. Bekijk bij de volgende beëindigde aanvraag de oorspronkelijke stopreden, SG-herhaalwacht en overschotbevestiging. Een update of herstart geeft zelf geen startrecht.

Aquarea 1.7.0 is gecontroleerd. Het nieuwe `auto_mode`-attribuut geeft een gekozen AUTO-richting aan, ook tijdens stilstand; het is geen bewijs dat de warmtepomp draait. SolarPilot verandert geen Panasonic-instelling en installeert de provider niet.

Het ingestelde boilerdoel blijft de normale Panasonic-doelwaarde. Het afzonderlijke berekende SG-doel gebruikt alleen de lokaal bevestigde percentagevergelijking; dit is geen terugmelding van een werkelijk toegepast doel.

[Installatie, controle en rollback](docs/BETA97_INSTELLEN.md) · [Actuele werking](docs/ACTUELE_WERKING.md) · [Testverslag](docs/TESTRESULTATEN_BETA97.md) · [Overdracht](OVERDRACHT.md)
