# Changelog

## 1.0.0-beta.59 — 2026-10-06

- Voorkomt te grote Recorder-attribuutpakketten door ontbrekende zware model-/leer-/analyseattributen uitsluitend van de herhaalde HA-historiekkopie uit te sluiten. De volledige actuele sensorinhoud, eigen opslag en directe exportmodellen blijven behouden; geen data-/leerreset of gewijzigde bewaartermijn. Extra schijfruimte vergroot de 16 KiB-limiet per Recorder-pakket niet.
- Hergebruikt EMS-/leerpresentatie per publicatieronde voor sensorupdates en bouwt aangevraagde pakketten één keer vóór listeners. Controllers en analyse blijven directe actuele overzichten gebruiken; minder herhaald opbouwwerk zonder nieuwe regelvrijgave.
- Herstelt een reproduceerbare `NameError` in de warmwater-avondvoorraadvoorspelling: `_comfort_forecast` gebruikte `timedelta` zonder import. De gewone zonnige forecast-/voorraadroute kan daardoor weer berekenen zonder deze interne foutpauze. Een live screenshot zonder traceback bewijst de specifieke oorzaak niet; de echte runtime-/opdrachtfoutbescherming blijft intact.
- Geeft de actuele tegels **Zonnepanelen** en **Net** een kleurenschaal met gekleurde rand, zachte achtergrond en horizontale kleurverloopindicator. PV loopt van rood naar groen ten opzichte van de ingestelde AC-omvormergrens; injectie is groen, nul lichtgroen en grotere netafname geel/oranje/rood.
- Gebruikt de positieve ingestelde netafnamegrens of anders de omvormergrens alleen als visuele importreferentie. Geen Wp/forecast als productieschaal en geen nieuwe vermogensvrijgave. Tekst, eenheden en afname/injectie blijven leesbaar; oude, ontbrekende of ongeldige bronnen blijven grijs.
- Voegt een kleine betekenislegenda toe; de blauwe activiteitstatus blijft afzonderlijk. De kaart neemt read-only bronbewijs en schaalreferenties over, zonder nieuwe toestelactie, configuratie- of rangordemigratie. Automatisch hervatten uit beta.58 en alle eerdere regelingen blijven behouden.
- Werkt versie, canonieke HA-uitleg, releasegebonden hulp, installatie/rollback, testverslag en overdracht samen bij. Eigen gate: `docs/TESTRESULTATEN_BETA59.md`; de gecontroleerde gepubliceerde beta.58 is bron- en rollbackbasis.

## 1.0.0-beta.58 — 2026-10-06

- Voegt **Na herstart automatisch hervatten** toe bij de dashboardmodi en als native Home Assistant-schakelaar, standaard Aan. Een gewone opgeslagen Pauze vraagt na HA-herstart of integratieherlading Automatisch regelen via de bestaande reconciliatie en bron-/opdracht-/DHW-controles. Met Uit blijft Pauze staan; opgeslagen solar behoudt haar gewone herstelpad. Alleen bekijken en eerste installatie krijgen geen automatische activering.
- De voorkeur wijzigen verandert de huidige modus niet. Een nieuwe Pauze-keuze annuleert een nu wachtende hervatting; bij de volgende herstart geldt de voorkeur weer. De kaart onderscheidt automatische wachtreden, blijvende Pauze en echte vereiste controle.
- Bewaart interne fout-/verwijderpauzes met oorzaak en reden; voorbereiden van verwijderen en bekende echte opdrachtfouten of boilerreview worden niet automatisch gepasseerd. Een gezonde volgende regelronde wist een interne foutreden niet. Oudere Pause zonder reden wordt alleen via het gewone beveiligde pad beoordeeld; er wordt geen vroegere pauzeoorzaak verzonnen.
- Behoudt alle beta.57-warmwater-, klimaat-, voorrangs-, shared-HP-, export- en activiteitfuncties, geldige leerdata, koppelingen, APP-aanvragen en dashboardoverrides. Geen oude fysieke opdracht herhalen, algemene fout-/leerreset of nieuwe rangordemigratie. Code, hulp, actuele uitleg, installatie/rollback, testverslag en handoff horen samen bij beta.58. Eigen gate: `docs/TESTRESULTATEN_BETA58.md`; gepubliceerde beta.57 is basis en rollback.

## 1.0.0-beta.57 — 2026-10-06

- Maakt de bekende sterilisatieplanning informatief: geen klok-only blokkering van een gewoon 60 °C-tankdoel. Panasonic kan intern naar 62 °C gaan zonder het normale HA/display-doel te wijzigen. Echte gekoppelde hygiene/manual/unknown en overige fabrikant-/opdrachtbescherming blijven gelden; geen sterilisatieinstelling of Force-DHW-opdracht.
- Migreert bij een geconfigureerde boiler extra DHW éénmalig achter Wallbox en alle afwasrijen, vóór gewone flexibele lasten. Marker57 bewaart latere expliciete saves. Opgeslagen EV-toestemming blijft behouden maar is onder Wallbox niet effectief. Nieuwe gewone toestellen blijven onderaan.
- Laat extra warm water veilige lager geplaatste eigen onderbreekbare lasten met verse echte meting vrijmaken, pas na prospectieve stabiliteit, bevestigde UIT, nieuwe P1 en verse PV. Geen stopintentie als gratis watts; minimumlooptijd/manual/boost/deadline beschermd. Geen afwascyclus, klimaatlast of Wallbox voor extra DHW stoppen.
- Voegt afzonderlijke zonne-AUTO-beschikbaarheid toe vanaf 2500 W werkelijk restoverschot gedurende 60 s plus nieuwe P1/PV. Geen modelscore of temperatuurvraag vereist; verse bekende programmastand en overige guards blijven. Alleen bevestigd eigen zonne-AUTO houdt vanaf 2000 W met eenmaal verse gedeelde warmtepompvraag, begrensd door echte PV. Dashboard/externe rust, minimum aan-/uittijden, pending/fout en legacyoptout behouden hun betekenis.
- Begroot ruimteklimaat en tapwater als één fysieke warmtepomp: werkelijk P1-verbruik eenmaal, gezamenlijke prospectieve taakreserve en expliciete meterscope hele warmtepomp/exclusieve tank. Geen gedeelde meter als specifieke DHW-opwarming tonen; onbekende/oude stroom geeft geen add-back. Na fysieke verandering nieuwe P1, verse PV en meetrust.
- Maakt bevestigde activiteit op het hoofdscherm grafisch zichtbaar met doorlopend blauw. AUTO-beschikbaarheid of een werkelijk hoger gemeld tankdoel is gestippeld blauw; voorstellen, globale HP-watts of oude bronnen geven geen fictieve warmteactiviteit.
- Behoudt beta.56-drempel/stabiliteit, passieve trends, comfortbevestiging, versiegebonden diagnoselog en gecomprimeerde privé-export. Code, optiehulp, actuele uitleg, installatie/rollback, testverslag en overdracht worden samen bijgewerkt. Definitieve gate: `docs/TESTRESULTATEN_BETA57.md`; gecontroleerde beta.56 is rollbackbasis.


## 1.0.0-beta.56 — 2026-10-05

- Verlaagt de standaard extra-DHW-startdrempel naar 3000 W en accepteert de exacte grens. Een éénmalige gemarkeerde migratie zet de oude standaard 3500 W om; afwijkende gebruikerswaarden blijven behouden. De afzonderlijke geschatte opwarmbelasting van standaard 3200 W, fysieke grenzen, reserves en Wallboxbeleid worden niet verlaagd.
- Maakt de actuele DHW-uitvoering en haar voorwaarden zichtbaar naast het beleidsvoorstel. Normaal doel, gemeld hoog Panasonic-doel en gemeten tanktemperatuur blijven afzonderlijk; een gemeld 60 °C-doel bewijst geen eigen opdracht, compressorstart of al warm vat. Fabrikant-hygiëne blijft beschermd, ook zonder actieve ruimtekoeling; de standaard maandagplanning begint om 12:00 met drie uur SolarPilot-bescherming.
- Toetst iedere nieuwe autonome AUTO-vraag aan het werkelijke Panasonic-programma. Lage kamertemperatuur start niet AUTO bij COOL/AUTO_COOL; koelvraag evenmin bij HEAT/AUTO_HEAT. Onbekend programma blokkeert nieuwe autonome AUTO met zichtbare reden. Een read-only observer controleert exacte Aquarea-entry/device/zone en een nieuwe geslaagde native update; een optionele expliciete programmabron is beschikbaar. HA AUTO/UIT kan door de onderliggende integratie globaal worden vertaald; er is geen garantie dat de programmakeuze ongewijzigd blijft.
- Voorkomt dat een actieve of gemengde ruimtetemperatuurtrend als passieve UIT-trend wordt gebruikt. Actuele richtingscontext gebruikt actueel buitenbewijs; later voorspeld buitenweer maakt geen huidige koel-/verwarmvraag. Bestaande zelfstandige comfortbewaking, relevant modelbewijs, gebruikersoverrides, minimumtijden en opdrachtbescherming blijven gelden.
- Onderscheidt bij pending AUTO een ongelabelde terugmelding van de bewezen oorspronkelijke UIT-stand van een echte nieuwe externe OFF-opdracht. Het journal bewaart de oorspronkelijke stand; expliciete gebruikers-/automatiseringsopdrachten blijven beschermd en oude onzekere journals blijven conservatief. Ongeldige DHW-rapportagetijden leveren een ontbrekende-bronreden in plaats van een afgebroken regelronde.
- Bewaart begrensde beslis- en opdrachtdiagnose per zone en de geladen versie op nieuwe meetpunten. Oude records zonder versiebewijs worden niet achteraf aan de huidige release toegeschreven. Dit onderbouwt latere diagnose en claimt geen bewezen oorzaak van een eerdere fysieke AUTO-actie.
- Levert grote analysebestanden als lokale gecomprimeerde JSON.GZ-download via een geauthenticeerde beheerderroute; de WebSocket draagt alleen de downloadinformatie. De volledige beschikbare geschiedenis binnen de bestaande bewaartermijnen blijft behouden, met dekking, bronprivacy en consistente pseudoniemen. Geen stille periodeverkorting of automatische upload.
- Behoudt alle beta.55-correcties, gebruikersinstellingen en geldige leerdata, read-only Wallbox, afwasbescherming en elektrische/fabrikantgrenzen. Code, actuele uitleg/hulp, installatie/rollback, testverslag en handoff worden samen bijgewerkt. De werkelijke beta.56-gates staan in `docs/TESTRESULTATEN_BETA56.md`; de gecontroleerde gepubliceerde beta.55 is de rollbackbasis.

## 1.0.0-beta.55 — 2026-10-05

- Scheidt de strikte dertigminutencontrole van actuele buitentemperatuur van de uurlijkse weersforecast. Een beschikbare correct gekoppelde °C-bron met bruikbare toekomstige curve blijft binnen de leeftijd van de laatste geslaagde forecastopvraag bruikbaar; de cachegrens is `max(1800 seconden, 2 × verversingsinterval)`, standaard twee uur. Een oudere weerstatusheartbeat wist niet uitsluitend daarom de curve.
- Behoudt de oorspronkelijke cacheleeftijd bij mislukte forecastopvragen; poging en succesvolle opvraag hebben afzonderlijke tijden. Ontbrekende/mislukte data krijgt begrensd na één minuut een nieuwe poging. Onbeschikbaar/restored, verkeerde eenheid, gewijzigde binding, ongeldige rapportagetijd, cacheverloop en ontbrekende opeenvolgende toekomstige dekking blijven beschermd. Een bewaard DHW-koeladvies toetst die geldigheid vóór hergebruik; een nieuwe succesvolle forecasttijd maakt de vijfminutencache direct opnieuw te beoordelen.
- Verankert ongedateerde native PV-bronnen voor vandaag/morgen/resterend aan hun werkelijke lokale rapportagedag en huidige-/volgende-uurtellers aan het verstreken uur. Oude rapporten verlopen bij middernacht of de uurgrens, inclusief het herhaalde wintertijd-uur, tot nieuw native bewijs terugkomt. Expliciet gedateerde curves en geldige opgeslagen leerdata blijven behouden; ontbrekende dekking wordt geen nulopbrengst.
- Verwerpt oude, restored, onbeschikbare en ongeldig/toekomstig gedateerde klimaatacties bij warmtepompclassificatie. Een idle/off-zone met een onbeschikbare tweede zone wordt zonder bewezen actieve richting onbekende warmtepompactiviteit, geen normale rustsample. PUMP blijft bewust onbekend voor gewone basislastleren, ook wanneer betrouwbare native idle de afzonderlijke DHW-guard vrijgeeft.
- Telt ongeldige P1/PV-metingen en stabilisatierust onder hun werkelijke basislastafwijsredenen (`site_source`/`settling`) in plaats van ze als onbekende warmtepompactiviteit te presenteren. Een geldige meting met onbekende warmtepompcontext blijft afzonderlijk beschermd; geen cosmetische herclassificatie of leerreset.
- Herkent een AEG die na een oude opgeslagen lopende cyclus met betrouwbaar actuele verbonden **Ready To Start** opnieuw gereed meldt. Alleen de oude cyclus wordt `end_unconfirmed`; een verbruikte aanvraag keert niet terug. Een volgende expliciete APP-overgang kan één nieuwe aanvraag maken. Onzekere attempted START, Running/Paused/Drying-/onbekende bronlocks en deurannulering blijven beschermd. De ingevulde maandagdeadline blijft leidend; het softwarepad maandag 08:30 → 10:00 claimt geen bewezen live APP-chronologie of fysieke start.
- Behoudt autonome zonebediening, dashboardoverrides, boilerbeleid, toestelisolatie, reserves, beschermde cycli en volledig read-only Wallbox. Een oude of semantisch onjuiste externe effectieve-sessiesensor vraagt installatiecontrole; native zonne-instelling alleen geeft geen nieuw sessiebewijs. PV-kalenderherstel claimt geen betere dagvoorspelling of nieuwe fysieke acceptatie.
- Code, actuele uitleg/hulp, installatie/rollback, testverslag en overdracht worden samen bijgewerkt. De werkelijke beta.55-softwaregate en afzonderlijke publicatie-/pakketstatus staan in `docs/TESTRESULTATEN_BETA55.md`; beta.54-resultaten worden niet als nieuw bewijs gebruikt. De rollbackbasis is de gecontroleerde gepubliceerde beta.54.

## 1.0.0-beta.54 — 2026-10-04

- Regelt de vrijgegeven Panasonic-ruimtezone afzonderlijk tussen AUTO en UIT. Een geldige native UIT-stand bij start is onder automatische zonebediening geen verplichte handmatige uitschakeling; er is geen voorafgaande handmatige AUTO-keuze nodig. Actuele temperaturen en passende comfortvraag blijven bruikbaar terwijl het thermische model nog leert.
- Voorkomt een permanente AUTO-keuze alleen wegens winter-/zomerweer. Iedere zone beoordeelt of de temperatuur zonder ruimtebedrijf veilig blijft en wanneer AUTO weer nodig is. Een warme ruimte die vanzelf naar het doel afkoelt krijgt niet alleen wegens koud toekomstig buitenweer een koelvraag.
- Voegt per zone dashboardbediening toe voor expliciet handmatig AUTO of UIT en terugkeer naar automatische regeling. Die bewuste override blijft bewaard over herstarts. Externe native wijzigingen krijgen tijdelijke bescherming; vaste HEAT/COOL, onzekere opdrachten en ontbrekende bronnen worden niet overschreven.
- Baseert voorspellende hervatting op de werkelijk geleerde relevante verwarm-/koelrespons en vertraging, binnen de echte opeenvolgende forecastdekking. Leerbewijs en voorspelfout blijven afzonderlijk; een sampletelling wordt geen 98% nauwkeurigheid. Een toekomstige hittegolf is zonder passend responsbewijs geen opdracht om nu de bouwschil te koelen. Panasonic kiest HEAT/COOL en het thermostaatdoel blijft behouden.
- Behoudt beta.53-toestelisolatie, reserves, beschermde cycli, boilerbeleid, bronversheid en opdrachtbevestiging. Code, actuele uitleg/hulp, installatie/rollback, testverslag en overdracht worden samen bijgewerkt. De definitieve volledige suite behaalt **2877 geslaagde tests in 30.62 s**, inclusief 206 nieuwe model-/runtime-/dashboard-/integratie-/servicegevallen. Syntax van 65 Python-productiemodules, vier JSON-bestanden en beide JavaScript-bestanden is groen, evenals publieke preflight, handoff, actuele uitleg en repository-/diffcontrole. Afzonderlijke publicatie-/pakketcontrole staat bij `docs/TESTRESULTATEN_BETA54.md`; eerdere publicatie geldt niet als beta.54-bewijs. Geen live Home Assistant- of fysieke klimaatacceptatie wordt geclaimd.

## 1.0.0-beta.53 — 2026-10-04

- Beperkt tijdelijke onbeschikbaarheid van een eerder beheerd toestel tot dat toestel. De overige beschikbare toestellen kunnen hun opgeslagen automatische modus hervatten zodra globale net- en veiligheidsbronnen geldig zijn; een ontbrekende status veroorzaakt geen blinde OFF of tweede START.
- Behoudt de eerdere beheerinformatie en controleert automatisch opnieuw. Betrouwbare terugmelding laat het toestel vanzelf terugkeren onder de bestaande deelname, prioriteit, minimumlooptijden, handmatige moduskeuze en bescherming van lopende cycli.
- Reserveert mogelijk onbekend of later toenemend verbruik conservatief naast het werkelijk in P1 opgenomen verbruik. Ontbrekende lastdata levert geen vrije vermogenscredit op. Echte opdrachtfouten, onzekere opdrachten en ongeldige globale bronnen blijven beschermd.
- Behoudt actieve elektrische fasebegrenzing bij ontbrekende of ongeldige actuele fasemetingen, ook met een aangeleerde fasekaart. Alle eerdere boiler-, paneel-, export-, klimaat- en veiligheidsreparaties blijven behouden. Actuele uitleg/hulp, installatie/rollback, testverslag en overdracht worden samen bijgewerkt. De definitieve volledige suite behaalt **2671 geslaagde tests in 24.56 s**, inclusief 113 nieuwe runtime-/reserve-/fase-/UI-/statusgevallen. Syntaxcontrole van 65 Python-productiemodules, vier JSON-bestanden en beide JavaScript-bestanden is groen, evenals publieke preflight, handoff, actuele uitleg en repository-/diffcontrole. Publicatie blijft afzonderlijk: `docs/TESTRESULTATEN_BETA53.md`; geen fysieke verbindingsreparatie of live toesteltest wordt geclaimd.

## 1.0.0-beta.52 — 2026-10-04

- Onderscheidt tijdelijke bronwacht van een echte opdrachtfout. Na oude, ontbrekende of onbeschikbare toesteldata toont de kaart een automatische broncontrole zonder misleidende Controle afronden-knop. Het bestaande opnieuw uitlezen en herstel blijft automatisch; verkeerde vereiste koppelingen vragen gerichte configuratiecontrole.
- Houdt echte opdrachtfouten, handmatige overname en onzekere opdrachten apart. Geen onzekere replay, reset bij een onbekende/aanstaande last, kortere bronversheid, gewijzigde minimumlooptijd of onderbreking van beschermde cycli.
- Leest de effectieve analyseconfiguratie en gekoppelde entiteitsbronnen ook uit read-only mappings. Voorkomt een onterecht niet-ondersteund configuratieblok en ontbrekende expliciete bronnen naast forecastmetadata; privacyfilters, bronlimieten en pseudoniemen blijven behouden.
- Behoudt alle eerdere boiler-, klimaat-, prioriteits-, paneel- en veiligheidsreparaties. Code, actuele uitleg/hulp, installatie/rollback, testverslag en overdracht worden samen bijgewerkt. De definitieve volledige suite behaalt **2558 geslaagde tests in 22.09 s**, met 37 nieuwe bronclassificatie-/UI-/mappinggevallen. Syntaxcontrole van 65 Python-productiemodules, vier JSON-bestanden en beide JavaScript-bestanden is groen. Publieke preflight, handoff, actuele uitleg en repository-/diffcontrole zijn groen. Publicatie blijft afzonderlijk: `docs/TESTRESULTATEN_BETA52.md`. Een diagnosecorrectie bewijst niet de specifieke fysieke verbindingsstoring of de oorzaak van een later screenshot zonder bijbehorende export.

## 1.0.0-beta.51 — 2026-10-04

- Registreert het zijbalkpaneel met `module_url`, gelijk aan de automatisch beschikbare kaartmodule. Voorkomt de klassieke/module-loadercombinatie en botsende globale declaraties bij klassieke lading van verschillende release-URL's.
- Houdt de eigen kaartcatalogusitems enkelvoudig bij herhaalde module-evaluatie en ruimt alleen eigen bestaande duplicaten op. De gedeelde catalogusarray, volgorde en inhoud van andere integraties blijven behouden; custom elements worden niet opnieuw gedefinieerd.
- Behoudt alle beta.50-boilerstabiliteit, opdrachtrust, uitvoeringswachtreden en eerdere toestel-/bron-/veiligheidsregels. Geen datareset, extra fysieke opdracht of veranderde toestemming. Actuele uitleg/hulp, installatie/rollback, testverslag en handoff worden samen bijgewerkt. De definitieve volledige suite behaalt **2521 geslaagde tests in 18.76 s**, inclusief tien nieuwe module-/frontendregistratiegevallen. Syntax- en releasecontroles zijn groen; de volledige browsergate is niet uitgevoerd. Details: `docs/TESTRESULTATEN_BETA51.md`; geen bewijsclaim voor de specifieke live HTTP-/WebView-oorzaak, geladen appkaart of fysieke toestelactie.

## 1.0.0-beta.50 — 2026-10-04

- Herstelt de herhaalde boilerstabiliteitscontrole tijdens de bestaande rust tussen doelopdrachten. Een voltooide kandidaat blijft geldig zolang het actuele zonne- en guardbewijs geldig blijft; werkelijk verloren zonnebewijs, koeling en te grote meetgaten behouden hun bescherming.
- Behoudt de minimumtijd van standaard 1800 seconden sinds de laatste werkelijk verstuurde doelopdracht, ook normaal herstel of verlaging. Een onuitgevoerd hoog voorstel krijgt geen eigendoms- of start-hystereserechten.
- Het overzicht en de warmwaterdetailkaart geven de actuele uitvoeringswachtreden voorrang op een gunstig beleidsadvies. Een gunstig zonneadvies verbergt de opdrachtrust of andere echte blokkering niet meer; voorstel, native doel en tanktemperatuur blijven afzonderlijk.
- Behoudt alle beta.49-instellingen, geldige leerdata en bron-, koel-, comfort-, ACK-, AEG-, prioriteits- en Wallboxregels. Actuele uitleg/hulp, installatie/rollback, testverslag en handoff worden samen bijgewerkt. De definitieve samengestelde suite behaalt **2511 geslaagde tests in 17.08 s**, inclusief 31 werkelijke Node VM-kaartweergaven. Syntax- en releasecontroles zijn groen; volledige browserproeven zijn niet opnieuw uitgevoerd. Details: `docs/TESTRESULTATEN_BETA50.md`; geen live installatie of fysieke opwarming geclaimd.

## 1.0.0-beta.49 — 2026-10-04

- Serialiseert pending batterijopdrachten met gewone laststarts/verhogingen, AEG-deadline-START, vermogensoverdracht en veilige klimaatvrijgave bij verwijderen. Nieuw P1-bewijs en de bestaande wachttijd blijven na batterijactie vereist; veilige reductie en beschermde cycli blijven behouden.
- Vereist verse passende batterijvermogenrapportage van ná de opdracht, duurzame intentie vóór actuatie en geldige actuele SoC. Neutrale verwijdering vraagt werkelijk neutraal vermogen én een neutraal numeriek doel; ontbrekende bronnen en fouten geven geen automatische retry. Ondersteunde input_number-actuatoren gebruiken hun juiste domein; gekoppelde Wallbox-actuatoren/scripts worden geweigerd.
- Behoudt ontbrekende forecasturen/staart als onbekend, zonder fictief nulbewijs in voorspelling of kwaliteit. Verstreken UTC-tijd voorkomt dubbele/overgeslagen planuren bij zomer-/wintertijd. Replay vraagt volledige werkelijke lokale dagen van 92/96/100 kwartieren en bewaart nulprijzen.
- Behoudt structuur, eenheden en enums bij consistente pseudonimisering van exportnamen, IDs en verwijzingen, inclusief korte en historische labels.
- Beveiligt setup/unload en startafbreking tegen achterblijvende callbacks of opslag van gedeeltelijk geladen gegevens. Ongeldige afzonderlijke pending-/optie-/archiefrecords blokkeren geldige andere records niet. Klimaatdeactivatie en zonebindingswijzigingen wachten ook bij een tijdelijk onbereikbare eigen coastzone.
- Vereist veilige vrijgave vóór overschakelen naar Alleen bekijken. Pauze geeft uitsluitend eigen coast of een passend bevestigd eigen numeriek batterijdoel terug; handmatige bediening/scripts blijven beschermd. Vervangende batterijdoelen verrekenen eigen gemeten flow, readonly/foutstromen en native actuatorgrenzen. Ontbrekend actueel PV-vermogen wordt geen thermische nulmeting.
- Behoudt alle beta.48-beschermingen, instellingen en geldige leerdata zonder algemene reset of nieuw actuatorrecht. Actuele uitleg, optieshulp, handoff, installatie/rollback en testverslag worden samen bijgewerkt. De definitieve samengestelde suite behaalt **2464 geslaagde tests in 13.90 s**, inclusief dertien werkelijke Node VM-klimaatkaartweergaven. Lokale release-/syntaxcontroles zijn groen; volledige browserproeven zijn niet opnieuw uitgevoerd. Details: `docs/TESTRESULTATEN_BETA49.md`; geen live installatie of fysieke toestelactie geclaimd.

## 1.0.0-beta.48 — 2026-10-03

- Wijzigt bewust het beleid voor handmatige OFF-zones: zij blijven uit tot de gebruiker zelf AUTO kiest, ook bij harde comfortoverschrijding, verlopen rusttijd, herstart of verwijderen. De oudere harde-comfortuitzondering vervalt; alleen bewezen eigen OFF/coast-zones mogen automatisch worden vrijgegeven.
- Herstelt klimaatopdrachtbeheer met per-zone persistent eigendom/bescherming en geen replay van pending of onzekere opdrachten. Een vertraagde AUTO-terugmelding na gebruikers-OFF die pending AUTO annuleerde herstelt geen automatische controle; expliciete gebruikers-AUTO blijft vereist. Ontbrekende/ongeldige ruimteactie wordt niet als idle-leerbewijs gebruikt.
- Beoordeelt coastzekerheid op de werkelijk benodigde voorspelde respons: passief en zon waar gebruikt, verwarm-/koelrespons plus bestaande reactievertraging bij relevante comfortgrens. Ontbrekende ongebruikte koelervaring blokkeert een voldoende geleerd verwarmingspad niet; de legacy volledige confidence blijft vergelijkingsinformatie.
- Maakt modelstatus, actuele relevante zekerheid en echte samples/dagen/episodes zichtbaar en benoemt winter-/zomerweer als context zonder actieve vraag te claimen. Winter-/zomercoast blijft standaard uit.
- Verwerpt restored, toekomstige en ongeldige operationele bronwaarden voor vermogen, Wallbox en boiler. Een onzekere AEG-START wordt alleen met een nieuwe betrouwbare fase-terugmelding van ná START opgelost. Handmatige toestelvraag kan een fout of interlock niet overrulen; bestaande minimumlooptijden en beschermde cycli blijven gelden.
- Laat ongeldige of meer dan 36 uur oude dynamische prijsbronnen terugvallen op het ingestelde vaste tarief en behoudt tijdposities bij ontbrekende prijsrijen.
- Voorkomt foutieve geleerde fasetoewijzing wanneer andere gemeten toestellen tijdens een gecontroleerde vermogensstap veranderen. Bij upgrade worden uitsluitend oude gecontroleerde fasewaarnemingen zonder dit isolatiebewijs niet hergebruikt; geldige passieve/nieuwe geïsoleerde waarnemingen, handmatige hints en instellingen blijven behouden. Ongeldige opgeslagen leerregels worden afzonderlijk overgeslagen zonder geldige andere gegevens te wissen.
- Behoudt beta.47-herstartherstel en bestaande actuatorgrenzen zonder algemene leerreset of nieuwe DHW-/AEG-/Wallboxopdracht. Werkt actuele uitleg, optieshulp, overdracht, installatie/rollback en testverslag samen bij. De definitieve samengestelde suite behaalt **2170 geslaagde tests in 8.72 s**, inclusief acht werkelijke Node VM-kaartweergaven; lokale release-/syntaxcontroles zijn groen. Volledige browserproeven zijn niet opnieuw uitgevoerd. Details: `docs/TESTRESULTATEN_BETA48.md`; geen live installatie of fysieke klimaatrespons geclaimd.

## 1.0.0-beta.47 — 2026-10-03

- Herhaalt gewone herstartcontrole automatisch wanneer eerder beheerde toestelbronnen later laden en hervat daarna de bewaarde gebruikersmodus. Die hervatkeuze blijft persistent; een bewuste latere Alleen bekijken-/Pauze-keuze vervangt haar. Minimumlooptijden beginnen bij de echte nieuwe waarneming.
- Laat een gewone boilerherstartcontrole modulelokaal automatisch afronden met verse temperatuur-, doel- en beschermingsdata, zonder oude doelopdracht te herhalen. Pending doelen vereisen een nieuwe rapportage na herstart en de bestaande adapterwachttijd; gewijzigd doel, echte fout en handmatige overname blijven beschermd.
- Lost uitsluitend een door herstart ontstane AEG-START-onzekerheid op wanneer betrouwbaar lopend of voltooid bewijs terugkeert. Geen tweede START, geen nieuwe APP-aanvraag en geen algemene foutreset.
- Respecteert tijdens herstart gewijzigde numerieke instellingen door eigendom los te laten en de bestaande handmatige rusttijd te behouden. Bevestigde lopende/voltooide AEG-cycli verbruiken ook hun APP-aanvraag; later Idle kan geen oude belading herarmen. Open boilerherstel telt als busy voor veilig verwijderen.
- Repareert éénmalig oude tijdelijke Observe-opslag zonder hervatmarker: alleen zonder echte fout/handmatige boilerbescherming én met een onderbroken lease van een bekend Auto-toestel of schoon routine-DHW-hersteljournal. De nieuwe marker, ook leeg, beschermt latere expliciete Observe-/Pauze-keuzes tegen opnieuw afleiden van Auto.
- Behoudt echte handmatige/fabrikantbescherming, fouten, onzeker opdrachtbewijs, minimumlooptijden, beschermde cycli en alle beta.46-DHW-/klimaat-/Wallboxgrenzen.
- Vernieuwt versie, actuele Home Assistant-uitleg, optieshulp, handoff, installatie/rollback en testverslag. De volledige samengestelde suite behaalt **1884 geslaagde Python-tests in 5.67 s**, inclusief 71 nieuwe herstartregressies; drie Node VM-rendergevallen zijn groen. Volledige browserproeven zijn niet uitgevoerd. Details staan in `docs/TESTRESULTATEN_BETA47.md`; live installatie of fysieke toestelactie wordt niet geclaimd.

## 1.0.0-beta.46 — 2026-10-03

- Corrigeert de onnodige extra-DHW-blokkering in Panasonic AUTO/HEAT_COOL: bij exact geregistreerde `aquarea` is een actuele native `hvac_action=idle/off` betrouwbaar. Een algemene `PUMP`-taak of oude/niet herkende optionele taakdata overschrijft die actie niet.
- Behoudt fail-closed bescherming voor ontbrekende, oude, restored of onbeschikbare klimaatbronnen en de oudere `panasonic_cc`-AUTO-ambiguïteit; daarvoor blijft actuele expliciete `IDLE/WATER`-taakinformatie vereist. Echte koeling en actieve ruimteverwarming/preheating/defrosting houden hun bestaande voorrang.
- Laat alleen bewezen koeling de koeluitloop starten of verlengen. Onbekende informatie blokkeert terwijl zij ontbreekt, maar veroorzaakt na betrouwbaar bronherstel geen nieuw verzonnen halfuur wachttijd.
- Behoudt ruwe taakdiagnostiek en conservatief leren: `PUMP` bewijst geen compressoractie en wordt geen normale rustsample. Alle beta.45-ACK-, review-, eigendoms-, comfort-, hygiëne-, AEG-, prioriteits- en Wallboxgrenzen blijven intact.
- Werkt versie, actuele uitleg, optieshulp, installatie/rollback en het actuele overdrachtsdossier samen bij. De volledige samengestelde suite behaalt **1813 geslaagde Python-tests in 6.79 s**; lokale release-/syntaxcontroles zijn groen. Browsercontroles zijn niet opnieuw uitgevoerd. Details staan in `docs/TESTRESULTATEN_BETA46.md`; live installatie en fysieke opwarming worden niet geclaimd.

## 1.0.0-beta.45 — 2026-10-02

- Corrigeert de exacte adapterherkenning voor vertraagde boilerdoelbevestiging: zowel `aquarea` als `panasonic_cc`, via geregistreerde integratieherkomst en zonder naamheuristiek. De live Aquarea Smart Cloud 1.0.61-koppeling publiceert optimistisch en vraagt pas na tien seconden geforceerd op; beta.44 miste het domein `aquarea`.
- Accepteert voor deze water-heateradapters geen onmiddellijke lokale doelweergave als opdrachtbevestiging. Een passende latere Home Assistant-rapportage blijft vereist en bewijst geen fysieke opwarming of onafhankelijk LIVE apparaatbericht.
- Behoudt de native read-only taakbron, alle handmatige/eigendoms-/review-, koel-, hygiëne- en elektrische beveiligingen en het bestaande contract van andere water-heateradapters. Geen nieuwe Powerful-/Force DHW-, Wallbox- of klimaatmodusopdrachten.
- Werkt versie, actuele uitleg, optieshulp, installatie/rollback en testverslag samen bij. De definitieve softwaregate behaalt **1773 Python-tests in 10.05 s** en **veertien browsercontroles** met nul fysieke actuatoroproepen. Beta.44 blijft een onveranderlijke gepubliceerde en geladen release; beta.45-publicatie, installatie en latere live-doelbevestiging zijn nog open.

## 1.0.0-beta.44 — 2026-10-02

- Maakt de effectieve starttoewijzing na hogere prioriteiten en reserves zichtbaar, naast de ruwe vrije injectie.
- Reserveert geen EV-vermogen bij verse geldige lage laadkracht plus expliciet geen laadvraag, geen verbonden auto of bekende inactieve status. Herkent Zonne-auto · wacht op auto compatibel zonder eigen waardelijsten te herschrijven; Wallbox blijft read-only.
- Verdeelt een lopende AEG-beurt en extra 60 °C proportioneel met conservatieve toestel-/comfortreserves, echte net-/PV-ruimte en geen Wallboxkrediet voor extra 60 °C.
- Scheidt gemeld en voorgesteld boilerdoel en beschermende pauze op het dashboard; ondersteunt een expliciete native taakbron zonder HEAT/COOL- of compressorclaim. De eerste vertraagde ACK-guard herkende alleen `panasonic_cc`; het live domein `aquarea` vereist daarom de beta.45-correctie.
- Corrigeert opties opslaan zonder afhankelijkheid van `form.elements`. Softwaregate: 1760 Python-tests en veertien browsercontroles; publicatie, pakketten, HACS-installatie en geladen backend/kaart zijn afzonderlijk bevestigd.

## 1.0.0-beta.43 — 2026-10-02

- Toont werkelijk actieve toestellen en programma's in Overzicht. Werkelijk autoladen krijgt dezelfde actieve rand/status als andere toestellen; een gekozen laadmodus, oude meting of ingeschakelde regeling is geen bewijs van actief verbruik.
- Toont bij de Wallbox een actuele fabrikantwachtreden, de afzonderlijke SolarPilot-verdelingsregel en de laatst waargenomen laadstop. Bewaart maximaal 30 laadperioden; ontbrekende oorzaken, herstarts en meetonderbrekingen worden niet als bewezen laadstops ingevuld. Wallbox-bediening blijft uitgesloten.
- Voegt een zichtbare Terug-knop en veilige browser-/muis-Terug/Vooruit toe. Niet-opgeslagen invoer wordt beschermd; Vooruit herhaalt geen opslag of toestelopdracht.
- Houdt een aparte, maximaal 90 dagen bewaarde schatting bij van het financiële voordeel van automatisch gestuurd zonverbruik. Handmatige starts/boosts zijn uitgesloten; een ontbrekende vergelijking zonder SolarPilot blijft nadrukkelijk geen bewezen extra besparing.
- Voegt een optionele maandag-startdeadline voor de afwasmachine toe. Andere dagen houden hun gewone deadline; bestaande aanvragen veranderen uitsluitend na expliciete bevestiging, zonder herarming of herhaalde START.
- Maakt de startvermogensuitleg precies: vrije zonnestroom, voorwaardelijk beschikbaar vermogen van autoladen en het totaal voor dit toestel. Een ontvangen APP-aanvraag wordt niet als ontbrekend aangeduid alleen omdat de verbindingsterugmelding oud is; een lopende cyclus toont geen startchecklist.
- Maakt de avondvoorraad warm water apart zichtbaar onder Voorrang: deze mag indien nodig zonnestroom gebruiken waarmee de auto nu laadt, uitsluitend bij een bevestigde, actuele zonnelaadsessie. Het ingestelde maximum (standaard 55 °C) en alle comfort-, koel-, sterilisatie- en elektrische grenzen blijven gelden. Extra 60 °C blijft alleen echt restoverschot gebruiken; SolarPilot bedient de Wallbox niet.
- Publiceert onder een nieuw beta-versienummer met bijbehorende actuele uitleg, installatie/rollback en testverslag. Bestaande tags en releasepakketten blijven ongewijzigd. Softwareverificatie en werkelijke live acceptatie worden afzonderlijk vastgelegd.

## 1.0.0-beta.42 — 2026-10-02

- Voegt bij een herkende handmatige boilerpauze een gerichte **Hervat**-actie toe. Zij is alleen beschikbaar buiten Automatisch regelen en zonder wachtende opdracht, beëindigt uitsluitend de SolarPilot-rust en schrijft niet direct een temperatuur.
- Toont onder **Voorrang** de effectieve uitkomst naast de bewaarde Wallbox-toestemming. Een opgeslagen Ja blijft bewaard, maar is onder Auto laden zichtbaar niet effectief; verplaatsen of opslaan verleent geen actuatorrecht.
- Corrigeert zichtbare DHW- en Wallbox-termen en de hulptekst voor onmiddellijke terugval bij echte netafname, zodat interface en werkelijk beleid hetzelfde zeggen.
- Begrensd wissen van leergegevens wist alleen de bedoelde lokale afgeleide Wallbox-, toestelvermogen-, PV-, fase- en klimaatleerlagen. Instellingen, historische bootstrap, operationele klimaatveiligheid en andere modellen blijven behouden; resetten stuurt geen apparaat.
- Behoudt alle beta.41-klimaat-/DHW-eigendomsgrenzen en de beta.40-AEG-recovery zonder verruiming van fysieke rechten.
- Legt de bewezen live basis vast: SolarPilot beta.41 draaide werkelijk op Home Assistant Core 2026.9.4, veilige modules waren gericht geactiveerd en de oude 60/50-boilerautomatiseringen stonden uit.
- Claimt nog geen fysieke beta.42-test van actieve koeling of een echte AEG-belading. De live Wallbox-broncontrole/reload bevestigde actuele gestopte bronversheid zonder EV-krediet; zonne-auto- en manuele overgangen blijven nog te doorlopen en onbekend of oud blijft fail-closed.
- Definitieve samengevoegde suite: **1472 tests geslaagd in 8.88 s**; alle elf browsercontroles en de bron-/documentreleasechecks zijn groen. Release-ZIP's worden pas na de publicatieworkflow inhoudelijk en op checksum gecontroleerd.

## 1.0.0-beta.41 — 2026-10-02

- Maakt **Voorrang** één duidelijke verticale bron van waarheid: beschermde regels staan vast, flexibele regels zijn verplaatsbaar en per toestel staat één begrijpelijke uitkomst voor **Mag de auto minder laden?**.
- Verbergt de oude dubbele toestelprioriteit- en Wallboxvelden ook voor het actuele schema 2. Een formulier dat vóór de centrale omzetting werd geopend kan de centrale volgorde of toestemming niet terugschrijven.
- Toont per toestel de doorslaggevende actuele regelreden plus gestructureerde startvoorwaarden, benodigd/startmargevermogen en resterende stabiliteitstijd. De geschiedenis benoemt Startreden en Stopreden afzonderlijk en verzint geen ontbrekende externe oorzaak.
- Behoudt een handmatig of extern uitgeschakelde Panasonic-zone tijdens een gewone AUTO-beslissing. Alleen de werkelijk overschrijdende zone kan bij een harde comfortgrens naar Panasonic AUTO worden vrijgegeven; verwijdering herstelt uitsluitend door SolarPilot zelf ingezette coast-zones. SolarPilot kiest nooit HEAT of COOL.
- Beperkt DHW-overschothysterese tot een aantoonbaar door SolarPilot uitgegeven en teruggemeld hoog doel. Werkelijke netafname, actieve koeling of een onbeheerde/onbevestigde extra-doelbeslissing kan de 60 °C-luxe zonder terugvalvertraging laten vervallen; manual hold en fabrikantbescherming blijven schrijfblokkeringen.
- Documenteert de live Wallbox-koppeling via één effectieve-sessiebron met volledige zonne-auto-, manueel- en gestoptwaarden. Een Full Solar-instelling alleen is geen sessiebewijs en SolarPilot blijft read-only.
- Houdt activering bewust in lagen: eerst Alleen bekijken, daarna de gecontroleerde globale regeling en vervolgens per toestel Auto. Een update, migratie of opgeslagen prioriteitswijziging verleent geen nieuw actuatorrecht.
- Behoudt de volledige beta.40-AEG-recovery: maximaal tien minuten gericht na opstart, uitsluitend één complete same-device mapping, geen APP-ticket of START tijdens migratie en alle bestaande veiligheidslocks.
- Testaantallen worden pas na de definitieve bronboomcontrole ingevuld in `docs/TESTRESULTATEN_BETA41.md`; dit changelog vermeldt geen voorlopige of afgeleide aantallen.

## 1.0.0-beta.40 — 2026-10-01

- Herstelt de bewezen Home Assistant-opstartvolgordefout waardoor beta.39 bij zijn enige recoverycontrole nog geen legacy-dashboardmarker zag, `not_applicable` vastlegde en het later volledig aanwezige AEG-profiel niet meer aanmaakte.
- Houdt uitsluitend de bestaande legacy-afwasmachinemigratie na SolarPilot-start tijdelijk actief: maximaal tien minuten, met gerichte state-events en een begrensde periodieke hercontrole. Listeners stoppen na succes, timeout of unload.
- Een late recovery wordt persistent én live toegepast, zodat het profiel zonder integratie-reload onder **Toestellen** en volgens de bestaande voorkeursregel onder **Voorrang** verschijnt.
- Herstel blijft éénmalig en fail-closed: alleen één complete, eenduidige same-device mapping van START, ApplianceState, ConnectivityState, RemoteControl, DoorState en programmaselectie kan een profiel opleveren. Ontbrekende of ambigue rollen geven geen fysiek recht.
- Rolstatus wordt zonder private Home Assistant-device-id in `dishwasher_setup` zichtbaar. Een eerder hersteld en later bewust verwijderd profiel wordt niet automatisch opnieuw gemaakt.
- Alleen het exact als legacy-recovery gemarkeerde nieuwe profiel kan de eerder afgesproken eenmalige Auto-deelname krijgen wanneer voor die identiteit nog geen gebruikersmodus bestaat. Gewone nieuwe toestellen blijven Uitgesloten en bestaande keuzes worden niet overschreven.
- De migratie verstuurt geen START, maakt geen APP-aanvraag en wijzigt geen programma. Exacte nieuwe APP-`Enabled`-overgang, gesloten deur, geldig programma, Ready To Start, actuele verbinding, één START per belading en alle elektrische/comfortlocks blijven verplicht.
- De beta.39-fixes voor lange zonwachttijd, volledige beschermde cyclusfasen en de onbewezen automatische alarmbron blijven cumulatief behouden.
- Volledige regressiesuite: **1445 tests geslaagd**; gerichte afwasmachine-/recovery-/runtime-set: **353 tests geslaagd**. Ook release-, privacy-, syntax- en documentconsistentiecontroles zijn groen.

## 1.0.0-beta.39 — 2026-10-01

- Gebouwd op de geregistreerde beta.38-bron; geen terugval naar een oudere branch of losse GitHub-state.
- Herstelt automatische AEG-starts die na langer wachten op zon konden blokkeren doordat beta.38 alle statische startvoorwaarden afzonderlijk na 300 seconden als te oud beschouwde. Alleen ConnectivityState fungeert nu als actuele heartbeat; Ready To Start, exacte `Enabled`, gesloten deur en programmaselectie blijven bruikbaar zolang ze niet unknown/unavailable/restored of werkelijk gewijzigd zijn.
- Herstelt de eerder afgesproken beschermde fasen Washing, Prewash, Main wash, Rinsing, Drying en Ado Drying naast Running/Paused. AirDry blijft dus dezelfde lopende cyclus tot End Of Cycle.
- Nieuwe legacy-recovery koppelt de optionele numerieke AEG Alerts-sensor niet automatisch als veiligheidsbron zonder bruikbare technische `DISH_ALARM_*`-vlaggen.
- Eénmalige beta.39-reparatiemigratie wijzigt uitsluitend een profiel dat aantoonbaar door beta.38 zelf als recovered werd aangemaakt: verkorte faselijst wordt hersteld en alleen een onbewezen automatisch gekozen alarmbron wordt verwijderd. Handmatige profielen blijven onaangeroerd.
- APP-startregels blijven strikt: uitsluitend nieuwe exacte `Enabled`-overgang, vóór 13:00 vandaag / vanaf 13:00 volgende dag, deadline/nettoestemming ongewijzigd, één START per belading, geen blind retry, nooit STOPRESET/PAUSE/RESUME of stekkerrelais.
- End Of Cycle blijft eventgestuurd en persistent; Off/Unavailable/Disconnected alleen bewijst geen einde.
- Centrale prioriteiten, Panasonic/DHW, Wallbox-read-onlybeleid, PV/fase/planner/analyse/leren en bestaande configuratie/leerdata blijven cumulatief behouden.
- Volledige regressiesuite na implementatie: 1434 tests geslaagd.

## 1.0.0-beta.38 — 2026-10-01

- Herstelt de concrete regressie waardoor de bestaande AEG-afwasmachine niet automatisch kon starten: de beta.35-analyse toonde wel de afwaslogica maar geen actief dishwasher-device, geen APP-ticket en geen afwasprioriteit.
- Nieuwe conservatieve éénmalige herstelmigratie reconstrueert uitsluitend de reeds bedoelde AEG/Electrolux-koppeling wanneer één eenduidig Home Assistant-apparaat alle verplichte bronnen bevat. Dubbele oude START-entiteiten worden gefilterd; PAUSE, RESUME, STOPRESET en starttijd kunnen nooit als START worden gekozen.
- Een hersteld profiel krijgt de bestaande APP-regels terug: exact `Enabled`, vóór 13:00 vandaag, vanaf 13:00 volgende kalenderdag, deadline 13:00 met bestaande nettoestemming, één START per belading, geen retry na onzekerheid en eventgestuurd End Of Cycle. Startup met APP al Enabled maakt geen kunstmatige aanvraag.
- Alleen een werkelijk hersteld legacy-profiel wordt éénmalig op Auto gezet wanneer daarvoor nog geen opgeslagen gebruikerskeuze bestaat. De migratie zelf verstuurt geen fysieke opdracht en wijzigt geen programma.
- SolarPilot-status exporteert `dishwasher_setup`, zodat ontbrekende, ambigue en herstelde koppelingen zichtbaar worden in plaats van stil uit te vallen.
- Behoudt de geldige beta.37-verbeteringen: eenvoudige namen, één centrale voorrang, nieuwe gewone toestellen onderaan, Wallbox-vermogen alleen voor toestellen die én boven de Wallbox staan én toestemming hebben, en de éénmalige veilige activering van reeds gekoppelde leer-/regelmodules.
- Afgesproken prioriteiten blijven behouden: veiligheid/fabrikantregels en noodzakelijk comfort beschermd; voorkeur-AEG vóór Wallbox wanneer actief; Wallbox vóór lagere flexibele lasten en extra 60 °C-buffer volgens de centrale lijst.
- Volledige cumulatieve regressiesuite, release-uitleg, veldhulp, overdrachtsdossier en installatiepakket worden samen vernieuwd.

## 1.0.0-beta.37 — 2026-10-01

- Eenvoudigere dashboardnamen en configuratiegroepen voor niet-technische bediening.
- Centrale zichtbare volgorde werd leidend: Wallbox-zonnevermogen kan alleen worden gebruikt door een toestel dat boven de Wallbox staat én daarvoor expliciet toestemming heeft.
- Nieuwe gewone flexibele toestellen starten onderaan de lijst; een voorkeurs-AEG-profiel blijft vóór de Wallbox wanneer die logica van toepassing is.
- Eénmalig veilig activeringsprofiel voor analyse, planner en bestaande bronafhankelijke modules; geen ontbrekende bron, veiligheidsbevestiging of actuatorrecht wordt verzonnen.
- Analyse-logregistratie volgt live het aan/uitzetten van de analysefunctie.

## 1.0.0-beta.36 — 2026-10-01

- Basislastleren scheidt duidelijke Panasonic-ruimteverwarming, -koeling, tapwater en sterilisatie van gewone huishoudlast. Zonder aparte W-meter wordt alleen uit stabiele P1+PV-start/stops een begrensde planningsschatting geleerd; realtime elektrische ruimte blijft uitsluitend op echte metingen gebaseerd.
- Wallbox-sessieherkenning uitgebreid: ingestelde modus, effectieve sessie, laadvermogen en actuele terugnametoestemming zijn afzonderlijk zichtbaar. Een kandidaat-sessiesensor wordt alleen voorgesteld bij voldoende bewijs op hetzelfde Wallbox-apparaat; er wordt nooit een entity_id verzonnen.
- Centrale prioriteitenlijst wordt bij beta.35 → beta.36 automatisch leidend met behoud van de bestaande effectieve volgorde. Beschermd: elektrische/fabrikantbeveiliging en legionella, noodzakelijk warmwatercomfort en noodzakelijk ruimtecomfort. Flexibele standaardvolgorde blijft Wallbox → ontvochtiger → extra boilerwarmte 60 °C. Wallbox-rang en per-toesteltoestemming om laadvermogen terug te nemen zijn afzonderlijke instellingen.
- Ontvochtiger en andere binaire lasten krijgen geen dubbele turn_on wanneer alleen hun geleerde/planningsvermogen wijzigt. Bestaande minimumlooptijden en anti-pendelregels blijven gelden.
- DHW gebruikt één persistente configuratiebron. De afgesproken 50 °C normaal, 46 °C bewaakte comfortgrens, -5 °C Panasonic-differentie, 50 °C zonnebuffer, 60 °C extra PV-buffer, 50 °C maximum bij actieve koeling en Panasonic 62 °C-sterilisatie blijven behouden. Configuratie, inschakeling, veiligheidsbevestiging, regeltoestemming, SolarPilot-doelbezit, Panasonic-autonomie en handmatige override zijn afzonderlijk zichtbaar.
- Klimaatbetrouwbaarheid opgesplitst in passieve temperatuurverandering, zonnewinst, verwarmingsrespons, koelrespons, reactievertraging, weerscorrectie en coast/off-feedback. Ontbrekende onderdelen worden als Nog niet geleerd/Eerste metingen/Voorlopig getoond en kunnen geen 100%-vertrouwen veroorzaken.
- PV-kalibratie behoudt minimum vijf geldige dagen, 13.800 Wp, 10.000 W omvormerlimiet, lokale schaduwdetectie en realtime-PV als waarheid. Diagnostiek toont voortaan ook bias en fout per ochtend/middag/namiddag.
- Faseherkenning onderscheidt geleerd, voldoende betrouwbaar, gebruikt voor advies en werkelijk vrijgegeven voor regeling; de expliciete regelvrijgave blijft vereist.
- Analyse-export schema 2 toont aangevraagde periode, beschikbare ruwe periode, werkelijk gedekte meettijd, dekking, eerste/laatste bruikbare meting, herstarts, offline/gat-tijd en fast telemetry. Bootstrapdata, live leerdata, berekende profielen en actuele metingen worden afzonderlijk benoemd; planberekeningen zijn geen leerdagen.
- Kwaliteitspagina herwerkt naar begrijpelijke secties Metingen, Zonnevoorspelling, Huishoudelijk verbruik, Toestellen, Klimaat en concrete aanbevolen acties; geen losse misleidende totaalscore bovenaan.
- Bestaande AEG-afwasmachinebeveiligingen blijven behouden: kort End Of Cycle event-driven opslaan, Off/Unavailable/Disconnected niet als bewezen einde, AirDry niet als einde, exact Remote Control Enabled voor start en maximaal één start per aanvraag.
- Migratie bewaart gekoppelde entiteiten, prijzen, Wallboxinstellingen, apparaten, leerdata, fase/PV/klimaat/boilerdata, bevestigingen en prioriteitsvolgorde. Incompatibele warmtepompleerdata reset alleen dat model.

## 1.0.0-beta.35 — 2026-09-30

- Cumulatief op de aangeleverde beta.34, zonder automatische herordening of reset van instellingen/leerdata.
- Nieuwe centrale tab Voorrang, stabiele editor met slepen en toetsenbord-/mobielvriendelijke pijlen, per-toesteltoestemming om autoladen te verminderen, expliciete bevestiging en conflictcontrole.
- Bestaande regeling blijft leidend tot een echte centrale wijziging. Daarna volgen realtime toestelallocatie, planner, Wallbox-relaties en afwas-afbouw dezelfde gekozen rangorde.
- Comfort, hygiëne, minimale looptijden en gestarte programma's blijven beschermd. Extra boilerwarmte is sorteerbaar tussen lagere lasten maar blijft na Wallbox en voorkeur-afwas; geen EV-vermogen voor die buffer.
- Nieuwe verbruikers komen automatisch in de lijst zonder nieuwe startrechten. Oude numerieke/globale controles kunnen een actieve centrale lijst niet overschrijven.
- Eén Export-pagina met bestaande privacy-/tijdsvensterkeuze en uitgebreid compleet analysebestand; geen upload en geen vervanging van een back-up.
- Negen tabbladen, duidelijkere verwijzingen, actuele volledige uitleg en veldhulp in dezelfde release. Native instellingen tijdens Zonnestroom, APP-/deadlinegedrag, PV-correctie en fabrikantsturing blijven behouden.
- Software- en browsertests gebruiken lokale testdubbels/voorbeelddata. Geen fysieke installatie, GitHub-publicatie of HACS-release uitgevoerd.

## 1.0.0-beta.34 — 2026-09-30

- Cumulatief op de rechtstreeks aangeleverde beta.33; alle bestaande PV-, Wallbox-, AEG- en warmwaterregels behouden.
- Configuratie toegankelijk in Zonnestroom; finale bevestiging met live/deferred overzicht. Gewone opties zonder volledige herlading, zelfde runtime, timers en statuslisteners.
- Gevoelige wijzigingen per toestel opgeslagen tot veilige vrijgave; effectieve oude koppelingen blijven ook na herstart leidend. Voorstellen individueel annuleerbaar.
- Deadline/nettoestemming: expliciete keuze huidige APP-aanvraag of alleen volgende beurten; geplande dag en eenmalige toestemming behouden.
- Toestellen beheren: toevoegen, instellingen, koppelingen, planning, historie en vervangen. Categorie en technische adapter afzonderlijk.
- Vervangen krijgt nieuw ID, geen oude koppelingen, meetprofielen, APP-vrijgave of automatische deelname. Oud profiel gearchiveerd; bestaande bewaartermijn blijft gelden.
- Native virtuele entiteiten dynamisch toevoegen/verwijderen zonder bronapparaten te wijzigen; archiefhistorie en analyse-export uitgebreid.
- Optimistische samenvoeging, bronduplicaat- en opslagfoutcontroles; vraagtekens en één actuele release-uitleg bijgewerkt.
- Geen nieuwe generieke merkintegratie voor wasmachine/droogkast; geen wijziging van de fysieke installatie of publicatie uitgevoerd.

## 1.0.0-beta.33 — 2026-09-29

- Cumulatief bovenop beta.32: instelbare automatische EV-zonneverdeling voor geschikte voorrangsverbruikers, met behouden compressor-minimumtijden.
- Effectieve Wallbox-sessie naast ingestelde Full Solar; manueel/onbekend laden geeft geen EV-credit. Optionele 60 °C terugval; gewoon Panasonic-comfort en sterilisatie blijven beschermd.
- Forecast.Solar-registerdetectie en guarded lokale coordinatoradapter, geen nieuwe HTTP-oproepen. Eén primaire PV-configuratie, expliciete fallbackbronnen.
- Robuuste 15-minutenkalibratie per zonnestand/seizoen, 13,8 kWp/10 kW-clippingbewaking, startup/cloud/outlierfilters, gradual bounded multi-day learning en persistente modelversie.
- Ruwe/gecorrigeerde horizon, kWh-integratie, 14 sensoren, admin PV-diagnose met grafiek/dagtabel en bevestigde PV-only reset; analyse-export uitgebreid.
- Opgeruimde Planning-samenvatting, Onderzoek & instellingen en nieuwe concrete leervragen; geen modals sluiten bij telemetrie.
- AEG APP/13:00/next-day en event-einde, prioriteiten, 50/46-DHW zonder52-herstel en bestaande leerdata blijven behouden. Geen nieuwe fasegewijze afwasoptimalisatie zonder Shelly.
- Zie docs/BETA33_INSTELLEN.md voor migratie, sessiebron en beperkingen; tests staan in het bijgevoegde testverslag.

## 1.0.0-beta.32 — afwasmachinevoorrang onder warmtepompcomfort

- Standaard voorkeursprofiel: gewone warmwater-/vloerregeling en noodzakelijke avondvoorraad eerst; daarna AEG-afwas vóór Wallbox, ontvochtiger en extra 60 °C.
- Afzonderlijke beschermde zonnestart met bestaand EV-zonnevermogen, zonder Wallbox-opdrachten of uitbreiding van elektrische ruimte. Nieuwe actieve status en netto balans worden gecontroleerd; geen afwas-rollback. Tijdelijke netafname mogelijk.
- Alleen benodigde lagere, eigen, gemeten lasten na stabiliteit vrijgeven; compressor-minimumlooptijd en verse bevestiging/P1 blijven vereist.
- Klaar voor morgen reserveert vandaag niets. Deadline verandert geen comfort- of elektrische grens.
- Zonder Shelly conservatieve nominale reservering; volledige faseprofielplanning blijft expliciet voor de latere Shelly-update.
- Vraagtekens, voorrangskaart, analysevelden, herstelmelding en actuele uitleg in dezelfde release.
- Bestaande AEG-profielen krijgen de twee voorkeurskeuzes standaard aan; bestaande Auto/Uitgesloten, mapping en fysieke APP-vrijgave blijven ongewijzigd. Keuzes kunnen uit.

## 1.0.0-beta.31 — APP-start, volgende dag standaard en betrouwbare eindeherkenning

- Nieuw AEG-profiel: fysieke Delay Start/APP-vrijgave, exact Enabled; geen native timer of extra klaarzetknop.
- Vóór 13:00 vandaag; op/na 13:00 standaard volgende kalenderdag. Instelbaar alternatief dezelfde dag.
- Uiterlijk 13:00 op de geplande dag met expliciete nettoestemming; nooit elektrische limieten of apparaatvoorwaarden omzeilen.
- Vast schema over herstart; één belading maximaal één START; geen retry van onzekere opdrachten.
- Kort End Of Cycle direct vastleggen en onthouden, ook na Off/Disconnected/herstart. AirDry blijft nadrogen.
- Aparte Cycle phase-meting en AEG-technische alarmvlagcontrole, geen oordeel op enkel Alerts-teller.
- APP-plan/eindstatus zichtbaar in kaart, uitleg bij elke nieuwe optie en volledige analyse-export.
- Cumulatief: behoudt beta.30 leren/vragen, beta.29 analyse-export en alle bestaande warmwater-/Wallbox-/historiefuncties.
- Bestaande fysieke rechten en handmatige AEG-profielen worden niet stilzwijgend aangepast.

## 1.0.0-beta.30 — Leren, toetsen en gerichte vragen

- Nieuw: Leren & vragen-popup met echte meetbasis voor alle bestaande modellen, gerichte keuzes, antwoordgeschiedenis, optionele HA-meldingen en admin-only API.
- Restverbruik leren tijdens Wallbox/eigen lasten waar actuele, aparte meters een betrouwbare balans geven; geen schattingen, hiaten of dubbele meters als leerwaarheid. Afwijzingsredenen en beschermde boilercontext apart geregistreerd.
- Recente basislastvariant in de achtergrond vergelijken op latere dagen; uitsluitend na jouw toestemming en aantoonbare verbetering binnen ±25% toepassen. Bij slechter bewijs terug naar gewoon profiel. Geen versoepeling van fysieke regels.
- Eerlijke labels: basislastvertrouwen is geen totaal huisvertrouwen. Aparte daglicht-PV-fout, bias, kalenderdagen en nieuwe meetdekking; geen reconstructie van oude dekking.
- Inclusief modellen, vragen en antwoorden in bestaande analyse-export; begrensd lokaal, geen automatische upload.
- Geen nieuwe AEG APP-start-/deadline-logica in deze release; bestaande beta.29 adapter behouden. Alle boiler-/Wallbox- en eerder vrijgegeven functies cumulatief behouden.

## 1.0.0-beta.29 — AEG-start en volledige analyse-export

- Toegevoegd: afzonderlijk AEG/Electrolux-start-only profiel met echte START-knop, gereedmelding, verbinding, remote-start, deur en geselecteerd programma.
- Per geladen afwasbeurt een bevestigde eenmalige klaarzettoestemming; pas native START bij actuele zonne-/plannervoorwaarden. Nieuwe koppelingen blijven Uitgesloten.
- Geen plugrelais, STOPRESET, PAUSE of RESUME. Een lopende cyclus blijft beschermd bij netafname, Pauze, uitsluiting en Wallbox-voorrang. Geen blinde herhaalstart na een onzekere opdracht/herstart.
- Voorbereid op exclusieve Shelly W/kW-meting; complete cyclus-/faseprofielen per programma, onbemeten fasen blijven onbekend. Oude geschatte fasen worden niet als echte meting geïmporteerd.
- Toegevoegd: admin Analyse-export-popup (JSON, 1h/24h/7d) met alle module-instellingen, bronwaarden/attributen/versheid, modellen, beslissingen, eigen foutlogs, verbruikershistorie, energiekosten en beschikbare tijdreeksen.
- Lokale begrensde registratie, configureerbaar; namen standaard gepseudonimiseerd, gevoelige velden gefilterd, geen automatische upload. Exportopbouw buiten de event loop. Private exports worden door public-preflight geweigerd.
- Nieuwe configuratieopties hebben release-gebonden vraagtekenuitleg. Bestaande beta.28-warmwatersturing en eerdere cumulatieve functies blijven behouden.
- Geen live HA- of GitHub-wijzigingen door het pakket; zie docs/AFWASMACHINE_EN_ANALYSE.md voor activering en testgrenzen.

## 1.0.0-beta.28 — 2026-09-28

- Onafhankelijk normaal boilerdoel (nieuw 50 °C) en bewaakte comfortgrens (nieuw 46 °C). Geen afgeleide tijdelijke verhoging om de Panasonic-differentie te omzeilen.
- Ochtendcontrole herstelt uitsluitend het normale doel; oude ochtend-/noodboost-latches worden niet afgespeeld. Geen Force DHW of mode-/compressoropdrachten.
- Expliciete waarschuwing: 50 °C met -5 °C differentie laat nominale herstart rond 45 °C toe. Geen minimumtemperatuur- of hygiënegarantie.
- Begrensde avondvoorraad uit echt beschikbare zon: één berekende reserve per dag, geen opkruipend setpoint om starten af te dwingen, behoud voltooiing na herstart.
- Extra zonne-opwarming wacht standaard bij bezige/onbekende ruimteklimaatactie en 30 minuten tussen extra verhogingen. Normale doelherstelling en beschermende verlaging blijven beschikbaar.
- Bestaande normale doelen, bronnen, rechten en leerdata blijven behouden via expliciete migratie; 50/46-profiel bewust kiezen bij bestaande installaties.
- Dashboard, actuele uitleg, optie-vraagtekens, native beschrijvingen en instelhandleiding tegelijk bijgewerkt. Nieuwe software- en browserregressies.

## 1.0.0-beta.27 — 2026-09-28

- Release-bound Nederlandse optie-uitleg voor alle wizardvelden en directe klimaat/planner/boileropties, onafhankelijke toegankelijke hulpdialogen en native HA-beschrijvingen.
- Geïntegreerde configuratiewizard gebruikt HA's bestaande admin-only optiesflow; bewaarde velden en hulp overleven live dashboardupdates.
- Alleen-lezen Wallbox-laadprofiel met same-device herkenning, expliciete fasebron of handmatige 1-/3-fasenkeuze, huidige25-A-terugval, bronactualiteit en ICP-uitsluiting.
- Optionele nachtrust tot stabiele zon, gemeten ochtenddoel45 °C om09:00 en beperkte avondvoorraad uit laatste bruikbare zon. Begrensd tankleren en expliciete aannames; geen temperatuurgarantie.
- Gewoon warmtepompcomfort vóór autonoom EV-laden; extra60 °C uitsluitend echt residuale injectie. Geen opdrachten naar Wallbox.
- Koeluitloop aanbevolen30 minuten en optionele voorspellende koelblokkering met bestaande thermische/weerdata. Nacht-/ochtend- en fabrikantbeveiligingen blijven gescheiden.
- Standaard zonne-stabiliteit300/300 seconden; bestaande opgeslagen wachttijden blijven behouden.
- Stabiel DHW-eigenaarschap blokkeert ruimteklimaat niet permanent; pending/fout-/hygiënebescherming blijft.
- Vaste testklok voor twee bestaande DHW-tests voorkomt afhankelijkheid van een echte maandagse hygiëneperiode. Nieuwe regres­sietests voor koude start, hele-gradenmetingen, DST, bescherming, EV-prioriteit, profielbronnen en UI.


## 1.0.0-beta.26 — Mobiele navigatie, manuele bediening, automatische herstartreconciliatie en 20% batterijverlies

- Mobiel SolarPilot-dashboard krijgt een eigen menuknop die het normale Home Assistant-zijmenu opent; desktopnavigatie blijft ongewijzigd.
- Verbruikers tonen fysiek AAN, SolarPilot-eigenaarschap, externe activiteit, werkelijk gemeten verbruik en manuele toestand visueel duidelijker.
- Nieuwe expliciete **Manueel starten**- en **Manueel stoppen/vrijgeven**-acties met bevestiging. Manuele start mag binnen de softwaregrenzen netstroom gebruiken; minimumrust, minimumlooptijd, vrijgave, fouten en overige beveiligingen blijven gelden.
- Na een Home Assistant/SolarPilot-herstart worden bekende echte AAN/UIT-toestanden automatisch gereconcilieerd. Een eerder door SolarPilot beheerd toestel hoeft niet eerst uit; de opgeslagen modus kan daarna automatisch hervatten zonder oude opdrachten te herhalen. Alleen onbeschikbare/onzekere status blijft handmatige controle vragen.
- Voor deze installatie is het voorlopige eenfasige Full Solar-minimum voor Wallbox-voorrang standaard **1380 W**; de waarde blijft instelbaar.
- Batterij-what-if gebruikt standaard **80% round-trip efficiëntie = 20% totaal batterij-/omvormerverlies**. Live simulatie verwerkt dit fysiek over laad- en ontlaadpad; historische bootstrapresultaten worden conservatief naar dezelfde efficiëntie omgerekend wanneer hun bronaanname afwijkt.
- Cumulatief bovenop beta.25; beta.22–beta.25 hoeven niet afzonderlijk gepubliceerd of geïnstalleerd te worden.

## 1.0.0-beta.25 — Dagoverzicht en sessiehistoriek per verbruiker

- Nieuwe Dagoverzicht-knop per verbruiker: totale ingeschakelde/actieve tijd per dag, 7/30-dagenkeuze, tijdlijn en sessies met start- en stopredenen.
- Alleen bevestigde statusovergangen worden starts/stops; externe bediening en onbekende beginsituaties worden duidelijk onderscheiden. Herstarts, meetgaten en gemiste bevestigingen leveren geen verzonnen draaitijd of stop op.
- Lokale, begrensde opslag met dagopsplitsing rond middernacht en zomer-/wintertijd. Behoud bij gewone updates; eigen historieopslag wordt bij definitieve verwijdering meegenomen.
- Authentieke alleen-lezen Home Assistant-WebSocket-query met controle van leesrechten, alleen voor het gekozen toestel en de gekozen dag. Ondersteunt de schema-engine van zowel oudere als nieuwere HA-WebSocket-API's.
- De aparte popup behoudt DOM, datum, scroll en open details tijdens vijfsecondenupdates. Volledige sessies staan niet in de gewone statusattributen en worden alleen opgevraagd zolang nodig.
- Nieuwe model-, runtime-, permissie- en browsercontroles; complete actuele uitleg in Home Assistant en documentatie bijgewerkt. Geen versoepeling van veiligheids- of schakelregels.
- Cumulatief: bevat ook beta.22–beta.24; tussenliggende publicaties/installaties zijn niet nodig.

## 1.0.0-beta.24 — dagkosten en Wallbox-voorrang per verbruiker

- Cumulatief: bevat de batterij-starttimingfix van beta.22 en stabiele uitklappers/browserrefresh van beta.23.
- Behoud van de bestaande netto planningskost met zichtbare import/export/PV-uitsplitsing; aparte dagkost uit gemeten P1/PV, meetdekking, prijswijzigingen en herstartbehoud.
- Voorkeur per verbruiker: globale keuze volgen / dit toestel eerst / Wallbox eerst met gebruik van klein overschot.
- Wallbox blijft alleen-lezen. Minimum zonnelaadvermogen expliciet bevestigen; laadvraag, hysterese, veilige compressorvrijgave, begrensde startwachttijd en terugval zonder herhaaljagen.
- Leeg dagdoel blokkeert geen realtime flexlast meer via forecastuitstel.
- Nieuwe regressietests; actuele uitleg in Home Assistant en documentatie bijgewerkt.

## 1.0.0-beta.23 — Rustige live-interface en cumulatieve update

- Bevat alle fixes uit beta.22; beta.22 hoeft niet afzonderlijk geïnstalleerd of gepubliceerd te worden wanneer rechtstreeks vanaf beta.21 naar beta.23 wordt bijgewerkt.
- Bewaart opengeklapte dashboardsecties tijdens live SolarPilot-updates, zodat details niet meer om de vijf seconden dichtklappen.
- Verwijdert de fade-animatie bij gewone telemetrie-updates; tabwissels en bediening blijven direct reageren zonder zichtbare volledige kaartrefresh.
- De Uitleg-tab slaat een herbouw over wanneer alleen niet-zichtbare realtime meetwaarden veranderen.
- De 5-seconden regelcyclus en veiligheidslogica blijven ongewijzigd; deze release optimaliseert vooral de browserweergave en verandert geen toestelbeslissingen.

## 1.0.0-beta.22 — Deterministische batterij-opstarttiming

- Herstelt een platformafhankelijke timingfout waarbij de allereerste toekomstige batterijopdracht op een pas opgestarte Linux/GitHub-runner ten onrechte door het minimuminterval kon worden geblokkeerd.
- Een verse batterij-runtime gebruikt nu expliciet 'nog geen eerdere opdracht' in plaats van monotone tijd 0 als impliciete vorige opdracht.
- Het minimuminterval blijft ongewijzigd gelden na een echte batterijopdracht en na een herstart/reconciliatie.
- Voegt een regressietest toe die een host met slechts 5 seconden monotone uptime simuleert.
- Geen wijziging aan de huidige ontvochtiger-, Wallbox-, boiler- of klimaatregeling.

## 1.0.0-beta.21 — Runtime-fix na eerste flexlast

- Herstelt een `NameError` in het toesteloverzicht (`i` → toestel-ID) waardoor de hoofdstatussensor en daardoor de SolarPilot-config entry konden mislukken zodra een flexlast was toegevoegd.
- Voegt een regressietest toe zodat een toesteloverzicht met cyclusprofiel niet opnieuw op deze fout kan stuklopen.
- Corrigeert Home Assistant-statistiekmetadata voor energie-entiteiten: dagzonne-energie gebruikt `total_increasing`; de batterij-what-if energie gebruikt `total`.
- Verplaatst lezen/verwijderen van de privébundel en historische bootstrap uit de Home Assistant event loop naar executor-werk, zodat de `read_text` blocking-call waarschuwing verdwijnt.
- Werking en veiligheidslogica blijven verder ongewijzigd; bestaande configuratie, privébundel, leerdata en toegevoegde verbruikers blijven behouden.

## 1.0.0-beta.20 — Public HACS/GitHub release

- Publieke HACS-build opgeschoond: geen woning- of installatie-specifieke entity-ID's meer in first-install defaults.
- Eerste installatie laat de gebruiker net/PV en overige bronentiteiten expliciet kiezen; alleen universele `sun.sun` mag veilig worden voorgesteld.
- `hacs.json` rendert de README expliciet in HACS.
- GitHub-validatie uitgebreid met HACS Action, Home Assistant hassfest, syntax-, documentatie- en privacy/preflightchecks.
- Releasehulpmiddelen aangepast aan de ingebouwde frontend onder `custom_components/solar_pilot/frontend`.
- Zowel de rootdocumentatie als de in Home Assistant meegeleverde actuele uitleg worden voortaan uit dezelfde bron gegenereerd en gecontroleerd.
- Python/test-cachebestanden worden niet meer in de publicatie-ZIP opgenomen.
- Windows-publicatiescript toegevoegd voor GitHub CLI, met preflight vóór de push en zonder automatische release vóór CI groen is.

## 1.0.0-beta.18 — HACS-ready

- HACS wordt de aanbevolen installatie- en updatemethode.
- Repositorystructuur voldoet aan HACS-integratievereisten: één integratie onder `custom_components/solar_pilot`.
- `hacs.json`, HACS-validatie-workflow en tag-release-workflow toegevoegd.
- Brand-assets toegevoegd voor Home Assistant/HACS.
- Frontend blijft ingebouwd in dezelfde integratie; geen aparte Lovelace-resource nodig.
- Configuratie en leerdata blijven in Home Assistant opgeslagen en worden niet door HACS-updates vervangen.
- Veilige verwijderprocedure behouden: eerst `Verwijderen voorbereiden`, daarna config-entry verwijderen en vervolgens HACS-uninstall.
- Custom-integrationvertalingen komen uit `translations/`; verouderde `strings.json` is uit het HACS-pakket verwijderd.
- Publicatiehulpmiddel toegevoegd om GitHub owner/repository éénmalig in manifest en README in te vullen.
