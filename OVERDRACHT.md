<!-- solarpilot-handoff-schema: 1 -->
<!-- solarpilot-handoff-version: 1.0.0-beta.112 -->

# OVERDRACHT — SolarPilot

Laatst bijgewerkt: **30 oktober 2026**. Actuele bron: **v1.0.0-beta.112**. Bouwbasis: gepubliceerde beta.111 `6e16eff56da55eacbc43452411e2d708050bf551`. Installatie en rollback: `docs/BETA112_INSTELLEN.md`. Softwarebewijs en publicatievoorwaarden: `docs/TESTRESULTATEN_BETA112.md`.

## 1. Projectdoel in gewone taal

SolarPilot verdeelt het echte huidige zonneoverschot lokaal zonder toekomstige toestelpieken te reserveren. SG/warmtepomp heeft vaste toegang tot actueel coherent bevestigd autonoom Wallbox-zonnelaadvermogen. Gewone toestelvolgorde en eigen overnamerechten blijven apart. Panasonic regelt comfort, warm water, koeling en sterilisatie zelfstandig. Een toegestaan automatisch algemeen SG-contact blijft aan zolang nog bruikbare zon en actuele overige voorwaarden aanwezig zijn. Lager moduleren vraagt geen herhaling van het startvermogen; korte wolken vallen onder de bestaande tekortbuffers.

## 2. Actuele basis

Beta.112 corrigeert twee oorzaken van onnodig stoppen. De nieuwe beta.111-controle op gezamenlijk bruikbaar zonnebudget gebruikte ook tijdens lopend SG de startdrempel minus hysterese. Daardoor kon een warmtepomp op lager volledig door zon gedekt vermogen alsnog als tekort gelden. Voortzetting vraagt nu bruikbaar gezamenlijk budget groter dan nul na bestaande import-, batterij- en huisbuffercorrecties. De ruwe P1-importbuffer blijft apart bepalen of actuele opname te veel net vraagt. Een werkelijk nieuwe start houdt zijn eigen drempel, raming en stabiliteit.

Daarnaast kan de oudste meettijd van het gezamenlijke budget teruggaan wanneer een nog actuele HP- of EV-bijdrage na een kort verschil in rapportagetijd weer coherent wordt. Dit is geen uitgeputte tekortbuffer. Oorspronkelijke actualiteit en rapportvoortgang worden afzonderlijk gecontroleerd; oude rapporten, herstart en klokterugloop geven geen nieuwe tekorttijd.

Op uitdrukkelijk verzoek gebruikt beta.112 een standaardtekortbuffer van vijftien minuten (900 s) voor zowel zonne- als importtekort. De vroegere standaard van 300 s migreert eenmaal naar 900 s; andere bewaarde aangepaste duurtijden en latere eigen keuzes blijven behouden. Bestaande actieve tekortdeadlines worden niet verlengd. Twintig minuten minimumduur, 600 W zachte importgrens, vier minuten begrensde Wallboxreactie en de korte 300 s/60 s-lokale lease blijven behouden. Bij doorlopend AAN blijven oorspronkelijke start/elapsed staan. Automatisch algemeen zonbedrijf heeft geen verplichte uurstop; handmatige en andere begrensde routes houden hun eindtijden.

De beta.111-herstart na bewezen automatische sessielimiet of onbekende reactie, vaste SG-zonnevoorrang, firmwareverificatie en bewezen rebootherstel blijven behouden. De 3000 W blijft een geraamd totaalvermogen bij SG; alleen complete verse passende HP-meting verlaagt de mogelijke extra opname bij een nieuwe aanvraag.

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

P1/PV, eventuele batterij-/fasebronnen en toestelmetingen blijven leidend. Echte vrije injectie, compleet gemeten HP-bijdrage en voorwaardelijk autonoom EV-zonnevermogen blijven afzonderlijk. Starten vraagt minstens de actuele ingestelde startdrempel, startstabiliteit en alle finale voorwaarden; actueel bruikbare herstart na de daarvoor bewezen beëindigde aanvraag vraagt ook actuele UIT en minstens twee nieuwe oorspronkelijke rapporten.

Bij een lopend automatisch algemeen contact hoeft bruikbaar zonnebudget niet opnieuw de startdrempel te halen. Meer dan nul na de bestaande correcties is nog zon; een modulerende warmtepomp met lager vermogen kan dus blijven draaien. Meer dan standaard 600 W ruwe P1-netafname begint de importbuffer. Bij de grens of lager wordt die klok gewist. Een geldig gezamenlijk bruikbaar zonnebudget van nul begint de aparte zonnebuffer; nieuwe actuele bruikbare zon wist die klok. Beide gebruiken standaard 900 seconden. Gewone tekortvrijgave volgt ook de oorspronkelijke minimumduur van standaard 1200 seconden; de lokale lease houdt terugmeldruimte vóór die gezamenlijke grens. De klokken lopen parallel en worden niet door leasevernieuwing vernieuwd. Een tekort dat in minuut 18 begint heeft in minuut 33 zijn vijftien minuten doorlopen; de lokale lease kan door haar bevestigingsmarge iets eerder aflopen. De actuele reden benoemt zonnebuffer en resterend minimum.

De gezamenlijke oudste rapporttijd is een actualiteitsgrens, geen monotone volgorde van alle afzonderlijke meters. Terugkerende geldige bijdragers mogen geen onmiddellijke stop vóór minimum of buffer veroorzaken. Bewijs uit oude of onbruikbare noodzakelijke bronnen geeft geen nieuwe toestemming. De korte lokale lease blijft standaard 300 seconden, met actuele hercontrole bij standaard 60 seconden vernieuwing.

De Wallboxreactie heeft haar eigen absolute eindtijd, standaard 240 seconden, en versoepelt alleen de softwarematige totale importgrens. Werkelijke fase-, kwartier-, batterij-, bron-, koel-, contact- en toepasselijke handmatige/native voorwaarden blijven onafhankelijk.

## 5. Configuratie, integraties en belangrijke entiteiten

Installatie-specifieke entiteiten blijven in privéconfiguratie, SolarPilot-opslag en userfiles. Nieuwe software wijzigt geen fysieke bronbinding, SG-capaciteit, native setpoint of lokale timerbevestiging op grond van een exportvermoeden. Het SG-ramingsgetal blijft bewaard; de nieuwe totaalbetekenis wordt in veldhulp en releasehandleiding expliciet vermeld.

De frontend, manifest en backend horen bij dezelfde versie. Actuele Aquarea-semantiek, bruikbare providerpoll, passende HA-rapporten en bevestigde brondekking blijven afzonderlijke voorwaarden. Een label of versienummer bewijst geen bronkwaliteit.

## 6. Belangrijke ontwerpbeslissingen + waarom

De startdrempel beschermt een nieuwe vraag met mogelijke extra opname. Hetzelfde vermogen blijven verlangen van een lopende, modulerende warmtepomp veroorzaakt onnodige UIT/AAN-cycli. Daarom controleert behoud alleen of actueel bruikbare zon aanwezig blijft; de werkelijke ruwe-P1-import bewaakt apart de dekking van de huidige opname. Een nulbudget start nog steeds een begrensde zonnebuffer zodat nacht met lage import geen eindeloze toestemming geeft. De reken- en bronfouten zijn afzonderlijk hersteld; daarnaast vraagt de gebruiker uitdrukkelijk vijftien minuten buffer om langere tijdelijke wolken te overbruggen.

Het budget kiest dynamisch bruikbare bijdragen uit niet-gelijktijdige meters. De oudste nog geldige bijdrage mag daardoor opnieuw ouder zijn dan in de vorige evaluatie. Dat is niet hetzelfde als een teruggespeeld P1-rapport of klokterugloop. Actualiteit en rapportvoortgang worden afzonderlijk bewaakt zonder de eerste tekortdeadline te verschuiven.

Vaste SG-zonnevoorrang tegenover autonoom laden verandert geen gewone toestelrangen of eigen EV-rechten. De volledige actuele EV-balans wordt vóór bestaande import en marges beoordeeld; feitelijke overname blijft afzonderlijk begrensd. Firmwaremetadata blijft informatief op dezelfde bewezen uitgang. Geen Panasonic- of Wallboxwriter wordt toegevoegd.

## 7. Automatische processen

De lokale regelcyclus, bronhercontrole, analysecollectie, historie, planner en modelopslag blijven hun eigen begrensde processen volgen. Bronwachten blokkeren alleen de betrokken onbruikbare route. Onzekere opdrachten krijgen geen blind replay.

SolarPilot uploadt geen exports automatisch en voert geen achtergrond-AI of providerupdate uit. GitHub Validate publiceert op main uitsluitend na de vijf vereiste gates. Een bestaande tag of asset wordt nooit verplaatst of overschreven.

## 8. Geheimenbeleid

Tests en browserfixtures gebruiken uitsluitend fictieve bronnen. Diagnosebestanden blijven buiten Git. Geen tokens, huisadressen, installatie-URLs, privé-entiteitslijsten, recorderbestanden of ruwe huishouddatasets in repository of release-ZIPs. Opslag en leermodellen blijven lokaal; publieke loguitvoer bevat geen geheime foutbodies of headers.

## 9. Testprocedure + actuele teststatus

De concrete nieuwe scenario’s gebruiken uitsluitend fictieve meters en de werkelijke runtime: lager modulerend zonnebedrijf, korte wolken, herstel en aanhoudende tekorten, nulbudget/nacht, herstelde niet-gelijktijdige HP/EV-bronnen en behoud van oorspronkelijke deadlines en starttijd. Bestaande handmatige, firmware-, lease-, klok-, fase-, kwartier-, batterij-, afwas-, recorder- en UI-regressies blijven gelden.

Op 30 oktober 2026 slaagde de definitieve volledige lokale suite: **9238 tests, 0 fouten, 0 overgeslagen**, in 237,83 seconden. De vijf nieuwe beta.112-bestanden bevatten 79 regressiegevallen. De echte Chromium-SG-controle slaagde op 320/390/768/1280 pixels, inclusief vijftienminutenbuffer en korte lokale toestemming. Uitleg/optiehulp, handoff, privacy/structuur, SG-opdrachtgrens, JavaScript-syntax, diffcontrole en online upstreamreview zijn groen. De actuele officiële HEADs en opgeloste stabiele tagcommits zijn ongewijzigd; guidehash `35bbe4479df8b4f4`. Zie `docs/TESTRESULTATEN_BETA112.md`. Dit is lokaal softwarebewijs; de exacte GitHub-controles en publicatiestatus blijven afzonderlijk te verifiëren.

Alle vijf commitgebonden CI-gates blijven vereist: repository/full-suite, HACS, Hassfest, echte Chromium-interacties en echte Home Assistant-startup. Geen oudere groene head als vervanging voor de nieuwe exacte controles.

## 10. Bekende problemen / beperkingen

Softwaretests bewijzen geen fysieke bekabeling, kalibratie, werkelijke SG-opname, lokale timer of Wallboxreactie. De 3000 W is een raming, geen bewezen technisch maximum. Minimumduur en wolkenbuffers kunnen tijdelijk netafname toelaten; fysieke en afzonderlijke actuele grenzen blijven gelden. De lokale lease wordt binnen tekort-/minimumdeadline en terugmeldruimte gehouden en kan daardoor standaard maximaal 20 seconden vóór de beleidsgrens aflopen. Exact 900 seconden fysieke AAN is geen belofte.

De vierminuten-Wallboxreactie betreft actieve HA-policy. De lokale eigen SG-lease is standaard 300 seconden; bij HA-uitval is fysieke UIT exact op 240 seconden niet gegarandeerd. Extern AAN krijgt geen nieuw lokaal timerrecht. Een screenshot van taak-/contactgeschiedenis alleen bewijst geen concrete stopreden; daarvoor zijn oorspronkelijke bronmetingen en beslisgeschiedenis nodig.

## 11. Concrete openstaande ontwikkeling

Controleer na normale installatie natuurlijk modulerend zonnebedrijf en korte wolken: geen contactonderbreking zolang bruikbare zon en de actuele overige voorwaarden passen. De oorspronkelijke starttijd moet blijven staan. Een concrete nieuwe onverklaarde stop vraagt een lokale analyse-export rond het moment, met echte P1/PV/HP/EV-rapporttijden, stopreden en timerbewijs. Geen geforceerde warmte- of laadproef als publicatiestap en geen privé-export publiceren.

## 12. Installatie/upgrade en rollback

Werk na publicatie via HACS bij naar beta.112, herstart Home Assistant volledig en herlaad app/browser. Behoud entry, configuratie, modellen en privéopslag. Controleer backend- en kaartversie. Deze correctie vraagt geen nieuwe instelling of herbevestiging alleen wegens de softwareupdate. Maak vooraf een volledige privé-back-up inclusief userfiles en aanvullende historie.

Rollback naar beta.111 behoudt gegevens, maar herstelt de te hoge behoudsdrempel en fout bij terugkerende oudere bronbijdragen. Daardoor kan SG opnieuw onnodig stoppen. Stel vóór rollback de tekortbuffer op een door beta.111 ondersteunde waarde in, bijvoorbeeld 300 s; die versie accepteert maximaal 600 s en kan 900 s niet valideren. Gebruik de normale versie- of pakketroute en wis integratie of opslag niet. Zie `docs/BETA112_INSTELLEN.md`.

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

Volledige suite en gerichte regressies; actuele uitleg, optiehulp en handoff; privacy/structuur; SG-opdrachtgrens; online upstreamreview; beide JS-syntaxcontroles; diffreview. Daarna vijf groene exacte PR-CI-gates. Pas vervolgens samenvoegen op main. Main herhaalt de gates en publiceert tag, HACS-ZIP, lokale ZIP en beide beta.112-release-documenten. Vergelijk alle vier gedownloade assets tegen exacte tag/bron-SHA. Geen manual-release-omweg, force-push of verplaatste oude tag.

## 15. AI-handoff

Begin bij de concrete gebruikersvraag, actuele bron en dit dossier. De gebruiker wil dat SG bij voldoende actuele zon blijft doorlopen en korte wolken overbrugt. Herstel geen startvermogensdrempel als behoudsvoorwaarde voor een lopend automatisch algemeen contact. Houd bruikbare zon groter dan nul en afzonderlijke ruwe-P1-importbuffer samen leidend, met dezelfde oorspronkelijke minimum- en tekortdeadlines. Geen toestemming uit alleen lage netafname wanneer het zonnebudget nul is.

Meetactualiteit en oorspronkelijke rapportvoortgang blijven apart. De oudste bijdragerstijd kan bij terugkerend coherent HP/EV-vermogen veranderen; dat geeft geen onmiddellijke tekortstop en evenmin nieuwe vijftien minuten. Behoud harde en native voorwaarden, fysieke handmatige UIT, onzekere opdrachten en begrensde eindtijden. Panasonic bepaalt compressorwerking.

SG behoudt vaste toegang tot bevestigde autonome Wallbox-zonnestroom; gewone toestelrangen en hun EV-rechten veranderen niet. Geen toekomstige toestelreserveringen, geen nieuwe native writer en geen fysieke instellingen wijzigen. Bestaande bewezen herstart-/firmwareroutes behouden hun voorwaarden. Verzin geen ontbrekend hardware-/timerbewijs of fysieke testresultaten. Werk bij iedere wijziging de volledige actuele uitleg en overdracht bij; publiceer nooit privébronnen.
