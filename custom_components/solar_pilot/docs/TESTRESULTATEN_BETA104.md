# SolarPilot beta.104 — test- en publicatieverslag

Versie: **1.0.0-beta.104** · 22 oktober 2026

Bouwbasis: beta.103 `8a81fc0ab5134d99d56da9941cbc5cfe0a8b7ecd`. Alle fixtures zijn synthetisch. Privé-exportgegevens zijn niet opgenomen.

## Uitgevoerd vóór definitieve CI

- **203 bestaande gerichte regressies geslaagd**: toestelhercontrole, source waits, isolatie-UI, runtime en herstartmodus.
- **16 nieuwe regressies geslaagd** in `tests/test_nonblocking_review104.py`: gelijktijdige afwas-/Wallbox-onbereikbaarheid, gezonde restzonstart, geen start bij onvoldoende overschot, bewaarde eigendoms-/herstartgegevens, gerichte echte foutreview, oude/restored UIT na onzekere opdracht, bescherming lopende batterijopdracht, automatische Wallbox-herstelweergave en kaartteksten zonder resetknop.
- De volledige lokale suite kon niet als voltooid worden beoordeeld: drie modules vereisen de lokaal ontbrekende dependency voluptuous; een bredere proef zonder die modules is vóór voltooiing afgebroken. Dit is geen volledige-suite-pass.

## Vereiste definitieve validatie

De ongewijzigde Validate-workflow moet op de definitieve bron alle vijf gates laten slagen: repository/privacy/documentatie/upstream en volledige pytest-suite, HACS, Hassfest, echte Home Assistant-start en Chromium. De status van de bijbehorende GitHub-run is het actuele bewijs; dit bestand claimt geen al voltooide toekomstige run, merge, release of gebruikersinstallatie.

De online upstreamgate controleert opnieuw defaultbranches, HEADs, laatste stabiele releases en tagcommits. De inhoudelijk beoordeelde Aquarea 1.8.1- en SDK 1.4.0-pins zijn behouden; nieuwe upstreamwijzigingen blokkeren publicatie tot beoordeling.

## Grenzen

Geen opslagmigratie, nulaanname bij onbekend vermogen of uitbreiding van actuatorrechten. Echte opdrachten en elektrische guards blijven beschermd. Een gewone bronwachter wordt nooit door een onafhankelijke foutreview gewist; herstel kan alleen door passende echte brongegevens worden vastgesteld. Softwaretests bewijzen geen fysieke toestelwerking of uitgevoerde Home Assistant-installatie.

## Releasebestanden

Na alle vereiste gates publiceert de bestaande workflow exact `v1.0.0-beta.104` met de volledige GitHub-HACS-ZIP, lokale component-ZIP en beide beta.104-documenten. Voor en na upload worden de vier assets vergeleken met dezelfde bron. Geen bestaande tag of asset overschrijven. Dit verslag en de installatiehandleiding hebben bytegelijke componentmirrors.
