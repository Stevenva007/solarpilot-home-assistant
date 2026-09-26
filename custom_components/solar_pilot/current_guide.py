"""Single source of truth for SolarPilot's user-facing current explanation.

Update this structure whenever behaviour changes. docs/ACTUELE_WERKING.md is generated
from this file. Home Assistant exposes the same content via a diagnostic sensor and
the SolarPilot dashboard card.
"""
from __future__ import annotations

import hashlib
import json

GUIDE_VERSION = "1.0.0-beta.21"
GUIDE_UPDATED = "2026-09-27"

CURRENT_GUIDE = {
    "title": "SolarPilot · Actuele werking",
    "version": GUIDE_VERSION,
    "updated": GUIDE_UPDATED,
    "intro": (
        "Dit is de enige actuele gebruikersuitleg voor deze release. Bij elke wijziging wordt deze tekst samen met "
        "de code vernieuwd. Deze HACS-release bevat bewust één actuele regelset. Configuratie en leerdata blijven lokaal in Home Assistant en worden bij gewone HACS-updates niet vervangen door programmabestanden."
    ),
    "sections": [
        {
            "title": "1. Basisprincipe en modi",
            "paragraphs": [
                "SolarPilot is een lokaal Home Assistant-EMS. De actuele P1- en PV-metingen, apparaatvoorwaarden en beveiligingen zijn altijd belangrijker dan voorspellingen of aangeleerde patronen.",
                "Observatie berekent en leert maar stuurt geen gewone flexibele verbruikers. Zonnestroom voert de toegestane regeling uit. Pauze start niets nieuws en bouwt eigen onderbreekbare lasten veilig af, met behoud van minimumlooptijden en beschermde cycli.",
                "Er wordt maximaal één gewone fysieke wijziging tegelijk uitgevoerd en daarna op terugmelding en nieuwe meetinformatie gewacht. Nieuwe apparaten staan standaard Uitgesloten totdat ze bewust op Auto worden gezet."
            ],
            "bullets": [
                "Eén actuator heeft maar één eigenaar.",
                "Een EMS-berekening is geen elektrische beveiliging.",
                "Onzekere opdrachten worden niet eindeloos herhaald.",
                "Na een herstart begint SolarPilot conservatief en reconcilieert het de echte toesteltoestand."
            ]
        },
        {
            "title": "2. Overschot, prioriteiten en planner",
            "paragraphs": [
                "De netmeter bepaalt echte import of injectie. SolarPilot houdt tegelijk rekening met de lasten die het zelf beheert, zodat een succesvolle inschakeling niet meteen als verdwenen zonne-energie wordt geïnterpreteerd.",
                "Toestellen op Auto worden volgens hun prioriteit gepland. Een hooggeprioriteerd toestel dat niet past mag een kleiner lager toestel niet automatisch blokkeren. Minimum aan/uit-tijden, start- en stopvertragingen, tijdvensters, dagminima en beschermde programma's blijven gelden.",
                "De Unified Planner rekent standaard iedere 15 minuten een rolling horizon van 36 uur opnieuw door in blokken van 15 minuten. Hij plant alleen flexibele, expliciet vrijgegeven lasten en combineert lokaal gecorrigeerde PV, geleerd basisverbruik, prijzen, kwartierpiek en toekomstige batterijruimte in één plan. Alleen het huidige blok mag invloed krijgen op de realtime regelaar; bij nieuwe meetinformatie wordt het plan opnieuw berekend.",
                "Per toestel kan naast minimumlooptijd een dagdoel in kWh worden ingesteld. Als een exclusieve vermogensmeter aanwezig is, integreert SolarPilot het werkelijk gemeten toestelvermogen tot dagenergie; zonder meter gebruikt het een verklaarbare vermogensschatting. De planner probeert alleen de nog ontbrekende energie binnen tijdvenster en deadline in de gunstigste blokken te plaatsen. Een lopende last wordt niet gestopt omdat een nieuw plan anders uitkomt. Actuele P1/PV, minimumlooptijden, comfort, sterilisatie en toestelbeveiligingen blijven altijd belangrijker dan het plan.",
                "Voor beschermde niet-onderbreekbare cycli kan SolarPilot energie, duur en piekvermogen per programma lokaal bijleren wanneer een exclusieve vermogensmeter beschikbaar is. De planner plant zo'n cyclus als één aaneengesloten blok in plaats van losse kwartieren. Tot er voldoende complete cycli geleerd zijn, kan een expliciete fallback in kWh en minuten worden ingesteld. Zonder betrouwbaar duurprofiel wordt geen optimistische duur uit piekvermogen gegokt. De realtime regelaar controleert bij de echte start nog altijd actuele vermogensruimte en laat een gestarte beschermde cyclus afwerken. Zodra zo'n cyclus loopt, reserveert de planner het geschatte resterende cyclusverbruik in de horizon zodat andere flexlasten niet op reeds toegezegd vermogen worden gepland."
            ],
            "bullets": [
                "Goedkope netfallback is dubbele opt-in en standaard UIT. Dynamische prijzen worden alleen gebruikt wanneer een bruikbare prijsreeks beschikbaar is. Tijdgestempelde reeksen worden op het echte planmoment uitgelijnd; gangbare today/tomorrow-profielen worden op het lokale uur of kwartier gelegd. Bij ontbrekende of ongeldige gegevens geldt de vaste prijsfallback.",
                "Capaciteitstarief- en fasegrenzen blijven van toepassing als netstroom wordt toegestaan.",
                "Aangeleerd toestelvermogen mag de planningsschatting alleen conservatiever, dus hoger, maken.",
                "Het basislastmodel leert alleen uit schone perioden zonder duidelijke Wallbox- of eigen flexlastvervuiling; de historische bootstrap versnelt de eerste weken maar wordt niet als zekerheid behandeld.",
                "Een toekomstige batterij wordt in de planner eerst adviserend meegetekend; de aparte realtime batterijguard blijft eigenaar van fysieke batterijsetpoints.",
                "Plannerkwaliteit wordt achteraf gemeten op voorspelde versus werkelijke PV, basislast en netresultaat, plus de mate waarin geplande run/stop-toestanden werkelijk konden worden uitgevoerd. SolarPilot bewaart hiervan compacte dagaggregaten en toont 7- en 30-dagenfouten; de kwaliteitsscore is een technische indicator en geen waarschijnlijkheid.",
                "Een begrensde 15-minutenreplay bewaart recente gemeten PV, basislast, prijzen en netresultaat. Daarmee vergelijkt de Planning-tab enkele alternatieve plannerstrategieën op dezelfde meetdata. Dit is een plannerreplay en geen exacte fysieke simulatie van elk historisch apparaat; verschillen worden daarom alleen als richtinggevend advies getoond.",
                "Voor grotere plannerwijzigingen bevat het pakket daarnaast een offline historische vergelijking die dezelfde Unified Planner met de huidige en een voorgestelde instelling op dezelfde meetachtergrond kan draaien. Ook die backtest is richtinggevend: historische startklaarheid, aanwezigheid en thermische toestand zijn niet volledig reconstrueerbaar."
            ]
        },
        {
            "title": "3. Wallbox Pulsar Max",
            "paragraphs": [
                "De Wallbox blijft volledig autonoom Full Solar regelen. SolarPilot leest laadvermogen, status en zonnemodus, maar schrijft geen laadstroom, zonnemodus, pauze, resume of start/stop naar de laadpaal.",
                "Andere toestellen voorrang staat standaard AAN. Geschikte SolarPilot-lasten mogen dan zonnevermogen gebruiken; de Wallbox ziet minder overschot en regelt zichzelf terug. Alleen een snel reagerende, onderbreekbare last met eigen actuele vermogensmeting mag bewust voor gecontroleerde Wallbox-overname worden vrijgegeven.",
                "Wallbox-laadvermogen wordt nooit zomaar bij echte injectie opgeteld. Voor de 60 °C-boilerregel telt uitsluitend werkelijk gemeten injectie."
            ],
            "bullets": [
                "Wallbox blijft read-only vanuit SolarPilot.",
                "Tijdelijke netafname tijdens Wallbox-terugregeling kan niet volledig worden uitgesloten.",
                "Dezelfde Wallbox mag niet ook als generiek bestuurbaar SolarPilot-toestel worden toegevoegd."
            ]
        },
        {
            "title": "4. Panasonic warm water",
            "paragraphs": [
                "Voor de Panasonic Aquarea WH-SXC12K9E8 / WH-UXZ12KE8 is het gewenste praktische minimum 43 °C. Omdat de fysieke tankdifferentie −5 °C is en standaard 1 °C veiligheidsbuffer wordt gebruikt, is het gewone basisdoel 49 °C. De nominale herstart ligt daardoor rond 44 °C.",
                "Buiten het nachtvenster gaat het doel vanaf 1000 W actuele PV-productie naar 50 °C. Bij meer dan 3500 W echte injectie mag het doel 60 °C worden, maar niet wanneer één van de gekoppelde koelzones actief of onzeker koelt. Tijdens koeling blijft de zonneopwarming maximaal 50 °C.",
                "De 50 °C-regel is op PV-productie gebaseerd en kan dus netstroom aanvullen. De 60 °C-regel vereist echte injectie. De fysieke −5 °C differentie wordt niet automatisch gewijzigd."
            ],
            "bullets": [
                "Panasonic-sterilisatie blijft zelfstandig AAN: maandag 12:00, 62 °C, maximaal 60 minuten.",
                "SolarPilot emuleert of vervangt sterilisatie niet en verlaagt het doel niet tijdens het beschermde sterilisatievenster.",
                "Krachtige modus en force-DHW kunnen als handmatige beschermingsbronnen worden gekoppeld.",
                "Het minimumregime wordt niet uitgesteld vanwege capaciteitstarief of forecast."
            ]
        },
        {
            "title": "5. Lokaal PV-model en schaduw",
            "paragraphs": [
                "SolarPilot vergelijkt werkelijk gemeten PV-vermogen met Forecast.Solar en leert een lokaal correctieprofiel. Het model koppelt terugkerende afwijkingen aan zonnestand en seizoenscontext; het leert dus niet simpelweg dat er op een vast uur schaduw is.",
                "Wanneer de optionele privébundel lokaal is geplaatst, gebruikt SolarPilot de geaggregeerde historische bootstrap vanaf de plaatsing van de zonnepanelen als voorzichtige start. Dezelfde bundel kan ook installatie-specifieke entity-koppelingen bevatten. Die privédata staat nooit in de publieke HACS-repository. Zonder bootstrap start het model gewoon leeg en leert het live. Nieuwe waarnemingen op verschillende dagen verhogen het vertrouwen. Willekeurige bewolking moet minder gewicht krijgen dan een terugkerende dip bij vergelijkbare zonnestand.",
                "Het model probeert ook herstel na lokale schaduw te leren. Zo kan de planner een geschikte last eerder laten starten vóór een verwachte dip of kort laten wachten wanneer bruikbaar herstel waarschijnlijk is."
            ],
            "bullets": [
                "Forecast vervangt nooit een actuele meter.",
                "Bij onvoldoende modelvertrouwen blijft de gewone forecast leidend.",
                "Historische uurdata wordt niet als exacte minuutvoorspelling geïnterpreteerd."
            ]
        },
        {
            "title": "6. Fasebewaking en faseherkenning",
            "paragraphs": [
                "L1, L2 en L3 worden afzonderlijk gemonitord. SolarPilot kan bij gecontroleerde vermogenssprongen leren op welke fase of fases een gemeten toestel waarschijnlijk zit. Alleen bruikbare, voldoende geïsoleerde gebeurtenissen tellen mee; conflicterende gelijktijdige veranderingen worden verworpen.",
                "Per toestel worden classificatie, vertrouwen en aantal waarnemingen bijgehouden. De faseweergave toont herkend toestelvermogen en een netto restcomponent. Die restcomponent is geen zuiver onbekend verbruik omdat PV en andere niet-gemeten stromen de P1-fasewaarden beïnvloeden.",
                "Automatisch starts blokkeren of lasten afbouwen op basis van fasegrenzen blijft uit totdat hoofdbeveiliging, tekenrichting en fasekaart voldoende zijn bevestigd."
            ],
            "bullets": [
                "Faseherkenning is adviserend totdat ze bewust wordt vrijgegeven.",
                "Read-only vermogenssensoren kunnen worden gebruikt om extra apparaten te leren zonder ze te bedienen.",
                "Een toekomstige batterij kan per fase of als 3-faseprofiel worden meegenomen."
            ]
        },
        {
            "title": "7. Thuisbatterij: analyse nu, aansturing later",
            "paragraphs": [
                "SolarPilot kan nu batterijscenario's analyseren en is voorbereid op één of meerdere echte thuisbatterijen. Zonder gekoppelde hardware blijft dit volledig adviserend.",
                "Per batterij zijn capaciteit, SoC, werkelijk batterijvermogen, reserve-SoC, laad-/ontlaadlimieten, fasehint en adaptertype voorzien. Fysieke bediening vereist globale toestemming én individuele toestemming én bevestiging dat SolarPilot de exclusieve externe setpoint-eigenaar is.",
                "Standaard is laden uit het net UIT en ontladen naar het net UIT. Een batterijopdracht moet door gemeten batterijvermogen worden bevestigd; bij ontbrekende bevestiging wordt het profiel geblokkeerd voor controle."
            ],
            "bullets": [
                "Loads first is de standaardstrategie voor deze installatie.",
                "Read-only, peak shaving en hybrid zijn ook voorzien.",
                "Bij meerdere batterijen wordt standaard bij laden de laagste SoC en bij ontladen de hoogste SoC eerst gebruikt.",
                "De historische batterijsimulatie is een technische what-if en geen aankoop- of terugverdiengarantie."
            ]
        },
        {
            "title": "8. Slim verwarmen en koelen: Panasonic beslist HEAT/COOL",
            "paragraphs": [
                "SolarPilot kiest nooit zelf HEAT of COOL. Panasonic AUTO blijft eigenaar van de verwarmings-/koelkeuze. SolarPilot kan alleen AUTO vrijgeven of, vooral in het tussenseizoen, de ruimtezones langdurig op OFF/coast zetten wanneer het thermische model voldoende vertrouwen heeft dat de woning comfortabel blijft.",
                "De Panasonic-doeltemperatuur blijft ongewijzigd de comfortreferentie. Een gewone planningsbeslissing gebeurt standaard om de 12 uur en kijkt 48 uur vooruit. Tijdens een coastperiode wordt wel vaker gecontroleerd of AUTO tijdig opnieuw moet worden vrijgegeven vóór de geleerde vloer-/bouwschilvertraging een comfortgrens bereikt.",
                "De energiebesparende coastlogica is standaard vooral voor het tussenseizoen. Bij een duidelijke winter- of zomervraag blijft Panasonic AUTO normaal gewoon actief, omdat de warmtepomp dan zelf beter kan moduleren en uitschakelen dan wanneer het EMS agressief heen en weer programmeert. Dit wordt op basis van de weersverwachting en het binnendoel bepaald, niet op vaste kalendermaanden.",
                "Per zone leert SolarPilot passieve warmteoverdracht, verwarmingsrespons, koelrespons en reactievertraging op basis van Panasonic hvac_action. Daarnaast leert SolarPilot de lokale zonnewinst in de woning: werkelijk PV-vermogen wordt als lokale instralingsproxy gebruikt om te schatten hoeveel de woning op zonnige momenten vanzelf opwarmt. Die bijdrage is begrensd en wordt pas gebruikt wanneer voldoende leerkwaliteit aanwezig is.",
                "De uurverwachting van de weersdienst wordt lokaal gecontroleerd tegen de werkelijk gemeten buitentemperatuur. SolarPilot leert afzonderlijk de systematische fout rond 6, 12, 24 en 48 uur vooruit en mag de voorspelling alleen binnen een instelbare maximumcorrectie bijstellen wanneer voldoende verschillende dagen en vertrouwen beschikbaar zijn.",
                "Iedere SolarPilot-coastperiode wordt achteraf geëvalueerd als correct, te lang of te voorzichtig. Na meerdere beoordeelde episodes mag alleen het minimum nuttige coastvenster voorzichtig binnen ingestelde grenzen worden aangepast. Comfortbanden, Panasonic-doeltemperatuur en de keuze HEAT/COOL veranderen hierdoor nooit.",
                "Als de actuele buitentemperatuurbron wijzigt, worden het thermische model en de lokale weerscorrectie veilig opnieuw geleerd. Als alleen de forecast-weerdienst wijzigt, leert de weerscorrectie opnieuw; zonder aparte buitensensor wordt dan ook het thermische model opnieuw opgebouwd.",
                "Een coastperiode is geen gegarandeerde energiebesparing. Panasonic AUTO kan zelf al langdurig idle blijven wanneer er geen warmtevraag of koelvraag is. Te agressief uitschakelen kan later een grotere inhaalvraag veroorzaken en de efficiëntie verslechteren. Daarom blijft fysieke AUTO/coast-bediening standaard opt-in en moet de praktijkdata aantonen dat ze voor deze woning zinvol is."
            ],
            "bullets": [
                "Een handmatig gekozen Panasonic HEAT- of COOL-stand wordt nooit door SolarPilot overschreven; de regeling wordt dan adviserend tot de gebruiker zelf terugkeert naar AUTO/OFF.",
                "Een harde comfortoverschrijding kan AUTO onmiddellijk opnieuw vrijgeven, maar SolarPilot kiest ook dan niet tussen HEAT en COOL.",
                "Nieuwe automatische coastperiodes vereisen voldoende modelzekerheid, een nuttig minimumvenster en standaard een lange AUTO/OFF-vasthoudtijd om pendelen te voorkomen.",
                "PV-voorconditionering staat standaard UIT en kan alleen een toch al noodzakelijke AUTO-herstart vervroegen; ze verandert het thermostaatdoel niet.",
                "Ook in duidelijke zomer/winter coasten kan afzonderlijk worden toegestaan, maar staat standaard UIT omdat de verwachte energiewinst onzeker is en comfort/COP kunnen verslechteren.",
                "Open raam- of deurcontacten worden bewust niet gebruikt door deze klimaatregeling. De gevraagde langzame raamblokkering is dus niet geïmplementeerd."
            ]
        },
        {
            "title": "9. Kwartierpiek, kosten en EMS-KPI's",
            "paragraphs": [
                "SolarPilot kan het actuele kwartiergemiddelde en de maandpiek gebruiken om een softwarematig importbudget te berekenen. Voor Vlaanderen is een instelbare facturatievloer voorzien; de standaard in deze configuratie is 2,5 kW.",
                "Dag-KPI's voor import, export, PV, zelfconsumptie, geregeld verbruik en indicatieve energiewaarde zijn toerekening en geen gecertificeerde energiemeting. Ze mogen niet als veiligheidsinput worden gebruikt.",
                "Een toekomstige batterij kan naast zelfconsumptie ook voor peak shaving worden geëvalueerd, maar fabrikantbeveiligingen, zekeringen en de echte netaansluiting blijven leidend."
            ]
        },
        {
            "title": "10. Leren: wat wel en niet automatisch verandert",
            "paragraphs": [
                "SolarPilot leert lokaal en verklaarbaar. Het herschrijft zijn eigen code niet en gebruikt geen externe AI-dienst voor de regeling.",
                "Leerdata mag planning conservatiever maken, lokale PV beter corrigeren, een faseclassificatie opbouwen, complete apparaatcycli samenvatten en het thermische gebouwmodel verfijnen. Voor ruimteklimaat omvat dat lokale zonnewinst, systematische weersvoorspellingsfout en het resultaat van eerdere coastperioden. Voor beschermde cycli worden alleen volledige start-tot-stopcycli met bruikbare vermogensmeting geaccepteerd; half waargenomen of te korte cycli worden niet als profiel gebruikt. Leren mag geen comfort-, hygiëne- of elektrische veiligheidsgrens zelfstandig versoepelen. Voor ruimteklimaat betekent leren vooral beter voorspellen wanneer AUTO opnieuw nodig is; niet zelf leren wanneer HEAT of COOL gekozen moet worden."
            ],
            "bullets": [
                "Niet automatisch leerbaar: prioriteiten, netlimieten, temperatuurminima, sterilisatie, fasegrenzen, deadlines, toestemming voor netstroom en batterij-eigenaarschap.",
                "De echte toestand van apparaten en actuele metingen blijven belangrijker dan historische verwachtingen.",
                "Leergegevens kunnen worden gewist zonder dat vaste veiligheidsinstellingen verdwijnen."
            ]
        },
        {
            "title": "11. Eerste ingebruikname, migratie en concurrerende regelingen",
            "paragraphs": [
                "SolarPilot vervangt PV Excess Control volledig bij de definitieve ingebruikname en gebruikt geen pv_excess_control_* runtime-entiteiten als bron. De twee oude boilerautomatiseringen worden eveneens uitgeschakeld voordat SolarPilot de boiler actief gaat regelen.",
                "De eerste ingebruikname gebeurt gecontroleerd: eerst SolarPilot in Observatie controleren, daarna de oude regelaar(s) uit, fysieke toestelstanden controleren en vervolgens één niet-kritieke SolarPilot-last activeren."
            ],
            "bullets": [
                "PV Excess Control wordt bij go-live volledig uitgeschakeld.",
                "Alle vervangen boiler- en PV-overschotautomatiseringen worden vóór overname uitgeschakeld.",
                "SolarPilot controleert de algemene PV Excess Control-hoofdschakelaar wanneer die integratie aanwezig is; overige oude regelaars controleer je tijdens de migratie expliciet.",
                "Panasonic-sterilisatie blijft aan en Wallbox Full Solar blijft autonoom."
            ]
        },
        {
            "title": "12. Logische interface en configuratiestructuur",
            "paragraphs": [
                "SolarPilot gebruikt één Configuratiecentrum in plaats van een lange lijst losse functies. De instellingen zijn gegroepeerd als Overzicht, Energie & net, Verbruikers & prioriteiten, Comfort & warmtepomp, Opslag & laden, Voorspellen & optimaliseren en Geavanceerd & systeem.",
                "De publieke HACS-release bevat bewust geen woning- of installatie-specifieke entity_id's. Wie geen privébundel gebruikt, kiest de net- en optionele PV-bron en overige koppelingen expliciet via Home Assistant. Wie wel een privébundel gebruikt, plaatst één lokaal bestand in de door HACS bewaarde userfiles-map; SolarPilot vult daarmee alleen nog lege, bestaande bronkoppelingen in. Ontbrekende entiteiten worden overgeslagen en later opnieuw geprobeerd. Dezelfde bundel kan de geaggregeerde historische bootstrap bevatten. Import schakelt nooit fysieke klimaatbediening, fase-afbouw of boilerregeling vrij en de runtime start altijd in Observatie.",
                "De basispagina's tonen alleen de instellingen die je normaal nodig hebt. Timing, faseherkenning en Wallbox-herkenningsdetails staan bewust onder Geavanceerd. De onderliggende option-keys en regelalgoritmen blijven compatibel met bestaande instellingen.",
                "De dashboardkaart gebruikt dezelfde mentale structuur met zeven tabbladen: Overzicht, Verbruikers, Comfort, Planning, Energie, Opslag en Uitleg. Moduskeuze en belangrijke waarschuwingen blijven altijd bovenaan zichtbaar. In Planning staan nu naast de horizon ook planfouten, uitvoeringstreffer, beschermde cyclusprofielen en recente what-if-replay. Daardoor hoeft niet alle telemetrie tegelijk in één lange kaart te staan.",
                "De tab Comfort bevat voor slim klimaat nu vier samenhangende delen: instellingen, bevindingen/leerresultaten, meldingen en uitleg. Iedere klimaatinstelling uit het regelmodel is rechtstreeks wijzigbaar in Home Assistant. Bij elk veld staat een korte uitleg, een aanbevolen uitgangspunt en in gewone taal wat een lagere/hogere waarde of Aan/Uit betekent. Voor het opslaan toont SolarPilot nogmaals het advies en de verwachte gevolgen."
            ],
            "bullets": [
                "Eerste installatie vraagt alleen de essentiële net- en PV-bronnen; een optionele lokale privébundel kan daarna de overige bronkoppelingen en historische bootstrap in één keer veilig invullen.",
                "Verbruikers worden toegevoegd via een duidelijke vierstappenwizard: basis, koppeling, gedrag & bescherming, planning & energie.",
                "Batterijprofiel en batterijbediening zijn gescheiden zodat read-only gebruik geen bedieningsvelden toont.",
                "Slim klimaat, fasebewaking en Wallbox hebben een korte basispagina en een aparte geavanceerde pagina.",
                "Dagelijkse bediening en klimaatfijnafstemming blijven op het dashboard; Configureren is vooral bedoeld voor koppelingen en hoofdregels.",
                "Er bestaan geen verborgen klimaat-tuningwaarden zonder dashboarduitleg: iedere SMART_CLIMATE-instelling heeft één catalogusitem met betekenis, advies, gevolg en aanbevolen standaard."
            ]
        },
        {
            "title": "13. Eenvoudige installatie en volledige verwijdering",
            "paragraphs": [
                "Vanaf de publieke HACS-release is HACS de aanbevolen installatiemethode. Voeg de publieke SolarPilot-repository één keer als HACS Custom Repository van het type Integration toe, download SolarPilot en herstart Home Assistant. Daarna voeg je SolarPilot toe via Apparaten & diensten. Voor een installatie-specifieke snelle start kan één privébestand als `custom_components/solar_pilot/userfiles/private_bundle.json` lokaal worden geplaatst; HACS bewaart die map bij gewone updates. Via Geavanceerd & systeem → Privéprofiel & historiek kan de bundel opnieuw worden ingelezen. De frontend zit in dezelfde integratie en verschijnt automatisch in de Home Assistant-zijbalk; een losse www-map, Lovelace-resource of handmatig dashboard-YAML is niet nodig.",
                "Voor verwijderen bestaat een veilige voorbereidingsactie. SolarPilot gaat naar Pauze, stopt nieuwe starts, laat eigen onderbreekbare lasten volgens hun beveiligingen vrijgeven, brengt een door SolarPilot veroorzaakte klimaat-coast terug naar Panasonic AUTO en laat een door SolarPilot beheerd boilerdoel terugvallen naar het normale basisregime. Beschermde cycli en onzekere fysieke toestanden worden nooit hard afgebroken alleen om sneller te kunnen verwijderen.",
                "Wanneer SolarPilot 'Verwijderen gereed' meldt, verwijder je eerst de SolarPilot-configuratie-entry via Apparaten & diensten. Daarbij wist SolarPilot zijn eigen leer-/runtime-opslag, services, melding en zijbalkpaneel. Onderliggende P1-, Panasonic-, Wallbox-, Shelly- en andere Home Assistant-entiteiten worden nooit verwijderd. Verwijder daarna SolarPilot in HACS en herstart Home Assistant; HACS beheert dan ook de programmabestanden onder custom_components."
            ],
            "bullets": [
                "Installatie via HACS: repository één keer toevoegen, SolarPilot downloaden, herstarten en daarna via de Home Assistant-UI configureren; een lokale privébundel is optioneel en wordt nooit via GitHub verspreid.",
                "Geen aparte /config/www/solar-pilot-card.js of dashboardresource nodig.",
                "Verwijderen voorbereiden is veilig en weigert 'gereed' te melden zolang SolarPilot nog een toestel, boiler, batterijopdracht of coasttoestand bezit.",
                "De verwijderactie wist uitsluitend SolarPilot-eigen data en raakt de gekoppelde apparaten/integraties niet aan.",
                "Bij HACS-installatie beheert HACS ook updates en het verwijderen van de programmabestanden; een handmatige mapverwijdering is normaal niet nodig."
            ]
        },
        {
            "title": "14. Release- en documentatieregel",
            "paragraphs": [
                "Deze actuele uitleg is onderdeel van de release zelf. Dezelfde inhoud wordt als Markdown meegeleverd én in Home Assistant getoond. Een releasecontrole faalt wanneer versie of gegenereerde uitleg niet overeenkomt met de integratieversie.",
                "Bij iedere toekomstige gedragswijziging moet eerst deze bron worden aangepast. Daarna wordt de leesbare documentatie opnieuw gegenereerd. Zo blijft er steeds één actuele beschrijving; losse historische updatebestanden zijn niet nodig in een First Install-pakket."
            ]
        }
    ]
}

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
