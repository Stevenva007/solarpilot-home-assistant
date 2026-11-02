# SolarPilot 1.0.0-beta.115 installeren

Werk na publicatie via HACS bij naar **1.0.0-beta.115**, herstart Home Assistant volledig en herlaad app of browser. Controleer de backend- en geladen kaartversie onder Instellingen & controle. Behoud integratie, modellen, koppelingen en historie. Maak vooraf een volledige privéback-up inclusief SolarPilot-opslag en userfiles.

## Bestaande Marstek-monitor aanpassen en bewaren

1. Kies bij een batterijbronmelding **Batterijbron controleren**, of open Batterijen in de SolarPilot-opties.
2. Kies **Marstek Venus E3 · monitor openen**. Bij één bestaande Marstek worden de opgeslagen velden geladen; bij meerdere kies je eerst het betreffende profiel. Dezelfde profielidentiteit blijft behouden.
3. Zoek de bedoelde sensor op naam of entity_id en selecteer haar uit de begrensde keuzelijst. Een zoekterm is geen opgeslagen sensorbinding. Gebruik de bestaande getekende batterij-AC-sensor. Bij de ondersteunde native Marstek-bron is dit **Vermogen netaansluiting (AC OnGrid)** met **Positief = ontladen naar huis**. CT **Totaal vermogen**, DC-batterijvermogen of een absolute waarde zijn hiervoor geen vervanging.
4. Controleer de werkelijke meetbetekenis en tekenrichting en bevestig daarna bewust de AC-meetdekking. SoC en de bekende fysieke fase zijn optioneel. De update zet een ontbrekende bevestiging niet aan en selecteert geen bron automatisch.
5. Kies **Verder**. Dit bereidt de wijziging voor en heeft nog niets opgeslagen. Controleer de laatste overzichtsstap, bevestig de beschreven wijzigingen en kies **Wijzigingen opslaan**.
6. Wacht op de geslaagde opgeslagenmelding en open dezelfde monitor opnieuw. De bewaarde naam, bronnen, tekenkeuze, bevestiging en fase horen terug te komen. Een netwerkfout is geen bewezen opslag; controleer dan de werkelijk opgeslagen waarden opnieuw.

Gebruik **Extra Marstek-monitor toevoegen** alleen voor een afzonderlijke extra batterij. Maak geen tweede profiel om een bestaande bronmelding te herstellen. Een actief profiel zonder AC-bevestiging of met een bekend verkeerde native meetsoort/tekenkeuze krijgt een veldfout. Je invoer blijft in de geopende flow beschikbaar om te verbeteren. Annuleren behoudt de bestaande configuratie; een niet afgeronde wizard is geen opgeslagen wijziging.

De globale batterijbronmelding gebruikt nu configuratie via **Batterijbron controleren**. **Controle afronden** is voor echte toestelfouten en bevestigt geen AC-meetdekking. Na het herstellen van één concrete oorzaak kan een andere bronoorzaak nog zichtbaar blijven. Een vinkje maakt een onbereikbare of oude bron niet actueel.

## Typen op een klein scherm

De sensorzoeker gebruikt een eigen begrensde lijst met ondoorzichtige achtergrond en scroll. De formulierinhoud volgt de beschikbare hoogte bij een mobiel toetsenbord. Lange entity_id's blijven binnen het formulier. Met pijltjes navigeer je door resultaten, Enter selecteert en Escape sluit de lijst. Deze handelingen slaan het formulier niet automatisch op. Bij wisselen van account of SolarPilot-integratie wordt het geopende concept gesloten; begin de gewenste configuratie dan opnieuw in de juiste context.

De softwarevalidatie gebruikt echte Chromium met gesimuleerde mobiele scherm- en toetsenbordhoogtes. Dit is geen fysieke Android- of WebViewproef. Sluit de app na de codeupdate volledig en open haar opnieuw om de nieuwe dialogcode te laden.

## Bestaande regelgrenzen

Marstek blijft uitsluitend monitoring via de bestaande Home Assistant-bronnen: geen laad-, ontlaad-, modus- of reserveopdracht en geen extra polling. Getekend AC-vermogen, oorspronkelijke rapporttijden, kwaliteit en afzonderlijke SoC behouden hun bestaande voorwaarden. Onbekend wordt geen nul. Basislastleren vraagt alle actieve afzonderlijk bevestigde passende AC-bronnen zonder onbekende overlap; het creëert geen actuele vrije zonnestroom.

SG behoudt zijn vijftienminuten-zonnebuffer en aparte vijftienminutenimportbuffer, oorspronkelijke minimumduur, korte lokale lease, vaste zonnevoorrang en onafhankelijke bron-/elektrische grenzen. Deze formulierupdate start of stopt geen fysiek toestel tijdens het opslaan.

## Rollback

Zet zo nodig beta.114 terug via HACS en herstart Home Assistant volledig. De opgeslagen monitoropties blijven leesbaar; beta.114 mist de herstelde beheerroute, mobiele kiezer en duidelijke laatste opslagstap. Gebruik daar **Batterij aanpassen** voor een bestaand profiel en rond de laatste bevestiging volledig af; de rechtstreekse Marstek-route kan weer een nieuw leeg profiel voorstellen. Maak geen duplicaten en wis geen configuratie of opslag.

Terug naar beta.113 mist bovendien de expliciete formuliervalidatie, bronredenen en basislast-fleetcorrectie uit beta.114. Beta.112 of ouder vraagt de profiel-/buffercompatibiliteitsstappen uit BETA113_INSTELLEN.md. Een gewone code-rollback is geen herstel van een oudere privéback-up.

Geen fysieke batterij-, SG-, warmtepomp- of laadproef is onderdeel van publicatie. Softwarebeschikbaarheid bewijst geen installatie op jouw Home Assistant. Zie [TESTRESULTATEN_BETA115.md](TESTRESULTATEN_BETA115.md).
