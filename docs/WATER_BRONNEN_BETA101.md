# Officiële waterbronnen voor beta.101

Dit generieke brononderzoek is uitgevoerd op **19 oktober 2026**. Het beschrijft openbare leveranciers- en Home Assistant-documentatie, geen individuele installatie, privé-entiteit of firmware-updateopdracht.

## Meterstand, debiet en lekindicatie

De officiële [Smart Gateways-supportpagina](https://smartgateways.nl/support/) verwijst voor de Watermeter Gateway naar de [Home Assistant-handleiding van 8 juli 2026](https://haprofs.com/wonitor-water-usage-in-home-assistant/). Deze kiest **Usage Total** als waterbron en **Water Flow** als debietbron. De bijbehorende [MQTT-discoveryafbeelding](https://haprofs.com/wp-content/uploads/2026/07/Smart-Gateways-Water-Meter-Gateway-Home-Assistant-MQTT-Autodiscovery.png) toont de cumulatieve meterstand in **L**, debiet in **L/min** en een binaire **Leak Detect**-indicatie.

Die labels bevestigen de rollen en getoonde eenheden, niet het exacte MQTT-topic of de firmware-discoverypayload. SolarPilot gebruikt expliciet gekozen bestaande HA-bronnen. Het leidt geen bron-ID, apparaatidentiteit of topic af uit een productnaam of openbaar voorbeeld. Totale meterstand is geen dagverbruik; debiet is geen tellerstand of energiebron.

De oudere [ontwikkelaarsbeschrijving van lekdetectie](https://haprofs.com/en-watermeter-gateway-for-home-assistant-domoticz-homey-mqtt/) beschrijft `leak_detect` als een MQTT-/REST-indicatie die bij afwijkend watergebruik van `false` naar `true` kan gaan. De geraadpleegde primaire bronnen publiceren geen numerieke drempel of vast vrijgave-/resetcriterium. Positief betekent daarom **mogelijk lek gemeld**; negatief betekent **geen lek gemeld**, niet bewezen lekvrij. Een ontbrekende, onbeschikbare of oude indicatie is geen negatieve melding.

## Publicatie, correcties en firmware

De officiële [watermeterhandleiding EN-v9](https://smartgateways.nl/wp-content/uploads/2024/04/Manual-SmartGateways.nl-Water-Meter-Gateway-EN-v9.pdf), pagina 1, noemt standaard iedere **10 seconden** een MQTT-publicatie. `INTERVAL` kan dit aantal seconden wijzigen. De meterstand kan handmatig worden aangepast; ingevoerde meterwaarden zijn in liters. Een nominale publicatiecadans bewijst niet de oorspronkelijke fysieke meettijd of de actuele apparaatinstelling.

De specifieke [watermeter-firmwarechangelog](https://smartgateways.nl/en/firmware-changelog-water-meter-gateway/) vermeldt als nieuwste openbare vermelding **2026071501**: een MQTT-autodiscoverycorrectie. **2026070601** herstelt de backup van waarden iedere vier uur; **2026062501** introduceert MQTT-autodiscovery. Dit bewijst niet welke firmware lokaal is geïnstalleerd of welke update een individueel apparaat aanbiedt. SolarPilot installeert geen gatewayfirmware en wijzigt geen meterstand, pulsinstelling of MQTT-configuratie.

Een tellerdaling kan samenhangen met een correctie, reset of herstel. De bronnen publiceren geen bruikbare telleromloopmodulus. Een daling mag daarom niet als negatief verbruik of een verzonnen telleromloop worden doorgerekend. Onbekende tussenliggende tijd of een gewijzigde koppeling krijgt geen achteraf verdeelde liters of gefingeerde beginstand.

## Tijden en onbekende gegevens

De officiële [HA MQTT-sensordocumentatie](https://www.home-assistant.io/integrations/sensor.mqtt/) beschrijft dat `expire_after` standaard nul is: de waarde verloopt dan niet automatisch. Een retained MQTT-bericht kan bij herstart of opnieuw verbinden een oudere waarde opnieuw aanbieden. De [MQTT-binaire-sensordocumentatie](https://www.home-assistant.io/integrations/binary_sensor.mqtt/) beschrijft `on`, `off` en `unknown`; beschikbaarheid hangt af van ingestelde availabilityberichten. Zonder availabilitytopic geldt de bron standaard als beschikbaar.

Een oorspronkelijke HA-rapporttijd beschrijft wanneer HA de waarde rapporteerde. Zonder bewezen bronklok is dit geen onafhankelijk vastgestelde fysieke meettijd. De geraadpleegde leveranciersbronnen publiceren geen volledig contract voor retained/QoS, oorspronkelijke tijdstempels, lekvrijgave of telleromloop. Ontbrekende, ongeldige, herstelde en verlopen gegevens blijven daarom afzonderlijk van een werkelijk gemeten nul. Een cumulatief verschil over een geldig waargenomen interval geeft geen bewezen volledig dagtotaal of dekking in ontbrekende tijd.

## Uitsluitend uitlezen en bronrechten

Watermonitoring geeft geen opdracht aan een klep, pomp of ander toestel en verleent geen extra SG-/Panasonic-recht. Bestaande HA-historie heeft haar eigen recorderdekking en bewaartermijn; een bronlink schakelt geen registratie in. De huidige broncatalogus bevat alleen gekozen waterrollen met HA-leesrechten. Waterhistorie controleert voor gewone gebruikers de volledige huidige én bewaarde historische water-/contextbronnen; onvolledige herkomst wordt niet tot toestemming gemaakt. Publieke documentatie en code bevatten geen bronidentiteiten uit een privé-installatie.
