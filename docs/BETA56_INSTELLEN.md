# SolarPilot 1.0.0-beta.56 — instellen en controleren

Beta.56 laat de extra warmwaterbuffer vanaf **3000 W** bruikbaar overschot starten, maakt start- en wachtredenen duidelijker, herstelt onterechte klimaathervatting door ongeschikte temperatuurtrends en levert grote analyses als gecomprimeerde lokale download. Op **Overzicht → Wat gebeurt er en waarom?** staan per toestel of regeling de stand, de actuele reden en de laatst vastgelegde actie. Technische bron- en opdrachtgegevens staan achter **Details**.

## Bronbasis en gegevensbehoud

De codebasis en rollbackbasis zijn de gepubliceerde beta.55 op commit `83dda3b820b913ae191aedd9d3628c10eb342a68`, tree `105c808dcaebb88a45319bd84453102c29b9a4ce`. De onveranderlijke [beta.55-release](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.55), workflow `37308059878` en alle vier gepubliceerde assets zijn gecontroleerd; beide ZIP-pakketten zijn inhoudelijk tegen de gepubliceerde bron vergeleken. Dit is basisbewijs en geen beta.56-publicatiebewijs.

Updates zijn cumulatief. Koppelingen, centrale prioriteit, geldige modellen en historiek, APP-aanvragen, dashboardoverrides en opdrachtbescherming blijven behouden. De oude effectieve extra-DHW-drempel van 3500 W wordt met een éénmalige marker naar 3000 W omgezet; andere waarden blijven behouden. Deze update vraagt geen algemene leerreset, nieuwe Wallbox-toestemming of wijziging van het normale boilerdoel.

## Upgrade

1. Maak een actuele volledige Home Assistant-back-up en bewaar de gecontroleerde beta.55-release.
2. Laat beschermde afwas- of andere cycli afwerken. Gebruik geen STOPRESET voor de update.
3. Installeer exact `1.0.0-beta.56` via HACS of vervang uitsluitend `custom_components/solar_pilot` met het gecontroleerde lokale pakket. Behoud bestaande `userfiles` en Home Assistant-opslag.
4. Herstart Home Assistant volledig. Herlaad de webpagina; stop op Android de Home Assistant-app volledig en open haar opnieuw, of ververs op iOS de weergave.
5. Controleer backendversie en geladen kaart afzonderlijk. Open **Uitleg** en controleer beta.56 en de actuele regel-hash. Een download of manifestnummer bewijst geen geladen kaartcode.

SolarPilot registreert de frontend zelf. Een extra Lovelace-resource, www-bestand of dashboard-YAML is niet nodig. De uitgevoerde softwaregate en bewijsgrenzen staan in `TESTRESULTATEN_BETA56.md`.

## Extra warm water: drempel en uitvoering

Controleer onder **Warmte & comfort** de ingestelde overschotdrempel: de standaard is nu 3000 W en exact 3000 W telt mee. Dit is werkelijke restinjectie; batterijontlading, onbekend verbruik, huisreserve en hogere prioriteiten blijven volgens de bestaande kern-/allocatievoorwaarden afzonderlijk verwerkt. De uitvoeringsdetails tonen de werkelijk getoetste ruimte. Totale PV-productie of vrijmaakbaar Wallboxvermogen vervangt geen echte restinjectie. Het afzonderlijk geschatte opwarmvermogen blijft standaard 3200 W; fase- en piekgrenzen worden niet verruimd.

De extra buffer houdt zijn gewone voorwaarden: module ingeschakeld en vrijgegeven, **Automatisch regelen**, betrouwbare bronnen, geldig native doelbereik, standaard vijf minuten zonnestabiliteit, standaard dertig minuten sinds de laatste werkelijk verstuurde doelopdracht en geen blokkerende andere opdracht. Stabiliteit en opdrachtrust zijn afzonderlijke tijden; blijvend geldig zonnebewijs hoort geen voltooide stabiliteitscontrole opnieuw te laten beginnen. Actieve/onzekere koeling, relevante ruimteactie, hygiëne, handmatige functies en overige bescherming blijven leidend.

Een eenmaal bewezen door SolarPilot beheerde hoge fase kan onder de afzonderlijke hysterese blijven werken: bij 3000 W start en 300 W hysterese is de gewone vasthouddrempel circa 2700 W. Een nog niet toegepaste verhoging krijgt dat lagere startrecht niet. Echte netafname en koeling behouden hun snellere begrenzing.

De kaart toont de **werkelijke uitvoeringsreden** met afzonderlijke voorwaarden en resterende tijden. Houd drie waarden apart: **SolarPilot-voorstel**, **gemeld Panasonic-doel** en **gemeten tanktemperatuur**. Een voorstel van 60 °C met gemeld doel 50 °C is nog geen uitgevoerde verhoging. Als het gemelde doel al 60 °C is maar de tanktemperatuur lager blijft, is het doel wel hoog; de werkelijke opwarming moet Panasonic nog uitvoeren. Dit bewijst geen SolarPilot-eigendom of compressorstart. Verstuur geen extra proefopdracht om een teller te laten verdwijnen.

## Maandag: fabrikant-hygiëne blijft beschermd

De standaard geplande sterilisatie is maandag om 12:00. SolarPilot beschermt die planning vanaf vijftien minuten ervoor tot drie uur erna: **11:45–15:00**. Binnen dat ingestelde venster kan de extra zonnebuffer dus wachten ondanks voldoende zon en uitgeschakelde ruimteverwarming/koeling. De uitvoeringsreden noemt de bescherming en het einde van een bepaalbaar venster.

Dit is een beschermingsvenster, geen bewijs dat Panasonic werkelijk drie uur steriliseert en geen SolarPilot-opdracht om de sterilisatie te starten. Een actieve native hygiënebron houdt zelfstandig bescherming, ook na het geplande venster. Verlaag of schakel de fabrikantbescherming niet uit om de luxe-buffer eerder te laten starten.

## Klimaat: zelfstandig AUTO/UIT met bruikbaar bewijs

Laat per zone **Handmatig bedienen: Uit** staan voor autonome AUTO/UIT-regeling. Aan met **AUTO / UIT** bewaart de expliciete handmatige keuze over herstarts. Terugkeer naar automatisch wist uitsluitend die override en geeft zelf geen opdracht of foutreset. Externe native wijzigingen, vaste HEAT/COOL, bronproblemen en pending/onzekere opdrachten behouden hun bescherming.

Controleer het **Werkelijk Panasonic-programma**. Een lage temperatuur geeft geen autonome AUTO-vraag bij COOL/AUTO_COOL; een koelvraag geeft die evenmin bij HEAT/AUTO_HEAT. De zone blijft dan UIT met een duidelijke reden. Onbekend of onbetrouwbaar programmabewijs laat een nieuwe autonome AUTO-start wachten. Een expliciete handmatige dashboard-AUTO-keuze blijft een bewuste gebruikersopdracht met de overige bron-/opdrachtbescherming.

De optionele koppeling **Werkelijk Panasonic-programma** kan leeg blijven bij de ondersteunde native Aquarea-integratie. SolarPilot controleert de exacte entry, het apparaat en de zone en wacht op een nieuwe geslaagde coordinatorupdate na het koppelen. Een oud setupbeeld of optimistische schrijfmelding bewijst het programma niet. De rapportage blijft maximaal vijf minuten geldig, of korter bij een strengere ingestelde bronversheid; er komen geen extra cloudopvragen bij. Andere adapters kunnen een gecontroleerde actuele sensor/select/climate-bron koppelen met exacte waarden `heat/heating/auto_heat`, `cool/cooling/auto_cool` of `heat_cool`. Een ruimtewaarde AUTO, algemene PUMP/WATER-taak of buitenweer volstaat niet.

Na een bewezen eigen SolarPilot-UIT kan de native bron alleen OFF melden. Hervatten kan uitsluitend de vooraf bewezen verwarm-/koelrichting gebruiken bij dezelfde koppeling, eigen bevestigde UIT en nieuwe betrouwbare native OFF. De werkelijk huidige stand blijft OFF; de eerdere richting is opgeslagen programma-intentie. Nieuwe echte HEAT/COOL-terugmelding vervangt haar. Onbekend, oud of onbetrouwbaar bewijs en een willekeurige handmatige UIT leveren dit recht niet.

SolarPilot verstuurt Home Assistant **AUTO / UIT** en kiest geen directe HEAT/COOL-opdracht. De onderliggende Panasonic-integratie bepaalt de vertaling naar het toestel en kan daarmee ook het globale programma wijzigen. Bij de ondersteunde Aquarea-adapter kan HA AUTO naar globale AUTO en UIT naar globale OFF worden vertaald. Het bestaande verwarmings-/koelprogramma behouden is daardoor geen gegarandeerd fysiek effect. Controleer de werkelijk gemelde stand en het programma na normale opdrachten; een doelrapportage alleen bewijst die uitkomst niet.

Een temperatuurtrend uit verwarmen, koelen of een gemengd interval mag niet als passieve ontwikkeling tijdens UIT worden gebruikt. Een bruikbare passieve trend vraagt passende verse interval-eindpunten met idle/UIT, dezelfde relevante bronnen en hetzelfde doel. De actuele richting gebruikt huidig betrouwbaar buitenbewijs; een later forecastgemiddelde is geen bewijs van huidige verwarm-/koelvraag. Forecasts blijven beschikbaar voor het afzonderlijke voorspellende pad met voldoende relevant leer- en validatiebewijs.

Een zachte nieuwe vraag vanuit UIT moet standaard **tien minuten** aanhouden voordat AUTO wordt gevraagd. Hard comfortherstel, onderbouwde dringende voorspellende behoefte en een expliciete dashboardkeuze houden hun bestaande pad. De bevestiging vraagt na de termijn ook een werkelijk nieuw native bronrapport. Bronverlies, normaal bereik, geen vraag, richtingwisseling, native gebruikerswijziging, configuratiewijziging of herstart beëindigt de kandidaat. Deze tijd vervangt geen minimum aan-/uittijd of opdrachtbevestiging en is geen compressorlooptijd.

Bij een pending AUTO-opdracht is een nieuwe terugmelding van de oorspronkelijke UIT-stand niet automatisch een nieuwe externe gebruikerskeuze. SolarPilot wacht op passende AUTO-bevestiging of timeout. Een expliciete gebruikers- of andere automatiseringsopdracht om UIT te zetten behoudt wel haar bescherming. Dit voorkomt een onterechte twaalfuurhold, zonder een onzekere opdracht te herhalen.

De nieuwe diagnose bewaart een begrensd beslisspoor per zone met meetwaarden, bronleeftijden, regel- en wachtredenen en opdracht-/terugmeldingsuitkomsten. Veranderingen worden vastgelegd, met maximaal eens per vijftien minuten een punt bij een gelijkblijvend besluit en maximaal 128 lokale spoorrecords. Een oudere vijfminutenanalyse kan een korte actie missen; nieuwe logging vult dat verleden niet achteraf in. Het huidige softwareherstel bewijst daarom niet afzonderlijk de oorzaak van iedere eerdere AUTO-actie.

## Zeven dagen exporteren

Kies **Export → Export samenstellen → 7 dagen**. Een Home Assistant-beheerder maakt één lokaal **JSON.GZ**-bestand. De WebSocket draagt alleen kleine downloadinformatie; de volledige JSON wordt buiten de eventloop direct gecomprimeerd en via een geauthenticeerde HTTP-download opgehaald. Alleen dezelfde ingelogde beheerder heeft toegang. Na succesvolle ontvangst wordt het serverbestand direct verwijderd; bij afbreken blijft het maximaal tien minuten beschikbaar en wordt het daarna of bij afsluiten opgeruimd. Maximaal twee bestanden kunnen tegelijk klaarstaan of worden gemaakt.

De nieuwe downloadroute heeft geen 16 MB-grens op de uitgepakte JSON en verkort de gewenste periode niet om een bericht te laten passen. Het bestand bevat alle werkelijk beschikbare gegevens binnen de bestaande bewaartermijnen en aantallimieten. Ontbrekende/offline perioden blijven zichtbaar; er is geen terugwerkende Recorder-import. JSON.GZ is gewone JSON in gzip: uitpakken verandert de onderzoeksinhoud niet. Alleen een oudere client die de oude contentaanroep gebruikt behoudt de vroegere 16 MB-berichtgrens; open na de update de actuele kaart opnieuw.

Nieuwe meetpunten, snelle regelpunten, gebeurtenissen en bronwijzigingen bewaren de geladen SolarPilot-versie. Oude records zonder stempel blijven versie onbekend. De release bovenaan benoemt de exportsoftware en is geen bewezen versie van alle oudere meetpunten. Ook de nieuwe warmwateruitvoeringsvoorwaarden en het klimaatsbeslisspoor gaan mee voor zover geregistreerd.

Consistente pseudoniemen en bestaande privacyfilters blijven behouden. Namen zijn standaard afgeschermd; gebruikspatronen en tijdstippen blijven gevoelig. Controleer vóór delen en publiceer analyses nooit op GitHub. De export verstuurt geen toestelopdracht en uploadt niets automatisch. Voor de actuele oorzaak van een ongewenste AUTO-actie of wachtende zonnebuffer is deze nieuwe analyse bruikbaarder dan alleen een screenshot.

## Teststatus en rollback

De uitgevoerde beta.56-softwaregate en afzonderlijke publicatie-/pakketcontrole staan in `TESTRESULTATEN_BETA56.md`. De geladen backend/kaart, passende nieuwe doelterugmelding en fysieke tank- of klimaatrespons blijven afzonderlijke acceptatiestappen. HA-API-/DOM-doubles bewijzen softwaregedrag; deze werksessie voert geen live Home Assistant- of fysieke toestelactie uit.

Rollback: **Pauze → beschermde cycli afwerken → onveranderlijke beta.55-release of gecontroleerde volledige back-up herstellen → Home Assistant herstarten → webpagina/app opnieuw openen → backend/kaart, bronnen, eigendom en beveiligingen controleren**. Beta.55 behoudt de eerdere forecast-, PV-kalender-, leerbron- en AEG-READY-correcties, maar mist de nieuwe klimaattrend-/vraagbevestiging, uitvoeringsdiagnose en grote gecomprimeerde download. De gewone oude client kan grote exports weer weigeren. Een teruggezet programmabestand herstelt niet vanzelf een gemigreerde opgeslagen instelling; controleer de effectieve overschotdrempel of herstel de bijbehorende volledige back-up. `OVERDRACHT.md` beschrijft altijd de huidige bron.
