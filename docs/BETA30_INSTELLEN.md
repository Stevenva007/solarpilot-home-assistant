# SolarPilot beta.30 — leren, toetsen en gerichte vragen

Deze volledige cumulatieve update bouwt op beta.29. Hij wijzigt geen live
Home Assistant-installatie of GitHub-repository totdat jij hem publiceert en
installeert. Geen nieuwe fysieke vrijgave; je boiler-, Wallbox-, klimaat- en
verbruikersregels blijven behouden. Bestaande leerdata worden niet gewist.

## 1. Waarom meer dagen alleen niet volstaan

De oude planning leert het basisverbruik niet tijdens >100 W Wallbox-/eigen
verbruik. Zo kunnen juist nuttige zonnige uren ontbreken. Ook is de oude
kwaliteitsindex geen nauwkeurigheidskans en bewijst de titel “7 dagen” niet dat
zeven volledige dagen zijn gemeten. De update verhelpt een deel van deze
model-/zichtbaarheidsbeperkingen, maar belooft geen perfecte kennis van je huis.

## 2. Installeren

Maak een Home Assistant-back-up en zet SolarPilot op Pauze. Laat eigen lasten
volgens hun beschermtijden vrijgeven; Pauze is geen noodstop. Publiceer de volledige
projectinhoud in je bestaande Git-repository, behoud `.git` en privégegevens.
Push eerst `main`, controleer de validatie van die commit en maak dan pas een
nieuwe tag `v1.0.0-beta.30`. Bestaande tags niet verplaatsen. Installeer via HACS
en herstart Home Assistant. Je kunt tussenliggende beta’s overslaan.

Er is geen aparte dashboardresource nodig. Bewaar je private bundle en eigen
configuratie; zet geen analyse-exporten in de publieke repository.

## 3. Leren & vragen openen

Na installatie staat onderaan het SolarPilot-dashboard **Leren & vragen**.
Bij open vragen staat ook bovenaan een bericht. Alleen een Home Assistant-beheerder
kan de volledige leervragen en beleidskeuzes lezen/beantwoorden. Er zijn zeven
overzichten: restverbruik, lokale PV/schaduw, ruimteklimaat, boiler, verbruikers/
Wallbox-reactie, fasen en batterijscenario’s. Per onderdeel zie je werkelijke
bron-/modelgegevens, geen samengevoegd “huis is voor 90% geleerd”-percentage.

### De drie leerkeuzes

| Keuze | Standaard | Betekenis |
|---|---|---|
| Brongebruik | Gemeten verbruik meenemen | Ook tijdens EV/eigen lasten leren wanneer de actuele aparte meters een betrouwbare balans geven. |
| Recent verbruiksprofiel | Eerst mijn toestemming | Kandidaat vergelijken; nog niet automatisch gebruiken. |
| Vragen als Home Assistant-melding | Uit | De vragen staan altijd in de popup. Optioneel ook onder HA-meldingen, maximaal een update per dag bij nieuwe vragen. |

Voor jouw wens om zoveel mogelijk zinvol te leren laat je **Gemeten verbruik
meenemen** staan. Beoordeel vervolgens de vraag over **Begrensd automatisch**.
Daarmee geef je uitsluitend toestemming voor de hieronder beschreven recente
basislastvariant. Het is geen algemene toestemming om apparaten of comfortgrenzen
te veranderen. De eigen PV-, thermische en toestelleermodules houden hun bestaande
instellingen; deze knop schakelt ze niet allemaal automatisch in.

Elke optie heeft een vraagteken met uitleg. Sla je keuzes expliciet op. Alleen
openen, hoveren of een voorspelling bekijken bedient niets. Je kunt later
terug naar “Eerst mijn toestemming”; de gewone bestaande live basislastmediaan
blijft dan leren, maar de aanvullende recente variant wordt niet toegepast.

## 4. Wat er extra wordt geleerd

Basislast is hier restverbruik, niet uitsluitend sluimerverbruik. Er wordt
alleen gerekend met de genormaliseerde netmeting, PV, een gevalideerde enkele
batterijmeting indien gekoppeld, de echte Wallboxmeting en het echte vermogen van
de beheerde actieve lasten. Ongemeten warmtepompvraag blijft in de restlast.

Geschatte/templatevermogens, dubbele bronnen, ontbrekende waarden, verkeerde
eenheden, ongeldige energiebalans en overgangsbedrijf worden geweigerd. Bronnen
moeten recent zijn; hun rapporttijdstippen mogen maximaal twee minuten uiteen
liggen. Na een eigen nieuwe start geldt twee minuten meetrust. Onzekerheid bij
een bron geeft geen nulwaarde. Een nieuwe meting wordt maximaal elke vijftien
minuten geteld, met een reden voor aannemen of afwijzen.

Voor meerdere echte batterijen is deze nieuwe restlastcorrectie nog niet
gevalideerd; die leerwaarneming wordt overgeslagen. Dat verandert de bestaande
batterijregeling niet. Unieke entiteitnamen bewijzen ook niet dat twee fysieke
meters geen overlap meten. Koppel de juiste echte meters; gebruik geen totale
huismeter als exclusieve toestel-/boilermeter.

Een herkend beschermd boiler-/sterilisatievenster wordt apart geregistreerd en
niet als dagelijkse basislast geleerd. De bijbehorende afwijking wordt WEL
meegerekend in de kwaliteitscontrole en apart benoemd. Dit is een contextlabel,
geen bewezen isolatie van het elektrische compressor-/elementvermogen.

## 5. Begrensd en controleerbaar aanpassen

De bestaande mediaan per uur en week-/weekenddag blijft het gewone profiel.
Daarvoor zijn minimaal vier verschillende bruikbare dagen per vak nodig; vaak
hebben weekendvakken daarom langer nodig dan werkdagen. Alleen plannen
herberekenen verhoogt de leerdagen niet.

De nieuwe kandidaat gebruikt de laatste veertien kalenderdagen. Bij de
vergelijking worden alleen dagen VOOR de beoordeelde dag als training gebruikt.
Dit vermijdt toetsen op dezelfde dag die al is meegeleerd. De kandidaat moet
op minstens vier verschillende vergelijkingsdagen in de recente periode zowel
10% als 20 W minder gemiddelde absolute fout geven dan het gewone profiel.
De correctie is begrensd op ±25% van dat profiel. Pas na jouw toestemming wordt
ze per geschikt vak gebruikt. Voldoet de vergelijking niet meer, dan keert
het vak terug naar het gewone profiel; gebruik/terugval worden gelogd.

Dit is historische rolling-origin validatie, geen garantie voor toekomstig
weer/gedrag en geen causaal aangetoonde energiebesparing. Bij een nieuwe meter,
veranderde gewoontes of nieuw seizoen blijft validatie nodig. De update gaat niet
zelf experimenteren door apparaten in te schakelen om ze te herkennen.

## 6. Welke vragen stelt SolarPilot?

Alleen concrete, geprogrammeerde vragen gebaseerd op de aanwezige gegevens,
geen onbeperkte AI-chat of zelfbedachte veiligheidsadviezen. Voorbeelden:

- Mag de getoetste recente basislastvariant binnen de aangegeven grenzen werken?
- Een bron kan niet voor leren worden gebruikt: koppelingen bekijken, zo laten of later vragen?
- Een toestel heeft nog geen aparte meter: meter koppelen of voorlopig schatten?
- Het restverbruik/de daglicht-PV-voorspelling wijkt af: analyse-export openen of verder verzamelen?
- De klimaatmodule meldt een fout: de bestaande instellingen/gegevens bekijken?

**Koppelingen bekijken** opent de bestaande configuratiewizard; het koppelt geen
sensor of schakelaar zonder jouw keuze. **Analyse-export** opent de bestaande
handmatige download. **Morgen vragen** stelt de vraag 24 uur uit. Een behoud-keuze
blijft geldig tot relevante bronkoppelingen veranderen. Geen antwoord is nooit
akkoord. Een verouderde revisie, dubbele klik of gewijzigde vraag wordt opnieuw
beoordeeld; een oude bevestiging kan geen andere keuze toepassen.

Optionele HA-meldingen krijgen een eigen ID zodat storingsmeldingen niet worden
overschreven. Ze worden ingetrokken als alle vragen beantwoord zijn of deze
meldingen zijn uitgezet. Dit zijn geen mobiele pushberichten, geen ChatGPT-taken
of automatische externe berichten.

## 7. Nieuwe kwaliteitsweergave

**Basislastvertrouwen** heet niet meer algemeen “Planvertrouwen”. De
**technische voorspelkwaliteit** toont de beschikbare dagen en vergelijkingen.
Er is een aparte **PV-fout bij zon** naast de gehele-dagfout. Voor deze aparte
statistiek telt een moment wanneer gemeten OF voorspeld PV minstens 100 W is,
zodat een onterecht hoge voorspelling bij nul opbrengst niet wordt weggelaten.
Ook fout-richting staat in de popup: positief is meer productie dan voorspeld.

Nieuwe dekking telt alleen korte intervallen tussen opeenvolgende bruikbare
waarnemingen. Hiaten groter dan tien minuten, restarttijd en ontbrekende data
worden niet ingevuld. Deze nieuwe meetdekking en daglichtstatistiek begint na
installatie van beta.30. De bestaande historische foutcijfers blijven behouden.

De oude kwaliteitsscore blijft een zelfgekozen technische index; deze update
valideert daarmee nog niet zelfstandig de hele 36-uursvoorspelling.

## 8. Wat beslist leren NOOIT zelf?

Geen wijziging van comfort-/temperatuurgrenzen, netstroomtoestemming, deadlines,
prioriteiten, stroom-/fasegrenzen, minimumtijden of hygiëne. Geen extra fysieke
bedieningsrechten, Force DHW, Powerful, HEAT/COOL-keuze of nieuw Shelly-relais.
Het rustige boilerprofiel, de zelfregelende Panasonic en je Wallbox-keuzes
blijven onder de bestaande regels vallen.

De AEG APP-start/13:00-deadline uit de verdere configuratiebespreking is NIET
geïmplementeerd in deze leerupdate. De beta.29-start-only adapter blijft behouden.
Een `Cycle phase: Unavailable` is geen bewezen programmastop; de eerder
geactiveerde oorspronkelijke Appliance state blijft de relevante statusbron.
De nieuwe complete APP-arm/einde/deadline-logica mag niet stilzwijgend worden
verondersteld omdat de software een hogere versie heeft.

## 9. Opslag, performance en analyse

Alles blijft lokaal en beperkt tot de gekoppelde functies. Geen inventarisatie
van alle camera’s, personen, sloten of aanwezigheidsgegevens. Leervakken bewaren
maximaal zestig dagen aan geaggregeerde data; oude/te toekomstige waarden worden
niet als actueel profiel gebruikt. Het dagoverzicht van leermetingen is beperkt
tot zestig dagen, antwoorden tot honderd en de audit tot 150 gebeurtenissen.

De volledige leerinformatie wordt alleen opgevraagd wanneer de popup geopend is: bij openen en daarna eenmaal per minuut. De normale
5-secondenstatus bevat slechts een kleine samenvatting en het aantal vragen.
Het scherm behoudt invoer, uitklappers en scrollpositie bij telemetrieupdates.
Berekeningen gebruiken bestaande HA-states en geen extra cloudoproepen. Lokale
softwareproeven zijn geen meting van jouw echte CPU-/geheugenbelasting.

De bestaande analyse-export bevat nu ook leerbeleid, meetkeuring, modelscores,
vragen en antwoorden. Deel die export alleen bewust; gebruikspatronen blijven
persoonlijk, ook met geanonimiseerde namen. Er is geen automatische upload.

## 10. Eerste beoordeling na installatie

Controleer onder Meetdekking of nieuwe waarnemingen geaccepteerd worden, ook
terwijl gemeten verbruikers werken. Open een bronvraag als veel punten geweigerd
worden. Beoordeel na meerdere uiteenlopende werkdagen én weekenddagen de
voorspelfouten per onderdeel, niet alleen of een percentage stijgt. Wis de
bestaande leerdata niet enkel om een betere score te krijgen.

Softwaretests gebruiken Home Assistant-doubles en fictieve browserantwoorden.
Geen fysieke AEG/Panasonic/Wallbox-test, echte HA-servertest of nieuwe
GitHub Actions/hassfest/HACS-run is door dit pakket uitgevoerd.
