# Beta.105 — onafhankelijke afwasmachinemeter

## Installatie

Maak eerst een volledige privéback-up van Home Assistant, inclusief de SolarPilot-instellingen en `.storage/solar_pilot.<entry_id>.consumer_history`.
Gebruik beta.105 pas als de gewone releasecontroles voor de exacte broncommit geslaagd zijn. Een lokale test-ZIP of open wijzigingsvoorstel is geen gepubliceerde HACS-release.

Na een gepubliceerde HACS-update: Home Assistant volledig herstarten en de app/browser herladen. Controleer dat de kaart 1.0.0-beta.105 toont. De bestaande integratie niet verwijderen of opnieuw toevoegen.

Open **SolarPilot → Toestellen → Toestellen beheren** en wijzig het bestaande AEG/Electrolux-afwasmachinetoestel. Kies in de koppelingen de eigen vermogenssensor (W/kW) en optioneel de bijbehorende cumulatieve energieteller (Wh/kWh, state_class total of total_increasing). Bewaar de bestaande AEG START-, status-, deur-, verbinding- en remote-koppelingen. Rond de volledige wizard af; de meetstekker wordt niet als tweede schakelbaar toestel toegevoegd. Bij een actieve beschermde cyclus kan een wijziging terecht worden uitgesteld.

## Voorlopige meetdrempels

- Activiteit: minimaal 10 W gedurende 60 seconden aan nieuwe geldige rapporten.
- Stille fase: maximaal 5 W. Pas na 900 seconden stopt de afgeleide activiteit; een betrouwbare native actieve/gepauzeerde status blijft leidend.
- Maximale rapportouderdom/onderlinge afstand: 120 seconden.

Dit zijn startwaarden, geen bewezen kalibratie voor een specifiek apparaat. Vergelijk ze met een volledige echte beurt. Een korte stroompiek is geen start, en een lange stille fase of deurverlichting kan elektrische activiteit anders laten afleiden dan de native programmafase. Verleng bronouderdom niet om ontbrekende rapporten te verbergen.

## Controle na koppelen

Controleer dat de kaart het werkelijk actuele metervermogen toont, ook als de cloudbediening niet bereikbaar is. Start voor de praktijkcontrole uitsluitend zelf een gewone beurt wanneer dat gewenst is. De nieuwe waargenomen sessie krijgt Extern gestart, of Begin onbekend wanneer de beginwaarneming ontbreekt; nooit een verzonnen SolarPilot-start. De nieuwe registratie vult het verleden niet aan.

Controleer na de beurt de tellerstand en geregistreerde deelenergie. Dag- en sessie-kWh zijn uitsluitend geldige opeenvolgende tellerstappen en blijven als onvolledig herkenbaar. Tellerresets, sprongen, herstart, middernacht en meetgaten worden niet ingevuld. Zonder tellerpaar blijft energie onbekend in plaats van nul.

De observator leest uitsluitend. Hij bevestigt geen START-opdracht, verbruikt geen startticket, geeft geen start-/stoprechten, onderbreekt geen programma en maakt geen volledige geleerde cyclus. Native cloudbediening kan dus terecht afzonderlijk onbeschikbaar blijven terwijl de meteractiviteit zichtbaar is. Andere apparaten houden hun eigen bestaande voorwaarden.

## Opslag en rollback

Bestaande sessies, bronrechten, instellingen en andere toestellen blijven behouden. Nieuwe meter-dagsommen worden aanvullend in de bestaande versie-1-historie opgeslagen, begrensd tot dertig lokale dagen per meterbinding. Onleesbare bestaande opslag wordt niet overschreven. Herstart herstelt dagsommen, nooit een activiteitsduur of tellerbaseline.

Terug naar beta.104 stopt de nieuwe meterwaarneming. Een oudere versie kent de extra meterhistoriek niet en kan die bij een volgende opslag verliezen. Bewaar daarom de volledige privéback-up en de nieuwe historie vóór rollback. Herstel niet blind oude fysieke opdrachtleases. De update verandert geen Panasonic-, SG-, Wallbox- of fysieke beveiligingsrechten.
