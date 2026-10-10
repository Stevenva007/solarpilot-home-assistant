# SolarPilot · Actuele werking

**Versie:** 1.0.0-beta.63
**Bijgewerkt:** 2026-10-10
**Regel-hash:** `186004d313d8e50a`

Deze herstelupdate laat SolarPilot correct laden met de onveranderbare configuratie van Home Assistant. Panasonic blijft de warmtepomp regelen; SolarPilot kan alleen een gecontroleerde SG-zonneboost aanvragen. Alle overige behouden SolarPilot-apparaten, beveiligingen en privégegevens houden hun eigen bestaande regels. De uitleg wordt bij iedere codewijziging samen met de release vernieuwd.

## 1. Basisprincipe en modi

SolarPilot verdeelt beschikbare zonnestroom lokaal in Home Assistant. Actuele net- en PV-metingen, echte toestelvoorwaarden en elektrische grenzen gaan altijd vóór een voorspelling of geleerd patroon. Eén uitgang heeft één eigenaar. Een regeling vervangt geen elektrische beveiliging.

Alleen bekijken berekent en registreert zonder nieuwe flexibele toestellen te starten. Automatisch regelen voert uitsluitend de toegestane apparaatbediening uit. Pauze start niets nieuws en geeft eigen onderbreekbare lasten veilig vrij, met behoud van minimumlooptijden en beschermde cycli. Een eigen SG-zonneboost wordt ingetrokken; de warmtepomp zelf blijft onder Panasonic-regie. Eigen bevestigde numerieke batterijdoelen behouden hun afzonderlijke veilige vrijgaveroute.

Na herstart automatisch hervatten staat standaard Aan. Een gewone opgeslagen Pauze vraagt na Home Assistant-start of herladen weer Automatisch regelen via de bestaande controles. Alleen bekijken, eerste installatie, echte interne fout- en verwijderpauzes blijven beschermd. De voorkeur wijzigen verandert de huidige modus niet. Opnieuw Pauze kiezen annuleert een wachtende hervatting. SG-ingebruikname en een oude boost krijgen hierdoor geen automatische bevestiging.

Na een herstart leest SolarPilot echte toestelstatussen. Een tijdelijk onbereikbaar eerder beheerd toestel wordt afzonderlijk opzijgezet; onbekend verbruik wordt niet als nul gerekend. De overige lasten kunnen verder zodra hun eigen voorwaarden en globale net- en veiligheidsmetingen betrouwbaar zijn. Het ontbrekende toestel wordt opnieuw beoordeeld zodra bruikbare brongegevens terugkeren. Onzekere fysieke opdrachten worden niet blind herhaald.

## 2. Overschot, centrale voorrang en planner

De volledige netmeter bepaalt werkelijke afname en injectie. W en kW worden naar hetzelfde vermogen omgerekend; een kWh-teller is geen actuele vermogensbron. De tekenafspraak wordt bewust gekozen. Restored, ontbrekende, toekomstige, niet-eindige of verkeerd gevormde waarden geven geen vrijgave. Een onveranderde waarde kan actueel zijn wanneer haar echte ontvangst of bruikbare heartbeat dat bewijst.

Voorrang is de enige flexibele rangorde. De opgeslagen gebruikersvolgorde blijft bij deze update staan; een oude rangordemigratie wordt niet opnieuw toegepast. De rij voor extra warmwaterproductie vertegenwoordigt voortaan Extra zonneboost via SG. Zij mag geen Wallbox-vermogen, beschermde afwascyclus of noodzakelijk Panasonic-comfort afnemen. Nieuwe gewone toestellen komen onderaan totdat je ze verplaatst.

Start- en stopvertragingen, minimum aan/uit-tijden, dagdoelen, tijdvensters en beschermde programma’s blijven gelden. Een hoger toestel dat niet past hoeft een kleiner passend toestel niet te blokkeren. Lager geplaatste, werkelijk eigen en veilig onderbreekbare lasten kunnen alleen volgens de bestaande overdrachtvoorwaarden wijken. Eerst bevestigde UIT en nieuwe net-/PV-metingen; een stopverzoek is nog geen vrij vermogen.

De planner herberekent de ingestelde horizon in kwartierblokken met beschikbare PV, basislast, tarieven, kwartierpiek en batterijruimte. Hij kan alleen expliciet vrijgegeven flexibele lasten plannen. Het huidige blok kan de gewone realtime regeling ondersteunen, maar nooit te weinig werkelijk overschot overstemmen. Er is geen actieve warmtepomp-, tanktemperatuur- of klimaatplanning meer.

Een dagdoel in kWh gebruikt werkelijk gemeten toestelenergie waar een exclusieve meter bestaat, anders een herkenbare schatting. Een beschermde cyclus wordt als aaneengesloten taak gepland. Zonder betrouwbaar duurprofiel wordt geen optimistische duur uit piekvermogen gegokt. Een lopende beschermde cyclus wordt niet gestopt wegens een nieuw plan. Goedkope netfallback blijft afzonderlijke dubbele toestemming en standaard uit.

Plannerkwaliteit toont meetdekking, voorspellingsfout en uitvoering afzonderlijk. Een historische replay is richtinggevend en reconstrueert niet iedere vroegere startvoorwaarde. Een volledige lokale dag heeft normaal 96 kwartieren, bij de zomer-/wintertijdwissel 92 of 100; gaten worden geen volledige prestatie.

## 3. Warmtepomp — Panasonic-regeling voor warm water, verwarmen en koelen

Panasonic regelt zelfstandig normaal warm water, tankhysterese, kamerthermostaten en zones, stooklijnen, verwarmen/koelen, omschakeling, compressor, pompen, kleppen, ontdooien, elektrische ondersteuning en sterilisatie. Dit blijft zo wanneer SolarPilot of Home Assistant uitvalt.

Voor de warmtepomp mag SolarPilot alleen de expliciet toegewezen bestaande Shelly-uitgang voor SG-zonneboost bedienen. Tank- en kamertemperaturen, native programma, activiteit, beschikbaarheid en vermogen zijn verder uitsluitend uitleesbaar. SolarPilot schrijft geen tankdoel, AUTO/UIT, HEAT/COOL, kamertemperatuur, Powerful, Force DHW, Force Heater, stooklijn of heater-toestemming.

De oude eigen temperatuurfasen, nacht-/ochtend-/avondvoorraadregeling, klimaatpauzes, voorspellende voorverwarming/voorkoeling en hun opdrachtbevestiging/herstelbediening zijn verwijderd. Normale doelen en fabrikantprogramma’s worden op Panasonic ingesteld. De nieuwe regeling corrigeert geen mogelijk door een oudere versie achtergelaten native instelling: controleer die eenmalig bij ingebruikname.

Het compacte warmtepompblok toont Automatische zonneboost, de actuele reden, tanktemperatuur en bekende vermogensmeting met haar dekking. Details onderscheiden SolarPilot-aanvraag, gemelde SG-contactstand en bewezen Panasonic-reactie. Zonder afzonderlijke SG-/reactiebron blijft die laatste onbekend. Een gelijkblijvend app-tankdoel is geen relaisfout; stijgende tanktemperatuur alleen bewijst geen SG-eigendom.

## 4. Extra zonneboost via SG

Automatische zonneboost staat standaard Uit. Activeren vereist de juiste bestaande uitgang, bevestigde contactmapping, gecontroleerde Panasonic-reactie, uitsluiting van dubbele sturing en bewezen lokale terugval bij communicatieverlies. Een geopende instellingenpagina, geselecteerde entiteit of opgeslagen globale Auto-modus is geen ingebruiknamebewijs.

De regeling onderscheidt normaal, wachten op voldoende overschot, boost aangevraagd, rusttijd en geblokkeerd. Voldoende bruikbaar werkelijk zonneoverschot moet stabiel beschikbaar zijn. Nieuwe standaardwaarden zijn 3000 W startdrempel en een afzonderlijke conservatieve vermogensraming van 3200 W. Die raming is geen meting of gegarandeerd SG-verbruik. Oude drempels en vermogensramingen blijven als kandidaten in het private migratiearchief; de nieuwe SG-instellingen vereisen een afzonderlijke beoordeling en bevestiging.

De nieuwe standaardvertraging voor starten is 120 seconden, voor een aanhoudend tekort 60 seconden, met 900 seconden rust tussen sessies en maximaal 3600 seconden per sessie. Deze tijden beperken schakelen bij wolken. Geldige recente metingen, toewijzing, fasegrenzen, eigen bediening en de lokale timer gaan vóór een gewenste minimale boostduur. Een harde limiet of onbetrouwbare noodzakelijke bron geeft de eigen aanvraag vrij.

Na een toegelaten start hoeft de resterende injectie niet boven de startdrempel te blijven: de warmtepomp gebruikt juist die zon. De aparte kleine-importbuffer staat standaard op 300 W. Netafname boven die buffer gedurende de stopvertraging geeft alleen de extra SG-aanvraag vrij; tijdens die tekortcontrole wordt de lokale toestemming niet verlengd. Dit garandeert geen nulimport en stopt geen noodzakelijke native cyclus.

Panasonic bepaalt wat het SG-signaal werkelijk doet. Controleer dat deze trap geen ongewenste extra ruimteverwarming of vloerkoeling vraagt. SolarPilot hardcodeert geen universele verhouding tussen normale en effectieve tanktemperatuur. Zonder bevestigde ingebruikname blijft SG uit en werken de overige toestellen onder hun eigen voorwaarden verder.

Bij stoppen opent alleen het SG-contact. SolarPilot zet de warmtepomp of elektrische heater niet uit. Een lopende native cyclus kan doorgaan en het verbruik kan dus blijven. Een voltooide of aantoonbaar niet langer opnemende sessie wordt niet eindeloos opnieuw gestart; onbekende tank-/bedrijfsinformatie is geen bewijs dat de tank klaar is.

Na de maximale sessieduur blijft een afzonderlijke wachtstand bewaard, ook bij herstart. Een verse betrouwbare tankmeting bij het sessie-einde wordt de referentie. Na rust mag een nieuwe zonnestart automatisch worden beoordeeld wanneer dezelfde tankbron minstens 2 °C is afgekoeld, bevestigd door minimaal twee latere echte rapporten gedurende vijf minuten. Dat toont nieuwe opslagruimte, geen bewezen comfortvraag, geslaagde eerdere SG-reactie of effectief SG-tankdoel. Alle gewone zon-/bron-/fase-/voorrangsvoorwaarden gelden opnieuw, inclusief de volledige startvertraging. Na herstart zijn weer echte nieuwe rapporten en een nieuwe vijfminutenbevestiging nodig. Zonder eindmeting, bij gewijzigde bron of onbetrouwbare data blijft de wachtstand staan; bewust Automatisering hervatten blijft een mogelijkheid na controle. Rusttijd of herstart alleen reset de sessiegrens niet. Een gewone stop wegens netafname kan na rust en verse geldige zon opnieuw worden beoordeeld.

Extra SG volgt de opgeslagen flexibele rangorde, zonder EV-vermogenskrediet. Een lager geplaatst eigen onderbreekbaar toestel mag alleen veilig wijken als minimumlooptijd, gebruikerskeuze en overige bescherming dat toelaten. Een afwascyclus, Wallbox en native noodzakelijk klimaat-/warmwaterverbruik worden daarvoor niet uitgezet.

## 5. Lokale SG-terugval en handmatige bediening

Opstartstand UIT is geen uitschakeling bij wifi- of Home Assistant-uitval. Daarom gebruikt automatische SG-bediening een lokaal op de Shelly aflopende toestemming: standaard 300 seconden geldig, vernieuwd iedere 60 seconden zolang de actuele boost toegestaan blijft. Vernieuwing moet de timer verlengen zonder het relais uit/aan te schakelen. De korte communicatietoestemming staat los van de langere maximale boostsessie. Iedere vernieuwing is ook begrensd tot de resterende sessieduur. Tegen het sessie-einde blijft een toereikende bestaande timer lopen zonder nieuwe volle lease; de aanvraag kan de ingestelde bevestigingsmarge eerder eindigen. Afloop geeft geen recht op een nieuwe sessie of oude ON-replay.

Zonder ondersteunde, echt gecontroleerde lokale aflooptimer geen automatische boost. De software registreert expliciete AAN/UIT-opdrachten, nooit een blinde toggle. Een geaccepteerde serviceaanroep bewijst geen relaisstand, lopende lokale timer of fysieke Panasonic-reactie. Bij onbereikbaarheid blijft de uitgang onbekend; er komt geen fictieve UIT-bevestiging en geen eindeloze retry.

Pauze, uitschakelen van SG-optimalisatie, gewijzigde koppeling en unload annuleren oude vernieuwingen en trekken de eigen aanvraag in waar betrouwbaar mogelijk. Een lokale timer laat die aanvraag ook zonder Home Assistant verlopen. Een late AAN-terugmelding verleent geen nieuwe toestemming. Na herstart wordt een achtergebleven eigen aanvraag eerst verzoend/vrijgegeven en volgt een nieuwe beoordeling met verse gegevens, geen replay.

Een werkelijk handmatige wijziging wordt gerespecteerd. Automatisering hervatten is een afzonderlijke duidelijke keuze; zij start geen boost zonder actuele voorwaarden. Een eigen vertraagde terugmelding of lokaal verlopen toestemming wordt niet zonder bewijs als gebruikershandeling behandeld.

De lokale timer is geen vervanging voor elektrische beveiliging en geen absolute garantie bij bijvoorbeeld een vastgelast contact. Deze release vraagt geen extra heaterrelais, broker, server, cloudregelaar of wijziging aan bedrading of DIP-schakelaars.

## 6. Warmtepompvermogen en elektrische ondersteuning

Koppel een echte W/kW-bron en bevestig wat zij meet: totaal warmtepompvermogen, alleen een deelvoeding of uitsluitend elektrische ondersteuning. Een gedeeltelijke meting krijgt haar eigen dekkingslabel en wordt niet als totaal voorgesteld. Een interne Shelly-temperatuur is geen tank- of vermogenssensor. Ontbrekend vermogen blijft onbekend.

Tankproductie en ruimteverwarming/-koeling delen één warmtepomp. De netmeter bevat haar werkelijke stroom al. Een gezamenlijke meting wordt slechts eenmaal gerekend; een al inbegrepen heater wordt niet opgeteld. Ook een afzonderlijke heaterwaarneming is geen gegarandeerde totale boostbelasting.

Het hele warmtepompvermogen is niet terugwinbaar door SG uit te zetten: native warmwater- of ruimtebedrijf kan blijven doorgaan. Vrijgekomen ruimte wordt pas toegewezen wanneer nieuwe metingen dat ondersteunen. Betrouwbaar eigen werkelijk verbruik kan het voortzetten van een geldige aanvraag helpen verklaren, maar is geen onbeperkte nieuwe startcapaciteit of bewijs dat al dat vermogen door SG wordt veroorzaakt.

Elektrische bijverwarming blijft volledig onder Panasonic-regie. Zonder echte bron blijft heaterstatus/-vermogen onbekend of expliciet geschat. Er is geen belofte van nul netafname of uitsluitend compressorbedrijf. Bij aanhoudende ongewenste import wordt de optionele eigen SG-aanvraag vrijgegeven; noodzakelijk native comfort, sterilisatie en beschermde afwas blijven beschikbaar.

## 7. Wallbox: uitsluitend uitlezen en voorrang

SolarPilot bedient de Wallbox niet: geen start, stop, laadstroom, laadmodus of faseopdracht. De laadpaal kan autonoom Full Solar regelen of manueel/gepland laden. Een ingestelde Full Solar-optie is geen bewijs dat de effectieve sessie op zon terugregelt. Een betrouwbare effectieve-sessiebron onderscheidt zonneladen, manueel en gestopt; een manuele melding gaat vóór de instelling.

Voorwaardelijk overneembaar EV-vermogen bestaat alleen voor een toegestaan toestel boven de Wallbox in de centrale lijst, met afzonderlijke toestemming en betrouwbare eigen meter/adapter en bevestigde zonnelaadsessie. SG-zonneboost gebruikt dit krediet nooit. Bij manueel, oud, onbekend of strijdig laden blijft alleen echte restinjectie bruikbaar. Geen ontbrekende sessiestatus gokken uit netafname.

EV-vermogen vergroot geen elektrische capaciteit. De volledige nieuwe belasting moet vóór een opdracht binnen net-, kwartierpiek- en fasegrenzen passen alsof de laadpaal nog niet heeft gereageerd. Eén stap tegelijk en nieuwe rapportages blijven vereist. Lange minimumlooptijden en beschermde programma’s worden niet ingekort om vermogen sneller terug te nemen.

Een verse lage laadkracht heft een reserve alleen op met een expliciete inactieve status, geen laadvraag of geen verbonden auto. Lage kracht alleen is onvoldoende. Klein restoverschot kan volgens de bestaande voorkeur door een lager toestel worden benut; veilige vrijgave kan later de autonome zonne-autostart ondersteunen. Bestaande voorkeuren en wachttijden blijven behouden.

Het laadprofiel leest expliciete grenzen en fasen uit betrouwbare bronnen of gebruikt een bewust bevestigd terugvalprofiel. Huisaansluitstroom is geen laadstroomlimiet. SolarPilot verandert die waarden niet. Het dashboard onderscheidt sessie, ingestelde zonnemodus, werkelijk laden en wachtreden. Lokaal bewaarde laadperiode-eindes krijgen alleen een native stopreden bij aantoonbaar passende nieuwe rapportage; een meetgat of herstart is geen bewezen stopoorzaak.

## 8. Gewone flexibele toestellen en ontvochtiger

Bestaande toestellen behouden hun adapter, deelname, centrale positie, meter, minimumlooptijd, rusttijd, bescherming, dagdoel en bewuste nettoestemming. Nieuwe identiteiten beginnen Uitgesloten. Een onbereikbaar toestel wordt tijdelijk geïsoleerd en na bruikbaar bronherstel weer beoordeeld; deelname wordt niet stil veranderd.

Actief betekent de werkelijk waargenomen aan-/actiefstatus, niet gegarandeerd continu compressorbedrijf of uitsluitend zonnegebruik. Gemeten W, geraamd W en onbekend blijven verschillende labels. Een ontbrekende noodzakelijke meting geeft geen verzonnen nul. Een fout wordt gericht bij de betrokken functie verklaard; alleen echte gedeelde onzekerheid mag andere starts beperken.

Handmatig starten/stoppen en een tijdelijke toestelboost gebruiken de bestaande toestemming en bescherming. Het zijn geen noodstop of bypass van fabrikant- en softwaregrenzen. Een looptijd mag tijdelijk netgebruik noodzakelijk maken. Een pure planningswijziging bij een bevestigde binaire AAN-last geeft geen nieuwe turn_on-opdracht.

Toestel- en batterijscripts worden vóór uitvoering op vaste onafhankelijke doelapparaten gecontroleerd. Panasonic en het gereserveerde SG-contact mogen niet indirect worden bediend. Ontbrekende of niet controleerbare scriptinhoud en dynamische doelen blijven geblokkeerd. Dit bewijst geen fysieke veiligheid van het script; geschikte terugmelding en de bestaande toestemming blijven nodig.

## 9. AEG-afwasmachine: één START per belading

De bestaande AEG/Electrolux-adapter verstuurt alleen de gecontroleerde native START-knop. Geen PAUSE, RESUME, STOPRESET, programmawijziging, native afteltimer of stroomonderbreking via een stekker. Een gestarte, gepauzeerde of nadrogende beurt blijft beschermd, ook bij wolken, Pauze of een manuele autosessie.

In APP-modus maakt alleen een nieuwe fysieke overgang naar exact RemoteControl Enabled één aanvraag. Enabled bij opstart, reconnect of migratie is geen nieuwe belading; Not Safety Relevant Enabled is geen toestemming. Ready To Start, gesloten deur, geldig programma, bruikbare verbinding en eventuele alarmcontrole blijven vereist. ConnectivityState levert de heartbeat: onveranderde geldige statische deur-/programma-/gereedwaarden vervallen niet alleen doordat de tekst gelijk blijft. Unknown, Unavailable en restored blijven beschermd.

Standaard geldt 13:00 als uiterste starttijd. Een aanvraag vóór de deadline gebruikt dezelfde kalenderdag; op/na de deadline geldt de opgeslagen keuze, standaard volgende dag. Een optionele maandagdeadline staat standaard leeg en gebruikt dan ook maandag de gewone tijd. Alleen een bewust ingestelde maandagwaarde wijzigt die dag. Tijdzone, geplande dag en toestemming worden in het aanvraagticket bevroren en over herstart bewaard.

Een zonnestart vereist de ingestelde stabiele injectietijd, standaard 300 seconden voor nieuwe profielen. Op de deadline kan alleen de zonnevoorwaarde vervallen wanneer netaanvulling bewust is toegestaan. Actuele net-/fase-/kwartierpiekruimte, globale modus en toestelvrijgave blijven nodig. Een gemiste deadline geeft volgens de bestaande regels eenmaal een melding; de standaard hersteltermijn van een nog niet verzonden start is 120 minuten, daarna is een nieuwe APP-aanvraag nodig.

Het ticket wordt vóór START duurzaam als geprobeerd bewaard. Alleen een nieuwe passende Running-rapportage bevestigt start. Een onzekere of mislukte START wordt niet blind herhaald, ook niet na herstart. Handmatig starten verbruikt dezelfde aanvraag. Een gewijzigde deur, programma, koppeling of ingetrokken APP-vrijgave annuleert alleen de nog wachtende aanvraag.

End Of Cycle wordt eventgestuurd opgeslagen en blijft na Off, onbereikbaarheid en herstart zichtbaar. AirDry/Ado Drying betekent nadrogen, geen einde of nieuwe belading. Alleen Off of een onderbreking bewijst geen voltooiing; onbekende starttijd wordt geen exacte duur. Een nieuw betrouwbaar Ready To Start kan een achtergebleven oude cyclus als einde niet bevestigd afsluiten zonder een oude aanvraag te herstellen.

Zonder exclusieve meter blijft de ingestelde nominale belasting een conservatieve reserve en geen gemeten faseprofiel. Met bruikbare W/kW worden volledige gedekte cycli geleerd. Een voorkeur-AEG en een vandaag veilig startklaar ticket behouden hun startkans volgens de centrale lijst. SG gebruikt uitsluitend overblijvende ruimte en neemt geen afwasvermogen af. Een al lopende beurt is geen algemeen SG-veto wanneer na alle reserves genoeg echte ruimte resteert.

Veilige overname van autonoom EV-zonnevermogen behoudt de bestaande afzonderlijke AEG-route en opt-in. De hele belasting moet passen vóór Wallbox-reactie. Een onzekere balans kan latere EV-gebaseerde starts blokkeren en een controle vragen, maar breekt de lopende beurt nooit af. Gerichte oudere profielherstelmigraties mogen alleen complete eenduidige koppelingen herstellen en maken zelf geen APP-ticket of fysieke START.

## 10. PV-model en Forecast.Solar

Forecast.Solar levert de basisverwachting via bestaande Home Assistant-bronnen en, waar ondersteund, de geladen coordinatorcurve. SolarPilot doet hiervoor geen nieuwe cloudpolling. Expliciete bronkeuzes blijven staan; bij precies één eenduidige installatie kan het register koppelingen vinden. Meerdere installaties vragen een bewuste keuze. Ontbrekende of oude forecast maakt geen virtueel huidig overschot.

Wattpiekvermogen van panelen en AC-omvormergrens blijven afzonderlijke instelwaarden. De actuele productiekleur en clipping gebruiken de ingestelde omvormergrens. SolarPilot wijzigt Forecast.Solar-instellingen niet. Geleerde lokale correctie wordt begrensd; onbekende delen van een curve of een scalar na haar lokale dag-/uurgrens worden niet automatisch nul of een nieuwe voorspelling.

Kwartierkalibratie verzamelt maximaal één verse waarneming per minuut. Een kwartier vereist minstens twaalf geldige waarnemingen, elf minuten spreiding en voldoende dekking. De eerste tien minuten na start/reload, clipping, ongeldige geschatte bronnen en sterk wisselende verhoudingen worden niet als structurele schaduw geleerd. Geweigerde kwartieren blijven met reden inspecteerbaar.

Het lokale model gebruikt vergelijkbare dagen, zonnegeometrie waar bruikbaar en seizoensgroepen, zonder vaste schaduwklok. Een empirische afwijking bewijst niet welke fysieke oorzaak haar gaf. Bron-/profielwijzigingen maken alleen onverenigbare PV-factoren opnieuw te leren; andere modellen worden niet gewist. Oude historische kwartieren zonder gelijktijdige forecast zijn geen bewezen live kalibratie.

PV-diagnose toont ruwe/gecorrigeerde/werkelijke W, dekking, fouten, geweigerde kwartieren en leerdagen. Zij wordt afzonderlijk opgevraagd en gebruikt bestaande lokale informatie. De bestaande grenzen van dertig dagen en 2880 diagnosekwartieren blijven gelden. Voorspellingssensoren zijn geen gecertificeerde energietellers; dagen bij zomer-/wintertijd worden op echte tijdstempels berekend.

## 11. Fasebewaking en fysieke grenzen

L1, L2 en L3 blijven afzonderlijk bewaakt wanneer geconfigureerd en bewust vrijgegeven. Netto-export over drie fasen bewijst niet dat iedere fase vrije stroomruimte heeft. Een ontbrekende vereiste fasekoppeling geeft geen algemene startvrijgave.

Faseherkenning leert alleen bruikbare voldoende geïsoleerde vermogenssprongen. Gelijktijdige veranderingen worden verworpen. Herkend toestelvermogen en netto restcomponent staan apart; die rest is geen zuiver onbekend verbruik omdat PV en andere stromen meespelen. Herkenning blijft adviserend tot bewuste activering. Beveiligingen, tekenrichting en betrouwbare actuele bronnen blijven noodzakelijk.

## 12. Thuisbatterij

Zonder gekoppelde hardware blijft de batterij-what-if adviserend. Fysieke batterijbediening vereist globale en individuele toestemming plus bevestigd exclusief eigenaarschap. Netladen en exportontladen staan standaard Uit. De eigen batterijcommandobescherming blijft bestaan en wordt niet door verwijdering van oude warmtepompsturing gereset.

Commandointentie wordt vóór actuatie duurzaam bewaard. Koppeling, native doel/eenheid/grenzen, toestemming en Wallboxbescherming worden direct voor verzending opnieuw getoetst. Een passende nieuwe vermogensrapportage van na de opdracht, en bij numerieke bediening ook een passend native doel, zijn nodig. Een oude al passende powerwaarde is geen nieuwe bevestiging; onzekere opdrachten worden niet blind herhaald.

Een pending batterijopdracht beschermt nieuwe starts en vermogensoverdracht tegen hergebruik van oude ruimte. Bestaande beschermde cycli blijven doorlopen. Na de actie zijn nieuwe P1 en normale wachttijden nodig. Voor verwijderen moet werkelijke neutrale power, en bij numerieke bediening een exact neutraal doel, betrouwbaar vaststaan. Handmatige doelen worden niet overschreven.

Batterijflow telt eenmaal mee; read-only of foutieve profielen behouden hun echte stroom zonder nieuw bedieningsrecht. SoC vraagt bruikbare procentdata binnen 0–100. Numerieke doelen moeten nul exact kunnen weergeven binnen bereik/stap. Scripts vragen controle van inhoud en terugmelding; een naam alleen bewijst geen veilige functie.

De what-if gebruikt standaard 80% round-trip efficiëntie, dus 20% totaalverlies over laden en later terugleveren. Dit blijft instelbaar en is geen aankoop- of besparingsgarantie. Bij meerdere batterijen gelden de bestaande verdeelstrategie en individuele grenzen.

## 13. Kwartierpiek, kosten en waardeschatting

Kwartiergemiddelde en maandpiek kunnen het ingestelde softwarematige importbudget beperken. Dat budget vervangt geen zekeringen of echte aansluiting. Dag-KPI’s zijn indicatieve toerekening en geen veiligheidsbron.

Elektriciteitskost vandaag telt geldige gemeten netafnamekost min injectievergoeding op. Direct gebruikte PV verlaagt de netafname al en wordt niet nogmaals afgetrokken. Prijzen horen bij hun werkelijke meetinterval; een later tarief verandert eerdere energie niet. Meetgaten blijven zichtbaar. De planningskost is een aparte toekomstschatting, geen dagkost.

Bij ontbrekende of ongeldige dynamische prijzen geldt het ingestelde vaste tarief. Een geldige nulprijs blijft nul, ontbrekende rijen verschuiven andere tijdposities niet. Negatieve prijzen en netto negatieve dagkosten blijven mogelijk. Bedragen bevatten geen vaste kosten, aanschaf, onderhoud of gegarandeerd capaciteitstarief.

Het geschatte voordeel van automatische sturing is een aparte voorwaartse telling met maximaal negentig kalenderdagen. Alleen werkelijk actieve eigen automatische gewone lasten tellen. Native Wallbox-, warmtepomp- en handmatig gebruik geven geen verzonnen SG-besparing of vaste COP. Dit voordeel wordt niet nogmaals van de dagkost afgetrokken.

## 14. Leren en modelgegevens

SolarPilot leert lokaal, zonder externe AI-dienst of het herschrijven van zijn code. Bruikbaar gemeten verbruik, basislast, PV-/weercorrectie, faseclassificatie en complete apparaatcycli kunnen analyse/planning verbeteren. Prioriteiten, deadlines, net-/fasegrenzen en fysieke toestemming veranderen niet autonoom door leren.

Oude woning-/tankmodellen en hun bewijs blijven bewaard voor privé-analyse en rollback. Zij verlenen in deze versie geen ruimte- of tankopdrachtrecht. Er is geen modelreset of nieuw actief klimaatleerregelpad. Bewaarde modelkwaliteit is geen kans dat een fysieke actie juist is.

Grote model- en leerattributen blijven live en in eigen SolarPilot-opslag/export beschikbaar. Alleen herhaalde zware kopieën in de gewone Home Assistant Recorderhistoriek zijn uitgesloten. De 16 KiB-grens betreft één attribuutpakket, niet vrije schijfruimte. Gedeelde weergavecache vermindert rekenwerk tijdens één publicatieronde; beslissingen en export gebruiken verse directe gegevens.

Leren & vragen maakt meetdekking, afwijkingen en voorgestelde keuzes zichtbaar. Gemeten verbruik kan volgens de ingestelde bronkeuze worden gebruikt; geschatte, dubbele of ongeschikte bronnen gelden niet als echte metingen. Een recente basislastaanpassing wordt eerst vergeleken en alleen binnen de bestaande begrensde toestemming toegepast. HA-leermeldingen blijven afzonderlijk van controlefouten.

## 15. Overzicht, uitleg en meldingen

Overzicht toont Wat gebeurt er en waarom? met per toestel de actuele toestand, één leidende reden, bekende W en uitklapbare voorwaarden. Gemeten, geschat en onbekend blijven herkenbaar. De warmtepomp gebruikt dezelfde SG-status en beslisreden als de backend, geen tweede frontendregelaar. Open details, formulieren, popup en scroll blijven bij verversen op vaste ids bewaard.

Doorlopend blauw betekent bevestigde activiteit; een aangevraagde of beschikbare functie blijft daarvan onderscheiden. Een gesloten SG-contact bewijst geen fysieke tankopwarming. Productie en net hebben afzonderlijke groen-roodkleuren; onbekende/oude bronnen blijven grijs. Die kleuren zijn uitsluitend presentatie, geen storing of vrijgave.

Resterende fouten waarvoor jouw controle nodig is verschijnen in Home Assistant → Meldingen → SolarPilot: controle nodig. De melding bundelt gerichte oorzaken en acties, wordt bij inhoudelijke verandering bijgewerkt en verdwijnt na herstel. Meldingtransport mag de regeling niet laten crashen. Gewone bronwacht, rusttijd, een bewuste Pauze of fabrikantsterilisatie veroorzaken geen nieuwe foutspam.

Een SG-koppelings- of terugvalprobleem blokkeert de betrokken SG-functie en noemt de ingebruiknamecontrole. Een oude gearchiveerde tank-/klimaatopdrachtfout wordt niet als actuele fysieke storing opgelost verklaard. Echte onbekende fouten, toestel-/batterijfouten, expliciete gebruikerskeuzes en verwijderverzoeken blijven beschermd. Controle afronden repareert geen verkeerde bronconfiguratie of onbereikbaar apparaat.

## 16. Apparaatgeschiedenis

Geschiedenis toont per toestel gekozen lokale dag, draaitijd, sessies en afzonderlijke start-/stopredenen. Een verzonden opdracht alleen is geen bevestigde start. Externe wijzigingen krijgen geen verzonnen gebruiker of automatisering als oorzaak. Een slimme stekker toont haar aan-tijd, niet noodzakelijk continu compressorbedrijf.

Herstart, reload, onbereikbaarheid en meetgaten begrenzen de waarneming en tellen onbekende tijd niet mee. Sessies over middernacht worden per lokale kalenderdag verdeeld; die dag kan 23 of 25 uur duren. Oude niet-geregistreerde redenen worden niet achteraf gereconstrueerd.

De bestaande eigen historie blijft bij updates staan: maximaal dertig kalenderdagen per gewone verbruiker, 2000 sessies en 300 extra gebeurtenissen. Bij volle detailgrens blijven dagtotalen met onvolledigheidslabel bestaan. Opslag is gebundeld; het laatste nog niet opgeslagen stukje kan bij een abrupte uitval ontbreken. Details worden alleen op aanvraag gelezen en bedienen niets.

## 17. Privé-analyse-export

Export → Export samenstellen levert voor een HA-beheerder één lokaal gecomprimeerd JSON.GZ-bestand voor 1 uur, 24 uur of zeven dagen. Het bevat actuele bron-/configuratiegegevens, beslisredenen, versie per nieuwe registratie, beschikbare historie en modellen. Oude records zonder versie blijven onbekend. Het bestand verandert geen toestel en wordt niet automatisch geüpload. Het is geen herstelbare HA-back-up.

Bronnamen en labels worden standaard consistent gepseudonimiseerd. Een expliciete keuze kan echte namen opnemen. Tokens, wachtwoorden, netwerk-/account-/locatiegegevens en ongeschikte privébronnen worden gefilterd. Tijdstippen en gebruikspatronen blijven aanwezig: controleer vóór delen en plaats geen analysebestand op publieke GitHub.

De beheerder-WebSocket geeft alleen downloadinformatie; het bestand wordt buiten de eventloop gecomprimeerd en daarna via geauthenticeerde lokale HTTP gedownload. De download is tien minuten geldig en wordt na ontvangst/afloop opgeruimd. Maximaal twee bestanden staan tegelijk klaar of worden gemaakt. De route beperkt de uitgepakte JSON niet tot 16 MB en verkort de gevraagde periode niet om die grens te omzeilen.

Alleen werkelijk bewaarde informatie is beschikbaar. De onderzoeksregistratie behoudt haar bestaande maximaal zeven dagen, 2016 gedetailleerde ronden, 20000 bronwijzigingen en 6000 gebeurtenissen. De laatste maximaal twee uur snelle punten blijven in RAM. Een korter registratie-interval kan door vaste aantallimieten een kortere ruwe periode geven. Geen onbeperkt archief, retentieverruiming of aanvulling van ontbrekende oude meetpunten.

## 18. Live configuratie en één eigenaar

Configureren opent de bestaande HA-optiesflow met uitleg bij de velden. Alleen expliciet opslaan kan een instelling veranderen; openen/renderen bedient niets. Gewone ongewijzigde toestellen behouden timers, listeners, leerdata en modus. Een HACS-codeupdate vereist nog wel een HA-herstart.

Koppeling-/meter-/beschermingswijzigingen aan actief of onzeker beheerde toestellen blijven onder de bestaande veilige voorstelroute staan. Naam en categorie kunnen zonder fysieke wijziging. Toestel vervangen geeft een nieuwe identiteit met voorkeuren als voorstel, geen oude fysieke rechten of startticket. Conflicterende edits en dubbele actuatoren/meters worden afgewezen.

De gekozen SG-uitgang mag niet tegelijk een gewone flexibele last of batterijactuator zijn. Backendvalidatie voorkomt dubbel eigenaarschap. Een gewijzigde SG-koppeling vereist opnieuw ingebruikname en kan geen oude AAN-bevestiging overnemen. Controleer externe automatiseringen die dezelfde uitgang of native Panasonic-instellingen nog schrijven; SolarPilot bewijst hun afwezigheid niet zonder live inzage.

Bij een wachtend APP-ticket kiest wijzigen van deadline/nettoestemming tussen volgende beladingen of expliciet hetzelfde huidige ticket. De bestaande kalenderdag blijft gelijk; er ontstaat geen START door opslaan. Wachtende voorstellen en archieven blijven inspecteerbaar. Alleen eigen virtuele SolarPilot-entiteiten mogen bij wijzigingen verdwijnen, nooit de oorspronkelijke apparaatentiteiten.

## 19. Migratie en veilige ingebruikname

Bij de beta.62-opstartfout volstaat de update naar beta.63 gevolgd door een volledige Home Assistant-herstart. Verwijder de integratie, configuratie, modellen of opslag niet. Deze herstelupdate leest de onveranderbare HA-opties als een gewone losse kopie, zonder oorspronkelijke of geneste opties te wijzigen. De bekende fout is lokaal met de onveranderbare HA-mappingvorm gereproduceerd vóór de migratiearchivering en opslag; dit is geen inspectie van jouw installatie.

Voor upgrade maak je een volledige privé Home Assistant-back-up inclusief configuratie en SolarPilot-opslag. De versiegebonden migratie archiveert oude warmtepompopties, modellen en relevante opdracht-/foutgegevens buiten de actieve regeling. Zij is idempotent en verstuurt geen tank-/klimaatopdracht, SG-boost of afwasstart.

Oude pending, doel-eigendom, hercontrole, foutwachttijden, manual hold en eigen klimaat-OFF kunnen niet opnieuw uitvoeren. Aantoonbaar uitsluitend vervallen regelopdrachtfouten worden als vervallen functie beoordeeld, niet als fysiek gerepareerd. Gemengde/onbekende foutpauzes, gewone apparaat-/batterijfouten, gebruikers-Pauze en verwijdering blijven beschermd. Brononzekerheid voor de nieuwe SG-functie blijft gelden.

De globale hervatvoorkeur, geldige andere toestellen, entity-identiteiten, opgeslagen prioriteiten, APP-tickets, historie en leerdata blijven behouden. Nieuwe SG-sturing blijft uit totdat juiste uitgang, native basisinstellingen, geen dubbele writers, contactmapping en lokale aflooptimer werkelijk zijn bevestigd. De noodzakelijke lokale Panasonic/Shelly-controle is geen softwaretest.

Controleer eenmalig op Panasonic de gewenste normale tank-/zone-/programma-instellingen, inclusief zelfstandig comfort en sterilisatie. Eerdere directe sturing kan iets hebben achtergelaten; deze nieuwe runtime schrijft dat niet terug. De fysieke SG-ingebruiknameproef gebeurt alleen met expliciete toestemming en zonder elektrische metingen in geopende apparatuur. Gebruik de korte controle in BETA63_INSTELLEN.md.

## 20. Installatie, verwijderen en rollback

Installeer of update de Integration via HACS en herstart Home Assistant. De frontend wordt meegeleverd en automatisch geregistreerd: geen aparte Lovelace-resource, dashboard-YAML of www-kopie. Heropen de webpagina/app en controleer geladen backend- en kaartversie afzonderlijk. Een download bewijst geen geladen browsercode.

Een privéprofiel blijft optioneel en uitsluitend lokaal. Importeren kan lege geldige bronkoppelingen aanvullen, maar activeert de SG-functie of nieuwe fysieke apparaatbediening niet. Bewaar userfiles en eigen HA-opslag; voeg ze niet aan publieke bron of pakket toe.

Voor verwijderen kies je Verwijderen voorbereiden en wacht je op de gerichte veilige vrijgave. Een onzekere SG-uitgang blijft eerlijk onbekend; de gecontroleerde lokale terugval begrenst de eigen aanvraag. Verwijderen van SolarPilot verwijdert geen oorspronkelijke meter-, warmtepomp-, Wallbox-, AEG- of Shelly-integratie.

Rollback vereist de gecontroleerde beta.61-bron én de bijbehorende privé-opslag/back-up van vóór migratie. Alleen een oudere ZIP terugzetten herstelt de opslag niet. Geef eerst de SG-aanvraag vrij, voorkom gelijktijdig oude Panasonic-writers en nieuwe SG-regelaar, herstel de passende back-up en start bewust met de gewenste globale modus. Zie de releasegebonden installatiehandleiding.

## 21. Release- en documentatieregel

Dit is de enige volledige actuele regelbeschrijving. current_guide.py genereert dezelfde Markdown-mirrors en HA-uitleg. Optiehulp, versie, changelog, OVERDRACHT.md, installatie, rollback en testverslag horen bij dezelfde bronrelease. Historische releasebestanden beschrijven oudere versies en zijn geen actuele bediening.

Softwaretests en geverifieerde publicatiepakketten bewijzen geen live HA-installatie, echt Shelly-timergedrag of fysieke Panasonic-reactie. Die bewijssoorten worden apart gerapporteerd. Publieke voorbeelden zijn fictief; persoonlijke installatiegegevens, ruwe exports en geheimen blijven lokaal.

---

Deze pagina wordt automatisch uit dezelfde bron gegenereerd als de uitleg die Home Assistant toont. Het First Install-pakket bevat alleen de actuele installatie- en gebruiksdocumentatie.
