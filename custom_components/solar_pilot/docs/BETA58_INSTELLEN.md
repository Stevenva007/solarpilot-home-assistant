# SolarPilot 1.0.0-beta.58 — instellen en controleren

Beta.58 hervat een gewone opgeslagen **Pauze** na een Home Assistant-herstart of integratieherlading automatisch, zodra de bestaande opstart-, bron- en opdrachtcontroles dit toelaten. De zichtbare schakelaar **Na herstart automatisch hervatten** staat standaard **Aan**. De kaart legt uit of SolarPilot automatisch wacht, bewust gepauzeerd blijft of een echte foutcontrole nodig heeft. Alle warmwater-, klimaat-, voorrangs- en meetregels uit beta.57 blijven behouden.

## Basis en upgrade

Basis en rollback zijn de gecontroleerde gepubliceerde [beta.57-release](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.57): commit `bfd49647d9a69e6a1608ecae687f04fd739a6d3b`, tree `41dbf19bc875d226fda803074b2c5a6736a0e749`, annotated tagobject `9510820fe69cd634aed36163e15b424bd683fae8`. Workflow `37457749071`, vier geslaagde jobs en alle vier release-assets zijn gecontroleerd. Beide ZIP-pakketten zijn byte voor byte met de tagbron vergeleken. De beta.57-suite behaalde lokaal 3474 tests in 39,47 s; CI behaalde 3474 tests in 51,84 s. Dit is basisbewijs; de eigen beta.58-gate staat afzonderlijk in `TESTRESULTATEN_BETA58.md`.

1. Maak een actuele volledige Home Assistant-back-up en bewaar beta.57 voor rollback.
2. Laat een lopende beschermde afwascyclus afwerken. Gebruik geen STOPRESET of stroomonderbreking. Voor een gewone upgrade is een extra Pauze-keuze niet verplicht.
3. Installeer exact `1.0.0-beta.58` via HACS, of vervang uitsluitend `custom_components/solar_pilot` met het lokale pakket. Behoud `userfiles` en Home Assistant-opslag.
4. Herstart Home Assistant volledig. Herlaad de webpagina; stop op Android de Home Assistant-app volledig en open haar opnieuw, of ververs op iOS de weergave.
5. Controleer backend én kaartversie. Open **Uitleg** en controleer beta.58 en de actuele regel-hash. Een manifestnummer alleen bewijst geen geladen kaartcode.
6. Controleer bij de modusknoppen **Na herstart automatisch hervatten: Aan** voor de gewenste automatische terugkeer. Deze keuze verandert de huidige modus niet.

SolarPilot registreert de kaart en het paneel zelf. Een extra Lovelace-resource, www-bestand of dashboard-YAML is niet nodig. Geldige leerdata, bronkoppelingen, APP-aanvragen, dashboardoverrides en bestaande veiligheidsvoorwaarden blijven behouden. Er is geen algemene leerreset of nieuwe voorrangsmigratie in beta.58. Wie van vóór beta.57 komt, behoudt wel haar éénmalige EXTRA-prioriteitsmigratie.

## Automatisch hervatten: wat gebeurt er?

| Opgeslagen situatie | Na herstart of integratieherlading |
| --- | --- |
| Gewone Pauze, automatisch hervatten Aan | Vraagt automatisch Automatisch regelen na de bestaande controles |
| Gewone Pauze, automatisch hervatten Uit | Blijft Pauze tot je een andere modus kiest |
| Automatisch regelen | Herstelt via het gewone beveiligde pad, ook als de nieuwe schakelaar Uit staat |
| Alleen bekijken of eerste installatie | Blijft Alleen bekijken; deze instelling geeft geen eerste actuatortoestemming |
| Interne fout of verwijderen voorbereid | Blijft beschermd; automatisch hervatten passeert de bewaarde reden niet |
| Echte opdrachtfout, onzekere eerdere opdracht of vereiste boilerbeoordeling | Bestaande gerichte controle en bescherming blijven gelden |

Een gewone herstart vraagt geen handmatige bevestiging. Wanneer echte toestelstatus of geldige globale P1-/veiligheidsmetingen nog ontbreken, noemt de kaart de automatische wachtreden. De normale regelrondes controleren opnieuw. Een tijdelijk onbeschikbaar eerder beheerd toestel wordt afzonderlijk beschermd; onbekend verbruik is geen vrije ruimte. Andere toestellen mogen na geldige globale controles hun eigen regeling hervatten. Wanneer het ontbrekende toestel terugkeert, wordt het zonder oude startopdracht opnieuw beoordeeld.

**Pauze nu** en **na de volgende herstart hervatten** zijn afzonderlijke keuzes. Opnieuw Pauze kiezen annuleert een momenteel wachtende hervatting. Als de schakelaar Aan blijft, geldt automatische hervatting bij de volgende herstart weer. Zet de schakelaar Uit vóór een herstart wanneer je bewust gepauzeerd wilt blijven; Uit annuleert ook een nu wachtende Pauze-hervatting. De schakelaar zelf start of stopt geen toestel en verandert de huidige modus niet.

Beta.57 bewaarde Pauze zonder afzonderlijke oorzaak. Het screenshot met Pauze bewijst daarom niet of die keuze handmatig, door voorbereiden van verwijderen of door een vroegere interne fout is ontstaan. Beta.58 probeert bij zulke oudere onbenoemde Pauze alleen het gewone beveiligde hervatpad. Nieuwe interne fout-/verwijderpauzes bewaren hun oorzaak en reden duurzaam. Een volgende gezonde meetronde laat een interne foutreden niet vanzelf verdwijnen. Bekende echte fouten en onzekere opdrachten worden nooit algemeen gewist.

Bekende echte opdrachtfouten van gewone toestellen, boiler, batterij of ruimteklimaat blijven beschermd, ook als zij tijdens een wachtende hervatting ontstaan. Een tijdelijke onbeschikbare ruimtebron is een afzonderlijke automatische bronwacht, geen nieuwe permanente foutpauze. Een geslaagde **Controle afronden** volgens de bestaande voorwaarden bevestigt een interne/opdrachtpauze, maar laat de huidige Pauze staan. Kies daarna bewust Automatisch regelen of laat een volgende herstart de bewaarde hervatvoorkeur volgen. Er wordt binnen deze controle geen automatische modus of toestelactie toegevoegd.

## Na de upgrade controleren

- Bij gewone Pauze met de schakelaar Aan: volg na de herstart **Automatische herstartcontrole** en de genoemde wachtreden; verwacht geen nieuwe knopdruk om een gewone controle af te ronden.
- Bij ontbrekende P1-/veiligheidsbron: laat de gewone automatische broncontrole opnieuw proberen; corrigeer een foutieve koppeling als die gemeld wordt.
- Bij **Opdrachtfout** of echte boilerbeoordeling: gebruik alleen de bestaande gerichte controle. Een bron die opnieuw beschikbaar is, geeft geen recht om een onzekere START of doelopdracht te herhalen.
- Een overgang naar Automatisch regelen betekent dat de regeling hervat is; het is geen bewijs dat ieder toestel onmiddellijk mag starten. Zon, prioriteit, minimumtijden en toestelvoorwaarden blijven afzonderlijk gelden.
- Alleen bekijken blijft Alleen bekijken. Kies Automatisch regelen alleen nadat de bestaande koppelingen en vrijgaven gecontroleerd zijn.

## Behouden regeling uit beta.57

Extra warm water start standaard vanaf **3000 W** werkelijk bruikbaar overschot, met de bestaande stabiliteit en rust sinds de laatste werkelijk verstuurde doelopdracht. De elektrische raming blijft **3200 W**. Een voorstel is geen write en een werkelijk gemeld 60 °C-doel is geen bewijs dat het vat al opwarmt. De bekende maandagsterilisatie 12:00/62 °C is informatie en blokkeert geen gewone 60 °C-vraag; echte gekoppelde hygiëne-, handmatige, fabrikant- en opdrachtbescherming blijven leidend.

Extra warm water mag veilige lager geplaatste eigen onderbreekbare gewone lasten laten wijken. Eerst geldige prospectieve stabiliteit, daarna bevestigde UIT, nieuwe P1 en verse PV. Het stopt hiervoor geen afwascyclus, ruimteklimaat of Wallbox. Een gereed en passend hoger afwasprogramma krijgt eerst de kans. De centrale lijst blijft de enige flexibele volgorde; de beta.57-migratie wordt niet opnieuw toegepast op een later bewust opgeslagen volgorde.

Ruimteklimaat en tapwater zijn één fysieke warmtepomp. Haar echte stroom staat al eenmaal in P1; nieuwe reserve gebruikt het ontbrekende deel van de grootste passende taak. De optionele meter onderscheidt **De hele warmtepomp** van **Uitsluitend de boiler**. Een gedeelde meter is geen specifieke tankopwarmmelding. Batterijontlading en onbekend autoladen zijn geen extra zonnevermogen.

Vanaf **2500 W** bruikbaar restoverschot gedurende **60 seconden** met nieuwe P1/PV mag AUTO beschikbaar zijn zonder temperatuurvraag of volledig geleerd model. Alleen bevestigd eigen zonne-AUTO houdt tot **2000 W** met eenmaal verse gedeelde warmtepompstroom, begrensd door echte PV. Het gewone comfortpad blijft richtingsgebonden. Dashboard-UIT, externe rust, minimumtijden en bron-/opdracht-/fabrikantbescherming blijven gelden. SolarPilot stuurt alleen HA AUTO/UIT; de onderliggende adapter kan dit globaal vertalen. Geen directe HEAT/COOL, Force DHW of ruimtedoelwijziging.

Op **Overzicht → Wat gebeurt er en waarom?** betekent doorlopend blauw bevestigde activiteit; gestippeld blauw betekent AUTO beschikbaar of werkelijk hoog gemeld tankdoel. Een voorstel, AUTO alleen of een gedeelde W-meter bewijst geen specifieke tankverwarming. Technische gegevens blijven achter Details. De volledige actuele uitleg staat in `ACTUELE_WERKING.md` en op **SolarPilot → Uitleg**.

## Analyse, bewijsgrenzen en rollback

De volledige beschikbare zeven dagen blijven als lokale beheerderdownload **JSON.GZ** beschikbaar. De compacte nieuwe analyse bewaart modus, pauzeoorzaak, hervatvoorkeur en wachtend hervatverzoek zodat een toekomstige Pauze beter verklaard kan worden. Oude onbekende oorzaken worden niet ingevuld en er komt geen traceback in publieke status. Privacyfilters, versie per nieuw record en begrensde bewaartermijnen blijven gelden. Deze werksessie voert geen live Home Assistant- of fysieke toestelactie uit. Softwaregate en publicatie-/pakketcontrole staan in `TESTRESULTATEN_BETA58.md`; een release bewijst geen geladen backend, telefoonapp, compressorstart of tankrespons.

Voor een rollback die bewust gepauzeerd moet blijven: zet in beta.58 **Na herstart automatisch hervatten Uit**, kies **Pauze**, laat beschermde cycli afwerken en herstel de onveranderlijke beta.57-release of een passende volledige back-up. Herstart daarna Home Assistant en open webpagina/app opnieuw. Controleer backend/kaart, bronnen, eigendom en beveiligingen. Beta.57 bewaart Pauze over herstarts en gebruikt de nieuwe hervatvoorkeur/pauzereden niet. Een opnieuw geïnstalleerde beta.58 kan de opgeslagen voorkeur weer lezen; zet haar bewust terug naar Aan wanneer gewenst. Programmabestanden herstellen op zichzelf geen eerdere opslag; gebruik voor exact herstel een passende volledige back-up. Geen fysieke proefopdracht om update of rollback af te dwingen.
