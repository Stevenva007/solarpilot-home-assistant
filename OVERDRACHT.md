<!-- solarpilot-handoff-schema: 1 -->
<!-- solarpilot-handoff-version: 1.0.0-beta.111 -->

# OVERDRACHT — SolarPilot

Laatst bijgewerkt: **28 oktober 2026**. Actuele bron: **v1.0.0-beta.111**. Bouwbasis: gepubliceerde beta.110 `b840a0cf25a8a7e0cc346c5d99b5c82090b88ffc`. Installatie en rollback: `docs/BETA111_INSTELLEN.md`. Softwarebewijs en publicatievoorwaarden: `docs/TESTRESULTATEN_BETA111.md`.

## 1. Projectdoel in gewone taal

SolarPilot verdeelt het echte huidige zonneoverschot lokaal zonder toekomstige toestelpieken te reserveren. SG/warmtepomp heeft vaste toegang tot actueel coherent bevestigd autonoom Wallbox-zonnelaadvermogen. Gewone toestelvolgorde en eigen overnamerechten blijven apart. Panasonic regelt comfort, warm water, koeling en sterilisatie zelfstandig. Actuele bronnen bepalen wat een opdracht of behoud mag; een plan of verstreken tijd is geen vrijgave. Een toegestaan automatisch algemeen AAN-contact mag zonder uurstop aanblijven zolang actuele voorwaarden passen, met korte lokale toestemming en oorspronkelijke looptijd.

## 2. Actuele basis

Automatisch algemeen SG-zonbedrijf heeft geen verplichte maximale uurduur meer. Een toegestaan AAN-contact blijft behouden zolang actueel bruikbaar zonnebudget en alle overige voorwaarden voldoen. Start/elapsed worden niet administratief vernieuwd. Iedere korte lokale lease en vernieuwing vraagt actuele toestemming; onvoldoende bruikbare zon wordt ook bij lage ruwe P1-import als begrensd tekort behandeld. De maximale duur blijft gelden voor tijdelijk handmatige en andere begrensde routes.

Beta.111 maakt de SG-zonnevoorrang op autonoom laden onafhankelijk van de centrale lijst en tijdelijke Wallboxvoorkeur. Gewone toestelrangen en hun eigen EV-rechten veranderen niet. SG is geen apart tijdelijk Wallboxvoorrangdoel meer. Alleen werkelijk actuele coherente bevestigde zonnelaadsessies geven EV-credit; oude, handmatige, onbekende of tegenstrijdige bronnen niet. Het volledige actuele EV-vermogen wordt in de energiebalans beoordeeld vóór bestaande import en marges, met afzonderlijk begrensde feitelijke overname.

Een afzonderlijke bruikbare-zonwaarneming bevat het gezamenlijke P1-/HP-/EV-budget met oorspronkelijke bronkwaliteit en meettijden. Echte vrije injectie blijft apart. Na een bewezen beëindigde automatische sessielimiet of onbekende reactie kan dit budget opnieuw voldoende zijn zonder eerdere zonnedip of gewijzigde Panasonic-context. Vereist zijn actuele UIT, minstens twee nieuwe oorspronkelijke rapporten en eenmaal de ingestelde startstabiliteit. Voor vervanging van nog lopende verzoekrust zijn daarnaast volledig passend oorspronkelijk opdrachtbewijs, dezelfde koppeling en UIT na dat einde nodig. Na gewone rust kan de actuele geldige configuratie met nieuwe stabiele bronnen een nieuwe aanvraag dragen, ook bij onvolledige historie of gewijzigde configuratie. Een oude beleidshash blijft dan geen permanent slot. Langzamer gemelde bronnen worden niet door een snelle P1-poll verjongd. De bronidentiteit en actuele finale toestemming worden ook na opslag- en transportwachten opnieuw getoetst.

Alleen de verzoekrust van zo'n bewezen automatische aanvraag wordt vóór afloop vervangbaar; dit is geen compressorbeveiliging. SG heeft geen tweede zonnepoort via de aparte Wallbox-residudrempel of Wallbox-stabiliteitsklok. Een al geopend oud contact wordt werkelijk als nieuwe aanvraag beoordeeld, zonder oude verstreken bewijsduur te lenen. De volgende krijgt een nieuwe korte gecontroleerde lokale lease; automatisch algemeen zonbedrijf kan daarna blijven zolang de actuele voorwaarden passen. Harde duurgrenzen blijven gelden voor handmatige en andere begrensde routes. Native voltooiing, aantoonbaar geen opname, profielwijziging, handmatige UIT en onzekere opdrachten behouden hun eigen behoefte-/herstelvoorwaarden. Herstart of oude samples geven geen nieuwe bevestigingsduur.

De 3000 W blijft een geraamd totaalvermogen bij SG; alleen complete verse passende HP-meting verlaagt de mogelijke extra opname. Geen toekomstige toestelreserves. De beta.110-firmwareverificatie en bewezen rebootherstel, compacte recordergegevens, beschermde cycli, gewone wolkenbuffer en begrensde vierminuten-Wallboxreactie blijven behouden.

## 3. Absolute ontwerpregels

- Panasonic-entiteiten en Wallbox blijven read-only. Alleen de bewust toegewezen bestaande fysieke SG-uitgang heeft haar aparte gecontroleerde schrijfroute. Geen native temperatuur-, programma-, heater-, AUTO/OFF-, laad- of tweede-Shelly-opdracht toevoegen.
- Actuele P1 bevat alle huidige lasten. Geen toekomstig piekvermogen of ongebruikte nominale toestelvraag als extra reserve aftrekken. De ingestelde vaste huisbuffer is een afzonderlijke expliciete marge. Ontbrekend toestelvermogen is onbekend, geen gemeten nul.
- Nieuwe opdrachten blijven geserialiseerd. Pending, opslagbewijs, echte terugmelding, stabilisatietijd en nieuwe oorspronkelijke netmeting blijven nodig. Een opgeslagen intentie is geen fysiek bewezen verbruik of vrij vermogen. Onzekere eigen SG-opdrachten behouden hun afzonderlijke herstelcontract.
- Alleen complete verse exclusieve HP-meting mag de resterende mogelijke SG-toename verlagen. Deelmetingen, restored, oude of overlappende bronnen geven geen credit. Een wijziging van raming mag nooit meetdekking verzinnen.
- De centrale volgorde van gewone toestellen, bewuste deelname, vraag, interlocks, minimumtijden en bestaande toestemming blijven gelden. Een wachtende aanvraag reserveert niets; een werkelijk startklare passende hogere kandidaat krijgt de volgende opdracht. Een lopende afwasbeurt wordt nooit gestopt om SG of een ander toestel te starten.
- SG heeft vaste zonnevoorrang op de bevestigde autonome Wallbox-sessie, ongeacht centrale of tijdelijke Wallboxkeuze. Gewone toestelvolgorde en rechten blijven ongewijzigd; hun passende kandidaat mag geen EV-credit lenen die uitsluitend SG mag benutten. Actuele coherente laaddata blijven vereist. Voorwaardelijke EV-bijdrage is geen vrije P1-injectie; handmatige, onbekende, oude, ontbrekende of tegenstrijdige bronnen geven geen credit.
- Houd echte restinjectie en het bruikbare gezamenlijke SG-zonnebudget als aparte waarnemingen. Nieuwe herstart na een automatische sessielimiet of onbekende reactie vraagt actuele UIT, minstens twee nieuwe rapporten en eenmaal startstabiliteit. Vervanging van nog lopende verzoekrust vraagt ook volledige passende oorspronkelijke opdrachtidentiteit; na gewone rust beoordeelt de huidige geldige configuratie de nieuwe aanvraag zonder permanent oudhashslot. Een bronhiaat, gewijzigde koppeling of nieuwe oorspronkelijke meettijd geeft geen fictieve terugwerkende bevestiging. Alleen deze bewezen verzoekrust is vervangbaar. Automatisch algemeen zonbedrijf mag doorlopen zonder zijn oorspronkelijke start te resetten; handmatige en andere begrensde eindtijden worden niet verlengd.
- De tijdelijke SG-/Wallboxuitzondering betreft uitsluitend de softwarematige totale importgrens. Ruwe P1, actuele afzonderlijke fasegrenzen, resterend kwartierbudget, batterijontlading, bronactualiteit, koeling, contact, eigendom en toepasselijke begrensde eindtijd blijven onafhankelijk. Relevante bronnen worden ook na awaits opnieuw gelezen.
- De episode krijgt één oorspronkelijke absolute eindtijd en eerste plafond. Uitlezen, nieuwe laadrapporten, leasevernieuwing en herstart verlengen die niet. Nieuw herstel vraagt lage ruwe P1 gedurende de bevestigingstijd en minstens twee nieuwe rapporten; rond de softwaregrens schommelen geeft geen nieuwe tijd. Bronverlies trekt de uitzondering in.
- Een bewezen firmware-update/Shelly-herstart naar werkelijk UIT veroorzaakt geen blijvende handmatige-UIT-pauze. Vereis passend oorspronkelijk eigen bewijs, dezelfde hardware/binding, actuele geldige configuratie en tijd-/uptimebewijs. Bij automatisch algemeen zonbedrijf eindigt de oude fysieke contactepisode; een nieuwe aanvraag volgt pas na verse gewone startstabiliteit en finale actuele controles met een nieuwe korte lokale lease. Een oude uurdeadline of verlopen automatische firmwarewacht wordt bij verse UIT op dezelfde actuele koppeling geen permanent slot. Dit is een echte fysieke OFF/ON-onderbreking, geen administratieve reset tijdens doorlopend AAN; alleen bij doorlopend AAN blijven de oorspronkelijke start/elapsed behouden. Handmatige en andere begrensde routes houden hun oorspronkelijke eindtijden en aparte herstelvoorwaarden. Geen blind ON-replay en zonder bewijs geen wegredeneren van fysieke handmatige UIT.
- Extern SG-AAN geeft geen eigendom of nieuw timerrecht. De oorspronkelijke vijftien minuten blijven na herstart staan. Voortzetting vraagt actuele voorwaarden en bevestiging van de korte lokale timer, zonder noodzakelijke UIT-puls. Fysieke handmatige UIT blijft beschermd; onzekere opdrachten worden niet blind herhaald.
- Een firmwareversiewijziging alleen mag geen blokkade of handmatige herbevestiging veroorzaken. Controleer dezelfde fysieke uitgang en actuele configuratie/timer automatisch; herstel de oude firmware-only-latch uitsluitend met passend bewaard hardwarebewijs en verse geldige uitlezing. Een echt ander toestel, andere fysieke koppeling of onbruikbare timer is geen firmware-only-geval. Ontbrekend bewijs en diagnostiek geven geen actuatorbevoegdheid.
- Afwasmeteractiviteit is presentatie/historie, geen START-bevestiging, ticketverbruik, programma-einde of volledig cyclusleerbewijs. Energie wordt niet over reset, gat, herstart, bronwissel of middernacht geïnterpoleerd.
- Ontbrekende, restored, boolean, niet-eindige, toekomstige of beschadigde gegevens worden geen actuele nul. Uitlezen en formatteren vernieuwen geen oorspronkelijke meettijd. Oude historie behoudt haar oorspronkelijke bronrechten en betekenis.
- Onleesbare bestaande opslag wordt niet stil overschreven. Geen privé-export, huisidentiteit, bronbinding of geheim in publieke Git-/releasebestanden.
- Iedere release werkt de canonieke actuele uitleg, optiehulp, changelog en dit dossier bij. Controleer actuele officiële upstream-HEADs en stabiele tagcommits. Publicatie vraagt alle vijf commitgebonden gates en de exacte assetvergelijking.

## 4. Actuele werking

P1/PV, eventuele batterij-/fasebronnen en toestelmetingen blijven leidend. Echte restinjectie, compleet gemeten HP-bijdrage en voorwaardelijke autonome EV-zonnebijdrage blijven afzonderlijk. De vaste SG-zonnevoorrang verandert niet de rangorde of eigen rechten van gewone toestellen. Plannen geven geen fysieke toestemming en lopende afwasprogramma’s blijven beschermd.

Het SG-startpad houdt zijn actuele voorwaarden, korte lokale lease, minimumduur en gewone tekortbevestiging. Een toegestaan automatisch algemeen zoncontact kan zonder uurstop aanblijven zolang de huidige voorwaarden passen, met oorspronkelijke start/elapsed en actuele lokale timervernieuwing. Maximumduur blijft van toepassing op handmatige en andere begrensde routes. Voor een volgende bewezen automatische algemene aanvraag na sessielimiet of onbekende reactie kan het huidige gezamenlijke budget over eenmaal de ingestelde startduur worden bevestigd, met minstens twee nieuwe bronrapporten en actuele UIT na de vorige aanvraag. Het contact wordt pas na finale actuele bron-, identiteit-, koel-, elektrische en contact-/timercontroles bediend.

De gewone wolkenbuffer blijft standaard 600 W/300 s op ruwe P1. Automatisch algemeen zonbedrijf heeft daarnaast een eigen bruikbare-zontekorttimer onder max(0, threshold_w - hysteresis_w), met de bestaande stop_delay_s en het oorspronkelijke minimum parallel. De oorspronkelijke minimumdeadline wordt niet verplaatst; onbruikbare of onbekende bronnen geven geen continuous-recht. Automatisch algemeen zonbedrijf heeft daarnaast een eigen bruikbare-zontekorttimer onder max(0, threshold_w - hysteresis_w), met de bestaande stop_delay_s en het oorspronkelijke minimum parallel. De oorspronkelijke minimumdeadline wordt niet verplaatst; onbruikbare of onbekende bronnen geven geen continuous-recht. De afzonderlijke Wallboxreactie is standaard 240 seconden met oorspronkelijk plafond en absolute eindtijd. Zij versoepelt alleen de softwarematige totale netgrens. Actuele fase-, kwartier-, batterij-, bron-, koel-, contact- en sessievoorwaarden blijven onafhankelijk. Er wordt geen EV-vermogen van ruwe P1 afgetrokken om die overige controles te omzeilen.

## 5. Configuratie, integraties en belangrijke entiteiten

Installatie-specifieke entiteiten blijven in privéconfiguratie, SolarPilot-opslag en userfiles. Nieuwe software wijzigt geen fysieke bronbinding, SG-capaciteit, native setpoint of lokale timerbevestiging op grond van een exportvermoeden. Het SG-ramingsgetal blijft bewaard; de nieuwe totaalbetekenis wordt in veldhulp en releasehandleiding expliciet vermeld.

De frontend, manifest en backend horen bij dezelfde versie. Actuele Aquarea-semantiek, bruikbare providerpoll, passende HA-rapporten en bevestigde brondekking blijven afzonderlijke voorwaarden. Een label of versienummer bewijst geen bronkwaliteit.

## 6. Belangrijke ontwerpbeslissingen + waarom

Een SG-start kon al genoeg zonnebijdrage uit HP en EV berekenen terwijl de herstart na de sessielimiet uitsluitend echte restinjectie of een nieuwe context verlangde. Dezelfde zonnestroom werd dan verschillend behandeld bij starten en opnieuw starten. Beta.111 voegt een afzonderlijk actueel bruikbaar budget toe; de echte P1-injectie wordt daarvoor niet herschreven.

De gewone startstabiliteit wordt eenmaal gebruikt in plaats van vijf minuten herbevestiging plus nogmaals de startbuffer. Originele brontijden, nieuwe rapporten, bevestigde UIT en finale hercontrole voorkomen toestemming uit alleen verstreken tijd of oude gekoppelde data. Bestaand volledig opdrachtbewijs kan aantonen dat de rust een beëindigde SG-aanvraag betreft, niet een door SolarPilot beheerde compressorstop.

Vaste SG-zonnevoorrang is een gerichte uitzondering tegenover autonoom laden. De hele centrale lijst herschikken zou onbedoeld gewone toestellen een andere Wallboxpositie of EV-recht geven. Daarom blijven die keuzes behouden en wordt SG uit de tijdelijke Wallboxvoorrangkeuze gehouden. Een gewone hogere kandidaat wordt op haar eigen overnamerechten beoordeeld.

Een versie-/build-/appwijziging blijft informatief. De bestaande actuele controle van dezelfde fysieke uitgang, configuratie en lokale timer en het bewezen firmwareherstel worden niet teruggedraaid. De korte lokale lease, handmatige/andere begrensde eindtijden en begrensde Wallboxreactie houden hun eigen controles. Automatisch algemeen zonbedrijf heeft geen einddeadline door de oude uurinstelling.

## 7. Automatische processen

De lokale regelcyclus, bronhercontrole, analysecollectie, historie, planner en modelopslag blijven hun eigen begrensde processen volgen. Bronwachten blokkeren alleen de betrokken onbruikbare route. Onzekere opdrachten krijgen geen blind replay.

SolarPilot uploadt geen exports automatisch en voert geen achtergrond-AI of providerupdate uit. GitHub Validate publiceert op main uitsluitend na de vijf vereiste gates. Een bestaande tag of asset wordt nooit verplaatst of overschreven.

## 8. Geheimenbeleid

Tests en browserfixtures gebruiken uitsluitend fictieve bronnen. Diagnosebestanden blijven buiten Git. Geen tokens, huisadressen, installatie-URLs, privé-entiteitslijsten, recorderbestanden of ruwe huishouddatasets in repository of release-ZIPs. Opslag en leermodellen blijven lokaal; publieke loguitvoer bevat geen geheime foutbodies of headers.

## 9. Testprocedure + actuele teststatus

Definitieve lokale volledige suite op 28 oktober 2026: 9159 geslaagd, 0 fouten, 0 overgeslagen in 256,83 seconden; 169 gevallen in zes nieuwe beta.111-testbestanden, 170 gevallen meer dan beta.110. Gerichte firmwarecontrole: 81 geslaagd; onafhankelijke actuele-zon-/firmwarecontrole: 32 geslaagd. Bron bleef tijdens de suite ongewijzigd. De regressies omvatten doorlopend automatisch algemeen zonbedrijf zonder uurstop/startreset, begrensd tekort bij weinig zon en lage P1-import, behoud van handmatige duurgrenzen, vaste SG-zonnevoorrang, gewone kandidaat-eigen rechten, volledige actuele EV-balans, herstart na sessielimiet met laag residu en actief HP-/EV-zonneverbruik, eenmaal startstabiliteit, oorspronkelijke meettijden en late bron-/identiteitswijzigingen. Ook de kortste geldige begrensde maximuminstelling knipt een bewezen automatische start-/vernieuwingslease niet meer in. Bestaande firmware-, lease-, klok-, fase-, kwartier-, batterij-, afwas-, recorder- en UI-regressies blijven gelden. Actuele uitleg/optiehulp, handoff, privacy/structuur, SG-opdrachtgrens, beide JS-syntaxcontroles, diffcontrole en online upstreamreview zijn lokaal groen; guidehash f01e17f3cc7b0353. Zie docs/TESTRESULTATEN_BETA111.md.

De aftelregressie behoudt haar vaste hele seconde om Python-/JavaScript-afronding uit de fixture te houden; productieklokken en strikte bronvervalcontroles blijven behouden. De echte browser-sleepregressie beweegt met twintig echte muisstappen van zichtbare rank-/sleepgreep naar doelgreep, zodat dragEnter en de dragOver-doelacceptatie beide plaatsvinden. Midden op een mobiele rij kan een keuzelijst staan. Exacte volgorde, vertrouwde native dragstart/drop, foutstatus en opslagbericht blijven verplicht; rect-/hitpoint-/eventdiagnostiek verklaart een mislukte sleep. Geen fake-events of gewijzigde productiebediening. GitHub bevestigde ook 9159 geslaagde gevallen op Python 3.13 in 189,61 seconden. Controleer volledige suite, actuele uitleg/optiehulp, handoff, privacy/structuur, SG-opdrachtgrens, beide JavaScript-syntaxcontroles en online upstreamreview.

Alle vijf commitgebonden CI-gates blijven verplicht: repository/full-suite, HACS, Hassfest, echte Chromium-interacties en echte Home Assistant-startup. Geen oudere groene head of lokaal ontbrekende browser als vervanging voor de exacte controles.

## 10. Bekende problemen / beperkingen

Softwaretests certificeren geen fysieke bekabeling, kalibratie, werkelijke SG-opname, lokale timer of Wallboxreactie. De 3000 W is een raming, geen bewezen technisch maximum. Nieuwe actuele pieken kunnen tijdens minimumduur of stopbuffer tijdelijke import geven. De software-uitzondering verhoogt geen fysieke aansluitcapaciteit.

Het vierminutenvenster betreft actieve HA-policy. De bestaande lokale eigen SG-lease is standaard 300 seconden; bij HA-uitval is fysieke UIT exact op 240 seconden niet gegarandeerd. Extern AAN krijgt geen nieuw lokaal timerrecht. Oude foutregistraties kunnen de oorspronkelijke fingerprintvergelijking missen; nieuwe versies vullen dat verleden niet in.

## 11. Concrete openstaande ontwikkeling

Controleer ook doorlopen voorbij de vroegere uurgrens zonder reset, actuele korte leasevernieuwing en tekortvrijgave bij weinig zon ondanks lage P1-import. Beoordeel na normale installatie de natuurlijke actuele SG-/Wallboxreactie met oorspronkelijke brontelemetrie. Controleer de afzonderlijke restinjectie, HP-/EV-bijdragen, gezamenlijke herstartbijdrage en concrete bronreden. Voer geen geforceerde warmte- of laadproef uit als publicatiestap. Een onbekende fysieke warmtepomprespons of energie-/bronfout blijft een afzonderlijke onderzoeksvraag; geen nieuwe native writer toevoegen.

## 12. Installatie/upgrade en rollback

Update via HACS naar beta.111, herstart Home Assistant volledig en herlaad app/browser. Behoud entry, configuratie, modellen en privéopslag. Controleer beide versies, de SG-totaalraming en de concrete actuele bron-/wachtreden. Er is geen nieuwe schakelaar nodig om de vaste SG-zonnevoorrang toe te staan. Maak vooraf een volledige privéback-up inclusief userfiles en aanvullende historie.

Rollback naar beta.110 behoudt actuele lastverdeling, totaalraming, firmwareherstel en begrensde Wallboxreactie, maar herstelt de oude automatische sessielimiet en maakt SG opnieuw afhankelijk van de oude centrale/tijdelijke Wallboxkeuze en eerdere herstartregels. De uurgrens kan SG dan weer openen en op een zonnedip of gewijzigde context laten wachten. Geef een eigen SG-aanvraag waar betrouwbaar mogelijk veilig vrij en behoud configuratie en gegevens. Zie docs/BETA111_INSTELLEN.md.

## 13. Belangrijkste bestanden

- runtime.py en engine.py: actuele lastverdeling, geserialiseerde opdrachten en finale bron-/elektrische controles.
- heatpump_budget.py: apart werkelijk restoverschot, compleet gemeten HP-bijdrage en voorwaardelijke EV-bijdrage; mogelijke SG-toename uit de totaalraming.
- priority_board.py / wallbox_priority.py: gewone centrale/tijdelijke keuzes en kandidaat-eigen rechten; vaste SG-zonnevoorrang en SG uitgesloten van tijdelijke Wallboxvoorkeur.
- dishwasher_priority.py: echte startvoorwaarden en ononderbreekbare cyclusbescherming zonder toekomstige piekreserve.
- sg_boost.py / sg_transport.py: afzonderlijke bruikbare-zonherstart, oorspronkelijke deadlines, eigendom, lokale SG-grens en firmwarediagnose.
- sg_wallbox_transfer.py: oorspronkelijk episodeplafond, absolute eindtijd, herstelbewijs en conservatieve herstart.
- analysis_export.py: oorspronkelijke brontelemetrie en begrensde SG-/Wallboxovergangen; geen aftelseconde-eventstroom of nieuw controlrecht.
- sensor.py: compacte Wallbox-recorderattributen met volledige actuele status.
- frontend/solar-pilot-card.js: actuele reden, geraamde totale/extra opname, wijzigingsdiagnose en geldige overdrachtafteller.
- current_guide.py / option_help.py: canonieke actuele uitleg en veldhulp met gegenereerde mirrors.

## 14. Release-checklist

Volledige suite en passende regressies; actuele uitleg, optiehulp en handoff; privacy/structuur; SG-opdrachtgrens; online upstreamreview; beide JS-syntaxcontroles; diffreview. Daarna vijf groene exacte PR-CI-gates. Pas vervolgens samenvoegen op main. Main herhaalt de gates en publiceert tag, HACS-ZIP, lokale ZIP en beide beta.111-release-documenten. Vergelijk alle vier gedownloade assets tegen exacte tag/bron-SHA. Geen manual-release-omweg, force-push of verplaatste oude tag.

## 15. AI-handoff

Begin bij de concrete volgende gebruikersvraag, actuele bron en dit dossier. De gebruiker wil dat SG altijd toegang heeft tot bevestigde autonome Wallbox-zonnestroom. Herstel geen afhankelijkheid van centrale of tijdelijke Wallboxvolgorde voor SG. Verander daarvoor niet de gewone toestelrangen of hun eigen EV-rechten.

Laat een bewezen automatische sessielimiet of onbekende reactie opnieuw beoordeeld worden op actueel bruikbaar P1-/HP-/EV-budget zonder verplichte eerdere zonnedip of Panasonic-contextwissel. Houd echte vrije injectie apart en stel EV-credit niet voor als gemeten export. Gebruik oorspronkelijke brongeldigheid, actuele UIT na einde, passende opdrachtidentiteit, minstens twee nieuwe rapporten en eenmaal startstabiliteit. Finale controle na awaits blijft verplicht. Herstart, uitlezen of een wijziging van bronnen verleent geen oude tijd of nieuwe sessie.

De 3000 W blijft een geraamd totaal, geen hard fysiek maximum. Geen toekomstige toestelreserveringen. Behoud de begrensde softwarematige Wallboxreactie, echte fase-/kwartier-/batterijvoorwaarden, koeling, handmatige UIT, beschermde cycli, onzekere opdrachten en native behoeftevoorwaarden. Behoud bij doorlopend AAN de oorspronkelijke start/elapsed en behoud bewijsdeadlines. Een bewezen werkelijke firmware-UIT beëindigt voor automatisch algemeen zonbedrijf de oude contactepisode; een nieuwe aanvraag vraagt verse gewone startstabiliteit en finale actuele controles, zonder oude uurcap. Automatisch algemeen zonbedrijf mag zonder uurstop aanblijven onder actuele voorwaarden; vernieuw de korte lokale lease alleen na actuele controle. Verleng handmatige of andere begrensde eindtijden niet.

Firmwareversiemetadata op dezelfde bewezen uitgang blokkeert niets; bestaand firmwareherstel blijft behouden. Verzin geen ontbrekend hardware-/timerbewijs, maak geen private bron publiek en claim geen fysieke proef die niet is uitgevoerd. Werk bij iedere wijziging actuele uitleg en overdracht bij.
