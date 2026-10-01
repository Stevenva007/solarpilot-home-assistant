"""Single release-bound guide; regenerate bundled documentation after changes."""
from __future__ import annotations
import hashlib
import json

GUIDE_VERSION = '1.0.0-beta.37'
GUIDE_UPDATED = '2026-10-01'

CURRENT_GUIDE = {'title': 'SolarPilot · Actuele werking',
 'version': '1.0.0-beta.37',
 'updated': '2026-10-01',
 'intro': 'Dit is de enige actuele gebruikersuitleg voor deze release. Bij elke wijziging wordt deze tekst '
          'samen met de code vernieuwd. Deze HACS-release bevat bewust één actuele regelset. Configuratie en '
          'leerdata blijven lokaal in Home Assistant en worden bij gewone HACS-updates niet vervangen door '
          'programmabestanden.',
 'sections': [{'title': '1. Basisprincipe en modi',
               'paragraphs': ['SolarPilot is een lokaal Home Assistant-EMS. De actuele P1- en PV-metingen, '
                              'apparaatvoorwaarden en beveiligingen zijn altijd belangrijker dan '
                              'voorspellingen of aangeleerde patronen.',
                              'Observatie berekent en leert maar stuurt geen gewone flexibele verbruikers. '
                              'Zonnestroom voert de toegestane regeling uit. Pauze start niets nieuws en bouwt '
                              'eigen onderbreekbare lasten veilig af, met behoud van minimumlooptijden en '
                              'beschermde cycli.',
                              'Er wordt maximaal één gewone fysieke wijziging tegelijk uitgevoerd en daarna op '
                              'terugmelding en nieuwe meetinformatie gewacht. Nieuwe apparaten staan standaard '
                              'Uitgesloten totdat ze bewust op Auto worden gezet.'],
               'bullets': ['Eén actuator heeft maar één eigenaar.',
                           'Een EMS-berekening is geen elektrische beveiliging.',
                           'Onzekere opdrachten worden niet eindeloos herhaald.',
                           'Na een herstart leest SolarPilot eerst de echte toestelstatussen. Bekende '
                           'aan/uit-toestanden worden automatisch gereconcilieerd en de eerder opgeslagen '
                           'modus wordt hervat zonder oude schakelopdrachten te herhalen. Alleen een '
                           'onbeschikbare of onzekere status vraagt nog handmatige controle.']},
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
                           'als richtinggevend advies getoond.',
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
                              'Na een bevestigde centrale wijziging bepaalt de positie vóór of na Auto laden · '
                              'Wallbox de relatieve voorrang. Per toestel kies je Mag de auto minder laten '
                              'laden?: Ja, als het veilig kan of Nee. Ja geeft alleen een voorwaardelijke '
                              'toestemming: een eigen exclusieve W/kW-meter, een onderbreekbare schakelaar of '
                              'numerieke actuator en een actuele bevestigde zonnelaadsessie blijven vereist. '
                              'De AEG gebruikt zijn aparte beschermde route. Achter de Wallbox krijgt een '
                              'toestel geen EV-vermogen, ook niet met Ja geselecteerd. Een bestaande '
                              'legacy-overname behoudt haar extra voorwaarde voor korte minimumlooptijd. '
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
                           'Per verbruiker: Voorrang volgen / Alleen echt overschot / Oude expliciete keuze.',
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
                              'of onbetrouwbaar is. Een HEAT-modus met idle is niet hetzelfde als actieve '
                              'verwarming. Een al hoger aangevraagd doel wordt niet alleen wegens een nieuwe '
                              'verwarmactie afgebroken; de fabrikant kan de begonnen taak afhandelen. '
                              'Werkelijke koeling, hygiëne, energietekort en andere beschermingen blijven '
                              'afzonderlijk leidend.',
                              'Voor extra verhogingen geldt standaard 300 seconden stabiele zonnevoorwaarde en '
                              'minstens 1800 seconden sinds de laatste verstuurde doelopdracht. Verlagingen '
                              'wegens echte netafname, nacht, koelbegrenzing of pauze hoeven niet op dat extra '
                              'verhogingsinterval te wachten. Het gewone doel herstellen wordt evenmin '
                              'uitgesteld. Dit zijn rustregels voor setpoints, geen gegarandeerde '
                              'compressorlooptijden.',
                              'Gewoon warmtepompcomfort staat vóór de autonome Full Solar-Wallbox. Voor '
                              'noodzakelijke avondvoorraad mag actueel bevestigd Full Solar-laadvermogen '
                              'alleen in de comfortbeoordeling als vrijmaakbaar zonnevermogen tellen; het '
                              'verhoogt nooit fysieke net- of faseruimte. De Wallbox krijgt geen opdrachten '
                              'van SolarPilot. De extra 60 °C-fase heeft deze voorrang niet: meer dan 3500 W '
                              'werkelijke restinjectie is nodig; een startklare Wallbox krijgt eerst de kans '
                              'om te laden.',
                              'Het gewone zonnedoel is standaard eveneens 50 °C, vanaf 1000 W actuele '
                              'PV-productie. Omdat dit gelijk is aan het normale doel, geeft het geen extra '
                              'temperatuurverhoging. Een bewust hoger gewoon zonnedoel blijft een '
                              'productievoorwaarde en kan netstroom vragen. Voor echt extra 60 °C telt alleen '
                              'overschot. Om een eigen hoge fase vast te houden kan uitsluitend een aparte '
                              'betrouwbare elektrische tankvermogensmeter compenseren, nooit geschatte watts '
                              'of een gedeelde meter.',
                              'Actieve/onzekere koeling begrenst de extra doelen tot de ingestelde koellimiet, '
                              'standaard 50 °C, met standaard 1800 seconden uitloop. Een warmwatercyclus die '
                              'recent koelen onderbreekt telt niet meteen als einde van de koelvraag. '
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
                              'ontbrekende toekomstige waarden onbekend, niet 0 W.',
                              'Resterende en toekomstige energie worden met echte tijdstempels en lokale '
                              'middernacht uit de curve geïntegreerd, in kWh. Er wordt geen vaste 24 uur '
                              'aangenomen bij zomer-/wintertijd. Als alleen een dagtotaal beschikbaar is, '
                              'wordt dat ongewijzigd en als ruw fallbacktotaal getoond; een huidige '
                              'correctiefactor wordt niet blind op morgen toegepast. De volledige ruwe energie '
                              'vandaag blijft eveneens beschikbaar voor diagnose.',
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
                              'bestaat, zonder fysieke bevoegdheden te veranderen. Een oude expliciete '
                              'forecast- of lokale-PV-opt-out blijft behouden. Normaal gebruikt minstens vijf '
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
                              'thermische model voldoende vertrouwen heeft dat de woning comfortabel blijft.',
                              'De Panasonic-doeltemperatuur blijft ongewijzigd de comfortreferentie. Een '
                              'gewone planningsbeslissing gebeurt standaard om de 12 uur en kijkt 48 uur '
                              'vooruit. Tijdens een coastperiode wordt wel vaker gecontroleerd of AUTO tijdig '
                              'opnieuw moet worden vrijgegeven vóór de geleerde vloer-/bouwschilvertraging een '
                              'comfortgrens bereikt.',
                              'De energiebesparende coastlogica is standaard vooral voor het tussenseizoen. '
                              'Bij een duidelijke winter- of zomervraag blijft Panasonic AUTO normaal gewoon '
                              'actief, omdat de warmtepomp dan zelf beter kan moduleren en uitschakelen dan '
                              'wanneer het EMS agressief heen en weer programmeert. Dit wordt op basis van de '
                              'weersverwachting en het binnendoel bepaald, niet op vaste kalendermaanden.',
                              'Per zone leert SolarPilot passieve warmteoverdracht, verwarmingsrespons, '
                              'koelrespons en reactievertraging op basis van Panasonic hvac_action. Daarnaast '
                              'leert SolarPilot de lokale zonnewinst in de woning: werkelijk PV-vermogen wordt '
                              'als lokale instralingsproxy gebruikt om te schatten hoeveel de woning op '
                              'zonnige momenten vanzelf opwarmt. Die bijdrage is begrensd en wordt pas '
                              'gebruikt wanneer voldoende leerkwaliteit aanwezig is.',
                              'De uurverwachting van de weersdienst wordt lokaal gecontroleerd tegen de '
                              'werkelijk gemeten buitentemperatuur. SolarPilot leert afzonderlijk de '
                              'systematische fout rond 6, 12, 24 en 48 uur vooruit en mag de voorspelling '
                              'alleen binnen een instelbare maximumcorrectie bijstellen wanneer voldoende '
                              'verschillende dagen en vertrouwen beschikbaar zijn.',
                              'Iedere SolarPilot-coastperiode wordt achteraf geëvalueerd als correct, te lang '
                              'of te voorzichtig. Na meerdere beoordeelde episodes mag alleen het minimum '
                              'nuttige coastvenster voorzichtig binnen ingestelde grenzen worden aangepast. '
                              'Comfortbanden, Panasonic-doeltemperatuur en de keuze HEAT/COOL veranderen '
                              'hierdoor nooit.',
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
                              'stilzwijgend als 100% worden voorgesteld.'],
               'bullets': ['Een handmatig gekozen Panasonic HEAT- of COOL-stand wordt nooit door SolarPilot '
                           'overschreven; de regeling wordt dan adviserend tot de gebruiker zelf terugkeert '
                           'naar AUTO/OFF.',
                           'Een harde comfortoverschrijding kan AUTO onmiddellijk opnieuw vrijgeven, maar '
                           'SolarPilot kiest ook dan niet tussen HEAT en COOL.',
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
                              'Energie & net, Verbruikers & prioriteiten, Comfort & warmtepomp, Opslag & '
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
                              'toestelstatussen automatisch zijn gereconcilieerd.',
                              "De basispagina's tonen alleen de instellingen die je normaal nodig hebt. "
                              'Timing, faseherkenning en Wallbox-herkenningsdetails staan bewust onder '
                              'Geavanceerd. De onderliggende option-keys en regelalgoritmen blijven compatibel '
                              'met bestaande instellingen.',
                              'De dashboardkaart bevat negen herkenbare tabbladen: Overzicht, Voorrang, '
                              'Verbruikers, Comfort, Planning, Energie, Opslag, Export en Uitleg. Modus en '
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
                              'Verbruikers en Wallbox tonen operationele status en een verwijzing naar '
                              'Voorrang, geen tweede rangorde-editor. Open popups, invoer en conceptvolgorde '
                              'worden niet opnieuw opgebouwd door een gewone live verversing.'],
               'bullets': ['Eerste installatie vraagt alleen de essentiële net- en PV-bronnen; een optionele '
                           'lokale privébundel kan daarna de overige bronkoppelingen en historische bootstrap '
                           'in één keer veilig invullen.',
                           'Verbruikers worden toegevoegd via een duidelijke vierstappenwizard: basis, '
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
                           'Iedere flexlast heeft in de tab Verbruikers een Dagoverzicht-popup voor de eigen '
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
              {'title': '14. Dagoverzicht en draaitijd per verbruiker',
               'paragraphs': ['Open het SolarPilot-dashboard → Verbruikers en klik bij een toestel op '
                              'Dagoverzicht. De knop toont ook de geregistreerde draaitijd van vandaag. De '
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
                              'gereedstand niet blokkeren.',
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
                              'beschikbaar voor andere expliciete alarmbronnen.',
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
                              'Installeren schakelt geen fysieke starttoestemming, bronbevestiging of '
                              'Auto-deelname in. Zolang je de centrale lijst niet wijzigt, rangschikt het oude '
                              'getal binnen de bestaande groepen. Na een bevestigde wijziging bepaalt de '
                              'centrale lijst de relatieve volgorde; de gewone comfortbescherming blijft '
                              'gelden. Een voorkeur-AEG blijft vóór de extra boilerwarmte. De toestemming voor '
                              'het benutten van EV-zonnevermogen staat dan uitsluitend in die centrale editor.',
                              'Een vandaag werkelijk startklare APP-aanvraag of een al lopende beurt blokkeert '
                              'extra 60 °C. Een aanvraag voor morgen doet dat vandaag niet. De gewone 50 °C en '
                              'een benodigde avondvoorraad tot de gekozen limiet blijven beschikbaar. Een '
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
                              'het veilig kan geselecteerd hebben. Zonder centrale wijziging blijft de oude '
                              'expliciete toestemming gelden. Actuele geldige Full Solar-status, conservatief '
                              'gecombineerd ruw/gefilterd netvermogen, de bestaande maximale overnamestap en '
                              'voldoende PV blijven noodzakelijk. De volledige nieuwe belasting moet binnen de '
                              'actuele elektrische, kwartierpiek- en fasegrenzen passen vóór de Wallbox '
                              'reageert. Dit vergroot nooit elektrische capaciteit en verstuurt geen opdracht '
                              'naar de Wallbox.',
                              'Deze start van een beschermd programma is niet dezelfde regeling als de '
                              'terugneembare overname voor onderbreekbare lasten. De oude optie Mag '
                              'gecontroleerd vermogen van Wallbox overnemen blijft voor afwasmachines UIT. De '
                              'nieuwe aparte keuze heet Zonnevermogen vóór Wallbox benutten. De belasting '
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
                           'Deze cumulatieve update bevat beta.31. Geen automatische publicatie, bronkoppeling '
                           'of fysieke activering. Alle proeven gebruiken fictieve apparatuur.']},
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
                              'met consistente koppelingen tussen instellingen en metingen. Een expliciete '
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
                              'ingestelde vrijgaven. Het oude Lokaal leren schakelt niet automatisch elk '
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
                              'fabrikantbescherming. Het wijzigen van tarieven of een analysevoorkeur vraagt '
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
                              'omzeilen.',
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
                              'en blijft na de Wallbox; hij gebruikt nooit geschat of onbewezen EV-vermogen.',
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
                              'identiteiten verdwijnen uit de actieve lijst. De bestaande beta.36-volgorde '
                              'wordt bij de upgrade naar beta.37 niet herschreven.',
                              'Opslag gebeurt onder dezelfde vergrendeling als de regelaar, zonder directe '
                              'toestelopdracht. Gewijzigde broninstellingen, een ander prioriteitsvenster of '
                              'nieuw/verwijderd toestel maken een ouder concept ongeldig. Bij een conflict '
                              'blijven de lokale keuzes zichtbaar en wordt niet stilzwijgend overschreven. '
                              'Vernieuwen vraagt toestemming om een lokaal concept weg te gooien. Alleen een '
                              'beheerder kan lezen via de editor-API en opslaan; het gewone statusoverzicht '
                              'blijft leesbaar. Bij een verbindingsfout eerst vernieuwen om te controleren of '
                              'de opslag toch is gelukt.',
                              'De vroegere prioriteitsgetallen, globale keuzes en ruwe toestelprofielen '
                              'blijven bewaard voor migratie en onderzoek. Na de automatische beta.36-migratie '
                              'zijn zij niet langer leidend: de oude numerieke/global-schakelbediening '
                              'wijst wijzigingsopdrachten af met een '
                              'verwijzing naar Voorrang. De toestelwizard verbergt dan de oude rangorde- en '
                              'overnametoestemmingsvelden. Een oude, al geopende wizard mag die keuzes niet '
                              'terugschrijven. Temperaturen, timers, startrechten, leerdata en '
                              'niet-gerelateerde opties worden niet gereset.'],
               'bullets': []},
              {'title': '21. Beta.36 — leren, Wallbox, boiler, klimaat en analyse',
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
                              'toegekend; werkelijk gemeten vrije injectie blijft wel bruikbaar.',
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
              {'title': '22. Beta.37 — eenvoudiger bedienen, centrale voorrang en automatische activering',
               'paragraphs': ['De dagelijkse dashboardnamen zijn vereenvoudigd: Alleen bekijken, Automatisch regelen, '
                              'Toestellen, Warmte & comfort, Auto & batterij, Voorrang en Export. Technische details '
                              'blijven beschikbaar via Info, uitlegknoppen en de configuratiewizard.',
                              'Wie krijgt eerst zonne-energie? is de centrale plaats voor flexibele verdeling. '
                              'Veiligheid, normale ruimteverwarming/koeling en noodzakelijk warmwatercomfort staan '
                              'vast bovenaan. De bestaande afgesproken volgorde van beta.36 blijft behouden. '
                              'De AEG-afwasmachine blijft vóór de Wallbox wanneer dat profiel aanwezig is; '
                              'de Wallbox blijft vóór de ontvochtiger en extra 60 °C-buffer. Nieuwe gewone '
                              'verbruikers komen standaard onderaan totdat de gebruiker ze verplaatst.',
                              'Een toestel mag zonnevermogen gebruiken dat de auto al gebruikt wanneer het boven '
                              'Auto laden (Wallbox) staat én de expliciete toestemming op Ja staat. Onder de '
                              'Wallbox blijft de toestemming bewaard maar inactief. De Wallbox blijft read-only: '
                              'SolarPilot stuurt geen laadstroom, pauze, start of laadmodus.',
                              'Export bevat één hoofdactie: een compleet analysebestand om zelf in ChatGPT te '
                              'uploaden. Standaard vraagt de export zeven dagen en pseudonimiseert hij namen. '
                              'Instellingen, centrale voorrang, meetdekking, beslissingen, modellen, leerresultaten '
                              'en fouten worden samengebracht zonder ontbrekende historie te verzinnen.',
                              'Bij de eerste start van beta.37 wordt éénmalig een activeringsprofiel toegepast. '
                              'Analyse, planner, basislastleren, lokaal PV-leren, Forecast.Solar-kalibratie, '
                              'batterij-what-if en beschikbare leerfuncties worden geactiveerd. Bronafhankelijke '
                              'regels zoals fasebewaking, Wallbox-monitoring, klimaatregeling en boilerregeling '
                              'worden alleen geactiveerd wanneer de bestaande koppelingen en noodzakelijke '
                              'bevestigingen al aanwezig zijn. SolarPilot verzint geen bron, bevestigt geen '
                              'veiligheidskeuze en geeft geen nieuw toestel- of batterijrecht.',
                              'De automatische activering gebeurt maar één keer. Latere keuzes van de gebruiker '
                              'blijven behouden. Leren & vragen gebruikt gemeten data en begrensde automatische '
                              'adaptatie; nieuwe vragen mogen als Home Assistant-melding verschijnen, maar leren '
                              'verruimt nooit zelfstandig comfort- of veiligheidsgrenzen.'],
               'bullets': ['Lopende programma’s, minimumlooptijden en beschermde cycli blijven beschermd wanneer '
                           'de voorrang wordt gewijzigd.',
                           'Extra warm water tot 60 °C blijft een flexibele luxe-zonbuffer en gebruikt geen '
                           'Wallbox-vermogen.',
                           'Nieuwe toestellen krijgen geen automatische Auto-deelname of fysieke starttoestemming.']},
              {'title': '23. Release- en documentatieregel',
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
