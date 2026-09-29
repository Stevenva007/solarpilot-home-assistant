# Beta.29 — AEG-afwasmachine en analyse-export

Deze cumulatieve versie voegt de twee ontbrekende onderdelen toe aan beta.28.
Alle eerdere warmwater-, Wallbox-, energie-, historie- en UI-functies blijven aanwezig.
Er wordt niets naar GitHub of jouw Home Assistant gepubliceerd door dit pakket.

## 1. AEG/Electrolux automatisch starten

### Wat het programma doet

Je laadt de afwasmachine, kiest het programma op de machine of in de fabrikantapp
én geeft per afwasbeurt één keer **Eén beurt klaarzetten** in SolarPilot. SolarPilot
kiest daarna het startmoment op basis van de actuele zonne- en planningsvoorwaarden.
Alleen **Zonnestroom + Auto + klaargezet + geldige bronnen** kan een nieuwe START geven.

De toestemming geldt standaard 24 uur en voor het gekozen programma. Een geopende
deur of gewijzigde programmakeuze trekt haar in. Na starten is ze verbruikt;
na afloop start dus niet vanzelf nog een lege afwasbeurt.

Een gestarte cyclus is niet onderbreekbaar vanuit SolarPilot. Minder zon, de Pauze-knop,
uitsluiting of Wallbox-voorrang geeft **geen** PAUSE, RESUME, STOPRESET of stekkeropdracht.
De cyclus kan daardoor later netstroom gebruiken. SolarPilot is geen lekbeveiliging en
bewijst niet dat een onbewaakte afwasbeurt voor jouw woning geschikt is.

### Eerst benodigde bronnen controleren

De bestaande AEG/Electrolux-integratie moet zelf aantoonbaar betrouwbaar zijn.
Een opgeslagen knop of oud online rapport bewijst geen startmogelijkheid.

Koppel de actuele bronnen van **hetzelfde geregistreerde afwasmachine-apparaat**:

| Bron | Gebruik |
|---|---|
| Native START-knop | Enige fysieke opdracht van deze adapter |
| Cyclus-/programmastatus | Gereed vóór starten, bezig en echt voltooid onderscheiden |
| Connectivity state | Actuele online-status |
| Remote control | Expliciete toestemming voor START op afstand |
| Door state | Gesloten deur vóór starten |
| Gekozen programma | Alleen uitlezen; bindt toestemming en leerprofiel |
| Optioneel alarm | Bij koppeling alleen starten met expliciet vrije, actuele status |
| Optionele native startvertraging | Bij koppeling alleen starten als die actueel nul is |
| Optionele W/kW-meter | Exclusieve Shelly/toestelmeter, nooit een relaisactuator |

**Selecteer nooit een knop op basis van alleen een suffix zoals `_3` of `_7`.**
Oude herstelde knoppen zijn geblokkeerd. Een actuele, nog nooit bediende START-knop
kan `unknown` tonen; live online/remote/deur/programmastatus moeten desondanks kloppen.

De ruwe gereed/bezig/voltooid- en remote-toestanden verschillen per integratie/apparaat.
De wizard toont voorlopige voorbeeldwoorden, geen geverifieerde waarden voor jouw
machine. Controleer ze via Home Assistant → Ontwikkelaarstools → Toestanden, terwijl
je de machine bedient. `Not Safety Relevant Enabled` wordt **niet** standaard
geaccepteerd als startrecht. Maak een onduidelijke waarde niet 'geldig' enkel om
SolarPilot te laten starten.

Zonder een aantoonbare gereedmelding en remote-starttoestemming kan de adapter wel
voorbereid worden, maar mag hij niet automatisch starten. Gebruik dan voorlopig de
fabrikantbediening; een actuele analyse-export helpt de ontbrekende bron te onderzoeken.

### Instellen

1. Maak een HA-back-up. Werk het cumulatieve pakket bij via de bestaande Git/HACS-route.
2. Zet SolarPilot op Pauze en wacht tot eigen lasten volgens hun beschermtijden zijn
   vrijgegeven. Onderbreek een lopend beschermd programma niet om sneller te configureren.
3. Open **Configureren met uitleg ? → Verbruikers & prioriteiten → Toestel toevoegen**.
4. Kies **AEG/Electrolux afwasmachine — alleen starten** als bedieningstype.
5. Selecteer de zes verplichte bronnen en eventueel alarm/startvertraging/vermogensmeter.
6. Controleer de ruwe statuswoorden en bevestig de koppelingen alleen na echte controle.
7. Kies in Gedrag & bescherming een conservatieve vermogensschatting. De voorgestelde
   **2000 W is een voorlopige planningswaarde, geen gecontroleerde AEG-specificatie**.
   Gebruik het typeplaatje/handleiding of later betrouwbare piekmetingen voor jouw keuze.
   Een gemiddelde van 1335 W of 1171 W uit een geschat faseprofiel is geen veilige piekgrens.
8. Laat voor een eerste eenvoudige proef startvertraging op **300 s** staan en de
   terugmelding op **300 s**, mits dit aansluit op werkelijke rapportage. Er is geen
   verplichte Shelly-meter om een native start mogelijk te maken.
9. Voor een plan over toekomstige blokken: geef onder Planning & energie een bruikbare
   cyclusduur en energieraming voor het gekozen programma op en schakel forecast-uitstel
   bewust in. Zonder betrouwbaar duurprofiel kan de planner niet eerlijk beloven dat
   een hele cyclus in het zonnige venster past. Voor de eerste realtime proef kan
   forecast-uitstel uit blijven. Geef geen fictief dagdoel op om een blokkering te omzeilen.
10. Opslaan laat een nieuw toestel **Uitgesloten**. Zet het pas na broncontrole op Auto,
    laad de machine, kies het programma, activeer de door de fabrikant vereiste remote
    start, sluit de deur en bevestig **Eén beurt klaarzetten**.
11. SolarPilot start niet meteen door het klaarzetten alleen. Bekijk de regelreden.
    Na voldoende stabiele voorwaarden volgt één native START. Alleen een **nieuwer
    echt bezigrapport** bevestigt die opdracht. Bij onbekende uitkomst volgt geen blinde
    herhaling, ook niet na een herstart.

Met **Klaarzetten annuleren** trek je alleen de toekomstige toestemming in. Gebruik de
fabrikantbediening voor het stoppen of annuleren van een werkelijk lopend programma.
Droogfase, een pauze of AirDry met open deur blijven onderdeel van de bestaande cyclus.

### Shelly-meter en het geschatte faseprofiel

Koppel later alleen de exclusieve vermogenssensor in W/kW. De plug moet qua belasting
bij de machine passen; het relais blijft buiten SolarPilot-aansturing.

SolarPilot leert met die meting per programma de werkelijk waargenomen fasen,
gemiddeld vermogen, piekvermogen, kWh en duur. Een volledig waargenomen start-tot-
voltooid-cyclus met minimaal 95% meetdekking en zonder detecteerbare hiaten is nodig
voor een betrouwbaar opgeslagen profiel. Maximaal twaalf recente gemeten profielen
worden bewaard. Onderbroken of half gemeten cycli worden niet als compleet geleerd.

**Onbemeten spoelen/drogen is onbekend, niet nul watt.** Het eerder getoonde geschatte
profiel wordt niet automatisch als echte meting geïmporteerd. Met alleen een algemene
woningmeter valt de afwasmachine niet betrouwbaar van andere toestellen te scheiden.
Voor het gebruik van nieuwe complete profielen in de bestaande cyclusplanner zet je
ook de expliciete optie **cyclusleren met exclusieve vermogensmeter** aan.

De verbruikerskaart toont programma, fase, klaarzettoestemming, gemeten of geschat
vermogen en het laatste complete faseprofiel. De bestaande **Dagoverzicht**-popup
bevat actieve programmaperioden en de geregistreerde redenen. Programmatijd omvat
bijvoorbeeld ook drogen/pauze; dit is niet de exacte aan-tijd van de verwarming of pomp.

## 2. Eén analysebestand voor alle SolarPilot-functies

Onderaan het dashboard staat **Analyse-export**. Openen bedient niets.
Een Home Assistant-beheerder kiest laatste uur, 24 uur of zeven dagen en downloadt
één gestructureerd JSON-bestand. Daarna upload je het zelf naar ChatGPT.
Er is geen automatische externe upload, adviesdienst of automatische codewijziging.

Het bestand bevat waar beschikbaar:

- Release/schema, tijdzone, eenheden, HA/Python-versie, instellingen en effectieve regels.
- Gekoppelde en relevante apparaatsensoren: raw states, bruikbare attributen, eenheden,
  rapport-/wijzigingstijden, ouderdom, bronplatform/model/softwareversie indien beschikbaar.
- Net/PV/fasen, bronkwaliteit, kwartierpiek, prijzen, dagkosten en energieverdeling.
- Verbruikers, AEG-gates/programmaprofielen, tickets, starts/stops, actieve sessies,
  pending opdrachten, fouten en beslisredenen.
- Boiler-, klimaat-, Wallbox-, batterij-, PV- en plannerstatus en de bestaande lokale
  leerprofielen, ramingen, prognoses en kwaliteitssamenvattingen.
- Geregistreerde meetreeksen, bronwijzigingen, start-/stop-/herstartnotities en alleen
  SolarPilot's eigen WARNING/ERROR-logs, inclusief beschikbare foutdetails.
- Meetdekking, ontbrekende bronnen, opslagfouten, limieten en doorlooptijdmetingen.

Het is **geen** dump van de volledige Home Assistant-database, alle automatiserings-
YAML, alle logbestanden of alle in huis aanwezige entiteiten. Niet gekoppelde relevante
bronnen kun je bewust als extra bron selecteren. Voor een probleem in een andere
integratie kan de bijbehorende code of eigen log nog apart nodig zijn.

### Registratie en belasting

| Onderdeel | Standaard / harde grens |
|---|---|
| Gedetailleerde momentopnamen | Elke 300 s, instelbaar 60–900 s |
| Bewaarperiode | Maximaal 7 dagen, instelbaar 1–7 |
| Maximum meetronden | 2016; korter interval kan de effectieve periode verkorten |
| Bronwijzigingen / gebeurtenissen | Maximaal 20000 / 6000 |
| Snelle regelgegevens | Maximaal 2 uur én 1440 cycli, alleen in RAM |
| Geselecteerde bronnen | Maximaal 250, expliciete configuratiebronnen eerst |
| Extra geselecteerde bronnen | Maximaal 50 |
| Downloadbestand | Maximaal 16 MB; kies een kortere periode als het te groot is |
| Exportverzoeken | Eén tegelijk, minimaal 30 s tussen geslaagde exports |

De gewone regelcyclus blijft ongewijzigd. Er komen geen extra cloud-API-oproepen bij.
Lokale opslag wordt gebundeld geschreven. De JSON-opbouw en pseudonimisering gebeuren
buiten de HA-eventloop; het verzamelen van bestaande HA-toestanden blijft op die loop.

Onder **Geavanceerd & systeem → Analyse-export & lokale registratie** kun je interval,
retentie, bronnen of registratie zelf aanpassen. Uitzetten stopt alleen nieuwe
analyseregistratie. Bestaande gegevens vervallen volgens de termijn; gewone regeling
blijft actief en een actuele snapshot kan nog handmatig worden gedownload.

Gedetailleerde historie begint na installatie van beta.29. Een periode zonder
Home Assistant of geldige bron blijft onbekend en wordt niet achteraf verzonnen.
Reeds aanwezige oudere dagtotalen/leerprofielen kunnen als context meekomen, ook bij
een kort exportvenster. Gedetailleerde sessies worden op overlap met het gekozen
venster gefilterd; dat venster wist niets uit de oorspronkelijke historie.

### Privacy en analyse

Standaard worden entiteitsnamen en apparaatlabels vervangen door consistente codes
binnen het bestand. De keuze **Echte entiteitsnamen en toestelnamen opnemen** maakt
technische vervolgvragen makkelijker, maar geeft meer persoonlijke informatie mee.
Credentials, netwerk-/account-/locatiegegevens worden gefilterd. Camera-, persoon-,
tracker-, slot- en media-entiteiten worden niet verzameld.

**Dit is geen anonimiteitsgarantie.** Tijden, temperatuur- en gebruikspatronen zijn
persoonlijke gegevens. Controleer voor delen. Zet het JSON-bestand nooit op je
publieke GitHub-repository; `.gitignore` en de public-preflight weren herkenbare
analyse-exportbestanden. Deel nooit wachtwoorden of tokens.

Een passende analysevraag is: 'Analyseer dit SolarPilot-bestand. Onderscheid bewezen
waarnemingen, schattingen en onbekende perioden. Zoek fouten in bronactualiteit,
start/stop-redenen, net/PV-balans, warmtepomp-/Wallbox-samenspel en modelkwaliteit.
Verwijs naar tijdstippen en broncodes. Geef eerst de oorzaken en reproduceerbare tests;
verlaag geen veiligheidsgrenzen om een fout te verbergen.'

## 3. Update en testgrenzen

Rechtstreeks van beta.26 of beta.28 naar beta.29 is mogelijk. Tussenversies hoeven niet
één voor één gepubliceerd of geïnstalleerd te worden. Publiceer de volledige inhoud
over de bestaande repository, behoud `.git`, test lokaal, push eerst `main` en tag
`v1.0.0-beta.29` pas nadat die commit GitHub Validate heeft doorlopen. Niet forceren of
bestaande tags verplaatsen. Controleer privacy vóór `git add`.

De tests gebruiken fictieve Home Assistant-bronnen en browser-API-antwoorden.
Ze sturen geen echte afwasmachine aan en bewijzen niet dat jouw huidige AEG-cloud
remote START ondersteunt. Geen fysieke AEG/Shelly/HA-integratieacceptatietest is gedaan.
De daadwerkelijke GitHub Actions-, HACS- en hassfest-run volgt na jouw publicatie.
