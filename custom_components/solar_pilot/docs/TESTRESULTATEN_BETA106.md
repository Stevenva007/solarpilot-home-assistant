# SolarPilot beta.106 — softwarevalidatie

## Uitgevoerde controles

- Ongewijzigde gepubliceerde beta.105-basis: **8638 tests geslaagd**.
- Volledige bijgewerkte softwarebron: **8667 tests geslaagd**; geen overgeslagen of mislukte tests.
- Gerichte controle van SG-overname, voorrang en bestaande tijdelijke SG-bediening: **47 tests geslaagd** op de nieuwe logica.
- De voorafgaande bredere controle van SG-transport, herstart, bronherkomst en externe overname: **191 tests geslaagd**.
- Werkelijke SG-kaartcode in Node uitgevoerd voor beide overzichten: externe afteller/label en geen onterechte mismatchmelding of toestelopdracht.
- JavaScript-syntax van kaart en optiehulp, actuele-uitlegconsistentie en Panasonic/SG-opdrachtgrens gecontroleerd.
- Aquarea- en SDK-defaultbranch, laatste stabiele release en tagcommits op 24 oktober 2026 opnieuw online vergeleken met de gepinde bronreview. Geen aanvullende upstreamwijzigingen. Zie [UPSTREAM_BETA106.md](UPSTREAM_BETA106.md).

## Nieuwe regressies

De nieuwe tests gebruiken fictieve bronnen, een deterministische klok en een lokaal aflopende gesimuleerde uitgang. Ze controleren de exacte vijftienminutengrens, geen AAN-herhaling tijdens waarnemen, voortzetting zonder UIT-puls, vrijgave bij te weinig zon of ongeldige voorwaarden, handmatige UIT, tijdelijke expliciete Aan, ontbrekende terugmelding, herstart vóór en na de oorspronkelijke deadline, Alleen bekijken/Pauze en het oorspronkelijke sessiemaximum.

Voorrangstests controleren eenmalige migratie van gegenereerde defaults, behoud van bewuste gebruikerskeuzes, nieuwe toestellen vóór een laatst geplaatste Wallbox, SG boven de Wallbox, afzonderlijk fysiek overschot versus voorwaardelijk laadvermogen en weigering van oude, ontbrekende, onbekende of handmatige laadsessiegegevens. De finale dispatch hercontroleert zonnebijdrage en netafname na asynchrone werkzaamheden.

`check_priority_external_ui106.py` bedient de echte kaart met fictieve data: de gemelde vier rijen, pijltjes, slepen, bevestigen, opslaan, smalle schermen en de externe SG-afteller. Deze controle is toegevoegd aan de verplichte browserjob. Een lokale Chromium-download leverde hier geen bruikbaar browserarchief; een lokale visuele uitslag wordt daarom niet geclaimd.

## Publicatievoorwaarden

De definitieve bron moet alle vijf bestaande GitHub-gates halen: repository/full-suite, HACS, Hassfest, Chromium en echte Home Assistant-startup. Publicatie op main blijft hiervan afhankelijk. De workflow maakt vervolgens beide ZIP-pakketten en beide release-documenten en vergelijkt de vier gepubliceerde assets opnieuw met de exacte tag en broncommit. Een eerder lokaal testtotaal vervangt deze commitgebonden controles niet.

## Opschoning en bewijsgrenzen

Drie niet meer aangeroepen hulpfuncties verwijderd: de oude configuratie-busy-helper en twee oude plannercontroles voor een enkel tijdstip. De werkelijk gebruikte volledige slot-/venster-/deadlinecontrole blijft staan. De actuele handleiding en optiehulp zijn samengevoegd tot één declaratieve versie, zonder eerdere append-/override-lagen; de gegenereerde documentatie blijft gelijklopen. README, startinstructie en overdracht verwijzen naar de actuele release. De oude Manual Release-workflow is verwijderd, zodat de volledige vijf-gate-/assetroute de enige publicatieroute is.

Dit is softwarebewijs. Er is geen fysieke SG-schakelproef, Wallbox-overdracht, nieuwe Aquarea-installatie of meterkalibratie in een woning uitgevoerd. De update bewijst niet dat iedere mogelijke fout afwezig is. De analyse-export en identificeerbare installatiegegevens staan niet in de openbare repository.
