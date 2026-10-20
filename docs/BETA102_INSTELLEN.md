# SolarPilot beta.102 — analysecorrecties en waterbronactualiteit

Versie: **1.0.0-beta.102** · 20 oktober 2026

Bouwbasis: gepubliceerde beta.101 `08d8c1f7446c78cc38bbb83f635491f429d1cdf2`, tree `c2e12dd9aaee2237370027df87b90c3759b98df5`. Deze update verwerkt drie afgebakende analysecorrecties en verduidelijkt de actualiteit van de optionele waterdetectoren. Bestaande instellingen, entiteitsidentiteiten, modellen, historie, opslag en userfiles blijven behouden.

## Wat verandert

- **PV-uitleg:** de planner gebruikt voor zijn PV-waarschuwing dezelfde daglicht-MAE als Leren & vragen: minstens twaalf daglichtvergelijkingen en strikt meer dan 700 W. Nachtelijke nulmetingen verbergen geen afwijking overdag. Bij ontbrekend of onvoldoende daglichtbewijs blijft de beoordeling onbekend. De gemengde MAE, daglicht-MAE en kwaliteitsscore blijven afzonderlijk bestaan; geen factor, PV-reserve of plannerkeuze verandert.
- **Warmtepompleren:** bij het bekende operation_status-contract wordt ingeschakeld zijn niet als bewezen actuele taak voor het leermodel gebruikt. Alleen passende oorspronkelijke bron- en meterinformatie kan de bestaande afleiding ondersteunen; die krijgt hoogstens afgeleid bewijs zonder nieuwe leertoestemming. Een opgeslagen schermlabel wordt niet als bronbewijs vertrouwd. Pomp UIT of 0 W alleen bewijst geen normale huishoudlast. Oudere onafhankelijke native contracten behouden hun betekenis.
- **Watervergelijking:** een daling vanaf 2 °C kan worden herkend over meerdere kleine stappen binnen maximaal dertig minuten. De hoogste geldige eerdere temperatuur vormt de referentie; gebruikte vensters en liters overlappen niet. Alleen volledig passende oorspronkelijke tellerintervallen worden vergeleken. Dit blijft samenloop van gedeeld huishoudelijk water en boilercontext, geen warmwaterliters of toestelverbruik.
- **Waterbronactualiteit:** debietbewaking en de eigen lekmelding van de meter tonen afzonderlijk of de bewust gekozen bron actuele bruikbare rapporten levert. Niet gekoppeld, onvolledig en niet beschikbaar zijn herkenbaar. Een verse totaalteller maakt de andere kanalen niet actueel. Actuele bronnen betekenen geen voltooide zestig minuten of bewezen lekvrijheid; een eerdere onopgeloste waarschuwing houdt voorrang.

Nieuwe watermeetgaten bewaren waar beschikbaar hun bronrol: volume, debiet of boilertemperatuur. Een uitsluitend nieuw debietgat blokkeert geen onafhankelijk geldig teller-/boilervenster. Oude generieke gaten, ontbrekende of ongeldige rollen, echte teller-/temperatuurgaten, herstart, reset en bronwissel blijven conservatieve grenzen. Historische ontbrekende herkomst wordt niet aangevuld.

De waterexport bevat ook de effectieve waterinstellingen, module-inschakeling en afzonderlijke bronkwaliteitsdiagnose. De vertrouwde implementatiecatalogus herkent alleen de drie generieke voorstellen op exacte inhoud én werkelijk geladen release; een importclaim bewijst geen geïnstalleerde correctie.

## Bijwerken zonder gegevensverlies

1. Maak een **volledige privé Home Assistant-back-up**, inclusief configuratie-entry, instellingen, eigen opslag, modellen, PV-factoren, tickets, geschiedenis en userfiles.
2. Geef een eigen SG-aanvraag vrij vóór codevervanging. Onderbreek geen beschermde afwas- of andere toestelcyclus.
3. Werk via HACS bij naar exact **beta.102**, zodra de geslaagde release is gepubliceerd. Behoud dezelfde integratie-entry. Bij lokale installatie vervang je uitsluitend `custom_components/solar_pilot`, met behoud van `userfiles` en bestaande opslag.
4. Herstart Home Assistant **volledig** en herlaad de app/browser volledig. Controleer backend- en kaartversie apart.
5. Controleer actuele PV-uitleg, warmtepompbroninformatie en, indien Water is ingeschakeld, de twee afzonderlijke detectorbronnen. Een ontbrekende of oude bron blijft onbekend; een herstart levert geen nieuwe meetdekking.

Er is geen reset, nieuwe verplichte entiteit, hernieuwde SG-ingebruikname of handmatige dependency-installatie nodig. De optionele watermonitor blijft afhankelijk van bewust gekozen bestaande bronnen. Deze update verandert geen SG-timer, minimumduur, elektrische grens, Panasonic-bediening, afwasdeadline of plannerbeleid en bedient geen waterkraan.

## Oude MQTT-rapporten controleren

Bij een oude debiet- of lekmelding controleer je de werkelijke publicatie, beschikbaarheid en configuratie van die afzonderlijke bron. Identieke MQTT-waarden kunnen zonder `force_update` in Home Assistant een oude `last_reported` houden. Een passende broninstelling kan nieuwe werkelijk ontvangen berichten herkenbaar maken; dat bewijst geen fysiek meettijdstip of lekvrijheid. SolarPilot wijzigt MQTT, `force_update`, bronkoppelingen of de ouderdomsgrens niet automatisch. Verleng de grens niet om ontbrekend bewijs als actueel te laten gelden.

## Behoud en rollback naar beta.101

Beta.101 kan de versie-1-wateropslag lezen en behandelt de meetgaten conservatief. De oudere code **laat de nieuwe optionele `source_role` bij een volgende opslag weg**. Bewaar daarom de volledige privéback-up om die aanvullende herkomst bij terugkeer naar beta.102 te behouden. Beloof geen behoud van deze extra rolmetadata na terugschrijven door beta.101.

Ruwe opnamepunten, tellerintervallen, dagsommen en bestaande modellen blijven onder hun eigen bewaartermijn bestaan. De oudere PV-samenvatting en warmtepompleerclassificatie keren terug, evenals de watervergelijking die alleen een voldoende grote opeenvolgende temperatuursprong herkent. Verwijder of hermaak de entry niet, reset geen opslag en laat geen twee runtimes tegelijk werken. Herstart na terugzetten Home Assistant volledig en herlaad de app/browser.

[Actuele werking](ACTUELE_WERKING.md) · [Testresultaten en publicatiestatus](TESTRESULTATEN_BETA102.md) · [Bestaande waterbronnen](WATER_BRONNEN_BETA101.md)
