<!-- solarpilot-handoff-schema: 1 -->
<!-- solarpilot-handoff-version: 1.0.0-beta.114 -->

# OVERDRACHT — SolarPilot

Laatst bijgewerkt: **2 november 2026**. Actuele bron: **v1.0.0-beta.114**. Bouwbasis: gepubliceerde beta.113 `703fc22d447fed5263eb2fbc3eabbccfd23ac940`. Installatie en rollback: `docs/BETA114_INSTELLEN.md`. Softwarebewijs en publicatievoorwaarden: `docs/TESTRESULTATEN_BETA114.md`.

## 1. Projectdoel in gewone taal

SolarPilot verdeelt het echte huidige zonneoverschot lokaal zonder toekomstige toestelpieken te reserveren. SG/warmtepomp heeft vaste toegang tot actueel coherent bevestigd autonoom Wallbox-zonnelaadvermogen. Gewone toestelvolgorde en eigen overnamerechten blijven apart. Panasonic regelt comfort, warm water, koeling en sterilisatie zelfstandig. Een toegestaan automatisch algemeen SG-contact blijft aan zolang nog bruikbare zon en actuele overige voorwaarden aanwezig zijn. Lager moduleren vraagt geen herhaling van het startvermogen; korte wolken vallen onder de bestaande tekortbuffers.

## 2. Actuele basis

Beta.114 voorkomt dat een actief Marstek-monitorprofiel zonder expliciete AC-meetbevestiging wordt opgeslagen. Een bekende verkeerde native meetsoort of strijdige bekende tekenrichting krijgt een veldfout. Bestaande onbevestigde koppelingen blijven zichtbaar onvoltooid; de softwareupdate bevestigt of vervangt geen bron automatisch.

De batterijrij, algemene bronmelding, SG en analyse-export benoemen de concrete oorzaak. BatteryFleetManager.source_status() geeft valid/code/reason/battery_id/native_key/expected_native_key; source_problem() is de stringwrapper. De rij gebruikt source_code en reason. Ontbrekende bevestiging, verkeerde native bronbetekenis, onbruikbare provider en ontbrekend actueel veldbewijs blijven afzonderlijk herkenbaar. Veilige metadata bevat alleen bekende native veldlabels, geen IP-adres, MAC-adres, unieke apparaatidentiteit of ruwe antwoordcache.

De bestaande native broncontrole blijft de werkelijk gekoppelde entiteit/coordinator, geslaagde ES-methodestatus, kwaliteit, passend ontvangen AC-/SoC-veld en oorspronkelijke ontvangsttijd vereisen. HA-herpublicatie en gedeeltelijke antwoorden zonder het veld verjongen niets. Begrensd bewaard bewijs houdt de oorspronkelijke termijn, standaard maximaal 120 seconden; gewijzigde binding/coordinator wist eerder bewijs. Geen extra RPC of polling.

Basislastleren weigert een ingeschakelde batterijvloot niet meer alleen wegens haar aanwezigheid. Alle actieve profielen moeten afzonderlijk volledige expliciet bevestigde getekende AC-metingen leveren. De balans is net + PV + getekend batterijvermogen − gemeten Wallbox − gemeten beheerde lasten. Laden is negatief; ontladen positief. Oorspronkelijke brontijden blijven nodig, voor deze leerwaarneming hoogstens 120 seconden oud en onderling passend. Templates, schattingen, restored, dubbele rollen en onbekende centrale-meteroverlap geven geen leerbewijs. Generieke profielen zonder AC-bevestiging blijven onbekend en behouden overige bestaande voorwaarden. Marstek mag onbekende SoC hebben bij afzonderlijk bewezen power. Geen retroactieve historiecorrectie of realtime vrij vermogen uit een model.

De uitsluitend uitleesbare Marstek-grens, vijftienminuten-SG-buffers, minimumduur, oorspronkelijke deadlines, korte lease, vaste SG-zonnevoorrang en overige opdrachtgrenzen blijven behouden. Geen PV-aftrek of huishoudinstelling wordt automatisch uit een analyse toegepast. De online Aquarea-/SDK-hercontrole bevestigt ongewijzigde beoordeelde bronnen: v1.9.1 en v1.5.0.

## 3. Absolute ontwerpregels

- Een actief Marstek-profiel vraagt bewuste AC-bevestiging vóór opslaan. Een bestaande onbevestigde bron wordt niet automatisch bevestigd, vervangen of als nul gelezen. Concrete bronredenen geven geen nieuwe meting of controlerecht.
- Basislast-fleetcorrectie vereist alle actieve afzonderlijke bevestigde AC-metingen met oorspronkelijke tijd, kwaliteit en eenduidige dekking. Geen gedeeltelijke som, onbekende overlap, afgeleide bron of model als actuele vrije ruimte.
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

Installatie-specifieke entiteiten blijven uitsluitend in privéconfiguratie, SolarPilot-opslag en userfiles. Gebruik bij een batterijbronmelding Batterijbron controleren en pas het bestaande profiel onder Batterijen aan. Kies de werkelijk getekende AC-batterijvermogenssensor en juiste richting en bevestig na controle de meetdekking. Maak geen dubbel profiel voor dezelfde bron.

Bij de ondersteunde native Marstek-koppeling is Vermogen netaansluiting (ongrid_power) de batterij-AC-bron met discharge_positive. CT em_total_power en DC battery_power zijn andere meetrollen. Een model- of apparaatnaam alleen bewijst geen native veld. Een onbekende offline bron wordt niet uit haar naam goedgekeurd. SoC blijft afzonderlijk optioneel.

De frontend, manifest, backend en actuele uitleg horen bij dezelfde versie. De AC-bevestiging is geen opdrachttoestemming en maakt onbruikbaar veldbewijs niet actueel. Nominale 5,12 kWh blijft fabrikantinformatie; fabrikantgrenzen en de autonome Marstek-regeling blijven bestaan.

## 6. Belangrijke ontwerpbeslissingen + waarom

Een onvoltooide actieve batterijbron kan de gedeelde energiebalans onbruikbaar maken. Een algemene net-/batterijfout vertelt niet welke handeling helpt. Daarom wordt de concrete bronoorzaak genoemd en wordt een nieuwe onvoltooide actieve koppeling bij opslaan afgewezen. Bestaande onvoltooide koppelingen houden hun bewuste herstelactie; de software mag hun ontbrekende bevestiging niet verzinnen.

Een betrouwbare batterijmeting mag het basislastleren niet alleen wegens aanwezigheid van een vloot blokkeren. Volledig afzonderlijk gevalideerde AC-metingen maken een onderbouwde balans mogelijk, inclusief laden als negatieve bijdrage. Deelmetingen, afgeleide waarden of onbekende overlap blijven onvoldoende. De correctie is leerbewijs, geen actueel regelbudget of nieuwe toestemming.

De bronintegratie kan eerdere waarden blijven publiceren. Daarom blijven native veldbewijs en oorspronkelijke tijden onafhankelijk van de nieuwe diagnostiek vereist. Marstek krijgt geen writer of SoC-reserveprioriteit. De SG-regels uit beta.112 en de read-only-grens uit beta.113 worden niet versoepeld.

## 7. Automatische processen

De lokale regelcyclus, bronhercontrole, analysecollectie, historie, planner en modelopslag blijven hun eigen begrensde processen volgen. Bronwachten blokkeren alleen de betrokken onbruikbare route. Onzekere opdrachten krijgen geen blind replay.

SolarPilot uploadt geen exports automatisch en voert geen achtergrond-AI of providerupdate uit. GitHub Validate publiceert op main uitsluitend na de vijf vereiste gates. Een bestaande tag of asset wordt nooit verplaatst of overschreven.

## 8. Geheimenbeleid

Tests en browserfixtures gebruiken uitsluitend fictieve bronnen. Diagnosebestanden blijven buiten Git. Geen tokens, huisadressen, installatie-URLs, privé-entiteitslijsten, recorderbestanden of ruwe huishouddatasets in repository of release-ZIPs. Opslag en leermodellen blijven lokaal; publieke loguitvoer bevat geen geheime foutbodies of headers.

## 9. Testprocedure + actuele teststatus

Nieuwe regressies toetsen een letterlijke AC-bevestiging en bekende native meetsoort/tekenrichting in het formulier, met behoud van opties wanneer opslaan wordt geweigerd. Diagnosetests toetsen concrete reden en veilige veldmetadata in batterijoverzicht, globale melding, SG en export, zonder nieuwe meetgeldigheid of bediening.

Basislasttests toetsen volledige afzonderlijke fleetmetingen, getekend laden/ontladen, gemengde profielen, oorspronkelijke native ontvangsttijd en maximaal 120 seconden actualiteit, bronalignment, templates/estimated/restored, ontbrekende leden, dubbele rollen en centrale-meteroverlap. Marstek-SoC is onafhankelijk; generieke profielen houden hun bestaande voorwaarden en hebben voor deze fleetcorrectie expliciete AC-bevestiging nodig.

De actuele Aquarea-/SDK-HEADs, stabiele releases en opgeloste tagcommits zijn op 2 november 2026 opnieuw online gecontroleerd en identiek aan het inhoudelijk beoordeelde beta.113-checkpoint. Er is geen nieuwe upstreamdiff te verwerken. Zie docs/UPSTREAM_BETA114.md en het machineleesbare checkpoint.

Passende regressies, echte Chromium-interacties, canonieke uitleg/optiehulp, handoff, privacy/structuur, commandogrenzen, JS-syntax en volledige testsuite worden gecontroleerd. De uitgevoerde resultaten en het publicatiemechanisme staan in docs/TESTRESULTATEN_BETA114.md. De volledige-suiteuitslag en HA-startup worden bewezen door Actions-runs voor de exacte PR-HEAD en uiteindelijke main-commit; een oudere groene head is geen vervanging.

Alle vijf commitgebonden Validate-gates moeten groen zijn vóór samenvoegen. Main herhaalt de volledige suite en alle overige gates vóór automatische publicatie. Daarna worden de vier gedownloade release-assets tegen de exacte tag en bron-SHA gecontroleerd.

## 10. Bekende problemen / beperkingen

Een softwareupdate bevestigt geen eerder onbevestigde AC-bron en bewijst geen gemaakte lokale bronkoppeling of fysieke kalibratie. Na het herstellen van één bronoorzaak kan een volgende oorzaak zichtbaar worden. Een vinkje alleen bewijst geen juiste native meetsoort, bereikbare provider of actueel ontvangen veld. Niet-ondersteunde broncontracten blijven onbekend.

Een generiek profiel zonder expliciete AC-bevestiging levert geen nieuwe basislast-fleetcorrectie. Ontbrekende of gedeeltelijke bronnen worden niet als nul geleerd. Oudere historie krijgt geen nieuw meetbewijs. Er worden geen PV-factor, meetbinding, SoC-reserve of apparaatinstellingen uit een analyse automatisch gewijzigd.

Geen fysieke batterij-, SG-, warmtepomp- of laadproef uitgevoerd. Nominale 5,12 kWh is geen gegarandeerde bruikbare AC-energie of reserve. Een vijftienminutenwolkenbuffer geldt binnen bestaande geldige meetvoorwaarden en onafhankelijke harde grenzen; ontbrekende noodzakelijke brondata krijgen geen vijftien minuten fictieve toestemming. Exact 900 seconden fysieke AAN is geen belofte. De korte lokale lease blijft 300 seconden.

Private brongegevens, exportidentiteit, meetreeksen en werkelijke huishoudincidenten worden niet als openbare fixture opgenomen. Veilige native veldlabels zijn diagnostiek en geen ruwe provider- of netwerkdata.

## 11. Concrete openstaande ontwikkeling

Controleer na gewone installatie eventuele genoemde batterijbronoorzaken via het bestaande profiel. Bevestig de AC-meetdekking alleen na werkelijke broncontrole en bekijk bij natuurlijk laden/ontladen of bronkwaliteit en richting kloppen. Controleer dat een onbruikbare noodzakelijke bron onbekend blijft en geen bediening krijgt.

Nieuwe volledige geldige fleetmetingen mogen toekomstige basislastwaarnemingen onder de bestaande bronvoorwaarden ondersteunen. Controleer hun meetdekking zonder oude historie, bronkwaliteit of huishoudinstellingen achteraf te verzinnen. Geen geforceerde fysieke warmte-, laad- of ontlaadproef als publicatiestap.

## 12. Installatie/upgrade en rollback

Werk na publicatie via HACS bij naar beta.114, herstart Home Assistant volledig en herlaad app/browser. Behoud entry, configuratie, modellen en privéopslag. Gebruik bij een concrete batterijbronmelding Batterijbron controleren en pas het bestaande profiel bewust aan. De update bevestigt of vervangt geen bron. Maak vooraf een volledige privé-back-up.

Rollback naar beta.113 behoudt het Marstek-profiel en de vijftienminuten-SG-buffer, maar mist de nieuwe formuliervalidatie, concrete bronredenen en basislast-fleetcorrectie. Een algemene meetmelding kan terugkomen; wis geen configuratie of opslag om haar te verbergen. Terug naar beta.112 of ouder vraagt bovendien de profiel- en buffercompatibiliteitsstappen uit BETA113_INSTELLEN.md. Zie docs/BETA114_INSTELLEN.md.

## 13. Belangrijkste bestanden

- battery_fleet.py / battery_runtime.py: read-only Marstek, afzonderlijke SoC/powerkwaliteit en concrete veilige bronstatus.
- learning_hub.py: volledige bevestigde AC-fleetcorrectie voor basislastleren met oorspronkelijke bronnen en overlapcontrole.
- config_flow.py: expliciete AC-bevestiging en bekende native bron-/tekenvalidatie zonder actuatorvelden.
- runtime.py en engine.py: actuele lastverdeling, geserialiseerde opdrachten en finale bron-/elektrische controles.
- heatpump_budget.py: apart werkelijk restoverschot, compleet gemeten HP-bijdrage en voorwaardelijke EV-bijdrage; mogelijke SG-toename uit de totaalraming.
- priority_board.py / wallbox_priority.py: gewone centrale/tijdelijke keuzes en kandidaat-eigen rechten; vaste SG-zonnevoorrang en SG uitgesloten van tijdelijke Wallboxvoorkeur.
- dishwasher_priority.py: echte startvoorwaarden en ononderbreekbare cyclusbescherming zonder toekomstige piekreserve.
- sg_boost.py / sg_transport.py: afzonderlijke bruikbare-zonherstart, oorspronkelijke deadlines, eigendom, lokale SG-grens en firmwarediagnose.
- sg_wallbox_transfer.py: oorspronkelijk episodeplafond, absolute eindtijd, herstelbewijs en conservatieve herstart.
- analysis_export.py: oorspronkelijke brontelemetrie en begrensde SG-/Wallboxovergangen; geen aftelseconde-eventstroom of nieuw controlrecht.
- sensor.py: compacte Wallbox-recorderattributen met volledige actuele status.
- frontend/solar-pilot-card.js: concrete bronreden, Batterijbron controleren, actuele metingen en bestaande status-/overdrachtdiagnostiek.
- current_guide.py / option_help.py: canonieke actuele uitleg en veldhulp met gegenereerde mirrors.

## 14. Release-checklist

Volledige suite en gerichte regressies; actuele uitleg, optiehulp en handoff; privacy/structuur; SG-opdrachtgrens; online upstreamreview; beide JS-syntaxcontroles; diffreview. Daarna vijf groene exacte PR-CI-gates. Pas vervolgens samenvoegen op main. Main herhaalt de gates en publiceert tag, HACS-ZIP, lokale ZIP en beide beta.114-release-documenten. Vergelijk alle vier gedownloade assets tegen exacte tag/bron-SHA. Geen manual-release-omweg, force-push of verplaatste oude tag.

## 15. AI-handoff

Begin bij de concrete gebruikersvraag, actuele bron en dit dossier. Beta.114 herstelt de onduidelijke route van onvoltooide batterijconfiguratie en het onvoorwaardelijke fleet-verbod in basislastleren. Een actief Marstek-profiel vraagt bewuste AC-bevestiging bij opslaan; bestaande onbevestigde koppelingen worden niet automatisch bevestigd of vervangen. Benoem concrete bronoorzaken en neem alleen veilige bekende native veldlabels in diagnostiek op.

Gebruik voor nieuwe basislast-fleetcorrectie alleen alle actieve afzonderlijke volledige expliciet bevestigde getekende AC-metingen met oorspronkelijke tijden en eenduidige dekking. Behoud bronalignment, maximaal 120 seconden actualiteit en uitsluiting van templates/estimated/restored/dubbele rollen/unknown overlap. Marstek-SoC blijft optioneel; generieke voorwaarden blijven gelden. Geen deelmeting als nul, historiecorrectie of actuele vrije ruimte uit een model.

Marstek blijft uitsluitend monitoring via bestaande HA-entiteiten. Geen native/API/pollingtoevoeging, actuatorrecht, automatische bronbinding of SoC-reserveprioriteit. Panasonic en Wallbox blijven read-only. Behoud alle SG-regels, vijftienminutenbuffers, vaste zonnevoorrang, oorspronkelijke deadlines en korte lokale lease. Wis geen onzekere opdracht of herstelwacht op grond van een analyse.

Werk iedere wijziging bij in canonieke uitleg, optiehulp en overdracht. Publiceer geen privébronidentiteit of huishouddataset. Claims over suite, exacte CI, publicatie en fysieke installatie blijven afzonderlijk bewezen.
