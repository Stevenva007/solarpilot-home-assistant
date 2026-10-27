# SolarPilot beta.109 â€” softwarevalidatie

## Controle

De nieuwe regressies toetsen grote fictieve Wallbox-profielen boven 16 KiB, compacte recordergegevens met behoud van volledige live status, 0 W, gemeten vermogen, ontbrekend vermogen, ongewijzigde brongegevens, ontbreken van apparaatopdrachten en watt-/meetmetadata.

De 30 gerichte recorder-/Wallbox-regressies slagen lokaal, inclusief vijf nieuwe tests. Actuele uitleg, handoff, publieke repositorycontrole, SG-grens en online upstreamcontrole slagen. De volledige Windows-run bereikte 8705 geslaagde tests; zes mislukkingen en twee foutmeldingen kwamen uit POSIX-bestandsrechten, Git-CRLF-archiefvergelijkingen en de Windows-omgevingslimiet. De Linux-CI voert deze platformafhankelijke controles ongewijzigd uit. De echte HA-startupjob gebruikt Ubuntu 24.04 voor de vastgelegde Python 3.14.2; ubuntu-latest is inmiddels Ubuntu 26.04 zonder dat Python-pakket. Alle vijf bestaande commitgebonden GitHub Validate-gates en de vergelijking van de vier gepubliceerde assets blijven verplicht vÃ³Ã³r publicatie. Er is geen fysieke laad- of SG-proef uitgevoerd.

Een software-update kan niet garanderen dat externe bronnen of camera-/cloudclients bereikbaar blijven. Private installatiegegevens en logs zijn geen openbare fixtures.
