# SolarPilot beta.93 — installatie en upgrade

Versie: **1.0.0-beta.93** · 16 oktober 2026

Beta.93 herstelt korte terugkerende **Taak onbekend**-intervallen tijdens Aquarea-bronhercontrole en laat andere toestellen weer hun werkelijk beschikbare zonneoverschot gebruiken wanneer Wallbox-laadgegevens ontbreken. De auto hoeft niet eerst te laden om de gewone automatiseringen te laten werken. Verse echte bronnen en de gewone apparaat- en netvoorwaarden blijven nodig.

## Bijwerken

1. Bewaar een actuele volledige privé Home Assistant-back-up met SolarPilot-opslag en userfiles.
2. Geef een eigen SG-aanvraag veilig vrij waar betrouwbaar mogelijk; onderbreek geen beschermde apparaatcyclus.
3. Installeer exact **1.0.0-beta.93** via HACS nadat de release gepubliceerd is. Behoud dezelfde integratie-entry, instellingen, opslag en userfiles.
4. Herstart Home Assistant volledig en herlaad browser/app. Controleer backend- en kaartversie afzonderlijk.
5. Nieuwe taakregistraties houden bij ongewijzigde actuele brongegevens hun taak tijdens de hercontrole. Gewone toestellen en SG beoordelen actuele vrije zonnestroom zonder op ontbrekende Wallbox-data te wachten. Eerdere onbekende historie blijft bewaard.

Er is geen nieuwe bron of instelling nodig. Alle bestaande Aquarea-, PV-, SG-, leer-, toestelherstel- en meldingsfuncties blijven behouden. De gewone uitvoeringsroute beslist opnieuw met de actuele vrije zonne-energie en bestaande toestelvoorwaarden. Panasonic en Wallbox blijven uitsluitend via hun bestaande toegestane routes betrokken; geen nieuwe native schrijfbevoegdheid.

## Welke onderbreking wordt hersteld?

De interne bronherkenning werd elke vijf minuten opnieuw gecontroleerd. Tijdens de asynchrone controle verdween het eerdere bewijs meteen, waardoor één of meer registratietikken onbekend werden. Bij dezelfde daadwerkelijk geladen module en semantiek blijft het eerder geverifieerde bewijs nu kort beschikbaar tot de inspectie klaar is. Een gewijzigde of onbruikbare koppeling trekt dat bewijs in. De gewone grenzen voor echte bronactualiteit worden niet verlengd.

## Vrije zonnestroom bij onbekende Wallbox

De actuele P1-injectie bevat het verbruik van de hele woning, inclusief de auto. Dit werkelijk vrije overschot is leidend voor gewone verbruikers en SG, na bestaande reserves, batterijcorrectie en toewijzing aan andere lasten. Bruto PV-productie wordt niet als volledig vrije ruimte beschouwd.

Oude, ontbrekende of ongeldige Wallbox-data blijft onbekend. Zij creëert geen extra verbruiksreserve, 0 W-startlimiet, geforceerde stop van gewone lasten of overneembaar EV-vermogen. SG krijgt nooit EV-krediet. Een actuele bewezen laadvraag of laadsessie behoudt de ingestelde voorrang. De actuele net-/fase-/kwartiergrenzen, minimumtijden, beschermde programma’s, opdrachtbevestiging en eigen apparaatvoorwaarden blijven gelden.

## Rollback

Herstel zo nodig beta.92 met behoud van entry, opslag en userfiles en herstart HA volledig. Geef een eigen SG-aanvraag veilig vrij waar betrouwbaar mogelijk en gebruik geen twee runtimes tegelijk. Beta.92 behoudt de rustige meldingen, maar kan tijdens de bronhercontrole opnieuw korte onbekende taken registreren en andere lasten door ontbrekende Wallbox-data blokkeren.

[Actuele werking](docs/ACTUELE_WERKING.md) · [Testverslag](docs/TESTRESULTATEN_BETA93.md) · [Overdracht](OVERDRACHT.md)
