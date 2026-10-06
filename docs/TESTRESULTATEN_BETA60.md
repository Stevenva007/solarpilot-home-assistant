# SolarPilot 1.0.0-beta.60 — testresultaten

Datum: **2026-10-06**

## Bronbasis en bewijsgrenzen

De absolute codebasis en rollbackbasis zijn gepubliceerde beta.59 op commit `32874118ba45a32d835d0a3189e75402ad62f8c3`, tree `21b3de88b4a3fe9b44d7cee183046d6076cbc8e0`, annotatietagobject `4e2e32d0c187e39908e1b5c3f7856996ca1a2312`. De onveranderlijke [beta.59-release](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.59), release-ID `404727324`, workflow `37469667437` en alle vier gepubliceerde assets zijn gecontroleerd. Beide ZIP-pakketten zijn inhoudelijk en met SHA-256 tegen de exacte gepubliceerde bron vergeleken. Lokaal behaalde beta.59 3569 tests in 44,55 s; CI behaalde 3569 tests in 52,59 s. Dit is basisbewijs, geen beta.60-test-/publicatiebewijs.

De gebruikersvraag betreft uitgebreidere verklaringen per regeling op Overzicht, bekend vermogen met brononderscheid en dezelfde Recorder-/presentatiecorrectie bij de native lokaal-leren-schakelaar. Regressies en voorbeelden gebruiken fictieve Home Assistant-data. Geen privé-export of installatie-identiteit wordt gepubliceerd. De UI verklaart bestaande runtime-informatie en doet geen eigen regeling.

## Softwaregate

**Geslaagd: 3630 tests in 45,70 s.** De definitieve volledige suite draaide met `PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider`.

61 nieuwe regressies toetsen de echte kaartbron en native metadatacontracten: 29 UI-tests voor alle uitklappers, identiteitsvast openherstel, programma-/uitvoerreden, watts, bronescaping en onbekende/nulmetingen; 25 tests voor het actuele exclusieve warmtepomp-/tankvermogen; 7 leren-schakelaartests voor Recordergrootte, gedeelde presentatiecache en behoud van volle live/eigen/exportdata. De aanvullende selectie voor forecast, uitgebreide uitleg en bestaande beslisregels behaalde 115 tests in 3,53 s. Het bestaande forecastcachetestgeval gebruikt nu een vaste tijd binnen één uur: een echte uurgrens vereist juist een verversing en mocht deze cachetest niet tijdsafhankelijk maken. Het productiegedrag aan uurgrenzen is behouden.

Publieke preflight, alle 15 handoffsecties, actuele uitleg/versie/441 hulpvelden (regel-hash `99d8ea738648816f`), repositorystructuur, gelijke installatiekopieën en diffcontrole zijn geslaagd. AST controleerde 67 Python-bestanden en JSON-controle 4 bestanden; `node --check` controleerde beide frontendbestanden. De fictieve voorbeeldpagina is opnieuw gegenereerd. De beta.59-resultaten hierboven zijn uitsluitend bewijs van de bronbasis.

| Onderdeel | Getoetst contract |
| --- | --- |
| Gewone toestellen | Zelfde startdiagnose als Toestellen, bekende watts, voorwaarden en wachttijden |
| Warm water | Werkelijk doel versus voorstel, correcte positieve tekst bij vervulde gates, actuele uitvoeringsvoorwaarden |
| Klimaat | Per ruimte programmebewijs, gebruikersoverride, pending, zonne-/comfortbevestiging en onbekend bewijs |
| Wallbox/batterij | Alleen echte read-only Wallboxredenen; batterijadvies gescheiden van bevestigde actie/fout/pending |
| Vermogen | Gemeten versus geschat versus onbekend; afwisselende warmtepomptaken op één gezamenlijke meting zonder parallelle som |
| Openstaat | Stabiele interne identiteit bewaart open uitleg over updates en rijherschikking |
| Read-only | Uitleg openen doet geen actuatoractie of instelling-/prioriteitswijziging |
| Leren-schakelaar | Gedeelde presentatie per publicatie; grote Recorderkopie uitgesloten, volle live/eigen/exportdata en aan/uitwerking behouden |
| Cumulatieve regeling | Beta.59-crash-/kleur-/Recorder-/cachefix en alle eerdere herstart-/warmwater-/klimaat-/voorraad-/veiligheidsregressies behouden |

## Betekenis en beperkingen

Uitleg van voorwaarden is geen bewijs van fysieke uitvoering. Een voorstel, AUTO of globaal warmtepompvermogen bewijst geen specifieke tankopwarming. Warm water en ruimteverwarming/koeling wisselen elkaar af op dezelfde warmtepomp; één gezamenlijke meting, niet apart opgeteld. Er is geen tweede fysieke verbruiker toegevoegd. Onbekende bron wordt geen nulmeting en een raming geen echte W-meting.

Recorderuitsluiting betreft uitsluitend zware herhaalde detailpakketten. Actuele attributen, eigen modellen en werkelijk beschikbare export blijven volledig behouden, met bestaande bewaartermijnen; geen onbeperkt archief of backfill. Presentatiecache wordt gedeeld door statusweergaven, nooit door fysieke regelbesluiten of directe analyse/export.

Geen live Home Assistant-, telefoonapp- of fysieke toestelacceptatie is uitgevoerd. Software-/DOM-doubles en gerenderde voorbeelden zijn geen bewijs van daadwerkelijke compressoractie, thermische voorspelnauwkeurigheid of live prestatieverbetering.

## Publicatie en installatie

De eigen [beta.60-release](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.60) moet een annotated tag op exact de geteste commit, vier geslaagde workflowjobs, twee ZIP-pakketten en twee beta.60-documenten hebben. Alle vier assets downloaden en grootte/SHA-256 controleren; beide ZIP-inhouden moeten exact met de tagbron overeenkomen. Eerdere tags en assets blijven onveranderd. Publicatiebewijs pas afleiden uit de werkelijke nieuwe release, niet uit oudere softwaregates.

Installatie en rollback staan in `BETA60_INSTELLEN.md`. Home Assistant herstarten, app/webpagina heropenen en backend-/kaartversie apart controleren. Rollbackbasis beta.59 behoudt haar reparaties maar mist nieuwe uitgebreide uitleg en leren-schakelaarcorrectie; beta.60 heeft geen nieuwe opslagmigratie.
