# SolarPilot 1.0.0-beta.48 — instellen en controleren

Beta.48 bouwt voort op de huidige beta.47-bron en herstelt de klimaatregeling. Een door de gebruiker OFF gezette zone blijft uit tot de gebruiker zelf AUTO kiest. Een onzekere of wachtende opdracht wordt niet opnieuw verstuurd. Thermische modelzekerheid wordt beoordeeld voor de verwarmings- of koelrespons die de actuele beslissing nodig heeft; ontbrekende koelervaring mag voldoende verwarmervaring niet als ontbrekend voorstellen.

## Bronbasis en gegevensbehoud

De absolute codebasis is beta.47 op commit `468291ad4a1f8050e71d2a842e434d93ecb8a104`. De onveranderlijke beta.47-release is de rollbackbasis. Geldige klimaatprofielen, samples, dag-/cyclusgegevens, andere leerdata, instellingen en toestelkoppelingen blijven behouden; deze update vereist geen algemene gegevensreset.

Er is één gerichte correctie van onbetrouwbaar fasebewijs: oudere gecontroleerde fasewaarnemingen bevatten geen bewijs dat andere gekoppelde meters tijdens die stap stabiel waren en worden daarom niet opnieuw gebruikt. Geldige passieve waarnemingen, nieuwe geïsoleerde fasewaarnemingen en handmatige fasekeuzes blijven behouden. Nieuwe natuurlijke geïsoleerde stappen mogen weer fasebewijs opbouwen; SolarPilot doet hiervoor geen schakelproeven. Ongeldige opgeslagen leerregels worden afzonderlijk overgeslagen zonder geldige andere regels te wissen.

## Upgrade

1. Maak een actuele volledige Home Assistant-back-up en bewaar de gecontroleerde beta.47-release.
2. Laat een beschermde afwas- of andere cyclus afwerken. Gebruik geen STOPRESET voor de update.
3. Installeer exact `1.0.0-beta.48` via HACS zodra die release beschikbaar is of vervang uitsluitend `custom_components/solar_pilot` met het lokale pakket. Behoud bestaande `userfiles` en Home Assistant-opslag.
4. Herstart Home Assistant volledig en controleer backendversie en vernieuwde kaart afzonderlijk.
5. Controleer dat een bewust OFF gezette klimaatzone OFF blijft. Alleen zelf AUTO kiezen geeft die zone weer vrij voor bestaande toegestane regeling.
6. Controleer de modeluitleg: de status, benodigde respons, meet-/leeraantallen en reden voor wachten horen zichtbaar te zijn. Geen ontbrekende koelmetingen als bewijs van ontbrekende verwarmervaring presenteren.

## Klimaatopdrachten en handmatige zones

Een handmatige OFF blijft beschermd totdat je zelf AUTO kiest. Deze bescherming staat los van de instelbare tijdelijke rust na een andere handmatige modewijziging. De per-zone bescherming, rusttijden en wachtende opdrachtinformatie blijven bewaard over herstart. Een vaste handmatige HEAT-/COOL-stand wordt eveneens niet overschreven.

Een nieuwe klimaatopdracht wacht op een passende nieuwe HA-standrapportage na minstens tien seconden. Een onmiddellijke lokale echo telt niet als bevestiging en er wordt geen oude pending opdracht herhaald. Bij herstart wordt uitsluitend opnieuw gelezen en moet de passende rapportage ook ná de herstartwachttijd beschikbaar zijn. Zonder passende bevestiging volgt na 180 seconden een zichtbare waarschuwing en blijft de feitelijke toestand behouden; geen automatische retry. Een daadwerkelijk OFF gebleven zone wordt beschermd.

Dit is bronbewijs uit Home Assistant en geen onafhankelijk fysieke ACK. Het overzicht toont de wachtende mode en herstel-/foutreden. Interne commandocontexten zijn geen gebruikersstatus.

Wanneer je zelf OFF kiest terwijl een SolarPilot-AUTO nog wacht, kan later een vertraagde AUTO-terugmelding aankomen. Die herstelt geen automatisch beheer, ook niet na langere tijd; alleen een expliciete nieuwe gebruikerskeuze voor AUTO in Home Assistant geeft die zone weer vrij. SolarPilot stuurt geen blinde corrigerende OFF. Controleer bij zo'n vertraagde melding de actuele native stand.

Een ontbrekende/onbekende actie wordt niet als idle aangeleerd en geeft geen nieuwe OFF-vrijgave. Een bewezen eigen SolarPilot-coast mag volgens bestaande comfortregels wel weer naar AUTO worden vrijgegeven; daarmee wordt ontbrekende actie niet als leerbewijs ingevuld.

## Modelzekerheid en bewijs

De coastbeoordeling vraagt passieve respons en zonnewinst wanneer gebruikt. Bij een voorspelde ondergrens zijn verwarmingsrespons en bestaande reactievertraging nodig; bij een bovengrens koelrespons en reactievertraging. Bij beide richtingen zijn beide responses nodig. Zonder voorspelde grensoverschrijding zet een niet gebruikte actieve respons de passieve beoordeling niet op nul.

Ontbrekende koelleerdata blijft eerlijk zichtbaar als niet geleerd, maar blokkeert niet alleen om die reden een voldoende geleerd verwarmingspad. Onvoldoende bewijs van een daadwerkelijk benodigde respons blijft de coastvrijgave blokkeren. De bestaande gedeelde reactievertraging wordt niet ten onrechte als apart bewezen verwarm-/koelvertraging voorgesteld.

Het overzicht toont de actuele relevante zekerheid, vereiste en nog onvoldoende onderdelen, status en werkelijk opgeslagen meet-/dag-/episodeaantallen. De oude complete confidence blijft aparte vergelijkingsinformatie. Geen comfortgrens of modeldrempel wordt verruimd om een ontbrekend onderdeel groen te laten lijken.

Handmatige OFF-zones vallen buiten de automatische coastplanning. Ontbrekend modelbewijs in zo'n beschermde zone blokkeert daarom niet op zichzelf een andere vrijgegeven AUTO-zone. Een concrete opdracht wordt vlak voor verzenden opnieuw tegen actuele zones en guards beoordeeld.

Een nieuwe coast vereist opeenvolgende actuele/toekomstige forecasturen met passende weer-/PV-tijdposities; oude uren of gaten gelden niet als volledig bewijs. Bij ontbrekende forecast mag alleen bewezen eigen coast veilig naar AUTO worden vrijgegeven, zonder gewone daglimiet/minimumvasthoudtijd af te wachten. Handmatige OFF, vaste HEAT/COOL en gebruikersrust blijven beschermd.

Coastfeedback begint en telt pas nadat alle betrokken zones hun nieuwe mode met de vereiste latere HA-terugmelding hebben bevestigd. Een mislukte/onbevestigde opdracht levert geen leerepisode op; zulke episodes worden na herstart niet gereconstrueerd. Wijzigingen van zonekoppelingen wachten op veilig afronden van eigen coast of pending opdrachten.

## Andere bron- en veiligheidscontrole

De update verwerpt restored, toekomstige en ongeldige operationele vermogens-, Wallbox- en boilerbronrapportages. Dit maakt een langdurig ongewijzigde maar geldige statische veiligheidswaarde niet vanzelf onbruikbaar. Native tankdoel, tankmeting en beschermingsstatus moeten echte bruikbare bronwaarden blijven; oud tankdoel is geen vrijgave voor een nieuwe opdracht.

Een onzekere eerdere AEG-START vereist een nieuwe betrouwbare lopende of voltooide fase-terugmelding van ná START. Een oude Washing/Finished-stand lost die onzekerheid niet op en er volgt nooit een tweede START. Een handmatige gewone toestelvraag kan een fout of interlock niet overrulen; bestaande minimumlooptijden en beschermde cycli blijven gelden.

Onbeschikbare, restored, toekomstige of meer dan 36 uur oude dynamische prijsbronnen vallen terug op het ingestelde vaste tarief. Ontbrekende of ongeldige rijen verschuiven de tijdposities niet; gaten worden niet met een andere tijdsprijs ingevuld.

## Behouden regels

- Panasonic kiest HEAT/COOL; SolarPilot stuurt uitsluitend toegestane AUTO/OFF-regeling en verandert geen thermostaatdoel of verwarmings-/koelrichting.
- Manual OFF blijft beschermd; een comfortwaarschuwing geeft geen recht om die zone automatisch in te schakelen.
- Een pending of onzekere opdracht wordt niet blind herhaald.
- De beta.47-regeling voor gewoon automatisch herstartherstel, persistent gebruikersintentie en beschermde AEG-/boilertoestanden blijft behouden.
- Normaal DHW-doel standaard 50 °C, bewaakte comfortgrens 46 °C, extra restoverschot maximaal 60 °C, autonome fabrikantsterilisatie en alle elektrische grenzen blijven gelden.
- Wallbox blijft read-only; extra 60 °C krijgt geen Wallboxkrediet.
- Geen algemene leerreset of fictieve metingen toevoegen om een modelstatus te verbeteren. Alleen ongeldige of aantoonbaar onbewezen opgeslagen leerregels worden gericht niet hergebruikt.

## Test- en installatiestatus

De definitieve softwaregate staat in `TESTRESULTATEN_BETA48.md`. Er is in deze werksessie geen live Home Assistant-toegang; beta.48-installatie, fysieke AUTO/OFF-overgangen en gemeten verwarm-/koelrespons zijn niet bevestigd.

## Rollback

Kies **Pauze**, laat beschermde cycli afwerken, herstel de onveranderlijke beta.47-release of een gecontroleerde volledige back-up en herstart Home Assistant. Controleer backend/kaart, zonebediening, actuele bronnen en beschermingen. Beta.47 bevat de huidige herstartherstelregels maar niet de klimaatcorrecties van beta.48; beoordeel handmatige OFF-zones vóór automatische regeling in die oudere versie.
