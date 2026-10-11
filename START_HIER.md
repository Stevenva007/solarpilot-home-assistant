# SolarPilot beta.71 — installatie en upgrade

Beta.71 toont de bestaande bevestiging van een nieuwe SG-aanleiding en de ingestelde startvertraging afzonderlijk. De privé-analyse-export onderscheidt de dertig dagen warmtepompgeschiedenis van het gekozen rollende venster. Regelgrenzen, timers, apparaatinstellingen en bestaande gegevens blijven behouden.

**Begin met [BETA71_INSTELLEN.md](docs/BETA71_INSTELLEN.md).** Daar staan behoud, back-up, controle en rollback naar beta.70. De volledige actuele werking staat in [ACTUELE_WERKING.md](docs/ACTUELE_WERKING.md) en **SolarPilot → Uitleg**. Actuele software-/publicatiestatus: [TESTRESULTATEN_BETA71.md](docs/TESTRESULTATEN_BETA71.md).

## Bestaande installatie bijwerken

1. Maak een volledige privé HA-back-up, inclusief instellingen, eigen opslag, modellen, tickets, geschiedenis en userfiles. Bewaar de gecontroleerde beta.70-code.
2. Geef een eigen SG-aanvraag vóór codevervanging vrij en controleer contact/lokale afloop. Onderbreek geen beschermde apparaatcyclus.
3. Update via HACS naar exact `1.0.0-beta.71` na publicatie, herstart HA volledig en herlaad de pagina volledig of sluit de app volledig af en open haar opnieuw.
4. Controleer backend- en kaartversie afzonderlijk. Behoud de bestaande entry, bindings, volgorde en geldige SG-/profiel-/split-/koelbevestigingen. Een ongewijzigde upgrade vraagt geen algemene herbevestiging.
5. Controleer de afzonderlijke SG-wachtfasen en, bij een bewuste analyse-export, het gekozen venster en de grensdatums. Een teller op nul geeft geen starttoestemming.

Bij lokale installatie vervang je uitsluitend `custom_components/solar_pilot`. Behoud lokale userfiles en HA-opslag; verwijder of hermaak de entry niet.

## SG-wachten en geschiedenis

De bestaande bevestiging van een nieuwe zonneperiode duurt 300 seconden met echte nieuwe bronrapporten. De ingestelde startvertraging, standaard 120 seconden, wordt apart getoond. Een verstreken bevestiging blijft wachten op een passend actueel eindrapport en de bestaande voorwaarden. Oude brondata verbergt de lopende teller.

**Geschiedenis** bij de warmtepomp blijft de bestaande dagtijdlijn en zeven/dertig-dagenweergave openen. Registratie sinds beta.70 blijft behouden, maximaal dertig lokale kalenderdagen in aparte HA-opslag. Activiteit en starts/stops zijn geen compressorbewijs. Totale gemeten elektrische energie hoort bij de meetdekking; SG-aanvraag/contact/ontvangen blijven aparte lagen.

Het analysevenster is 1, 24 of 168 rollende uren. Het warmtepompdeel omvat iedere overlappende lokale datum. Dagtotalen blijven volledige werkelijk geregistreerde kalenderdagtotalen, met expliciete gedeeltelijke grensdatums. Geen evenredige energieknip, ingevulde meetgaten of historische backfill.

Panasonic beheert zijn native regeling en beveiligingen. SolarPilot gebruikt uitsluitend de bestaande toegewezen SG-uitgang. Alle lokaal gekozen percentages, koelwaarden, programma's en overige apparaatinstellingen blijven behouden.

## Rollback naar beta.70

Geef de eigen SG-aanvraag vrij, controleer contact/lokale afloop, stop beta.71 en herstel gecontroleerde beta.70-code. Beta.70 gebruikt dezelfde aparte warmtepompgeschiedenis; behoud de entry, opslag en userfiles. Alleen de verbeterde wachtweergave en exportvensteruitleg vallen terug. Voor exact herstel van de pre-upgradetoestand gebruik je code én de volledige passende privéback-up; bewaar gewenste nieuwe historie eerst. Laat nooit twee runtimes tegelijk werken. De volledige procedure staat in [BETA71_INSTELLEN.md](docs/BETA71_INSTELLEN.md).
