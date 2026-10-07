# SolarPilot 1.0.0-beta.61 — testresultaten

Datum: **2026-10-07**

## Bronbasis en bewijsgrenzen

De absolute codebasis en rollbackbasis zijn gepubliceerde beta.60 op commit `213b31a69c9768aea7a6b52e845f2cc6e77bb7de`, tree `378533419b62251b218238fad4d242f3efe5bf81`, annotatietagobject `3968c772103828c9e3781fca5adc575630faacc0`. De onveranderlijke [beta.60-release](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.60), release-ID `404797193`, workflow `37475747281` en alle vier gepubliceerde assets zijn gecontroleerd. HACS-archief: 380 bestanden; lokaal pakket: 126 bestanden. Beide ZIP-pakketten zijn inhoudelijk en met SHA-256 tegen de exacte gepubliceerde bron vergeleken. Lokaal behaalde beta.60 3630 tests in 45,70 s; CI behaalde 3630 tests in 33,31 s. Dit is basisbewijs, geen beta.61-test-/publicatiebewijs.

De gebruikersmelding betreft een blijvende boileropdrachtfout terwijl **Controle afronden** niets lijkt te veranderen. De codeanalyse onderscheidt de generieke ordinary-reset van de afzonderlijke boilerreview: ordinary reset wist de DHW-fout niet, en een pure opgeslagen boilerfout kon buiten de oude Hervat-melding vallen. Het screenshot bewijst niet waarom de fysieke doelopdracht of cloudterugmelding oorspronkelijk mislukte. Regressies en voorbeelden gebruiken fictieve Home Assistant-data; privébronnen en installatie-identiteiten blijven buiten publieke code en pakketten.

## Softwaregate

De definitieve volledige lokale suite op de bevroren beta.61-code behaalt **3814 geslaagde tests in 46,62 s** onder Python 3.12.14. Dit omvat de behouden 3630 basisgevallen en **184 nieuwe regressies**. Uitvoering: `PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider`.

| Nieuwe regressies | Geslaagd |
| --- | ---: |
| Begrensd DHW-foutbewijs en automatische hercontrole | 76 |
| Gerichte backend-/dashboardboilercontrole en generieke resetroutering | 36 |
| Herstelbarrière, nieuwe metingen en veilige doorgang van overige lasten | 12 |
| HA-controlemeldingen, transport, opslag en langdurige ACK-wacht | 58 |
| DHW-fout-/herstelkopieën in het bestaande onderzoekslog | 2 |
| **Totaal nieuw** | **184** |

| Aanvullende lokale controle | Uitkomst |
| --- | --- |
| Publieke repositorypreflight | Geslaagd |
| Alle 15 actuele overdrachtssecties | Geslaagd |
| Actuele HA-uitleg en releasegebonden optiehulp | Geslaagd — regel-hash `40c0493c856ad3cf`, 441 hulpvelden |
| Repositorystructuur en pakketbronvalidatie | Geslaagd |
| Python-syntax/AST | Geslaagd — 68 productiebronnen |
| JSON-validatie | Geslaagd — 4 bestanden |
| Node-syntaxcontrole | Geslaagd — beide JavaScript-bestanden |
| Actuele uitleg, installatiehandleiding en testverslag: root/component-mirrors | Alle drie paren bytegelijk |
| `git diff --check` | Geslaagd |

De nieuwe regressies toetsen automatisch herstel van bekende fouten via verse rapportage van na de fout: late passende melding van het aangevraagde doel, of twee overeenkomende normale doelen over minstens 60 seconden. Het afzonderlijke hersteljournal en de foutreeks blijven bij dezelfde koppeling over herstart behouden. Hercontrole stuurt geen temperatuur en herhaalt geen oude aanvraag. Wachttijden van 300/900/3600 seconden, bij herhaling maximaal één nieuwe poging per uur, bestaande opdrachtrust en actuele P1/PV, prioriteiten, serialisatie en doelgrenzen blijven vereist. Een betrouwbaar vastgesteld native doel laat andere veilige lasten doorgaan terwijl de boiler lokaal wacht. Handmatige pauze, onbekende fout, gewijzigde koppeling en bron-/fabrikantbescherming blijven apart. De optionele gerichte kaart-/backendbeoordeling vereist werkelijk bevestigde Pauze/Alleen bekijken met duidelijke voorwaarden en resultaat; generieke reset bij alleen DHW geeft geen vals succes. Eén laatste diagnose-record blijft bewaard zonder opdrachttoestemming, ook na beoordeling; ontbrekend bewijs blijft onbekend.

Meldingsregressies toetsen een aparte stabiele HA-controlemelding voor echte handmatige fouten, juiste betrokken onderdelen/acties, wijzigingsgestuurd bijwerken en verwijderen na oplossing. Korte automatische boilerhercontrole, gewone bronwacht/isolatie, herprobeerwachttijd op zichzelf, hygiëne, gebruikers-Pauze en normale handmatige dashboardmodus blijven uitgesloten. Langdurige bekende ACK-onzekerheid vanaf vijftien minuten geeft dezelfde stabiele verbinding-/doelcontrolemelding, zonder foutreset te vereisen of automatische checks te stoppen; herstel verwijdert deze melding. Een meldingtransportfout laat de regelaar niet crashen. Ook echte bronconfiguratiefouten en werkelijk actieve dubbele regelingen worden gericht zichtbaar; tijdelijke bronwacht blijft uitgesloten.

Alle behouden beta.60-uitleg-, openstaat-, Recorder-/presentatie-, gegevensbehoud- en warmtepompvermogensgevallen blijven in de samengestelde suite. Dit omvat alle eerdere herstart-, prioriteits-, klimaat-, warmwater-, afwas-, Wallbox- en elektrische/fabrikantbescherming.

De eigen beta.61-CI, tag, release en assetcontrole moeten na upload afzonderlijk uitgevoerd en geverifieerd worden. Bovenstaande lokale softwaregate is geen nieuw publicatiebewijs.

## Betekenis en beperkingen

Bekende automatische foutreconciliation is read-only. Een eventuele nieuwe poging volgt pas een latere actuele beleidsbeoordeling na een nieuwe P1-rapportage, met begrensde foutwachttijd; handmatige review blijft optionele gerichte fallback. Geen fysieke proefopdracht of blinde oude opdrachtreplay. Een nieuwe passende HA-doelrapportage blijft nodig voor werkelijk uitgegeven tankdoelen; de bestaande tien-secondenadapterwacht en 180-secondentimeout blijven gelden. Een doelrapportage bewijst geen onafhankelijk fysiek ACK of daadwerkelijk bereikte tanktemperatuur.

Geen live Home Assistant-, telefoonapp-, volledige browser- of fysieke toestelacceptatie is uitgevoerd. Software-/DOM-doubles en fictieve voorbeelden bewijzen geen daadwerkelijke compressoractie of reparatie van een fysieke/cloudverbindingsstoring. Warm water en ruimteklimaat blijven afwisselende taken op één gezamenlijk gemeten warmtepomp.

De foutdiagnose voegt begrensd operationeel bewijs toe en verandert geen meetretentie. Actuele attributen, eigen modellen en werkelijk beschikbare export blijven behouden; geen onbeperkt archief of backfill.

Naast het laatste diagnose-record bewaart de bestaande lokale onderzoeksregistratie nieuwe boilerfout- en herstelgebeurtenissen met een kopie van aangevraagd/gemeld doel, wachttijd en soort beoordeling. Daardoor kan een nieuwer laatste record het eerdere gestructureerde spoor binnen de werkelijk beschikbare onderzoeksperiode behouden. Deze gebeurtenissen vallen onder de bestaande maximaal zeven dagen en vaste aantallimieten; er is geen onbeperkt archief of aanvulling achteraf. Een fout in deze aanvullende registratie mag de regelaar niet laten vastlopen.

## Publicatie en installatie

De eigen [beta.61-release](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.61) moet een annotated tag op exact de geteste commit, vier geslaagde workflowjobs, twee ZIP-pakketten en twee beta.61-documenten hebben. Alle vier assets downloaden en grootte/SHA-256 controleren; beide ZIP-inhouden moeten exact met de tagbron overeenkomen. Eerdere tags en assets blijven onveranderd. Publicatiebewijs pas afleiden uit de werkelijke nieuwe release, niet uit oudere softwaregates.

Installatie en rollback staan in `BETA61_INSTELLEN.md`. Home Assistant herstarten, app/webpagina heropenen en backend-/kaartversie apart controleren. Rollbackbasis beta.60 behoudt de uitgebreide uitleg en eerdere reparaties, maar mist automatische bekend-fouthercontrole, begrensde foutwachttijden, gerichte boilercontrole en foutdiagnosespoor. Haar generieke controle verhelpt geen boilerfout.
