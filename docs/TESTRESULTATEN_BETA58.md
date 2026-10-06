# SolarPilot 1.0.0-beta.58 — testresultaten

Datum: **2026-10-06**

## Bronbasis en bewijsgrenzen

Basis is de gecontroleerde gepubliceerde beta.57: commit `bfd49647d9a69e6a1608ecae687f04fd739a6d3b`, tree `41dbf19bc875d226fda803074b2c5a6736a0e749`, annotated tagobject `9510820fe69cd634aed36163e15b424bd683fae8`. Release `404640253`, workflow `37457749071`, vier geslaagde jobs en vier release-assets zijn gecontroleerd. Beide ZIP-pakketten zijn byte voor byte met de tagbron vergeleken. Lokaal behaalde beta.57 3474 tests in 39,47 s; CI behaalde 3474 tests in 51,84 s. Dit is basisbewijs, geen beta.58-resultaat.

Een screenshot met Pauze uit beta.57 bewijst de opgeslagen modus, maar niet haar vroegere oorzaak. Die release bewaarde geen afzonderlijke pauzereden. De nieuwe voorkeur verandert het toekomstige herstartbeleid; zij bewijst niet achteraf een fysieke foutoorzaak. Regressies en voorbeelden gebruiken fictieve gegevens. Geen privé-export of installatie-identiteit wordt gepubliceerd.

## Softwaregate

**Geslaagd na de laatste functionele wijziging: 3561 tests in 41,68 s.** De volledige suite draaide met `PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider`. De 87 nieuwe gevallen toetsen de opstartmodus en de dashboard-/native bediening. Publieke preflight, alle 15 handoffsecties, actuele uitleg/versie/hulp, repositorystructuur en `git diff --check` zijn geslaagd. AST controleerde 67 Python-bestanden; JSON-controle 4 bestanden; `node --check` controleerde beide frontendbestanden. Canonieke uitleg: regel-hash `db857daeaac62ed1`, 441 hulpvelden. De fictieve voorbeeldpagina is opnieuw gegenereerd.

De oude sensorfixture is uitgebreid met de nieuwe opstartvelden; haar isolatie-/reserveasserties blijven behouden. Tests die bewust een blijvende Pauze toetsen zetten de nieuwe hervatvoorkeur expliciet Uit. Er zijn geen productieguards versoepeld om deze oudere verwachtingen te behouden. Een eerste tussenrun met nog niet gegenereerde uitleg/hulp en de oude fixture was geen geldige releasegate; de bovenstaande volledige run gebruikte de bevroren code en actuele artefacten.

| Onderdeel | Te toetsen contract |
| --- | --- |
| Gewone Pauze na herstart | Standaard Aan vraagt solar via het bestaande beveiligde herstelpad |
| Voorkeur Uit | Opgeslagen Pauze blijft Pause; opgeslagen solar houdt normale herstelroute |
| Alleen bekijken / eerste installatie | Geen automatische eerste activering |
| Directe bediening | Voorkeur wijzigen verandert huidige modus niet; Pauze annuleert nu wachtende hervatting |
| Fout-/verwijderpauze | Oorzaak en reden duurzaam bewaard; gezond vervolg wist interne reden niet |
| Bestaande bescherming | Echte ordinary/DHW/battery/climate-command-fouten en DHW-review niet gepasseerd, ook tijdens wachten; tijdelijke klimaatbronwacht modulelokaal |
| Gerichte controle | Bestaande off/pending-voorwaarden; bevestigen interne/opdrachtpauze laat Pauze staan zonder directe solar- of toestelactie |
| Compacte diagnose | Nieuwe modus/pauzeoorzaak/voorkeur/hervatverzoek, geen verzonnen oude reden of publieke traceback |
| Oudere opslag | Geen verzonnen pauzeoorzaak; alleen normale beveiligde hervatting |
| Dashboard en native switch | Dezelfde voorkeur, begrijpelijke automatische wacht-/foutreden, geen tweede regeling |
| Cumulatieve regeling | Alle beta.57-voorrangs-, DHW-, zon-/comfort-, shared-HP-, export- en activiteitregressies behouden |
| Uitleg en repository | Versie58, één canonieke uitleg/hulp, gelijke installatiekopieën, handoff/preflight |

## Betekenis en beperkingen

Automatisch hervatten activeert de gewone regelaar, geen lijst met onvoorwaardelijke toestelstarts. Elk apparaat behoudt actuele bronnen, deelname, prioriteit, minimumtijden en elektrische/fabrikantbescherming. Oude opdrachten worden niet opnieuw verstuurd en een onzekere afwas-START blijft beschermd. Een tijdelijk ontbrekend toestel blijft afzonderlijk beschermd en kan later op echte status terugkeren.

Pauze nu geldt tot een nieuwe bewuste moduskeuze of, met de voorkeur Aan, een volgende beveiligde herstart. De schakelaar wijzigen is geen onmiddellijke modus- of actuatoropdracht. Alleen bekijken en een eerste installatie blijven Alleen bekijken. Interne fout-/verwijderpauzes en bekende echte opdrachtfouten vereisen hun bestaande beoordeling.

Geen live Home Assistant- of fysieke toestelacceptatie is uitgevoerd. HA-/DOM-doubles toetsen softwaregedrag, geen daadwerkelijk geladen app, compressoractie, tankrespons of thermische voorspelkwaliteit.

## Publicatie en installatie

**Afzonderlijke publicatiecontrole naast de softwaregate.** De eigen [beta.58-release](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.58) moet een annotated tag op exact de geteste commit, vier geslaagde workflowjobs, twee ZIP-pakketten en twee beta.58-documenten hebben. Download alle vier assets, controleer SHA-256 en vergelijk beide volledige ZIP-inhouden met de exacte tagbron. Eerdere releases blijven onveranderd. De exacte workflow-/tag-/assetgegevens worden pas uit de werkelijke nieuwe publicatie afgeleid; bovenstaande lokale softwaregate claimt die controle niet vooraf.

Installatie en rollback staan in `BETA58_INSTELLEN.md`. Na installatie Home Assistant herstarten, app/webpagina opnieuw openen en backend-/kaartversie controleren. Beta.57 bewaart Pauze over herstarts en gebruikt de beta.58-hervatvoorkeur niet. Programmabestanden herstellen eerdere opslag niet vanzelf; gebruik zo nodig een passende volledige back-up. Publicatie is geen installatieacceptatie.
