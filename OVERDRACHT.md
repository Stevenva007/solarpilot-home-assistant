<!-- solarpilot-handoff-schema: 1 -->
<!-- solarpilot-handoff-version: 1.0.0-beta.113 -->

# OVERDRACHT — SolarPilot

Laatst bijgewerkt: **2 november 2026**. Actuele bron: **v1.0.0-beta.113**. Bouwbasis: gepubliceerde beta.112 `7d77b08bc6f7ced6f12a5d68820a98351be69992`. Installatie en rollback: `docs/BETA113_INSTELLEN.md`. Softwarebewijs en publicatievoorwaarden: `docs/TESTRESULTATEN_BETA113.md`.

## 1. Projectdoel in gewone taal

SolarPilot verdeelt het echte huidige zonneoverschot lokaal zonder toekomstige toestelpieken te reserveren. SG/warmtepomp heeft vaste toegang tot actueel coherent bevestigd autonoom Wallbox-zonnelaadvermogen. Gewone toestelvolgorde en eigen overnamerechten blijven apart. Panasonic regelt comfort, warm water, koeling en sterilisatie zelfstandig. Een toegestaan automatisch algemeen SG-contact blijft aan zolang nog bruikbare zon en actuele overige voorwaarden aanwezig zijn. Lager moduleren vraagt geen herhaling van het startvermogen; korte wolken vallen onder de bestaande tekortbuffers.

## 2. Actuele basis

Beta.113 voegt een Marstek Venus E 3.0-monitor toe boven de bestaande Marstek-integratie in Home Assistant. Expliciete getekende AC-batterijpower, juiste tekenrichting en bevestigde meetdekking zijn nodig. SoC en fase zijn optioneel. Het profiel marstek_venus_e3 blijft hard read-only, ongeacht globale bediening of achtergebleven actuatorvelden. Geen automatische bronbinding, aanvullende UDP-/Modbus-/cloudpolling of SolarPilot-SoC-reserveprioriteit. 5,12 kWh is nominale fabrikantcapaciteit, geen gegarandeerd bruikbare AC-energie.

De ondersteunde native Marstek-entiteit wordt read-only aan haar bestaande coordinator gekoppeld. Oorspronkelijke ES-methodesuccessen, kwaliteitsvlaggen en werkelijk ontvangen AC-/SoC-velden van hetzelfde bronadres bepalen actualiteit. HA-herpublicatie of een gedeeltelijk antwoord zonder het veld verjongt geen waarde; een nieuw passend veld met onveranderde 0 W wel. Kort in geheugen bewaard veldbewijs overleeft de kortere routercache met de oorspronkelijke ontvangsttijd, hoogstens tot de ingestelde bronleeftijd, standaard 120 s. Falende bronstatus wordt meteen onbekend; gewijzigde binding/coordinator wist oud bewijs. SoC en power zijn onafhankelijk. Geen extra RPC of polling.

Werkelijke actuele ontlading wordt eenmaal van het bruikbare zonneoverschot afgetrokken. Laden zit al in P1 en wordt niet extra bij het overschot geteld. Ontbrekende of oude power is onbekend, geen nul. Een geldige vermogensbron kan zonder SoC bruikbaar blijven; de laadtoestand blijft dan afzonderlijk onbekend.

De waarschuwing na een gewone toestel-/vermogensoverdracht benoemt haar betrokken controle. Een oude herstelwacht of onzekere opdracht wordt niet automatisch gewist. Geen afleiding dat de volledige installatie fout is uit één lokale waarschuwing en geen fysieke herstelaanname uit één meting.

Alle beta.112-SG-regels blijven behouden: geen startvermogensdrempel voor lopend moduleren, afzonderlijke bruikbare-zon- en ruwe-P1-tekortklokken, standaard vijftien minuten, minimum twintig minuten, zachte importgrens 600 W en korte lease 300 s/60 s. Bestaande deadlines, handmatige grenzen en vaste SG-zonnevoorrang blijven staan. Aquarea v1.9.1 is inhoudelijk beoordeeld; de nieuwe loginbackoff verandert geen native broncontract en geeft geen verse bronrechten.

## 3. Absolute ontwerpregels

- Marstek-profiel marstek_venus_e3 is uitsluitend monitoring via bestaande HA-bronnen. Geen batterij-, modus- of reservebediening, geen extra polling en geen SoC-reserveprioriteit. Getekende AC-power met bevestigde dekking is nodig; SoC mag onbekend blijven. Geen automatische bronbinding of nulaanname bij bronverlies.
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

Installatie-specifieke entiteiten blijven uitsluitend in privéconfiguratie, SolarPilot-opslag en userfiles. De nieuwe Marstek wordt niet uit een bestaande export, apparaatnaam of softwareupdate automatisch gekoppeld. De gebruiker selecteert na installatie bewust de reeds aanwezige getekende AC-batterijvermogenssensor, richting en eventuele SoC-bron en bevestigt de AC-meetdekking. Geen woning-P1/CT, DC- of absolute vermogenswaarde.

De frontend, manifest, backend en actuele uitleg horen bij dezelfde versie. De nominale Marstek-capaciteit is fabrikantinformatie; meetbronidentiteit en polariteit moeten lokaal kloppen. Actuele Aquarea-/SDK-semantiek en oorspronkelijke HA-rapporten blijven afzonderlijk vereist. Een label of versie bewijst geen bronkwaliteit.

## 6. Belangrijke ontwerpbeslissingen + waarom

De gevraagde Marstek-koppeling is monitoring, terwijl andere generieke batterijprofielen eventueel actief regelbaar zijn. Daarom krijgt dit profiel een harde read-only-grens en geen reserve-/laadprioriteit: globale controlekeuzes of achtergebleven velden mogen het niet alsnog bedienbaar maken. De native Marstek-regelaar behoudt de werking.

Een batterijmeter is geen woningmeter. Alleen getekend AC-vermogen van de batterij zelf kan eenmaal correct ontlading van het zonnebudget onderscheiden. Laden zit al in P1. SoC is apart optioneel, zodat een ontbrekende procentwaarde een geldige vermogensmeting niet verbergt en evenmin fictieve reserve creëert.

Een lokale overdrachtwaarschuwing moet de concrete betrokken controle benoemen. Tekstverbetering is geen toestemming om oud onzeker opdrachtbewijs te wissen. De bestaande herstelvoorwaarden blijven nodig. De SG-behouds- en bronherstelcorrecties uit beta.112 worden niet teruggedraaid.

## 7. Automatische processen

De lokale regelcyclus, bronhercontrole, analysecollectie, historie, planner en modelopslag blijven hun eigen begrensde processen volgen. Bronwachten blokkeren alleen de betrokken onbruikbare route. Onzekere opdrachten krijgen geen blind replay.

SolarPilot uploadt geen exports automatisch en voert geen achtergrond-AI of providerupdate uit. GitHub Validate publiceert op main uitsluitend na de vijf vereiste gates. Een bestaande tag of asset wordt nooit verplaatst of overschreven.

## 8. Geheimenbeleid

Tests en browserfixtures gebruiken uitsluitend fictieve bronnen. Diagnosebestanden blijven buiten Git. Geen tokens, huisadressen, installatie-URLs, privé-entiteitslijsten, recorderbestanden of ruwe huishouddatasets in repository of release-ZIPs. Opslag en leermodellen blijven lokaal; publieke loguitvoer bevat geen geheime foutbodies of headers.

## 9. Testprocedure + actuele teststatus

Nieuwe regressies moeten het monitorprofiel onder normale en gemanipuleerde controlevelden read-only houden; beide powertekens, W/kW, ontbrekende SoC, nul/ontbrekende/oude bronnen, meetdekking en site-overlap toetsen; en actuele batterijflow eenmaal verwerken zonder SoC-reserveprioriteit. Waarschuwingstests behouden oude herstelwacht en onzekere opdrachten. De bestaande SG-, tijd-, firmware-, fase-, kwartier-, batterij-, afwas-, recorder- en UI-regressies blijven vereist.

Op 2 november zijn de officiële Aquarea v1.9.1-diff en ongewijzigde SDK v1.5.0 beoordeeld. De bestaande source/poll/energieperiodetests slaagden met 131 gevallen; dit is geen volledige beta.113-suite. De uitgevoerde gerichte controles en het publicatiemechanisme staan in `docs/TESTRESULTATEN_BETA113.md`. Geen oude beta.112-uitslag als nieuw bewijs.

De 116 nieuwe Marstek-regressies zijn groen: provider 28, opdrachtgrens 21, SG 12, runtime 31, configuratie/UI 21 en fasebewaking 3. Echte Chromium-interacties op vier schermbreedtes en de historie-, timer- en gemengde kaartencontroles zijn groen. De actuele uitleg heeft hash 6b26f5854ba02df7 en 371 hulpvelden; uitleg-, overdrachts- en diffcontroles zijn groen. De volledige-suiteuitslag en HA-startup worden bewezen door de Actions-runs voor de exacte PR-HEAD en de uiteindelijke main-commit, niet door een uitslag op tussentijds gewijzigde bron.

Alle vijf commitgebonden CI-gates moeten groen zijn: repository/full-suite, HACS, Hassfest, echte Chromium-interacties en echte Home Assistant-startup. Publicatie vereist de volledige suite en alle overige gates opnieuw op de uiteindelijke main-commit; vervolgens worden de vier release-assets tegen tag en bron-SHA gecontroleerd.

## 10. Bekende problemen / beperkingen

Er is geen fysieke Marstek-, SG-, warmtepomp- of laadproef uitgevoerd. Een nieuwe softwareversie bewijst geen werkelijke lokale batterijkoppeling of juiste AC-sensordekking. Nominale 5,12 kWh is geen gegarandeerde bruikbare AC-energie of reserve; fabrikantgrenzen blijven autonoom.

De Marstek-bron kan bij een gedeeltelijk geslaagde ES-statusreactie een eerder powerveld publiceren. Daarom vraagt SolarPilot afzonderlijk bewijs dat het veld werkelijk in een ontvangen antwoord stond; een ontbrekend veld vernieuwt de oorspronkelijke bewijstijd niet. Een niet-ondersteund native broncontract blijft onbekend. Ook passend ontvangen veldbewijs is geen onafhankelijke fysieke meetgarantie.

Een getekende waarde alleen bewijst niet dat het batterij-AC betreft. De bestaande HA-bronbetekenis moet bewust worden gecontroleerd. Ontbrekende noodzakelijke power blijft onbekend. Private brongegevens, identiteit en waarschuwingsincidenten worden niet als openbare fixture opgenomen.

De SG-wolkenbuffer is een policy met bestaande terugmeldmarge en onafhankelijke harde grenzen. Exact 900 seconden fysieke AAN is geen belofte; de korte lokale lease blijft 300 seconden.

## 11. Concrete openstaande ontwikkeling

Controleer na normale installatie de bewust gekozen Marstek-bronnen bij natuurlijk laden en ontladen en de afzonderlijke SoC-weergave. Controleer dat geen batterijopdracht wordt aangeboden of verzonden. Beoordeel een eventuele volgende overdrachtwaarschuwing met oorspronkelijke lokale rapporten en opdrachtbewijs; laat oude herstelwacht niet automatisch vervallen. Geen geforceerde fysieke warmte-, laad- of ontlaadproef als publicatiestap.

## 12. Installatie/upgrade en rollback

Werk na publicatie via HACS bij naar beta.113, herstart Home Assistant volledig en herlaad app/browser. Behoud entry, configuratie, modellen en privéopslag. De Marstek-monitor vraagt daarna bewuste bronkeuze en AC-bevestiging; de update zelf koppelt geen batterij. SG-instellingen blijven behouden. Maak vooraf een volledige privé-back-up.

Rollback naar beta.112 verliest de nieuwe profielondersteuning en waarschuwingstekst. Verwijder vóór rollback de alleen-uitlezen-Marstekkoppeling uit SolarPilot en controleer dat geen generieke bedienbare batterijrepresentatie achterblijft. Native Marstek blijft autonoom. Beta.112 ondersteunt dezelfde SG-buffer; beta.111 accepteert hoogstens 600 s en vraagt vóór downgrade een ondersteunde buffer zoals 300 s. Zie `docs/BETA113_INSTELLEN.md`.

## 13. Belangrijkste bestanden

- battery_fleet.py / battery_runtime.py: hard read-only Marstek-profiel, afzonderlijke SoC/powerkwaliteit en eenmaal batterijflow.
- config_flow.py: bewuste Marstek AC-bronkeuze zonder actuatorvelden.
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

Volledige suite en gerichte regressies; actuele uitleg, optiehulp en handoff; privacy/structuur; SG-opdrachtgrens; online upstreamreview; beide JS-syntaxcontroles; diffreview. Daarna vijf groene exacte PR-CI-gates. Pas vervolgens samenvoegen op main. Main herhaalt de gates en publiceert tag, HACS-ZIP, lokale ZIP en beide beta.113-release-documenten. Vergelijk alle vier gedownloade assets tegen exacte tag/bron-SHA. Geen manual-release-omweg, force-push of verplaatste oude tag.

## 15. AI-handoff

Begin bij de concrete gebruikersvraag, actuele bron en dit dossier. Marstek Venus E 3.0 is uitsluitend monitoring via bestaande HA-entiteiten. Geen native/API/pollingtoevoeging, geen automatische bronbinding, geen bedieningsrecht via algemene of achtergebleven velden en geen SolarPilot-SoC-reserveprioriteit. AC-batterijpower met richting is verplicht; SoC optioneel. Trek actuele ontlading eenmaal af, tel laden niet nogmaals bij P1 op en verzin geen nul bij bronverlies.

Benoem lokale overdrachtwaarschuwingen concreet, maar wis geen onzekere opdracht of oude herstelwacht zonder passend bestaand herstelbewijs. Publiceer geen privébronidentiteit, export of werkelijk huishoudincident.

Behoud alle beta.112-SG-regels, vijftienminutenbuffer, vaste zonnevoorrang, oorspronkelijke deadlines en korte lokale lease. Het inhoudelijk beoordeelde Aquarea-loginbackoff geeft geen nieuwe bronkwaliteit en vraagt geen automatische providerupgrade. Werk iedere wijziging bij in actuele uitleg en overdracht. Claims over suite, CI, publicatie en fysieke installatie blijven afzonderlijk bewezen.
