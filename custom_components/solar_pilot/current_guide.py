"""Single release-bound guide; regenerate bundled documentation after changes."""
from __future__ import annotations
import hashlib
import json

GUIDE_VERSION = '1.0.0-beta.52'
GUIDE_UPDATED = '2026-10-04'

CURRENT_GUIDE = {'title': 'SolarPilot · Actuele werking',
 'version': '1.0.0-beta.52',
 'updated': '2026-10-04',
 'intro': 'Dit is de enige actuele gebruikersuitleg voor deze release. Bij elke wijziging wordt deze tekst '
          'samen met de code vernieuwd. Deze HACS-release bevat bewust één actuele regelset. Configuratie en '
          'leerdata blijven lokaal in Home Assistant en worden bij gewone HACS-updates niet vervangen door '
          'programmabestanden.',
 'sections': [{'title': '1. Basisprincipe en modi',
               'paragraphs': ['SolarPilot is een lokaal Home Assistant-EMS. De actuele P1- en PV-metingen, '
                              'apparaatvoorwaarden en beveiligingen zijn altijd belangrijker dan '
                              'voorspellingen of aangeleerde patronen.',
                              'Operationele vermogens-, toestel- en beschermingsrapportages moeten geldig '
                              'en echt bruikbaar zijn. Restored, toekomstige, niet-eindige of verkeerd '
                              'gevormde waarden worden niet als actuele vrijgave gebruikt. Een geldige '
                              'statische veiligheidswaarde mag ongewijzigd blijven; er wordt niet '
                              'kunstmatig een nieuwe waarde of heartbeat gemaakt.',
                              'Alleen bekijken (technisch: observe) berekent en leert maar stuurt geen gewone '
                              'flexibele toestellen. Automatisch regelen (technisch: solar) voert de toegestane '
                              'regeling uit. Pauze start niets nieuws en bouwt eigen onderbreekbare lasten veilig '
                              'af, met behoud van minimumlooptijden en beschermde cycli. Tijdens actief '
                              'beheer kan Alleen bekijken worden geweigerd: kies eerst Pauze en wacht tot '
                              'beheerde toestellen veilig zijn vrijgegeven. Pauze mag alleen bewezen eigen '
                              'OFF/coast-zones naar Panasonic AUTO teruggeven en een bevestigd eigen '
                              'numeriek batterijdoel neutraliseren zolang het actuele doel nog exact past. '
                              'Handmatige OFF, overgenomen, onbekende of foutieve doelen en willekeurige '
                              'scripts worden niet op basis van een aanname overschreven. Ontbrekend '
                              'eigendom- of bronbewijs blijft beschermd.',
                              'Er wordt maximaal één gewone fysieke wijziging tegelijk uitgevoerd en daarna op '
                              'terugmelding en nieuwe meetinformatie gewacht. Nieuwe apparaten staan standaard '
                              'Uitgesloten totdat ze bewust op Auto worden gezet.',
                              'Een pending batterijopdracht blokkeert nieuwe gewone laststarts/verhogingen, '
                              'AEG-deadline-START en nieuwe vermogensoverdracht. Ook veilige klimaatvrijgave '
                              'bij verwijderen wacht op die bevestiging. Bestaande beschermde cycli blijven '
                              'afwerken; veilige reductie van gewone lasten behoudt haar normale rustregels. '
                              'Na batterijactie is naast powerbevestiging ook een nieuwe P1-rapportage en '
                              'de normale wachttijd nodig; oude netruimte wordt niet opnieuw uitgegeven.'],
               'bullets': ['Eén actuator heeft maar één eigenaar.',
                           'Een EMS-berekening is geen elektrische beveiliging.',
                           'Onzekere opdrachten worden niet eindeloos herhaald.',
                           'Na een herstart leest SolarPilot eerst de echte toestelstatussen. Bekende '
                           'aan/uit-toestanden worden automatisch gereconcilieerd en de eerder opgeslagen '
                           'modus wordt hervat zonder oude schakelopdrachten te herhalen. Een tijdelijk '
                           'ontbrekende status wordt bij volgende gewone regelrondes automatisch opnieuw '
                           'gecontroleerd. Een normale herstart vraagt geen handmatige bevestiging. Echte '
                           'fouten, handmatige overname en een onzekere uitgevoerde START blijven beschermd.']},
              {'title': '2. Overschot, prioriteiten en planner',
               'paragraphs': ['De netmeter bepaalt echte import of injectie. SolarPilot houdt tegelijk '
                              'rekening met de lasten die het zelf beheert, zodat een succesvolle inschakeling '
                              'niet meteen als verdwenen zonne-energie wordt geïnterpreteerd.',
                              'De tab Voorrang toont alle flexibele toestellen, de Wallbox en de extra '
                              'boilerwarmte samen. Bij de upgrade vanaf beta.35 wordt de reeds effectieve '
                              'volgorde éénmalig en ongewijzigd vastgelegd als centrale bron van waarheid. '
                              'Beveiliging/legionella, noodzakelijk warmwatercomfort en noodzakelijk '
                              'ruimtecomfort blijven boven de verplaatsbare lijst staan. Daarna blijft de '
                              'afgesproken flexibele volgorde Wallbox, ontvochtiger en extra boilerwarmte '
                              'naar 60 °C behouden totdat de gebruiker die bewust wijzigt.',
                              'Toestellen op Auto worden volgens hun prioriteit gepland. Een hooggeprioriteerd '
                              'toestel dat niet past mag een kleiner lager toestel niet automatisch blokkeren. '
                              'Minimum aan/uit-tijden, start- en stopvertragingen, tijdvensters, dagminima en '
                              "beschermde programma's blijven gelden.",
                              'De Unified Planner rekent standaard iedere 15 minuten een rolling horizon van '
                              '36 uur opnieuw door in blokken van 15 minuten. Hij plant alleen flexibele, '
                              'expliciet vrijgegeven lasten en combineert lokaal gecorrigeerde PV, geleerd '
                              'basisverbruik, prijzen, kwartierpiek en toekomstige batterijruimte in één plan. '
                              'Alleen het huidige blok mag invloed krijgen op de realtime regelaar; bij nieuwe '
                              'meetinformatie wordt het plan opnieuw berekend.',
                              'Per toestel kan naast minimumlooptijd een dagdoel in kWh worden ingesteld. Als '
                              'een exclusieve vermogensmeter aanwezig is, integreert SolarPilot het werkelijk '
                              'gemeten toestelvermogen tot dagenergie; zonder meter gebruikt het een '
                              'verklaarbare vermogensschatting. De planner probeert alleen de nog ontbrekende '
                              'energie binnen tijdvenster en deadline in de gunstigste blokken te plaatsen. '
                              'Een lopende last wordt niet gestopt omdat een nieuw plan anders uitkomt. '
                              'Actuele P1/PV, minimumlooptijden, comfort, sterilisatie en toestelbeveiligingen '
                              'blijven altijd belangrijker dan het plan.',
                              'Voor beschermde niet-onderbreekbare cycli kan SolarPilot energie, duur en '
                              'piekvermogen per programma lokaal bijleren wanneer een exclusieve '
                              "vermogensmeter beschikbaar is. De planner plant zo'n cyclus als één "
                              'aaneengesloten blok in plaats van losse kwartieren. Tot er voldoende complete '
                              'cycli geleerd zijn, kan een expliciete fallback in kWh en minuten worden '
                              'ingesteld. Zonder betrouwbaar duurprofiel wordt geen optimistische duur uit '
                              'piekvermogen gegokt. De realtime regelaar controleert bij de echte start nog '
                              'altijd actuele vermogensruimte en laat een gestarte beschermde cyclus afwerken. '
                              "Zodra zo'n cyclus loopt, reserveert de planner het geschatte resterende "
                              'cyclusverbruik in de horizon zodat andere flexlasten niet op reeds toegezegd '
                              'vermogen worden gepland.',
                              'Een vrijgegeven last zonder dagdoel, dagminimum of beschermde cyclus wordt niet '
                              'door een leeg plannerdoel geblokkeerd, ook niet wanneer forecastuitstel is '
                              'aangevinkt. De normale realtime overschotregeling blijft dan leidend.'],
               'bullets': ['Goedkope netfallback is dubbele opt-in en standaard UIT. Dynamische prijzen worden '
                           'alleen gebruikt wanneer een bruikbare prijsreeks beschikbaar is. Tijdgestempelde '
                           'reeksen worden op het echte planmoment uitgelijnd; gangbare '
                           'today/tomorrow-profielen worden op het lokale uur of kwartier gelegd. Bij '
                           'ontbrekende of ongeldige gegevens geldt de vaste prijsfallback.',
                           'Capaciteitstarief- en fasegrenzen blijven van toepassing als netstroom wordt '
                           'toegestaan.',
                           'Aangeleerd toestelvermogen mag de planningsschatting alleen conservatiever maken. '
                           'Voor een binaire last die fysiek al AAN staat is een gewijzigde geleerde '
                           'vermogenswaarde alleen een plannings-/boekhoudkundige update; SolarPilot stuurt '
                           'daarom niet opnieuw turn_on zolang de bestaande opdracht bevestigd is.',
                           'Het basislastmodel kan ook leren tijdens gemeten Wallbox- en flexlastgebruik. '
                           'Alleen werkelijk afzonderlijk gemeten vermogen wordt afgetrokken; '
                           'ontbrekende/geschatte of ongeldige bronnen worden niet als nul gebruikt. De '
                           'historische bootstrap is een voorzichtige start, geen zekerheid.',
                           'Een toekomstige batterij wordt in de planner eerst adviserend meegetekend; de '
                           'aparte realtime batterijguard blijft eigenaar van fysieke batterijsetpoints.',
                           'Plannerkwaliteit wordt achteraf gemeten op voorspelde versus werkelijke PV, '
                           'gewone huishoudelijke basislast en netresultaat, plus de mate waarin geplande '
                           'run/stop-toestanden werkelijk konden worden uitgevoerd. SolarPilot bewaart '
                           'hiervan compacte dagaggregaten en toont meetdekking, 7- en 30-dagenfouten en '
                           'uitvoering afzonderlijk. Er is geen losse totaalscore die als '
                           'waarschijnlijkheid of kwaliteitsgarantie moet worden gelezen.',
                           'Een begrensde 15-minutenreplay bewaart recente gemeten PV, basislast, prijzen en '
                           'netresultaat. Daarmee vergelijkt de Planning-tab enkele alternatieve '
                           'plannerstrategieën op dezelfde meetdata. Dit is een plannerreplay en geen exacte '
                           'fysieke simulatie van elk historisch apparaat; verschillen worden daarom alleen '
                           'als richtinggevend advies getoond. Alleen volledig gedekte lokale dagen '
                           'tellen als dagreplay: 92 kwartieren bij de korte zomertijdwisseldag, normaal '
                           '96 en 100 bij de lange wintertijdwisseldag. Gaten of een gedeeltelijke dag '
                           'worden niet als volledige dagprestatie voorgesteld.',
                           'Voor grotere plannerwijzigingen bevat het pakket daarnaast een offline historische '
                           'vergelijking die dezelfde Unified Planner met de huidige en een voorgestelde '
                           'instelling op dezelfde meetachtergrond kan draaien. Ook die backtest is '
                           'richtinggevend: historische startklaarheid, aanwezigheid en thermische toestand '
                           'zijn niet volledig reconstrueerbaar.']},
              {'title': '3. Wallbox: effectieve sessie, prioriteit en gecontroleerde vermogensverdeling',
               'paragraphs': ['SolarPilot bedient de Wallbox niet: geen laadstroom-, fase-, pauze-, start- of '
                              'hervatopdrachten. De laadpaal kan autonoom Full Solar regelen, of door de '
                              'gebruiker manueel/gepland laden. Die situaties worden onderscheiden; de '
                               'ingestelde Full Solar-optie is geen bewijs dat de huidige sessie ook '
                               'terugregelt op zon.',
                               'Koppel een betrouwbare effectieve-sessiebron met volledige waarden voor '
                               'zonneladen, manueel en gestopt. Een manuele melding wint van een Full '
                               'Solar-instelling. Een onbekende, te oude of strijdige bron geeft geen '
                               'overneembaar EV-vermogen vrij. De expliciete terugval Alleen Full '
                               'Solar-instelling vertrouwen staat standaard UIT; uitsluitend kiezen wanneer die '
                               'aanname voor jouw gebruik klopt. Geen statuscode gokken en geen mode afleiden '
                               'uit alleen netimport.',
                               'De standaardlijst met zonne-autostatussen herkent ook Zonne-auto · wacht op '
                               'auto. Een opgeslagen lijst die exact overeenkomt met de oude standaardwaarden '
                               'krijgt die nieuwe canonieke waarde compatibel erbij, ongeacht volgorde, '
                               'hoofdletters of eenvoudige scheidingstekens. Een bewust aangepaste lijst wordt '
                               'niet stil verbreed. Ook bij een herkende tekst blijft de actuele native Full '
                               'Solar-modus verplicht.',
                               'Een verse geldige vermogensmeting onder de ingestelde laaddrempel heft de '
                               'EV-reservering alleen direct op wanneer ook expliciet geen laadvraag, geen '
                               'verbonden auto of een bekende inactieve status is gemeld. Dit geldt ook als '
                               'een afgeleide sessietekst nog achterloopt. Oude, ongeldige, onbekende of '
                               'strijdige bronnen blijven fail-closed. Deze vrijgave verandert alleen de '
                               'SolarPilot-begroting en uitleg; zij verstuurt geen Wallbox-opdracht.',
                              'Na een bevestigde centrale wijziging bepaalt de positie vóór of na Auto laden · '
                              'Wallbox de relatieve voorrang. Per toestel kies je Mag de auto minder laten '
                              'laden?: Ja, als het veilig kan of Nee. Ja geeft alleen een voorwaardelijke '
                              'toestemming: een eigen exclusieve W/kW-meter, een onderbreekbare schakelaar of '
                              'numerieke actuator en een actuele bevestigde zonnelaadsessie blijven vereist. '
                              'De AEG gebruikt zijn aparte beschermde route. Achter de Wallbox krijgt een '
                              'toestel geen EV-vermogen, ook niet met Ja geselecteerd. Een reeds ingestelde '
                              'korte-cycluskeuze behoudt haar strengere voorwaarde voor de minimumlooptijd. '
                              'Zolang de centrale lijst nog niet is gewijzigd, blijven de bestaande numerieke '
                              'en per-Wallbox-keuzes exact leidend.',
                              'Een lange minimumlooptijd wordt bij Voorrang volgen niet weggeknipt om een '
                              'overdracht sneller terug te nemen. Ook bij een mislukte overdracht blijft de '
                              'compressor beschermd. Daardoor kan tijdelijk netstroom nodig blijven tot veilig '
                              'vrijgeven mogelijk is. De generieke route wordt niet voor een beschermd '
                              'huishoudprogramma of onbevestigde scriptcyclus gebruikt. De AEG heeft de '
                              'afzonderlijke, niet-terugneembare start-only route.',
                              'Werkelijk vrij overschot en voorwaardelijk overneembaar Wallbox-vermogen zijn '
                              'twee verschillende grootheden. EV-vermogen wordt nooit als extra elektrische '
                              'capaciteit gerekend. De volledige nieuwe belasting moet vóór de opdracht binnen '
                              'de actuele net-, kwartierpiek- en eventuele fasegrenzen passen alsof de Wallbox '
                              'nog niet heeft gereageerd. Er wordt één stap tegelijk gezet en gecontroleerd '
                              'met nieuwe net-, Wallbox- en toestelrapporten. Bij mislukking volgen een '
                              'blokkering en veilige terugname van uitsluitend de eigen verhoging, geen blinde '
                              'herhaling en geen laadpaalbediening.',
                              'Bij manueel laden geldt: de auto moet geladen worden. Er wordt geen EV-vermogen '
                              'aan andere lasten toegekend. Gewone zonneflexlasten mogen wel werkelijk '
                              'resterende injectie gebruiken. Een gestarte afwascyclus blijft afwerken; de '
                              'expliciet toegestane 13:00-netfallback behoudt zijn voorwaarden. Gewoon '
                              'ruimtecomfort en sanitair warm water werken onder hun eigen voorwaarden verder. '
                              'Ze worden niet voor de auto uitgeschakeld.',
                              'Extra 60 °C uitstellen bij manueel/onzeker laden staat standaard AAN. Tijdens '
                              'zo’n actieve/onzekere laadbehoefte krijgt SolarPilot geen nieuwe 60 '
                              '°C-luxe-opwarming vrij. Een reeds door SolarPilot beheerd hoog doel kan volgens '
                              'de terugvaltijd naar het gewone niveau dalen; bij het 50/46-profiel normaal 50 '
                              '°C. Dit koelt de tank niet actief en is geen onmiddellijke compressorstop. '
                              'Noodzakelijke avondvoorraad onder het plafond blijft een aparte comfortfunctie. '
                              'Sterilisatie, Powerful en Force DHW worden nooit door deze EV-regel aangepast. '
                              'Een bewezen afwezige/volle auto houdt de luxe-opwarming niet onnodig tegen. De '
                              'optie UIT laat alleen echte restinjectie opnieuw als grond voor extra 60 °C '
                              'gelden; manueel EV-vermogen blijft niet-overneembaar.',
                              'Voor een verbruiker onder de Wallbox blijft Wallbox eerst; klein restoverschot '
                              'benutten beschikbaar. Zonder auto/laadvraag geen reservering. Als de auto nog '
                              'niet aan zijn minimale laadvermogen komt, mag een lager toestel kleine '
                              'overschotten gebruiken. Wanneer stoppen van gemeten eigen lagere lasten een '
                              'start mogelijk maakt, worden zij na stabiliteit en minimumlooptijd veilig '
                              'vrijgegeven. Tijdslimieten voorkomen eindeloos wachten op een auto die niet '
                              'begint. Bestaande ingestelde tijden worden niet gewijzigd.',
                              'Het laadprofiel kan maximale laadstroom uit een eenduidige bron van hetzelfde '
                              'Wallbox-apparaat lezen. De maximale ICP-/huisaansluiting is geen '
                              'laadstroomlimiet. Een- of driefasig laden vereist een expliciete betrouwbare '
                              'bron of handmatige bevestiging. Het opgegeven terugvalprofiel is 1 fase / 25 A; '
                              'ongeveer 5,75 kW bij 230 V. Full Solar-minimum 1380 W is apart instelbaar of '
                              'uit bevestigde fasen × minimumstroom × spanning te berekenen. Geen automatische '
                              'wijziging van stroom- of faseinstellingen.',
                              'De daadwerkelijke terugmelding bepaalt of een overdracht bevestigd is. '
                              'Tijdelijke netafname tijdens de Wallbox-reactie kan niet worden uitgesloten. '
                              'Geen bescherming of zekering wordt vervangen door deze software. Alle nieuwe '
                              'standaardkeuzes verhogen geen Auto-deelname, actuatorvrijgave of toestemming om '
                              'nieuwe hardware aan te sturen.'],
               'bullets': ['Effectieve sessie en ingestelde zonnemodus staan naast elkaar in het dashboard.',
                           'Per verbruiker staat één uitkomst: auto mag veilig minder laden, alleen vrij '
                           'zonneoverschot, of de strengere route voor een kort en gemeten toestel.',
                           'De bestaande voortgang, fouten en overnamebesluiten staan ook in de '
                           'analyse-export.']},
              {'title': '4. Sanitair warm water: rustig normaal doel, zon voor extra voorraad',
               'paragraphs': ['SolarPilot vraagt alleen een tankdoel. De normale boilerdoeltemperatuur is een '
                              'afzonderlijke instelling, standaard 50 °C; de bewaakte comfortondergrens is '
                              'standaard 46 °C. Een lage tanktemperatuur, de ochtenddeadline of een andere '
                              'tankdifferentie verhoogt het normale doel niet. Er is geen tijdelijke '
                              'herstelverhoging naar 52 °C, geen Force DHW, geen Powerful en geen compressor-, '
                              'hoofdvoedings- of DHW-modeopdracht.',
                              'Met 50 °C als normaal doel en de fysieke heropwarmdifferentie -5 °C kan '
                              'Panasonic nominaal pas rond 45 °C herstarten. Daarom kan deze zachte sturing '
                              'geen 46 °C minimum garanderen. Onderschrijding wordt zichtbaar gemeld; '
                              'uitsluitend het normale doel blijft beschikbaar. De fabrikant bepaalt zelf hoe '
                              'hij ruimteverwarming, koeling en tankverwarming afwisselt. Een strikter '
                              'gegarandeerd minimum vraagt een andere, fabrikantgeschikte fysieke regeling en '
                              'wordt hier niet nagebootst.',
                              'Normaal doel en comfortgrens zijn geen hygiëneverklaring. Een 46/50 °C-profiel '
                              'is een comfort-/energiekeuze, geen bewezen Legionella-beheersing. '
                              'Onafhankelijke fabrikant-hygiëne, goede doorstroming, juiste installatie en '
                              'passende verbrandingsbeveiliging blijven nodig. De software bevestigt die '
                              'geschiktheid niet namens de gebruiker.',
                              'De nachtbeperking blokkeert extra zonnebuffers maar laat het normale doel '
                              'staan. De uitgebreidere keuze wacht na de nacht op stabiele zon voor extra '
                              'voorraad. Zij verlaagt het normale doel niet en veroorzaakt geen hogere '
                              'klokstart om 06:00. Panasonic mag ook zonder zon volgens zijn eigen thermostaat '
                              'bijverwarmen. Een setpointkoppeling kan geen nulverbruik tijdens de nacht '
                              'garanderen.',
                              'Ochtendcontrole is optioneel. Standaard wordt om 09:00 een gemeten voorraad van '
                              'minstens 46 °C beoordeeld; de effectieve ochtendgrens is nooit lager dan de '
                              'algemene comfortgrens. De bestaande lokale tankmodule schat afkoeling en '
                              'opwarmsnelheid en meldt een dreigend tekort. Zij kan tijdig alleen het normale '
                              'doel herstellen. Zij zet dat doel niet hoger om de fabrikant tot starten te '
                              'bewegen. Een gemiste of onhaalbare deadline wordt gemeld in plaats van als '
                              'behaald getoond.',
                              'De voorspelde ochtendtemperatuur is een afkoelscenario zonder toekomstige '
                              'bijverwarming, niet een gegarandeerde werkelijke temperatuur. Onverwachte '
                              'waterafname, gelaagdheid, sensormetingen en beperkte opwarmtijd kunnen het '
                              'verloop sterk veranderen. Het bounded leermodel gebruikt pas voldoende '
                              'waarnemingen op verschillende dagen; anders staan de ingestelde '
                              'terugvalramingen en hun herkomst zichtbaar in beeld.',
                              'Avondvoorraad is afzonderlijk opt-in en kan ook zonder actieve ochtenddeadline '
                              'werken. Het doel komt uit het ochtendniveau, verwachte nachtverliezen en '
                              'instelbare reserves, standaard begrensd op 55 °C. Een doel van bijvoorbeeld 52 '
                              '°C kan dus alleen als berekende zonnevoorraad worden gevraagd, nooit als '
                              'tijdelijke minimumherstelboost. Een gekozen avondreserve wordt niet stapsgewijs '
                              'verhoogd om de native herstartdrempel te passeren. Zodra de reserve bereikt is, '
                              'wordt die dag geen tweede avondbuffer gestart; dit blijft bij een gewone '
                              'herstart bewaard.',
                              'De avondplanning kiest de laatste nuttige zonneperiode uit bestaande forecasts '
                              'of een ingesteld terugvalvenster. Er moet werkelijk bruikbare zonne-ruimte voor '
                              'de nieuwe avondbuffer zijn. Voorspelling alleen geeft geen start. Een eenmaal '
                              'lopende, door SolarPilot beheerde avondbuffer mag met actuele PV en voldoende '
                              'netbalans blijven bestaan. De temperatuur zelf of het feit dat de avondlimiet '
                              'bereikt is bewijst geen energiebron.',
                              'Nieuwe optionele verhogingen boven het normale doel wachten standaard zolang de '
                              'gekoppelde ruimteklimaatactie heating, preheating, cooling of defrosting meldt, '
                              'of de noodzakelijke klimaatbron onbetrouwbaar is. Een gekozen HEAT-, AUTO- of '
                              'HEAT_COOL-modus bewijst niet dat de warmtepomp nu verwarmt of koelt. Voor de '
                              'exact geregistreerde aquarea-klimaatadapter is een actuele native '
                              'hvac_action idle/off betrouwbaar, ook in AUTO/HEAT_COOL. Een algemene taakmelding '
                              'PUMP, of een oude of niet herkende optionele taakmelding, mag die betrouwbare '
                              'actie niet overschrijven. PUMP blijft zichtbaar als gemeld ruimtebedrijf, '
                              'zonder daaruit verwarmen, koelen of compressorvermogen af te leiden. '
                              'De oudere panasonic_cc-adapter kan in AUTO/HEAT_COOL idle/off melden bij '
                              'mogelijk ruimtebedrijf. Daarvoor blijft een actuele, expliciete taakbron '
                              'nodig: IDLE/WATER kan de onduidelijkheid opheffen; PUMP of een ontbrekende, '
                              'oude, restored, overlappende of onbekende taakwaarde geeft geen vrijgave. '
                              'Een werkelijk ontbrekende, oude, restored of onbeschikbare klimaatbron '
                              'blokkeert de optionele buffer ook bij een geruststellende taakmelding. '
                              'Echte koeling heeft altijd voorrang. Een al hoger aangevraagd doel wordt niet '
                              'alleen wegens een nieuwe verwarmactie afgebroken; de fabrikant kan de begonnen '
                              'taak afhandelen. Hygiëne, energietekort en andere beschermingen blijven '
                              'afzonderlijk leidend.',
                              'Voor extra verhogingen geldt standaard 300 seconden stabiele zonnevoorwaarde en '
                              'minstens 1800 seconden sinds de laatste verstuurde doelopdracht. Verlagingen '
                              'wegens echte netafname, nacht, koelbegrenzing of pauze hoeven niet op dat extra '
                              'verhogingsinterval te wachten. Het gewone doel herstellen wordt evenmin '
                              'uitgesteld. Dit zijn rustregels voor setpoints, geen gegarandeerde '
                              'compressorlooptijden.',
                              'Zonnestabiliteit en de minimumtijd tussen doelopdrachten lopen afzonderlijk. '
                              'Als de zonnevoorwaarden geldig blijven, wordt een voltooide stabiliteitscontrole '
                              'niet opnieuw gestart alleen omdat de vorige doelopdracht nog te recent is. '
                              'Zodra beide wachttijden voorbij zijn, kan een volgende gewone regelronde de '
                              'verhoging vragen, mits alle overige voorwaarden nog kloppen. Verlies van geldig '
                              'zonneoverschot, echte koeling of een te groot meetgat onderbreekt de betrokken '
                              'zonnestabiliteit wel. Een wachtend voorstel krijgt geen eigendoms- of '
                              'hysteresevrijgave alsof het hoge doel al is toegepast. Een nog niet uitgevoerde '
                              '55 °C-verhoging mag daardoor ook niet bij minder PV alsnog starten via de '
                              'lagere vasthouddrempel. Alleen een passend eigen werkelijk doel kan zo een '
                              'bestaande fase vasthouden.',
                              'Het warmwateroverzicht en de warmwaterdetailkaart tonen de actuele '
                              'regel- of wachtreden. Stabiliteitscontrole en rust tussen doelopdrachten '
                              'worden apart benoemd; voldoende zon in het beleidsadvies verbergt geen '
                              'wachttijd bij uitvoering. Ook wachten op een andere regelopdracht of een '
                              'ongeschikt native doelbereik blijft zichtbaar. SolarPilot-voorstel, gemeld Panasonic-doel en '
                              'gemeten tanktemperatuur blijven afzonderlijke waarden. Een voorstel van '
                              '60 °C bij een gemeld doel van 50 °C betekent nog geen verzonden of '
                              'bevestigde verhoging en bewijst geen fysieke opwarming.',
                              'Gewoon warmtepompcomfort staat vóór de autonome Full Solar-Wallbox. Voor de '
                              'beschermde avondvoorraad, nooit hoger dan de ingestelde limiet en maximaal 55 '
                              '°C, mag SolarPilot actueel gemeten EV-zonnevermogen alleen in de '
                              'comfortbeoordeling als vrijmaakbaar tellen. Daarvoor moet de native Full '
                              'Solar-sessie expliciet ingeschakeld, verbonden en vragend zijn, minstens 50 W '
                              'laden en moeten zowel sessiestatus als vermogen hoogstens 120 seconden oud zijn. '
                              'Handmatig laden en onbekende, strijdige of oude sessies leveren geen krediet. '
                              'Dit vermogen verhoogt nooit fysieke net- of faseruimte en de Wallbox krijgt geen '
                              'opdrachten van SolarPilot. Comfortgrens, actieve/verwachte koeling, '
                               'fabrikantsterilisatie en overige beveiligingen houden voorrang. De extra 60 '
                               '°C-fase krijgt nooit EV-krediet: de ingestelde overschotdrempel moet uit '
                               'werkelijke restinjectie passen en een startklare Wallbox krijgt eerst de kans '
                               'om te laden.',
                               'Een lopende voorkeurs-afwasmachine is voor extra 60 °C geen algemeen veto. '
                               'SolarPilot trekt eerst huisreserve, batterijontlading, nog niet verbruikt '
                               'toegezegd toestelvermogen en — zonder exclusieve AEG-meter — de conservatieve '
                               'nominale afwasreserve af. De bruikbare ruimte is bovendien begrensd door zowel '
                               'de actuele en gefilterde netmeting als de echte PV-productie. Een startklare '
                               'afwas die aantoonbaar past krijgt eerst één startkans; blijft daarna voldoende '
                               'werkelijk overschot over, dan mag de 60 °C-buffer naast een lopende beurt '
                               'werken. Onvolledige of onbetrouwbare vermogensinformatie blokkeert deze luxe '
                               'fail-closed. Wanneer kwartierpiekbewaking voor optionele DHW actief is, moet '
                               'een nieuwe start of onbevestigde native herstart bovendien het geschatte '
                               'boilervermogen in de geldige piekruimte passen. Een bewezen reeds actieve, '
                               'door SolarPilot beheerde 60 °C-verwarming wordt daarbij niet dubbel '
                               'gereserveerd.',
                              'Het gewone zonnedoel is standaard eveneens 50 °C, vanaf 1000 W actuele '
                              'PV-productie. Omdat dit gelijk is aan het normale doel, geeft het geen extra '
                              'temperatuurverhoging. Een bewust hoger gewoon zonnedoel blijft een '
                              'productievoorwaarde en kan netstroom vragen. Voor echt extra 60 °C telt alleen '
                              'overschot. Om een eigen hoge fase vast te houden kan uitsluitend een aparte '
                              'betrouwbare elektrische tankvermogensmeter compenseren, nooit geschatte watts '
                              'of een gedeelde meter.',
                              'Actieve of onzekere koeling begrenst de extra doelen tot de ingestelde '
                              'koellimiet, standaard 50 °C. Alleen bewezen koeling start of verlengt de '
                              'ingestelde uitloop, standaard 1800 seconden. Onbekende informatie blokkeert '
                              'zolang zij ontbreekt, maar maakt geen nieuwe dertigminutenwachttijd zodra '
                              'de bronnen weer betrouwbaar zijn. Een warmwatercyclus die recent bewezen '
                              'koelen onderbreekt telt niet meteen als einde van de koelvraag. '
                              'Een vóór beta.46 opgeslagen koel-/onzekerheidstijd blijft bij upgrade '
                              'conservatief behouden, omdat de oorspronkelijke oorzaak niet betrouwbaar '
                              'te reconstrueren is. Daardoor kan een bestaande uitloop of bescherming '
                              'tijdens een native warmwatertaak nog tijdelijk blijven gelden. '
                              'Optionele voorspelde koelvraag kan extra opwarming uitstellen; dit kiest nooit '
                              'HEAT/COOL en activeert geen nieuwe ruimteklimaatbediening.',
                              'Bestaande configuraties worden voorzichtig gemigreerd: het vroeger uit minimum, '
                              'differentie en buffer berekende normale doel wordt éénmalig als expliciet '
                              'normaal doel bewaard. Vanaf dat moment veranderen die andere waarden het '
                              'normale doel niet meer. Kies bij de overstap bewust 50 °C normaal en 46 °C '
                              'bewaakt voor dit profiel. Een nieuwe lege configuratie gebruikt 50/46. '
                              'Bronkoppelingen, lokale leerdata en expliciete rechten blijven behouden; geen '
                              'functie of veiligheidsbevestiging wordt stilzwijgend aangezet.'],
               'bullets': ['Onafhankelijke fabrikantsterilisatie blijft autonoom en heeft voorrang ongeacht '
                           'zon, prijs, koeling of Wallbox. Een beschermingsvenster in SolarPilot is geen '
                           'bewijs dat het hele vat of alle leidingen werkelijk gedesinfecteerd zijn.',
                           'De bestaande gecombineerde veiligheidsbevestiging blijft verplicht. Niet aanvinken '
                           'zolang toestelgeschiktheid, hygiëne en verbrandingsbeveiliging niet daadwerkelijk '
                           'gecontroleerd zijn.',
                           'Het normale setpoint verhogen, de fysieke differentie aanpassen of de '
                           'warmwatermodus forceren om 46 °C af te dwingen gebeurt niet in deze versie. Een '
                           'melding is geen activering van zo een bypass.',
                           'Panasonic-doel en gemeten temperatuur staan apart in beeld: een bevestigd setpoint '
                           'betekent nog niet dat het water warm is of dat de compressor begonnen is.',
                           'Met 50 °C als gewone instelling blijft netbijverwarming van de fabrikant mogelijk. '
                           'Een ondergrens nooit overschrijden en tegelijk nooit op netstroom bijverwarmen '
                           'zijn geen garanties van deze zachte sturing.']},
              {'title': '5. PV-model: Forecast.Solar, lokale kwartierkalibratie en PV-diagnose',
               'paragraphs': ['Forecast.Solar is de basisvoorspelling; de gemeten net- en PV-vermogens blijven '
                              'leidend voor de snelle regeling. De nieuwe pagina PV-voorspelling & lokale '
                              'kalibratie verzamelt bronkeuze, installatiegrenzen en leerinstellingen. Er '
                              'worden geen nieuwe Forecast.Solar-cloudoproepen gedaan: alleen reeds aanwezige '
                              'Home Assistant-sensoren en, waar ondersteund, de geladen coordinator-tijdreeks '
                              'worden gelezen.',
                              'Bij precies één gevonden actieve Forecast.Solar-installatie worden entiteiten '
                              'via het register gekoppeld, ook wanneer ze zijn hernoemd. Reeds expliciet '
                              'gekozen bronnen blijven staan. Bij meerdere installaties kiest SolarPilot niet '
                              'willekeurig en telt niet zomaar op: kies één configuratie-ID uit PV-diagnose of '
                              'gebruik selectors. Kan de interne tijdreeksadapter de versie niet lezen, dan '
                              'blijven gekoppelde scalar-sensoren bruikbaar. Bij ontbrekende/verouderde '
                              'forecast blijven realtime regeling, minimumtijden, comfort en deadlines werken; '
                              'niet gedekte uren worden geen virtueel zonneoverschot.',
                              'Voor het opgegeven profiel gelden 13.800 Wp panelen, 10.000 W '
                              'AC-omvormerlimiet, 25° helling en 180° zuid. Forecast.Solar staat met '
                              'morning/evening damping 0,00 en zonder API-key ingesteld. Dit zijn '
                              'afzonderlijke instellingen van Forecast.Solar; SolarPilot wijzigt die '
                              'integratie niet. De eigen clippinggrens en profielvelden zijn instelbaar. Een '
                              'afwijkende native omvormerlimiet of niet-nul damping wordt in PV-diagnose '
                              'gemeld.',
                              'De vermogenscurve wordt tussen originele tijdstempels lineair geïnterpoleerd. '
                              'De ruwe nu-waarde kan daardoor afwijken van de trapsgewijze native '
                              'Forecast.Solar-sensor; beide staan ter controle in de diagnose. Correctie = '
                              'ruwe waarde × geleerde factor, begrensd op de AC-limiet. Nu, +1, +2 en +3 uur '
                              'worden afzonderlijk getoond. Zonder gedekte curve of aparte +1-sensor blijven '
                              'ontbrekende toekomstige waarden onbekend, niet 0 W. Ook een ontbrekende '
                              'staart of gat in de curve blijft onbekend; ontbrekend forecastbewijs wordt '
                              'geen nulwaarde of kunstmatig lage fout in de kwaliteitsscore. Een evaluatie '
                              'mag zich beperken tot een volledig gemeenschappelijk weer-/PV-tijdvenster '
                              'dat de noodzakelijke coastvoorspelling dekt; de ontbrekende staart wordt '
                              'daarmee niet als bekend ingevuld en interne gaten blijven blokkeren.',
                              'Resterende en toekomstige energie worden met echte tijdstempels en lokale '
                              'middernacht uit de curve geïntegreerd, in kWh. Er wordt geen vaste 24 uur '
                              'aangenomen bij zomer-/wintertijd. Als alleen een dagtotaal beschikbaar is, '
                              'wordt dat ongewijzigd en als ruw fallbacktotaal getoond; een huidige '
                              'correctiefactor wordt niet blind op morgen toegepast. De volledige ruwe energie '
                              'vandaag blijft eveneens beschikbaar voor diagnose. Plan- en forecaststappen '
                              'volgen verstreken UTC-tijd met lokale tijdlabels; de klokwisseling maakt '
                              'geen dubbel verzonnen of overgeslagen uur. Lokale kalenderdeadlines behouden '
                              'hun bestaande tijdzonebetekenis.',
                              'Per minuut wordt maximaal één verse meetwaarneming verzameld. Een kwartier '
                              'wordt alleen geleerd met minstens 12 bruikbare waarnemingen, minimaal 11 '
                              'minuten spreiding, geen grote hiaten en geen ongeldige stukken. De eerste 10 '
                              'minuten na start/reload worden niet geleerd. Ontbrekende, bevroren, ongeldige '
                              'of expliciet als geschat gemarkeerde metingen worden geweigerd. Snelle sprongen '
                              'of sterk variërende verhoudingen wijzen op wisselende bewolking en worden niet '
                              'als structurele correctie opgenomen.',
                              'Vanaf 98% van de ingestelde omvormerlimiet wordt een kwartier niet voor '
                              'schaduwkalibratie gebruikt. Meetwaarden boven 110% zijn outliers. Dit voorkomt '
                              'dat de verhouding 13,8 kWp/10 kW en clipping onterecht als schaduw worden '
                              'geleerd. Weinig zon en extreme verhoudingen worden eveneens uitgesloten. '
                              'Geweigerde kwartieren blijven in de diagnose met reden staan; kwaliteit bij zon '
                              'wordt niet mooier gemaakt door alleen trainingssuccessen te beoordelen.',
                              'Vergelijkbare dagen worden per grove zonne-azimut (10°), zonnehoogte (5°) en '
                              'tweemaandse seizoensgroep bijgehouden; zonder bruikbare positie valt dit terug '
                              'op lokale kwartier/tijdvakken. Bij uitgeschakeld schaduwprofiel wordt de '
                              'globale factor gebruikt. Er is geen vaste factor vanaf 16:00. Lokale '
                              'HA-coördinaten dienen alleen voor de geometrie; ze worden niet naar een externe '
                              'dienst gestuurd. Een terugkerende empirische afwijking is niet automatisch '
                              'bewezen fysieke schaduw.',
                              'Kalibratie en schaduwleren staan standaard aan wanneer een bruikbare bron '
                              'bestaat, zonder fysieke bevoegdheden te veranderen. Een al gemaakte keuze om '
                              'forecast- of lokale-PV-aanpassing uit te schakelen blijft behouden. Normaal gebruikt minstens vijf '
                              'vergelijkbare dagen; Rustig minstens zeven. Per dag beweegt de factor maximaal '
                              '0,05 / 0,025 / 0,075 voor Normaal / Rustig / Vlotter, binnen 0,35–1,25. Bij te '
                              'wisselende dagen of te weinig bewijs blijft de factor 1. Meer metingen op '
                              'dezelfde dag maken geen extra leerdagen.',
                              'Het compacte model bewaart per vak maximaal 45 recente dagen en negeert bewijs '
                              'ouder dan 120 dagen; de seizoensgroepen blijven afzonderlijk. Gewone herstarts '
                              'en updates behouden het model. Wijziging van forecast-/meetbron of fysieke '
                              'profielbinding maakt oude live factoren incompatibel en begint die kalibratie '
                              'opnieuw, zonder andere leermodellen te wissen. Historische '
                              'HomeWizard-kwartieren zonder gelijktijdig opgeslagen ruwe forecast worden niet '
                              'als bewezen forecastkalibratie geïmporteerd. Het bestaande historische '
                              'PV-profiel blijft als aparte terugval bewaard.',
                              'De gewone planner en thermische/boiler-vooruitblik gebruiken beschikbare '
                              'gecorrigeerde uurenergie. Waar de curve niet dekt blijft de bestaande expliciet '
                              'begrensde fallback zichtbaar; geen nieuwe permissie voor actuele starts. De AEG '
                              'APP-start behoudt vooralsnog de actuele conservatieve startdrempel en '
                              '13:00-deadline. Volledige fasegewijze optimalisatie van het afwasprogramma '
                              'wacht nog op een echte Shelly-meter en de afgesproken latere update.',
                              'PV-diagnose opent los van de vijfsecondenkaart: kies een dag, bekijk grafiek en '
                              'kwartiertabel met ruwe/gecorrigeerde/werkelijke W, afwijking W/% en leerreden. '
                              'De knop Vernieuwen haalt alleen bestaande lokale gegevens op. Op de '
                              'Planning-pagina staat een compacte samenvatting; uitgebreide informatie staat '
                              'niet meer in een lange extra hoofdkaart. Analyse-export bevat model, bronnen, '
                              'instellingen en de beschikbare kwartierhistorie.',
                              'De diagnose bewaart maximaal 30 dagen en 2880 kwartierregels. '
                              'Berekenen/verzamelen gebeurt maximaal eens per minuut; het leerbesluit en '
                              'gebundelde opslag per afgesloten kwartier. Historiek zit niet in elke '
                              'vijfsecondenstatus of iedere scalar-sensor. De volledige diagnose is alleen op '
                              'aanvraag beschikbaar voor een HA-beheerder. De bevestigde knop PV-profiel '
                              'wissen wist alleen de live PV-profielen en PV-diagnose; afwasaanvragen, tank- '
                              'en woningmodellen, prioriteiten en apparaatstanden blijven behouden. Bij '
                              'opslaan mislukt blijft de vorige PV-toestand hersteld.',
                              'Veertien aanvullende native sensoren tonen ruw/gecorrigeerd nu/+1/+2/+3, '
                              'resterende kWh vandaag ruw/gecorrigeerd, gecorrigeerde kWh morgen, factor, '
                              'confidence en gemiddelde fout bij zon. Hun eenheden zijn W/kWh/% of '
                              'dimensieloos. Het zijn voorspellingen, geen oplopende energietellers voor '
                              'facturatie en geen vervanging voor echte PV-productie.'],
               'bullets': ['Geen nieuwe cloudpolling of API-key nodig.',
                           'Geen dubbele toepassing van oud en nieuw correctieprofiel.',
                           'Leerdagen en geweigerde kwartieren zijn zichtbaar; geen belofte dat het huis '
                           'perfect voorspelbaar wordt.']},
              {'title': '6. Fasebewaking en faseherkenning',
               'paragraphs': ['L1, L2 en L3 worden afzonderlijk gemonitord. SolarPilot kan bij gecontroleerde '
                              'vermogenssprongen leren op welke fase of fases een gemeten toestel '
                              'waarschijnlijk zit. Alleen bruikbare, voldoende geïsoleerde gebeurtenissen '
                              'tellen mee; conflicterende gelijktijdige veranderingen worden verworpen.',
                              'Per toestel worden classificatie, vertrouwen en aantal waarnemingen '
                              'bijgehouden. De faseweergave toont herkend toestelvermogen en een netto '
                              'restcomponent. Die restcomponent is geen zuiver onbekend verbruik omdat PV en '
                              'andere niet-gemeten stromen de P1-fasewaarden beïnvloeden.',
                              'Automatisch starts blokkeren of lasten afbouwen op basis van fasegrenzen blijft '
                              'uit totdat hoofdbeveiliging, tekenrichting en fasekaart voldoende zijn '
                              'bevestigd.'],
               'bullets': ['Faseherkenning is adviserend totdat ze bewust wordt vrijgegeven.',
                           'Read-only vermogenssensoren kunnen worden gebruikt om extra apparaten te leren '
                           'zonder ze te bedienen.',
                           'Een toekomstige batterij kan per fase of als 3-faseprofiel worden meegenomen.']},
              {'title': '7. Thuisbatterij: analyse nu, aansturing later',
               'paragraphs': ["SolarPilot kan nu batterijscenario's analyseren en is voorbereid op één of "
                              'meerdere echte thuisbatterijen. Zonder gekoppelde hardware blijft dit volledig '
                              'adviserend.',
                              'Per batterij zijn capaciteit, SoC, werkelijk batterijvermogen, reserve-SoC, '
                              'laad-/ontlaadlimieten, fasehint en adaptertype voorzien. Fysieke bediening '
                              'vereist globale toestemming én individuele toestemming én bevestiging dat '
                              'SolarPilot de exclusieve externe setpoint-eigenaar is.',
                              'Standaard is laden uit het net UIT en ontladen naar het net UIT. Een '
                              'batterijopdracht moet door gemeten batterijvermogen worden bevestigd; bij '
                              'ontbrekende bevestiging wordt het profiel geblokkeerd voor controle. De '
                              'minimale tijd tussen batterijopdrachten geldt pas nadat werkelijk een eerdere '
                              'batterijopdracht is verzonden; een verse runtime wordt dus niet afhankelijk van '
                              'systeem-uptime kunstmatig geblokkeerd.',
                              'Commandointentie wordt duurzaam vóór actuatie bewaard. Vlak voor verzending '
                              'worden native doel/eenheid/grenzen, koppeling, expliciete toestemmingen en '
                              'Wallboxbescherming opnieuw gecontroleerd. Een tussentijdse wijziging breekt '
                              'de opdracht af zonder fysieke aanroep en bewaart een controlefout; het '
                              'handmatige native doel blijft behouden. Alleen een verse '
                              'passende vermogensrapportage van ná de opdracht kan batterijbevestiging geven; '
                              'bij numerieke aansturing moet ook het werkelijk gemelde doel passen. Een '
                              'al eerder passende powerwaarde is geen nieuwe ACK. Dit is HA-bronbewijs, '
                              'geen onafhankelijke fysieke apparaatbevestiging. Ontbrekende bronnen of '
                              'fouten geven geen blinde retry of onterechte klaarstatus.',
                              'Een native SoC-sensor moet procenten (%), een eindige waarde van 0 tot 100 '
                              'en een verse echte rapportage leveren. Een geldige input_number-helper mag '
                              'onveranderd blijven, maar niet restored, toekomstig of ongeldig zijn. '
                              'Een ondersteund input_number-doel gebruikt de juiste Home Assistant-service. '
                              'Geselecteerde batterij-actuatoren en scripts mogen niet aan het Wallbox-apparaat '
                              'gekoppeld zijn. Controleer zelf willekeurige scriptinhoud en terugmelding; '
                              'een scriptnaam of apparaatkoppeling bewijst de werking niet.',
                              'Voor verwijderen is verse werkelijk neutrale batterijpower nodig; bij '
                              'numerieke aansturing moet het actuele doel ook exact neutraal zijn. Stil '
                              'gemeten vermogen bij een niet-neutraal setpoint is geen vrijgave. Ontbrekende '
                              'power houdt de voorbereiding tegen; een fout geeft geen automatische retry. '
                              'Een aantoonbaar al neutrale toestand kan read-only worden afgehandeld.',
                              'Een vervangend laad-/ontlaaddoel houdt rekening met de werkelijk aanwezige '
                              'eigen gestuurde batterijflow. Zo wordt bestaande flow niet dubbel '
                              'meegeteld of onterecht op nul gezet bij elke nieuwe berekening. Read-only '
                              'of foutieve profielen blijven als werkelijk aanwezige stroom meetellen '
                              'zonder nieuw bedieningsrecht. Native actuatorgrenzen begrenzen het doel '
                              'voordat een herhaalde te grote of afgekapte opdracht ontstaat. Numerieke '
                              'actuatoren moeten neutraal nul exact binnen hun native bereik en stap kunnen '
                              'weergeven; anders blijft dat profiel uitleesbaar zonder fysieke vrijgave.',
                              'De batterij-what-if rekent standaard met 80% round-trip efficiëntie, dus 20% '
                              'totaal batterij-/omvormerverlies over laden en later terugleveren aan de '
                              'woning. De simulator verdeelt dit verlies symmetrisch over laden en ontladen. '
                              'Historische bootstrapresultaten die oorspronkelijk met een andere efficiëntie '
                              'zijn opgebouwd, worden conservatief naar de ingestelde efficiëntie omgerekend; '
                              'voor een exacte historische herberekening zouden de private 15-minutenbronnen '
                              'nodig zijn.'],
               'bullets': ['Loads first is de standaardstrategie voor deze installatie.',
                           'Read-only, peak shaving en hybrid zijn ook voorzien.',
                           'Bij meerdere batterijen wordt standaard bij laden de laagste SoC en bij ontladen '
                           'de hoogste SoC eerst gebruikt.',
                           'De historische batterijsimulatie is een technische what-if en geen aankoop- of '
                           'terugverdiengarantie.',
                           'Standaardverlies in de what-if: 20% totaal round-trip (80% efficiëntie); dit '
                           'blijft instelbaar.']},
              {'title': '8. Slim verwarmen en koelen: Panasonic beslist HEAT/COOL',
               'paragraphs': ['SolarPilot kiest nooit zelf HEAT of COOL. Panasonic AUTO blijft eigenaar van de '
                              'verwarmings-/koelkeuze. SolarPilot kan alleen AUTO vrijgeven of, vooral in het '
                              'tussenseizoen, de ruimtezones langdurig op OFF/coast zetten wanneer het '
                              'thermische model voldoende vertrouwen heeft dat de woning comfortabel blijft. '
                              'Een handmatig of extern OFF gezette zone blijft onbeperkt uit totdat de '
                              'gebruiker zelf AUTO kiest. Ook een harde comfortoverschrijding, verlopen '
                              'handmatige rusttijd, herstart of verwijderen geeft geen recht die zone '
                              'automatisch in te schakelen. Een comfortwaarschuwing blijft wel zichtbaar.',
                              'De Panasonic-doeltemperatuur blijft ongewijzigd de comfortreferentie. Een '
                              'gewone planningsbeslissing gebeurt standaard om de 12 uur en kijkt 48 uur '
                              'vooruit. Tijdens een coastperiode wordt wel vaker gecontroleerd of AUTO tijdig '
                              'opnieuw moet worden vrijgegeven vóór de geleerde vloer-/bouwschilvertraging een '
                              'comfortgrens bereikt.',
                              'De energiebesparende coastlogica is standaard vooral voor het tussenseizoen. '
                              'Bij duidelijke winter- of zomercontext blijven door de gebruiker vrijgegeven '
                              'AUTO-zones normaal in AUTO, omdat de warmtepomp dan zelf beter kan moduleren dan '
                              'wanneer het EMS agressief heen en weer programmeert. Dit wordt op basis van de '
                              'weersverwachting en het binnendoel bepaald, niet op vaste kalendermaanden. '
                              'Die weerscontext bewijst geen werkelijk actieve verwarmings- of koelvraag.',
                              'Per zone leert SolarPilot passieve warmteoverdracht, verwarmingsrespons, '
                              'koelrespons en reactievertraging op basis van Panasonic hvac_action. Daarnaast '
                              'leert SolarPilot de lokale zonnewinst in de woning: werkelijk PV-vermogen wordt '
                              'als lokale instralingsproxy gebruikt om te schatten hoeveel de woning op '
                              'zonnige momenten vanzelf opwarmt. Die bijdrage is begrensd en wordt pas '
                              'gebruikt wanneer voldoende leerkwaliteit aanwezig is. Een onbekende, '
                              'onbeschikbare, restored of ongeldige ruimteactie wordt niet als idle '
                              'aangeleerd; geen ontbrekende verwarm-/koelactiviteit verzinnen. Ook ontbrekend '
                              'actueel PV-vermogen wordt niet als 0 W in het thermische leerbewijs ingevuld. '
                              'Bij ingeschakelde zonnewinst moet PV op beide uiteinden van het leerinterval '
                              'bekend zijn; ontbrekende PV onderbreekt alleen dat interval, niet bestaande '
                              'geldige samples of coëfficiënten. Twee volgende geldige eindpunten laten '
                              'leren vanzelf hervatten. Bij expliciet uitgeschakelde zonnewinst mag zonder '
                              'PV worden geleerd en wordt geen zonnecoëfficiënt afgetrokken.',
                              'De uurverwachting van de weersdienst wordt lokaal gecontroleerd tegen de '
                              'werkelijk gemeten buitentemperatuur. SolarPilot leert afzonderlijk de '
                              'systematische fout rond 6, 12, 24 en 48 uur vooruit en mag de voorspelling '
                              'alleen binnen een instelbare maximumcorrectie bijstellen wanneer voldoende '
                              'verschillende dagen en vertrouwen beschikbaar zijn.',
                              'Iedere SolarPilot-coastperiode wordt achteraf geëvalueerd als correct, te lang '
                              'of te voorzichtig. Na meerdere beoordeelde episodes mag alleen het minimum '
                              'nuttige coastvenster voorzichtig binnen ingestelde grenzen worden aangepast. '
                              'Comfortbanden, Panasonic-doeltemperatuur en de keuze HEAT/COOL veranderen '
                              'hierdoor nooit. Een feedbackepisode begint en telt pas nadat alle betrokken '
                              'zones hun nieuwe mode met de vereiste latere HA-terugmelding hebben bevestigd. '
                              'Geen echo, mislukte opdracht of vaste HEAT/COOL levert geen fictieve '
                              'coastleerervaring op; na herstart wordt zo\'n episode niet gereconstrueerd.',
                              'Als de actuele buitentemperatuurbron wijzigt, worden het thermische model en de '
                              'lokale weerscorrectie veilig opnieuw geleerd. Als alleen de forecast-weerdienst '
                              'wijzigt, leert de weerscorrectie opnieuw; zonder aparte buitensensor wordt dan '
                              'ook het thermische model opnieuw opgebouwd.',
                              'Een coastperiode is geen gegarandeerde energiebesparing. Panasonic AUTO kan '
                              'zelf al langdurig idle blijven wanneer er geen warmtevraag of koelvraag is. Te '
                              'agressief uitschakelen kan later een grotere inhaalvraag veroorzaken en de '
                              'efficiëntie verslechteren. Daarom blijft fysieke AUTO/coast-bediening standaard '
                              'opt-in en moet de praktijkdata aantonen dat ze voor deze woning zinvol is.',
                              'Ruimteverwarming/koeling heeft voorrang op autonoom EV-laden zodra fysieke '
                              'klimaatbediening bewust vrijgegeven is. Een gewoon stabiel beheerd DHW-setpoint '
                              'blokkeert deze klimaatregelaar niet permanent. Openstaande/onzekere opdrachten '
                              'en beschermde fabrikantcycli blijven wel geserialiseerd en beschermd. De '
                              'betrouwbaarheid wordt daarom per onderdeel getoond: passieve '
                              'temperatuurverandering, zonnewinst, verwarmingsrespons, koelrespons, '
                              'reactievertraging, weerscorrectie en coast/off-feedback. Een ontbrekend '
                              'onderdeel staat als Nog niet geleerd, Eerste metingen of Voorlopig en kan niet '
                              'stilzwijgend als 100% worden voorgesteld.',
                              'Voor een nieuwe automatische coast telt alleen het bewijs dat de actuele '
                              'voorspelling nodig heeft. Passieve temperatuurverandering en zonnewinst '
                              'wanneer die wordt gebruikt blijven nodig. Een voorspelde onderschrijding '
                              'vraagt verwarmingsrespons en de bestaande reactievertraging; een voorspelde '
                              'overschrijding vraagt koelrespons en die reactievertraging. Als beide '
                              'richtingen in de voorspelling nodig zijn, tellen beide mee. Zonder '
                              'voorspelde grensoverschrijding hoeft een niet gebruikte verwarm-/koelrespons '
                              'de passieve coastbeoordeling niet op nul te zetten. Ontbrekende koelervaring '
                              'blokkeert dus niet enkel om die reden een voldoende geleerd verwarmingspad.',
                              'De bestaande reactievertraging is gedeelde leerervaring. Oudere samples '
                              'leggen niet vast of die vertraging uit verwarmen of koelen kwam; de '
                              'weergave verzint daarom geen afzonderlijk bewezen vertraging per richting.',
                              'Het overzicht toont de zekerheid voor de huidige beslissing, de benodigde '
                              'respons, modelstatus en werkelijk opgeslagen samples/dagen/episodes. De '
                              'oude volledige score blijft vergelijkingsinformatie voor alle onderdelen, '
                              'zonder de actuele beslissing stil met een ontbrekend ongebruikt onderdeel '
                              'te blokkeren. Geen score is een fysieke garantie; onvoldoende relevant '
                              'bewijs houdt coast conservatief uit. De voorspelling gebruikt alleen '
                              'opeenvolgende actuele/toekomstige uren met overeenkomende weer- en '
                              'PV-tijdposities; oude uren, gaten of ontbrekende uren geven geen nieuwe coastvrijgave.',
                              'Een wachtende of onzekere klimaatopdracht wordt niet opnieuw verstuurd. '
                              'Een passende nieuwe Home Assistant-standrapportage na minstens tien '
                              'seconden kan de uitkomst bevestigen; een onmiddellijke lokale echo telt '
                              'niet. Na herstart moet die rapportage ook nieuw zijn na de herstartwachttijd. '
                              'Dit is HA-bronbewijs, geen onafhankelijke fysieke apparaatbevestiging. '
                              'Na 180 seconden zonder passende bevestiging blijft de feitelijke stand '
                              'behouden en verschijnt een waarschuwing; er volgt geen replay of retry. '
                              'Een werkelijk OFF gebleven zone blijft beschermd. '
                              'Een oude lokale toestand of een herstart maakt geen nieuw opdrachtrecht. '
                              'Als je zelf OFF kiest terwijl een SolarPilot-AUTO nog wacht, mag een '
                              'vertraagde AUTO-terugmelding het automatische beheer niet herstellen, ook '
                              'niet na langere tijd. Alleen een expliciete nieuwe gebruikerskeuze voor '
                              'AUTO in Home Assistant geeft de zone weer vrij. SolarPilot verstuurt geen '
                              'blinde corrigerende OFF; controleer bij zo\'n vertraagde melding de native stand. '
                              'Handmatige bescherming en verwacht eigendom blijven per zone bewaard. '
                              'Een onbekende actie geeft geen nieuwe OFF-vrijgave. Het vrijgeven van een '
                              'bewezen eigen OFF/coast naar AUTO blijft afzonderlijk mogelijk volgens '
                              'de bestaande comfort-/herstelregels, zonder die onbekende actie als '
                              'idle te leren. Bij ontbrekende forecast mag een bewezen eigen coast '
                              'veilig naar AUTO worden vrijgegeven zonder gewone daglimiet of '
                              'minimumvasthoudtijd af te wachten. Handmatige OFF, vaste HEAT/COOL en '
                              'gebruikersrust blijven beschermd. Een wijziging van de gekoppelde zones '
                              'wacht op veilig afronden van eigen coast of pending opdrachten, zodat '
                              'beheerde zones niet stil uit de herstelcontrole verdwijnen.'],
               'bullets': ['Een handmatig gekozen Panasonic HEAT- of COOL-stand wordt nooit door SolarPilot '
                           'overschreven; de regeling wordt dan adviserend tot de gebruiker zelf terugkeert '
                           'naar AUTO. Zelf OFF kiezen laat de zone uit.',
                           'Een harde comfortoverschrijding mag uitsluitend een door SolarPilot zelf '
                           'beheerde OFF/coast-zone naar AUTO vrijgeven. Een handmatige OFF-zone blijft '
                           'uit tot de gebruiker AUTO kiest; SolarPilot kiest nooit HEAT of COOL.',
                           'Nieuwe automatische coastperiodes vereisen voldoende modelzekerheid, een nuttig '
                           'minimumvenster en standaard een lange AUTO/OFF-vasthoudtijd om pendelen te '
                           'voorkomen.',
                           'PV-voorconditionering staat standaard UIT en kan alleen een toch al noodzakelijke '
                           'AUTO-herstart vervroegen; ze verandert het thermostaatdoel niet.',
                           'Ook in duidelijke zomer/winter coasten kan afzonderlijk worden toegestaan, maar '
                           'staat standaard UIT omdat de verwachte energiewinst onzeker is en comfort/COP '
                           'kunnen verslechteren.',
                           'Open raam- of deurcontacten worden bewust niet gebruikt door deze klimaatregeling. '
                           'De gevraagde langzame raamblokkering is dus niet geïmplementeerd.']},
              {'title': "9. Kwartierpiek, kosten en EMS-KPI's",
               'paragraphs': ['SolarPilot kan het actuele kwartiergemiddelde en de maandpiek gebruiken om een '
                              'softwarematig importbudget te berekenen. Voor Vlaanderen is een instelbare '
                              'facturatievloer voorzien; de standaard in deze configuratie is 2,5 kW.',
                              "Dag-KPI's voor import, export, PV, zelfconsumptie, geregeld verbruik en "
                              'indicatieve energiewaarde zijn toerekening en geen gecertificeerde '
                              'energiemeting. Ze mogen niet als veiligheidsinput worden gebruikt.',
                              'Een toekomstige batterij kan naast zelfconsumptie ook voor peak shaving worden '
                              'geëvalueerd, maar fabrikantbeveiligingen, zekeringen en de echte netaansluiting '
                              'blijven leidend.',
                              'De bestaande Geschatte energiekost op Planning blijft de netto raming voor de '
                              'komende ingestelde horizon (standaard 36 uur), niet de kost van vandaag. Per '
                              'planblok wordt netafname na aftrek van lokale PV berekend; injectievergoeding '
                              'wordt al van de afnamekost afgetrokken. De aparte uitsplitsing toont verwachte '
                              'netafnamekost, injectievergoeding en lokale zon.',
                              'Elektriciteitskost vandaag is een apart gemeten-tot-nu-toe-overzicht op '
                              'Overzicht, Planning en Energie: netafname in kWh en euro, injectie in kWh en '
                              'vergoeding, rechtstreeks gebruikte PV in kWh en vermeden netaankoop, en de '
                              'netto dagkost. De formule is uitsluitend netafnamekost min injectievergoeding. '
                              'Eigen PV verlaagt al de netafname en wordt niet nogmaals als korting van dat '
                              'resultaat afgetrokken.',
                              'Dagkosten worden opgebouwd uit geldige P1/PV-vermogenmetingen en de dan '
                              'ingestelde import- en exportprijs. Negatieve prijzen en netto negatieve '
                              'dagkosten blijven zichtbaar. Tariefwijzigingen prijzen eerder gemeten energie '
                              'niet opnieuw. De teller gebruikt de lokale datum en behoudt dagtotalen over '
                              'herstarts; uitgevallen of onbekende meetperioden worden niet verzonnen en staan '
                              'als onvolledige meetdekking vermeld.',
                              'Bij de eerste update worden bestaande SolarPilot-dagtotalen eenmalig '
                              'overgenomen en gewaardeerd tegen de op dat moment ingestelde tarieven. Die '
                              'voorhistorie krijgt een expliciet schattingslabel; daarna worden prijzen per '
                              'meetinterval verwerkt. Zonder ingeschakelde prijskoppeling wordt geen fictieve '
                              'kost van nul euro getoond.',
                              'Een onbeschikbare, restored, toekomstige of meer dan 36 uur oude dynamische '
                              'prijsbron valt terug op het ingestelde vaste tarief. Ongeldige rijen schuiven '
                              'de tijdposities van andere prijzen niet op; een ontbrekend tijdstip of '
                              'ontbrekende prijs krijgt de vaste terugvalprijs in plaats van een verzonnen tarief. '
                              'Een geldige nulprijs blijft nul en wordt niet als ontbrekend behandeld. '
                              'Booleans, niet als eindig getal te verwerken prijswaarden en ongeldige '
                              'tijden geven veilige vaste terugval, geen herinterpreteerd gratis tarief.',
                              'Rechtstreeks PV-verbruik kan zonder batterij uit productie en export worden '
                              'geschat. Bij een gekoppelde thuisbatterij wordt dit niet ten onrechte als '
                              'bewezen direct zonneverbruik getoond; netkosten blijven wel bruikbaar. De '
                              'eurobedragen zijn variabele energiekosten volgens de ingestelde tarieven, '
                              'exclusief vaste kosten, het capaciteitstarief, aanschaf en onderhoud; geen '
                              'factuurgarantie.'],
               'bullets': []},
              {'title': '10. Leren: wat wel en niet automatisch verandert',
               'paragraphs': ['SolarPilot leert lokaal en verklaarbaar. Het herschrijft zijn eigen code niet '
                              'en gebruikt geen externe AI-dienst voor de regeling.',
                              'Leerdata mag planning conservatiever maken, lokale PV beter corrigeren, een '
                              'faseclassificatie opbouwen, complete apparaatcycli samenvatten en het '
                              'thermische gebouwmodel verfijnen. Voor ruimteklimaat omvat dat lokale '
                              'zonnewinst, systematische weersvoorspellingsfout en het resultaat van eerdere '
                              'coastperioden. Voor beschermde cycli worden alleen volledige '
                              'start-tot-stopcycli met bruikbare vermogensmeting geaccepteerd; half '
                              'waargenomen of te korte cycli worden niet als profiel gebruikt. Leren mag geen '
                              'comfort-, hygiëne- of elektrische veiligheidsgrens zelfstandig versoepelen. '
                              'Voor ruimteklimaat betekent leren vooral beter voorspellen wanneer AUTO opnieuw '
                              'nodig is; niet zelf leren wanneer HEAT of COOL gekozen moet worden.'],
               'bullets': ['Niet automatisch leerbaar: prioriteiten, netlimieten, temperatuurminima, '
                           'sterilisatie, fasegrenzen, deadlines, toestemming voor netstroom en '
                           'batterij-eigenaarschap.',
                           'De echte toestand van apparaten en actuele metingen blijven belangrijker dan '
                           'historische verwachtingen.',
                           'Leergegevens kunnen worden gewist zonder dat vaste veiligheidsinstellingen '
                           'verdwijnen.']},
              {'title': '11. Eerste ingebruikname, migratie en concurrerende regelingen',
               'paragraphs': ['SolarPilot vervangt PV Excess Control volledig bij de definitieve ingebruikname '
                              'en gebruikt geen pv_excess_control_* runtime-entiteiten als bron. De twee oude '
                              'boilerautomatiseringen worden eveneens uitgeschakeld voordat SolarPilot de '
                              'boiler actief gaat regelen.',
                              'De eerste ingebruikname gebeurt gecontroleerd: eerst SolarPilot in Observatie '
                              'controleren, daarna de oude regelaar(s) uit, fysieke toestelstanden controleren '
                              'en vervolgens één niet-kritieke SolarPilot-last activeren.'],
               'bullets': ['PV Excess Control wordt bij go-live volledig uitgeschakeld.',
                           'Alle vervangen boiler- en PV-overschotautomatiseringen worden vóór overname '
                           'uitgeschakeld.',
                           'SolarPilot controleert de algemene PV Excess Control-hoofdschakelaar wanneer die '
                           'integratie aanwezig is; overige oude regelaars controleer je tijdens de migratie '
                           'expliciet.',
                           'Panasonic-sterilisatie blijft aan en Wallbox Full Solar blijft autonoom.']},
              {'title': '12. Logische interface en configuratiestructuur',
               'paragraphs': ['Het Configuratiecentrum groepeert bron- en toestelinstellingen als Overzicht, '
                              'Energie & net, Toestellen, Warmte & comfort, Auto & batterij, '
                              'laden, Voorspellen & optimaliseren en Geavanceerd & systeem. De dagelijkse '
                              'prioriteitsbediening staat op de eigen tab Voorrang; nadat die lijst is '
                              'gewijzigd verdwijnen de oudere, concurrerende prioriteitsvelden uit de '
                              'toestelwizard.',
                              'De publieke HACS-release bevat bewust geen woning- of installatie-specifieke '
                              "entity_id's. Wie geen privébundel gebruikt, kiest de net- en optionele PV-bron "
                              'en overige koppelingen expliciet via Home Assistant. Wie wel een privébundel '
                              'gebruikt, plaatst één lokaal bestand in de door HACS bewaarde userfiles-map; '
                              'SolarPilot vult daarmee alleen nog lege, bestaande bronkoppelingen in. '
                              'Ontbrekende entiteiten worden overgeslagen en later opnieuw geprobeerd. '
                              'Dezelfde bundel kan de geaggregeerde historische bootstrap bevatten. Import '
                              'schakelt nooit fysieke klimaatbediening, fase-afbouw of boilerregeling vrij. '
                              'Een eerste installatie begint veilig in Observatie; na latere Home '
                              'Assistant-herstarts wordt de opgeslagen modus alleen hervat nadat de actuele '
                              'toestelstatussen automatisch zijn gereconcilieerd. Als een eerder beheerd '
                              'toestel later laadt, blijft SolarPilot wachten en controleert het automatisch '
                              'opnieuw; daarna hervat de oorspronkelijke modus. Een later gekozen Alleen '
                              'bekijken of Pauze vervangt die bewaarde hervatkeuze. Minimum aan-/uittijden '
                              'starten conservatief bij de echte nieuwe waarneming en oude opdrachten '
                              'worden niet herhaald. Een numerieke toestelinstelling die tijdens de herstart '
                              'veranderd is, blijft bij haar huidige bediening: SolarPilot laat eigendom '
                              'los en respecteert de bestaande handmatige rusttijd zonder herstelwrite. '
                              'Een nieuwe betrouwbare lopende of voltooide AEG-fase van na de eerdere START '
                              'kan uitsluitend de specifieke herstartonzekerheid oplossen. Een oude '
                              'Washing/Finished-stand telt daarvoor niet. Een bevestigde cyclus verbruikt ook '
                              'haar bestaande APP-aanvraag, zodat later Idle geen oude belading opnieuw '
                              'klaarzet. Alleen oude Alleen bekijken-opslag zonder de nieuwe '
                              'hervatmarker kan éénmaal haar verloren Auto-keuze herstellen: uitsluitend '
                              'zonder echte fout of handmatige boilerbescherming en met een onderbroken '
                              'lease van een bekend Auto-toestel of een schoon routine-boilerhersteljournal. '
                              'Daarna voorkomt de expliciet opgeslagen marker, ook wanneer zij leeg is, '
                              'dat een bewuste Alleen bekijken- of Pauze-keuze ooit opnieuw wordt afgeleid.',
                              'Een tijdelijke oude, ontbrekende of onbeschikbare toestelrapportage is een '
                              'bronwacht, ook nadat de herstartcontrole al klaar is. SolarPilot toont '
                              'Automatische broncontrole, vraagt geen Controle afronden en leest bij de '
                              'volgende gewone regelrondes opnieuw. Na betrouwbaar bronherstel verdwijnt '
                              'die wachtreden zonder reset of oude opdrachtreplay. Een verkeerde of '
                              'ontbrekende vereiste bronkoppeling vraagt de configuratie te corrigeren; een '
                              'echte opdrachtfout behoudt haar eigen controle en veiligheidsvoorwaarden. '
                              'Controle afronden meldt geen geslaagde foutreset wanneer er alleen een '
                              'bronprobleem en geen foutjournal of herstelcontrole te wissen is. De '
                              'bestaande voorwaarden voor een echte reset blijven gelden; een actuele '
                              'onbekende of nog actieve betrokken last wordt niet automatisch vrijgegeven. '
                              'Een werkende regelmodule of beschermd programma krijgt door de bronwacht '
                              'geen nieuwe vrijgave en wordt niet blind uitgeschakeld.',
                              "De basispagina's tonen alleen de instellingen die je normaal nodig hebt. "
                              'Timing, faseherkenning en Wallbox-herkenningsdetails staan bewust onder '
                              'Geavanceerd. De onderliggende option-keys en regelalgoritmen blijven compatibel '
                              'met bestaande instellingen.',
                              'De dashboardkaart bevat negen herkenbare tabbladen: Overzicht, Voorrang, '
                              'Toestellen, Warmte & comfort, Planning, Energie, Batterij, Export en Uitleg. Modus en '
                              'belangrijke waarschuwingen blijven bovenaan. Voorrang bundelt de rangorde en '
                              'toestemming om autoladen te verminderen. Planning bundelt horizon, planfouten, '
                              'beschermde cyclusprofielen en what-if-replay. Zo hoeft niet alle informatie op '
                              'één scherm te staan.',
                              'Op mobiele schermen bevat het SolarPilot-paneel een eigen menuknop die het '
                              'normale Home Assistant-zijmenu opent; op desktop blijft de bestaande Home '
                              'Assistant-navigatie ongewijzigd.',
                              'Een verbruiker die fysiek aan staat krijgt een duidelijke AAN-status en visueel '
                              'accent. SolarPilot onderscheidt daarbij eigen beheer, externe activiteit en een '
                              'expliciete manuele start. Via Manueel starten kan de gebruiker na bevestiging '
                              'bewust netstroom gebruiken binnen de softwaregrenzen; de manuele toestand kan '
                              'daarna weer worden vrijgegeven zonder minimale looptijd of andere beveiligingen '
                              'te omzeilen.',
                              'De tab Comfort bevat voor slim klimaat nu vier samenhangende delen: '
                              'instellingen, bevindingen/leerresultaten, meldingen en uitleg. Iedere '
                              'klimaatinstelling uit het regelmodel is rechtstreeks wijzigbaar in Home '
                              'Assistant. Bij elk veld staat een korte uitleg, een aanbevolen uitgangspunt en '
                              'in gewone taal wat een lagere/hogere waarde of Aan/Uit betekent. Voor het '
                              'opslaan toont SolarPilot nogmaals het advies en de verwachte gevolgen.',
                              'Instellingen & onderzoek bevat snelkoppelingen naar toestelbeheer, PV-diagnose, '
                              'Leren & vragen, Export en de instellingenwizard. Alle algemene '
                              'exportverwijzingen komen bij de ene Export-pagina uit. Planning begint met Zon '
                              '& voorspelling; handmatige forecastbronnen blijven een geavanceerde terugval. '
                              'Toestellen en Auto laden tonen operationele status en een verwijzing naar '
                              'Voorrang, geen tweede rangorde-editor. Open popups, invoer en conceptvolgorde '
                              'worden niet opnieuw opgebouwd door een gewone live verversing.'],
               'bullets': ['Eerste installatie vraagt alleen de essentiële net- en PV-bronnen; een optionele '
                           'lokale privébundel kan daarna de overige bronkoppelingen en historische bootstrap '
                           'in één keer veilig invullen.',
                           'Toestellen worden toegevoegd via een duidelijke vierstappenwizard: basis, '
                           'koppeling, gedrag & bescherming, planning & energie.',
                           'Batterijprofiel en batterijbediening zijn gescheiden zodat read-only gebruik geen '
                           'bedieningsvelden toont.',
                           'Slim klimaat, fasebewaking en Wallbox hebben een korte basispagina en een aparte '
                           'geavanceerde pagina.',
                           'Dagelijkse bediening en klimaatfijnafstemming blijven op het dashboard; '
                           'Configureren is vooral bedoeld voor koppelingen en hoofdregels.',
                           'De dashboardkaart bewaart opengeklapte secties tijdens live telemetrie-updates. De '
                           'Uitleg-weergave wordt niet opnieuw opgebouwd wanneer alleen niet-zichtbare '
                           'realtime meetwaarden wijzigen, zodat lezen en scrollen niet om de paar seconden '
                           'worden onderbroken.',
                           'Er bestaan geen verborgen klimaat-tuningwaarden zonder dashboarduitleg: iedere '
                           'SMART_CLIMATE-instelling heeft één catalogusitem met betekenis, advies, gevolg en '
                           'aanbevolen standaard.',
                           'Ieder toestel heeft in de tab Toestellen een Geschiedenis-popup voor de eigen '
                           'draaitijd, sessies en beslisredenen; de popup blijft open tijdens live '
                           'telemetrie-updates.',
                           'Manuele start is een expliciete gebruikersoverride met bevestiging. Pauze en harde '
                           'veiligheids-/vermogensgrenzen blijven hoger staan; een manuele stop/vrijgave '
                           'respecteert de ingestelde minimale looptijd.']},
              {'title': '13. Eenvoudige installatie en volledige verwijdering',
               'paragraphs': ['Vanaf de publieke HACS-release is HACS de aanbevolen installatiemethode. Voeg '
                              'de publieke SolarPilot-repository één keer als HACS Custom Repository van het '
                              'type Integration toe, download SolarPilot en herstart Home Assistant. Daarna '
                              'voeg je SolarPilot toe via Apparaten & diensten. Voor een '
                              'installatie-specifieke snelle start kan één privébestand als '
                              '`custom_components/solar_pilot/userfiles/private_bundle.json` lokaal worden '
                              'geplaatst; HACS bewaart die map bij gewone updates. Via Geavanceerd & systeem → '
                              'Privéprofiel & historiek kan de bundel opnieuw worden ingelezen. De frontend '
                              'zit in dezelfde integratie en verschijnt automatisch in de Home '
                              'Assistant-zijbalk; een losse www-map, Lovelace-resource of handmatig '
                              'dashboard-YAML is niet nodig.',
                              'Het zijbalkpaneel en de automatisch beschikbare dashboardkaart gebruiken '
                              'hetzelfde gebundelde JavaScript-modulebestand. SolarPilot vermijdt daarmee '
                              'een combinatie van klassieke scriptlading en modulelading. Bij opnieuw '
                              'laden blijven de eigen kaartcatalogusitems enkelvoudig; kaarten van andere '
                              'integraties blijven behouden. Dit verandert geen toestelregeling of '
                              'fysieke toestemming.',
                              'Na een update herstart je Home Assistant volledig en open je de frontend '
                              'opnieuw, zodat een al open pagina niet met oude kaartcode blijft werken. '
                              'Herlaad de webpagina; stop op Android de Home Assistant-app volledig en '
                              'open haar opnieuw. Op iOS kun je de weergave naar beneden trekken om te '
                              'verversen. Controleer backend en geladen kaart afzonderlijk. Een melding '
                              'dat een custom panel niet geladen kan worden vraagt ook controle van '
                              'bestandslevering en de browser-/appfout; alleen die melding bewijst niet '
                              'welke oorzaak optreedt. Behoud configuratie en leerdata.',
                              'Voor verwijderen bestaat een veilige voorbereidingsactie. SolarPilot gaat naar '
                              'Pauze, stopt nieuwe starts, laat eigen onderbreekbare lasten volgens hun '
                              'beveiligingen vrijgeven, brengt een door SolarPilot veroorzaakte klimaat-coast '
                              'terug naar Panasonic AUTO en laat een door SolarPilot beheerd boilerdoel '
                              'terugvallen naar het normale basisregime. Beschermde cycli en onzekere fysieke '
                              'toestanden worden nooit hard afgebroken alleen om sneller te kunnen '
                              'verwijderen.',
                              "Wanneer SolarPilot 'Verwijderen gereed' meldt, verwijder je eerst de "
                              'SolarPilot-configuratie-entry via Apparaten & diensten. Daarbij wist SolarPilot '
                              'zijn eigen leer-/runtime-opslag, services, melding en zijbalkpaneel. '
                              'Onderliggende P1-, Panasonic-, Wallbox-, Shelly- en andere Home '
                              'Assistant-entiteiten worden nooit verwijderd. Verwijder daarna SolarPilot in '
                              'HACS en herstart Home Assistant; HACS beheert dan ook de programmabestanden '
                              'onder custom_components.'],
               'bullets': ['Installatie via HACS: repository één keer toevoegen, SolarPilot downloaden, '
                           'herstarten en daarna via de Home Assistant-UI configureren; een lokale privébundel '
                           'is optioneel en wordt nooit via GitHub verspreid.',
                           'Updates zijn cumulatief: tussenliggende beta-versies hoeven niet één voor één '
                           'geïnstalleerd of gepubliceerd te worden. De nieuwste release bevat de voorgaande '
                           'codefixes; Home Assistant-configuratie, userfiles en lokale leerdata blijven bij '
                           'een gewone HACS-update behouden.',
                           'Geen aparte /config/www/solar-pilot-card.js of dashboardresource nodig.',
                           "Verwijderen voorbereiden is veilig en weigert 'gereed' te melden zolang SolarPilot "
                           'nog een toestel, boiler, batterijopdracht of coasttoestand bezit.',
                           'De verwijderactie wist uitsluitend SolarPilot-eigen data en raakt de gekoppelde '
                           'apparaten/integraties niet aan.',
                           'Bij HACS-installatie beheert HACS ook updates en het verwijderen van de '
                           'programmabestanden; een handmatige mapverwijdering is normaal niet nodig.',
                           'De eigen dag-/sessiehistoriek van verbruikers wordt eveneens behouden bij gewone '
                           'updates en verwijderd bij definitieve verwijdering van de '
                           'SolarPilot-configuratie-entry.']},
              {'title': '14. Apparaatgeschiedenis en draaitijd per toestel',
               'paragraphs': ['Open het SolarPilot-dashboard → Toestellen en klik bij een toestel op '
                              'Geschiedenis. De knop toont ook de geregistreerde draaitijd van vandaag. De '
                              'aparte, uitsluitend uitlezende popup toont per gekozen dag de totale '
                              'aan-/actieve tijd, het aantal bevestigde starts en stops, een tijdlijn en de '
                              'afzonderlijke sessies. Met de datumkiezer of de balkjes van 7/30 dagen kies je '
                              'een eerdere dag.',
                              'Per sessie worden begin, einde, duur, startreden en stopreden bijgehouden. Een '
                              'bevestigde SolarPilot-opdracht krijgt de werkelijk geregistreerde beslisreden, '
                              'bijvoorbeeld voldoende overschot, aanhoudend tekort, Pauze, een taaklimiet of '
                              'Wallbox-voorrang. Een aangevraagde of mislukte opdracht alleen is geen '
                              'succesvolle start. Externe wijzigingen worden apart gemarkeerd; zonder verdere '
                              'broninformatie wordt geen specifieke gebruiker of automatisering als oorzaak '
                              'verzonnen.',
                              'Draaitijd betekent hier de waargenomen aan-/actiefstatus van de geconfigureerde '
                              'statusbron. Bij een slimme stekker is dat de tijd dat de stekker aan staat, '
                              'niet noodzakelijk de tijd dat de compressor ononderbroken draait. Het tijdstip '
                              'volgt het meetritme (standaard 5 seconden) en is geen milliseconde-nauwkeurige '
                              'fysieke startmeting. Deze registratie verandert geen compressor-minimumtijden, '
                              'prioriteiten of schakeltoestemmingen.',
                              'Een al ingeschakeld toestel bij het begin van registratie krijgt begin '
                              'onbekend. Herladen, herstarten, onbeschikbare status of een te groot meetgat '
                              'beëindigen alleen de waarnemingsperiode, niet het fysieke toestel. De popup '
                              'markeert die onderbreking en telt onbekende tijd niet mee. Een sessie over '
                              'middernacht wordt per lokale kalenderdag opgesplitst; zomer-/wintertijd kan een '
                              'dag 23 of 25 uur maken.',
                              'De registratie begint na installatie van de versie met deze functie. Eerdere '
                              'start-/stopredenen worden niet uit forecasts, algemene leerdata of oude '
                              'dagtotalen gereconstrueerd. Een eerste of onvolledig gemeten dag wordt '
                              'expliciet als onvolledig getoond. De geregistreerde sessies blijven bewaard bij '
                              'gewone updates en herstarts; ontbrekende tijd tijdens stilstand blijft '
                              'onbekend.',
                              'De popup blijft open tijdens live dashboardupdates en bewaart de gekozen dag, '
                              'scrollpositie en open details. De volledige sessielijst wordt pas opgevraagd '
                              'bij openen, datumwissel of vernieuwen, en periodiek zolang de popup open is. In '
                              'de gewone vijfsecondenstatus staat alleen een compacte dagsamenvatting; er '
                              'komen geen extra cloudverzoeken of apparaatopdrachten bij.'],
               'bullets': ['Historiek blijft lokaal in eigen Home Assistant-opslag, per verbruiker maximaal 30 '
                           'kalenderdagen. Per verbruiker worden maximaal 2000 sessies en 300 aanvullende '
                           'gebeurtenissen bewaard. Wanneer de detailgrens is bereikt, blijven de dagtotalen '
                           'staan en wordt de onvolledigheid van de sessiedetails gemeld.',
                           'Schrijven naar opslag gebeurt gebundeld: bij veranderingen en ongeveer iedere '
                           'minuut tijdens doorlopende registratie, niet bij elke vijfsecondenmeting. Bij een '
                           'abrupte stroomuitval kan het nog niet opgeslagen laatste stukje ontbreken; dat '
                           'wordt niet achteraf als zekere draaitijd aangevuld.',
                           'De historiek wordt ook uitlezend bijgehouden in Observatie of bij externe '
                           'bediening, zolang de gekoppelde statusbron beschikbaar is. Dit neemt een extern '
                           'gestart toestel niet over.',
                           'De popup gebruikt de bestaande Home Assistant-verbinding en leesrechten. Het '
                           'openen, kiezen van een dag en verversen kan geen toestel schakelen. Na sluiten '
                           'stopt de aparte popup-verversing.',
                           'Normale HACS-updates behouden de nieuwe historiek. Bij definitief verwijderen van '
                           'de SolarPilot-configuratie-entry wordt uitsluitend de eigen historieopslag samen '
                           'met de andere SolarPilot-data gewist; de gekoppelde apparaten blijven bestaan.']},
              {'title': '15. Uitleg bij iedere instelling',
               'paragraphs': ['Open in het SolarPilot-dashboard Configureren met uitleg ?. De geïntegreerde '
                              'wizard gebruikt dezelfde Home Assistant-optiesflow en dezelfde servervalidatie '
                              'als de standaard configuratie. Er worden geen beveiligingen omzeild. Alleen een '
                              'HA-beheerder kan configureren; instellingen zijn ook tijdens Zonnestroom '
                              'toegankelijk. Gewone wijzigingen worden live toegepast; gevoelige wijzigingen '
                              'wachten alleen op de betrokken veilige grens.',
                              'Bij iedere ondersteunde optie staat een vraagteken. Hover/focus toont een korte '
                              'toelichting; klikken of tikken opent volledige uitleg met betekenis, gevolgen, '
                              'uitgangspunt en relevante grenzen. De hulp staat buiten de live kaartopbouw en '
                              'blijft open bij nieuwe telemetrie. De uitleg zelf kan geen instellingen opslaan '
                              'of apparaten bedienen.',
                              'De complete Nederlandse uitleg komt uit option_help.py samen met de bestaande '
                              'klimaat-/plannercatalogi. Het gegenereerde frontend-catalogusbestand en de '
                              'korte native HA-veldtoelichtingen worden tijdens dezelfde release vernieuwd en '
                              'gecontroleerd. De klassieke HA-formulieren blijven beschikbaar als terugval; '
                               'hun icoonpresentatie hangt af van Home Assistant. De vaste klikbare vraagtekens '
                               'horen bij de geïntegreerde SolarPilot-configuratiewizard en de directe '
                               'dashboardinstellingen.',
                               'Bij opslaan leest de geïntegreerde wizard uitsluitend benoemde invoervelden '
                               'binnen het actuele formulier. Daardoor blijft hij bruikbaar in Home '
                               'Assistant-frontends waarin de algemene form.elements-verzameling niet is '
                               'geïmplementeerd. Browservalidatie en de bestaande Home Assistant-optiesflow '
                               'blijven leidend; een leesfout geeft zichtbare feedback en bewaart niets.',
                               'De lokale uitlegcode en catalogus worden pas bij gebruik geladen; ze bevatten '
                              'geen privédata. Er worden geen extra externe API-aanvragen voor hulp, '
                              'nachtregeling of avondplanning gedaan.'],
               'bullets': []},
              {'title': '16. AEG-afwasmachine — fysieke APP-vrijgave, vaste startdeadline en bewaard einde',
               'paragraphs': ['De afzonderlijke AEG/Electrolux start-only adapter verstuurt uitsluitend '
                              'button.press naar de gecontroleerde oorspronkelijke START-knop. Een nieuw '
                              'toestel blijft Uitgesloten en de koppelingen moeten bewust worden bevestigd. '
                              'Bestaande handmatige profielen blijven handmatig; kies APP-vrijgave expliciet '
                              'bij aanpassen. De nieuwe profielwizard stelt APP voor zonder fysieke bediening '
                              'alvast aan te zetten.',
                              'In APP-modus is uitsluitend een nieuw waargenomen overgang naar exact Enabled '
                              'een aanvraag voor één belading. Not Safety Relevant Enabled is geen '
                              'starttoestemming. Een native afteltimer wordt niet ingesteld, gewijzigd of '
                              'geannuleerd. Geen extra klaarzetknop in SolarPilot. Ready To Start, actuele '
                              'verbinding, gesloten deur, programma en alarmcontrole blijven vereist voor de '
                              'uiteindelijke start; Unavailable in de aanvullende Cycle phase mag deze '
                              'gereedstand niet blokkeren. ConnectivityState is daarbij de actuele '
                              'bereikbaarheidsheartbeat. Een ongewijzigde Ready To Start-, deur-, programma- '
                              'of exact Enabled-status verloopt niet meer kunstmatig na vijf minuten alleen '
                              'omdat Home Assistant geen identieke toestand opnieuw heeft gemeld. '
                              'Unknown, Unavailable, restored of een werkelijk onveilige waarde blokkeert nog '
                              'steeds fail-closed. Ook No Program geldt expliciet niet als een geselecteerd '
                              'programma.',
                              'Standaard geldt 13:00 als uiterste starttijd. Een aanvraag vóór 13:00 wordt op '
                              'dezelfde dag gepland; een aanvraag op of na 13:00 wacht tot de volgende '
                              'kalenderdag. Die volgende dag wordt eerst zon benut, maar uiterlijk 13:00 mag '
                              'netstroom aanvullen wanneer die expliciete optie aanstaat. Een bewolkte dag '
                              'schuift de aanvraag niet weer door. De optie na de deadline is instelbaar; '
                              'standaard Volgende dag, alternatief Nog dezelfde dag. Het schema en de '
                              'gebruikte tijdzone worden bij de knopdruk vastgelegd en blijven over herstart '
                              'behouden.',
                              'Voor een zonnestart geldt de ingestelde stabiele injectietijd, bij een nieuw '
                              'AEG-profiel 300 seconden. Op de startdeadline vervalt alleen die '
                              'zonnevoorwaarde en -wachttijd, niet de geldige net-/fase-/kwartierpiekmeting, '
                              'fysieke ruimte, globale Zonnestroommodus of apparaatvrijgave. De deadline is '
                              'geen garantie wanneer Home Assistant, de cloud of een interlock niet '
                              'beschikbaar is. Een overschrijding van meer dan 30 seconden geeft eenmaal een '
                              'HA-melding. Een nog niet verzonden start mag standaard nog 120 minuten na de '
                              'deadline bij herstelde voorwaarden plaatsvinden; daarna is een nieuwe '
                              'APP-aanvraag nodig.',
                              'De aanvraag wordt vóór START duurzaam als geprobeerd vastgelegd. Alleen een '
                              'nieuwe Running-terugmelding na de opdracht bevestigt de echte start. Een '
                              'onzekere of mislukte opdracht wordt niet herhaald, ook niet na herstart. '
                              'Ook herstel van die onzekerheid vraagt een nieuwe betrouwbare lopende of '
                              'voltooide fase-terugmelding van ná START; een oude fase wordt geen nieuw bewijs. '
                              'Handmatig starten verbruikt dezelfde aanvraag, zodat er om 13:00 geen tweede '
                              'START volgt. Opnieuw geopende deur vóór start, ander programma, gewijzigde '
                              'bronkoppelingen of ingetrokken APP-vrijgave annuleren de wachtende aanvraag. '
                              'Een eerste installatie met APP al aan neemt dat niet aan als nieuwe knopdruk: '
                              'eenmaal APP uit en aan. Reconnect en herstart maken nooit een nieuwe belading.',
                              'End Of Cycle wordt direct via een op de relevante entiteiten gerichte '
                              'HA-statuslistener vastgelegd, zonder vijfsecondenpolling of minimumduur. '
                              'Eindtijd en bevestiging blijven lokaal bewaard na Off, Unavailable, '
                              'Disconnected en herstart. De kaart toont klaar met het tijdstip; dat betekent '
                              'niet leeggemaakt. Een korte verbindingsonderbreking midden in de cyclus is geen '
                              'einde. Alleen Off zonder gezien eindesignaal krijgt einde niet bevestigd. '
                              'Onbekende starttijd wordt niet als exact duurgegeven ingevuld.',
                              'Ado Drying en de geopende AirDry-deur betekenen nadrogen, niet stoppen, nieuwe '
                              'start of een lege machine. Het programma blijft beschermd tot het echte einde. '
                              'SolarPilot verstuurt geen PAUSE, RESUME, STOPRESET, programmakeuze of '
                              'Shelly-relaisopdracht. Ook Pauze, Wallbox-voorrang, wolken of annuleren van een '
                              'klaarzetaanvraag onderbreken de reeds gestarte beurt niet.',
                              'De optionele AEG-alarmvlagmodus inspecteert de DISH_ALARM-attributen in plaats '
                              'van alleen het tellertje. Technische alarmvlaggen moeten OFF zijn; onbekende '
                              'vlaggen of ontbrekende informatie blokkeren. Alleen de benoemde zout- en '
                              'glansmiddelmeldingen tellen niet als startblok. De toestandmodus blijft '
                              'beschikbaar voor andere expliciete alarmbronnen. SolarPilot koppelt een '
                              'optionele numerieke AEG Alerts-sensor niet meer automatisch als veiligheidsbron '
                              'wanneer daarmee geen echte DISH_ALARM-vlaggen bewezen kunnen worden. Een bewust '
                              'handmatig gekoppelde alarmbron blijft wel volgens de gekozen fail-closed-regel '
                              'werken.',
                              'De Shelly wordt alleen als exclusieve vermogensmeter gebruikt. Het voorlopige '
                              'vermogen voor nieuwe profielen is 2000 W, een handmatig te controleren '
                              'planningsschatting, geen geverifieerde specificatie. Bestaande fasegemiddelden '
                              'zijn geen veilige pieklimiet. Zonder meter wordt geen gemeten faseprofiel '
                              'verzonnen. Met echte W/kW-data gebruikt de aanvullende Cycle phase '
                              'voorwas/wassen/drogen/nadrogen als meetfase; alleen volledige cycli met '
                              'voldoende dekking worden als gemeten profiel geleerd. Onbekende fasen zijn niet '
                              'nul. De vaste 13:00-regel is geen belofte dat alle latere programmafasen '
                              'uitsluitend op zon lopen.',
                              'De analyse-export bevat de APP-aanvraag, geplande dag/deadline, laatste '
                              'aanvraaguitkomst, verbruikte toestemming, Running-/End Of Cycle-waarnemingen en '
                              'bewaarde voltooiing naast alle eerder beschikbare SolarPilot-modellen en '
                              'meetgegevens. Alles blijft lokaal totdat een beheerder bewust exporteert.',
                              'Ook de afzonderlijke AEG-overname van EV-zonnevermogen vereist nu een '
                              'bevestigde effectieve zonnelaadsessie. Bij manueel of onbekend laden wordt vóór '
                              '13:00 alleen echt restoverschot gebruikt. De ingestelde 13:00-nettoestemming '
                              'blijft apart, evenals comfort- en elektrische limieten. Een al begonnen '
                              'programma wordt nooit afgebroken wegens een latere manuele autosessie.',
                              'Het bestaande AEG-voorkeursprofiel blijft bij deze update behouden: gewoon warm '
                              'water, noodzakelijke avondvoorraad en vloerverwarming eerst; daarna de '
                              'afwasmachine, de Wallbox, lagere automatische lasten en extra boilerwarmte. '
                              'Een gewone nieuwe installatie schakelt geen fysieke starttoestemming, '
                               'bronbevestiging of Auto-deelname in. De beta.38-herstelmigratie voor de eerder '
                               'al gebruikte AEG-koppeling kan een verdwenen profiel éénmalig als Auto '
                               'herstellen. Beta.39 repareerde uitsluitend zo’n door beta.38 aangemaakt profiel '
                               'wanneer de eerdere herstelstap een te beperkte faselijst of een onbewezen automatische '
                               'alarmbron had opgeslagen. Beta.40 houdt de herstelcontrole na SolarPilot-start '
                               'nog tien minuten gericht actief wanneer Home Assistant de herstelmarkers of '
                               'AEG-entiteiten later laadt. Ook dat maakt geen APP-aanvraag en verstuurt geen START. '
                              'Zolang je de centrale lijst niet wijzigt, rangschikt het bewaarde '
                              'getal binnen de bestaande groepen. Na een bevestigde wijziging bepaalt de '
                              'centrale lijst de relatieve volgorde; de gewone comfortbescherming blijft '
                              'gelden. Een voorkeur-AEG blijft vóór de extra boilerwarmte. De toestemming voor '
                              'het benutten van EV-zonnevermogen staat dan uitsluitend in die centrale editor.',
                               'Een vandaag startklare APP-aanvraag die aantoonbaar in de veilige startpool past '
                               'krijgt één startkans vóór extra 60 °C. Een aanvraag voor morgen doet dat vandaag '
                               'niet. Een al lopende beurt is geen algemeen verbod: haar nog niet gemeten '
                               'nominale afwasvermogen wordt als reserve afgetrokken. Alleen wanneer na die '
                               'reserve, huisreserve, batterijontlading en open toesteltoezeggingen nog genoeg '
                               'werkelijke net- én PV-ruimte overblijft, mag extra 60 °C daarnaast werken. De '
                               'gewone 50 °C en een benodigde avondvoorraad tot de gekozen limiet blijven '
                               'beschikbaar. Een '
                               'eerder zelf aangevraagd extra hoog doel valt volgens de bestaande vertraging en '
                               'bescherming terug; fabrikantsterilisatie en handmatige functies worden niet '
                               'verlaagd. Afwasvoorrang verandert geen vloer-, compressor-, Powerful-, '
                               'Force-DHW- of andere warmtepompopdracht.',
                              'De ontvochtiger mag kleine restjes gebruiken zolang er niet genoeg beschikbaar '
                              'kan worden gemaakt voor de afwas. Pas na de afwas-startstabiliteit wordt een '
                              'benodigde lagere, eigen, daadwerkelijk gemeten onderbreekbare last vrijgegeven. '
                              'Het minimum aan/uit en handmatige eigenaarschap blijven gelden. Eén '
                              'stopopdracht moet bevestigd zijn en een nieuwe netmeting beschikbaar voordat de '
                              'afwas kan starten. Voldoende ruimte voor beide betekent dat beide mogen '
                              'draaien. Gewone warmtepompacties worden eerst afgehandeld; reeds lopend '
                              'warmteverbruik zit in P1 en wordt niet als vrije zonne-energie voorgesteld.',
                              'Bij voldoende stabiele werkelijke zonneproductie kan een vrijgegeven afwasbeurt '
                              'ook zonnevermogen benutten dat de Full Solar-laadpaal momenteel gebruikt. In de '
                              'actieve centrale lijst moet de afwasmachine vóór de Wallbox staan en Ja, als '
                              'het veilig kan geselecteerd hebben. Zolang de centrale lijst nog niet is '
                              'aangepast, blijft de eerder gekozen uitkomst ongewijzigd gelden. Actuele geldige Full Solar-status, conservatief '
                              'gecombineerd ruw/gefilterd netvermogen, de bestaande maximale overnamestap en '
                              'voldoende PV blijven noodzakelijk. De volledige nieuwe belasting moet binnen de '
                              'actuele elektrische, kwartierpiek- en fasegrenzen passen vóór de Wallbox '
                              'reageert. Dit vergroot nooit elektrische capaciteit en verstuurt geen opdracht '
                              'naar de Wallbox.',
                              'Deze start van een beschermd programma is niet dezelfde regeling als de '
                              'terugneembare overname voor onderbreekbare lasten. Bij de afwasmachine bepaalt '
                              'Mag de auto minder laden? rechtstreeks of deze beschermde start zonnevermogen '
                              'mag benutten dat de auto op dat moment gebruikt. De belasting '
                              'verlaagt het door Wallbox gezien overschot; Full Solar moet autonoom reageren. '
                              'Tijdelijke netafname en latere netaanvulling kunnen niet worden uitgesloten. Na '
                              'START wordt de nieuwe actieve toestelstatus en netto energiebalans '
                              'gecontroleerd. Dit is zonder Shelly geen bewijs van gemeten afwasvermogen of '
                              'causale vermogensoverdracht. Een ontbrekende balans na 15 minuten geeft een '
                              'melding en blokkeert toekomstige EV-gebaseerde starts voor deze afwasmachine '
                              'tot gecontroleerd herstel. De huidige beurt wordt nooit afgebroken.',
                              'Ook met deze prioriteit blijven de fysieke APP-vrijgave, Ready To Start, '
                              'gesloten deur, geldige verbinding, storingscontrole, één toestemming per beurt, '
                              '13:00-deadline en volgende-dagkeuze behouden. Om 13:00 vervalt met toestemming '
                              'alleen de zonnevoorwaarde. Comfortreserveringen, fabrikantbescherming, '
                              'elektrische ruimte en lopende opdrachten mogen niet door de deadline worden '
                              'omzeild. Te weinig vermogen of een storing kan daarom een deadline missen; de '
                              'bestaande melding en begrensde hersteltermijn blijven gelden.',
                              'Zonder een exclusieve Shelly-meter wordt geen gemeten faseprofiel verzonnen. '
                              'Tijdens een onbekend elektrisch verloop reserveert deze voorkeursregeling de '
                              'ingestelde nominale stap extra conservatief voor latere pieken, ook als een '
                              'lopende onbeheerde afwas weinig lijkt te verbruiken. Dat kan minder kleine '
                              'restverbruikers toelaten; de reservering is een schatting en geen meting. Een '
                              'gemeten meter laat de bestaande berekening voor nog onbenut toegezegd vermogen '
                              'werken. De fasegewijze optimalisatie van het APP-startmoment op de zonprognose '
                              'is bewust nog NIET actief: die hoort bij de later gevraagde Shelly-update. Alle '
                              'besluiten, reserveringen, voorrang en balansmeldingen staan in '
                              'dashboard/analyses.'],
               'bullets': ['Voor nieuwe AEG-profielen wordt prioriteitsgetal 10 voorgesteld. Het actieve '
                           'voorkeursprofiel gaat ook bij oude gelijke getallen boven de gewone ontvochtiger; '
                           'minlooptijden gaan voor.',
                           'Een definitief End Of Cycle wordt nog altijd eventgestuurd opgeslagen; AirDry, Off '
                           'en Disconnected zijn geen nieuwe belading.',
                           'Normaal boilerdoel 50 °C en bewaakte comfortgrens 46 °C blijven onafhankelijk. '
                           'Geen hersteldoel van 52 °C en geen beloofde fysieke 46 °C-garantie.',
                           'De actuele release behoudt alle APP-, deadline-, einddetectie- en prioriteitsregels. '
                           'Softwareproeven gebruiken fictieve apparatuur; een echte start blijft afhankelijk '
                           'van de live AEG- en Home Assistant-terugmeldingen.']},
              {'title': '17. Export — één onderzoeksbestand voor alle SolarPilot-functies',
               'paragraphs': ['Open Export → Export samenstellen. Een Home Assistant-beheerder kiest 1 uur, 24 '
                              'uur of 7 dagen en downloadt één gestructureerd JSON-bestand voor handmatige '
                              'analyse. Dit wijzigt geen instellingen, verstuurt geen toestelopdracht en '
                              'uploadt niets. Het bestand bevat release/schema, tijdzone, '
                              'instellingen/effectieve regels, de centrale voorrang met toestemmingen en vaste '
                              'bescherming, actuele bronwaarden/attributen, rapportleeftijden, modellen, '
                              'besluiten, fouten en werkelijk beschikbare historie voor verbruikers/AEG, '
                              'tapwater, klimaat, PV/forecast, net/fasen/kwartierpiek, Wallbox, dagkosten, '
                              'planner en batterijsimulatie. Ontbrekende gegevens worden niet aangevuld. Niet '
                              'geconfigureerde onderdelen blijven herkenbaar. Dit onderzoeksbestand is geen '
                              'herstelbare Home Assistant-back-up.',
                              'Snelle analysepunten bewaren naast de toestand ook de actuele probleemreden '
                              'en probleemsoort: bronwacht, bronconfiguratie of echte opdrachtfout. Dit '
                              'maakt opeenvolgend wachten en herstellen gericht uitlegbaar zonder '
                              'fysieke proefopdracht of nieuwe cloudpolling.',
                              'De registratie gebruikt bestaande HA-toestanden, geen extra cloudpolling. '
                              'Standaard wordt iedere vijf minuten een gedetailleerde momentopname bewaard, '
                              'maximaal zeven dagen/2016 ronden, 20000 bronwijzigingen en 6000 gebeurtenissen. '
                              'Relevante entiteiten van dezelfde gekoppelde apparaten mogen mee; maximaal 250 '
                              'bronnen, expliciete eerst. Tot 50 extra relevante bronnen zijn configureerbaar. '
                              'De laatste maximaal twee uur/1440 snelle regelcycli blijven in RAM. Verkorting '
                              'van het interval kan de bewaarde periode verkorten door de vaste aantallimiet. '
                              'Bewaren gebeurt gebundeld; na een herstart blijven opgeslagen gegevens, niet de '
                              'RAM-historiek, behouden.',
                              'Alleen eigen SolarPilot-WARNING/ERROR-logs en beslisnotities worden verzameld, '
                              'niet de volledige Home Assistant-logbestanden of automatiseringscode. De export '
                              'vermeldt de aangevraagde periode naast de beschikbare ruwe periode, werkelijk '
                              'gedekte meettijd, dekking, eerste en laatste bruikbare sample, herstarts, '
                              'bepaalbare offline/gattijd en beschikbare snelle telemetrie. Er is geen '
                              'terugwerkende Recorder-import: bootstrap-/historische data, echte '
                              'SolarPilot-live leerdata, berekende startprofielen en actuele metingen worden '
                              'afzonderlijk benoemd. Een planberekening telt nooit als extra leerdag of '
                              'meettijd. Doorlooptijden zijn geen CPU-percentages en bewijzen niet wat de '
                              'fysieke apparaten verbruiken.',
                              'Standaard worden entiteitsnamen en apparaatlabels per bestand gepseudonimiseerd '
                              'met consistente koppelingen tussen instellingen en metingen. IDs en verwijzingen '
                              'blijven onderling gekoppeld; schema-sleutels, eenheden, enums en analysebetekenis '
                              'blijven behouden. Ook korte en historische labels krijgen dezelfde bescherming. '
                              'Een expliciete '
                              'checkbox kan de werkelijke namen opnemen. Tokens/wachtwoorden, netwerkadressen, '
                              'accountgegevens en locatievelden worden gefilterd; camera-, person-, tracker-, '
                              'slot- en media-entiteiten worden niet geëxporteerd. De export bevat wel '
                              'tijdstippen en gebruikspatronen: controleer zelf vóór delen, geen '
                              'anonimiteitsgarantie. Plaats analysebestanden nooit in de publieke '
                              'GitHub-repository.',
                              'Maken van het bestand is alleen beschikbaar via de geauthenticeerde '
                              'admin-WebSocket. Verzoeken zijn geserialiseerd en begrensd; '
                              'pseudonimisering/JSON-opbouw draait buiten de event loop. Boven 16 MB '
                              'verschijnt een fout met de vraag een kortere periode te kiezen, niet een '
                              'stilzwijgend onvolledig bestand. Open formulieren en details blijven tijdens '
                              'gewone dashboardupdates behouden. Lokale analyseregistratie kan afzonderlijk '
                              'uit; de energieregeling blijft dan werken.',
                              'De effectieve configuratie en bronselectie worden ook uit read-only '
                              'configuratiemappings gelezen. Gekoppelde net-, toestel-, klimaat- en '
                              'overige bronnen blijven daardoor aanwezig naast automatisch gevonden '
                              'forecastbronnen. Die volledigheidsreparatie verandert geen privacyfilters, '
                              'maximale bronlijsten, pseudonimisering of toestemming; een werkelijk '
                              'ontbrekende bron blijft herkenbaar ontbrekend.',
                              'De export bevat aanvullend de effectieve Wallbox-sessiebron met gemaakte '
                              'classificatie, de per-toestelkeuze voor vermogensovername en de PV-kalibratie '
                              'met ruwe/gecorrigeerde/werkelijke kwartieren, clipping-/afwijsredenen, '
                              'brondekking en modelversie. Alleen automatisch gevonden relevante '
                              'forecastbronnen worden toegevoegd, niet de rest van Home Assistant. API-keys en '
                              'locatiegegevens van Forecast.Solar staan niet in de bronmetadata. Een export '
                              'blijft privé ondanks pseudoniemen.'],
               'bullets': []},
              {'title': '18. Leren & vragen — meetkwaliteit, bijsturen en jouw keuzes',
               'paragraphs': ['SolarPilot leert lokaal uit expliciet gekoppelde bronnen. Geen universele AI '
                              'die alle apparaten perfect kent, geen zelfwijzigende code en geen nieuwe '
                              'fysieke schakelproeven om data te verzamelen. Elke module toont zijn eigen '
                              'gegevens, herkomst, meetdekking en bevoegdheid. Thermische modelzekerheid, '
                              'basislastvertrouwen, voorspelkwaliteit en uitvoeringstreffers zijn '
                              'verschillende grootheden. Een hoge score geeft geen veiligheidsgarantie.',
                              'Gecontroleerd faseleren mag een vermogensstap alleen aan een toestel '
                              'toeschrijven wanneer de andere gekoppelde meters stabiel en hun '
                              'beginmetingen bruikbaar waren. Gelijktijdige veranderingen maken die '
                              'waarneming ongeschikt als eigen fasebewijs. Oude gecontroleerde '
                              'fasewaarnemingen zonder opgeslagen isolatiebewijs worden bij upgrade niet '
                              'hergebruikt; geldige passieve en nieuwe geïsoleerde fasewaarnemingen, '
                              'handmatige fasekeuzes en instellingen blijven behouden. Ongeldige '
                              'opgeslagen leerregels worden afzonderlijk overgeslagen; geen algemene leerreset.',
                              'Het basislastmodel leert nu ook tijdens EV-laden of het draaien van beheerde '
                              'apparaten als de eigen vermogensmeting daarvan actueel, eenduidig en '
                              'afzonderlijk is. De restlast is net + PV + getekende batterijontlading minus '
                              'gemeten Wallbox en gemeten beheerde last. Onbekend, geschat, dubbel, '
                              'asynchroon, overgangsbedrijf of niet-plausibele balans wordt niet als nul '
                              'aangeleerd. Voor batterijvloten is deze nieuwe correctie nog niet gevalideerd; '
                              'dan blijft die leerwaarneming onbekend. Dat verandert de aparte '
                              'batterijbesturing niet.',
                              'Duidelijke Panasonic-activiteit wordt vanaf beta.36 apart geclassificeerd als '
                              'ruimteverwarming, ruimtekoeling, tapwaterverwarming, '
                              'legionella/sterilisatie of onbekende warmtepompactiviteit en wordt niet als '
                              'normale huishoudelijke basislast aangeleerd. Zonder afzonderlijke elektrische '
                              'W-meter mag SolarPilot uit voldoende stabiele P1+PV-veranderingen rond duidelijke '
                              'compressorstarts/-stops een conservatieve vermogensschatting leren met eigen '
                              'betrouwbaarheid. Die schatting is uitsluitend voor planning en classificatie en '
                              'wordt nooit van de realtime gemeten vrije netruimte afgetrokken.',
                              'De oorspronkelijke basislastlearner blijft na minimaal vier verschillende dagen '
                              'per uur en dagtype een live mediaan gebruiken. De nieuwe aanvullende recente '
                              'variant gebruikt de laatste veertien dagen. Vergelijkingen trainen alleen op '
                              'dagen VOOR de getoetste dag, nooit op de te voorspellen dag zelf. Na minimaal '
                              'vier vergelijkingsdagen, minimaal 10% EN 20 W minder absolute fout en jouw '
                              'toestemming kan de recente variant worden gebruikt. De verandering is per vak '
                              'maximaal ±25% van het gewone profiel. Bij niet meer voldoen valt dat vak terug '
                              'naar het gewone profiel. Dit is historische rolling-origin vergelijking, geen '
                              'garantie voor morgen of causaal gemeten energiebesparing.',
                              'Standaard verzamelt en beoordeelt SolarPilot de recente variant, maar vraagt '
                              'toestemming voordat die wordt toegepast. Alleen de voorspelde basislast wordt '
                              'daarmee aangepast; de actuele overschotberekening, deadlines, temperaturen, '
                              'minimumlooptijden, prioriteiten, hygiëne en toestemmingen voor netstroom '
                              'blijven onaangeroerd. De andere bestaande modellen gebruiken hun eigen al '
                              'ingestelde vrijgaven. Toestelvermogen en Wallbox-respons leren schakelt niet automatisch elk '
                              'afzonderlijk model in of uit.',
                              'De daglicht-PV-fout (voorspeld of gemeten vermogen minstens 100 W), richting '
                              'van de fout, gemeten dagen en nieuwe dekking staan apart. De PV-kalibratie '
                              'toont daarnaast fout en bias voor ochtend, middag en namiddag. Dekking telt '
                              'alleen korte intervallen tussen opeenvolgende geldige waarnemingen; oude '
                              'historie wordt niet retrospectief als live dekking ingevuld. Voor de gewone '
                              'basislast worden warmtepompperioden niet meegeteld. De verschillende fouten en '
                              'de dekking worden afzonderlijk getoond, niet samengeperst tot één '
                              'misleidende totaalscore.',
                              'Open Leren & vragen op het dashboard. De popup toont rekenmodellen, ontbrekende '
                              'meters, voorspelfouten, vragen met keuzes, geaccepteerde en geweigerde '
                              'leerwaarnemingen, en jouw antwoordgeschiedenis. Alleen een Home '
                              'Assistant-beheerder kan antwoorden. Oude of dubbel gebruikte antwoorden worden '
                              'opnieuw gecontroleerd en zo nodig geweigerd. Een vraag heeft nooit een '
                              'stilzwijgend akkoord bij timeout. Nu configureren en Analyse-export openen '
                              'navigeren alleen naar die functie.',
                              'Je kunt een vraag uitstellen, een huidige keuze behouden of begrensde '
                              'voorspellingadaptatie toestaan. Zonder antwoord blijven de bestaande rechten en '
                              'het gewone profiel staan. De leerinstellingen zijn later terug te draaien. De '
                              'optionele HA-melding gebruikt een eigen melding-ID, maximaal eenmaal per 24 uur '
                              'bij nieuwe vragen; geen push- of ChatGPT-bericht. De popup blijft bestaan '
                              'tijdens gewone vijfsecondenupdates, vraagt alleen geopend elke minuut volledige '
                              'gegevens en stopt bij sluiten.',
                              'Per uur/dagtype blijven maximaal zestig dagen geaggregeerde basislastgegevens '
                              'staan; de leervragengeschiedenis maximaal 150 gebeurtenissen en maximaal '
                              'honderd antwoordstatussen. Er worden geen camerabeelden, personen, '
                              'locatiehistorie of willekeurige entiteiten aan dit huisprofiel toegevoegd. '
                              'Relevante gegevens, leerkeuzes, modelvergelijkingen en antwoorden worden '
                              'meegenomen in de bestaande handmatige analyse-export; geen automatische upload.',
                              'Leren & vragen kan nu melden dat de effectieve Wallbox-laadsessie nog ontbreekt '
                              'of dat meerdere Forecast.Solar-bronnen zijn gevonden. De opties zijn '
                              'instellingen bekijken, voorlopig alleen veilige fallback houden of later '
                              'vragen. Een antwoord activeert geen fysieke koppeling op basis van een '
                              'vermoeden; de normale configuratiecontrole blijft vereist.'],
               'bullets': []},
              {'title': '19. Live instellingen en afzonderlijk toestelbeheer',
               'paragraphs': ['Vanaf beta.34 is configuratie ook in Zonnestroom toegankelijk. Openen en '
                              'doorlopen van een wizard verstuurt geen bedieningsopdrachten. Voor opslaan '
                              'volgt een overzicht met expliciete bevestiging. Gewone wijzigingen worden in '
                              'dezelfde runtime verwerkt; er wordt geen volledige integratie herladen. Modus, '
                              'metingen, timers, leerprofielen en statuslisteners van ongewijzigde toestellen '
                              'blijven behouden.',
                              'Naam en categorie kunnen ook bij een draaiend toestel aangepast worden. '
                              'Voorrang wijzigt via de centrale tab met bevestiging; een reeds verzonden '
                              'opdracht of lopende vermogensoverdracht moet eerst afgehandeld zijn. De oude '
                              'numerieke bediening blijft alleen werken zolang nog geen centrale wijziging is '
                              'opgeslagen. Actuator-, terugmeldings-, meter- en beschermingswijzigingen aan '
                              'een draaiend toestel blijven wachtende voorstellen. De actieve oude koppeling '
                              'blijft leidend, ook na herstart. SolarPilot stopt geen toestel om zo een '
                              'voorstel te kunnen toepassen; toepassing volgt na gewone, bevestigde veilige '
                              'vrijgave.',
                              'Een andere koppeling begint Uitgesloten en vraagt nieuwe bewuste vrijgave. Oude '
                              'starttickets en op die oude bronnen gebaseerd leren worden niet gebruikt op de '
                              'nieuwe koppeling. Bij veranderen van een fysiek toestel is Toestel vervangen de '
                              'aangewezen functie: deze geeft een nieuw ID, archiveert de oude historie en '
                              'neemt alleen voorkeuren als voorstel over, geen oude meters, vermogen, '
                              'startrechten of leerdata.',
                              'Bij een aangepaste deadline of nettoestemming en een nog wachtende APP-aanvraag '
                              'vraagt de wizard expliciet: alleen volgende beurten of ook huidige aanvraag. '
                              'Alleen volgende behoudt de bewaarde deadline en nettoestemming. Ook huidige '
                              'past die aan op dezelfde al geplande kalenderdag; het maakt geen nieuwe '
                              'belading. Als een opdracht al verzonden is, wachten zulke wijzigingen voor '
                              'volgende beurten. Een nieuwe deadline in het verleden kan bij de volgende '
                              'gewone controle starten toestaan; beveiligingen blijven gelden.',
                              'Net-/fase- of andere centrale gevoelige bronwijzigingen wachten zolang een '
                              'opdracht/overdracht nog bevestigd moet worden. Boiler- of '
                              'klimaatbindingswijzigingen wachten op gerichte vrijgave, inclusief '
                              'fabrikantbescherming. Klimaat deactiveren of zones wijzigen wacht ook bij '
                              'een tijdelijk onbereikbare eigen OFF/coast-zone; onbekend is geen veilige '
                              'vrijgave om eigendom te vergeten. Het wijzigen van tarieven of een analysevoorkeur vraagt '
                              'dat niet. Onbekend/onbereikbaar is geen bevestigde rusttoestand. Wachtende '
                              'voorstellen zijn zichtbaar en afzonderlijk annuleerbaar. De overige regeling '
                              'loopt door.',
                              'Toestellen beheren staat op Toestellen en onder Instellingen & controle. Elk '
                              'profiel heeft Instellingen, Koppelingen, Planning, Historiek en Vervangen. Oude '
                              'profielen hebben alleen historiek. De categorieën wasmachine en droogkast zijn '
                              'labels voor bestaande ondersteunde adapters/scripts, geen nieuwe geteste '
                              'merkintegraties. De native AEG-afwasmachineadapter blijft uitsluitend starten; '
                              'geen stekkeronderbreking, STOPRESET of programmawijziging.',
                              'Toestelentiteiten worden bij toevoegen/verwijderen afzonderlijk bijgewerkt '
                              'zonder de rest te herladen. Alleen eigen virtuele SolarPilot-entiteiten mogen '
                              'worden verwijderd, nooit de bronentiteiten van AEG, Wallbox of Shelly. De '
                              'analyse-export bevat effectieve configuratie, wachtende voorstellen, archieven '
                              'en toepassingsmeldingen. De bestaande historie bewaart maximaal dertig dagen; '
                              'archiveren verandert die termijn niet.',
                              'Gelijktijdige wizardwijzigingen worden per opgeslagen sleutel samengevoegd. '
                              'Tegenstrijdige veranderingen aan dezelfde sleutel of dubbele '
                              'actuator-/meterbindings worden afgewezen in plaats van overschreven. Een '
                              'voorstel mag geen bron overnemen die al door een ander wachtend voorstel wordt '
                              'gereserveerd. Opslaan is geen toestemming om normale apparaatbeveiligingen te '
                              'omzeilen. Ongeldige afzonderlijke opgeslagen pending-, optie- of archiefrecords '
                              'worden veilig afgehandeld zonder geldige andere records te wissen.',
                              'Setup en unload sluiten oude callbacks en taken veilig af. Een afgebroken '
                              'start schrijft geen gedeeltelijk geladen gegevens over goede opslag. '
                              'Gewone opgeslagen instellingen en leerdata blijven behouden.',
                              'Een software-update via HACS vereist nog steeds een Home Assistant-herstart. '
                              'Deze verbetering betreft het latere wijzigen van instellingen in de '
                              'geïnstalleerde versie. De softwareproeven gebruiken fictieve Home '
                              'Assistant-antwoorden en vervangen geen praktische acceptatietest.'],
               'bullets': []},
              {'title': '20. Eén centrale voorrangslijst — bewaren, aanpassen en grenzen',
               'paragraphs': ['Bij de upgrade van beta.35 naar beta.36 wordt de bestaande effectieve volgorde '
                              'automatisch en ongewijzigd vastgelegd als de centrale prioriteitenlijst. '
                              'Daarbij worden geen toestellen ingeschakeld, geen startrechten toegevoegd en '
                              'geen leerdata of timers gereset. Vanaf dat moment is deze lijst de leidende '
                              'bron voor flexibele energieregeling. Openen, slepen of een keuze wijzigen '
                              'bedient nog steeds niets; alleen expliciet opslaan verandert de lijst.',
                              'Gebruik Wie krijgt eerst zonne-energie?. Sleep rijen op desktop of gebruik de '
                              'omhoog/omlaagknoppen, ook op mobiel en met toetsenbord. De lijst bevat elk '
                              'huidig toestel, Auto laden (Wallbox) en Extra warm water tot het werkelijk '
                              'ingestelde extra doel. De standaard is 60 °C; een ander bestaand doel wordt '
                              'niet teruggezet. Per flexibele verbruiker staat Mag dit toestel zonnevermogen '
                              'gebruiken dat de auto al gebruikt?. Daarvoor zijn twee voorwaarden nodig: het '
                              'toestel staat boven de Wallbox én de toestemming staat op Ja. Onder de Wallbox '
                              'blijft een opgeslagen toestemming inactief. Een eigen actuele meter, bevestigde '
                              'zonnelaadsessie en alle elektrische grenzen blijven vereist.',
                              'Elektrische en fabrikantbeveiliging inclusief legionella, noodzakelijk normaal '
                              'warmwatercomfort en noodzakelijk ruimteverwarmings-/koelcomfort staan boven de '
                              'verplaatsbare lijst en zijn niet versleepbaar. Ook handmatige overname, een '
                              'expliciete boost, toegestane deadline en minimale looptijden behouden hun '
                              'bescherming. Extra boilerwarmte naar 60 °C is wél een flexibele zonnestroomtaak '
                              'en gebruikt nooit Wallbox-vermogen. De centrale volgorde is zichtbaar en '
                              'leidend; de 60 °C-buffer mag normaal comfort of een beschermde afwasstart niet '
                              'verdringen.',
                              'Na bevestiging bepaalt de centrale volgorde de automatische verdeling tussen '
                              'gewone verbruikers en hun positie ten opzichte van de Wallbox. De gewone '
                              'realtime berekening en planner gebruiken dezelfde toestelrangorde. Een hoger '
                              'toestel dat niet past hoeft een passend kleiner toestel niet tegen te houden. '
                              'De afwasroute mag alleen lagere gemeten eigen lasten laten wijken, nooit een '
                              'hoger geplaatste verbruiker. Beginnen, stopvertraging, minimumrust en '
                              'minimumlooptijd worden niet herschreven.',
                              'Extra boilerwarmte wacht op een passend, vrijgegeven hoger geplaatst gewoon '
                              'toestel dat nog moet starten. Anders mag een werkelijk door het bestaande '
                              'boilerbeleid goedgekeurd zonnevenster vóór nieuwe lagere starts komen. Er wordt '
                              'geen lagere lopende cyclus onderbroken voor extra warmte. Een inactieve tank '
                              'boven de herstartdrempel van het bestaande Panasonic-temperatuurverschil houdt '
                              'niet alleen wegens een hoog setpoint eindeloos een zonnevenster vast. Koeling, '
                              'nacht, onbekende status, fabrikantbescherming en bestaande stabiliteit blijven '
                              'het boilerbeleid begrenzen. Er wordt geen Force DHW, compressorstop of nieuwe '
                              'ruimteklimaatmodus toegevoegd.',
                              'Nieuwe gewone verbruikers verschijnen automatisch onderaan de centrale lijst '
                              'en kunnen daarna omhoog of omlaag worden gezet. Een nieuw voorkeur-AEG-profiel '
                              'wordt vóór de Wallbox toegevoegd wanneer die voorkeurslogica van toepassing is. '
                              'Nieuwe identiteiten blijven Uitgesloten totdat je ze bewust vrijgeeft. Vervangen '
                              'erft geen Auto-deelname, fysieke koppelingen of startticket. Verwijderde '
                              'identiteiten verdwijnen uit de actieve lijst. De bij de upgrade vastgelegde '
                              'bestaande volgorde wordt niet herschreven.',
                              'Opslag gebeurt onder dezelfde vergrendeling als de regelaar, zonder directe '
                              'toestelopdracht. Gewijzigde broninstellingen, een ander prioriteitsvenster of '
                              'nieuw/verwijderd toestel maken een ouder concept ongeldig. Bij een conflict '
                              'blijven de lokale keuzes zichtbaar en wordt niet stilzwijgend overschreven. '
                              'Vernieuwen vraagt toestemming om een lokaal concept weg te gooien. Alleen een '
                              'beheerder kan lezen via de editor-API en opslaan; het gewone statusoverzicht '
                              'blijft leesbaar. Bij een verbindingsfout eerst vernieuwen om te controleren of '
                              'de opslag toch is gelukt.',
                              'Na de automatische omzetting is de centrale lijst leidend en blijft de '
                              'effectieve volgorde gelijk. De toestelwizard toont geen tweede bediening voor '
                              'rangorde of autolaadvermogen. Een al geopend formulier kan die centrale keuzes '
                              'niet overschrijven. Temperaturen, timers, startrechten, leerdata en '
                              'niet-gerelateerde opties worden niet gereset.'],
               'bullets': []},
              {'title': '21. Leren, Wallbox, boiler, klimaat en analyse',
               'paragraphs': ['De huishoudelijke basislast leert alleen uit perioden die als gewone '
                              'huishoudlast zijn geclassificeerd. Duidelijke Panasonic-ruimteverwarming, '
                              'ruimtekoeling, tapwaterverwarming en sterilisatie worden apart gehouden. '
                              'Zonder aparte warmtepomp-W-meter mag SolarPilot uit stabiele P1+PV-sprongen '
                              'een conservatieve vermogensschatting leren, maar uitsluitend voor planning en '
                              'classificatie. Die schatting wordt nooit van actuele P1-netruimte afgetrokken.',
                              'De Wallbox blijft read-only. Een Full Solar-instelling bewijst niet welke '
                              'laadsessie werkelijk actief is. SolarPilot kan alleen een sessie-entiteit '
                              'voorstellen wanneer één entiteit op hetzelfde Wallbox-apparaat voldoende '
                              'bewijs bevat. Zonder bevestigde effectieve sessie wordt geen Wallbox-vermogen '
                              'toegekend; werkelijk gemeten vrije injectie blijft wel bruikbaar. De '
                              'afgeleide live-sessiebron moet alleen beschikbaar zijn wanneer haar fysieke '
                              'status-, vermogen- en ruwe rapportagebronnen bruikbaar, niet restored en '
                              'hoogstens vijf minuten oud zijn. Ongeldige of toekomstige rapportagetijden '
                              'geven evenmin actuele bronvrijgave. Een minuutheartbeat maakt die controle '
                              'zichtbaar. De live configuratiecontrole en herlading bevestigden zo een '
                              'actuele gestopte sessie zonder EV-vermogenskrediet. Bij een oude, onbekende '
                              'of strijdige status blijft SolarPilot fail-closed.',
                              'De boiler gebruikt vanaf beta.36 één config-entrybron voor de effectieve '
                              'instellingen. Bij de beta.35-migratie worden de werkelijk gebruikte waarden '
                              '50 °C normaal, 46 °C bewaakte comfortgrens, -5 °C Panasonic-differentie, '
                              '50 °C zonnebuffer, 60 °C extra PV-buffer en 50 °C maximum tijdens actieve '
                              'koeling behouden. Het wekelijkse Panasonic-sterilisatieprogramma op 62 °C '
                              'blijft autonoom. Geconfigureerd, ingeschakeld, vrijgegeven, doelbezit, '
                              'Panasonic-autonomie en handmatige override zijn afzonderlijk zichtbaar.',
                              'Klimaatbetrouwbaarheid wordt niet meer als één algemene 100%-waarde getoond. '
                              'Passieve temperatuurverandering, zonnewinst, verwarmingsrespons, koelrespons, '
                              'reactievertraging, weerscorrectie en coast/off-feedback hebben elk een eigen '
                              'status: Nog niet geleerd, Eerste metingen, Voorlopig of Betrouwbaar. Ontbrekend '
                              'bewijs maakt de regeling conservatiever en verruimt nooit de comfortgrenzen.',
                              'Apparaat-, lokale PV-, fase- en klimaatleerdata wissen is in beta.42 begrensd '
                              'tot de lokale afgeleide leerlagen: '
                              'Wallbox-responsstatistiek, toestelvermogenssamples, live-PV-correctie, '
                              'faseprofielen, klimaatprofielen, weersbias en coast-feedback. Instellingen, '
                              'historische PV-bootstrap en operationele klimaatveiligheid zoals handmatige '
                              'rust, commandolimieten, verwacht modus-/OFF-eigendom en een lopende of '
                              'wachtende coastepisode blijven behouden. De reset publiceert de lege '
                              'leerstatus maar voert geen regelcyclus of fysieke opdracht uit. Andere '
                              'modellen, zoals cyclus-, DHW- en plannerleren, worden niet door deze knop '
                              'gewist.',
                              'De lokale PV-kalibratie houdt minimaal vijf geldige vergelijkingsdagen nodig. '
                              '13,8 kWp panelen, 10 kW omvormerlimiet en lokale schaduwdetectie blijven '
                              'behouden. Diagnostiek toont daarnaast fout en bias per ochtend, middag en '
                              'namiddag. Realtime PV blijft altijd belangrijker dan de forecast.',
                              'Analyse-export vermeldt bovenaan de aangevraagde periode én de werkelijk '
                              'beschikbare en gedekte meettijd, gaten, eerste/laatste bruikbare sample, '
                              'herstarts en snelle telemetrie. Bootstrap/historiek, echte SolarPilot-live '
                              'leerdata, berekende profielen en actuele metingen worden apart benoemd; een '
                              'planberekening telt nooit als extra leerdag.'],
               'bullets': []},
              {'title': '22. Eenvoudige bediening en éénmalige veilige activering',
               'paragraphs': ['De dagelijkse modusnamen zijn Alleen bekijken, Automatisch regelen en Pauze. '
                              'De hoofdgroepen heten Toestellen, Warmte & comfort, Batterij, Voorrang '
                              'en Export. Technische details blijven beschikbaar via uitleg en instellingen.',
                              'Bij de eerste start van de actuele migratiereeks wordt het beta.37-activeringsprofiel '
                              'hoogstens één keer toegepast. Analyse, planner en leerfuncties worden geactiveerd '
                              'waar dat zonder nieuw actuatorrecht kan. Bronafhankelijke regeling wordt alleen '
                              'ingeschakeld wanneer de noodzakelijke bestaande koppelingen al aanwezig zijn; '
                              'DHW vereist de bestaande veiligheidsbevestiging. Een later door de gebruiker '
                              'uitgeschakelde functie wordt niet bij iedere herstart opnieuw aangezet.',
                              'De centrale prioriteitenlijst is de enige leidende flexibele volgorde. Een '
                              'toestel mag gemeten zonnevermogen gebruiken dat de auto al gebruikt alleen als '
                              'het boven Auto laden (Wallbox) staat én de afzonderlijke toestemming op Ja '
                              'staat. De Voorrang-editor maakt daarom onderscheid tussen de bewaarde keuze '
                              'en het huidige effectieve resultaat: Ja blijft bewaard wanneer het toestel '
                              'onder Auto laden staat, maar geldt daar effectief als Nee. Verplaatsen is '
                              'nooit een nieuw actuatorrecht. De Wallbox blijft read-only: SolarPilot '
                              'verstuurt geen start, stop, laadmodus of laadstroom naar de laadpaal.',
                              'Wanneer het gemelde boilerdoel afwijkt van de laatste bevestiging, blijft de '
                              'regeling gepauzeerd voor controle. Dit bewijst niet wie het doel heeft gewijzigd: '
                              'een vertraagde cloudmelding is ook mogelijk. Vanaf beta.45 worden uitsluitend '
                              'de exacte geregistreerde adapterdomeinen aquarea en panasonic_cc herkend '
                              'voor de vertraagde bevestiging van hun water_heater-tankdoel. Geen naam-, '
                              'label- of apparaatheuristiek. Voor deze adapters wordt de eerste '
                              'lokale, optimistische temperatuurterugmelding niet als bevestiging gebruikt; '
                              'een passende nieuwe bronrapportage moet na minimaal tien seconden volgen. '
                              'Ook die bron kan cloudcache bevatten en is geen onafhankelijke fysieke meting. '
                              'De live aquarea 1.0.61-koppeling publiceert eerst lokaal het gevraagde doel '
                              'en doet pas na tien seconden een geforceerde statusopvraag. Beta.44 herkende '
                              'dit domein nog niet; een ha_state-bevestiging vóór die wachttijd was daarom '
                              'geen bewijs voor de nieuwe beveiliging. Dit is apart van een werkelijk '
                              'geladen versienummer of correcte dashboardweergave. Andere water-heateradapters '
                              'houden hun bestaande bevestigingscontract. '
                              'Na een gewone herstart controleert de boiler zijn actuele temperatuur, '
                              'doel, doelbron en handmatige/hygiënestatus automatisch. '
                              'Restored tank-, doel- of beschermingswaarden zijn geen bruikbaar bewijs; '
                              'ook een te oud native tankdoel geeft geen opdrachtvrijgave. Een tijdelijke '
                              'bronuitval laat alleen deze module wachten; een routinematige boilercontrole '
                              'is geen blijvende globale blokkering. Een passend eerder beheerd doel wordt '
                              'zonder doelopdracht opnieuw herkend. Voor een nog niet bevestigde opdracht '
                              'is een nieuwe doelrapportage ná deze herstart en ná de eigen adapterwachttijd '
                              'nodig. Er wordt geen oude opdracht herhaald. Een afwijkend doel krijgt '
                              'handmatige bescherming; een echte fout of bewuste handmatige overname '
                              'wordt niet automatisch gewist. Een fabrikant-/krachtige cyclus behoudt '
                              'haar huidige doel zonder SolarPilot-write. De herstelreden blijft zichtbaar '
                              'tot deze gewone controle is afgerond. Een open boilerhersteljournal telt '
                              'ook mee als bezig bij veilig verwijderen; het wordt niet als vrijgegeven '
                              'getoond terwijl de toestand nog onduidelijk is.',
                              'Wanneer de boiler in deze beschermende manual hold '
                              'staat, toont beta.42 een gerichte Hervat-knop. Die knop werkt alleen buiten '
                              'Automatisch regelen en zonder al wachtende opdracht, beëindigt uitsluitend de '
                              'SolarPilot-rust en schrijft niet meteen een temperatuur. Na hercontrole kan '
                              'pas een volgende gewone regelcyclus volgens alle bestaande vrijgaven en '
                              'veiligheidslocks handelen.',
                              'Powerful/Krachtig wordt niet automatisch als boilerboost gebruikt. De Panasonic '
                              'K T-CAP-servicehandleiding PAPAMY2310071CE, onderdeel 14.11, beschrijft deze '
                              'functie uitsluitend voor ruimteverwarming en het verhogen van zone-waterdoelen. '
                              'Dat is geen bewijs van sneller sanitair water verwarmen. SolarPilot verandert '
                              'de afzonderlijke installateursinstelling DHW capacity niet en verzint geen '
                              'leerresultaat, COP of besparing voor een niet uitgevoerde boilerboost.',
                              'Export bundelt de belangrijke instellingen, meetdekking, beslissingen, modellen, '
                              'leerresultaten en fouten. Namen worden standaard gepseudonimiseerd en SolarPilot '
                              'uploadt het bestand niet automatisch.'],
               'bullets': ['Lopende programma’s, minimumlooptijden, elektrische grenzen en fabrikantbeveiliging '
                           'blijven boven de flexibele volgorde staan.',
                           'Nieuwe gewone toestellen komen onderaan tot de gebruiker ze bewust verplaatst.',
                           'Een voorkeurs-AEG-profiel wordt vóór de Wallbox geplaatst wanneer die afwaslogica '
                           'actief is.']},
               {'title': '23. Afwasmachineherstel na late Home Assistant-start',
                'paragraphs': ['De beta.35-analyse kon een situatie bevatten waarin de AEG-regelcode nog '
                               'aanwezig was maar geen afwasmachine in de actieve devices-configuratie stond. '
                               'Zonder zo’n profiel bestaan er geen APP-tickets, geen afwasprioriteit en dus '
                               'geen automatische START, ook al zijn de AEG-entiteiten in Home Assistant wel '
                               'beschikbaar.',
                               'Beta.38 voegde daarvoor een conservatieve éénmalige herstelmigratie toe voor '
                               'de reeds bedoelde bestaande AEG/Electrolux-koppeling. Beta.39 behoudt die '
                               'migratie, maar corrigeert drie regressies die een hersteld profiel nog konden '
                               'blokkeren of verkeerd volgen: statische AEG-startvoorwaarden vervallen niet '
                               'meer na vijf minuten zolang de actuele ConnectivityState gezond blijft; de '
                               'volledige lijst Washing/Prewash/Main wash/Rinsing/Drying/Ado Drying/Paused '
                               'wordt opnieuw als lopende beschermde cyclus herkend; en een optionele '
                               'numerieke Alerts-sensor wordt niet automatisch als veiligheidsbron gebruikt '
                               'zonder expliciete bruikbare DISH_ALARM-vlaggen.',
                               'De praktijkdiagnose voor beta.39 bewees daarna een afzonderlijke '
                               'opstartvolgordefout. SolarPilot controleerde de herstelmarkers één keer tijdens '
                               'zijn eigen config-entry-setup. Op dat moment waren de template-markers nog niet '
                               'geladen en werd terecht maar definitief “niet van toepassing” gemeld. Kort '
                               'daarna waren beide markers en alle verplichte AEG-rollen wel volledig op één '
                               'Home Assistant-apparaat aanwezig, maar beta.39 controleerde niet opnieuw.',
                               'Beta.40 doet de directe controle nog steeds en houdt daarna uitsluitend deze '
                               'gerichte herstelcontrole maximaal tien minuten actief. Relevante statuswijzigingen en '
                               'een begrensde periodieke controle kunnen de ontdekking opnieuw uitvoeren. Na '
                               'succes, timeout of unload worden de tijdelijke listeners opgeruimd. Dit is '
                               'geen permanente algemene toestelherkenning en de retry roept geen regelcyclus '
                               'of fysieke service aan.',
                               'De herstelzoektocht blijft streng same-device: START, ApplianceState, '
                               'ConnectivityState, RemoteControl, DoorState en programmaselectie moeten '
                               'eenduidig op hetzelfde Home Assistant-apparaat zitten. Bij dubbele oude en '
                               'actuele AEG-knoppen wordt alleen een bruikbare START gekozen; PAUSE, RESUME, '
                               'STOPRESET en starttijd kunnen nooit als START worden gekoppeld. Ontbreekt een '
                               'verplichte bron, zijn er meerdere mogelijke apparaten of is de START niet '
                               'betrouwbaar te onderscheiden, dan maakt SolarPilot geen profiel en verleent '
                               'het geen fysiek recht.',
                               'De status toont per verplichte rol missing, selected of ambiguous en telt '
                               'afwijzingen door disabled, restored, not_loaded of unavailable, zonder het '
                               'private Home Assistant-apparaat-id te publiceren. Een '
                               'compleet laat gevonden profiel wordt persistent opgeslagen, direct in '
                               'Toestellen opgenomen en volgens de bestaande voorkeursregel in Voorrang '
                               'geplaatst. Alleen het exact door deze herstelroute gemarkeerde profiel kan zijn '
                               'afgesproken eenmalige Auto-deelname terugkrijgen wanneer er nog geen eerdere '
                               'gebruikersmodus voor die identiteit bestaat. Een later bewust verwijderd '
                               'herstelprofiel wordt niet stil opnieuw gemaakt.',
                               'De beta.39-reparatiemigratie blijft uitsluitend een profiel wijzigen dat aantoonbaar '
                               'door beta.38 zelf als recovered is gemarkeerd. Handmatig aangemaakte of '
                               'bewust aangepaste afwasmachineprofielen worden niet generiek herschreven. '
                               'Wanneer beta.38 de verkorte Running;Paused-lijst heeft opgeslagen, wordt de '
                              'volledige eerder afgesproken faselijst hersteld. Wanneer beta.38 automatisch '
                              'een AEG Alerts-bron in attribuutmodus koos maar die bron geen technische '
                              'DISH_ALARM-vlaggen levert, wordt alleen die automatische optionele blokkade '
                              'verwijderd. Deze reparatie maakt geen APP-ticket en verstuurt geen START.',
                               'Een werkelijk hersteld profiel houdt alle bestaande APP-regels: exact Remote '
                               'Control Enabled is de fysieke aanvraag. De gewone startdeadline blijft 13:00. '
                               'Beta.43 kan optioneel uitsluitend voor maandag een andere lokale deadline '
                               'gebruiken; leeg betekent ook op maandag de gewone 13:00. Startup met APP al '
                               'Enabled telt niet als nieuwe aanvraag. Eén belading krijgt maximaal één START '
                               'en een onzekere opdracht wordt niet blind herhaald.',
                               'Geen enkele herstel- of reparatiemigratie verstuurt zelf een START of wijzigt '
                               'een programma. Een lopende '
                               'cyclus blijft beschermd; End Of Cycle wordt eventgestuurd bewaard, AirDry '
                               'blijft onderdeel van de cyclus en Off of Disconnected alleen bewijst geen '
                               'einde. De status meldt of herstel/reparatie is uitgevoerd, al eerder gebeurde '
                               'of niet veilig/eenduidig toepasbaar was.'],
                'bullets': ['ConnectivityState is de versheidsheartbeat voor startveiligheid; statische '
                            'startvoorwaarden blijven fail-closed op Unknown, Unavailable, restored of een '
                            'afwijkende waarde.',
                            'Ook na een laat hersteld profiel blijft een nieuwe fysieke APP-overgang naar exact '
                            'Enabled per belading verplicht; een bestaande Enabled-stand bij startup telt niet.',
                            'De afgesproken comfortvolgorde blijft behouden: noodzakelijke warmte/warm water '
                           'blijven beschermd; een voorkeurs-afwasmachine kan vóór de Wallbox staan; lagere '
                           'flexibele lasten en de extra 60 °C-buffer volgen de centrale lijst.',
                           'Een afwasstart blijft afhankelijk van gesloten deur, Ready To Start, geldig '
                           'programma, veilige/bruikbare alarmcontrole indien gekoppeld, elektrische ruimte '
                           'en een geldige nieuwe APP-aanvraag.']},
               {'title': '24. Actueel overzicht, Wallboxwaarneming, navigatie, waardeschatting en maandagdeadline',
                'paragraphs': ['Het blok Nu actief toont uitsluitend toestellen waarvan de actuele gekoppelde '
                               'status werkelijk actief is. Bij de Wallbox is vers, geldig laadvermogen nodig; '
                               'een ingestelde laadmodus alleen bewijst geen laadactiviteit. Gemeten en geschat '
                               'toestelvermogen blijven zichtbaar onderscheiden. Actief betekent niet dat het '
                               'verbruik op dat moment uitsluitend uit zonnepanelen komt of dat SolarPilot de '
                               'start veroorzaakte. Ontbrekende of oude gegevens blijven onbekend.',
                               'De startuitleg toont naast de ruwe vrije injectie ook de effectieve toewijzing '
                               'voor precies dat toestel. Die toewijzing komt uit dezelfde engineberekening als '
                               'het startbesluit en is dus al verminderd met hogere prioriteiten, comfort- en '
                               'cyclusreserves en eerder toegezegd vermogen. Benodigd, beschikbaar en '
                               'voldoende/onvoldoende blijven afzonderlijk zichtbaar. Dat alle algemene '
                               'controles groen zijn bewijst niet dat deze toewijzing groot genoeg is; de '
                               'actuele beslisreden blijft leidend.',
                               'De Wallbox blijft volledig read-only. De huidige native fabrikantstatus kan '
                               'uitleggen waarop de laadpaal nu wacht. SolarPilot bewaart lokaal maximaal dertig '
                               'waargenomen eindes van laadperioden. Een historische stopreden wordt alleen aan '
                               'de stop gekoppeld wanneer een exact bekende native status ná het laatste '
                               'laadrapport en binnen vijf seconden van het stop-vermogensrapport is ontvangen. '
                               'Een meetgat, herstart, toekomstige of onlogische opgeslagen tijd en een oude '
                               'status worden nooit tot een bevestigde stopoorzaak gemaakt. De tijd is de '
                               'Home Assistant-waarneming, niet noodzakelijk het fysieke stopmoment. Deze '
                               'registratie verleent geen recht om de Wallbox te starten, stoppen of wijzigen.',
                               'Voor de actuele begroting betekent verse lage laadkracht plus een expliciete '
                               'native melding geen laadvraag, geen verbonden auto of bekende inactieve status '
                               'dat geen EV-vermogen wordt gereserveerd. Alleen lage laadkracht of een oude '
                               'afgeleide sessietekst is onvoldoende. De canonieke zonne-autostatus Zonne-auto '
                               '· wacht op auto wordt door nieuwe standaardlijsten herkend; exact oude '
                               'standaardlijsten migreren compatibel, terwijl eigen waardelijsten onaangeroerd '
                               'blijven. Native Full Solar blijft voor zonneclassificatie vereist.',
                               'Terug en Vooruit in de browser herstellen alleen SolarPilot-schermen en '
                               'dialogen op dezelfde Home Assistant-URL. Een gewijzigd formulier vraagt eerst '
                               'bevestiging voordat het wordt weggegooid; opslaan of een lopende actie wordt '
                               'niet door navigatie onderbroken. SolarPilot wijzigt de Home Assistant-router '
                               'niet, speelt geen formulierdata opnieuw af en gebruikt navigatie nooit als '
                               'toestelopdracht.',
                               'Het geschatte voordeel van automatische sturing is een aparte, voorwaartse '
                               'telling van maximaal negentig bewaarde kalenderdagen. Alleen een door '
                               'SolarPilot beheerde, werkelijk actieve verbruiker op Auto telt mee; handmatige '
                               'starts, boosts, autonoom autoladen, boiler en klimaat zijn uitgesloten. Per '
                               'bruikbaar meetinterval is de formule toegerekende zonnestroom maal '
                               '(afnameprijs min injectievergoeding). Netafname en batterijontlading worden '
                               'eerst conservatief toegerekend. Ontbrekende meters of prijzen worden niet als '
                               'nul aangevuld en oude perioden worden niet achteraf gereconstrueerd. Dit is '
                               'een opportunity-value-schatting, geen bewezen extra besparing door SolarPilot '
                               'en geen bedrag dat nogmaals van de elektriciteitskost mag worden afgetrokken.',
                               'De optionele maandagdeadline van de afwasmachine staat standaard leeg. Leeg '
                               'betekent dat ook maandag de gewone 13:00 geldt. Alleen een bewust ingevulde '
                               'lokale tijd, bijvoorbeeld 10:00, wijzigt maandag; alle andere weekdagen houden '
                               'de gewone deadline. Een bestaand APP-ticket behoudt bij een update zijn vaste '
                               'geplande dag en deadline. Alleen wanneer de gebruiker expliciet kiest om de '
                               'wijziging op het huidige verzoek toe te passen, wordt dezelfde geplande dag '
                               'herberekend; dat maakt geen nieuw ticket en verstuurt geen START. Tijdens een '
                               'lopende beschermde cyclus wacht de instelling tot het bevestigde einde.'],
                'bullets': ['APP moet per nieuwe belading fysiek opnieuw van uit naar exact Enabled gaan; '
                            'Enabled bij startup is geen nieuwe aanvraag.',
                            'Deur, programma, Ready To Start, verbinding, alarmcontrole, elektrische grenzen '
                            'en toestemming voor netstroom op de deadline blijven ongewijzigd verplicht.',
                            'Een bestaande of gemigreerde aanvraag wordt nooit alleen door de nieuwe '
                            'maandaginstelling opnieuw klaargezet of gestart.']},
               {'title': '25. Release- en documentatieregel',
               'paragraphs': ['Deze actuele uitleg is onderdeel van de release zelf. Dezelfde inhoud wordt als '
                              'Markdown meegeleverd én in Home Assistant getoond. Een releasecontrole faalt '
                              'wanneer versie of gegenereerde uitleg niet overeenkomt met de integratieversie.',
                              'Bij iedere toekomstige gedragswijziging moet eerst deze bron worden aangepast. '
                              'Daarna wordt de leesbare documentatie opnieuw gegenereerd. Zo blijft er steeds '
                              'één actuele beschrijving; losse historische updatebestanden zijn niet nodig in '
                              'een First Install-pakket.'],
               'bullets': []}]}

GUIDE_HASH = hashlib.sha256(
    json.dumps(CURRENT_GUIDE, sort_keys=True, ensure_ascii=False).encode("utf-8")
).hexdigest()


def render_markdown() -> str:
    """Render the canonical guide as the bundled Markdown document."""
    g = CURRENT_GUIDE
    lines = [
        f"# {g['title']}", "", f"**Versie:** {g['version']}",
        f"**Bijgewerkt:** {g['updated']}", f"**Regel-hash:** `{GUIDE_HASH[:16]}`",
        "", g["intro"], "",
    ]
    for section in g["sections"]:
        lines += [f"## {section['title']}", ""]
        for paragraph in section.get("paragraphs", []):
            lines += [paragraph, ""]
        for bullet in section.get("bullets", []):
            lines.append(f"- {bullet}")
        if section.get("bullets"):
            lines.append("")
    lines += [
        "---", "",
        "Deze pagina wordt automatisch uit dezelfde bron gegenereerd als de uitleg die Home Assistant toont. Het First Install-pakket bevat alleen de actuele installatie- en gebruiksdocumentatie.", "",
    ]
    return "\n".join(lines)
