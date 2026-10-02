# SolarPilot · Configuratiestructuur

**Geldig voor 1.0.0-beta.43.** Dit document beschrijft waar instellingen staan. Voor de inhoudelijke EMS-regels geldt uitsluitend `ACTUELE_WERKING.md`.

## Configuratiecentrum

Open **Instellingen → Apparaten & diensten → SolarPilot → Configureren**.

### Overzicht & controle

Toont modus, gekoppelde bronnen, actieve onderdelen, waarschuwingen en concurrerende regelingen. Gebruik dit als eerste controlepunt als iets onverwacht werkt.

### Energie & net

Hier staan de P1-/PV-bronnen, tekenrichting, injectiereserve, maximale softwarematige netafname, kwartierpiek, L1/L2/L3 en energieprijzen.

### Toestellen

Flexibele lasten worden via **Basis → Koppeling → Gedrag & bescherming → Planning & energie** beheerd. Nieuwe apparaten blijven **Uitgesloten** totdat je ze bewust op Auto zet. De gezamenlijke volgorde en toestemming om zonnevermogen van de auto te gebruiken staan uitsluitend centraal op **Voorrang → Voorrang en autoladen instellen**. Beschermde regels staan vast; toestellen, Auto laden en extra warm water vormen één verplaatsbare stapel. Per toestel staat één keuze **Mag de auto minder laden?**. Zodra de centrale lijst actief is, toont de toestelwizard geen tweede prioriteits- of Wallboxbediening. Ook een eerder geopend formulier kan de centrale keuzes niet terugschrijven. Minimumlooptijden blijven beschermd.

Op de toestelkaart staat de doorslaggevende actuele beslisreden. **Waarom dit toestel nog niet gestart is** toont daarnaast de relevante startinvoer: globale modus, Auto-deelname, beschikbaarheid/storing, vrijgave, vraag/tijdvenster, minimumrust, cyclusvrijgave, daglimiet, planner-/Wallbox-/runtimeblokkering, benodigd vermogen en stabiliteitstijd. Deze lijst is uitleg en geen extra startgarantie. **Geschiedenis** toont afzonderlijk Startreden en Stopreden en verzint geen ontbrekende externe oorzaak.

Het eenmalige AEG-herstel is een afzonderlijke migratie, geen instelling voor algemene toestelontdekking. De sinds beta.40 behouden herstelcontrole blijft na opstart maximaal tien minuten actief wanneer Home Assistant de markers of AEG-entiteiten later laadt. Een profiel wordt uitsluitend bij één volledige koppeling op hetzelfde apparaat blijvend en direct toegevoegd. De migratie verstuurt geen START; een nieuwe APP-overgang naar exact `Enabled` en alle bestaande veiligheidsvoorwaarden blijven nodig. Bij geen profiel toont `dishwasher_setup` per verplichte rol `missing`, `selected` of `ambiguous` en de afwijsredenen `disabled`, `restored`, `not_loaded` en `unavailable`, zonder het private Home Assistant-device-id.

Bij een AEG-profiel staat onder **Planning & energie** ook **Maandag: afwijkende uiterste starttijd (optioneel)**. Leeg gebruikt op maandag dezelfde gewone deadline als alle andere dagen, standaard 13:00. Alleen een bewust ingevulde tijd, bijvoorbeeld 10:00, wijzigt maandag. Een bestaand ticket houdt zijn geplande dag en deadline, tenzij je expliciet bevestigt dat de wijziging op het huidige verzoek mag worden toegepast; dan wordt uitsluitend dezelfde geplande dag herberekend, zonder nieuw ticket of START. Een lopende beschermde cyclus stelt de configuratiewijziging uit tot het bevestigde einde.

### Warmte & comfort

**Sanitair warm water** bevat de Panasonic-bronnen en het gewone 50 °C-doel, de bewaakte 46 °C-grens en de afzonderlijke extra zonnebuffer (standaard 60 °C), nachtvenster, koelblokkering en sterilisatiebescherming.

De beschermde avondvoorraad blijft begrensd tot de ingestelde limiet en maximaal 55 °C. Alleen een actueel bevestigde native Full Solar-sessie die ingeschakeld, verbonden en vragend is, minstens 50 W laadt en waarvan zowel status als vermogen hoogstens 120 seconden oud zijn, mag in deze comfortbeoordeling als vrijmaakbaar zonnevermogen tellen. Handmatig, onbekend, strijdig of oud laden telt niet mee. Extra 60 °C krijgt nooit dit EV-krediet; comfortgrens, koeling, fabrikantsterilisatie en overige beveiligingen blijven hoger.

Na herkende handmatige Panasonic-bediening toont de boilerkaart een gerichte **Hervat**-actie. Gebruik die in **Pauze** of **Alleen bekijken**. Zij beëindigt alleen de SolarPilot-rust en stuurt niet direct een temperatuur; tijdens **Automatisch regelen** of een wachtende opdracht blijft hervatten geblokkeerd.

**Ruimteklimaat · basis** koppelt de Panasonic-zones, weather-entiteit, actuele buitentemperatuur en de belangrijkste comfortbanden. SolarPilot stuurt nooit HEAT of COOL; Panasonic AUTO beslist dat zelf.

Een zone op AUTO is beschikbaar voor Panasonic, maar `hvac_action` bepaalt of zij werkelijk verwarmt of koelt. Een handmatig of extern OFF gezette zone blijft bij een gewone AUTO-beslissing OFF. SolarPilot zet alleen een eigen coast-zone terug naar AUTO; bij een harde comfortoverschrijding uitsluitend de werkelijk overschrijdende zone. Verwijderen geeft eveneens alleen SolarPilot-eigen coast vrij.

**Ruimteklimaat · geavanceerd** blijft beschikbaar als fallback-configuratie, maar de normale plaats om het klimaat te begrijpen en fijn af te stellen is voortaan het **dashboard → Warmte & comfort → Ruimteklimaat**.

Daar vind je in één samenhangend blok:

- **Status & advies** — binnentemperatuur, Panasonic-doel, AUTO/coast-advies en voorspelde comfortband;
- **Meldingen** — blokkeringen, lage modelzekerheid, ontbrekende PV/forecast en adviesmodus;
- **Bevindingen & leren** — warmteverlies, reactie op verwarmen/koelen, vloerreactievertraging, aangeleerde zonnewinst, lokale weerscorrectie en coast-resultaten;
- **Instellingen** — **iedere** `SMART_CLIMATE`-instelling, gegroepeerd per onderwerp;
- **Uitleg** — in gewone taal wat de klimaatregeling wel en niet doet.

Bij iedere dashboardinstelling staat:

1. een korte betekenis;
2. een aanbevolen startwaarde of keuze;
3. voor getallen: wat lager/hoger praktisch betekent;
4. voor schakelaars: wat Aan/Uit praktisch betekent;
5. bij bronwijziging: welk model daardoor opnieuw moet leren;
6. vóór opslaan: een bevestiging met huidige waarde, nieuwe waarde, advies en gevolg.

Er zijn dus geen verborgen klimaat-tuningwaarden zonder gebruikersuitleg. De fysieke Panasonic-doeltemperatuur blijft je thermostaatinstelling en is bewust **geen** SolarPilot-tuningwaarde.

### Klimaatleerlagen

**Zonnewinst in de woning**

Werkelijk PV-vermogen dient als lokale instralingsproxy. SolarPilot leert per zone hoeveel extra natuurlijke opwarming daarmee samenhangt. Dit is begrensd en wordt alleen bij voldoende leerkwaliteit gebruikt.

**Lokale weerscorrectie**

SolarPilot bewaart de fout tussen de eerdere uurforecast en de later werkelijk gemeten buitentemperatuur. Correctie wordt afzonderlijk geleerd rond 6, 12, 24 en 48 uur vooruit, met minimumsamples, minimum verschillende dagen, confidence en een maximumcorrectie.

**Coast-evaluatie**

Een door SolarPilot gestarte OFF/coastperiode wordt achteraf als **correct**, **te lang** of **te voorzichtig** beoordeeld. Alleen het minimum nuttige coastvenster mag daarna stap voor stap binnen jouw ingestelde onder-/bovengrens verschuiven. Comfortbanden, Panasonic-doel en HEAT/COOL worden nooit door deze feedback aangepast.

**Niet geïmplementeerd:** raam- en deurcontacten hebben geen invloed op het klimaatmodel of AUTO/coast-beslissingen.

### Auto & batterij

Wallbox blijft alleen-lezen. Onder **Wallbox · koppeling** kies je de effectieve sessiebron die volledige waarden onderscheidt voor zonne-auto, manueel laden en gestopt. De Full Solar-select is een instelling en geen bewijs van de werkelijke sessie. Stel ook het werkelijke minimum zonnelaadvermogen in (0 = nog niet bevestigd) en optioneel een specifiek aansluitingssignaal van deze laadpaal. Onder de geavanceerde Wallbox-instellingen staan stabiliteit, terugvalmarge, maximale wachttijd en herbeoordeling. Een aangesloten maar volle, gepauzeerde of niet-vragende auto houdt geen onnodige reserve vast. Het dashboard kan de actuele bekende native wachtstatus en maximaal dertig lokaal waargenomen laadperiodes tonen. Alleen een exact bekende status die na het laatste laadrapport en binnen vijf seconden van het stop-vermogensrapport werd ontvangen, mag als historische stopoorzaak gelden; meetgaten, herstarts en oude of onlogische tijden blijven onbekend. Dit observatiegeheugen verleent geen actuatorrecht. Toekomstige thuisbatterijen kunnen read-only of expliciet bestuurbaar worden gekoppeld; fysieke batterijbediening vereist meerdere toestemmingen. Batterij-what-if blijft adviserend zonder hardware.

### Voorspellen & leren

Forecast.Solar, lokaal PV-/schaduwmodel en planner. Actuele meters blijven altijd belangrijker dan forecast of historische patronen.

**Apparaat-, lokale PV-, fase- en klimaatleerdata wissen** is een begrensde onderhoudsactie voor lokale afgeleide leerlagen: Wallbox-respons, toestelvermogenssamples, live-PV-correctie, faseprofielen, klimaatprofielen, weersbias en coast-feedback. De actie wist geen instellingen of historische PV-bootstrap, laat operationele klimaatveiligheid en andere modellen staan en voert geen regelcyclus of fysieke opdracht uit.

### Export

Eén hoofdactie **Analysebestand downloaden** maakt het volledige onderzoeksbestand voor periodieke controle. Standaard wordt zeven dagen gevraagd en worden namen gepseudonimiseerd. Extra periode-/naamkeuzes staan onder de geavanceerde exportopties.

### Instellingen & systeem

Technische engine-timing, meetkwaliteit, faseherkenning, Wallbox-herkenning, privéprofiel/historiek en systeeminformatie. Dit zijn geen dagelijkse instellingen. **Privéprofiel & historiek** leest uitsluitend het lokale `userfiles/private_bundle.json`, toont welke bron-groepen ontbreken en kan de bundel opnieuw conservatief toepassen zonder fysieke regeltoestemmingen te activeren.

## Dashboardstructuur

De gewone kaart heeft negen hoofdtabs:

- **Overzicht** — beslisinformatie, belangrijkste KPI's, **Nu actief** op werkelijk waargenomen status en een afzonderlijke automatische-voordeelschatting;
- **Voorrang** — alle flexibele zonneprioriteiten, Wallbox en extra warmwaterbuffer in één verschuifbare lijst;
- **Toestellen** — apparaten toevoegen, koppelen, plannen, historiek bekijken of vervangen;
- **Warmte & comfort** — boiler én het volledige klimaat-Control Center;
- **Planning** — gezamenlijke 24–48-uursplanning, dagdoelen, beschermde cyclusprofielen, planfouten, what-if-replay, tijdlijn en plannerinstellingen;
- **Energie** — kwartierpiek, fasen, forecast en lokaal PV-model;
- **Batterij** — Wallbox, batterijvloot en batterijscenario's;
- **Export** — één lokaal onderzoeksbestand met expliciete periode- en privacykeuze;
- **Uitleg** — de release-gebonden actuele werking.

Moduskeuze en kritieke waarschuwingen blijven bovenaan zichtbaar.

## Ontwerpregel

Nieuwe functies horen in een bestaande logische categorie tenzij dat echt niet kan. Bij iedere gedragswijziging worden code, Home Assistant-uitleg en `ACTUELE_WERKING.md` in dezelfde release bijgewerkt.


## Planning-tab

De Planning-tab hoort bij **Voorspellen & optimaliseren → Unified Planner**. Hier staan horizon, planblokken, dagdoelen, beschermde cycli, voorspelde import/export/kost, 7/30-dagen plannerkwaliteit, recente what-if-replay en alle actieve plannerinstellingen. Wijzigingen vanuit het dashboard tonen eerst een korte uitleg, advies en de gevolgen. Beschermde cycli worden per programma geconfigureerd bij **Toestellen → Planning & energie**.

### Elektriciteitskost vandaag

**Overzicht** toont de netto kost vandaag. **Planning** en **Energie** tonen daarnaast afnamekost, injectievergoeding, rechtstreeks zonneverbruik en vermeden aankoop. De kost over de planhorizon blijft een afzonderlijke voorspelling. Bedragen gebruiken de ingestelde afname-/injectieprijs; ontbrekende meetperioden worden expliciet gemeld. Eigen zon wordt niet tweemaal afgetrokken.

De afzonderlijke automatische-voordeelweergave start voorwaarts en bewaart maximaal negentig kalenderdagen. Alleen een door SolarPilot beheerde, werkelijk actieve Auto-verbruiker telt mee; ontbrekende meet- of prijsdata wordt niet als nul ingevuld en eerdere dagen worden niet gereconstrueerd. Het resultaat is een opportunity-value-schatting, geen bewezen causale extra besparing en geen tweede korting op de elektriciteitskost. Gemeten en geschatte bronkwaliteit blijven onderscheiden.

### Geschiedenis per toestel

**Toestellen → Geschiedenis** opent een aparte popup voor het gekozen toestel. Bovenaan staan de dagtotalen; eronder de aan-perioden op een tijdlijn, 7/30-dagenbalkjes en de sessies met afzonderlijke Startreden en Stopreden. De datumkiezer, Vandaag en Vorige/Volgende dag veranderen alleen wat je bekijkt. Een actieve sessie wordt als lopend gemarkeerd. De popup blijft open tijdens de gewone dashboardupdates.

De registratie is alleen-lezen en respecteert Home Assistant-leesrechten. Historische redenen van vóór de installatie worden niet ingevuld. Een onbeschikbare status of herstart is een meetgat, geen bewezen stop. Bij een slimme stekker is de draaitijd de ingeschakelde tijd; voor echte compressorlooptijd is een bijpassende actieve-statusbron nodig. De complete begrenzing en opslagregels staan in `ACTUELE_WERKING.md`.

Browser **Terug** en **Vooruit** herstellen uitsluitend SolarPilot-schermen en -dialogen binnen dezelfde Home Assistant-URL. Een gewijzigd formulier vraagt bevestiging voordat het wordt weggegooid; een opslag- of andere lopende actie kan zo niet worden onderbroken. SolarPilot wijzigt de Home Assistant-router niet en speelt geen formulierinhoud of fysieke opdracht opnieuw af.

## Geïntegreerde opties met vraagtekens

Open onderaan het SolarPilot-dashboard **Configureren met uitleg ?**. De wizard gebruikt de bestaande Home Assistant-optiesflow en voegt per veld een hover-/klikbare uitleg toe. De oorspronkelijke HA-instellingen blijven beschikbaar.

**Sanitair warm water** bestaat nu uit Koppelingen → Temperatuurregels → Nacht, ochtend en avondvoorraad → Terugmelding en stabiliteit. In de nieuwe derde stap staan het nachtbeleid, ochtenddoel/tijd/buffers, avondreserve/zonnehorizon en de optionele voorspellende koelblokkering.

**Wallbox** bevat ook automatisch laadprofiel, optionele laadstroom-/fasebron, handmatig fase-/stroomprofiel en afgeleid zonnelaadminimum. ICP is niet de laadlimiet.


## Dagelijkse bediening in beta.43

**Overzicht · Voorrang · Toestellen · Warmte & comfort · Planning · Energie · Batterij · Export · Uitleg**

Voorrang bundelt toestellen, Wallbox en extra boilerwarmte. Vaste comfort- en hygiënebescherming staat zichtbaar erboven. Een bewaarde toestemming Ja onder Auto laden blijft bewaard, maar wordt daar als effectief Nee getoond; pas de positie boven Auto laden kan haar actief maken en ook dan blijven alle startvoorwaarden gelden. **Nu actief** is actuele waarneming en geen oorzaaksclaim. Export bundelt het samenstellen van één lokaal onderzoeksbestand met bestaande privacy- en tijdvensterkeuze. Toestelbeheer, PV-diagnose en Leren & vragen blijven afzonderlijk beschikbaar; alle algemene exportverwijzingen komen op Export uit.

Activeer in lagen: controleer eerst alles in **Alleen bekijken**, kies pas daarna globaal **Automatisch regelen** en zet vervolgens alleen gecontroleerde toestellen afzonderlijk op **Auto**. **Pauze** voorkomt nieuwe gewone opdrachten maar onderbreekt geen beschermde lopende cyclus. Een update, migratie, uitlegscherm of opgeslagen Voorrang stuurt op zichzelf geen toestel en verleent geen nieuwe batterij-, klimaat-, DHW- of AEG-bevoegdheid.
