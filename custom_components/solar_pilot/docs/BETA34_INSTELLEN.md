# SolarPilot beta.34 — live instellingen en toestelbeheer

Volledige cumulatieve update op de rechtstreeks geüploade beta.33. Dezelfde energie-,
boiler-, Wallbox-, APP-afwas- en PV-regels blijven aanwezig. Deze versie wijzigt hoe
configuratie wordt opgeslagen en hoe afzonderlijke toestelprofielen beheerd worden.
Er is niets naar jouw GitHub gestuurd of op jouw Home Assistant bediend.

## 1. Installeren

Maak eerst een volledige Home Assistant-back-up. Zet voor de software-installatie
SolarPilot op Pauze en laat eigen lasten volgens hun bescherming vrijgeven. Een
lopende afwasbeurt wordt niet onderbroken. Werk bij voorkeur buiten een wasbeurt
bij zodat ook het korte native End Of Cycle-event tijdens de HA-herstart niet
verloren kan gaan. Deze verbetering verwijdert geen noodzaak tot een HA-herstart
bij een software-update; zij vermijdt herladen bij latere gewone optie-aanpassingen.

Publiceer de volledige projectinhoud bovenop je beta.33-repository, behoud `.git`,
privébundel en lokale data. Voeg geen extra geneste versiemap aan de repository toe.
Publiceer nooit je HA-configuratie, exportbestanden of `.storage`. Push de nieuwe
commit eerst naar `main`; wacht op groene validatie van die commit en maak daarna
pas de nieuwe tag `v1.0.0-beta.34`. Bestaande tags niet overschrijven.

Installeer via HACS en herstart Home Assistant. Controleer dat integratie en
SolarPilot-dashboard beide 1.0.0-beta.34 melden; herlaad eventueel de browser voor
de nieuwe lokale interfacebestanden. Geen extra frontend-resource, helper of
herimport nodig. Instellingen, APP-aanvragen en modellen worden niet naar een
nieuw standaardprofiel gereset.

## 2. Instellingen openen tijdens Zonnestroom

Gebruik het tandwiel bij Instellingen → Apparaten & diensten → SolarPilot, of
**Configureren met uitleg ?** in SolarPilot. De globale pauzeblokkering bij openen
is verwijderd. De koppelingen en lopende toestellen worden niet door openen gewijzigd.

De laatste wizardstap heet **Wijzigingen controleren en opslaan**. Daar staat:

- wat direct zonder volledige herlading kan worden toegepast;
- wat opgeslagen wordt maar op veilige vrijgave wacht;
- bij een relevante afwaswijziging: huidige aanvraag of volgende beurten.

Pas na aanvinken van de bevestiging en opslaan wordt de wijziging bewaard.
Een gewone edit behoudt de runtime, eigenaarschap, tellers, start-/stoptimers,
minimumlooptijden, modellen en de statuslisteners van ongewijzigde toestellen.
Opslaan verstuurt zelf geen start/stop. De normale volgende regelbeslissing kan
met de gewijzigde effectieve prioriteit of voorwaarden uiteraard anders uitvallen.

## 3. Wat wordt direct toegepast en wat wacht?

| Wijziging | Toepassing |
|---|---|
| Naam, categorie, prioriteit | Direct, ook als het toestel loopt. Prioriteit maakt een beschermd programma niet onderbreekbaar. |
| Tarief, analyse- of vooruitplanningsinstelling | Zonder volledige herlading; bestaande apparaten/timers blijven behouden. |
| Gedrag, minimumtijden of bronkoppeling bij een actief toestel | Bewaard als wachtend voorstel; pas toepassen zodra het toestel veilig vrij is. |
| Nieuwe actuator/status-/meterkoppeling bij een rustend toestel | Na validatie toepassen; Auto-deelname wordt Uitgesloten en de oude brongebonden leerdata/startrechten worden niet hergebruikt. |
| Centrale gevoelige bron-/limietwijziging tijdens een opdracht | Eerst terugmelding afhandelen. Geen dubbele opdracht of herstart van de hele regelaar. |
| Boiler-/klimaatbinding tijdens eigen beheer of bescherming | Wacht op gerichte vrijgave. Andere functies blijven lopen. |

**Onbekend is niet uit.** Een onzekere START-uitkomst, onbereikbaar toestel zonder
bevestigd einde of open herstelcontrole kan een voorstel langer laten wachten.
SolarPilot zet niets geforceerd uit om een instelling te kunnen toepassen. Bij een
ontvochtiger kan een voorstel wachten tot de normale regeling hem veilig heeft
laten stoppen. Bij een afwasmachine blijven de oorspronkelijke bronnen gedurende
de hele beurt actief, inclusief AirDry en het korte End Of Cycle-signaal.

Bij **Wachtende wijzigingen** zie je het toestel/de functiegroep en de reden.
Selecteer daar een voorstel om het te annuleren; de oude effectieve configuratie
blijft dan staan. Voor hetzelfde toestel eerst het bestaande voorstel annuleren
voordat je opnieuw een andere wijziging opslaat.

Een opgeslagen voorstel staat apart van de effectieve bronkoppelingen in de
config-entry. Ook na herstart blijft een lopende cyclus dus de oude bronnen volgen.
Een nieuwe meting die veilige vrijgave bevestigt, laat het voorstel op een normale
regelcyclus toepassen. Dit is geen vaste kloktijd of garantie dat het altijd snel kan.

## 4. Deadline/nettoestemming van een APP-aanvraag wijzigen

Bij een klaargezette afwasbeurt en een gewijzigde deadline, te-laatbeleid,
herstelvenster of nettoestemming verschijnt een extra keuze:

**Alleen volgende beurten** — standaard. De reeds bewaarde aanvraag houdt haar
geplande dag, oorspronkelijke deadline en nettoestemming. De nieuwe waarden worden
gebruikt na een nieuwe fysieke APP-vrijgave voor een volgende belading.

**Ook huidige klaargezette beurt** — wijzigt deadline/herstelvenster/nettoestemming
op dezelfde al geplande dag. Geen nieuwe toestemming, geen nieuwe plandag en geen
extra START. Een naar het verleden verplaatste deadline kan bij de volgende
regelcontrole starten toestaan als de apparaat- en elektrische voorwaarden kloppen.
Een reeds verstuurde/onzekere START mag hiermee niet opnieuw worden gestart.

Een lopende beurt werkt af met de oorspronkelijke koppelingen. Annuleren van een
wachtende wijziging is geen annuleren van een al gestart programma. De fysieke
APP-knop, exacte Enabled-herkenning, deadline 13:00 en standaard volgende kalenderdag
bij klaarzetten vanaf 13:00 blijven verder ongewijzigd.

## 5. Toestellen beheren

Op **Verbruikers** en onder **Onderzoek & instellingen** staat **Toestellen beheren**.
Je ziet per SolarPilot-profiel:

**Instellingen · Koppelingen · Planning · Historiek · Vervangen**

Met **Toestel toevoegen** voeg je een onafhankelijk profiel toe. Het categorieveld
onderscheidt afwasmachine, wasmachine, droogkast en andere verbruiker. Het technische
bedieningstype blijft apart: aan/uit, regelbaar, gecontroleerde scripts of de
bestaande AEG/Electrolux afwasmachine-startadapter.

Een categorie wasmachine/droogkast is **geen nieuw geteste merkintegratie**. Controleer
voor zo'n toestel de juiste oorspronkelijke bronnen en fabrikantondersteuning.
Gebruik geen slimme stekker om een lopend huishoudprogramma hard te onderbreken.
Een nieuw profiel begint Uitgesloten; nieuwe fysieke startrechten worden nooit
uit een naam, categorie of oude toestemming afgeleid.

De oorspronkelijke AEG-, Shelly- of Wallbox-integratie blijft bestaan. SolarPilot
maakt/verwijdert alleen zijn eigen virtuele bedienings-/statusentiteiten. Andere
SolarPilot-entiteiten behouden hun identiteit en listeners bij toevoegen of aanpassen.

## 6. Toestel vervangen

Kies bij het oude profiel **Vervangen** en bevestig de nieuwe identiteit. De wizard
neemt alleen herkenbare voorkeuren als voorstel mee: naam/categorie, energiekeuzes,
prioriteit en tijden. Actuator-, meter- en statusbronnen moet je opnieuw koppelen.
Vermogen, fysieke geschiktheid en minimumtijden moeten opnieuw worden gecontroleerd.

Het nieuwe toestel erft geen oude APP-aanvraag, Auto-deelname, boost, overname,
fouttoestand, vermogensmetingen of geleerd programma. Het begint Uitgesloten. Een
nog lopende oude beurt wordt eerst afgerond; tot die tijd staat ook de vervanging
als wachtend voorstel en bestaat de opvolger nog niet als actief profiel.

Het oude profiel staat daarna onder **Gearchiveerde toestellen** met alleen
historietoegang. De bestaande sessiehistoriek blijft maximaal 30 dagen bewaard,
niet onbeperkt. Afgesloten leerprofielen blijven als herkenbaar archief in de
analyse-export; ze worden niet op de opvolger toegepast. Een nieuwe machine met
dezelfde naam krijgt toch een eigen ID en meetprofiel.

## 7. Gelijktijdige wijzigingen en foutmeldingen

Twee wizardtabbladen mogen niet stilzwijgend dezelfde opgeslagen instelling
overschrijven. Niet-overlappende wijzigingen worden samengevoegd; een conflict op
dezelfde sleutel vraagt heropenen. Nieuwe actuator-/meterbindings worden ook
gecontroleerd tegen andere profielen en wachtende voorstellen. Een opslagfout
wordt gemeld en is geen bevestiging dat de wijziging actief is.

De analyse-export bevat ook de effectieve configuratie, voorgestelde wijzigingen,
archieven en toepasredenen. De privacyfilter neemt namen/ID's van gearchiveerde en
wachtende profielen mee. Behandel de export alsnog als privé; tijdstippen en
huishoudelijke patronen zijn geen anonieme gegevens.

## 8. Grenzen en eerste beoordeling

Deze release wijzigt geen energiemarges, maximaal vermogen, comfortdoelen, hygiëne,
APP-permissies of Wallbox-sessiedetectie automatisch. De rustige 50/46-boilerlogica
zonder 52 °C-herstelboost blijft behouden. Voorrangsverbruikers kunnen alleen onder
de bestaande voorwaarden bevestigd zonnevermogen van de Wallbox gebruiken;
manueel/onbekend laden geeft geen overdrachtsruimte. De Shelly-faseprofielplanning
blijft voor de afzonderlijke latere uitbreiding.

Controleer na installatie eerst een naam-/prioriteitswijziging terwijl de gewone
regeling actief blijft. Bekijk een opgeslagen gevoelige wijziging en annuleer die
bij twijfel. Verander geen werkende fysieke bron puur om te testen. Software- en
browserproeven met fictieve Home Assistant-antwoorden zijn geen echte HA-servertest
of fysieke acceptatie van AEG, Wallbox, warmtepomp of netbeveiliging.

## 9. Deze update als projectbron bewaren

Bewaar bij deze release de volledige ZIP, deze handleiding en het testverslag samen.
De ZIP bevat volledige broncode en ingebedde actuele uitleg. Voeg de drie bestanden
via de bronnenpagina van je ChatGPT-project toe. Een downloadlink in een chat of het
bewaren van alleen een tekstantwoord bewijst niet dat de oorspronkelijke ZIP als
projectbron is opgenomen. In deze sessie is geen tool beschikbaar om het lidmaatschap
van Project-bronnen zelf te wijzigen; de bestanden zijn daarvoor los aangeleverd.
