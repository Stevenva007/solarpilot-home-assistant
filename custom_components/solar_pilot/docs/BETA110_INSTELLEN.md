# SolarPilot 1.0.0-beta.110 installeren

Werk SolarPilot via HACS bij naar **1.0.0-beta.110**, herstart Home Assistant volledig en herlaad de app of browser. Maak vooraf een volledige privéback-up, inclusief SolarPilot-opslag en userfiles. Verwijder de integratie niet.

Deze versie verdeelt het echte huidige overschot zonder toekomstige toestelpieken apart te houden. Het huidige afwas-, thermostaat- en overige huisverbruik zit al in P1; een nominale piek of wachtend plan wordt niet nogmaals van de zonnepot of actuele elektrische ruimte afgetrokken. De ingestelde vaste huisbuffer, filtering, batterijcorrectie, startmarges en echte net-, fase- en kwartiercontroles blijven gelden. Lopende beschermde programma’s worden niet onderbroken.

## Warmtepomp en SG

**Geraamd totaalvermogen bij SG** is standaard **3000 W**. Het bestaande ingestelde getal blijft behouden, maar de betekenis is vanaf deze versie bewust het geraamde totaalvermogen van de warmtepomp met SG. Voor de elektrische toename telt alleen `max(0, totaalraming − compleet actueel warmtepompvermogen)`. Bijvoorbeeld: totaalraming 3000 W en een complete verse meting van 800 W vragen nog 2200 W extra ruimte. Bij een ontbrekende, oude, onvolledige of overlappende meting wordt de volle totaalraming getoetst. De raming is geen gegarandeerd fysiek maximum. De afzonderlijke ingestelde SG-startdrempel blijft behouden.

Een wachtend toestelverzoek houdt geen vermogen vooruit vast. Een werkelijk startklare passende hogere aanvraag krijgt de eerstvolgende opdracht volgens de centrale volgorde. Daarna blijven bevestiging, stabilisatietijd en een nieuwe netmeting nodig voordat een andere start wordt verstuurd.

Staat SG vóór de Wallbox, dan kan SG betrouwbaar bevestigd autonoom zonnelaadvermogen overnemen terwijl de Wallbox zelfstandig terugregelt. De afzonderlijke reactie-episode duurt standaard vier minuten, begrensd door de bestaande `handover_s`. Alleen de softwarematige totale netgrens krijgt tijdelijk de bewezen beperkte uitzondering. De eerste bijdrage is het episodeplafond; oorspronkelijke begin- en eindtijd blijven na herstart behouden. Nieuw herstel vereist lage ruwe P1, bevestigingstijd en minstens twee nieuwe rapporten. De gewone wolkenbuffer van standaard 600 W gedurende vijf minuten loopt parallel op ruwe P1. Actuele fase-, kwartier-, batterij-, bron-, koel-, contact- en sessievoorwaarden blijven onafhankelijk.

De korte lokale eigen SG-lease blijft apart, standaard 300 seconden. Vier minuten is een venster voor actieve Home Assistant-software; bij HA-uitval garandeert het geen fysieke UIT precies na 240 seconden. De Wallbox krijgt geen laadcommando en Panasonic krijgt geen gewijzigde temperatuur-, programma- of heaterinstelling.

## Firmwarewijziging zonder nieuwe blokkade

Een firmwareversiewijziging alleen is **informatief**: SG blijft automatisch bruikbaar en er is geen nieuwe handmatige herbevestiging nodig. SolarPilot controleert dezelfde fysieke Shelly en uitgang opnieuw op actuele identiteit, ondersteunde configuratie en beschikbaar lokaal timerbewijs. Geldige bestaande ingebruiknamebevestigingen blijven behouden.

Een oude `firmware_changed`-blokkade kan bij een verse geldige uitlezing en passend bewaard bewijs van dezelfde fysieke uitgang automatisch herstellen. Ontbrekende of afwijkende hardwaregegevens worden niet ingevuld. Een werkelijk ander toestel, andere fysieke koppeling of onbruikbare configuratie of timer houdt zijn eigen actuele controlevoorwaarden; een firmwareversie alleen veroorzaakt die blokkade niet.

Bij een bewezen firmware-update met Shelly-herstart naar UIT tijdens een bestaande eigen SG-toestemming ontstaat geen blijvende handmatige-UIT-pauze. Passend oorspronkelijk sessiebewijs, dezelfde hardware/binding, actuele geldige configuratie en tijd-/uptimebewijs van de herstart zijn vereist. Daarna volgt de gewone actuele zonnebeoordeling met startstabiliteit; geen blinde AAN-herhaling. De oorspronkelijke sessiegrens en eventuele tijdelijke handmatige eindtijd blijven behouden. Ontbreekt het bewijs, dan blijft een werkelijke handmatige UIT beschermd.

Details en nieuwe exports bewaren de eerste beschikbare vergelijking, haar detectietijd, gewijzigde veldnamen en beschikbare oude/nieuwe firmwareversie, ook na herstart. Oudere ontbrekende vergelijkingsgegevens blijven onbekend. Er wordt geen geforceerde fysieke timerproef of SG-schakeling uitgevoerd om alleen een firmwaremelding te verwerken.

Controleer na volledig opstarten backend- en kaartversie, de centrale volgorde, de SG-totaalraming en de concrete SG-wachtreden. De recordercorrectie uit beta.109 blijft behouden. Een normale update bewaart configuratie, modellen, aanvragen en historie. Softwarepublicatie is geen fysieke installatieproef.

## Rollback

Installeer indien nodig **beta.109** via HACS en herstart volledig, met behoud van configuratie en privégegevens. Geef een eigen SG-aanvraag waar betrouwbaar mogelijk eerst veilig vrij. Beta.109 mist de nieuwe verdeling op actuele lasten, totaalvermogensberekening, begrensde Wallbox-reactietijd en uitgebreidere wijzigingsdiagnose. De oudere versie interpreteert `expected_power_w` weer als extra vraag en kan toekomstige afwaspieken reserveren. Controleer daarom de raming en concrete wachtreden na rollback. Gebruik geen twee runtimes tegelijk.

[Actuele werking](ACTUELE_WERKING.md) · [Testresultaten](TESTRESULTATEN_BETA110.md)
