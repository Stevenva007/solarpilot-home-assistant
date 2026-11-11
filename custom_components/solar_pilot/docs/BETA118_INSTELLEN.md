# SolarPilot beta.118 — installatie en rollback

## Wat deze versie oplost

Een schermklok die enkele seconden achterloopt, kon een nieuwe SolarPilot-publicatie als toekomstig beoordelen. De SG-bediening wisselde dan tussen Automatisch en onbekend terwijl de backendkeuze en het gemelde fysieke contact gelijk bleven. De kaart mag dit verschil niet als een echte bedieningswisseling tonen.

Beta.118 stemt de weergavetijd af via een kleine geauthenticeerde, uitsluitend uitleesbare Home Assistant-aanvraag. De kaart laat tijd monotoon verstrijken, weigert een antwoord met meer dan vijf seconden retourtijd en gebruikt een bevestigde referentie hoogstens drie minuten. Vernieuwing is begrensd tot eenmaal per dertig seconden per kaart. Zonder bruikbare afstemming benoemt de kaart dat expliciet. Een andere gebruiker, verbinding of entry krijgt geen laat antwoord uit de vorige context.

De oorspronkelijke rapporttijden blijven gelijk. Oude, toekomstige, onbeschikbare en herstelde bronnen blijven onbruikbaar. De contactlease, handmatige eindtijd, backendregeling en alle SG-/Panasonic-/Wallbox-opdrachtgrenzen veranderen niet. De tijdsaanvraag pollt geen bronintegratie en bedient geen apparaat.

## Bijwerken

1. Maak een privé Home Assistant-back-up met SolarPilot-configuratie en -opslag.
2. Installeer na geslaagde publicatie **1.0.0-beta.118** via HACS.
3. Herstart Home Assistant volledig en herlaad de browser of app. Controleer dat zowel integratie als geladen kaart beta.118 tonen.
4. Behoud de bestaande configuratie en lokale SG-bevestigingen. Een nieuwe fysieke SG-test of nieuwe vrijgave is geen onderdeel van deze weergavecorrectie.
5. Controleer de keuze onder SG-bediening over meerdere normale publicaties. De fysieke contactstand staat afzonderlijk vermeld; Automatisch betekent niet dat het contact AAN moet zijn.

Zonder beschikbaar tijdsantwoord blijft de actuele SG-weergave onbekend en verschijnt uitleg over tijdsafstemming. Dit geeft geen toestemming om bron- of contactbeveiligingen uit te schakelen. Een systeemklok automatisch met een betrouwbare tijdbron synchroniseren blijft nuttig voor andere toepassingen.

## Rollback

Installeer beta.117 opnieuw via HACS, herstart Home Assistant en herlaad de browser of app. Instellingen, modellen en historie gebruiken hetzelfde opslagformaat. Een afwijkende schermklok kan met de oude kaart opnieuw de flikkering veroorzaken. Herstel voor een volledige rollback de passende privéback-up. De Aquarea v2-binaire pompstatus wordt ook door beta.117 ondersteund.

Zie [TESTRESULTATEN_BETA118.md](TESTRESULTATEN_BETA118.md) voor het softwarebewijs. Een softwaretest bewijst geen fysieke warmtepomp-/SG-proef.
