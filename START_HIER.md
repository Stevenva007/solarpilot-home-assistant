# SolarPilot beta.61 — installatie en upgrade

SolarPilot controleert bekende boilerbevestigings- en servicefouten automatisch opnieuw, zonder gewone handmatige controleklik. Alleen expliciet herkende foutsoorten en een nauw begrensde oude bevestigingsfout krijgen dit pad. Een afzonderlijk persistent hersteljournal bij dezelfde koppeling vereist werkelijke nieuwe, geldige en niet-restored tank-/doelrapportage en bekende inactieve bescherming. Een nieuwe passende rapportage van het werkelijk aangevraagde doel na de fout kan de late bevestiging oplossen. Twee overeenkomende nieuwe rapportages van het actuele normale native doel na de fout, over minstens zestig seconden, kunnen onzekere eigen aansturing veilig loslaten. De hercontrole zelf schrijft geen temperatuur en herhaalt geen oude opdracht.

Een volgende gewone beleidsbeoordeling mag alleen na een nieuwe P1-rapportage, met verse PV en huidige prioriteiten, reserves, serialisatie, doelgrenzen, eigendom en fabrikantbescherming een nieuwe boilerpoging kiezen. Fouten geven begrensde wachttijd: 300 seconden na de eerste, 900 na de tweede en 3600 vanaf de derde; bij herhaling bovendien hoogstens één nieuwe poging per uur. De bestaande ingestelde rust voor optionele verhogingen sinds een echte doelopdracht, standaard 1800 seconden, blijft gelden. Betrouwbaar vastgesteld native doel laat andere veilige lasten doorwerken terwijl uitsluitend de boiler nog haar herprobeerwachttijd afwacht. Journal en foutreeks blijven over herstart behouden; herstart omzeilt onzekerheid of wachttijd niet.

Onbekende foutsoorten, een gewijzigde koppeling, bewuste handmatige boilerpauze en ongeldige of actieve bescherming blijven beschermd. De gerichte handmatige controle blijft een optionele fallback: in Automatisch regelen **Pauzeren voor boilercontrole**, daadwerkelijk bevestigde **Pauze**, daarna **Boilercontrole afronden** met de bestaande voorwaarden. Alleen bekijken mag hetzelfde pad gebruiken. Geen pending opdracht, verse tank-/doelrapportage en bekende inactieve bescherming blijven vereist. Geslaagde review schrijft geen temperatuur en geeft een zichtbaar resultaat; vervolgens kan je gewone Auto kiezen. De generieke toestelfoutreset wist geen boilerfout en geeft bij alleen DHW de juiste gerichte instructie in plaats van vals succes.

De uitgebreide uitleg en Recorder-/presentatiecorrecties uit beta.60 blijven behouden. De definitieve lokale softwaregate behaalt **3814 geslaagde tests in 46,62 s**; de eigen CI/publicatie en pakketverificatie volgen na upload. Test-/publicatiestatus: [docs/TESTRESULTATEN_BETA61.md](docs/TESTRESULTATEN_BETA61.md).

Beta.60 breidt **Overzicht → Wat gebeurt er en waarom?** uit met begrijpelijke uitklapbare uitleg bij elk toestel en elke regeling. Je ziet wat wel in orde is, welke voorwaarde nog ontbreekt, welke wachttijd loopt en het bekende vermogen. Gemeten vermogen en een schatting blijven afzonderlijk herkenbaar. Warm water en ruimteverwarming/koeling wisselen elkaar af op dezelfde warmtepomp; één gezamenlijke meting, niet apart opgeteld. Uitgeklapte uitleg blijft open bij automatisch verversen en herschikken. De pagina verklaart de bestaande regeling en geeft geen nieuwe toestemming om toestellen te bedienen.

Ook de native schakelaar voor lokaal leren gebruikt voortaan hetzelfde gedeelde leerpresentatieoverzicht en laat grote detailpakketten uit de herhaalde Recorder-kopie weg. De actuele volledige attributen, eigen opgeslagen leer-/modelgegevens en de volledige beschikbare analyse-export blijven behouden. De 16 KiB-limiet betreft één Home Assistant-historiekpakket, niet vrije schijfruimte. Er is geen data-/leerreset of gewijzigde bewaartermijn; deze update maakt geen onbeperkt archief en reconstrueert geen vroeger ontbrekende Recorder-records.

Beta.59 verhelpt ook de melding over te grote leergegevens voor de Home Assistant-historiek en vermindert herhaald rekenwerk bij het bijwerken van het dashboard. De volledige leer- en modelgegevens blijven beschikbaar in SolarPilot zelf, in de eigen opslag en in de analyse-export. Home Assistant bewaart bij de gewone sensorhistoriek alleen de kleine samenvatting, zodat dezelfde grote modellen niet iedere keer worden gekopieerd. De melding gaat over de maximale grootte van één historiekregel, niet over vrije schijfruimte. Bestaande bewaartermijnen blijven behouden; dit voegt geen onbeperkt archief van alle ruwe meetpunten toe.

Beta.59 herstelt een concrete interne fout bij het berekenen van de avondvoorraad voor warm water. Met een bruikbare zonnevoorspelling kon die berekening vastlopen en de algemene regeling naar een beschermde Pauze laten gaan. De berekening kan nu doorgaan. Het screenshot van Pauze na kiezen van Automatisch regelen bewijst zonder bijbehorende foutregel niet dat juist deze fout op de live installatie optrad.

Beta.59 maakt de twee actuele energietegels **Zonnepanelen** en **Net** herkenbaar met een gekleurde rand, zachte achtergrond en een kleurverloopbalk. Zonneproductie loopt van rood via oranje, geel en lichtgroen naar groen naarmate meer van de ingestelde omvormergrens wordt gebruikt. Netinjectie is groen; rond nul is de kleur lichtgroen en stijgende netafname loopt via geel en oranje naar rood. De getallen en de woorden afname/injectie blijven zichtbaar. Oude of onbeschikbare metingen blijven grijs en onbekend. Dit is alleen weergave, geen foutmelding, regelwijziging of nieuwe vermogensvrijgave.

De beta.58-regeling hervat een gewone opgeslagen Pauze na herstart automatisch zodra de bestaande controles dit toelaten. **Na herstart automatisch hervatten** staat standaard Aan bij de modusknoppen. Alleen bekijken, echte fouten en voorbereiden van verwijderen blijven beschermd. De kaart toont automatisch wachten of een vereiste echte controle.

Alle beta.57-regelingen blijven behouden: één gezamenlijke warmtepompbegroting, extra 60 °C vóór veilige gewone lasten, AUTO vanaf 2500 W restzon, informatie-only sterilisatieplanning en blauwe activiteitsranden. Geldige leerdata, bronkoppelingen, dashboardkeuzes, APP-aanvragen en veiligheid blijven behouden. Er is geen nieuwe rangordemigratie; de bestaande éénmalige beta.57-migratie blijft bij upgrades van oudere versies gelden. Test-/publicatiestatus: [docs/TESTRESULTATEN_BETA61.md](docs/TESTRESULTATEN_BETA61.md).

Echte resterende fouten die handmatige controle vragen staan ook onder **Home Assistant → Meldingen → SolarPilot: controle nodig**. De melding noemt wat er fout is en waar je de gerichte controle uitvoert. Automatische hercontrole en tijdelijke bronwacht blijven op het dashboard; normale Pauze, handmatige bediening of hygiëne geven geen nieuwe foutmelding. Na oplossing verdwijnt de controlemelding.

Een echte bronconfiguratiefout meldt welke koppelingen, exclusieve vermogensmeting of eenheid je onder Toestellen → Toestellen beheren moet controleren. Controle afronden herstelt geen verkeerde configuratie. Een werkelijk actieve dubbele regeling krijgt de melding Dubbele regeling actief: kies één regelaar en schakel de oude regeling zelf uit of pas haar aan. SolarPilot schakelt een andere regelaar niet automatisch uit. Tijdelijke bronwacht blijft automatische dashboardinformatie.

Blijft een bekende automatische boilerbevestigingsfout minstens vijftien minuten wachten op nieuwe bronrapportage of een betrouwbare bevestiging van het actuele doel, dan vraagt dezelfde stabiele HA-controlemelding de toestelverbinding en het werkelijk gemelde doel te controleren. De automatische hercontrole blijft lopen; hiervoor hoef je geen foutreset of boilercontrole uit te voeren. Na herstel verdwijnt de melding. Vroege gewone bronwacht, de zestigseconden-bewijscontrole, een herprobeerwachttijd op zichzelf en native fabrikantbescherming veroorzaken dit bericht niet. Ongewijzigde inhoud wordt niet iedere regelronde opnieuw gemeld.

Naast het laatste diagnose-record bewaart de bestaande lokale onderzoeksregistratie nieuwe boilerfout- en herstelgebeurtenissen met een kopie van aangevraagd/gemeld doel, wachttijd en soort beoordeling. Daardoor kan een nieuwer laatste record het eerdere gestructureerde spoor binnen de werkelijk beschikbare onderzoeksperiode behouden. Deze gebeurtenissen vallen onder de bestaande maximaal zeven dagen en vaste aantallimieten; er is geen onbeperkt archief of aanvulling achteraf. Een fout in deze aanvullende registratie mag de regelaar niet laten vastlopen.

## 1. Vooraf

- Maak een actuele volledige Home Assistant-back-up en bewaar de gecontroleerde beta.60-release voor rollback.
- Laat een lopende beschermde afwas- of andere cyclus afwerken.
- Gebruik bij een nieuwe installatie **Alleen bekijken** voor de eerste broncontrole. Bij bestaand actief beheer kan die modus eerst **Pauze** en veilige vrijgave vereisen. Alleen bewezen eigen coast en passende bevestigde numerieke batterijdoelen mogen worden vrijgegeven; handmatige bediening blijft beschermd.
- Voor een gewone upgrade is Pauze niet verplicht. Wil je bewust gepauzeerd blijven na de herstart, zet **Na herstart automatisch hervatten Uit**; de standaard Aan vraagt dan juist automatische terugkeer. Deze schakelaar verandert de huidige modus niet.
- Updates zijn cumulatief: bestaande Home Assistant-configuratie en lokale leerdata blijven behouden; tussenliggende beta-versies hoeven niet afzonderlijk geïnstalleerd te worden.

## 2. Via HACS installeren of upgraden

1. Voeg bij een nieuwe installatie in **HACS → Custom repositories** `https://github.com/Stevenva007/solarpilot-home-assistant` toe als type **Integration**.
2. Download of update naar exact `1.0.0-beta.61` zodra die release beschikbaar is.
3. Herstart Home Assistant volledig.
4. Herlaad de webpagina. Stop op Android de Home Assistant-app volledig en open haar opnieuw; op iOS kun je de weergave naar beneden trekken om te verversen. Controleer backendversie en geladen kaart afzonderlijk. Een download of manifestnummer bewijst geen geladen kaartcode.
5. Voeg bij een nieuwe installatie **SolarPilot** toe via **Instellingen → Apparaten & diensten** en kies je P1/netbron en optionele PV-bron.

De interface verschijnt automatisch. Er is geen aparte Lovelace-resource of dashboard-YAML nodig. Bij een lokaal pakket vervang je uitsluitend `custom_components/solar_pilot`; bewaar bestaande `userfiles` en Home Assistant-opslag.

Controleer bij een waarschuwing de genoemde toestelbron. **Automatische broncontrole** wacht op betrouwbaar nieuwe data en vraagt geen reset. Bij een verkeerde vereiste bronkoppeling corrigeer je die koppeling; een echte **Opdrachtfout** behoudt de bestaande gerichte controle. Controleer bij de modusknoppen **Na herstart automatisch hervatten Aan** voor automatische terugkeer. Zie [docs/BETA61_INSTELLEN.md](docs/BETA61_INSTELLEN.md); verwijder geen configuratie of leerdata.

## Interne fout na Automatisch regelen

Zie je na installeren nog de eerder opgeslagen interne foutpauze, kies dan één keer **Automatisch regelen**. Deze bewuste keuze hervat na de codeherstelling de gewone regeling; er is daarvoor geen algemene reset nodig. Alleen bij een afzonderlijk gemelde gewone herstart-/toestelfout volg je de bedoelde **Controle afronden**. Bekende boilerbevestigings-/servicefouten worden automatisch herbeoordeeld met nieuw betrouwbaar bronbewijs. Alleen wanneer die automatische route niet van toepassing is, blijft **Pauzeren voor boilercontrole → bevestigde Pauze → Boilercontrole afronden** een gerichte optionele fallback; een generieke toestelreset wist de boilerfout niet. Wordt de regeling opnieuw door een interne fout gepauzeerd, bewaar dan het tijdstip en de bijbehorende SolarPilot-foutmelding met foutdetails uit **Instellingen → Systeem → Logboeken**. Voor die foutanalyse is een grote zeven-dagenexport niet nodig. Wis geen leerdata of onzekere toestelopdrachten om de melding weg te krijgen.

## 3. Optioneel privéprofiel

Plaats een bestaande installatie-specifieke `private_bundle.json` alleen lokaal in:

```text
/config/custom_components/solar_pilot/userfiles/private_bundle.json
```

Importeer via **SolarPilot → Configureren → Geavanceerd & systeem → Privéprofiel & historiek**. De bundel vult alleen lege, werkelijk bestaande entiteiten in. Fysieke klimaatbediening, fase-afbouw en boilerregeling krijgen hierdoor geen automatische vrijgave. Deel dit bestand niet publiek.

## 4. Boilerwachttijden en gegevensbehoud

Controleer bij extra warm water de twee afzonderlijke wachttijden. **Stabiliteitscontrole** vraagt voortdurend geldig zonnebewijs; **rust tussen doelopdrachten** wacht op de ingestelde minimumtijd sinds de laatste werkelijk verstuurde doelopdracht. Die laatste opdracht kan ook een verlaging of herstel naar het normale doel zijn. Standaard zijn dat respectievelijk 300 en 1800 seconden; bestaande eigen instellingen blijven behouden.

Als de zonnevoorwaarden geldig blijven, mag de stabiliteitscontrole niet telkens opnieuw beginnen alleen omdat de opdrachtrust nog loopt. De kaart toont die echte uitvoeringswachtreden. Zodra beide voorwaarden en alle andere guards voldaan zijn, kan de volgende gewone regelronde de verhoging vragen. Werkelijk verlies van geldig zonnebewijs, koeling of een te groot meetgat kan een nieuwe stabiliteitscontrole vereisen.

Houd **gemeten tanktemperatuur**, **SolarPilot-voorstel** en **gemeld Panasonic-doel** apart. Een voorstel is nog geen uitgevoerde verhoging. Een echt gemeld hoger doel krijgt een gestippelde blauwe rand; alleen passend verse opwarmactiviteit krijgt doorlopend blauw. De bekende maandagsterilisatie 12:00/62 °C kan intern blijven zonder doelwijziging; de planning blokkeert geen gewone 60 °C-vraag. Echte gekoppelde hygiene/manual/native-onzekerheid en pending behouden hun afzonderlijke guard.

### Behouden opdracht- en forecastcontrole

Een pending batterijopdracht laat nieuwe gewone lasten, AEG-deadline-START en vermogensoverdracht wachten. Nieuw passend batterijvermogen van ná de opdracht en daarna nieuw P1-bewijs blijven nodig; ontbrekende rapportage is geen klaarstatus of reden voor een blinde retry. Een verwijderen-voorbereiding vereist werkelijk neutraal batterijvermogen en bij numerieke aansturing een neutraal doel.

Ontbrekende forecasturen of staart blijven onbekend. Controleer tijdzone-/dekkinglabels; een onvolledige dag is geen volledige dagreplay en een werkelijk nultarief blijft nul. Export behoudt schema-sleutels, eenheden en statuswaarden bij consistente pseudoniemen. Een afgebroken start of ongeldige afzonderlijke opslagrij mag geldige andere gegevens niet wissen.

Op **Warmte & comfort** staat per zone **Handmatig bedienen**. Uit laat SolarPilot zelf AUTO/UIT kiezen; Aan toont de vaste **AUTO / UIT**-keuze. Die expliciete dashboardoverride blijft bewaard over herstarts tot je Handmatig bedienen weer uit zet. Een native wijziging buiten het dashboard krijgt tijdelijke gebruikersrust, standaard twaalf uur; vaste HEAT/COOL en pending/onzekere opdrachten blijven beschermd. Een geldige oorspronkelijke UIT-stand vraagt onder automatische zonebediening geen handmatige AUTO-fiets.

Gewone comfortvraag controleert **Werkelijk Panasonic-programma**: geen warmtevraagstart bij COOL/AUTO_COOL of koelvraagstart bij HEAT/AUTO_HEAT. Daarnaast mag zonne-AUTO bij 2500 W bruikbaar restoverschot na 60 s en nieuwe P1/PV zonder thermische vraag of modelscore. Het programma moet bekend en vers zijn; UIT is bekende context. Alleen bevestigd eigen zonne-AUTO houdt vanaf 2000 W met eenmaal verse gedeelde warmtepompstroom, begrensd door echte PV. Dashboardkeuze, externe rust, minimumtijden en bron-/opdrachtbescherming blijven leidend. HA AUTO/UIT kan door de integratie globaal worden vertaald; geen ongewijzigd programma garanderen.

Een passieve UIT-trend mag geen actief verwarm-/koelverloop gebruiken; actueel buitenbewijs bepaalt de huidige richting. Zachte nieuwe AUTO-vraag vanuit UIT moet standaard tien minuten aanhouden. Harde of onderbouwd dringende comfortvraag behoudt haar bestaande herstelpad. Het overzicht noemt **Comfortbewaking tijdens leren** of **Voorspellend geregeld**, per-zone reden en echte forecastdekking. Actuele passende comfortvraag werkt zonder volledig geleerd model. Leerbewijs, relevante dagen/episodes en gemeten voorspelfout blijven afzonderlijk; samples bewijzen geen 98% nauwkeurigheid. Winter-/zomerweer houdt AUTO niet alleen wegens die context aan. Een toekomstige hittegolf vraagt relevant koelbewijs en echte forecasturen; AUTO met ongewijzigd doel garandeert geen bouwschilvoorkoeling.

Behoud je huidige instellingen en leerdata. Deze update vraagt geen algemene leerreset. De eerdere bescherming van gecontroleerde fasewaarnemingen zonder bewijs van stabiele andere meters blijft gelden; geldige passieve waarnemingen, nieuwe geïsoleerde fasewaarnemingen en handmatige fasekeuzes blijven behouden. Zie [docs/BETA61_INSTELLEN.md](docs/BETA61_INSTELLEN.md) voor de volledige controle.

## 5. Automatisch herstel na herstart

Een gewone opgeslagen **Pauze** vraagt met **Na herstart automatisch hervatten Aan** bij de volgende Home Assistant-herstart of integratieherlading automatisch **Automatisch regelen** via de bestaande controles. Met Uit blijft Pauze staan; een al opgeslagen automatische modus houdt haar normale herstelroute. Alleen bekijken en een eerste installatie blijven Alleen bekijken. De schakelaar verandert de huidige modus niet. Opnieuw Pauze kiezen annuleert een nu wachtende hervatting; bij de volgende herstart geldt de voorkeur weer.

Interne fouten en voorbereiden van verwijderen bewaren een afzonderlijke pauzeoorzaak en reden en hervatten niet automatisch. Bekende opdrachtfouten, onzekere eerdere opdrachten en vereiste boilerbeoordeling blijven beschermd. Een gezonde volgende meetronde wist een interne foutreden niet. Oudere beta.57-Pauze heeft geen opgeslagen oorzaak; daar kan SolarPilot uitsluitend een gewone beveiligde hervatting proberen, geen vroegere handmatige/foutoorzaak bewijzen.

SolarPilot controleert eerder beheerde toestellen afzonderlijk. Bij ontbrekende, restored of onbeschikbare bediening wordt alleen dat toestel tijdelijk opzijgezet. Er volgt geen blinde OFF en onbekend verbruik wordt niet als nul gerekend. De overige beschikbare toestellen kunnen in de opgeslagen automatische modus verder zodra betrouwbare globale P1- en veiligheidsmetingen en hun eigen voorwaarden dit toelaten. Een eerste installatie zonder opgeslagen Auto-keuze blijft Alleen bekijken.

Het ontbrekende toestel wordt bij volgende gewone regelrondes automatisch opnieuw gecontroleerd. Zodra echte bruikbare status terugkomt, volgt de gewone herbeoordeling: eigen ON wordt zonder nieuwe start herkend; OFF laat het oude eigendom los; een gewijzigd numeriek doel blijft handmatig beschermd. Minimum aan-/uittijden starten conservatief bij de nieuwe waarneming. Deelname en prioriteit worden niet aangepast. Alleen bekijken blijft gelden; Pauze stopt de actuele hervatting en volgt bij een volgende herstart de zichtbare voorkeur.

Een onbeschikbaar toestel kan nog steeds stroom gebruiken of later opnieuw gaan vragen. De P1-meting bevat werkelijk huidig verbruik al; SolarPilot houdt daarnaast een conservatieve reserve voor mogelijk niet gemeten of later toenemend verbruik. Daardoor kunnen andere lasten soms nog wachten op echte vermogensruimte. Dat is een veiligheidsbeperking, geen globale opstartblokkering door het ontbreken van één status. Echte opdrachtfouten, een onzekere START, ongeldige globale bronnen en elektrische begrenzing houden hun bestaande bescherming.

Een bronwacht kan ook ontstaan na de herstart. De kaart toont een gerichte automatische controle zonder resetknop. Betrouwbaar bronherstel ruimt de wachtreden automatisch op; **Controle afronden** blijft bedoeld voor een echte fout of vereiste handmatige controle.

De boilercontrole werkt afzonderlijk. Een passend eerder beheerd tankdoel wordt zonder doelwrite herkend; een routinecontrole wacht op verse temperatuur-/doel-/beschermingsbronnen. Een vóór herstart pending opdracht wordt nooit herhaald en vereist voor bevestiging een nieuwe rapportage ná herstart en de bestaande adapterwachttijd. Echte fouten, bewuste handmatige overname of gewijzigd doel blijven beschermd. Een hygiëne-/krachtige fabrikantcyclus behoudt haar doel.

Een onzekere eerdere AEG-START krijgt geen nieuwe START. Alleen een nieuwe betrouwbare fase-terugmelding van ná START voor een lopende of voltooide cyclus kan de specifieke herstartonzekerheid oplossen; een oude Washing/Finished-stand niet. Idle of onduidelijke START-uitkomst leidt niet tot een tweede START. Een tijdelijk ontbrekende bron wordt automatisch opnieuw geprobeerd; een blijvend ontbrekende bron blijft als wachtreden zichtbaar.

Voor oude Alleen bekijken-opslag zonder hervatmarker kan de verloren Auto-keuze éénmalig worden hersteld, uitsluitend zonder echte fout/handmatige boilerbescherming en met een onderbroken lease van een bekend Auto-toestel of schoon routine-boilerjournal. Nieuwe expliciete Alleen bekijken-keuzes blijven beschermd. De Pauze-regel staat hierboven.

## 6. Bronnen en warm water controleren

Controleer in **Alleen bekijken** of **Pauze** de echte adapterherkomst, bronversheid, ruwe klimaat- en taakstatus, gemeld tankdoel, tankmeting, P1/PV, handmatige functies, hygiëne en pending opdrachten.

- Exact geregistreerde `aquarea` met actuele native `idle/off` kan de klimaatguard vrijgeven, ook in AUTO/HEAT_COOL en bij algemene `PUMP`-taakinfo.
- Werkelijke `cooling` blijft extra warmte begrenzen. Werkelijke `heating/preheating/defrosting` houdt de ingestelde ruimtecomfortvoorrang.
- Ontbrekende, oude, restored of onbeschikbare klimaatdata blijft blokkeren. Een taakmelding vervangt geen ontbrekende betrouwbare klimaatbron.
- Oudere `panasonic_cc` in AUTO/HEAT_COOL blijft zonder actuele expliciete `IDLE/WATER`-taak onduidelijk.
- Alleen bewezen koeling verlengt de ingestelde koelrusttijd. Onbekende data maakt geen nieuwe halfuurwachttijd na bronherstel.

Een vóór beta.46 opgeslagen koel-/onzekerheidstijd blijft conservatief behouden. Een bestaande uitloop of bescherming tijdens een native warmwatertaak kan daarom nog tijdelijk gelden; de upgrade wist geen mogelijk echte koeling.

Extra warm water start standaard vanaf 3000 W bruikbaar overschot; exacte grens telt. De vroegere drempelmigratie blijft éénmalig, eigen waarden blijven. Veilige lager geplaatste eigen onderbreekbare lasten mogen wijken na stabiliteit, echte UIT-bevestiging, nieuwe P1 en verse PV. Afwas, ruimteklimaat en Wallbox worden hiervoor niet gestopt. De raming van 3200 W wordt niet verlaagd. Controleer de W/kW-bron en **Wat meet deze vermogensmeter?**: standaard hele warmtepomp, exclusieve boiler alleen bij echte tankmeter. P1 bevat gezamenlijke stroom al eenmaal; een gedeelde meter bewijst geen specifieke tankopwarming. Stabiliteit, opdrachtrust, reserves, koeling, eigendom en elektrische/fabrikantgrenzen blijven afzonderlijk gelden.

## 7. Hervatten en doelbevestiging

Gebruik alleen waar nodig de bestaande gerichte boilerreview buiten **Automatisch regelen** en zonder pending opdracht. Zij schrijft zelf geen temperatuur. Een gewone herstartcontrole wordt automatisch afgewerkt; een echte fout of bewuste handmatige overname wordt hierdoor niet gewist.

Hervat gewone regeling na bron- en beveiligingscontrole en observeer een natuurlijke toegestane doelopdracht. Voor exact geregistreerde `aquarea` en `panasonic_cc` blijft minstens tien seconden nodig vóór een passende nieuwe Home Assistant-doelrapportage telt. Ook die rapportage bewijst geen compressorstart of bereikte tanktemperatuur.

Laat concurrerende boilerautomatiseringen uit zolang SolarPilot regelt. AEG-APP-aanvragen en beschermde cycli blijven behouden; maak geen nieuwe APP-aanvraag of START om updateacceptatie af te dwingen. De Wallbox blijft read-only. Nieuwe toestellen blijven afzonderlijk gecontroleerd en vrijgegeven.

## 8. Analyse, uitleg en rollback

Kies **Export → Export samenstellen → 7 dagen** voor de volledige beschikbare analyse als **JSON.GZ**. Alleen dezelfde ingelogde beheerder kan de lokale gecomprimeerde download tien minuten ophalen. De nieuwe route verkort de periode niet wegens de vroegere 16 MB-berichtgrens. Nieuwe punten bewaren de geladen versie; oudere ongestempelde punten blijven versie onbekend. Privacyfilters blijven behouden; publiceer analyses niet op GitHub.

De enige actuele regelbeschrijving staat in [docs/ACTUELE_WERKING.md](docs/ACTUELE_WERKING.md) en in Home Assistant onder **SolarPilot → Uitleg**. De volledige upgradecontrole staat in [docs/BETA61_INSTELLEN.md](docs/BETA61_INSTELLEN.md).

Voor rollback die bewust gepauzeerd blijft: **Na herstart automatisch hervatten Uit → Pauze → beschermde cycli afwerken → onveranderlijke beta.60-release of passende volledige back-up herstellen → Home Assistant herstarten → webpagina/app opnieuw openen → backend/kaart en beveiligingen controleren**. Beta.60 behoudt de uitgebreide uitleg en eerdere reparaties, maar mist automatische bekende-boilerfouthercontrole, begrensde foutwachttijden, gerichte controle en het nieuwe foutdiagnosespoor; haar generieke reset verhelpt geen DHW-fout. Meetretentie en centrale rangorde blijven behouden; programmabestanden herstellen eerdere opslag niet vanzelf. Gebruik voor exact herstel zo nodig de volledige bijbehorende back-up. Oude releasedocumenten blijven historie; `OVERDRACHT.md` beschrijft de huidige bron.
