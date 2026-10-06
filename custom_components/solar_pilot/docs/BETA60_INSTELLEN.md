# SolarPilot 1.0.0-beta.60 — instellen en controleren

Beta.60 breidt **Overzicht → Wat gebeurt er en waarom?** uit met begrijpelijke uitklapbare uitleg bij elk toestel en elke regeling. Je ziet wat wel in orde is, welke voorwaarde nog ontbreekt, welke wachttijd loopt en het bekende vermogen. Gemeten vermogen en een schatting blijven afzonderlijk herkenbaar. Warm water en ruimteverwarming/koeling wisselen elkaar af op dezelfde warmtepomp; één gezamenlijke meting, niet apart opgeteld. Uitgeklapte uitleg blijft open bij automatisch verversen en herschikken. De pagina verklaart de bestaande regeling en geeft geen nieuwe toestemming om toestellen te bedienen.

Ook de native schakelaar voor lokaal leren gebruikt voortaan hetzelfde gedeelde leerpresentatieoverzicht en laat grote detailpakketten uit de herhaalde Recorder-kopie weg. De actuele volledige attributen, eigen opgeslagen leer-/modelgegevens en de volledige beschikbare analyse-export blijven behouden. De 16 KiB-limiet betreft één Home Assistant-historiekpakket, niet vrije schijfruimte. Er is geen data-/leerreset of gewijzigde bewaartermijn; deze update maakt geen onbeperkt archief en reconstrueert geen vroeger ontbrekende Recorder-records.

## Basis en upgrade

De absolute codebasis en rollbackbasis zijn gepubliceerde beta.59 op commit `32874118ba45a32d835d0a3189e75402ad62f8c3`, tree `21b3de88b4a3fe9b44d7cee183046d6076cbc8e0`, annotatietagobject `4e2e32d0c187e39908e1b5c3f7856996ca1a2312`. De onveranderlijke [beta.59-release](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.59), release-ID `404727324`, workflow `37469667437` en alle vier gepubliceerde assets zijn gecontroleerd. Beide ZIP-pakketten zijn inhoudelijk en met SHA-256 tegen de exacte gepubliceerde bron vergeleken. Lokaal behaalde beta.59 3569 tests in 44,55 s; CI behaalde 3569 tests in 52,59 s. Dit is basisbewijs, geen beta.60-test-/publicatiebewijs.

1. Maak een actuele volledige Home Assistant-back-up en bewaar beta.59 voor rollback.
2. Laat een lopende beschermde afwascyclus afwerken; onderbreek haar niet via de stekker of STOPRESET.
3. Installeer exact `1.0.0-beta.60` via HACS of vervang uitsluitend `custom_components/solar_pilot` met het lokale pakket. Behoud `userfiles` en Home Assistant-opslag.
4. Herstart Home Assistant volledig. Herlaad de webpagina; stop op Android de Home Assistant-app volledig en open haar opnieuw, of ververs de weergave op iOS.
5. Controleer backend én kaartversie. **SolarPilot → Uitleg** moet beta.60 en de actuele regel-hash tonen; een manifestnummer bewijst geen geladen kaartcode.
6. Open **Overzicht → Wat gebeurt er en waarom?** en klap de uitleg bij een toestel of regeling open. Hiervoor is geen extra instelling, dashboard-YAML of Lovelace-resource nodig.

Instellingen, geldige leerdata, bronkoppelingen, APP-aanvragen, prioriteiten, dashboardoverrides en veiligheidsvoorwaarden blijven behouden. Beta.60 voegt geen configuratie- of rangordemigratie toe. Bij een upgrade van vóór beta.57 blijft haar bestaande éénmalige EXTRA-prioriteitsmigratie gelden.

## Wat toont de uitgebreide uitleg?

| Onderdeel | Wat je op één plaats kunt bekijken |
| --- | --- |
| Gewone toestellen en afwas | Huidige toestand, beschikbare/benodigde stroom, startvoorwaarden, wachttijden en ontbrekende vrijgave |
| Warm water | Werkelijk toesteldoel naast voorstel, actuele zonne-/ruimte-/fabrikantvoorwaarden, stabiliteit en rust sinds de vorige opdracht |
| Ruimteklimaat | Programma en gebruikerskeuze per ruimte, lopende bevestiging of comfort-/zonnevraag en opdrachtstatus |
| Wallbox | Werkelijk uitgelezen laden/wachten en bekende reden; SolarPilot bedient de Wallbox niet |
| Batterij | Bekende activiteit, advies, opdrachtbevestiging of fout; een advies is geen daadwerkelijke uitvoering |
| Vermogen | Waar bekend de werkelijke meting; schattingen zijn herkenbaar, ontbrekende metingen blijven onbekend |

Een al vervulde voorwaarde krijgt een positieve uitleg. Een hogere voorsteltemperatuur is geen bewijs van versturen, bevestiging of opwarming. AUTO beschikbaar is evenmin fysiek verwarmen/koelen. De blauwe doorlopende/gestippelde rand houdt haar bestaande betekenis. Warm water en ruimteverwarming/koeling wisselen elkaar af op dezelfde warmtepomp; één gezamenlijke meting, niet apart opgeteld. Een exclusieve boilermeter wordt alleen als zodanig benoemd als de broninstelling dat daadwerkelijk aangeeft.

Open uitleg blijft open bij automatisch verversen en veranderde volgorde. De compacte hoofdregel blijft leesbaar; verdere technische gegevens zijn beschikbaar als je ze nodig hebt. Openen van de uitleg start geen toestel en slaat geen keuze op.

## Leren, Recorder en gegevensbehoud

De groottewaarschuwing bij de native lokaal-leren-schakelaar wordt gericht aangepakt: dezelfde leerpresentatie als de leersensor wordt gedeeld en zware details krijgen uitsluitend geen herhaalde Recorder-kopie. De schakelaar behoudt haar bestaande aan/uitwerking; de correctie schakelt lokaal leren niet uit.

Volledige live gegevens, eigen leer-/modelopslag en de volledige werkelijk beschikbare analyse-export blijven bestaan. Geen data- of leerreset, verkorte bewaring of reconstructie van oude ontbrekende Recorder-records. De bestaande gecomprimeerde zeven-dagenexport behoudt werkelijke dekking en privacyfilters; deze update maakt geen onbeperkt archief van alle ruwe meetpunten. Meer schijfruimte verandert de 16 KiB-limiet per Recorder-attribuutpakket niet.

Controleer na installeren of nieuwe grootte-/traagheidsmeldingen voor de leren-schakelaar terugkomen. Bewaar dan het tijdstip en de gemelde entiteit. Een eerdere traagheidswaarschuwing bewijst niet dat de fysieke besturing is uitgevallen; het herhaalde presentatie-opbouwwerk wordt gericht verminderd.

## Behouden regeling en herstel

**Na herstart automatisch hervatten** blijft standaard Aan. Een gewone opgeslagen Pauze hervat via de bestaande bron-/toestel-/opdrachtcontroles. Alleen bekijken, eerste installatie, interne fout-/verwijderpauzes en echte opdracht-/boilerbeoordeling blijven beschermd. Staat alleen een eerdere interne foutpauze na reparatie opgeslagen, kies één keer **Automatisch regelen**. Volg alleen een afzonderlijk gemelde beoordeling volgens de bestaande voorwaarden. Bij een nieuwe interne fout bewaar je tijdstip en SolarPilot-traceback uit HA Logboeken; geen grote export nodig voor een concrete uitzondering.

Extra warm water behoudt 3000 W werkelijk bruikbaar overschot, stabiliteit, opdrachtrust en 3200 W elektrische raming. Veilige lager geplaatste eigen onderbreekbare lasten mogen na bevestigde UIT en nieuwe metingen wijken; afwas, ruimteklimaat en Wallbox blijven beschermd. De bekende sterilisatieplanning is informatie; werkelijke fabrikant-/hygiëne-/handmatige bescherming blijft gelden.

Zonne-AUTO blijft beschikbaar vanaf 2500 W werkelijk restoverschot gedurende 60 seconden met nieuwe P1/PV. Alleen bevestigde eigen zonne-AUTO houdt vanaf 2000 W met eenmaal verse gedeelde warmtepompstroom, begrensd door echte PV. Dashboard-UIT, externe rust, minimumtijden en elektrische/fabrikantbescherming blijven gelden. Geen directe HEAT/COOL, Force DHW of Wallboxwrite.

PV/netkleuren, de avondvoorraadcrashreparatie, sensor-Recorderuitsluiting, presentatiecache, beschermde afwascycli en geauthenticeerde export blijven behouden. De enige volledige actuele regeling staat in `ACTUELE_WERKING.md` en op **SolarPilot → Uitleg**.

## Bewijsgrenzen en rollback

Softwaregate en de afzonderlijke publicatie-/pakketcontrole staan in `TESTRESULTATEN_BETA60.md`. Geen live Home Assistant- of fysieke toestelacceptatie in deze werksessie. Een release bewijst geen geladen telefoonapp, daadwerkelijke compressoractie of fysiek temperatuurverloop.

Voor rollback herstel je de onveranderlijke beta.59-release of een passende volledige back-up, herstart Home Assistant en open de app/webpagina opnieuw. Beta.59 behoudt de eerdere reparaties maar mist de uitgebreide beta.60-uitleg en leren-schakelaarcorrectie. Er is geen nieuwe beta.60-opslagmigratie. Wil je bewust gepauzeerd blijven, zet **Na herstart automatisch hervatten Uit** en kies **Pauze** vóór de herstart; laat beschermde cycli afwerken. Programmabestanden herstellen eerdere opslag niet vanzelf; gebruik voor exact herstel een passende volledige back-up. Geen fysieke proefopdracht om update of rollback af te dwingen.
