# SolarPilot beta.32 — afwasmachinevoorrang, cumulatieve update

## Wat deze release instelt

Deze versie bouwt volledig voort op beta.31. Hij behoudt de APP-knop, één toestemming
per beurt, de uiterste starttijd van 13:00 en na 13:00 standaard de volgende kalenderdag.
De korte `End Of Cycle`-melding blijft direct eventgestuurd vastgelegd; AirDry blijft
nadrogen en geen einde of leegmelding.

De nieuwe standaardvoorkeur is:

1. Gewoon warmtepompcomfort: vloerverwarming, sanitair water en noodzakelijke avondvoorraad.
2. AEG-afwasmachine met een werkelijk geldige aanvraag voor de geplande dag.
3. Wallbox, lagere automatische lasten (zoals de ontvochtiger), en de extra 60 °C-zonnebuffer.

De rangorde tussen de functies onder punt 3 blijft zoals jij die hebt ingesteld.
Dit is dus geen nieuwe keuze of de ontvochtiger boven of onder de extra 60 °C staat.
Handmatige overnames, beschermde cycli en minimumlooptijden zijn geen vrij opofferbare
lasten. Bij voldoende ruimte kunnen meerdere apparaten tegelijk werken.

Dit profiel is standaard AAN voor nieuwe én bestaande AEG-afwasmachineprofielen.
Het wijzigt geen fysieke bedieningsvrijgave, Auto-deelname, bronkoppelingen, gekozen
wasprogramma of bestaande toestemming voor deadline-netstroom. Een ontbrekend
AEG-profiel wordt niet op basis van een naam automatisch aan je installatie toegevoegd.

## Twee nieuwe opties, standaard aan

Open **Configureren met uitleg ? → Verbruikers & prioriteiten → AEG-profiel aanpassen**.
De opties staan in de stap met de AEG-statuswaarden en APP-afspraken:

| Optie | Standaard | Betekenis |
|---|---:|---|
| Afwasmachinevoorrang onder warmtepompcomfort | AAN | Afwas boven Wallbox, lagere automatische verbruikers en extra 60 °C; normale warmtepompregeling behoudt voorrang. |
| Zonnevermogen vóór Wallbox benutten | AAN | De afwas mag onder afzonderlijke controles starten met zonnevermogen dat de autonome Full Solar-lader momenteel gebruikt. Tijdelijke en latere netafname blijven mogelijk. |

Een eerder expliciet opgeslagen UIT blijft UIT. De afzonderlijke generieke optie
**Mag gecontroleerd vermogen van Wallbox overnemen** blijft voor afwasmachines UIT.
Die oudere regeling vereist een onderbreekbare last en terugneembare opdracht en
wordt niet voor een beschermd wasprogramma gebruikt.

Nieuwe AEG-profielen krijgen prioriteitsgetal 10 als voorstel. Een reeds opgeslagen
getal wordt niet herschreven. De voorkeurgroep gaat vóór gewone lagere verbruikers;
het getal rangschikt apparaten binnen hun groep. Een lager getal op je ontvochtiger
maakt hem daarom niet automatisch belangrijker dan een vrijgegeven afwasbeurt.

## Wat gebeurt er bij een al draaiende ontvochtiger?

SolarPilot beoordeelt of het werkelijk gemeten vermogen van een lagere, eigen en
onderbreekbare last genoeg ruimte kan vrijmaken. Als de afwas nog niet past, mag
de ontvochtiger klein restoverschot blijven gebruiken.

Bij voldoende stabiele ruimte voor de afwas wordt alleen de benodigde lagere last
vrijgegeven. De ingestelde compressor-minimumlooptijd blijft leidend. Pas na een
bevestigde stop én nieuwe netmeting kan er een nieuwe startopdracht komen.
SolarPilot schakelt geen extern of handmatig beheerde ontvochtiger uit om deze
voorkeur af te dwingen. Bestaande beschermde cycli worden niet onderbroken.

Voorbeeld (fictief, zonder overige blokkeringen): 1950 W injectie plus een eigen
350 W-ontvochtiger kan 2300 W injectie opleveren nadat die veilig is gestopt.
Dat kan voldoende zijn voor een 2000 W-planningswaarde, 100 W startmarge en 150 W
injectiereserve. Die 350 W wordt niet al als werkelijk vrij elektrisch vermogen
behandeld terwijl de ontvochtiger nog draait.

## Wallbox blijft autonoom: geen pauze-, stroom- of startopdrachten

Bijvoorbeeld: de auto gebruikt al 3000 W zonnestroom en er is weinig netto-injectie.
Een beschermde afwasstart mag met de nieuwe aparte optie van dat zonnevermogen
gebruikmaken, maar alleen wanneer:

- de geplande dag, APP-vrijgave, deur, gereedstatus, verbinding en technische alarmen kloppen;
- actuele PV-, net- en Full Solar-metingen bruikbaar en stabiel zijn;
- de afwas binnen de huidige net-, kwartierpiek- en faseruimte past **alsof de Wallbox nog niet terugregelt**;
- bestaande verbruiksverplichtingen en aankomend gewoon warmwatercomfort gereserveerd blijven;
- de totale gedeelde stap onder de ingestelde maximale Wallbox-overnamestap blijft.

Het actuele Wallboxvermogen telt alleen mee voor de mogelijke verdeling van zon,
nooit als extra capaciteit van de elektrische aansluiting. De ingestelde
Wallboxrapport-ouderdom en de bestaande stabiliteitstijden blijven gelden; geen
sneller ophalen van de cloud of extra cloudoproepen.

**Dit is geen garantie op uitsluitend zonnestroom.** De laadpaal reageert zelf op
minder overschot. Tijdens die reactie kan netafname ontstaan; later kan bewolking
ook netstroom nodig maken. Een eenmaal begonnen afwasbeurt wordt nooit afgebroken
om een energiebudget achteraf alsnog passend te maken.

Na de START registreert SolarPilot het werkelijk nieuwe Running-signaal en vraagt
hij verse Wallbox- en netmetingen. Een netto balans gedurende 30 seconden met
meerdere netrapporten wordt als balansbevestiging genoteerd, niet als bewijs van
exclusief gemeten afwasvermogen of een bewezen causale vermogensoverdracht.

Komt binnen 15 minuten geen bruikbare bevestiging, dan volgt één melding en worden
nieuwe starts op reeds door EV gebruikte zonne-energie voor die afwasmachine
geblokkeerd tot controle. De huidige beurt blijft afwerken. Een volgende start op
voldoende echt restoverschot of de expliciete deadline-nettoestemming blijft apart.
Gebruik de bestaande foutcontrole pas na controle van de metingen en wanneer de
betrokken machine werkelijk uit is. Geen blinde START-reeks of rollback-opdracht.

Zet **Zonnevermogen vóór Wallbox benutten** UIT om tot de Shelly/proef alleen op
werkelijke restinjectie te starten. De prioriteit boven ontvochtiger en extra 60 °C
blijft dan behouden, maar een autonoom ladende auto kan vóór de deadline vrijwel
al het zonneoverschot blijven benutten. De volledige directe Wallboxsturing wordt
hier niet stilzwijgend als alternatief aangezet.

## Warmtepomp blijft leidend

Gewone Panasonic-doelopdrachten en vrijgegeven klimaatopdrachten worden eerst
verwerkt; de afwas wijzigt geen enkele klimaatinstelling. Er wordt rekening
gehouden met een nog te verwachten gewone tankvraag, inclusief een al aangevraagde
avondvoorraad onder de ingestelde avondlimiet. Een alleen geselecteerde stand
`heating` wordt niet gebruikt als bewijs dat de compressor al vermogen trekt.
Een actuele afzonderlijke meter of expliciete actie kan daarvoor informatie leveren.

Zonder aparte warmtepompmeter blijven reserveringen conservatieve schattingen.
Dat kan tot extra wachten leiden, ook wanneer de installatie in werkelijkheid
ruimte zou hebben. Een bekende fabrikant-/sterilisatiecyclus wordt niet verlaagd;
met voldoende ruimte kunnen warmte en afwas tegelijk werken. Onbekende gekoppelde
comfort-/beschermingsgegevens geven geen nieuwe voorrangsstart vrij.

Alleen de extra 60 °C-zonnebuffer wijkt voor een actuele startklare of lopende
wasbeurt. Een aanvraag voor morgen blokkeert de hoge zonnebuffer vandaag niet.
Een reeds zelf aangevraagd hoog doel valt volgens bestaande terugvaltijd en
bescherming terug. Deze wijziging is geen harde compressorstop. Sterilisatie,
handmatige Powerful en Force DHW blijven buiten deze energiesturing.

Normaal 50 °C en bewaakte 46 °C blijven onafhankelijk. Geen tijdelijke verhoging
naar 52 °C voor herstel. De fysieke Panasonic-differentie en interne verdeling
van vloer- en tankverwarming blijven ongewijzigd. De bestaande waarschuwing dat
50 °C met −5 °C differentie geen gegarandeerde 46 °C biedt blijft van toepassing.

Na de start blijft het afwasprogramma beschermd, ook wanneer daarna de warmtepomp
meer vermogen nodig heeft. Voorrang is daarom geen absolute capaciteitstoewijzing
of garantie op gelijktijdig uitsluitend zonnestroomgebruik. De fabrikant en echte
elektrische beveiligingen blijven leidend.

## Zonder Shelly: nog geen fasegewijze programma-optimalisatie

De actuele startdrempel blijft de conservatieve toestelplanningswaarde plus marges.
De bestaande dashboardgemiddelden worden niet als bewezen piekmeting gebruikt.
Voorgesteld 2000 W is geen geverifieerde specificatie; controleer de passende
waarde voor de eigen machine voordat je voor het eerst automatische bediening vrijgeeft.

Tijdens een lopende ongemeten beurt reserveert de voorkeursregeling extra de
nominale stap voor latere verwarmpieken. Een fictief "gemeten" wattgetal uit een
schatting mag geen extra vrije ruimte creëren. Deze schatting staat expliciet in
het dashboard en de export. Dat is conservatief en kan restverbruikers langer
laten wachten. Met een echte exclusieve meter geldt weer de bestaande reservering
voor het nog onbenutte deel van toegezegd vermogen.

**Het gekozen programma per fase tegenover de zonnevoorspelling plannen blijft
voor de later gevraagde Shelly-update.** Deze release claimt die functie niet en
schakelt haar niet stilzwijgend in wanneer een willekeurige sensor beschikbaar komt.

## Dashboard en analyse-export

De AEG-kaart toont de voorkeurgroep, voorwaardelijk EV-zonnevermogen, eventuele
extra reservering zonder meter en het resultaat van de energiebalanscontrole.
De vraagtekens geven volledige uitleg bij de twee keuzes. De bestaande analyse-
export bevat ook de beleidskeuzes, de actieve reserveringen, de balanswaarneming,
de aanvraag/deadline en de start-/stopredenen. Er wordt niets automatisch geüpload.

## Bijwerken

1. Bewaar een volledige Home Assistant-back-up. Zet SolarPilot op Pauze en laat
   eigen onderbreekbare lasten veilig vrijgeven. Een lopend afwasprogramma wordt
   hierdoor niet gestopt. Doe de update bij voorkeur wanneer dat klaar is.
2. Kopieer de volledige projectinhoud naar de bestaande Git-repository. Behoud
   `.git` en privébestanden; publiceer geen `.storage`, HA-configuratie of exports.
3. Draai lokale tests en de meegeleverde uitleg-, repository- en privacycontroles.
4. Push `main`, controleer de validatie van die commit en maak dan de nieuwe tag
   `v1.0.0-beta.32`. Verplaats geen al gepubliceerde tag.
5. Werk via HACS bij en herstart Home Assistant. Een directe overstap vanaf oudere
   beta's is mogelijk; tussenliggende releases hoeven niet apart geïnstalleerd.
6. Bestaand AEG-profiel: controleer de twee nieuwe standaardvoorkeuren, de bestaande
   bronbevestiging, Auto, globale Zonnestroom en Wallbox Full Solar-terugmelding.
   Nieuw AEG-profiel: doorloop eerst de normale koppelingen uit BETA31_INSTELLEN.md.
7. Observeer één gewone belading. Vergelijk de startreden, fysieke Running-status,
   netmeting en Wallbox-reactie. De Shelly-koppeling blijft leeg zolang geen echte
   exclusieve vermogenssensor bestaat. Zet geen geschatte helper als echte meter.

Alle nieuwe voorrangsproeven zijn lokale software- en browsertests met fictieve
apparaten. Geen fysieke AEG-, Wallbox- of warmtepomptest of echte HA-serverproef.
Downloaden/installeren van de ZIP publiceert niet namens jou naar GitHub.
