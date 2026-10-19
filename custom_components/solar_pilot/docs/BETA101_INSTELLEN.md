# SolarPilot beta.101 — watermonitor en gedeelde waterhistorie

Versie: **1.0.0-beta.101** · 19 oktober 2026 · Bouwbasis: gepubliceerde beta.100.

## Wat verandert

Het tabblad **Water** toont de gekozen watermeterstand, actueel debiet, geregistreerde liters van vandaag en afzonderlijk een bestaande lekindicatie en een vermoeden van langdurige stroming. **Watergeschiedenis** bewaart werkelijke meetpunten, tellerintervallen en beschikbare boiler-/afwascontext op dezelfde lokale tijdas. Bronhistorie opent de bijbehorende toegestane Home Assistant-bron.

De watermonitor staat standaard **uit**. Je kiest zelf bestaande bronnen; SolarPilot zoekt of koppelt geen meter automatisch. De functie leest uitsluitend. Zij sluit geen waterkraan, wijzigt geen meterstand of gatewayfirmware en geeft geen opdracht aan een toestel. SG, Panasonic, afwasbediening, Wallbox, batterijen en de gewone zonneoverschotregeling behouden hun bestaande voorwaarden. De lichtere SG-bediening uit beta.100 blijft behouden.

## Watermeter instellen

Open **Instellingen & controle → Watermeter**, of de instelknop onder **Water**. Kies ten minste één passende bestaande bron voordat je **Watermonitor inschakelen** aanzet. De drie rollen zijn afzonderlijk optioneel:

| Instelling | Standaard | Betekenis |
|---|---|---|
| Watermonitor inschakelen | Uit | Bewust inschakelen van de waterregistratie. |
| Cumulatieve watermeterstand | Geen bron | Bestaande `sensor` met een oplopende volume-/watermeterstand; geen debiet, dagtotaal of elektriciteitsmeter. |
| Actueel waterdebiet | Geen bron | Bestaande `sensor` voor volume per tijdseenheid. Een tellerdelta wordt niet als direct debiet gebruikt. |
| Bestaand waterleksignaal | Geen bron | Bestaande `binary_sensor` met apparaatklasse `moisture`. Het is de melding van die bron, geen zelfstandige lekvaststelling door SolarPilot. |
| Maximale ouderdom bronrapport | 300 s | Bruikbaar bereik 15–86400 s. Een ouder of onbruikbaar rapport blijft onbekend. |
| Drempel voor aanhoudend debiet | 0,1 L/min | Bruikbaar bereik 0,01–1000 L/min; gelijk aan de drempel telt mee. |
| Duur aanhoudend debiet | 60 minuten | Bruikbaar bereik 1–1440 minuten. Nieuwe passende debietrapporten moeten de opbouw ondersteunen. |
| Waterwaarschuwingen in Home Assistant | Aan | Alleen actief bij ingeschakelde watermonitor; eigen blijvende HA-meldingen, zonder mobiel meldingsdoel. |

De meterstand ondersteunt expliciet **L/l, m³/m3 en mL** en wordt in liters weergegeven. Debiet ondersteunt **L/min, l/min, L/h, L/s, m³/h, m3/h, m³/min, m³/s en mL/s** en wordt naar L/min omgerekend. De geselecteerde metadata moet bij de rol passen. Er wordt geen eenheid of schaal uit een naam geraden. Een werkelijke verse nul blijft nul; onbeschikbaar, ongeldig, hersteld, geschat of verlopen wordt geen nul.

Bewaar het formulier pas nadat de rollen juist zijn. Een gewiste optionele bron blijft gewist. Bij alleen een cumulatieve meterstand kan SolarPilot geregistreerde tellerintervallen tonen, maar geen actueel debiet of bewezen zestig minuten aanhoudende stroming afleiden. Een native lekindicatie kan ook zonder debietbron worden gebruikt.

## Waarschuwingen lezen

**Mogelijk lek gemeld** volgt een verse positieve indicatie van de gekozen lekbron. **Geen lek gemeld** volgt haar verse negatieve indicatie en bewijst niet dat de installatie lekvrij is. Ontbrekend of oud blijft onbekend.

**Langdurige stroming** is een afzonderlijk vermoeden: het gemelde debiet bleef bij opeenvolgende nieuwe oorspronkelijke rapporten op of boven de ingestelde drempel gedurende de gekozen duur. Normaal watergebruik kan dit ook veroorzaken. Debietbevestiging vraagt hoogstens vijf minuten tussen nieuwe rapporten, of de kortere ingestelde bronouderdom. Eén vastgehouden rapport, herhaald openen van het dashboard of alleen positieve tellerpulsen bouwt de duur niet op.

Een melding wordt per episode bijgehouden en bij een gewone herstart niet opnieuw verzonden. Oude, onbekende of onder hetzelfde rapporttijdstip gewijzigde gegevens mogen de waarschuwing niet wissen of opnieuw activeren. Een nog niet opgehelderde episode kan zichtbaar blijven wanneer actueel bewijs ontbreekt. Opruimen vraagt passende nieuwe negatieve/onderdrempelige rapporten; een vervangende bron heft de eerdere episode niet op. Bewust uitschakelen van de watermonitor of haar meldingen ruimt alleen de eigen HA-melding op.

## Liters en historiek begrijpen

**Meterstand** is de cumulatieve bronwaarde. **Geregistreerd vandaag** is uitsluitend de som van bruikbare, werkelijk geregistreerde tellerdelta's binnen die lokale kalenderdag. Dit is een gedeeltelijke registratie met meetdekking, geen automatisch volledig dagverbruik. Zonder bruikbare intervallen blijft het aantal liters onbekend. Debiet wordt niet geïntegreerd om ontbrekende liters te fabriceren.

Een tellerdaling begint een nieuwe uitgangsstand; SolarPilot verzint geen negatief verbruik of telleromloop. Een bronwissel of herstart geeft geen verschil tussen oude en nieuwe tellers. Een positief verschil over een meetonderbreking of lokale daggrens kan als niet aan een dag toegewezen interval blijven staan; de dagtotalen krijgen daarvan geen naar rato verdeelde liters. Lokale dagen volgen de HA-tijdzone, inclusief dagen van 23 of 25 uur.

De eigen historie bewaart maximaal **30 lokale kalenderdagen**, **8192 meetpunten**, **8192 tellerintervallen** en **512 gebeurtenissen**. Aantalsgrenzen kunnen oudere details eerder laten vervallen; dekking en verdringing blijven zichtbaar. Waardevariaties leveren hoogstens eenmaal per minuut een opnamepunt, belangrijke statusovergangen kunnen eerder worden vastgelegd en bij gelijkblijvende waarden volgt uiterlijk na vijf minuten een nieuw punt. De selectie toont het echte opgeslagen meetpunt met zijn oorspronkelijke bronrapporten. Meetgaten worden niet geïnterpoleerd en oude HA Recorder-gegevens worden niet aangevuld.

Boilertemperatuur en een beschikbare normale doelwaarde worden alleen met hun eigen geldige oorspronkelijke rapporten bij een watermeetpunt bewaard. Een daling van minstens 2 °C tussen passende punten van dezelfde contextbron over maximaal dertig minuten kan naast gedeelde waterwaarnemingen worden getoond. Dat bewijst geen warmwaterafname, oorzaak of aantal boilerliters. Water tijdens betrouwbaar gemeld afwasbedrijf blijft **huishoudelijk water tijdens die context**, geen afwasmachineverbruik. Ontbrekende of gewijzigde context blijft onbekend.

Bronlinks tonen de **huidige** geselecteerde HA-bron en haar eigen werkelijk bewaarde Recorder-historie. Dat is geen bewijs van een eerdere toestel-/bronbinding en schakelt geen registratie in. Gewone gebruikers hebben voor de eigen waterhistorie leesrechten nodig op alle huidige én bewaarde water-/contextbronnen; onbekende herkomst geeft geen extra toegang. De actuele broncatalogus filtert de huidige rollen afzonderlijk op leesrecht.

## Bijwerken en controleren

1. Bewaar een volledige privé Home Assistant-back-up, inclusief instellingen en eigen opslag.
2. Werk via HACS bij naar **beta.101** nadat de releasecontroles zijn geslaagd en de prerelease is gepubliceerd. Behoud dezelfde entry, instellingen, modellen, historie, opslag en userfiles.
3. Herstart Home Assistant volledig en herlaad de app/browser. Controleer backend- en kaartversie afzonderlijk op **1.0.0-beta.101**.
4. Laat Water uit als je deze functie niet wilt gebruiken. Voor inschakelen kies je bewust de bestaande rollen en controleer je eenheden, bronrapporttijden en een echte nul afzonderlijk.
5. Bekijk Watergeschiedenis na nieuwe bronrapporten. Direct na inschakelen of herstart is nog geen volledig dagverbruik of volledige duurbevestiging beschikbaar. Vergelijk bronhistorie met de oorspronkelijke watermeterbron.

HA-rapporttijd beschrijft de rapportage in Home Assistant en is geen onafhankelijk bewezen fysiek meettijdstip. Er is geen nieuwe dependency of verplichte waterhardware nodig. Deze softwarevalidatie bewijst geen uitgevoerde live-installatie, werkelijke lekkage, gegarandeerde lekdetectie of fysieke apparaatreactie. De bronuitleg staat in [Waterbronnen](WATER_BRONNEN_BETA101.md).

## Rollback

Schakel de watermonitor vooraf uit zodat haar eigen HA-waarschuwing kan worden opgeruimd. Herstel indien nodig de gepubliceerde **beta.100-code**, met behoud van entry, instellingen, modellen, historie, eigen opslag en userfiles. Herstart Home Assistant volledig en herlaad de app/browser. Verwijder of maak de entry niet opnieuw aan en draai geen twee runtimes tegelijk.

Beta.100 kent de nieuwe waterweergave en waterregistratie niet. Bewaar de afzonderlijke wateropslag en back-up voor een eventuele terugkeer naar beta.101; vul ontbrekende tijd niet achteraf in. De lichtere SG-bediening en de bestaande toestel-/warmtepomphistorie blijven op beta.100 beschikbaar. Geef een eigen SG-aanvraag waar betrouwbaar mogelijk vooraf veilig vrij en onderbreek geen beschermde cyclus.

[Actuele werking](ACTUELE_WERKING.md) · [Testverslag en publicatiestatus](TESTRESULTATEN_BETA101.md) · [Overdracht](../OVERDRACHT.md)
