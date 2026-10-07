# SolarPilot 1.0.0-beta.61 — instellen en controleren

SolarPilot controleert bekende boilerbevestigings- en servicefouten automatisch opnieuw, zonder gewone handmatige controleklik. Alleen expliciet herkende foutsoorten en een nauw begrensde oude bevestigingsfout krijgen dit pad. Een afzonderlijk persistent hersteljournal bij dezelfde koppeling vereist werkelijke nieuwe, geldige en niet-restored tank-/doelrapportage en bekende inactieve bescherming. Een nieuwe passende rapportage van het werkelijk aangevraagde doel na de fout kan de late bevestiging oplossen. Twee overeenkomende nieuwe rapportages van het actuele normale native doel na de fout, over minstens zestig seconden, kunnen onzekere eigen aansturing veilig loslaten. De hercontrole zelf schrijft geen temperatuur en herhaalt geen oude opdracht.

## Basis en upgrade

De absolute codebasis en rollbackbasis zijn gepubliceerde beta.60 op commit `213b31a69c9768aea7a6b52e845f2cc6e77bb7de`, tree `378533419b62251b218238fad4d242f3efe5bf81`, annotatietagobject `3968c772103828c9e3781fca5adc575630faacc0`. De onveranderlijke [beta.60-release](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.60), release-ID `404797193`, workflow `37475747281` en alle vier gepubliceerde assets zijn gecontroleerd. Het HACS-archief heeft 380 bestanden, het lokale pakket 126; beide zijn inhoudelijk en met SHA-256 tegen de exacte gepubliceerde bron vergeleken. Lokaal behaalde beta.60 3630 tests in 45,70 s; CI behaalde 3630 tests in 33,31 s. Dit is basisbewijs, geen beta.61-test-/publicatiebewijs.

1. Maak een actuele volledige Home Assistant-back-up en bewaar beta.60 voor rollback.
2. Laat een lopende beschermde afwascyclus afwerken; onderbreek haar niet via de stekker of STOPRESET.
3. Installeer exact `1.0.0-beta.61` via HACS of vervang uitsluitend `custom_components/solar_pilot` met het lokale pakket. Behoud `userfiles` en Home Assistant-opslag.
4. Herstart Home Assistant volledig. Herlaad de webpagina; stop op Android de Home Assistant-app volledig en open haar opnieuw, of ververs de weergave op iOS.
5. Controleer backend én kaartversie. **SolarPilot → Uitleg** moet beta.61 en de actuele regel-hash tonen; een manifestnummer bewijst geen geladen kaartcode.

De frontend wordt automatisch geregistreerd. Je hebt geen extra dashboard-YAML, Lovelace-resource of kopie onder www nodig. Instellingen, leerdata, APP-aanvragen, dashboardoverrides en centrale voorrang blijven behouden. Deze update voegt geen rangordemigratie, leerreset of gewijzigde bewaartermijn toe.

## Automatische hercontrole en hervatting

Bij een bekende bevestigings-/servicefout blijft SolarPilot vanzelf echte nieuwe rapportages controleren. De kaart toont de hercontrole, ontbrekende bron-/beschermingsvoorwaarden en resterende lokale wachttijd. Je hoeft geen gewone controleklik of Pauze-/Auto-cyclus uit te voeren.

| Nieuwe betrouwbare waarneming | Automatische afhandeling |
| --- | --- |
| Werkelijk aangevraagd doel meldt passend opnieuw van na de fout | De late bevestiging kan het eigen doelbezit oplossen. Alleen passende nieuwe bronrapportage telt. |
| Normaal native doel meldt tweemaal gelijk na de fout, over minstens 60 seconden | Onzeker eigen beheer kan veilig losgelaten worden en de eigen bekende ACK-fout worden opgelost. De oude aanvraag/stabiliteitskandidaat wordt niet als uitgevoerd behandeld. |
| Oud, restored, ontbrekend of ongeldig tank-/doel-/beschermingsbewijs | Read-only wachten en automatisch opnieuw controleren. Geen blind foutwissen of opnieuw schrijven. |
| Native doel is betrouwbaar vastgesteld, maar boilerwachttijd loopt | Andere veilige lasten kunnen onder hun gewone voorwaarden verder. Alleen de boiler wacht lokaal op een eventuele nieuwe poging. |
| Nieuwe actuele boilerpolicy is toegestaan en wachttijden zijn voorbij | Een latere gewone regelronde kan een nieuwe actuele doelopdracht vragen; dit is geen replay van de mislukte aanvraag. |

Een volgende gewone beleidsbeoordeling mag alleen na een nieuwe P1-rapportage, met verse PV en huidige prioriteiten, reserves, serialisatie, doelgrenzen, eigendom en fabrikantbescherming een nieuwe boilerpoging kiezen. Fouten geven begrensde wachttijd: 300 seconden na de eerste, 900 na de tweede en 3600 vanaf de derde; bij herhaling bovendien hoogstens één nieuwe poging per uur. De bestaande ingestelde rust voor optionele verhogingen sinds een echte doelopdracht, standaard 1800 seconden, blijft gelden. Betrouwbaar vastgesteld native doel laat andere veilige lasten doorwerken terwijl uitsluitend de boiler nog haar herprobeerwachttijd afwacht. Journal en foutreeks blijven over herstart behouden; herstart omzeilt onzekerheid of wachttijd niet.

Pauze, Alleen bekijken en bewuste dashboardkeuzes blijven gelden. Automatisch bronherstel maakt geen nieuwe globale Auto-keuze en wist geen onbekende fout, handmatige pauze of actieve/onbekende fabrikantbescherming. Alleen expliciet bekende foutsoorten en de nauw begrensde herkenning van de oudere bevestigingsfout krijgen dit herstelpad.

## Optionele handmatige boilercontrole

Onbekende foutsoorten, een gewijzigde koppeling, bewuste handmatige boilerpauze en ongeldige of actieve bescherming blijven beschermd. De gerichte handmatige controle blijft een optionele fallback: in Automatisch regelen **Pauzeren voor boilercontrole**, daadwerkelijk bevestigde **Pauze**, daarna **Boilercontrole afronden** met de bestaande voorwaarden. Alleen bekijken mag hetzelfde pad gebruiken. Geen pending opdracht, verse tank-/doelrapportage en bekende inactieve bescherming blijven vereist. Geslaagde review schrijft geen temperatuur en geeft een zichtbaar resultaat; vervolgens kan je gewone Auto kiezen. De generieke toestelfoutreset wist geen boilerfout en geeft bij alleen DHW de juiste gerichte instructie in plaats van vals succes.

Wacht bij een handmatige fallback tot de echte modus Pauze is; een klik of lopende modusaanvraag is geen bevestiging. Een mislukte Pause-aanvraag of beoordeling toont haar precieze reden. Het gewone automatische herstel vraagt deze handmatige route niet. Een direct generiek resetverzoek bij alleen DHW geeft de instructie voor het gerichte boilerpad in plaats van onterecht succes.

## Resterende controlefouten in Home Assistant Meldingen

Echte resterende fouten waarvoor gebruikerscontrole nodig is verschijnen ook in Home Assistant Meldingen als SolarPilot: controle nodig. Deze afzonderlijke melding bundelt de betrokken onderdelen, wat er fout is en waar je in SolarPilot de gerichte controle uitvoert. Zij omvat echte gewone toestel-/overdrachtfouten, klimaatopdrachtfouten, batterijopdrachtfouten, interne foutpauzes en boilerfouten waarvoor echte gebruikersbeoordeling nodig blijft. Een bewust uitgeschakelde boilerautosturing of normale handmatige keuze is op zichzelf geen controlefout. De inhoud wordt alleen bij een werkelijke verandering bijgewerkt; na oplossing wordt de melding verwijderd. Korte gewone automatische boilerhercontrole, tijdelijke bronwacht/toestelisolatie, fabrikant-hygiëne, een bewust gekozen Pauze of normale handmatige dashboardbediening veroorzaken geen nieuwe controlemelding. Meldingtransport dat tijdelijk faalt mag de regelaar niet laten vastlopen. Deze foutmelding staat los van leer-/voorkeursvragen en vraagt geen terugkerende handmatige klik voor automatisch herstel.

Open **Home Assistant → Meldingen → SolarPilot: controle nodig**. Volg de genoemde plek en gerichte actie: Overzicht/Sanitair warm water voor boilercontrole, Overzicht/Toestellen voor gewone toestelfouten, Warmte & comfort/Ruimteklimaat voor de betreffende zone en Batterij voor batterijcontrole. Bij een interne fout bekijk je eerst de genoemde SolarPilot-foutregel onder HA Instellingen/Systeem/Logboeken. Een onbekende bron wordt niet met een algemene reset of extra proefopdracht opgelost. De melding blijft gericht op echte controlefouten, zonder herhaalde melding bij iedere gewone regelronde.

Een echte bronconfiguratiefout meldt welke koppelingen, exclusieve vermogensmeting of eenheid je onder Toestellen → Toestellen beheren moet controleren. Controle afronden herstelt geen verkeerde configuratie. Een werkelijk actieve dubbele regeling krijgt de melding Dubbele regeling actief: kies één regelaar en schakel de oude regeling zelf uit of pas haar aan. SolarPilot schakelt een andere regelaar niet automatisch uit. Tijdelijke bronwacht blijft automatische dashboardinformatie.

Blijft een bekende automatische boilerbevestigingsfout minstens vijftien minuten wachten op nieuwe bronrapportage of een betrouwbare bevestiging van het actuele doel, dan vraagt dezelfde stabiele HA-controlemelding de toestelverbinding en het werkelijk gemelde doel te controleren. De automatische hercontrole blijft lopen; hiervoor hoef je geen foutreset of boilercontrole uit te voeren. Na herstel verdwijnt de melding. Vroege gewone bronwacht, de zestigseconden-bewijscontrole, een herprobeerwachttijd op zichzelf en native fabrikantbescherming veroorzaken dit bericht niet. Ongewijzigde inhoud wordt niet iedere regelronde opnieuw gemeld.

## Wat wordt bij een mislukte doelopdracht bewaard?

SolarPilot bewaart één laatste begrensd diagnose-record van de mislukte boileropdracht, ook na beoordeling: het werkelijk aangevraagde doel, het laatst daadwerkelijk gemelde doel, tijdstip en bevestigingswachttijd, plus de waargenomen fout-/wachtreden. De diagnose helpt het verschil tussen voorstel, versturen en rapportage te volgen. Ontbrekend bewijs blijft onbekend; een oude aanvraag wordt niet alsnog als bevestiging gebruikt.

Bij dezelfde koppeling blijft dit bewijs over herstart beschikbaar zonder een oude opdracht opnieuw uit te voeren. Dit diagnose-record verleent geen opdrachtrecht: automatisch herstel gebruikt een afzonderlijk persistent journal en foutreeks. Dit voegt geen onbeperkt archief of gewijzigde meetbewaring toe. Gebruik voor een terugkerende fout de actuele kaartvoorwaarden en **Export → Export samenstellen**, of de bijbehorende lokale SolarPilot-foutregel. Privé-analyses blijven privé; publiceer ze niet op GitHub.

Naast het laatste diagnose-record bewaart de bestaande lokale onderzoeksregistratie nieuwe boilerfout- en herstelgebeurtenissen met een kopie van aangevraagd/gemeld doel, wachttijd en soort beoordeling. Daardoor kan een nieuwer laatste record het eerdere gestructureerde spoor binnen de werkelijk beschikbare onderzoeksperiode behouden. Deze gebeurtenissen vallen onder de bestaande maximaal zeven dagen en vaste aantallimieten; er is geen onbeperkt archief of aanvulling achteraf. Een fout in deze aanvullende registratie mag de regelaar niet laten vastlopen.

De getoonde fout bewijst niet waarom de echte warmtepomp of haar cloudkoppeling een doel niet bevestigde. Een doelrapportage in HA is evenmin onafhankelijke fysieke bevestiging van compressorbedrijf of vatopwarming.

## Behouden bevestiging en regeling

Voor de exact geregistreerde `aquarea`- en `panasonic_cc`-tankdoeladapter blijft een onmiddellijke lokale optimistische echo onvoldoende. Een passende werkelijk nieuwe doelrapportage van na minstens tien seconden is nodig. De bestaande opdracht-timeout van 180 seconden, bronversheid, eigendom en fabrikant-/handmatige bescherming worden niet verkort of versoepeld. Alleen het bekende automatische herstelpad mag bewezen post-foutdoelrapportage gebruiken om de specifieke eigen bevestigingsfout op te lossen; onbekende fouten en handmatige bescherming blijven gelden.

Extra warm water behoudt 3000 W werkelijk bruikbaar overschot, stabiliteit, opdrachtrust en 3200 W elektrische raming. Lager geplaatste eigen onderbreekbare lasten mogen alleen na bevestigde UIT en nieuwe metingen veilig wijken; afwas, ruimteklimaat en Wallbox blijven beschermd. De bekende sterilisatieplanning is informatie; werkelijke gekoppelde bescherming blijft gelden.

Zonne-AUTO behoudt 2500 W restoverschot gedurende 60 seconden en nieuwe P1/PV; bevestigde eigen zonne-AUTO houdt vanaf 2000 W onder de bestaande gedeelde-warmtepompgrenzen. Ruimtedoelen, AUTO/UIT-overrides, passende comfort-/programmacontrole, minimumtijden en elektrische/fabrikantbescherming blijven gelden. Geen directe HEAT/COOL, Force DHW, Powerful, extra APP-aanvraag of Wallboxwrite.

De uitgebreide overzichtsuitleg, energiekleuren, leren-schakelaar-/sensor-Recorderuitsluiting en gedeelde presentatiecache blijven behouden. Volledige actuele attributen, eigen modelopslag en werkelijk beschikbare export blijven bestaan met de bestaande bewaartermijnen. Warm water en ruimteverwarming/koeling wisselen elkaar af op één warmtepomp: één gezamenlijke vermogensmeting, zonder parallelle som.

**Na herstart automatisch hervatten** blijft standaard Aan, via de gewone bestaande guards. Alleen bekijken, eerste installatie, interne fout-/verwijderpauzes en echte opdracht-/boilerbeoordeling blijven beschermd. De enige volledige actuele regeling staat in `ACTUELE_WERKING.md` en op **SolarPilot → Uitleg**.

## Bewijsgrenzen en rollback

De definitieve lokale softwaregate behaalt **3814 geslaagde tests in 46,62 s**, inclusief 184 nieuwe regressies. Actuele guidehash `40c0493c856ad3cf`, 441 hulpvelden. Alle lokale bron-/document-/syntaxchecks zijn groen; de eigen CI, release en asset-/pakketcontrole volgen afzonderlijk na upload. Werkelijke software- en publicatiestatus staan in `TESTRESULTATEN_BETA61.md`. Geen live Home Assistant-, telefoonapp- of fysieke toestelacceptatie in deze werksessie. Een release bewijst geen daadwerkelijke doelacceptatie, compressoractie of vatopwarming.

Voor rollback herstel je de onveranderlijke beta.60-release of een passende volledige back-up, herstart Home Assistant en open je de app/webpagina opnieuw. Beta.60 behoudt haar uitgebreide uitleg en leren-schakelaarcorrectie, maar mist het nieuwe gerichte boilercontrolepad en foutdiagnosespoor. Haar generieke controle verhelpt geen boilerfout en zij mist de nieuwe automatische hercontrole en begrensde foutwachttijden. Wil je bewust gepauzeerd blijven, zet **Na herstart automatisch hervatten Uit** en kies **Pauze** vóór de herstart; laat beschermde cycli afwerken. Programmabestanden herstellen eerdere opslag niet vanzelf; gebruik voor exact herstel een passende volledige back-up. Geen fysieke proefopdracht om update of rollback af te dwingen.
