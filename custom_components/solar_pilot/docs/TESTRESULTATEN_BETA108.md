# SolarPilot beta.108 — softwarevalidatie

## Controle

De nieuwe regressies toetsen grote fictieve Wallbox-profielen boven 16 KiB, compacte recordergegevens met behoud van volledige live status, 0 W, gemeten vermogen, ontbrekend vermogen, ongewijzigde brongegevens, ontbreken van apparaatopdrachten en watt-/meetmetadata.

De 30 gerichte recorder-/Wallbox-regressies slagen lokaal, inclusief vijf nieuwe tests. Actuele uitleg, handoff, publieke repositorycontrole, SG-grens en online upstreamcontrole slagen. De volledige lokale suite loopt afzonderlijk; de volledige suite op de definitieve GitHub-commit blijft de publicatievoorwaarde. Alle vijf bestaande commitgebonden GitHub Validate-gates en de vergelijking van de vier gepubliceerde assets blijven verplicht vóór publicatie. Er is geen fysieke laad- of SG-proef uitgevoerd.

Een software-update kan niet garanderen dat externe bronnen of camera-/cloudclients bereikbaar blijven. Private installatiegegevens en logs zijn geen openbare fixtures.
