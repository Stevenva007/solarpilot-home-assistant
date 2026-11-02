# SolarPilot 1.0.0-beta.113 installeren

Werk na publicatie SolarPilot via HACS bij naar **1.0.0-beta.113**, herstart Home Assistant volledig en herlaad de app of browser. Controleer de backend- en kaartversie onder Instellingen & controle. Behoud de integratie, bestaande koppelingen, modellen en historie. Maak vooraf een volledige privéback-up inclusief SolarPilot-opslag en userfiles.

## Marstek Venus E 3.0 toevoegen als monitor

De nieuwe batterij wordt niet automatisch gevonden of aangesloten door de softwareupdate. De bestaande **Marstek-integratie in Home Assistant** blijft de bron van alle metingen. SolarPilot opent geen tweede UDP-, Modbus- of cloudverbinding en installeert die integratie niet.

1. Open SolarPilot-instellingen en kies onder **Batterijen** de Marstek Venus E 3.0-monitor.
2. Kies een herkenbare naam en de bestaande sensor voor het **getekende AC-vermogen van de batterij zelf**, in W of kW.
3. Kies bewust de tekenrichting en controleer die bij werkelijk laden en ontladen. Bevestig daarna de AC-meetdekking.
4. Selecteer eventueel de bestaande SoC-sensor in procent en, wanneer bekend, de fysieke fase. Onbekende SoC of fase blijft onbekend.
5. Sla de koppeling op en controleer of laden, ontladen en eventueel SoC overeenkomen met de Marstek-weergave.

Bij Marstek is **Vermogen netaansluiting (AC OnGrid)** de bedoelde batterij-AC-bron; **Totaal vermogen** van de CT is een woningnetmeting. Controleer de bronbetekenis. Een woning-P1/CT-meter, DC-batterijvermogen of absolute `batteryPower` zonder richting is geen geschikte AC-batterijvermogensbron. Ontbreekt een betrouwbare bron, laat de koppeling onbevestigd in plaats van nul of een richting te veronderstellen. SoC is optioneel; het ontbreken daarvan maakt een afzonderlijke geldige AC-vermogensmeting niet automatisch ongeldig.

Het profiel blijft **uitsluitend uitleesbaar**. Het krijgt geen laad-, ontlaad-, pauze-, reserve- of modusbediening, ook niet als algemene batterijbediening actief is. De meetbevestiging verleent geen bedieningstoestemming. Marstek blijft autonoom regelen. Er is geen SolarPilot-SoC-reserveprioriteit voor dit profiel die gewone toestellen tegenhoudt totdat de batterij is gevuld.

De profielcapaciteit van **5,12 kWh** is de nominale fabrikantwaarde. Zij is geen gegarandeerde bruikbare AC-energie of beschikbare reserve. De fabrikant vermeldt ontladingsdiepte en omzettingsrendement afzonderlijk; SolarPilot verandert deze grenzen niet.

## Wat gebeurt er met het zonneoverschot?

Actueel werkelijk ontladen batterijvermogen wordt eenmaal afgetrokken van het bruikbare zonneoverschot: opgeslagen energie telt niet als nieuwe zon. Laden is al in de P1-balans opgenomen en wordt niet opnieuw als extra overschot toegevoegd. Een onbekende of oude vermogensbron wordt geen gemeten nul. P1, PV, bronactualiteit, net-, fase- en kwartiergrenzen blijven leidend.

## Actualiteit van de Marstek-bron

SolarPilot leest voor de ondersteunde native bron de gekoppelde Home Assistant-entiteit, bestaande Marstek-coordinator, oorspronkelijke geslaagde ES-statusuitlezing en bijbehorende kwaliteit mee. Een al ontvangen antwoord van dezelfde batterij moet bovendien het gekozen AC-vermogensveld bevatten en met de gepubliceerde waarde overeenkomen. Een nieuw HA-publicatiemoment of gedeeltelijk antwoord zonder dit veld maakt een oude waarde niet actueel. Een nieuw geldig antwoord met dezelfde waarde kan ook stabiele 0 W vernieuwen. Er volgt geen extra RPC, poll of netwerkverbinding.

SolarPilot bewaart passend veldbewijs kort in het geheugen wanneer de bronintegratie haar kortere antwoordcache opruimt. De oorspronkelijke ontvangsttijd blijft gelden: uiterlijk na de ingestelde bronleeftijd, standaard 120 seconden, is nieuw veldbewijs nodig. Een gedeeltelijk antwoord verlengt die termijn niet. Expliciet falende bronstatus wordt meteen onbekend; bij een andere koppeling of coordinator vervalt het eerdere bewijs. SoC heeft een eigen controle en mag onbekend zijn terwijl AC-vermogen geldig blijft. Dit controleert daadwerkelijk ontvangen gegevens, zonder onafhankelijke fysieke meetgarantie.

## Gerichte waarschuwing na vermogensoverdracht

De waarschuwing benoemt de betrokken gewone toestel-/vermogensoverdracht en haar bevestigingscontrole. Een oude herstelwacht blijft afzonderlijk herkenbaar en wordt door de tekstcorrectie niet automatisch gewist. Nieuwe metingen en de werkelijke opdrachtterugmelding blijven nodig; een enkel gunstig meetpunt of een UIT-label is niet vanzelf bewijs dat de volledige overdracht is geslaagd. De melding is geen bewijs van een storing in de volledige installatie.

## SG blijft op vijftien minuten

De SG-correcties uit beta.112 blijven behouden: een lopend automatisch algemeen contact hoeft de startdrempel niet opnieuw te halen, de gewone zonne-/importbuffers zijn standaard vijftien minuten, de zachte importgrens blijft 600 W en de oorspronkelijke minimumduur twintig minuten. De korte lokaal gecontroleerde Shelly-toestemming blijft standaard 300 seconden met actuele vernieuwing om de 60 seconden. Harde grenzen en handmatige eindtijden blijven apart. Panasonic en Wallbox krijgen geen nieuwe opdracht.

## Controle en rollback

Controleer na de update de batterijmeting tijdens natuurlijk laden en ontladen en bekijk of de waarschuwing de juiste betrokken overdracht noemt. Deze release claimt geen fysieke test of reeds gemaakte lokale bronkoppeling. Bewaar bij een aanhoudende onverwachte melding de lokale analyse-export; plaats privégegevens niet op publieke GitHub.

Rollback naar beta.112 verwijdert de nieuwe Marstek-profielondersteuning en waarschuwingstekst. Verwijder daarom vóór rollback de uitsluitend uitleesbare Marstek-koppeling uit SolarPilot en controleer dat er geen generiek bedienbaar batterijprofiel is overgebleven. De native Marstek-integratie en autonome werking blijven bestaan. Beta.112 ondersteunt dezelfde vijftienminuten-SG-buffer; teruggaan naar beta.111 of ouder vraagt bovendien eerst een daar ondersteunde buffertijd, bijvoorbeeld 300 seconden. Wis de overige SolarPilot-configuratie en historie niet.

De softwarecontrole en publicatiestatus worden afzonderlijk vastgelegd in TESTRESULTATEN_BETA113.md. Er is geen fysieke batterij-, SG-, warmtepomp- of laadproef uitgevoerd.
