# SolarPilot 1.0.0-beta.59 — instellen en controleren

Beta.59 verhelpt ook de melding over te grote leergegevens voor de Home Assistant-historiek en vermindert herhaald rekenwerk bij het bijwerken van het dashboard. De volledige leer- en modelgegevens blijven beschikbaar in SolarPilot zelf, in de eigen opslag en in de analyse-export. Home Assistant bewaart bij de gewone sensorhistoriek alleen de kleine samenvatting, zodat dezelfde grote modellen niet iedere keer worden gekopieerd. De melding gaat over de maximale grootte van één historiekregel, niet over vrije schijfruimte. Bestaande bewaartermijnen blijven behouden; dit voegt geen onbeperkt archief van alle ruwe meetpunten toe.

Beta.59 herstelt een concrete interne fout bij het berekenen van de avondvoorraad voor warm water. Met een bruikbare zonnevoorspelling kon die berekening vastlopen en de algemene regeling naar een beschermde Pauze laten gaan. De berekening kan nu doorgaan. Het screenshot van Pauze na kiezen van Automatisch regelen bewijst zonder bijbehorende foutregel niet dat juist deze fout op de live installatie optrad.

Beta.59 maakt de twee actuele energietegels **Zonnepanelen** en **Net** herkenbaar met een gekleurde rand, zachte achtergrond en een kleurverloopbalk. Zonneproductie loopt van rood via oranje, geel en lichtgroen naar groen naarmate meer van de ingestelde omvormergrens wordt gebruikt. Netinjectie is groen; rond nul is de kleur lichtgroen en stijgende netafname loopt via geel en oranje naar rood. De getallen en de woorden afname/injectie blijven zichtbaar. Oude of onbeschikbare metingen blijven grijs en onbekend. Dit is alleen weergave, geen foutmelding, regelwijziging of nieuwe vermogensvrijgave.

## Basis en upgrade

De absolute codebasis en rollbackbasis zijn gepubliceerde beta.58 op commit `5920c3f3156cd62f508559ee5a860e1bec9e9c9a`, tree `3a8838c63897285b32f1829b0ccf59b96fe59e3c`, annotatietagobject `b385d59109de64f1e7da0367f01baadb88d49547`. De onveranderlijke [beta.58-release](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.58), release-ID `404666467`, workflow `37461351451` en alle vier gepubliceerde assets zijn gecontroleerd. Beide ZIP-pakketten zijn inhoudelijk en met SHA-256 tegen de exacte gepubliceerde bron vergeleken. Lokaal behaalde beta.58 3561 tests in 41,68 s; CI behaalde 3561 tests in 52,14 s. Dit is basisbewijs, geen beta.59-test-/publicatiebewijs.

1. Maak een actuele volledige Home Assistant-back-up en bewaar beta.58 voor rollback.
2. Laat een lopende beschermde afwascyclus afwerken; onderbreek haar niet via de stekker of STOPRESET.
3. Installeer exact `1.0.0-beta.59` via HACS of vervang uitsluitend `custom_components/solar_pilot` met het lokale pakket. Behoud `userfiles` en Home Assistant-opslag.
4. Herstart Home Assistant volledig. Herlaad de webpagina; stop op Android de Home Assistant-app volledig en open haar opnieuw, of ververs de weergave op iOS.
5. Controleer backend én kaartversie. **SolarPilot → Uitleg** moet beta.59 en de actuele regel-hash tonen. Een manifestnummer bewijst geen geladen kaartcode.
6. Staat een eerdere interne foutpauze nog opgeslagen, kies één keer Automatisch regelen. Volg alleen een afzonderlijk gemelde herstart- of boilerbeoordeling als die keuze daardoor geweigerd wordt.
7. Controleer de twee energietegels op **Overzicht**. Hiervoor is geen extra instelling, dashboard-YAML of Lovelace-resource nodig.

Alle instellingen, geldige leerdata, bronkoppelingen, APP-aanvragen, prioriteiten, dashboardoverrides en veiligheidsvoorwaarden blijven behouden. Beta.59 voegt geen configuratie- of rangordemigratie toe. Bij een upgrade van vóór beta.57 blijft haar bestaande éénmalige EXTRA-prioriteitsmigratie gelden.

## Leerdata, historiek en reactiesnelheid

De melding **attributes exceed maximum size** betekent dat één pakket sensorhistoriek te groot is voor Home Assistant Recorder. Extra vrije schijfruimte verandert die per-pakketlimiet niet. Beta.59 laat de grote leer-/modeldetails daarom uit die herhaalde historiekkopie weg, terwijl de actuele details in SolarPilot, haar eigen opslag en de volledige beschikbare analyse-export blijven staan. Er wordt geen leerdata of Home Assistant-opslag verwijderd.

De sensoren delen het presentatieoverzicht per publicatieronde; zo hoeft dezelfde fase-/leer-/EMS-uitleg niet telkens voor iedere sensor opnieuw opgebouwd te worden. De besturing blijft haar eigen actuele bronnen lezen. Een eerdere melding over een trage sensorupdate bewijst niet dat de fysieke fasebewaking gestopt is. Controleer na laden of nieuwe grootte- en traagheidsmeldingen terugkomen; bewaar dan het tijdstip en de gemelde entiteit.

De bestaande bewaartermijnen blijven gelden, waaronder de beschikbare analyseperiode tot zeven dagen. Deze reparatie maakt geen onbeperkt archief van alle ruwe meetpunten en vult ontbrekende eerdere Recorder-records niet achteraf aan. De gecomprimeerde export bewaart alle werkelijk beschikbare gegevens binnen de bestaande grenzen.

## Interne fout en herstel

De reparatie voorkomt het concrete vastlopen van de zonnige avondvoorraadberekening; zij wist geen eerder opgeslagen foutoorzaak.

Zie je na installeren nog de eerder opgeslagen interne foutpauze, kies dan één keer **Automatisch regelen**. Deze bewuste keuze hervat na de codeherstelling de gewone regeling; er is daarvoor geen algemene reset nodig. Alleen als een afzonderlijke herstart- of boilerbeoordeling wordt gemeld, volg je de genoemde controlevoorwaarden en gebruik je waar vereist **Controle afronden**. Wordt de regeling opnieuw door een interne fout gepauzeerd, bewaar dan het tijdstip en de bijbehorende SolarPilot-foutmelding met foutdetails uit **Instellingen → Systeem → Logboeken**. Voor die foutanalyse is een grote zeven-dagenexport niet nodig. Wis geen leerdata of onzekere toestelopdrachten om de melding weg te krijgen.

Alleen de vastlopende berekening is hersteld; echte opdrachtfouten, onzekere eerdere STARTs en fabrikantbescherming blijven hun beoordeling vragen. De opgeslagen hervatvoorkeur is geen algemene foutreset.

## Betekenis van de kleuren

| Tegel | Kleurbereik | Betekenis |
| --- | --- | --- |
| Zonnepanelen | Rood → oranje → geel → lichtgroen → groen | Van nul productie naar de ingestelde maximale omvormerproductie |
| Net: injectie | Groen | Stroom teruggeleverd aan het net |
| Net: rond nul | Lichtgroen | Nagenoeg geen netafname |
| Net: afname | Lichtgroen → geel → oranje → rood | Meer stroom uit het net, relatief aan de weergaveschaal |
| Onbekende of oude meting | Grijs | Geen betrouwbare actuele kleur beschikbaar |

De productieschaal gebruikt **maximaal AC-vermogen van de omvormer**, niet het wattpiekvermogen van de panelen en geen zonnevoorspelling. Zo toont dezelfde productie haar aandeel van de ingestelde omvormercapaciteit. De schaal voor netafname gebruikt een positieve ingestelde maximale netafname, anders de omvormergrens. Die referentie is alleen voor de kleur en is geen zekeringwaarde, comforttoestemming of nieuwe regelgrens.

Rood bij nul zonneproductie is geen storing; rood bij netafname bewijst evenmin overbelasting. De kleine legenda legt productie en netgebruik uit. Tekst, eenheden en afname/injectie blijven leidend en leesbaar, ook als kleuren minder goed zichtbaar zijn. De blauwe randen bij **Wat gebeurt er en waarom?** behouden hun eigen betekenis: doorlopend blauw is bevestigde activiteit, gestippeld blauw is AUTO beschikbaar of een werkelijk hoger gemeld tankdoel.

## Automatisch hervatten blijft behouden

**Na herstart automatisch hervatten** staat standaard Aan. Een gewone opgeslagen Pauze vraagt na herstart of integratieherlading automatisch Automatisch regelen via de bestaande toestel-, bron- en opdrachtcontroles. Met de voorkeur Uit blijft Pauze staan. Alleen bekijken, eerste installatie, interne fout-/verwijderpauzes, echte opdrachtfouten en noodzakelijke boilerbeoordeling blijven beschermd.

De voorkeur wijzigen verandert de huidige modus niet. Opnieuw Pauze kiezen annuleert een nu wachtende hervatting; een volgende herstart volgt opnieuw de bewaarde voorkeur. Andere beschikbare toestellen mogen na geldige globale controles hervatten wanneer een ontbrekend toestel afzonderlijk beschermd blijft. Een terugkerend toestel wordt opnieuw beoordeeld zonder een oude opdracht te herhalen. Er is geen handmatige bevestiging voor een gewone automatische herstartcontrole.

## Regeling en praktische controle

Extra warm water behoudt **3000 W** werkelijk bruikbaar overschot, haar stabiliteit, opdrachtrust en **3200 W** elektrische raming. Het mag veilige lager geplaatste eigen onderbreekbare gewone lasten laten wijken na bevestigde UIT en nieuwe actuele metingen; afwas, ruimteklimaat en Wallbox blijven beschermd. De bekende maandagsterilisatieplanning blijft informatie; echte gekoppelde fabrikant-, hygiëne-, handmatige en opdrachtbescherming blijft gelden.

Zonne-AUTO blijft vanaf **2500 W** echt restoverschot gedurende **60 seconden** met nieuwe P1/PV beschikbaar zonder temperatuurvraag of modelscore. Alleen bevestigde eigen zonne-AUTO houdt vanaf **2000 W** met eenmaal verse gedeelde warmtepompstroom, begrensd door echte PV. Ruimteklimaat en tapwater blijven één fysieke warmtepomp. Dashboard-UIT, externe rust, minimumtijden en elektrische-/fabrikantbescherming blijven gelden. Geen directe HEAT/COOL, Force DHW of Wallboxwrite.

Controleer na laden dat actuele productie en afname/injectie dezelfde waarden blijven tonen, dat onbekende/oude bronnen grijs zijn en dat de blauwe activiteitstatus afzonderlijk leesbaar blijft. De kleur kan door veranderde metingen wisselen zonder dat SolarPilot een toestel heeft bediend. De volledige actuele uitleg staat in `ACTUELE_WERKING.md` en op **SolarPilot → Uitleg**.

## Analyse, bewijsgrenzen en rollback

De volledige beschikbare zeven dagen blijven als lokale beheerderdownload **JSON.GZ** beschikbaar. Privacyfilters, versie per nieuw record, brondekking en begrensde bewaartermijnen blijven gelden. Deze werksessie voert geen live Home Assistant- of fysieke toestelactie uit. Softwaregate en aparte publicatie-/pakketcontrole staan in `TESTRESULTATEN_BETA59.md`; een release bewijst geen geladen backend, telefoonapp of fysieke warmtepomprespons.

Voor rollback herstel je de onveranderlijke **beta.58**-release of een passende volledige back-up, herstart Home Assistant en open de app/webpagina opnieuw. Er is geen nieuwe beta.59-opslagmigratie om terug te draaien; beta.58 blijft de hervatvoorkeur lezen, maar bevat de herstelde avondvoorraadfout nog. Wil je bij rollback bewust gepauzeerd blijven, zet **Na herstart automatisch hervatten Uit** en kies **Pauze** vóór de herstart. Laat beschermde cycli afwerken. Programmabestanden herstellen eerdere opslag niet vanzelf; gebruik voor exact herstel een passende volledige back-up. Geen fysieke proefopdracht om update of rollback af te dwingen.
