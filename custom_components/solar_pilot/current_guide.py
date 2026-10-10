"""Single release-bound guide; regenerate bundled documentation after changes."""
from __future__ import annotations
import hashlib
import json

GUIDE_VERSION = '1.0.0-beta.67'
GUIDE_UPDATED = '2026-10-11'

CURRENT_GUIDE = {'title': 'SolarPilot · Actuele werking',
 'version': '1.0.0-beta.67',
 'updated': '2026-10-11',
 'intro': 'De warmtepomp staat naast de andere toestellen met een afzonderlijke taakmelding, gemeten '
          'elektrische activiteit en elektrische bijverwarming. Verse native taakmeldingen blijven '
          'herkenbaar als Panasonic meldt; meter- en contextafleidingen krijgen hun eigen uitleg. Het '
          'bestaande meterpaar gebruikt automatisch een zichtbaar Panasonic-voedingsprofiel, zonder nieuwe '
          'invoer. Een geanimeerd symbool toont actuele elektrische activiteit, geen afzonderlijk gemeten '
          'compressorbeweging of warmteproductie. SolarPilot geeft één rustige, begrensde SG-zonneboost '
          'warmtepomp. Het lokaal bevestigde toepassingsbereik bepaalt of uitsluitend tapwater of het '
          'algemene Panasonic-bedrijf wordt ondersteund. Panasonic blijft volledig eigenaar van comfort en '
          'beveiligingen. Alleen complete bevestigde niet-overlappende metingen vormen het totaal. Aanvraag, '
          'contactstand, bedrijfsbewijs en ontvangen SG-status blijven afzonderlijk. Andere '
          'SolarPilot-apparaten, instellingen en privédata behouden hun bestaande regels.',
 'sections': [{'title': '1. Basisprincipe en modi',
               'paragraphs': ['SolarPilot verdeelt beschikbare zonnestroom lokaal in Home Assistant. Actuele '
                              'net- en PV-metingen, echte toestelvoorwaarden en elektrische grenzen gaan '
                              'altijd vóór een voorspelling of geleerd patroon. Eén uitgang heeft één '
                              'eigenaar. Een regeling vervangt geen elektrische beveiliging.',
                              'Alleen bekijken berekent en registreert zonder nieuwe flexibele toestellen te '
                              'starten. Automatisch regelen voert uitsluitend de toegestane apparaatbediening '
                              'uit. Pauze start niets nieuws en geeft eigen onderbreekbare lasten veilig vrij, '
                              'met behoud van minimumlooptijden en beschermde cycli. Een eigen SG-zonneboost '
                              'wordt ingetrokken; de warmtepomp zelf blijft onder Panasonic-regie. Eigen '
                              'bevestigde numerieke batterijdoelen behouden hun afzonderlijke veilige '
                              'vrijgaveroute.',
                              'Na herstart automatisch hervatten staat standaard Aan. Een gewone opgeslagen '
                              'Pauze vraagt na Home Assistant-start of herladen weer Automatisch regelen via '
                              'de bestaande controles. Alleen bekijken, eerste installatie, echte interne '
                              'fout- en verwijderpauzes blijven beschermd. De voorkeur wijzigen verandert de '
                              'huidige modus niet. Opnieuw Pauze kiezen annuleert een wachtende hervatting. '
                              'SG-ingebruikname en een oude boost krijgen hierdoor geen automatische '
                              'bevestiging.',
                              'Na een herstart leest SolarPilot echte toestelstatussen. Een tijdelijk '
                              'onbereikbaar eerder beheerd toestel wordt afzonderlijk opzijgezet; onbekend '
                              'verbruik wordt niet als nul gerekend. De overige lasten kunnen verder zodra hun '
                              'eigen voorwaarden en globale net- en veiligheidsmetingen betrouwbaar zijn. Het '
                              'ontbrekende toestel wordt opnieuw beoordeeld zodra bruikbare brongegevens '
                              'terugkeren. Onzekere fysieke opdrachten worden niet blind herhaald.'],
               'bullets': []},
              {'title': '2. Overschot, centrale voorrang en planner',
               'paragraphs': ['De volledige netmeter bepaalt werkelijke afname en injectie. W en kW worden '
                              'naar hetzelfde vermogen omgerekend; een kWh-teller is geen actuele '
                              'vermogensbron. De tekenafspraak wordt bewust gekozen. Restored, ontbrekende, '
                              'toekomstige, niet-eindige of verkeerd gevormde waarden geven geen vrijgave. Een '
                              'onveranderde waarde kan actueel zijn wanneer haar echte ontvangst of bruikbare '
                              'heartbeat dat bewijst.',
                              'Voorrang is de enige flexibele rangorde. De opgeslagen gebruikersvolgorde '
                              'blijft bij deze update staan; een oude rangordemigratie wordt niet opnieuw '
                              'toegepast. De rij voor extra warmwaterproductie vertegenwoordigt voortaan '
                              'SG-zonneboost warmtepomp. Zij mag geen Wallbox-vermogen, beschermde afwascyclus '
                              'of noodzakelijk Panasonic-comfort afnemen. Nieuwe gewone toestellen komen '
                              'onderaan totdat je ze verplaatst.',
                              'Start- en stopvertragingen, minimum aan/uit-tijden, dagdoelen, tijdvensters en '
                              'beschermde programma’s blijven gelden. Een hoger toestel dat niet past hoeft '
                              'een kleiner passend toestel niet te blokkeren. Lager geplaatste, werkelijk '
                              'eigen en veilig onderbreekbare lasten kunnen alleen volgens de bestaande '
                              'overdrachtvoorwaarden wijken. Eerst bevestigde UIT en nieuwe net-/PV-metingen; '
                              'een stopverzoek is nog geen vrij vermogen.',
                              'De planner herberekent de ingestelde horizon in kwartierblokken met beschikbare '
                              'PV, basislast, tarieven, kwartierpiek en batterijruimte. Hij kan alleen '
                              'expliciet vrijgegeven flexibele lasten plannen. Het huidige blok kan de gewone '
                              'realtime regeling ondersteunen, maar nooit te weinig werkelijk overschot '
                              'overstemmen. Er is geen actieve warmtepomp-, tanktemperatuur- of '
                              'klimaatplanning meer.',
                              'Een dagdoel in kWh gebruikt werkelijk gemeten toestelenergie waar een '
                              'exclusieve meter bestaat, anders een herkenbare schatting. Een beschermde '
                              'cyclus wordt als aaneengesloten taak gepland. Zonder betrouwbaar duurprofiel '
                              'wordt geen optimistische duur uit piekvermogen gegokt. Een lopende beschermde '
                              'cyclus wordt niet gestopt wegens een nieuw plan. Goedkope netfallback blijft '
                              'afzonderlijke dubbele toestemming en standaard uit.',
                              'Plannerkwaliteit toont meetdekking, voorspellingsfout en uitvoering '
                              'afzonderlijk. Een historische replay is richtinggevend en reconstrueert niet '
                              'iedere vroegere startvoorwaarde. Een volledige lokale dag heeft normaal 96 '
                              'kwartieren, bij de zomer-/wintertijdwissel 92 of 100; gaten worden geen '
                              'volledige prestatie.'],
               'bullets': []},
              {'title': '3. Warmtepomp — Panasonic-regeling / SG-zonneboost voor warm water, verwarmen en '
                        'koelen',
               'paragraphs': ['Panasonic regelt zelfstandig normaal warm water, tankhysterese, '
                              'kamerthermostaten en zones, stooklijnen, verwarmen/koelen, omschakeling, '
                              'compressor, pompen, kleppen, ontdooien, elektrische ondersteuning en '
                              'sterilisatie. Dit blijft zo wanneer SolarPilot of Home Assistant uitvalt.',
                              'Voor de warmtepomp mag SolarPilot alleen de expliciet toegewezen bestaande '
                              'Shelly-uitgang voor SG-zonneboost bedienen. Tank- en kamertemperaturen, '
                              'native programma, activiteit, beschikbaarheid en vermogen zijn verder '
                              'uitsluitend uitleesbaar. SolarPilot schrijft geen tankdoel, AUTO/UIT, '
                              'HEAT/COOL, kamertemperatuur, Powerful, Force DHW, Force Heater, stooklijn of '
                              'heater-toestemming.',
                              'De oude eigen temperatuurfasen, nacht-/ochtend-/avondvoorraadregeling, '
                              'klimaatpauzes, voorspellende voorverwarming/voorkoeling en hun '
                              'opdrachtbevestiging/herstelbediening zijn verwijderd. Normale doelen en '
                              'fabrikantprogramma’s worden op Panasonic ingesteld. De nieuwe regeling '
                              'corrigeert geen mogelijk door een oudere versie achtergelaten native '
                              'instelling: controleer die eenmalig bij ingebruikname.',
                              'De warmtepomp staat in Overzicht en Toestellen tussen de andere blokken en '
                              'heeft dezelfde actuele uitleg onder Warmtepomp. Vervallen boiler- en '
                              'klimaatregeling wordt niet meer als ontbrekende configuratie getoond. Twee '
                              'vaste onderdelen tonen Taak van de warmtepomp en Elektrische bijverwarming; '
                              'daarnaast blijven tankinformatie, beide voedingsmetingen, totaal waar '
                              'compleet, SG-lagen, beslisreden en Details beschikbaar.',
                              'De hoofdtaak gebruikt een verse passende werkelijke native taakmelding en '
                              'benoemt haar als Panasonic meldt. De exacte bestaande Aquarea-binding kan de '
                              'actuele DeviceAction HEATING (2), COOLING (3) of HEATING_WATER (4) '
                              'automatisch read-only uitlezen. Passende expliciete native acties kunnen '
                              'eveneens ruimteverwarming, ruimtekoeling of tankopwarming melden. Deze '
                              'taakmelding staat los van hoeveel vermogen de meters op dat moment zien: '
                              'nul, basisverbruik of een ontbrekend totaal wist haar bronbetekenis niet. De '
                              'melding bewijst niet apart dat de compressor draait of hoeveel warmte wordt '
                              'geproduceerd.',
                              'Afgeleid elektrisch bedrijf en taakcontext blijven afzonderlijk herkenbaar. '
                              'Verse geldige meterwaarden tonen actief verbruik vanaf de standaard '
                              'weergavegrens van 200 W. Een passende verse tankroute kan alleen met verse '
                              'actieve hoofdvoeding én compleet actueel totaal sanitair water opwarmen '
                              'afleiden, met de gebruikte bronnen als uitleg. Actieve ondersteuning met '
                              'hoofdvoeding op nul of basisverbruik heet Elektrische bijverwarming actief '
                              'en geeft zelf geen warmwater- of ruimtefunctie. Alleen een gekozen '
                              'heating-tankstand is geen werkelijk gemelde opwarmactie; de kaart noemt '
                              'zulke informatie Tankroute of Gekozen stand wanneer zij alleen context '
                              'geeft. Oude, ontbrekende of tegenstrijdige context levert geen actuele '
                              'functieclaim. Zonder actuele taakmelding verschijnt Geen actuele '
                              'taakmelding, zonder prominente Werking onbekend-badge.',
                              'Een gekozen koelprogramma met tankmogelijkheid is geen tegenstrijdige '
                              'werkelijke taakmelding: verse werkelijke tankopwarming kan naast die keuze '
                              'worden gemeld. Gelijktijdige tegenstrijdige werkelijke ruimte- en tankacties '
                              'geven wel geen eenduidige functie. Een geverifieerde verse ontdooimelding '
                              'houdt haar eigen betekenis en onderdrukt een gewone '
                              'warmwater-/ruimtefunctie. Zij wordt niet uit watts, temperatuur of tijd '
                              'gegokt en verandert geen native programma, koelvrijgave of SG-toestemming.',
                              'De elektrische bijverwarming heeft een eigen voedingswaarde en activiteit. '
                              'Het bestaande paar verschillende gebonden sensoren gebruikt automatisch het '
                              'herkenbaar benoemde Panasonic-profiel: voeding 1 voor warmtepomp inclusief '
                              'regeling/pompen, voeding 2 voor elektrische bijverwarming. Dat is een '
                              'presentatie-aanname en geen gecontroleerde bedrading of afzonderlijke '
                              'heaterterugmelding. Eerder bewust gekozen afwijkende geldige rollen blijven '
                              'staan. Verse hoge voeding-2-meting kan Bijverwarming aan · afgeleid tonen, '
                              'nul Geen verbruik, laag positief Basisverbruik en ontbrekend of oud Geen '
                              'actuele meting. Zonder gekoppelde heaterdeelmeting heet dit Geen '
                              'heaterdeelmeting. Wattages onderscheiden geen interne backupheater en '
                              'eventuele tapwaterbooster.',
                              'Blauwe grafische activiteit en ventilatoranimatie tonen bevestigde '
                              'activiteit of actueel elektrisch bedrijf van de hoofdvoeding. De ventilator '
                              'mag daarom bij verse actieve hoofdmeting bewegen, ook als een afzonderlijke '
                              'Hz-bron 0 Hz meldt; dit is geen bewering over echte compressor- of '
                              'ventilatorbeweging. Bij alleen elektrische bijverwarming en een niet actieve '
                              'hoofdvoeding blijft het ventilatorsymbool stil en beweegt het '
                              'verwarmingssymbool. Bij oude of ongeldige betrokken bronnen verdwijnt hun '
                              'activiteit. De systeemvoorkeur voor verminderde beweging onderdrukt '
                              'animaties; tekst en activiteit blijven leesbaar.',
                              'De echte actuele compressorfrequentie blijft afzonderlijk compressorbewijs. '
                              'Alleen wanneer geen compressorbron is gekoppeld kan een verse passende '
                              'native activiteitsmelding bedrijf of rust bevestigen. Een gekoppelde maar '
                              'oude, onbeschikbare of ongeldige compressorbron blijft technisch onbekend; '
                              'een verse meter of andere bron verbergt dit niet. Programma, '
                              'WATER-/klepstand, alleen gemeten watts en een bewegend symbool bewijzen geen '
                              'compressorbedrijf. De gekozen modus, native taak, elektrische activiteit en '
                              'werkelijk gemelde compressoractiviteit blijven apart.',
                              'De gemelde SG-contactstand staat prominent op de kaart. SolarPilot-aanvraag, '
                              'eigenaar en reden staan in Details en blijven afzonderlijk van wat Shelly '
                              'terugmeldt. Een bekende afwijking tussen aanvraag en contact krijgt een '
                              'duidelijke waarschuwing; zij wordt niet uit vermogen of taakmelding opgelost '
                              'verklaard. Ontvangen SG wordt alleen zichtbaar als een echte passende '
                              'actuele bron de ontvangen stand bevestigt. Zonder zo een bron verschijnt '
                              'geen permanent onbekende ontvangen-SG-indicator; de onderliggende '
                              'onzekerheid en broninformatie blijven beschikbaar in Details/export. '
                              'SG-contact AAN is de gemelde uitgang, geen bewijs van werkelijk ontvangen '
                              'SG. Ook een draaiende compressor, native taak, stijgende tanktemperatuur of '
                              'animatie bewijst geen door SG veroorzaakte extra opname. De bevestigde '
                              'lokale resterende toestemming houdt haar eigen betekenis. Oude bronwaarden '
                              'geven geen actueel AAN/UIT- of ontvangenbewijs. Een gelijkblijvend '
                              'app-tankdoel is geen relaisfout en geen bewijs over het effectieve SG-doel.'],
               'bullets': []},
              {'title': '4. SG-zonneboost warmtepomp: lokaal toepassingsbereik en rustige herbeoordeling',
               'paragraphs': ['Automatische zonneboost staat standaard Uit. Activeren vereist de juiste '
                              'bestaande uitgang, bevestigde contactmapping, gecontroleerde Panasonic-reactie, '
                              'uitsluiting van dubbele sturing en bewezen lokale terugval bij '
                              'communicatieverlies. Een geopende instellingenpagina, geselecteerde entiteit of '
                              'opgeslagen globale Auto-modus is geen ingebruiknamebewijs.',
                              'Kies Uitsluitend tapwater of Algemene SG-boost volgens Panasonic-bedrijf en '
                              'bevestig het toepassingsbereik lokaal. De algemene keuze staat extra tapwater, '
                              'ruimteverwarming of koeling toe volgens de actuele native bedrijfsmodus en het '
                              'lokaal gekozen SG-profiel. Eén contact vraagt geen gelijktijdige productie van '
                              'tapwater en ruimtewarmte. SolarPilot schrijft geen Panasonic-percentages of '
                              'temperaturen en maakt daar geen universele vermogens- of temperatuurformule '
                              'van. Een gewenste klimaatverhoging is geen configuratiefout. Een wijziging van '
                              'toepassingsbereik vereist opnieuw bewuste lokale bevestiging; een upgrade '
                              'bevestigt of activeert het algemene profiel niet.',
                              'De regeling onderscheidt normaal, wachten op voldoende overschot, boost '
                              'aangevraagd, rusttijd en geblokkeerd. Voldoende bruikbaar werkelijk '
                              'zonneoverschot moet stabiel beschikbaar zijn. Standaardwaarden blijven 3000 W '
                              'startdrempel en een afzonderlijke conservatieve vermogensraming van 3200 W. Die '
                              'raming is geen meting of gegarandeerd SG-verbruik. Oude drempels en '
                              'vermogensramingen blijven als kandidaten in het private migratiearchief; '
                              'beoordeel en bevestig de SG-instellingen afzonderlijk.',
                              'Standaardvertraging voor starten is 120 seconden, voor een aanhoudend tekort 60 '
                              'seconden, met 900 seconden rust tussen sessies en maximaal 3600 seconden per '
                              'sessie. Geldige recente metingen, toewijzing, fasegrenzen, eigen bediening en '
                              'de lokale timer gaan vóór een gewenste minimale boostduur. Een harde limiet of '
                              'onbetrouwbare noodzakelijke bron geeft de eigen aanvraag vrij.',
                              'Na een toegelaten start hoeft de resterende injectie niet boven de startdrempel '
                              'te blijven: de warmtepomp kan juist die zon gebruiken. De kleine-importbuffer '
                              'blijft standaard 300 W. Netafname boven die buffer gedurende de stopvertraging '
                              'geeft alleen de extra SG-aanvraag vrij; tijdens die tekortcontrole wordt de '
                              'lokale toestemming niet verlengd. Dit garandeert geen nulimport en stopt geen '
                              'noodzakelijke native cyclus.',
                              'Een sessielimiet beëindigt de aanvraag, maar bewijst geen volle tank of '
                              'voltooide native cyclus. Wachtredenen onderscheiden sessielimiet, werkelijk '
                              'native voltooid, geen aangetoonde opname en onbekende reactie. De algemene '
                              'wachtstand blijft ook na een onderbroken sessie gelden, zoals lokale '
                              'timerafloop, bronverlies, netvrijgave of reload. Een onbekende reactie is geen '
                              'voltooiingsbewijs. De bewaarde beleidswachtstand staat los van echte '
                              'handmatige, communicatie- en veiligheidsblokkeringen. Alleen het verlopen van '
                              'rust, dezelfde samples opnieuw lezen of Home Assistant herstarten geeft geen '
                              'nieuwe aanleiding.',
                              'Voor Uitsluitend tapwater blijft de bestaande anti-herhaalregel behouden: een '
                              'verse betrouwbare tankmeting bij het sessie-einde is de referentie. Na rust kan '
                              'minstens 2 °C afkoeling van dezelfde bron, met minstens twee nieuwe echte '
                              'rapporten over vijf minuten, een nieuwe zonbeoordeling toestaan. Dit toont '
                              'nieuwe opslagruimte, geen comfortvraag, bewezen eerdere SG-opwarming of '
                              'effectief tankdoel. Na reload is een nieuwe vijfminutenbevestiging nodig. '
                              'Zonder bruikbaar eindbewijs, na bronwisseling of bij onbetrouwbare data blijft '
                              'deze wachtstand staan.',
                              'Voor het lokaal bevestigde algemene profiel is een warme, onveranderde of niet '
                              'gemeten tank op zichzelf geen permanente blokkering. Na iedere beëindigde of '
                              'onderbroken algemene sessie vereist herbeoordeling na rust betekenisvol nieuw '
                              'bewijs, telkens met minstens twee nieuwe echte rapporten over vijf minuten: een '
                              'gewijzigde betrouwbare relevante native bedrijfscontext, of een nieuwe '
                              'relevante actieve native episode na eveneens bevestigde rust. Een aantoonbaar '
                              'nieuwe zonneperiode kan ook gelden: eerst minstens vijf minuten restoverschot '
                              'hoogstens de ingestelde kleine-importbuffer, daarna minstens vijf minuten '
                              'restoverschot vanaf de startdrempel. Constante zon, ongewijzigde context, tijd '
                              'of reload geeft geen herstartlus. Vastgelegde bewijslagen blijven bij reload '
                              'staan, lopende bevestigingsvensters beginnen met nieuwe rapporten. De volledige '
                              'gewone startvertraging en alle actuele guards gelden daarna opnieuw. Bewust '
                              'Automatisering hervatten laat een nieuwe actuele beoordeling toe, geen '
                              'ongecontroleerde AAN.',
                              'Extra koeling heeft een afzonderlijke vrijgavevoorwaarde. De bewuste algemene '
                              'profielkeuze bewijst geen condensveiligheid. Bevestig lokaal bestaande '
                              'geschikte condens-/dauwpuntbeveiliging vóór extra SG in koelbedrijf. Zonder die '
                              'bevestiging laat het algemene profiel alleen extra SG toe als verse native '
                              'context betrouwbaar uitsluit dat koeling mogelijk is. Werkelijke koeling, AUTO '
                              'of onbekende context geeft geen stilzwijgende vrijgave. Normale '
                              'Panasonic-koeling en de ingestelde SG-koelwaarde worden niet gewijzigd. Een '
                              'vaste minimumtemperatuur of alleen een luchtvochtigheidssensor is geen '
                              'volledige beveiligingsbevestiging.',
                              'Extra SG volgt de opgeslagen flexibele rangorde, zonder EV-vermogenskrediet. '
                              'Een lager geplaatst eigen onderbreekbaar toestel mag alleen veilig wijken als '
                              'minimumlooptijd, gebruikerskeuze en overige bescherming dat toelaten. Een '
                              'afwascyclus, Wallbox en native noodzakelijk klimaat-/warmwaterverbruik worden '
                              'daarvoor niet uitgezet.'],
               'bullets': []},
              {'title': '5. Lokale SG-terugval en handmatige bediening',
               'paragraphs': ['Opstartstand UIT is geen uitschakeling bij wifi- of Home Assistant-uitval. '
                              'Daarom gebruikt automatische SG-bediening een lokaal op de Shelly aflopende '
                              'toestemming: standaard 300 seconden geldig, vernieuwd iedere 60 seconden zolang '
                              'de actuele boost toegestaan blijft. Vernieuwing moet de timer verlengen zonder '
                              'het relais uit/aan te schakelen. De korte communicatietoestemming staat los van '
                              'de langere maximale boostsessie. Iedere vernieuwing is ook begrensd tot de '
                              'resterende sessieduur. Tegen het sessie-einde blijft een toereikende bestaande '
                              'timer lopen zonder nieuwe volle lease; de aanvraag kan de ingestelde '
                              'bevestigingsmarge eerder eindigen. Afloop geeft geen recht op een nieuwe sessie '
                              'of oude ON-replay.',
                              'Zonder ondersteunde, echt gecontroleerde lokale aflooptimer geen automatische '
                              'boost. De software registreert expliciete AAN/UIT-opdrachten, nooit een blinde '
                              'toggle. Een geaccepteerde serviceaanroep bewijst geen relaisstand, lopende '
                              'lokale timer of fysieke Panasonic-reactie. Bij onbereikbaarheid blijft de '
                              'uitgang onbekend; er komt geen fictieve UIT-bevestiging en geen eindeloze '
                              'retry.',
                              'Pauze, uitschakelen van SG-optimalisatie, gewijzigde koppeling en unload '
                              'annuleren oude vernieuwingen en trekken de eigen aanvraag in waar betrouwbaar '
                              'mogelijk. Een lokale timer laat die aanvraag ook zonder Home Assistant '
                              'verlopen. Een late AAN-terugmelding verleent geen nieuwe toestemming. Na '
                              'herstart wordt een achtergebleven eigen aanvraag eerst verzoend/vrijgegeven en '
                              'volgt een nieuwe beoordeling met verse gegevens, geen replay.',
                              'Een werkelijk handmatige wijziging wordt gerespecteerd. Een buiten SolarPilot '
                              'ingeschakeld contact heeft niet automatisch een door SolarPilot bewezen lokale '
                              'timer. Automatisering hervatten is een afzonderlijke duidelijke keuze; zij '
                              'start geen boost zonder actuele voorwaarden. Een eigen vertraagde terugmelding '
                              'of lokaal verlopen toestemming wordt niet zonder bewijs als gebruikershandeling '
                              'behandeld.',
                              'Langdurig laag gemeten vermogen is geen opdracht om de Shelly te pulsen, de '
                              'warmtepomp te herstarten of een Force-/heateropdracht te geven. Na twintig '
                              'minuten nieuwe actuele lage vermogensrapporten zonder bevestigde '
                              'compressoractiviteit verschijnt één diagnose in Details en op de bestaande '
                              'tijdlijn: SG-contact actief; extra warmteopname nog niet aangetoond. Dit is '
                              'geen fout of grond om gezonde andere toestellen te blokkeren. De lage grens '
                              'dient alleen diagnose, geen start- of veiligheidsdrempel. Aanvraag, fysieke '
                              'relaiswissel, timervernieuwing, beschikbare native context en metingen blijven '
                              'binnen de bestaande begrensde tijdlijn.',
                              'De lokale timer is geen vervanging voor elektrische beveiliging en geen '
                              'absolute garantie bij bijvoorbeeld een vastgelast contact. Deze release vraagt '
                              'geen extra heaterrelais, broker, server, cloudregelaar of wijziging aan '
                              'bedrading of DIP-schakelaars.'],
               'bullets': []},
              {'title': '6. Warmtepompvermogen en elektrische ondersteuning',
               'paragraphs': ['Koppel één bestaande bevestigde totaalmeter, of twee lokaal bevestigde '
                              'volledige niet-overlappende deelmeters voor voeding 1 en voeding 2. Beide '
                              'routes lezen actuele W/kW, valideren eenheid, tekenrichting, plausibiliteit '
                              'en echte rapportage/heartbeat. De bestaande geldige single-meterkeuze blijft '
                              'bij upgrade behouden. Selecteer geen P1/PV, energieteller in kWh of interne '
                              'Shelly-temperatuur als exclusieve warmtepompvermogensbron.',
                              'Alleen twee complete actuele gevalideerde deelmetingen vormen samen het '
                              'totaal: voeding 1 plus voeding 2. Een ontbrekende, oude of ongeldige '
                              'deelmeter maakt het totaal onvolledig/onbekend; de wel bekende deelwaarde '
                              'blijft zichtbaar. Een actuele 0 W is gemeten nul. Gelijke bronnen, totaal '
                              'plus deelmeter en inspecteerbare template-overlap worden geweigerd; verborgen '
                              'overlap vereist lokale bevestiging. Een al inbegrepen heater wordt niet '
                              'nogmaals opgeteld.',
                              'Bij twee verschillende bestaande gebonden vermogenssensoren gebruikt de '
                              'weergave automatisch het Panasonic-voedingsprofiel: voeding 1 omvat de '
                              'warmtepomp, regeling en pompen; voeding 2 wordt als elektrische bijverwarming '
                              'uitgelegd. De kaart noemt dit uitdrukkelijk een aanname. '
                              'Panasonic-documentatie kent modelverschillen: elektrische ondersteuning kan '
                              'een interne backupheater en/of een externe tapwaterbooster omvatten, en bij '
                              'sommige varianten ligt backupverwarming op de eerste voeding. Het profiel '
                              'bevestigt daarom geen werkelijke lokale bedrading. Voeding 1 is geen zuivere '
                              'compressormeter en voeding-2-watts onderscheiden backup en booster niet.',
                              'De standaardweergave werkt automatisch met bestaande koppelingen en 200 W; je '
                              'hoeft geen nieuw formulier of leesentiteit in te vullen. Alleen als je zelf '
                              'wilt verfijnen, kan Actief verbruik vanaf (W) — alleen weergave tussen 10 en '
                              '2000 W worden gekozen. Zij bepaalt uitsluitend wanneer de elektrische '
                              'activiteit per geldige voeding wordt getoond en verandert geen '
                              'SG-start-/stopdrempel, bronvalidatie, timer, koelvrijgave, budget of '
                              'toestemming. Compleet totaal nul heet Geen elektrisch verbruik; positief '
                              'totaal onder de grens Basisverbruik. Actieve watts geven elektrische '
                              'activiteit, geen aparte compressor- of warmteproductiemeting.',
                              'Elke verse geldige deelmeting heeft haar eigen betekenis, ook als het totaal '
                              'onvolledig is. Actieve hoofdvoeding kan warmtepompactiviteit tonen en actieve '
                              'ondersteuning haar eigen bijverwarmingsmelding. Een bekende nul op één '
                              'voeding bewijst niet dat de hele installatie niets verbruikt. Alleen complete '
                              'actuele gevalideerde niet-overlappende dekking kan het totaal of totale '
                              'elektrische inactiviteit tonen. Een verse native taakmelding kan apart '
                              'blijven staan bij een deelmeting, lage watts of ontbrekend totaal; een taak '
                              'die uit meter plus context wordt afgeleid houdt dat brononderscheid.',
                              'Functie voeding 1/2 — automatische weergave is optioneel. Automatisch volgens '
                              'Panasonic-voedingen gebruikt het genoemde profiel op het bestaande '
                              'verschillende sensorpaar; expliciete keuzes zijn Hoofdvoeding: warmtepomp, '
                              'regeling en pompen of Elektrische ondersteuning. Eerder bewust gekozen '
                              'afwijkende rollen blijven behouden. Een enkelvoudige meter krijgt geen '
                              'automatisch hoofd-/heaterpaar. De totale niet-overlapbevestiging en de '
                              'onderdeelrol zijn afzonderlijk: de profielaanname maakt geen onvolledige som '
                              'compleet en geeft geen SG- of heaterbedieningsrecht. Na een echte '
                              'meterwijziging blijven de bestaande dekkingscontrole en herbeoordeling van '
                              'afwijkende rollen gelden.',
                              'Het SG-contact is een afzonderlijk signaal, geen vermogensvoeding. '
                              'Compressorbedrijf met 0 W op de ondersteuningsmeter is mogelijk en bewijst '
                              'geen SG-effect. Optionele actuele compressorfrequentie gebruikt een echte '
                              'Hz-bron. Zonder gekoppelde compressorbron kan passende verse native '
                              'activiteit bedrijf of rust bevestigen; alleen programma, klepstand of watts '
                              'niet. Een geschikte actuele ontvangen-SG-bron kan een expliciete '
                              'actieve/inactieve SG-stand bevestigen; numerieke standen worden niet gegokt. '
                              'Ontvangen SG en een draaiende compressor bewijzen geen causaal extra '
                              'SG-effect.',
                              'Het hele warmtepompvermogen is niet terugwinbaar door SG uit te zetten: '
                              'native warmwater- of ruimtebedrijf kan blijven doorgaan. De netmeter bevat '
                              'die stroom al. Vrijgekomen ruimte wordt pas toegewezen wanneer nieuwe '
                              'metingen dat ondersteunen. Betrouwbaar werkelijk verbruik is geen onbeperkte '
                              'nieuwe startcapaciteit of bewijs dat al dat vermogen door SG wordt '
                              'veroorzaakt.',
                              'Elektrische bijverwarming blijft volledig onder Panasonic-regie. Afgeleid '
                              'opgenomen vermogen via de aangenomen of expliciete voedingsrol is geen '
                              'afzonderlijk bevestigde native heaterstatus en maakt geen onderscheid tussen '
                              'backup-/boosterelementen. Compressor en ondersteuning kunnen tegelijk actief '
                              'zijn. Een afzonderlijk werkpunt is geen gegarandeerd totaal, heatermaximum of '
                              'startdrempel. Er is geen belofte van nul netafname of uitsluitend '
                              'compressorbedrijf. Bij aanhoudende ongewenste import wordt uitsluitend de '
                              'optionele eigen SG-aanvraag vrijgegeven.'],
               'bullets': []},
              {'title': '7. Wallbox: uitsluitend uitlezen en voorrang',
               'paragraphs': ['SolarPilot bedient de Wallbox niet: geen start, stop, laadstroom, laadmodus of '
                              'faseopdracht. De laadpaal kan autonoom Full Solar regelen of manueel/gepland '
                              'laden. Een ingestelde Full Solar-optie is geen bewijs dat de effectieve sessie '
                              'op zon terugregelt. Een betrouwbare effectieve-sessiebron onderscheidt '
                              'zonneladen, manueel en gestopt; een manuele melding gaat vóór de instelling.',
                              'Voorwaardelijk overneembaar EV-vermogen bestaat alleen voor een toegestaan '
                              'toestel boven de Wallbox in de centrale lijst, met afzonderlijke toestemming en '
                              'betrouwbare eigen meter/adapter en bevestigde zonnelaadsessie. SG-zonneboost '
                              'gebruikt dit krediet nooit. Bij manueel, oud, onbekend of strijdig laden blijft '
                              'alleen echte restinjectie bruikbaar. Geen ontbrekende sessiestatus gokken uit '
                              'netafname.',
                              'EV-vermogen vergroot geen elektrische capaciteit. De volledige nieuwe belasting '
                              'moet vóór een opdracht binnen net-, kwartierpiek- en fasegrenzen passen alsof '
                              'de laadpaal nog niet heeft gereageerd. Eén stap tegelijk en nieuwe rapportages '
                              'blijven vereist. Lange minimumlooptijden en beschermde programma’s worden niet '
                              'ingekort om vermogen sneller terug te nemen.',
                              'Een verse lage laadkracht heft een reserve alleen op met een expliciete '
                              'inactieve status, geen laadvraag of geen verbonden auto. Lage kracht alleen is '
                              'onvoldoende. Klein restoverschot kan volgens de bestaande voorkeur door een '
                              'lager toestel worden benut; veilige vrijgave kan later de autonome '
                              'zonne-autostart ondersteunen. Bestaande voorkeuren en wachttijden blijven '
                              'behouden.',
                              'Het laadprofiel leest expliciete grenzen en fasen uit betrouwbare bronnen of '
                              'gebruikt een bewust bevestigd terugvalprofiel. Huisaansluitstroom is geen '
                              'laadstroomlimiet. SolarPilot verandert die waarden niet. Het dashboard '
                              'onderscheidt sessie, ingestelde zonnemodus, werkelijk laden en wachtreden. '
                              'Lokaal bewaarde laadperiode-eindes krijgen alleen een native stopreden bij '
                              'aantoonbaar passende nieuwe rapportage; een meetgat of herstart is geen bewezen '
                              'stopoorzaak.'],
               'bullets': []},
              {'title': '8. Gewone flexibele toestellen en ontvochtiger',
               'paragraphs': ['Bestaande toestellen behouden hun adapter, deelname, centrale positie, meter, '
                              'minimumlooptijd, rusttijd, bescherming, dagdoel en bewuste nettoestemming. '
                              'Nieuwe identiteiten beginnen Uitgesloten. Een onbereikbaar toestel wordt '
                              'tijdelijk geïsoleerd en na bruikbaar bronherstel weer beoordeeld; deelname '
                              'wordt niet stil veranderd.',
                              'Actief betekent de werkelijk waargenomen aan-/actiefstatus, niet gegarandeerd '
                              'continu compressorbedrijf of uitsluitend zonnegebruik. Gemeten W, geraamd W en '
                              'onbekend blijven verschillende labels. Een ontbrekende noodzakelijke meting '
                              'geeft geen verzonnen nul. Een fout wordt gericht bij de betrokken functie '
                              'verklaard; alleen echte gedeelde onzekerheid mag andere starts beperken.',
                              'Handmatig starten/stoppen en een tijdelijke toestelboost gebruiken de bestaande '
                              'toestemming en bescherming. Het zijn geen noodstop of bypass van fabrikant- en '
                              'softwaregrenzen. Een looptijd mag tijdelijk netgebruik noodzakelijk maken. Een '
                              'pure planningswijziging bij een bevestigde binaire AAN-last geeft geen nieuwe '
                              'turn_on-opdracht.',
                              'Toestel- en batterijscripts worden vóór uitvoering op vaste onafhankelijke '
                              'doelapparaten gecontroleerd. Panasonic en het gereserveerde SG-contact mogen '
                              'niet indirect worden bediend. Ontbrekende of niet controleerbare scriptinhoud '
                              'en dynamische doelen blijven geblokkeerd. Dit bewijst geen fysieke veiligheid '
                              'van het script; geschikte terugmelding en de bestaande toestemming blijven '
                              'nodig.'],
               'bullets': []},
              {'title': '9. AEG-afwasmachine: één START per belading',
               'paragraphs': ['De bestaande AEG/Electrolux-adapter verstuurt alleen de gecontroleerde native '
                              'START-knop. Geen PAUSE, RESUME, STOPRESET, programmawijziging, native '
                              'afteltimer of stroomonderbreking via een stekker. Een gestarte, gepauzeerde of '
                              'nadrogende beurt blijft beschermd, ook bij wolken, Pauze of een manuele '
                              'autosessie.',
                              'In APP-modus maakt alleen een nieuwe fysieke overgang naar exact RemoteControl '
                              'Enabled één aanvraag. Enabled bij opstart, reconnect of migratie is geen nieuwe '
                              'belading; Not Safety Relevant Enabled is geen toestemming. Ready To Start, '
                              'gesloten deur, geldig programma, bruikbare verbinding en eventuele '
                              'alarmcontrole blijven vereist. ConnectivityState levert de heartbeat: '
                              'onveranderde geldige statische deur-/programma-/gereedwaarden vervallen niet '
                              'alleen doordat de tekst gelijk blijft. Unknown, Unavailable en restored blijven '
                              'beschermd.',
                              'Standaard geldt 13:00 als uiterste starttijd. Een aanvraag vóór de deadline '
                              'gebruikt dezelfde kalenderdag; op/na de deadline geldt de opgeslagen keuze, '
                              'standaard volgende dag. Een optionele maandagdeadline staat standaard leeg en '
                              'gebruikt dan ook maandag de gewone tijd. Alleen een bewust ingestelde '
                              'maandagwaarde wijzigt die dag. Tijdzone, geplande dag en toestemming worden in '
                              'het aanvraagticket bevroren en over herstart bewaard.',
                              'Een zonnestart vereist de ingestelde stabiele injectietijd, standaard 300 '
                              'seconden voor nieuwe profielen. Op de deadline kan alleen de zonnevoorwaarde '
                              'vervallen wanneer netaanvulling bewust is toegestaan. Actuele '
                              'net-/fase-/kwartierpiekruimte, globale modus en toestelvrijgave blijven nodig. '
                              'Een gemiste deadline geeft volgens de bestaande regels eenmaal een melding; de '
                              'standaard hersteltermijn van een nog niet verzonden start is 120 minuten, '
                              'daarna is een nieuwe APP-aanvraag nodig.',
                              'Het ticket wordt vóór START duurzaam als geprobeerd bewaard. Alleen een nieuwe '
                              'passende Running-rapportage bevestigt start. Een onzekere of mislukte START '
                              'wordt niet blind herhaald, ook niet na herstart. Handmatig starten verbruikt '
                              'dezelfde aanvraag. Een gewijzigde deur, programma, koppeling of ingetrokken '
                              'APP-vrijgave annuleert alleen de nog wachtende aanvraag.',
                              'End Of Cycle wordt eventgestuurd opgeslagen en blijft na Off, onbereikbaarheid '
                              'en herstart zichtbaar. AirDry/Ado Drying betekent nadrogen, geen einde of '
                              'nieuwe belading. Alleen Off of een onderbreking bewijst geen voltooiing; '
                              'onbekende starttijd wordt geen exacte duur. Een nieuw betrouwbaar Ready To '
                              'Start kan een achtergebleven oude cyclus als einde niet bevestigd afsluiten '
                              'zonder een oude aanvraag te herstellen.',
                              'Zonder exclusieve meter blijft de ingestelde nominale belasting een '
                              'conservatieve reserve en geen gemeten faseprofiel. Met bruikbare W/kW worden '
                              'volledige gedekte cycli geleerd. Een voorkeur-AEG en een vandaag veilig '
                              'startklaar ticket behouden hun startkans volgens de centrale lijst. SG gebruikt '
                              'uitsluitend overblijvende ruimte en neemt geen afwasvermogen af. Een al lopende '
                              'beurt is geen algemeen SG-veto wanneer na alle reserves genoeg echte ruimte '
                              'resteert.',
                              'Veilige overname van autonoom EV-zonnevermogen behoudt de bestaande '
                              'afzonderlijke AEG-route en opt-in. De hele belasting moet passen vóór '
                              'Wallbox-reactie. Een onzekere balans kan latere EV-gebaseerde starts blokkeren '
                              'en een controle vragen, maar breekt de lopende beurt nooit af. Gerichte oudere '
                              'profielherstelmigraties mogen alleen complete eenduidige koppelingen herstellen '
                              'en maken zelf geen APP-ticket of fysieke START.'],
               'bullets': []},
              {'title': '10. PV-model en Forecast.Solar',
               'paragraphs': ['Forecast.Solar levert de basisverwachting via bestaande Home Assistant-bronnen '
                              'en, waar ondersteund, de geladen coordinatorcurve. SolarPilot doet hiervoor '
                              'geen nieuwe cloudpolling. Expliciete bronkeuzes blijven staan; bij precies één '
                              'eenduidige installatie kan het register koppelingen vinden. Meerdere '
                              'installaties vragen een bewuste keuze. Ontbrekende of oude forecast maakt geen '
                              'virtueel huidig overschot.',
                              'Wattpiekvermogen van panelen en AC-omvormergrens blijven afzonderlijke '
                              'instelwaarden. De actuele productiekleur en clipping gebruiken de ingestelde '
                              'omvormergrens. SolarPilot wijzigt Forecast.Solar-instellingen niet. Geleerde '
                              'lokale correctie wordt begrensd; onbekende delen van een curve of een scalar na '
                              'haar lokale dag-/uurgrens worden niet automatisch nul of een nieuwe '
                              'voorspelling.',
                              'Kwartierkalibratie verzamelt maximaal één verse waarneming per minuut. Een '
                              'kwartier vereist minstens twaalf geldige waarnemingen, elf minuten spreiding en '
                              'voldoende dekking. De eerste tien minuten na start/reload, clipping, ongeldige '
                              'geschatte bronnen en sterk wisselende verhoudingen worden niet als structurele '
                              'schaduw geleerd. Geweigerde kwartieren blijven met reden inspecteerbaar.',
                              'Het lokale model gebruikt vergelijkbare dagen, zonnegeometrie waar bruikbaar en '
                              'seizoensgroepen, zonder vaste schaduwklok. Een empirische afwijking bewijst '
                              'niet welke fysieke oorzaak haar gaf. Bron-/profielwijzigingen maken alleen '
                              'onverenigbare PV-factoren opnieuw te leren; andere modellen worden niet gewist. '
                              'Oude historische kwartieren zonder gelijktijdige forecast zijn geen bewezen '
                              'live kalibratie.',
                              'PV-diagnose toont ruwe/gecorrigeerde/werkelijke W, dekking, fouten, geweigerde '
                              'kwartieren en leerdagen. Zij wordt afzonderlijk opgevraagd en gebruikt '
                              'bestaande lokale informatie. De bestaande grenzen van dertig dagen en 2880 '
                              'diagnosekwartieren blijven gelden. Voorspellingssensoren zijn geen '
                              'gecertificeerde energietellers; dagen bij zomer-/wintertijd worden op echte '
                              'tijdstempels berekend.'],
               'bullets': []},
              {'title': '11. Fasebewaking en fysieke grenzen',
               'paragraphs': ['L1, L2 en L3 blijven afzonderlijk bewaakt wanneer geconfigureerd en bewust '
                              'vrijgegeven. Netto-export over drie fasen bewijst niet dat iedere fase vrije '
                              'stroomruimte heeft. Een ontbrekende vereiste fasekoppeling geeft geen algemene '
                              'startvrijgave.',
                              'Faseherkenning leert alleen bruikbare voldoende geïsoleerde vermogenssprongen. '
                              'Gelijktijdige veranderingen worden verworpen. Herkend toestelvermogen en netto '
                              'restcomponent staan apart; die rest is geen zuiver onbekend verbruik omdat PV '
                              'en andere stromen meespelen. Herkenning blijft adviserend tot bewuste '
                              'activering. Beveiligingen, tekenrichting en betrouwbare actuele bronnen blijven '
                              'noodzakelijk.'],
               'bullets': []},
              {'title': '12. Thuisbatterij',
               'paragraphs': ['Zonder gekoppelde hardware blijft de batterij-what-if adviserend. Fysieke '
                              'batterijbediening vereist globale en individuele toestemming plus bevestigd '
                              'exclusief eigenaarschap. Netladen en exportontladen staan standaard Uit. De '
                              'eigen batterijcommandobescherming blijft bestaan en wordt niet door '
                              'verwijdering van oude warmtepompsturing gereset.',
                              'Commandointentie wordt vóór actuatie duurzaam bewaard. Koppeling, native '
                              'doel/eenheid/grenzen, toestemming en Wallboxbescherming worden direct voor '
                              'verzending opnieuw getoetst. Een passende nieuwe vermogensrapportage van na de '
                              'opdracht, en bij numerieke bediening ook een passend native doel, zijn nodig. '
                              'Een oude al passende powerwaarde is geen nieuwe bevestiging; onzekere '
                              'opdrachten worden niet blind herhaald.',
                              'Een pending batterijopdracht beschermt nieuwe starts en vermogensoverdracht '
                              'tegen hergebruik van oude ruimte. Bestaande beschermde cycli blijven doorlopen. '
                              'Na de actie zijn nieuwe P1 en normale wachttijden nodig. Voor verwijderen moet '
                              'werkelijke neutrale power, en bij numerieke bediening een exact neutraal doel, '
                              'betrouwbaar vaststaan. Handmatige doelen worden niet overschreven.',
                              'Batterijflow telt eenmaal mee; read-only of foutieve profielen behouden hun '
                              'echte stroom zonder nieuw bedieningsrecht. SoC vraagt bruikbare procentdata '
                              'binnen 0–100. Numerieke doelen moeten nul exact kunnen weergeven binnen '
                              'bereik/stap. Scripts vragen controle van inhoud en terugmelding; een naam '
                              'alleen bewijst geen veilige functie.',
                              'De what-if gebruikt standaard 80% round-trip efficiëntie, dus 20% totaalverlies '
                              'over laden en later terugleveren. Dit blijft instelbaar en is geen aankoop- of '
                              'besparingsgarantie. Bij meerdere batterijen gelden de bestaande '
                              'verdeelstrategie en individuele grenzen.'],
               'bullets': []},
              {'title': '13. Kwartierpiek, kosten en waardeschatting',
               'paragraphs': ['Kwartiergemiddelde en maandpiek kunnen het ingestelde softwarematige '
                              'importbudget beperken. Dat budget vervangt geen zekeringen of echte '
                              'aansluiting. Dag-KPI’s zijn indicatieve toerekening en geen veiligheidsbron.',
                              'Elektriciteitskost vandaag telt geldige gemeten netafnamekost min '
                              'injectievergoeding op. Direct gebruikte PV verlaagt de netafname al en wordt '
                              'niet nogmaals afgetrokken. Prijzen horen bij hun werkelijke meetinterval; een '
                              'later tarief verandert eerdere energie niet. Meetgaten blijven zichtbaar. De '
                              'planningskost is een aparte toekomstschatting, geen dagkost.',
                              'Bij ontbrekende of ongeldige dynamische prijzen geldt het ingestelde vaste '
                              'tarief. Een geldige nulprijs blijft nul, ontbrekende rijen verschuiven andere '
                              'tijdposities niet. Negatieve prijzen en netto negatieve dagkosten blijven '
                              'mogelijk. Bedragen bevatten geen vaste kosten, aanschaf, onderhoud of '
                              'gegarandeerd capaciteitstarief.',
                              'Het geschatte voordeel van automatische sturing is een aparte voorwaartse '
                              'telling met maximaal negentig kalenderdagen. Alleen werkelijk actieve eigen '
                              'automatische gewone lasten tellen. Native Wallbox-, warmtepomp- en handmatig '
                              'gebruik geven geen verzonnen SG-besparing of vaste COP. Dit voordeel wordt niet '
                              'nogmaals van de dagkost afgetrokken.'],
               'bullets': []},
              {'title': '14. Meetkwaliteit en modelgegevens',
               'paragraphs': ['SolarPilot leert lokaal, zonder externe AI-dienst of het herschrijven van '
                              'zijn code. Bruikbaar gemeten verbruik, basislast, PV-/weercorrectie, '
                              'faseclassificatie en complete apparaatcycli kunnen analyse/planning '
                              'verbeteren. Prioriteiten, deadlines, net-/fasegrenzen en fysieke toestemming '
                              'veranderen niet autonoom door leren.',
                              'Oude woning-/tankmodellen en hun bewijs blijven bewaard voor privé-analyse '
                              'en rollback. Zij verlenen in deze versie geen ruimte- of tankopdrachtrecht. '
                              'Er is geen modelreset of nieuw actief klimaatleerregelpad. Bewaarde '
                              'modelkwaliteit is geen kans dat een fysieke actie juist is.',
                              'Grote model- en leerattributen blijven live en in eigen '
                              'SolarPilot-opslag/export beschikbaar. Alleen herhaalde zware kopieën in de '
                              'gewone Home Assistant Recorderhistoriek zijn uitgesloten. Ook de nieuwe '
                              'veranderlijke waarnemingstijden van de warmtepompweergave worden alleen uit '
                              'die herhaalde attributenkopie uitgesloten. Een onveranderde rusttoestand '
                              'maakt daardoor geen nieuw detailrecord bij iedere vijfsecondenronde. Actuele '
                              'sensorwaarden, live attributen, eigen metingen en export blijven behouden. '
                              'De 16 KiB-grens betreft één attribuutpakket, niet vrije schijfruimte. '
                              'Gedeelde weergavecache vermindert rekenwerk tijdens één publicatieronde; '
                              'beslissingen en export gebruiken verse directe gegevens.',
                              'Meetkwaliteit toont meetdekking, modelbasis en afwijkingen als waarnemingen, '
                              'zonder leervragen of knoppen die je tussendoor bron-/aanpassingsbeleid laten '
                              'kiezen. Als analyse nodig is, verzamelt één exportactie de beschikbare zeven '
                              'dagen en de open bevindingen. Download het bestand, laat het hier analyseren '
                              'en upload desgewenst het JSON-antwoordrapport terug. Alleen antwoorden die '
                              'exact bij de geëxporteerde én nog actuele bevindingidentiteit/revisie passen '
                              'kunnen haar reviewstatus verwerken. Beoordeelde bevindingen worden '
                              'afgehandeld; meer data nodig blijft open. Een antwoord wijzigt geen '
                              'sampling-/aanpassingsbeleid, modeltoestemming, instelling, code of '
                              'apparaatbediening. De bestaande leer-/aanpassingsregels blijven gelden. '
                              'Gemeten verbruik kan volgens de ingestelde bronkeuze worden gebruikt; '
                              'geschatte, dubbele of ongeschikte bronnen zijn geen echte meting. Een '
                              'recente basislastaanpassing wordt eerst vergeleken en alleen binnen de '
                              'bestaande begrensde toestemming toegepast. Optionele HA-analysemeldingen '
                              'verwijzen naar Export en blijven afzonderlijk van echte controlefouten.'],
               'bullets': []},
              {'title': '15. Overzicht, uitleg en meldingen',
               'paragraphs': ['Overzicht toont Wat gebeurt er en waarom? met per toestel de actuele '
                              'toestand, één leidende reden, bekende W en uitklapbare voorwaarden. Gemeten, '
                              'geschat, native gemeld en afgeleid blijven herkenbaar. De warmtepomp toont '
                              'dezelfde backendtaak, metingen en SG-beslisreden, geen tweede '
                              'frontendregelaar. Taak van de warmtepomp en Elektrische bijverwarming blijven '
                              'afzonderlijk leesbaar. Een verse native taakmelding is iets anders dan '
                              'elektrische activiteit of een gekozen stand. Zonder bruikbaar taakbewijs '
                              'verschijnt Geen actuele taakmelding; brononzekerheid blijft in Details en '
                              'export beschikbaar. Open details, formulieren, popup en scroll blijven bij '
                              'verversen op vaste ids bewaard.',
                              'Doorlopend blauw en een bewegend warmtepompsymbool kunnen actuele elektrische '
                              'activiteit weergeven. De ventilatoranimatie volgt de verse actieve '
                              'hoofdmeting en is geen afzonderlijk bewijs van compressorbeweging. Bij alleen '
                              'actieve elektrische ondersteuning beweegt het verwarmingssymbool en blijft de '
                              'ventilator stil. Andere toestellen krijgen hun activiteitssymbool volgens de '
                              'eigen betrouwbare actieve status. Verminderde beweging onderdrukt animaties. '
                              'Een aangevraagde of beschikbare functie blijft onderscheiden van waargenomen '
                              'activiteit. Een gesloten SG-contact bewijst geen fysieke tankopwarming. '
                              'Productie en net hebben afzonderlijke groen-roodkleuren; onbekende/oude '
                              'bronnen blijven grijs. Kleuren en beweging zijn presentatie, geen storing of '
                              'vrijgave.',
                              'Resterende fouten waarvoor jouw controle nodig is verschijnen in Home '
                              'Assistant → Meldingen → SolarPilot: controle nodig. De melding bundelt '
                              'gerichte oorzaken en acties, wordt bij inhoudelijke verandering bijgewerkt en '
                              'verdwijnt na herstel. Meldingtransport mag de regeling niet laten crashen. '
                              'Gewone bronwacht, rusttijd, een bewuste Pauze of fabrikantsterilisatie '
                              'veroorzaken geen nieuwe foutspam.',
                              'Een SG-koppelings- of terugvalprobleem blokkeert de betrokken SG-functie en '
                              'noemt de ingebruiknamecontrole. Een oude gearchiveerde '
                              'tank-/klimaatopdrachtfout wordt niet als actuele fysieke storing opgelost '
                              'verklaard. Echte onbekende fouten, toestel-/batterijfouten, expliciete '
                              'gebruikerskeuzes en verwijderverzoeken blijven beschermd. Controle afronden '
                              'repareert geen verkeerde bronconfiguratie of onbereikbaar apparaat.'],
               'bullets': []},
              {'title': '16. Apparaatgeschiedenis',
               'paragraphs': ['Geschiedenis toont per toestel gekozen lokale dag, draaitijd, sessies en '
                              'afzonderlijke start-/stopredenen. Een verzonden opdracht alleen is geen '
                              'bevestigde start. Externe wijzigingen krijgen geen verzonnen gebruiker of '
                              'automatisering als oorzaak. Een slimme stekker toont haar aan-tijd, niet '
                              'noodzakelijk continu compressorbedrijf.',
                              'Herstart, reload, onbereikbaarheid en meetgaten begrenzen de waarneming en '
                              'tellen onbekende tijd niet mee. Sessies over middernacht worden per lokale '
                              'kalenderdag verdeeld; die dag kan 23 of 25 uur duren. Oude niet-geregistreerde '
                              'redenen worden niet achteraf gereconstrueerd.',
                              'De bestaande eigen historie blijft bij updates staan: maximaal dertig '
                              'kalenderdagen per gewone verbruiker, 2000 sessies en 300 extra gebeurtenissen. '
                              'Bij volle detailgrens blijven dagtotalen met onvolledigheidslabel bestaan. '
                              'Opslag is gebundeld; het laatste nog niet opgeslagen stukje kan bij een abrupte '
                              'uitval ontbreken. Details worden alleen op aanvraag gelezen en bedienen niets.'],
               'bullets': []},
              {'title': '17. Privé-analyse-export',
               'paragraphs': ['Export → Maak analysebestand levert voor een HA-beheerder met één klik een lokaal '
                              'gecomprimeerd JSON.GZ-bestand van de beschikbare zeven dagen. De oorspronkelijke '
                              'exportroute blijft ook perioden van 1 uur of 24 uur ondersteunen. Het bevat '
                              'actuele bron-/configuratiegegevens, beslisredenen, versie per nieuwe '
                              'registratie, beschikbare historie en modellen. Oude records zonder versie '
                              'blijven onbekend. Het pakket bevat een gerichte analysis_request voor '
                              'warmtepompinstellingen, SolarPilot-keuzes en logische verbetervoorstellen, '
                              'plus bronherkomst en het adviesrapportformaat. Het bijbehorende '
                              'Adviesrapport-sjabloon downloaden is daarna apart beschikbaar; dat sjabloon '
                              'bevat de exacte bronhash. Het bestand verandert geen '
                              'toestel, wordt niet automatisch geüpload en is geen herstelbare HA-back-up.',
                              'Bronnamen en labels worden standaard consistent gepseudonimiseerd. Een '
                              'expliciete keuze kan echte namen opnemen. Tokens, wachtwoorden, '
                              'netwerk-/account-/locatiegegevens en ongeschikte privébronnen worden '
                              'gefilterd. Tijdstippen en gebruikspatronen blijven aanwezig: controleer vóór '
                              'delen en plaats geen analysebestand op publieke GitHub.',
                              'De beheerder-WebSocket geeft alleen downloadinformatie; het bestand wordt '
                              'buiten de eventloop gecomprimeerd en daarna via geauthenticeerde lokale HTTP '
                              'gedownload. De download is tien minuten geldig en wordt na ontvangst/afloop '
                              'opgeruimd. Maximaal twee bestanden staan tegelijk klaar of worden gemaakt. '
                              'De route beperkt de uitgepakte JSON niet tot 16 MB en verkort de gevraagde '
                              'periode niet om die grens te omzeilen.',
                              'Alleen werkelijk bewaarde informatie is beschikbaar. De '
                              'onderzoeksregistratie behoudt haar bestaande maximaal zeven dagen, 2016 '
                              'gedetailleerde ronden, 20000 bronwijzigingen en 6000 gebeurtenissen. De '
                              'laatste maximaal twee uur snelle punten blijven in RAM. Een korter '
                              'registratie-interval kan door vaste aantallimieten een kortere ruwe periode '
                              'geven. Geen onbeperkt archief, retentieverruiming of aanvulling van '
                              'ontbrekende oude meetpunten.',
                              'De warmtepompanalyse bundelt beschikbare voedingshistorie, native taken en '
                              'gekozen context, ontdooimeldingen, SG-aanvraag/contact/beslisredenen, '
                              'bronkwaliteit, instellingenwijzigingen en Aquarea-versie. De bestaande '
                              'koppelingen worden automatisch gebruikt; hiervoor is geen extra entiteit of '
                              'formulier nodig. De meetregistratie gebruikt standaard zeven dagen met '
                              'vijfminutenmeetpunten; bestaande instellingen en aantallimieten blijven gelden. '
                              'Een meetpunt is geen volledige registratie van iedere '
                              'korte piek of heater-/compressorwisseling. Meetgaten, gedeeltelijke dekking, '
                              'bronversheid en de voedingsprofielaanname blijven expliciet; meterwatts '
                              'bewijzen geen type backupheater/booster, warmteproductie of causaal '
                              'SG-effect.',
                              'Bij Analyse nodig maakt één actie een export van de beschikbare zeven dagen '
                              'met open bevindingen, zonder extra vragen of nieuwe configuratie. Download '
                              'het JSON.GZ-bestand en voeg het hier bewust toe voor analyse. De meegeleverde '
                              'analysevraag betreft tips voor de native warmtepompinstellingen, SolarPilot-keuzes en concrete '
                              'logische codeverbeteringen, met bewijs en beperkingen. Een analyse kan een '
                              'JSON-antwoord-/adviezenrapport volgens het meegeleverde template teruggeven. '
                              'Onder Export kun je dat rapport optioneel uploaden en de bevindingen/tips '
                              'bekijken. De upload is uitsluitend een lokaal read-only rapport; zij wijzigt '
                              'geen configuratie, programmabestand of apparaat en doet geen servicecall. '
                              'Exact gekoppelde actuele antwoorden verwerken alleen de reviewstatus van '
                              'bevindingen. Meer data nodig blijft open. Gewenste instellingenwijzigingen '
                              'blijven een afzonderlijke bewuste configuratieactie met hun bestaande '
                              'voorwaarden. Een codeverbetering vereist een afzonderlijke geteste release.',
                              'Alleen een HA-beheerder kan een adviesrapport uploaden, bekijken of '
                              'verwijderen. Upload ondersteunt UTF-8 JSON van maximaal 1 MiB met maximaal '
                              'honderd adviezen en honderd bevindingantwoorden; dubbele of onbekende velden en ongeschikte schema-inhoud '
                              'worden geweigerd. Adviezen benoemen categorie, bewijs, vertrouwen en '
                              'beperkingen. Bronbinding vergelijkt exportidentiteit, SHA-256, versie en '
                              'aanmaakdatum met maximaal vijftig recent bewaarde succesvolle '
                              'exportidentiteiten. Een exacte match wordt als gekoppelde bron getoond; een '
                              'niet gekoppeld rapport blijft ongeverifieerd en krijgt geen inhoudelijk '
                              'vertrouwen of toepasrecht. Alleen het laatste rapport per integratie-entry '
                              'wordt lokaal bewaard. Het rapport verwijderen wist geen oorspronkelijke '
                              'metingen, exporthistorie of instellingen. Een bronmatch bewijst herkomst, '
                              'niet dat ieder advies inhoudelijk correct of geschikt is. Antwoorden op open '
                              'bevindingen vereisen de bijbehorende zevendagenexport en worden uitsluitend '
                              'verwerkt wanneer de geëxporteerde en huidige '
                              'identiteit/revisie exact overeenkomen. Een oud, niet gekoppeld of inmiddels '
                              'gewijzigd vraagpunt wordt niet als actueel afgehandeld. Reviewstatus is geen '
                              'toestemming voor automatisch instellen, leren, code of bediening.',
                              'Een logische verbetersuggestie kan een stabiele proposal_id bevatten. De '
                              'status van die suggestie wordt uitsluitend berekend uit het vertrouwde '
                              'meegeleverde implementatieregister en de werkelijk geïnstalleerde '
                              'SolarPilot-versie. Uitgevoerd vereist exact dezelfde voorstelidentiteit én '
                              'inhoud in het register, plus een geïnstalleerde versie vanaf de geteste '
                              'introductierelease. Een gewijzigde tekst of oudere/onherkende versie blijft '
                              'open; een onbekende identiteit blijft ongekoppeld. Een upload kan zichzelf '
                              'niet als uitgevoerd verklaren. '
                              'Het rapport en zijn oorspronkelijke bronversie blijven bij een gewone '
                              'update bewaard; de huidige versie wordt apart getoond. Een volgende analyse '
                              'neemt beschikbare nog open logische voorstellen mee met dezelfde proposal_id '
                              'en ongewijzigde abstracte voorsteltekst. Privébronnen, tijdstippen en '
                              'ondersteunende details horen afzonderlijk in evidence, zodat nieuwe '
                              'pseudoniemen de betekenis van het voorstel niet veranderen. Het uploaden van een '
                              'antwoord werkt de integratie niet bij: een codeverbetering komt alleen via '
                              'een afzonderlijk geverifieerde release en de normale HACS-/herstartprocedure. '
                              'Dit maakt geen automatische codeactie buiten een actieve werksessie.'],
               'bullets': []},
              {'title': '18. Live configuratie en één eigenaar',
               'paragraphs': ['Configureren opent de bestaande HA-optiesflow met uitleg bij de velden. Alleen '
                              'expliciet opslaan kan een instelling veranderen; openen/renderen bedient niets. '
                              'Gewone ongewijzigde toestellen behouden timers, listeners, leerdata en modus. '
                              'Een HACS-codeupdate vereist nog wel een HA-herstart.',
                              'Koppeling-/meter-/beschermingswijzigingen aan actief of onzeker beheerde '
                              'toestellen blijven onder de bestaande veilige voorstelroute staan. Naam en '
                              'categorie kunnen zonder fysieke wijziging. Toestel vervangen geeft een nieuwe '
                              'identiteit met voorkeuren als voorstel, geen oude fysieke rechten of '
                              'startticket. Conflicterende edits en dubbele actuatoren/meters worden '
                              'afgewezen.',
                              'De gekozen SG-uitgang mag niet tegelijk een gewone flexibele last of '
                              'batterijactuator zijn. Backendvalidatie voorkomt dubbel eigenaarschap. Een '
                              'gewijzigde SG-koppeling vereist opnieuw ingebruikname en kan geen oude '
                              'AAN-bevestiging overnemen. Wijzigen van toepassingsbereik of '
                              'splitmeterkoppelingen vraagt de passende nieuwe lokale bevestiging; een vinkje '
                              'wordt niet stil overgenomen. Controleer externe automatiseringen die dezelfde '
                              'uitgang of native Panasonic-instellingen nog schrijven; SolarPilot bewijst hun '
                              'afwezigheid niet zonder live inzage. Een gewijzigde native uitleesbron is geen '
                              'nieuwe warmte-/koelvraag: de eerste verse rapportage vormt alleen een nieuwe '
                              'referentie, waarna echt veranderde context of een nieuwe zonneperiode nodig '
                              'blijft. Wijzigen van relevante native bronnen vraagt ook opnieuw de passende '
                              'koelbeveiligingsbevestiging.',
                              'Bij een wachtend APP-ticket kiest wijzigen van deadline/nettoestemming tussen '
                              'volgende beladingen of expliciet hetzelfde huidige ticket. De bestaande '
                              'kalenderdag blijft gelijk; er ontstaat geen START door opslaan. Wachtende '
                              'voorstellen en archieven blijven inspecteerbaar. Alleen eigen virtuele '
                              'SolarPilot-entiteiten mogen bij wijzigingen verdwijnen, nooit de '
                              'oorspronkelijke apparaatentiteiten.'],
               'bullets': []},
              {'title': '19. Migratie en veilige ingebruikname',
               'paragraphs': ['Beta.67 behoudt de beta.63-fix voor onveranderbare en geneste Home '
                              'Assistant-opties. Verwijder de integratie, configuratie, modellen of opslag '
                              'niet. De upgrade houdt geldige single-meterkoppelingen, bestaande overige '
                              'toestellen en privégegevens intact. Ongewijzigde geldige SG-, profiel-, '
                              'meter- en koelbeveiligingsbevestigingen uit beta.66 blijven staan; een '
                              'codeupdate vraagt daarvoor geen herbevestiging. Nieuwe profiel-, splitmeter-, '
                              'compressor- en SG-bronvelden leveren geen stilzwijgende toestemming. De '
                              'algemene SG-keuze vraagt expliciete lokale bevestiging.',
                              'Een oude tankgebonden beleidswachtstand wordt bij bevestigde omschakeling '
                              'naar het algemene profiel gericht beoordeeld. De oude herkomst blijft privé '
                              'bewaard en nieuw betrouwbaar relevant native bewijs of een aantoonbaar nieuwe '
                              'zonneperiode is nodig; omschakelen alleen start niets. De overgang doet geen '
                              'fysieke opdracht. Echte handmatige overname, transportonzekerheid en '
                              'veiligheidsblokkeringen worden hierdoor niet gewist.',
                              'Voor upgrade maak je een volledige privé Home Assistant-back-up inclusief '
                              'configuratie en SolarPilot-opslag. De versiegebonden migratie archiveert oude '
                              'warmtepompopties, modellen en relevante opdracht-/foutgegevens buiten de '
                              'actieve regeling. Zij is idempotent en verstuurt geen tank-/klimaatopdracht, '
                              'SG-boost of afwasstart.',
                              'Oude pending, doel-eigendom, hercontrole, foutwachttijden, manual hold en '
                              'eigen klimaat-OFF kunnen niet opnieuw uitvoeren. Aantoonbaar uitsluitend '
                              'vervallen regelopdrachtfouten worden als vervallen functie beoordeeld, niet '
                              'als fysiek gerepareerd. Gemengde/onbekende foutpauzes, gewone '
                              'apparaat-/batterijfouten, gebruikers-Pauze en verwijdering blijven beschermd. '
                              'Brononzekerheid voor de nieuwe SG-functie blijft gelden.',
                              'De globale hervatvoorkeur, geldige andere toestellen, entity-identiteiten, '
                              'opgeslagen prioriteiten, APP-tickets, historie en leerdata blijven behouden. '
                              'Nieuwe SG-sturing blijft uit totdat juiste uitgang, native basisinstellingen, '
                              'geen dubbele writers, contactmapping en lokale aflooptimer werkelijk zijn '
                              'bevestigd. De noodzakelijke lokale Panasonic/Shelly-controle is geen '
                              'softwaretest.',
                              'Controleer eenmalig op Panasonic de gewenste normale '
                              'tank-/zone-/programma-instellingen, inclusief zelfstandig comfort en '
                              'sterilisatie. Eerdere directe sturing kan iets hebben achtergelaten; deze '
                              'nieuwe runtime schrijft dat niet terug. De fysieke SG-ingebruiknameproef '
                              'gebeurt alleen met expliciete toestemming en zonder elektrische metingen in '
                              'geopende apparatuur. Gebruik de korte controle in BETA67_INSTELLEN.md.'],
               'bullets': []},
              {'title': '20. Installatie, verwijderen en rollback',
               'paragraphs': ['Installeer of update de Integration via HACS en herstart Home Assistant. De '
                              'frontend wordt meegeleverd en automatisch geregistreerd: geen aparte '
                              'Lovelace-resource, dashboard-YAML of www-kopie. Heropen de webpagina/app en '
                              'controleer geladen backend- en kaartversie afzonderlijk: beide staan '
                              'zichtbaar onder Instellingen & controle. Een oude kaart kon alleen de nieuwe '
                              'backendversie tonen terwijl zij zelf nog oude weergavecode gebruikte. Het '
                              'zijbalkpaneel gebruikt nu de releasekaart. Bij een verschil in versies geeft '
                              'de kaart herlaadadvies. Herlaad de pagina volledig of sluit de app volledig '
                              'af en open haar opnieuw, ook voor een bestaande Lovelace-kaart. Een oude '
                              'kaart kan de nieuwe versieverschilwaarschuwing zelf nog niet tonen. Alleen '
                              'naar een ander tabblad gaan of de integratie herladen vervangt niet zeker de '
                              'al geladen browsercode. Een download bewijst geen geladen browsercode.',
                              'Een privéprofiel blijft optioneel en uitsluitend lokaal. Importeren kan lege '
                              'geldige bronkoppelingen aanvullen, maar activeert de SG-functie of nieuwe '
                              'fysieke apparaatbediening niet. Bewaar userfiles en eigen HA-opslag; voeg ze '
                              'niet aan publieke bron of pakket toe.',
                              'Voor verwijderen kies je Verwijderen voorbereiden en wacht je op de gerichte '
                              'veilige vrijgave. Een onzekere SG-uitgang blijft eerlijk onbekend; de '
                              'gecontroleerde lokale terugval begrenst de eigen aanvraag. Verwijderen van '
                              'SolarPilot verwijdert geen oorspronkelijke meter-, warmtepomp-, Wallbox-, '
                              'AEG- of Shelly-integratie.',
                              'Rollback naar de gecontroleerde beta.66-basis vereist de bij de upgrade '
                              'behorende privé HA-back-up naast de code, zodat instellingen, opgeslagen '
                              'bewijslagen en modellen samen passend terugkeren. Geef eerst de SG-aanvraag '
                              'vrij en controleer lokale terugval; laat nooit twee runtimes tegelijk werken. '
                              'Voor terugkeer naar de oude directe beta.61-regeling blijft de volledige '
                              'back-up van vóór de beta.62-migratie nodig. Alleen een oudere ZIP herstelt '
                              'gewijzigde opslag niet. Zie BETA67_INSTELLEN.md.'],
               'bullets': []},
              {'title': '21. Release- en documentatieregel',
               'paragraphs': ['Dit is de enige volledige actuele regelbeschrijving. current_guide.py genereert '
                              'dezelfde Markdown-mirrors en HA-uitleg. Optiehulp, versie, changelog, '
                              'OVERDRACHT.md, installatie, rollback en testverslag horen bij dezelfde '
                              'bronrelease. Historische releasebestanden beschrijven oudere versies en zijn '
                              'geen actuele bediening.',
                              'Softwaretests en geverifieerde publicatiepakketten bewijzen geen live '
                              'HA-installatie, echt Shelly-timergedrag of fysieke Panasonic-reactie. Die '
                              'bewijssoorten worden apart gerapporteerd. Publieke voorbeelden zijn fictief; '
                              'persoonlijke installatiegegevens, ruwe exports en geheimen blijven lokaal.'],
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
