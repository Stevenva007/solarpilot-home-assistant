# SolarPilot 1.0.0-beta.44 — testresultaten

Datum: **2026-10-02**

> **Definitieve lokale softwarecontrole groen:** **1760 geslaagde Python-tests in 11.68 s** en **veertien geslaagde browsercontroles**, inclusief de aanvullende boilerbewaking en dashboardcorrectie. Dit bevestigt de softwarekandidaat, niet publicatie, installatie of fysieke beta.44-acceptatie. De werkelijk geladen release blijft beta.43 totdat een nieuwe release en herstart afzonderlijk zijn gecontroleerd.

## Definitieve lokale softwarecontrole

De volledige Python-regressiesuite behaalde op **2 oktober 2026** **1760 geslaagde tests in 11.68 s**. Alle **veertien browsercontroles** zijn groen, inclusief het nieuwe boileroverzicht met gerapporteerd doel, voorgesteld doel en beschermende pauze. De browserproeven gebruikten fictieve gegevens en registreerden **nul actuatoroproepen**.

Ook de overige lokale releasecontroles zijn uitgevoerd en groen:

- actuele-uitlegcontrole: hash `65b54c9797e55bb4`;
- overdrachtscontrole, repositoryvalidatie en publieke preflight;
- syntaxcontrole van beide meegeleverde frontend-JavaScriptbestanden;
- `git diff --check`, documentspiegels en versieconsistentie tussen manifest, backend, kaart, actuele uitleg en optiehulp.

Drie gecontroleerde cachemappen zijn opgeruimd. De definitieve lokale softwaregate omvat de aanvullende Panasonic-bevestiging, native taakbron en nieuwe boilerweergave; zij vervangt het eerdere testtotaal als actuele softwarestatus.

## Eerdere volledige run

Op **2 oktober 2026** zijn **1729 Python-tests** en **veertien browsercontroles** geslaagd op de toenmalige beta.44-bron. De browserproeven gebruikten fictieve gegevens en voerden geen fysieke opdrachten uit.

Daarna zijn aanvullende wijzigingen toegevoegd: uitsluiten van de onmiddellijke optimistische Panasonic-doelterugmelding als opdrachtbevestiging, gemeld versus voorgesteld doel op het boilerdashboard en een expliciete read-only bron voor de native ruimte-/tapwatertaak. Het eerdere totaal is uitsluitend historische testinformatie. De hierboven vastgelegde definitieve run omvat de aanvullende wijzigingen.

## Werkelijk uitgevoerde gerichte controles

- Wallbox-guard, huis-eerstregel, verbruikersprioriteit, runtime-uitleg en automatische waarderegistratie rond expliciet **geen laadvraag**: **105 geslaagd in 0.81 s**.
- Wallbox-sessiebeleid met **Zonne-auto · wacht op auto**, native Full Solar, migratie van exact oude standaardlijsten en behoud van eigen waardelijsten: **56 geslaagd in 0.67 s**.
- De testopdrachten gebruikten UTF-8, schreven geen bytecode en maakten geen pytest-cache.

Deze twee aantallen zijn afzonderlijke, mogelijk overlappende gerichte suites en worden niet tot één totaal opgeteld.

## Gericht afgedekt gedrag

- Geen EV-reservering bij verse geldige lage laadkracht plus expliciet `demand=false`, een niet-verbonden auto of een bekende inactieve status.
- Lage laadkracht alleen is onvoldoende; oude, ongeldige, onbekende en strijdige bronnen blijven fail-closed.
- Actief manueel laden, verse gemeten laadactiviteit en externe stopvoorwaarden behouden hun bestaande bescherming.
- De standaard zonnelaadlijst herkent **Zonne-auto · wacht op auto** alleen samen met native Full Solar.
- Exact oude standaardlijsten worden case-, volgorde- en eenvoudig scheidingsteken-onafhankelijk compatibel uitgebreid; een werkelijk aangepaste lijst niet.
- De Wallbox-routes blijven read-only en verkrijgen geen start-, stop-, modus-, fase- of laadstroomrecht.

## Aanvullende controles op de definitieve bron

De definitieve regressies en browsercontroles dekken ook af dat:

- alleen de geregistreerde Panasonic-adapter de minimale wachttijd voor latere doelwaarneming gebruikt; een onmiddellijk optimistisch echo-bericht mag geen eigendom of opdrachtbevestiging opleveren;
- timeout, mismatch, herstart en een bestaande beschermende pauze niet leiden tot blinde herhaalopdrachten of automatisch wissen van handmatige overname;
- de dashboarduitleg het gerapporteerde doel en een beschermende pauze vóór een voorgesteld doel toont;
- een expliciet gekoppelde native taakbron vers, geldig en eenduidig moet zijn, en ruimtebedrijf of tegenstrijdige informatie de extra zonnebuffer blokkeert;
- Panasonic AUTO met een inactieve klimaatactie zonder betrouwbare taakbron niet als bewezen afwezig ruimtebedrijf geldt;
- `PUMP` en `WATER` niet als HEAT/COOL- of compressor-/elektrisch meetbewijs worden gebruikt, en de nieuwe bron read-only blijft;
- een nieuwe koppeling niet automatisch wordt ontdekt of uit private installatie-identiteiten wordt samengesteld.

Deze softwarecontrole bewijst niet dat een latere HA-waarneming rechtstreekse LIVE cloud-/apparaatrapportage is of dat de nieuwe regels fysiek zijn uitgevoerd.

## Nog open buiten de lokale softwarecontrole

- GitHub-CI, een nieuwe onveranderlijke beta.44-tag en de releasepublicatie;
- beide release-ZIP's, inhoud tegenover de tag, padveiligheid en werkelijk berekende SHA-256-checksums;
- HACS-installatie van exact beta.44, volledige herstart en afzonderlijke bevestiging van geladen backend en kaart;
- gecontroleerde toepassing/bevestiging van maandag uiterlijk 10:00 en de gerichte boilerreview;
- fysieke observatie van de nieuwe verdelingsregels tijdens een natuurlijk passend venster.

## Bewezen live uitgangspunt

- Home Assistant Core **2026.9.4** heeft SolarPilot **1.0.0-beta.43** werkelijk geladen; backend en kaart zijn afzonderlijk bevestigd.
- Na de gerichte DHW-review is **Automatisch regelen** om 15:02 hersteld en SolarPilot vroeg daarna een doel van 55 °C; de tankmeting lag rond 50 °C.
- Rond 15:45 ging de boilerregeling opnieuw in beschermende pauze bij een gemeld doel van 55 °C tegenover de laatste bevestiging van 50 °C. Een bewuste gebruikerswijziging is niet bevestigd. Optimistische lokale terugmelding gevolgd door oude cloudinformatie is een gereproduceerde softwarematige mogelijkheid, geen bewezen oorzaak van deze historische gebeurtenis. Een nieuwe gerichte review na installatie en controle is toegestaan, maar nog niet uitgevoerd.
- De native Panasonic-adapter 2026.8.7 kan bij AUTO een inactieve klimaatactie tonen ondanks mogelijk ruimtebedrijf. De gemelde taak `WATER` identificeert tapwater, maar bewijst geen draaiende compressor of exclusief vermogen. De nieuwe koppeling is aanvullende read-only bewaking, geen uitbreiding van actuatorrechten.
- De private Wallbox-helper onderscheidt inmiddels wachten op de auto van wachten op overschot; de native Wallbox-modus bleef Full Solar en werd niet door SolarPilot gewijzigd.
- De live Wallbox meldde vers geen laadvraag en 0 W. De bestaande beta.43-guard blokkeerde daardoor niet, maar een afgeleide sessietekst kon nog achterlopen. Beta.44 maakt de vrijgave en uitleg onafhankelijk van zo'n aantoonbaar achterlopende tekst, zonder de versheids- of geldigheidseisen te versoepelen.
- De live vermogensanalyse liet zien dat een conservatieve DHW-reserve plus een geschatte lopende AEG-reserve vrijwel alle ruwe vrije injectie kon verbruiken. Dat motiveert de nieuwe zichtbare effectieve toewijzing en proportionele 60 °C-regel, maar bewijst niet dat beta.44 die regels al live heeft uitgevoerd.
- Om 16:19 is een versleutelde Home Assistant-back-up van **1.24 GB** gereed gemeld op de bestaande NAS, inclusief instellingen, geschiedenis, SSL en alle vijf apps. De back-up gebruikt alleen deze NAS. Dit is geen uitgevoerde herstelproef.
- Om 16:34 is het SolarPilot-logo werkelijk zichtbaar bevestigd in het Home Assistant/HACS-updatevenster, samen met geïnstalleerd en beschikbaar `v1.0.0-beta.43`. De ondersteunde `entity_picture`-customisatie gebruikt de lokale Home Assistant-brandsproxy; daarna is uitsluitend de update-entiteit opnieuw opgevraagd. Er is geen HACS-codepatch of warmtepompcommando voor uitgevoerd.
- Maandag 10:00 en de nieuwe gerichte boilerreview zijn nog niet live toegepast en bevestigd.

## Geen fysieke claim

Beta.44 is tijdens dit verslag niet gepubliceerd of geïnstalleerd. Er is geen fysieke AEG-START, Wallbox-opdracht, geforceerde 60 °C-opwarming, Powerful-activering of nieuwe laadcyclus uitgevoerd om de softwaretest te laten slagen. Een echte AEG-/60 °C-samenloop mag alleen in een natuurlijk passend overschotvenster worden geobserveerd; onbekende broninformatie blijft fail-closed. Een doelwaarneming na wachttijd bewijst niet dat de tank het doel heeft bereikt of dat het cloudbericht een rechtstreekse fysieke meting was.

## Releasepakketten

De GitHub-workflow, release-tag en ZIP-assets bestaan pas na een afzonderlijke goedgekeurde publicatie. Controleer daarna werkelijk manifestversie, padveiligheid, afwezigheid van private/cachebestanden, inhoud tegenover de tag en SHA-256-checksums. Vul deze sectie niet vooraf met verwachte waarden.

Zie `BETA44_INSTELLEN.md` voor installatie, liveacceptatie en rollback.
