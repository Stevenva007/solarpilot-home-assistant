# SolarPilot 1.0.0-beta.41 — instellen, controleren en rollback

Datum: 2026-10-02

## Waarom deze release

Beta.41 bouwt cumulatief voort op de geregistreerde beta.40. De veilige late AEG-recovery blijft behouden. Deze release maakt vooral duidelijk wat SolarPilot werkelijk beslist en corrigeert twee eigendomsgrenzen die in de live installatie zichtbaar werden:

- de centrale prioriteit mocht geen tweede bediening in de toestelwizard houden;
- een gewone klimaat-AUTO-beslissing mocht een handmatig OFF gezette zone niet wakker maken;
- een extra hoog boilerdoel mocht alleen door hysterese worden vastgehouden wanneer SolarPilot dat doel werkelijk bezat.

Daarnaast toont het dashboard startvoorwaarden en echte start-/stopredenen zonder ontbrekende oorzaken te verzinnen.

## Voor de upgrade

1. Maak een volledige Home Assistant-back-up.
2. Laat een reeds lopende AEG-cyclus afwerken. Gebruik geen STOPRESET vanuit SolarPilot.
3. Zet SolarPilot bij twijfel tijdelijk op **Pauze** of **Alleen bekijken**.
4. Noteer de huidige centrale volgorde, de per-toestelmodus en handmatig OFF gezette Panasonic-zones.
5. Schakel oude PV-/boilerregelaars nog niet uit voordat SolarPilot veilig klaarstaat om ze over te nemen.

## Installeren en werkelijk geladen versie controleren

1. Installeer `1.0.0-beta.41` via de bestaande HACS-repository.
2. Herstart Home Assistant volledig.
3. Controleer in de SolarPilot-status dat de geladen integratieversie exact `1.0.0-beta.41` is.
4. Vernieuw de browser geforceerd wanneer de backend beta.41 meldt maar de kaart nog oude teksten toont.
5. Blijf tijdens de onderstaande controles in **Alleen bekijken**.

## Eén centrale Voorrang

Open **SolarPilot → Voorrang**.

- Beschermde elektrische, fabrikant-, hygiëne- en noodzakelijke comfortregels staan vast.
- Toestellen, **Auto laden** en extra warm water staan in één verplaatsbare lijst.
- Per toestel staat één keuze **Mag de auto minder laden?**.
- **Ja** is uitsluitend een voorwaardelijke toestemming. Positie vóór Auto laden, een geldige zonnelaadsessie, een geschikte eigen meter/actuator en alle elektrische grenzen blijven nodig.
- Een toestel na Auto laden krijgt geen autolaadvermogen, ook niet omdat eerder ergens een oude toestemming stond.
- Opslaan wijzigt de centrale regelset maar stuurt op zichzelf geen toestel.

Open daarna bij één toestel **Planning & energie**. Bij een actieve centrale lijst mogen daar geen tweede prioriteits- of Wallbox-toestemmingsvelden staan. Een formulier dat vóór de omzetting openstond mag de centrale keuzes niet terugschrijven; sluit en open het formulier opnieuw bij twijfel.

## Startvoorwaarden en start-/stopredenen

Open **SolarPilot → Toestellen** en kies een toestel dat nog niet draait.

Het blok **Waarom dit toestel nog niet gestart is** toont onder meer:

- globale modus en per-toestel Auto-deelname;
- beschikbaarheid, storing en vrijgave/interlock;
- actuele vraag of tijdvenster;
- resterende minimumrust;
- vrijgave van een beschermde cyclus;
- dagelijkse maximumlooptijd;
- planner-, Wallbox- en overige runtimeblokkeringen;
- minimumvermogen, startmarge en geldige gemeten vrije ruimte;
- opbouw en resterende tijd van de startstabiliteit.

De tekstuele beslisreden komt rechtstreeks uit de regelaar en blijft doorslaggevend. De checklist verklaart invoer maar verleent geen startrecht en is geen belofte dat een opdracht zal volgen.

Onder **Geschiedenis** staan per sessie altijd **Startreden** en **Stopreden**. Alleen werkelijk geregistreerde redenen worden getoond. Bij externe bediening, een herstart of een meetgat kan de oorzaak expliciet onbekend blijven.

## Wallbox live koppelen

Open **Configureren → Auto & batterij → Wallbox → Koppeling** en kies als effectieve sessiebron de entiteit die werkelijk deze volledige waarden levert:

- `Zonne-auto · laden`;
- `Zonne-auto · wacht op overschot`;
- `Manueel laden`;
- `Manueel laden · klaar`;
- `Manueel / solar uit`;
- `Laden gestopt`.

De standaard herkenningslijsten van beta.41 ondersteunen deze waarden al. Controleer minstens één zonne-auto-, één manuele en één gestopte toestand. De afzonderlijke Full Solar-select is alleen een instelling en geen bewijs van de actieve sessie. Bij onbekende, oude of strijdige status blijft Wallbox-vermogen gereserveerd. SolarPilot verstuurt geen start-, stop-, laadstroom-, fase- of modusopdracht naar de Wallbox.

## Klimaat controleren

Panasonic **AUTO** betekent dat de fabrikant mag regelen; kijk naar `hvac_action` om te zien of een zone werkelijk verwarmt of koelt.

1. Laat één zone bewust op AUTO staan en zet een andere zone handmatig op OFF.
2. Laat SolarPilot in Alleen bekijken de winter-/zomerbeslissing berekenen.
3. Na gerichte vrijgave mag een gewone AUTO-beslissing de handmatige OFF-zone niet wijzigen.
4. Alleen wanneer precies die zone de ingestelde harde comfortband werkelijk overschrijdt, mag zij afzonderlijk naar Panasonic AUTO worden vrijgegeven.
5. SolarPilot kiest nooit HEAT of COOL en wijzigt de Panasonic-doeltemperatuur niet.

De harde grens wordt pas bij een echte overschrijding actief; exact op de ingestelde grens is nog geen hard override. Bij onvoldoende geleerde warmte-/koelrespons blijft automatisch coast conservatief uit. De zichtbare reactievertraging is dan een fallback totdat echte cycli voldoende bewijs leveren.

## Warm water controleren

Het normale doel, de comfortgrens, Panasonic-sterilisatie en handmatige functies blijven afzonderlijk beschermd.

- De bredere overschothysterese geldt alleen wanneer SolarPilot het extra hoge doel werkelijk heeft verstuurd en de terugmelding dat eigendom bevestigt.
- Bij werkelijke netafname boven de ingestelde grens valt een door SolarPilot beheerd extra doel zonder gewone terugvalvertraging weg.
- Actieve koeling begrenst het extra doel onmiddellijk tot de ingestelde koelcap.
- Een onbeheerde, externe of alleen berekende 60 °C-stand krijgt geen SolarPilot-hysterese.
- Tijdens `manual_hold`, sterilisatie of andere fabrikantbescherming berekent SolarPilot hoogstens advies en schrijft het geen doel.

Controleer dit eerst met live statusvelden `control_allowed`, `manual_hold`, `owns_target`, `cooling_block`, actueel doel en voorgesteld doel. Schakel de oude boilerautomatiseringen pas uit wanneer SolarPilot veilig kan overnemen en geen tweede regelaar tegelijk schrijft.

## Veilig activeren

Activering blijft bewust in lagen:

1. **Alleen bekijken** — diagnose, leren en planning zonder gewone fysieke toestelopdrachten.
2. **Automatisch regelen** — globale toestemming, maar nog geen toestemming voor elk individueel toestel.
3. **Auto** per gecontroleerd toestel — afzonderlijke deelname met behoud van koppelingen, interlocks, minimumtijden en elektrische grenzen.

Laat nieuwe of nog niet fysiek gecontroleerde toestellen **Uitgesloten**. Batterijbediening vereist daarnaast globale én individuele toestemming en bevestigd exclusief setpoint-eigendom. Fasecontrole vereist geldige L1/L2/L3-metingen en correcte fysieke limieten. Een update, migratie, opgeslagen prioriteit of leerresultaat activeert deze rechten niet.

## AEG-regels uit beta.40 blijven gelden

- Alleen één volledige, eenduidige same-device mapping kan door de begrensde herstelroute worden opgeslagen.
- De migratie verstuurt geen START, maakt geen APP-ticket en kiest geen programma.
- Iedere nieuwe belading vereist een nieuwe fysieke overgang naar exact `Enabled`.
- Ready To Start, actuele verbinding, gesloten deur, geldig programma, elektrische ruimte en alle andere veiligheidslocks blijven verplicht.
- Eén belading krijgt maximaal één native START. Running, Washing, Rinsing, Drying en Ado Drying blijven beschermd tot het echte End Of Cycle.
- Zonder exclusieve afwasmachinemeter wordt geen gemeten fase- of programmaprofiel verzonnen.

## Rollback

1. Zet SolarPilot op **Pauze**.
2. Laat een beschermde lopende cyclus afwerken.
3. Herstel beta.40 of de Home Assistant-back-up en herstart Home Assistant.
4. Controleer centrale prioriteit, toestelmodi, klimaatzones, boilerdoel/eigendom en Wallbox-sessiebron opnieuw.
5. Houd er rekening mee dat beta.40 de nieuwe startdiagnostiek en de beta.41-klimaat-/DHW-correcties niet bevat.

Zie `TESTRESULTATEN_BETA41.md` voor de werkelijk uitgevoerde software- en livecontroles. Publiceer of activeer geen fysieke regeling op basis van voorlopige testvelden.
