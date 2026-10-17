# SolarPilot beta.95 — actuele status en duidelijke SG-diagnose

Versie: **1.0.0-beta.95** · 17 oktober 2026

Beta.95 herstelt vier fouten in instellingen toepassen, actuele afwasstatus, SG-stopregistratie en de meetdekking van dagelijkse PV-cijfers. De bestaande regeling, instellingen, minimale rust-/looptijden, broncontroles, modellen en historie blijven behouden.

## Bijwerken

1. Bewaar een actuele volledige privé Home Assistant-back-up, inclusief SolarPilot-opslag en userfiles.
2. Geef een eigen SG-aanvraag veilig vrij waar betrouwbaar mogelijk en controleer de contactstand of lokale afloop. Onderbreek geen beschermde apparaatcyclus.
3. Installeer **1.0.0-beta.95** via HACS nadat de release gepubliceerd is. Behoud dezelfde integratie-entry, bronkoppelingen en opslag.
4. Herstart Home Assistant volledig en herlaad browser/app volledig. Controleer de backend- en geladen kaartversie afzonderlijk.
5. Controleer eventuele wachtende instellingen. Een daadwerkelijk uitsluitend visueel SG-voorstel kan nu worden toegepast zonder op het einde van een actieve SG-sessie te wachten. Een echte wijziging van de regeling of bronnen houdt haar bestaande veilige wachtgrens.

## Berekend SG-boilerdoel

Het **ingestelde boilerdoel** blijft het normale doel dat Panasonic meldt. Bij 50 °C en een lokaal bevestigd profiel van 115% toont SolarPilot daarnaast **SG-doel · berekend: 57,5 °C** wanneer het contact bevestigd AAN staat. Bij een onbekend of UIT-contact heet de vergelijking **SG-doel bij AAN · berekend**. Dit is een berekening, geen afzonderlijk door Panasonic gemeld effectief doel.

Ontbreekt de berekening, dan staat de reden nu ook in het gewone overzicht en bij Warmtepomp. Open **SG-doel voor weergave instellen**, kies de juiste bestaande Panasonic-tankbron, vul het werkelijk op Panasonic ingestelde percentage in en bevestig dit lokaal. Alleen 115% invullen zonder bron en bevestiging volstaat niet. Een algemeen bevestigd SG-profiel is een andere instelling. De update vult geen universeel percentage of ontbrekende bevestiging in en schrijft geen Panasonic-doel.

## Wat verandert

- Een vergelijking met effectieve instellingen herkent uitsluitend visuele SG-wijzigingen, ook bij oudere opgeslagen standaardwaarden. Dezelfde ruimtebronnen in een andere volgorde zijn geen nieuwe bronkoppeling. Andere bronnen, toestemming of regelgrenzen worden niet langs deze route direct toegepast.
- Een oude bevestigde afwasvoltooiing blijft historie. Zij maakt een nu onbereikbare afwasmachine niet beschikbaar of bewezen UIT. Een ontbrekende oorspronkelijke rapporttijd blijft onbekend; een nieuw waargenomen einde sluit de oorspronkelijke beurt nog steeds eenmaal af.
- Nieuwe SG-stops registreren de concrete afgewezen hercontrole waar die bekend is. Algemene oude meldingen krijgen geen verzonnen specifieke oorzaak. Een expliciet onbereikbaar SG-contact krijgt de juiste bron-/contactcategorie. Stopbesluit, transport en contactstand blijven afzonderlijk.
- Dagelijkse EMS-cijfers onderscheiden gemeten, ontbrekende en oudere onbekende PV-dekking. Een geldige 0 W is een meting; ontbrekend PV is geen 0 W. Een percentage op onvolledige dekking wordt als gedeeltelijk aangeduid. Bestaande totalen blijven behouden zonder achteraf verzonnen meettijd.

De lokale Shelly-toestemming blijft standaard 300 seconden met vernieuwing na 60 seconden. De bestaande 600 W/300 seconden wolkenbuffer, SG-minimumduur en maximale sessie blijven gelijk. Panasonic blijft native geregeld, Wallbox blijft alleen uitlezen en AEG blijft één START per belading. De conservatieve leerclassificatie en PV-kalibratiefactoren veranderen niet; onvoldoende leerbewijs wordt niet automatisch goedgekeurd.

## Rollback

Bewaar eerst een actuele volledige privéback-up. Geef een eigen SG-aanvraag veilig vrij waar betrouwbaar mogelijk en onderbreek geen beschermde cyclus. Herstel zo nodig gecontroleerde beta.94-code met behoud van entry, opslag en userfiles, herstart Home Assistant volledig en herlaad browser/app. Gebruik geen twee runtimes tegelijk.

Beta.94 behoudt de regeling en de rusttijdcorrectie na herstart, maar kan de vier herstelde status-/diagnoseproblemen opnieuw tonen. Oudere code kent de nieuwe PV-dekkingsvelden mogelijk niet of bewaart die niet bij nieuwe opslag; exact herstel vraagt passende code én back-up. Herstel geen oude onverbruikte afwasaanvraag nadat dezelfde belading werkelijk gestart is.

[Actuele werking](docs/ACTUELE_WERKING.md) · [Testverslag](docs/TESTRESULTATEN_BETA95.md) · [Overdracht](OVERDRACHT.md)
