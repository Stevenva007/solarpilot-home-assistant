<!-- solarpilot-handoff-schema: 1 -->
<!-- solarpilot-handoff-version: 1.0.0-beta.110 -->

# OVERDRACHT — SolarPilot

Laatst bijgewerkt: **27 oktober 2026**. Actuele bron: **v1.0.0-beta.110**. Bouwbasis: gepubliceerde beta.109 `ef1572f`. Installatie en rollback: `docs/BETA110_INSTELLEN.md`. Softwarebewijs en publicatievoorwaarden: `docs/TESTRESULTATEN_BETA110.md`.

## 1. Projectdoel in gewone taal

SolarPilot verdeelt het echte huidige zonneoverschot lokaal tussen flexibele toestellen en optionele SG-zonneboost. De centraal geplaatste autonome Wallbox gebruikt volgens de effectieve volgorde het resterende overschot. Panasonic regelt zelfstandig comfort, warm water, koeling en sterilisatie. Plannen en ramingen ondersteunen beslissingen; actuele metingen bepalen wat fysiek mag.

## 2. Actuele basis

Beta.110 trekt toekomstig afwas-, thermostaat- of ander toestelverbruik niet meer af van het actuele zonnebudget of de actuele elektrische ruimte. P1 bevat het werkelijke huidige huisverbruik al. Wachtende aanvragen houden geen vermogen apart; de centrale volgorde bepaalt welke werkelijk startklare passende kandidaat de volgende opdracht krijgt. Een lopende beschermde cyclus blijft ononderbreekbaar.

`expected_power_w` betekent vanaf deze expliciete beleidswijziging geraamd totaalvermogen bij SG, standaard 3000 W. Bestaande getallen blijven behouden. Alleen een complete verse exclusieve warmtepompmeting wordt eenmaal afgetrokken om de mogelijke extra opname te bepalen: `max(0, totaalraming - huidige opname)`. Ontbrekende, oude, onvolledige of overlappende meting behoudt de volle totaalraming. Dit is geen bewezen fysiek maximum. De vaste ingestelde huisbuffer, filtering, batterijcorrectie en afzonderlijke startdrempel blijven behouden.

De eerdere ontwikkelde SG-/Wallboxreactie wordt in deze actuele release opgenomen. SG vóór een lager geplaatste bevestigde autonome zonne-Wallbox mag haar betrouwbaar gemeten zonnevermogen gebruiken terwijl de Wallbox later terugregelt. Alleen de totale softwarematige netgrens krijgt een beperkte uitzondering. De episode heeft één oorspronkelijk plafond en absolute eindtijd, standaard 240 seconden. De gewone 600 W/300 s wolkentimer loopt parallel op ruwe P1. De beta.109-recordercorrectie blijft behouden.

Een firmwareversiewijziging alleen is informatief en blokkeert geen SG-aanvraag. Dezelfde fysieke Shelly en uitgang worden automatisch opnieuw gecontroleerd op actuele identiteit, ondersteunde configuratie en beschikbaar timerbewijs; geldige ingebruiknamebevestigingen blijven behouden. Een oude firmware_changed-blokkade kan bij een verse passende uitlezing met bewaard bewijs van dezelfde uitgang automatisch herstellen. Een werkelijk andere fysieke koppeling of onbruikbare configuratie of timer houdt haar eigen actuele voorwaarden. De diagnose bewaart de eerste beschikbare vergelijking en detectie; oudere ontbrekende gegevens blijven onbekend.

## 3. Absolute ontwerpregels

- Panasonic-entiteiten en Wallbox blijven read-only. Alleen de bewust toegewezen bestaande fysieke SG-uitgang heeft haar aparte gecontroleerde schrijfroute. Geen native temperatuur-, programma-, heater-, AUTO/OFF-, laad- of tweede-Shelly-opdracht toevoegen.
- Actuele P1 bevat alle huidige lasten. Geen toekomstig piekvermogen of ongebruikte nominale toestelvraag als extra reserve aftrekken. De ingestelde vaste huisbuffer is een afzonderlijke expliciete marge. Ontbrekend toestelvermogen is onbekend, geen gemeten nul.
- Nieuwe opdrachten blijven geserialiseerd. Pending, opslagbewijs, echte terugmelding, stabilisatietijd en nieuwe oorspronkelijke netmeting blijven nodig. Een opgeslagen intentie is geen fysiek bewezen verbruik of vrij vermogen. Onzekere eigen SG-opdrachten behouden hun afzonderlijke herstelcontract.
- Alleen complete verse exclusieve HP-meting mag de resterende mogelijke SG-toename verlagen. Deelmetingen, restored, oude of overlappende bronnen geven geen credit. Een wijziging van raming mag nooit meetdekking verzinnen.
- Centrale volgorde, bewuste deelname, vraag, interlocks, minimumtijden en bestaande toestemming blijven gelden. Een wachtende aanvraag reserveert niets; een werkelijk startklare passende hogere kandidaat krijgt de volgende opdracht. Een lopende afwasbeurt wordt nooit gestopt om SG of een ander toestel te starten.
- Alleen met SG vóór Auto laden telt actuele coherente gemeten laadruimte uit een bevestigde autonome zonnelaadsessie voor SG mee. Dit blijft voorwaardelijk EV-vermogen, apart van echte P1-injectie. Handmatige, onbekende, oude, ontbrekende of fysiek tegenstrijdige laadgegevens geven geen EV-credit.
- De tijdelijke SG-/Wallboxuitzondering betreft uitsluitend de softwarematige totale importgrens. Ruwe P1, actuele afzonderlijke fasegrenzen, resterend kwartierbudget, batterijontlading, bronactualiteit, koeling, contact, eigendom en harde sessiegrens blijven onafhankelijk. Relevante bronnen worden ook na awaits opnieuw gelezen.
- De episode krijgt één oorspronkelijke absolute eindtijd en eerste plafond. Uitlezen, nieuwe laadrapporten, leasevernieuwing en herstart verlengen die niet. Nieuw herstel vraagt lage ruwe P1 gedurende de bevestigingstijd en minstens twee nieuwe rapporten; rond de softwaregrens schommelen geeft geen nieuwe tijd. Bronverlies trekt de uitzondering in.
- Een bewezen firmware-update/Shelly-herstart naar UIT binnen een bestaande eigen SG-toestemming veroorzaakt geen blijvende handmatige-UIT-pauze. Vereis passend oorspronkelijk eigen sessiebewijs, dezelfde hardware/binding, actuele geldige configuratie en tijd-/uptimebewijs. Alleen de gewone actuele zonnebeoordeling met startstabiliteit krijgt opnieuw gelegenheid, met behoud van oorspronkelijke sessiegrens en tijdelijke handmatige eindtijd. Geen blind ON-replay, geen nieuwe sessie en zonder bewijs geen wegredeneren van fysieke handmatige UIT.
- Extern SG-AAN geeft geen eigendom of nieuw timerrecht. De oorspronkelijke vijftien minuten blijven na herstart staan. Voortzetting vraagt actuele voorwaarden en bevestiging van de korte lokale timer, zonder noodzakelijke UIT-puls. Fysieke handmatige UIT blijft beschermd; onzekere opdrachten worden niet blind herhaald.
- Een firmwareversiewijziging alleen mag geen blokkade of handmatige herbevestiging veroorzaken. Controleer dezelfde fysieke uitgang en actuele configuratie/timer automatisch; herstel de oude firmware-only-latch uitsluitend met passend bewaard hardwarebewijs en verse geldige uitlezing. Een echt ander toestel, andere fysieke koppeling of onbruikbare timer is geen firmware-only-geval. Ontbrekend bewijs en diagnostiek geven geen actuatorbevoegdheid.
- Afwasmeteractiviteit is presentatie/historie, geen START-bevestiging, ticketverbruik, programma-einde of volledig cyclusleerbewijs. Energie wordt niet over reset, gat, herstart, bronwissel of middernacht geïnterpoleerd.
- Ontbrekende, restored, boolean, niet-eindige, toekomstige of beschadigde gegevens worden geen actuele nul. Uitlezen en formatteren vernieuwen geen oorspronkelijke meettijd. Oude historie behoudt haar oorspronkelijke bronrechten en betekenis.
- Onleesbare bestaande opslag wordt niet stil overschreven. Geen privé-export, huisidentiteit, bronbinding of geheim in publieke Git-/releasebestanden.
- Iedere release werkt de canonieke actuele uitleg, optiehulp, changelog en dit dossier bij. Controleer actuele officiële upstream-HEADs en stabiele tagcommits. Publicatie vraagt alle vijf commitgebonden gates en de exacte assetvergelijking.

## 4. Actuele werking

De runtime leest P1/PV, eventuele batterij- en fasegegevens en toestelbronnen. Echt restoverschot, reeds gebruikt compleet gemeten HP-vermogen en voorwaardelijk overdraagbaar EV-vermogen blijven apart. Toestelramingen bepalen een nieuwe start of plan, maar reserveren geen toekomstige piek naast het actuele verbruik in P1.

De planner mag toekomstige slots vergelijken; een plan geeft geen fysiek startrecht en houdt geen actuele zonnepot vast. Voor iedere echte opdracht gelden opnieuw actuele bronnen, ruimte en apparaatvoorwaarden. De afwasroute behoudt eenmalige appvrijgave, native interlocks, deadline en bescherming van een lopend programma.

SG gebruikt haar afzonderlijke lokale lease, minimumduur, wolkenbuffer, herbeoordelingsregels en hard sessiemaximum. De gewone wolkenbuffer is standaard 600 W/300 s op ruwe P1. Een geldige begrensde Wallboxreactie kan uitsluitend de softwarematige totale netgrens tijdelijk versoepelen; fase-, kwartier-, batterij-, bron- of andere actuele voorwaarden kunnen eerder vrijgeven. Na afloop geldt de gewone totale netgrens weer.

## 5. Configuratie, integraties en belangrijke entiteiten

Installatie-specifieke entiteiten blijven in privéconfiguratie, SolarPilot-opslag en userfiles. Nieuwe software wijzigt geen fysieke bronbinding, SG-capaciteit, native setpoint of lokale timerbevestiging op grond van een exportvermoeden. Het SG-ramingsgetal blijft bewaard; de nieuwe totaalbetekenis wordt in veldhulp en releasehandleiding expliciet vermeld.

De frontend, manifest en backend horen bij dezelfde versie. Actuele Aquarea-semantiek, bruikbare providerpoll, passende HA-rapporten en bevestigde brondekking blijven afzonderlijke voorwaarden. Een label of versienummer bewijst geen bronkwaliteit.

## 6. Belangrijke ontwerpbeslissingen + waarom

Een lopend toestel kan later opnieuw verwarmen. Zijn volledige mogelijke piek nogmaals van het gemeten actuele overschot aftrekken hield echter bruikbare zon tegen. De nieuwe policy gebruikt echte huidige P1 en houdt geen hypothetische toekomstige toestelvraag apart. Latere echte pieken worden via nieuwe metingen, actuele limieten en bestaande stopbuffers behandeld. Dit kan tijdelijk import geven en belooft geen nulimport.

Een SG-raming als volledige extra last telde bestaand warmtepompverbruik tweemaal. De nieuwe totaalraming trekt alleen aantoonbaar compleet actueel HP-vermogen af bij het toetsen van de resterende toename. Zonder dat bewijs blijft de hele raming gelden.

De autonome Wallbox kan trager terugregelen nadat SG zon overneemt. Daarom bestaat een afzonderlijke begrensde software-uitzondering met oorspronkelijke eindtijd en nieuw herstelbewijs. Een langere gewone wolkenbuffer vervangt die regeling niet. De reactie-uitzondering is geen fysieke netcapaciteit of bewezen EV-reactie.

Een firmwareversie is geen identiteit van een ander fysiek toestel. Een versiewijziging wordt daarom apart van echte hardware-/uitgangswijziging behandeld en blijft informatief. Bestaande ingebruikname wordt voor dezelfde bewezen fysieke uitgang behouden; een oude firmware-only-blokkade kan na actuele verificatie automatisch verdwijnen. Ondersteunde configuratie en betrouwbaar lokaal timerbewijs blijven vereist. De diagnose bewaart de eerste beschikbare vergelijking; oude ontbrekende gegevens worden niet achteraf bewezen verklaard.

## 7. Automatische processen

De lokale regelcyclus, bronhercontrole, analysecollectie, historie, planner en modelopslag blijven hun eigen begrensde processen volgen. Bronwachten blokkeren alleen de betrokken onbruikbare route. Onzekere opdrachten krijgen geen blind replay.

SolarPilot uploadt geen exports automatisch en voert geen achtergrond-AI of providerupdate uit. GitHub Validate publiceert op main uitsluitend na de vijf vereiste gates. Een bestaande tag of asset wordt nooit verplaatst of overschreven.

## 8. Geheimenbeleid

Tests en browserfixtures gebruiken uitsluitend fictieve bronnen. Diagnosebestanden blijven buiten Git. Geen tokens, huisadressen, installatie-URLs, privé-entiteitslijsten, recorderbestanden of ruwe huishouddatasets in repository of release-ZIPs. Opslag en leermodellen blijven lokaal; publieke loguitvoer bevat geen geheime foutbodies of headers.

## 9. Testprocedure + actuele teststatus

De definitieve beta.110-bron slaagt lokaal met 8989 tests zonder fouten of skips, waaronder 280 nieuwe regressies. De volledige loop eindigde op 100% met exitcode 0 en de verzamelde testlijst bevestigt hetzelfde aantal. Een onafhankelijke adversarial review vond geen materiële fout. Zie docs/TESTRESULTATEN_BETA110.md. De gerichte regressies omvatten echte huidige lastverdeling, SG-totaalraming, prioriteitskandidaten, late bronwijzigingen, beschermde cycli, fingerprintdiagnose en begrensde EV-reactie. De recordercorrectie uit beta.109 blijft onder regressietest.

De aftelregressie gebruikt een vaste hele seconde om zwevendekomma-afronding tussen Python en JavaScript uit de test te houden; productietijden en strikte vervalcontroles zijn ongewijzigd.

Controleer volledige suite, actuele uitleg/optiehulp, handoff, repositoryprivacy/structuur, SG-opdrachtgrens, beide JavaScript-syntaxcontroles en online upstreamreview. Alle vijf commitgebonden CI-gates blijven verplicht: repository/full-suite, HACS, Hassfest, Chromium en echte Home Assistant-startup. Geen lokaal ontbrekende browser als reden voor een remote skip.

## 10. Bekende problemen / beperkingen

Softwaretests certificeren geen fysieke bekabeling, kalibratie, werkelijke SG-opname, lokale timer of Wallboxreactie. De 3000 W is een raming, geen bewezen technisch maximum. Nieuwe actuele pieken kunnen tijdens minimumduur of stopbuffer tijdelijke import geven. De software-uitzondering verhoogt geen fysieke aansluitcapaciteit.

Het vierminutenvenster betreft actieve HA-policy. De bestaande lokale eigen SG-lease is standaard 300 seconden; bij HA-uitval is fysieke UIT exact op 240 seconden niet gegarandeerd. Extern AAN krijgt geen nieuw lokaal timerrecht. Oude foutregistraties kunnen de oorspronkelijke fingerprintvergelijking missen; nieuwe versies vullen dat verleden niet in.

## 11. Concrete openstaande ontwikkeling

Beoordeel na normale installatie de natuurlijke SG-/Wallboxreactie met oorspronkelijke brontelemetrie en actuele P1. Voer geen geforceerde warmte- of laadproef uit als publicatiestap. Een firmwareversiemelding vraagt automatische actuele verificatie van dezelfde fysieke uitgang; een echt gewijzigd toestel of onbruikbare koppeling/timer houdt zijn afzonderlijke controlevoorwaarden. PV-voorspelling en ontbrekende exclusieve meters blijven eigen analyseonderwerpen.

## 12. Installatie/upgrade en rollback

Update via HACS naar beta.110, herstart Home Assistant volledig en herlaad app/browser. Controleer beide versies, de effectieve volgorde, SG-totaalraming en concrete wachtreden. Maak vooraf een volledige privéback-up inclusief userfiles en aanvullende historie. Een firmware-only-blokkade herstelt automatisch zodra verse controle en passend bewaard bewijs dezelfde fysieke uitgang en bruikbare configuratie/timer bevestigen; een andere fysieke koppeling erft dat bewijs niet.

Rollback naar beta.109 behoudt recorderfix en eerdere centrale SG-coherentie, maar mist actuele lastverdeling, totaalraming, begrensde Wallboxreactie en uitgebreidere diagnose. De oude versie leest expected_power_w opnieuw als extra vraag en kan toekomstige afwaspieken reserveren. Geef een eigen SG-aanvraag waar betrouwbaar mogelijk veilig vrij en behoud entry, configuratie en gegevens. Zie docs/BETA110_INSTELLEN.md.

## 13. Belangrijkste bestanden

- runtime.py en engine.py: actuele lastverdeling, geserialiseerde opdrachten en finale bron-/elektrische controles.
- heatpump_budget.py: apart werkelijk restoverschot, compleet gemeten HP-bijdrage en voorwaardelijke EV-bijdrage; mogelijke SG-toename uit de totaalraming.
- priority_board.py: effectieve centrale volgorde en werkelijk startklare passende kandidaten.
- dishwasher_priority.py: echte startvoorwaarden en ononderbreekbare cyclusbescherming zonder toekomstige piekreserve.
- sg_boost.py / sg_transport.py: oorspronkelijke deadlines, eigendom, lokale SG-grens en wijzigingsdiagnose.
- sg_wallbox_transfer.py: oorspronkelijk episodeplafond, absolute eindtijd, herstelbewijs en conservatieve herstart.
- analysis_export.py: oorspronkelijke brontelemetrie en begrensde SG-/Wallboxovergangen; geen aftelseconde-eventstroom of nieuw controlrecht.
- sensor.py: compacte Wallbox-recorderattributen met volledige actuele status.
- frontend/solar-pilot-card.js: actuele reden, geraamde totale/extra opname, wijzigingsdiagnose en geldige overdrachtafteller.
- current_guide.py / option_help.py: canonieke actuele uitleg en veldhulp met gegenereerde mirrors.

## 14. Release-checklist

Volledige suite en passende regressies; actuele uitleg, optiehulp en handoff; privacy/structuur; SG-opdrachtgrens; online upstreamreview; beide JS-syntaxcontroles; diffreview. Daarna vijf groene exacte PR-CI-gates. Pas vervolgens samenvoegen op main. Main herhaalt de gates en publiceert tag, HACS-ZIP, lokale ZIP en beide beta.110-release-documenten. Vergelijk alle vier gedownloade assets tegen exacte tag/bron-SHA. Geen manual-release-omweg, force-push of verplaatste oude tag.

## 15. AI-handoff

Begin bij de concrete volgende gebruikersvraag, actuele bron en dit dossier. De gebruiker wil geen toekomstige toestelreserveringen en noemt circa 3000 W totaalvermogen van de warmtepomp bij SG. Behoud die expliciete totaalbetekenis, echte actuele P1 en onafhankelijke actuele grenzen; herstel geen oude afwaspiek- of target-minus-measured-reserve onder een andere naam.

De gebruiker heeft eveneens toegestaan dat SG zon van een lager geplaatste autonome Wallbox overneemt en dat de laadpaal later terugregelt. Bewaar de begrensde software-uitzondering met oorspronkelijke eindtijd en bewijs. Verleng niets door uitlezen, leasevernieuwing of herstart. Geef onbekende laadgegevens of oude HP-metingen geen credit.

Laat een firmwareversiewijziging op dezelfde bewezen fysieke uitgang niets blokkeren en vraag daarvoor geen handmatige herbevestiging. Gebruik automatische actuele verificatie en herstel de oude firmware-only-latch waar het passende bewijs dat draagt. Verzin geen ontbrekend hardware- of timerbewijs en behandel een echte fysieke wijziging afzonderlijk. Een onzekere foutoorzaak blijft onzeker. Bewaar beschermde cycli, eenmalige aanvragen, fysieke handmatige UIT en private bronrechten. Werk actuele uitleg en overdracht bij iedere wijziging bij en claim geen fysieke proef die niet is uitgevoerd.
