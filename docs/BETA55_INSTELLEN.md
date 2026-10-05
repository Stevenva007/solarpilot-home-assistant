# SolarPilot 1.0.0-beta.55 — instellen en controleren

Beta.55 herstelt het gebruik van de uurlijkse weersforecast, de kalendergrenzen van ongedateerde native PV-dag-/uurbronnen, de betrouwbaarheid en uitleg van basislastleren en een nieuwe AEG-APP-aanvraag na een oude opgeslagen lopende cyclus. Een bruikbare toekomstige weerscurve blijft beschikbaar tussen normale uurupdates, terwijl de actuele buitentemperatuur haar eigen strikte versheidscontrole behoudt. Klimaatacties en leerafwijzingen worden met hun werkelijke bronbewijs beoordeeld. Verlopen, ontbrekende of verkeerd gekoppelde data wordt niet als geldig bewijs gebruikt.

## Bronbasis en gegevensbehoud

De codebasis en rollbackbasis zijn de gepubliceerde beta.54 op commit `8047742cf3fbb376792bb0730d7c0638923c03aa`, tree `b904876c53c8d136581ab1f12a0a1f17f7f5ef7f`. De onveranderlijke [beta.54-release](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.54), workflow `37220469340` en alle vier gepubliceerde assets zijn gecontroleerd; beide ZIP-pakketten zijn tegen de exacte gepubliceerde bron vergeleken. Dit is beta.54-bewijs en geen beta.55-publicatiebewijs.

Updates zijn cumulatief. Geldige instellingen, koppelingen, centrale prioriteit, modellen, historiek, APP-aanvragen, dashboardoverrides en operationele opdrachtbescherming blijven behouden. Deze update vraagt geen leerreset, nieuwe PV-dimensionering, extra Wallbox-toestemming of wijziging van boilerdoelen.

## Upgrade

1. Maak een actuele volledige Home Assistant-back-up en bewaar de gecontroleerde beta.54-release.
2. Laat beschermde afwas- of andere cycli afwerken. Gebruik geen STOPRESET voor de update.
3. Installeer exact `1.0.0-beta.55` via HACS zodra de release beschikbaar is, of vervang uitsluitend `custom_components/solar_pilot` met het gecontroleerde lokale pakket. Behoud bestaande `userfiles` en Home Assistant-opslag.
4. Herstart Home Assistant volledig. Herlaad de webpagina; op Android stop je de Home Assistant-app volledig en open je haar opnieuw, op iOS kun je de weergave naar beneden trekken om te verversen.
5. Controleer backendversie en geladen kaart afzonderlijk. Open **Uitleg** en controleer beta.55 en de bijbehorende actuele regel-hash. Een download of manifestnummer bewijst geen geladen kaartcode.

SolarPilot registreert de frontend zelf. Een extra Lovelace-resource, www-bestand of dashboard-YAML is niet nodig. De regel-hash is `0e41b3f32ae816e2`; de volledige lokale softwaregate behaalde 3064 geslaagde tests. Resultaten en bewijsgrenzen staan in `TESTRESULTATEN_BETA55.md`.

## Weersforecast en actuele buitentemperatuur

De geselecteerde actuele buitenbron moet betrouwbaar en in °C zijn. Voor actuele temperatuur blijft de maximumleeftijd dertig minuten. Een uurlijkse forecast heeft een afzonderlijke beschikbaarheids- en cachecontrole: de geselecteerde bron moet beschikbaar en niet restored zijn, de binding en eenheid moeten nog passen, de rapportagetijd moet geldig zijn, de curve moet bruikbare opeenvolgende huidige/toekomstige uren bevatten en de laatste geslaagde forecastopvraag moet binnen haar cachetermijn liggen.

De forecastcache is maximaal `max(1800 seconden, 2 × ingestelde verversingsinterval)` oud; bij de standaard uurverversing is dat twee uur. Een ouder ongewijzigd weerstatusrapport wist zo'n geldige forecast niet uitsluitend wegens de dertigminutengrens van actuele temperatuur. Dit maakt de actuele temperatuur zelf niet langer geldig.

Een mislukte forecastopvraag vernieuwt de cacheleeftijd niet; de laatste poging en laatste geslaagde opvraag hebben afzonderlijke tijden. Ontbrekende of mislukte opvragen krijgen een begrensde nieuwe poging na één minuut in plaats van pas na een volledig uur. Een bestaande bruikbare curve blijft alleen binnen haar oorspronkelijke geldigheid beschikbaar. Onbeschikbaar, restored, verkeerde eenheid, gewijzigde koppeling, ongeldige rapportagetijd, verlopen cache of ontbrekende toekomstige dekking geeft geen voorspellend vrijgavebewijs. Ook een bewaard DHW-koeladvies moet vóór hergebruik aan de huidige forecastgeldigheid voldoen; een nieuwe succesvolle forecasttijd maakt zijn vijfminutencache meteen opnieuw te beoordelen.

Controleer onder **Warmte & comfort** de actuele buitenbron, de weersforecast en de werkelijk beschikbare toekomstige uren. Laat een normale forecastverversing plaatsvinden en maak daarna een nieuwe analyse-export. Een gat of ontbrekende staart blijft onbekend; vijf beschikbare uren worden niet als 48 uur voorgesteld.

## Native PV-dag-/uurbronnen bij kalendergrenzen

Ongedateerde native bronnen zoals **vandaag**, **morgen** en **resterend vandaag** worden aan hun werkelijke lokale rapportagedag gekoppeld. Een rapport van vóór lokale middernacht krijgt na middernacht niet automatisch het nieuwe label **vandaag** of **morgen**. De nieuwe dag blijft onbekend tot passend vers native bewijs terugkomt.

**Huidig uur** en **volgend uur** moeten in het actuele verstreken uur zijn gerapporteerd. Na de uurgrens verlopen oude uurtellers tot nieuwe native rapportage, ook wanneer bij de overgang naar wintertijd hetzelfde lokale uur voor de tweede keer verschijnt. Een ongewijzigde tellerstand kan alleen weer bruikbaar worden met een echte passende nieuwe bronrapportage.

Een bron met eigen expliciete tijdstempels behoudt die tijden. Deze correctie herschrijft geen geldige gedateerde forecastcurve, historische metingen of opgeslagen PV-leerdata. Onbekende nieuwe dagdekking is geen nulopbrengst. Controleer na middernacht de datum en echte dekking; vergelijk dagvoorspellingen alleen met een overeenkomstige volledig gedekte meetperiode.

PV-leren blijft gebaseerd op werkelijke metingen, geconfigureerd paneelvermogen, omvormerlimiet en geldige dekking. Een nachtbin met nul meetbare productie is op zichzelf geen leerdefect. Een gemeten voorspelfout overdag blijft een afzonderlijke diagnose; de kalendercorrectie bewijst geen lagere fout of hogere nauwkeurigheid. Pas configuratie of modellen alleen aan op nieuw passend bewijs.

## Betrouwbare klimaatactie en basislastleren

Warmtepompactiviteit wordt alleen uit actuele betrouwbare gerapporteerde klimaatacties afgeleid. Oude, restored, onbeschikbare of ongeldig/toekomstig gedateerde acties worden niet als gewone rustlast geleerd. Een betrouwbare idle/off-zone maakt een onbeschikbare tweede zone niet bekend; zonder bewezen actieve richting blijft die gedeeltelijke zonestatus **onbekende warmtepompactiviteit**. Betrouwbaar gemelde verwarming of koeling blijft wel richtingsbewijs.

Een algemene **PUMP**-taak blijft bewust onbekende warmtepompcontext voor gewone huishoudelijke basislastleren. Zij bewijst geen verwarm-/koelrichting of compressorvermogen, ook niet wanneer betrouwbaar native idle de afzonderlijke optionele warmwaterguard vrijgeeft. **WATER** meldt evenmin zelf een gemeten compressoractie. Dit onderscheid verandert geen boilerbeleid en wist geen geldige modellen.

De leerdiagnose noemt de werkelijke reden waarom een restlastmeting wordt overgeslagen. Ontbrekende of ongeldige P1/PV telt als bronprobleem (`site_source`); stabilisatierust na een nieuwe last of een wachtende opdracht/overdracht als `settling`. Die afwijzingen zijn geen telling van onbekende warmtepompactiviteit. Een geldige restlastmeting kan afzonderlijk een onbekende warmtepompcontext hebben en blijft dan uitgesloten van gewone basislastleren. Beoordeel nieuwe analysegegevens op die afzonderlijke redenen; een leerreset is niet nodig.

## AEG: opnieuw gereed en een nieuwe APP-aanvraag

Als een eindmelding is gemist, kan de vorige cyclus opgeslagen als lopend blijven terwijl de AEG werkelijk alweer **Ready To Start** meldt. Beta.55 herkent een betrouwbare actuele verbonden READY-terugmelding en markeert uitsluitend de vorige cyclus als **einde onbevestigd**. Dit herstelt geen oude verbruikte aanvraag en claimt geen voltooide afwasbeurt. Een volgende expliciete APP-Enabled-overgang kan daarna één nieuwe aanvraag voor de nieuwe belading maken.

Een onzekere eerder verstuurde START blijft beschermd tegen herhalen. Running, Paused, Drying en onbekende, oude, restored of onbereikbare gegevens geven geen nieuwe aanvraagvrijgave. Deur openen vóór start blijft een wachtende aanvraag annuleren. Startup of een reconnect met APP al Enabled maakt geen nieuwe belading; geef de nieuwe belading bewust via de gewone APP-handeling vrij zodra de machine betrouwbaar gereed is.

Controleer de **maandag-startdeadline** afzonderlijk van de gewone deadline. Een ingevulde maandagkeuze heeft op maandag voorrang; leeg gebruikt de gewone deadline, standaard 13:00. Bij maandag 10:00 hoort een nieuwe geldige maandagaanvraag om 08:30 dus bij dezelfde dag met deadline 10:00. Bestaande aanvragen houden hun vastgelegde plandag/deadline tenzij je de bestaande gerichte herberekening kiest. Dit softwarepad is getest zonder een fysieke start te claimen. Een export van rond middernacht bewijst geen later werkelijk 08:30-APP-event of de live aanvraagchronologie; gebruik daarvoor nieuwe bron- en aanvraaghistoriek.

## Wallbox: effectieve sessiebron controleren

De Wallbox blijft volledig read-only. SolarPilot heeft een betrouwbare effectieve-sessiebron nodig die zonne-auto, handmatig en gestopt onderscheidt én haar daadwerkelijke rapportage tijdig vernieuwt. Een geselecteerde bestaande sensor kan nog steeds een oude of onjuiste sessietekst melden. Een native opgeslagen zonne-instelling bewijst niet dat de gebruiker op dit moment autonoom zonne-auto laadt.

Controleer in de installatie de definitie van de effectieve-sessiesensor, de echte handmatige overname en de periodieke bronrapportage. Een sensor die alleen de native zonne-instelling doorgeeft, of die alleen bij tekstwijziging rapporteert, levert geen passend actueel sessiebewijs. Deze installatiebron moet buiten de SolarPilot-integratie worden gecorrigeerd als haar definitie onjuist is. Zonder passende bron blijft manueel, oud, restored, onbekend of strijdig bewijs conservatief geblokkeerd. Geen template die alleen kunstmatig de tijd ververst, geen ruimere brontermijn en geen Wallbox-write gebruiken om die bescherming te omzeilen.

## Behouden ruimtebediening en beveiligingen

De beta.54-bediening blijft behouden: vrijgegeven Panasonic-zones worden afzonderlijk tussen AUTO en UIT geregeld; actuele passende comfortvraag blijft werken terwijl het model leert. Onder **Warmte & comfort** betekent **Handmatig bedienen: Uit** automatische regeling. **Aan** met **AUTO / UIT** bewaart de bewuste vaste keuze over herstarts. Terugkeer naar automatisch wist die override, geeft geen foutreset en verstuurt zelf geen opdracht. Externe native wijzigingen, vaste HEAT/COOL, onbeschikbare bronnen en pending/onzekere opdrachten blijven beschermd. Panasonic kiest verwarmen/koelen en het ruimtedoel blijft behouden.

Toestelisolatie, conservatieve reserves, actuele P1/PV, fase-/piekgrenzen, beschermde afwascycli, boilerstabiliteit, rust sinds de laatste werkelijk verstuurde boilerdoelopdracht, doelbevestiging en hygiëne blijven gelden. Historiek bevat geen sample-per-versiestempel; meerdere updates op dezelfde dag maken oudere boilerdoel- of timerwaarnemingen geen bewijs van een nieuwe beta.54- of beta.55-regressie. Een nieuwe analyse moet bij de werkelijk geladen versie en actuele bronnen worden beoordeeld.

Gebruik bij onduidelijk gedrag **Export → Export samenstellen** voor een nieuwe actuele analyse. Privacyfilters en pseudoniemen blijven behouden; publiceer privé-analyses niet op GitHub.

## Teststatus en rollback

De uitgevoerde beta.55-softwaregate en vereiste afzonderlijke publicatie-/pakketcontrole staan in `TESTRESULTATEN_BETA55.md`. De volledige lokale suite is geslaagd; de daarna ontstane CI-status hoort bij de exacte gepubliceerde commit en tag. HA-API-/DOM-doubles bewijzen softwaregedrag, geen fysieke respons of live installatie. In deze werksessie is geen live Home Assistant-toegang of fysieke toestelactie uitgevoerd.

Rollback: **Pauze → beschermde cycli afwerken → onveranderlijke beta.54-release of gecontroleerde volledige back-up herstellen → Home Assistant herstarten → webpagina/app opnieuw openen → backend/kaart, bronnen, eigendom en beveiligingen controleren**. Beta.54 behoudt de autonome zonebediening en dashboardoverrides, maar bevat de beta.55-forecastcache-, PV-kalender-, leerdiagnose- en AEG-READY-correcties niet. Controleer daarom na rollback opnieuw de forecastgeldigheid, native PV-dag-/uurdekking en de werkelijke AEG-aanvraag-/cyclestatus. Oude releasedocumenten blijven onveranderd; `OVERDRACHT.md` beschrijft de huidige bron.
