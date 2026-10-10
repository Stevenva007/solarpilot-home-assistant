<!-- solarpilot-handoff-schema: 1 -->
<!-- solarpilot-handoff-version: 1.0.0-beta.64 -->

# OVERDRACHT — SolarPilot

Laatst bijgewerkt: **10 oktober 2026**. Actuele bron: **v1.0.0-beta.64**. Panasonic is exclusief eigenaar van zijn warmtepompregeling; SolarPilot mag daarvoor uitsluitend één expliciet toegewezen SG-contact aanvragen/vrijgeven. De voormalige directe tank-/klimaatsturing en haar uitvoerende herstelcomplexiteit zijn verwijderd. Andere apparaatfuncties en bestaande privédata blijven behouden. Werkelijke software-/publicatiestatus staat in `docs/TESTRESULTATEN_BETA64.md`; ingebruikname, installatie en rollback in `docs/BETA64_INSTELLEN.md`. Geen live fysieke acceptatie is uit deze softwarewerkrondes af te leiden.

## 1. Projectdoel in gewone taal

SolarPilot verdeelt beschikbare zonnestroom tussen flexibele verbruikers, een beschermde afwasmachine, autonoom autoladen en optionele extra opname via één lokaal bevestigde SG-zonneboost warmtepomp. Het combineert actuele P1/PV, fysieke fase-/netgrenzen, voorspellingen, basislast, kosten, lokaal leren en begrijpelijke beslisredenen. Panasonic verzorgt zelfstandig comfort en beveiligingen, ook zonder SolarPilot. Eén overzicht vertelt wat actief is, wacht of gerichte controle nodig heeft.

## 2. Actuele basis

Bouwbasis: gecontroleerde gepubliceerde [beta.63](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.63), commit `977f2fe1eb19c4944be7ee7125b911a473ef7c29`. Main, release en relevante open PR's zijn bij aanvang opnieuw gecontroleerd; beta.64 was vrij. Oude tags/assets blijven onveranderd. De GitHub-versie bewijst geen lokaal geladen HA-/kaartversie.

De beta.63-fix voor Home Assistant `ConfigEntry.options` als onveranderbare mapping blijft behouden: lokale dictionarymaterialisatie vóór deepcopy, verliesvrije mappingacceptatie in migratie, behoud van geneste opties en origineel HA-object. Beta.64 voegt uitsluitend expliciet lokaal bevestigd SG-toepassingsbereik, gerichte herbeoordeling, aparte koelbeveiligingsvoorwaarde, twee afzonderlijke vermogensbronnen en read-only bedrijfs-/SG-observatie toe. Geen tweede warmtepompregelaar.

De canonieke gebruikersuitleg is `custom_components/solar_pilot/current_guide.py`; `docs/ACTUELE_WERKING.md` en de ingebedde mirror worden gegenereerd. Dit dossier beschrijft actuele technische waarheid. Historische regels en testresultaten staan bij hun eigen release in CHANGELOG/Git. Nieuwe beta.64-gates staan in `docs/TESTRESULTATEN_BETA64.md`; oude beta.63-testtellers zijn geen nieuwe validatie. Voor rollback naar beta.63 blijft de bij deze upgrade passende volledige privéback-up nodig; terugkeer naar directe beta.61-regeling vereist de volledige pre-beta.62-migratieback-up.

## 3. Absolute ontwerpregels

- Voor Panasonic uitsluitend de toegewezen bestaande SG-uitgang; Panasonic-entiteiten verder read-only. Geen set_temperature, AUTO/OFF, HEAT/COOL, Powerful/Force, kamertemperatuur-, stooklijn-, heater- of herstelwrite, ook niet via generieke helpers, scripts, planner, opstart, Pauze, unload of verwijdering.
- Panasonic bezit normaal warm water, hysterese, ruimte-/zoneregeling, compressor, kleppen, pompen, ontdooien, elektrische ondersteuning en sterilisatie. Geen tweede heaterrelais of nieuwe hardware-/DIP-functie.
- Eén actuator heeft één eigenaar. Het gekozen SG-contact kan geen gewone flexlast- of batterijactuator zijn. Geladen gewone/batterijscripts worden per dispatch statisch op vaste onafhankelijke doelen gecontroleerd; niet inspecteerbare inhoud/dynamische/proxydoelen zijn geblokkeerd. Geen bewijs over externe dubbele writers zonder afzonderlijke lokale inzage.
- Automatische SG staat standaard uit. Uitgang, mapping, Panasonic-reactie/native basis, geen dubbele sturing en echte lokale aflooptimer moeten bevestigd zijn. Een globale Auto-/hervatvoorkeur vervangt dit bewijs niet.
- Een opdracht is geen bevestiging. Aanvraag/eigenaar/reden, gemelde relaisstand/lokale toestemming, compressor/native context en ontvangen SG-status blijven gescheiden. Compressorbedrijf, WATER-/klepstand of app-tankdoel bewijst geen causaal extra SG-verbruik.
- Lokale communicatietoestemming standaard 300 s, vernieuwing 60 s zonder fysieke uit/aan-cyclus. Power-on UIT geldt alleen herstart, niet wifi-uitval. Geen werkende geteste terugval: geen automatische SG.
- Geen laagvermogenpulsen, periodieke OFF/ON, twintigminuten-hertrigger of reboottruc. Historische verschillende bedrijfsmomenten bewijzen geen contactflankprobleem of SolarPilot-oorzaak.
- Toepassingsbereik dhw_only/general vraagt expliciete lokale bevestiging; geen automatische algemene toestemming of Panasonic-profielwijziging. Extra koelvrijgave vereist afzonderlijk bevestigde bestaande condens-/dauwpuntbeveiliging, of verse native context die koeling betrouwbaar uitsluit. AUTO/onbekend is geen bewijs van veilige extra koeling.
- Expliciete AAN/UIT, geen toggle, oude replay, onbegrensde retries of late callback die nieuwe toestemming creëert. Onbereikbaar blijft onbekend. Echte handmatige overname wordt gerespecteerd en hervatten vraagt een nieuwe actuele beoordeling.
- Harde fysieke-/bronlimieten gaan vóór minimale boostduur. Pauze/uitschakelen trekt alleen eigen SG-aanvraag in, niet native warmtepompbedrijf. Een native cyclus en verbruik kunnen doorgaan.
- P1/PV en elektrische grenzen gaan vóór forecast/leren. Actualiteit volgt bruikbare echte ontvangst/heartbeat; last_changed alleen is onvoldoende. Ontbrekend is niet nul. W/kW en tekenrichting worden gevalideerd.
- Eén bevestigde totaalmeter of twee bevestigde volledige niet-overlappende voedingen. Split totaal alleen bij twee actuele geldige W/kW-metingen; een bekende deelwaarde blijft zichtbaar bij ontbrekend totaal. Nul is nul. Geen totaal plus deelmeter/heater optellen. Native vermogen is niet volledig terugwinbaar door SG-UIT.
- SG is uitsluitend flexibele extra vraag, geen onaantastbare comfortreserve. Geen EV-krediet, afwas-, Wallbox- of noodzakelijk native comfort afnemen. Alleen lagere eigen werkelijk gemeten veilige onderbreekbare lasten mogen onder bestaande voorwaarden wijken.
- Centrale gebruikersvolgorde blijft behouden; oudere rangordemigratie niet opnieuw uitvoeren. Nieuwe gewone toestellen beginnen Uitgesloten. Beschermde programma’s, minimumtijden, bewuste overrides en deadlines houden hun eigen voorwaarden.
- Wallbox blijft read-only. Voorwaardelijk EV-krediet van andere bevoegde toestellen vergroot nooit elektrische capaciteit. De gehele nieuwe belasting moet vóór Wallbox-reactie passen.
- AEG alleen één native START per belading na geldige nieuwe APP-overgang. APP al Enabled bij startup is geen ticket. Geen PAUSE/RESUME/STOPRESET, programmakeuze, timerwrite of stekkeronderbreking. AirDry is geen einde; onzekere START niet herhalen.
- Batterijcommandobescherming, gebruikers-Pauze, onbekende/mengfouten en verwijderverzoeken blijven beschermd. Verwijderde DHW-/klimaatfouten worden hoogstens gericht als vervallen functie beoordeeld, nooit algemeen als fysiek opgelost.
- Migratie is idempotent, archiveert relevante oude configuratie/opslag privé en doet geen fysieke opdracht. Oude pending/eigendom/ACK/recovery/coast kan geen recht in de nieuwe runtime geven.
- Bewaar geldige instellingen, entity-identiteiten, modellen, bestaande meet-/historieretentie en echte tickets. Recorderuitsluiting betreft alleen zware herhaalde detailkopieën, niet live attributen, eigen opslag of export. Presentatiecache is nooit beslisinvoer.
- Meldingen zijn wijzigingsgestuurd, gericht en verdwijnen na herstel; transport mag regeling niet laten crashen. Gewone wait/rusttijd geeft geen foutspam. Oude DHW-/klimaatreviewacties bestaan niet meer.
- Geen privé-entiteiten, ruimtebenamingen, adressen, IP’s, tokens, exports, back-ups of persoonlijke opdrachtbestanden in publieke bron/pakketten. Gebruik fictieve voorbeelden en behoud lokale userfiles.
- Softwaretests/publicatie zijn geen live hardwareacceptatie. Fysiek proefdraaien gebeurt uitsluitend na expliciete toestemming, zonder metingen in geopende elektrische apparatuur.

## 4. Actuele werking

**Modi en restart.** Alleen bekijken berekent/registreert; Automatisch regelen voert toegestane eigen apparaatbediening uit; Pauze verhindert nieuwe starts en geeft eigen flexibele aanvragen veilig vrij. `auto_resume_after_restart` blijft standaard True, met bestaande afzonderlijke behandeling van observe/eerste installatie/interne fout/verwijdering en bewuste keuzes. De voorkeur wijzigen verandert de huidige modus niet. SG krijgt bij herstart geen replay of ingebruiknamerechten.

**SG.** Eén toestandmachine en één lokale Shelly-route. Defaults blijven startdrempel 3000 W, aparte raming 3200 W, startvertraging 120 s, stopvertraging 60 s, rust 900 s en sessie maximaal 3600 s. Lease 300 s/renew 60 s is apart begrensd tot de resterende sessie; geen nieuwe volle lease tegen het einde. ACK-marge kan aanvraag eerder eindigen. Een actieve boost hoeft de startinjectie niet te behouden; afname boven de buffer van standaard 300 W gedurende 60 s geeft alleen de eigen aanvraag vrij. Tijdens tekortcontrole geen vernieuwing. Native bedrijf blijft zelfstandig. Waarden zijn policy, geen gegarandeerd toestelvermogen.

**Profiel en herbeoordeling.** `dhw_only` behoudt de same-binding verse eindtankreferentie en ≥2 °C afkoeling, ≥2 nieuwe echte rapporten over 300 s na rust. Reload vraagt die bevestiging opnieuw. `general` vereist expliciete lokale profielbevestiging en gebruikt geen verplichte tankmeting. Completion-hold onderscheidt sessielimiet, native voltooid, geen aangetoonde opname en onbekende reactie; alleen passende voltooiingsbron kan voltooiing bewijzen. Iedere beëindigde/onderbroken algemene sessie bewaart nieuw-aanleidingswachtstand, ook bij lokale timerafloop, soft-source/netvrijgave of reload. Na rust vereist algemeen nieuw bewijs met ≥2 verse rapporten over 300 s: gewijzigde betrouwbare relevante native signature, of een nieuwe relevante actieve episode na eveneens bevestigd idle. Een echt nieuwe zonnepisode kan ook gelden: ≥2 verse rapporten/300 s met eligible surplus ≤hysteresis, daarna ≥2 verse rapporten/300 s vanaf startdrempel. De volledige startvertraging/actuele guards volgen opnieuw. Vastgelegde bewijsfasen blijven bewaard, lopende kandidaten vragen na reload nieuwe rapporten. Constante zon, dezelfde samples, rust/reload alleen geeft geen herstartlus. Een gewijzigde native read-binding rebased alleen de eerste verse referentie; latere werkelijke semantische verandering of nieuwe zon blijft nodig. Bij bevestigde omschakeling van oude tankhold blijft herkomst privé bewaard en is nieuw relevant native bewijs of een aantoonbaar nieuwe zonneperiode nodig. Echte manual/transport/safety-holds blijven staan.

**Extra koeling.** Algemene profielbevestiging en `cooling_protection_confirmed` zijn apart. Zonder bevestigde bestaande geschikte condens-/dauwpuntbeveiliging blokkeert general wanneer koeling mogelijk of onbekend is; AUTO is geen koel-onmogelijk bewijs. Verse expliciete betrouwbare context die koeling uitsluit kan passeren. Geen eigen koelwaterregeling of wijziging van lokaal ingestelde Panasonic-SG-waarden.

**Metingen/prioriteiten.** Volledige aansluiting P1 is waarheid. PV, batterijflow, beschermde afwasreserves, open opdrachttoezeggingen en fase-/piekgrenzen beperken toewijzing. Warmtepompmeterdekking wordt expliciet total/deelvoeding/split getoond; totaal alleen bij complete actuele gevalideerde splitmeting en lokale niet-overlapbevestiging, zonder heaterdubbeltelling. Native warmtepompbedrijf is niet-afschakelbaar verbruik. Extra SG volgt de bestaande flexibele rij en krijgt geen EV-krediet. Een lower-load-stopreserve wordt niet onmiddellijk vrije ruimte.

**Gewone lasten.** Ontvochtiger en andere eigen lasten behouden minimumlooptijd/rust, start/stopvertraging, mode, bron-/interlock-/opdrachtbevestiging en dagdoelen. Afwezige eerder beheerde lasten worden individueel geïsoleerd en bij bronherstel beoordeeld. Een gezonde andere last wordt niet door een uitsluitend vervallen warmtepompfout tegengehouden.

**Afwas/Wallbox.** AEG behoudt APP-edge/ticket/calendar, standaard 13:00, afzonderlijke optionele maandagdeadline, bewuste netaanvulling en maximaal één START. Beschermde cyclus blijft afwerken. Wallbox blijft autonoom; effectieve sessie en echte power zijn afzonderlijk nodig voor toegestane andere EV-overname. SG gebruikt alleen restzon.

**Planner/kosten/leren.** Bestaande niet-warmtepompplanning, PV-kalibratie, basislast, batterijscenario’s, kwartierpiek, dagkost, gewone historie en geauthenticeerde JSON.GZ-export blijven behouden. Oude thermische/tankmodellen zijn privé-archief/diagnose, geen actieve klimaat- of tankplanner. Géén leerreset of retentiewijziging.

**Interface/meldingen.** Eén compact Warmtepomp — Panasonic-regeling / SG-zonneboost, met aanvraag/eigenaar/reden, Shelly-stand/resterende lokale toestemming, echte compressor/native context, bekende voedingen/totaal en ontvangen SG-status. Details houden bewijslagen gescheiden; geen SG-effect afleiden uit compressorbedrijf. Native doelen/programma’s zijn uitlezing. Stabiele ids bewaren open details, scroll en formulieren. Na 1200 s echte actuele lage vermogensrapporten (≤100 W, uitsluitend diagnose) zonder bewezen draaiende compressor verschijnt eenmaal uptake_diagnostic in Details en op de bestaande begrensde tijdlijn; geen fout-/schakelrecht. Request/end, bevestigde relay reports en lease renew houden beschikbare context/metingen bij. PV/netkleuren en blauwe bewezen activiteit blijven behouden. `SolarPilot: controle nodig` bevat nog geldige toestel-/batterij-/interne/SG-koppelingsfouten; geen vervallen boilerreview.

## 5. Configuratie, integraties en belangrijke entiteiten

Publieke documentatie bevat uitsluitend generieke rollen. Koppel echte lokale entiteiten via HA-selectors; namen/schermafbeeldingen bewijzen dekking niet. `sg_boost` bevat één bestaande switchuitgang, enabled/commissioning/watchdog, `profile` (dhw_only/general), `profile_confirmed`, afzonderlijke `cooling_protection_confirmed` en behouden policy-/leasewaarden. `comfort_hub` gebruikt de bestaande sg_boost/sg_sources/sg_advanced-paden; geen nieuwe controller.

Read-only rollen: tank_temperature_entity, tank_target_entity, activity_entity, zone_entities, bestaande power_entity/power_scope, nieuwe power_supply1_entity/power_supply2_entity met split_power_confirmed, compressor_frequency_entity en sg_status_entity. Single-meterconfig blijft behouden. Split totaal vereist beide actuele plausibele nonnegatieve W/kW-waarden en volledige niet-overlap. Gelijke/reserved bronnen, bekende verklaarde brondependencies en inspecteerbare geladen template-overlap worden begrensd gecontroleerd; verborgen overlap blijft lokaal. Compressorbron moet een echte actuele sensor met Hz en plausibele waarde zijn; ontvangen-SG-bron heeft expliciete actief/inactief-semantiek, geen gegokte numerieke stand.

Andere blokken houden hun betekenis: P1/PV/prijs-/forecast, fasen, gewone devices, AEG, Wallbox en batterijen. De centrale gebruikersvolgorde blijft behouden. Nieuwe profiel- of splitvelden krijgen geen permission uit oude boiler enabled-, AUTO- of importingestellingen. Lokaal gekozen Panasonic-percentages/koelwaarden worden niet door SolarPilot geschreven of als publieke installatie-default bewaard.

`private_bundle.json` blijft optioneel uitsluitend lokaal in de bewaarde userfilesmap; lege geldige bronnen kunnen worden aangevuld, nooit nieuwe actuator-/profielrechten. HA-configuratie/eigen opslag staan buiten vervangen HACS-programmabestanden. `panasonic_archive` en migratiemarker bewaren read-only herkomst; de aangepaste algemene completion-hold behoudt relevante oude herkomst voor rollback. Geen fysieke migratiewrite of oude opdracht replay. Een complete passende privéback-up blijft noodzakelijk.

## 6. Belangrijke ontwerpbeslissingen + waarom

| Besluit | Reden |
| --- | --- |
| Native Panasonic exclusief eigenaar | Vermindert tegenstrijdige doelen, AUTO-keuzes en herstelwrites; comfort blijft autonoom. |
| Eén SG-commandoroute en centrale deny-grens | Generieke adapters/planners mogen de verwijderde writer niet opnieuw introduceren. |
| Lokale kortlopende toestemming | Een netwerkonderbreking is iets anders dan power-on; aanvraag moet zonder HA kunnen vervallen. |
| Aanvraag, relais en reactie apart | HA-serviceacceptatie of app-tankdoel bewijst geen fysieke SG-respons. |
| Bevestigd algemeen bereik naast tapwater-only | Verwijdert een onterechte permanente tankvoorwaarde zonder extra thermostaat of stilzwijgende toestemming. |
| Nieuwe aanleiding in plaats van periodieke herstart | Begrensde sessies blijven rustig, ook bij reload en constante zon zonder opnamebewijs. |
| Koelbeveiliging apart van profielkeuze | Gewenste extra koeling bewijst geen condensveiligheid; native beveiliging blijft extern bevestigd. |
| Complete bevestigde splitmeting | Voorkomt schijn-totaal, verborgen overlap en dubbele heater-/warmtepompwatts. |
| Geen totaal warmtepompvermogen als terugwinbaar | Normale native warmteproductie kan na SG-UIT blijven werken. |
| Migratiearchief buiten uitvoerende runtime | Behoud rollback/evidentie zonder oud pending/ACK-writepad. |
| Bestaande lijst en overige guards behouden | Gerichte vereenvoudiging, geen algemene herschrijving of reset. |
| Eén canonieke uitleg | HA, Markdown en releasehulp geven dezelfde actuele betekenis. |

## 7. Automatische processen

De gewone regelcyclus leest actuele bronnen en eigen actuatorstatussen, verzoent toegestane open opdrachten, registreert bruikbare data en beslist onder globale/per-device voorwaarden. Alleen de SG-adapter kan een SG-aanvraag vernieuwen, en uitsluitend voor de huidige geldige sessie. Pauze, rebind/unload of oude epoch maakt eerdere callbacks ongeldig. Bij crash/open communicatie blijft de lokaal ingestelde toestemming begrensd.

Planner, PV-diagnose, basislastleren, dagkosten en historie blijven onder hun bestaande cadans en retentie. Recorder/presentatiecorrecties bewaren volledige live-/eigen data en vermijden zware herhaalde kopieën. Geauthenticeerde export blijft on-demand lokaal. Meldingen volgen werkelijke veranderde controleoorzaken en worden bij afhandeling verwijderd; transportfout blokkeert de regelcyclus niet.

Startup-migratie archiveert eenmaal zonder fysieke actie. Alleen aantoonbaar uitsluitend vervallen actieve warmtepomp-opdrachtfouten verliezen hun blokkaderecht. Gerichte AEG-legacydetectie kan volgens haar bestaande begrensde same-device route een ontbrekend profiel herkennen, maar maakt geen belading. Een normale restart/isolation meldt automatische controle, geen verplichte generieke reset.

## 8. Geheimenbeleid

Publiek: generieke broncode, generieke vertalingen/help, fictieve testdata, actuele handleidingen, changelog en overdracht. Privé: userfiles, HA-back-ups, opslag/modelarchief, entitybindings, auth, netwerkgegevens, persoons-/locatiegegevens en ruwe analyse-export. Niets daarvan committen, in workflowlogs drukken of als release-asset opnemen. Een SG-installatieprompt met persoonlijke context blijft buiten repository en pakketten.

Geheimen komen uitsluitend uit bestaande HA-koppelingen/lokale configuratie; geen token in frontend of voorbeeld. Export blijft beheerdergeauthenticeerd, pseudonimiseert standaard namen en filtert gevoelige gegevens. Tijdstippen/gebruikspatronen blijven privé te beoordelen. Publieke preflight is noodzakelijk maar geen garantie dat ieder denkbaar privéveld automatisch wordt herkend.

## 9. Testprocedure + actuele teststatus

Definitieve volledige lokale pytest: **2932 geslaagd in 33,97 s op Python 3.12.14**. De aanvullende volledige run op **Python 3.14.2: 2932 geslaagd in 35,06 s**, met geïnstalleerde pytest-plugins bewust beperkt tot pytest_asyncio voor dezelfde unit/protocoldoubles. De onafhankelijke gerichte set heeft **430 geslaagde cases** en is onderdeel van de volledige teller. Opdracht conventionele run: `PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider`. Nieuwe resultaten en exacte bewijsgrenzen staan in `docs/TESTRESULTATEN_BETA64.md`; historische tellers worden niet als nieuw bewijs gebruikt.

De echte **Core 2026.10.0/Python 3.14.2** productie-entry setup/reload/unload is afzonderlijk geslaagd voor de legacyfixture (**2,017 s**) en actuele `--current-sg-fixture` (**1,927 s**). Beide laden zes echte platforms/58 registry-entiteiten, behouden configuratie en exact privéarchief, en geven 0 fysieke servicecalls/geen opgevangen exceptions. De actuele fixture bewaart geneste immutable opties en manual/completion/new-evidence-holds, valideert echte split W/kW/nul/ontbrekend/som en scheidt compressor/WATER/ontvangen-SG van causaal SG-effect. De ongewijzigde beta.62-baseline reproduceert haar verwachte mappingproxy-startfout in **1,877 s** met oorspronkelijke opties/Store intact. Alleen HTTP bind/start en source-IP discovery zijn voor offline proef vervangen; productie-entry/migratie/Store/platforms zijn echt.

De officiële Hassfest-logica van HA 2026.10.0 is daadwerkelijk geslaagd: **23 validators, 1 integratie, 0 ongeldig, 1,079 s**. Alleen multiprocessing-fork in plaats van de hier geblokkeerde forkserver is omgevingsaanpassing; validatielogica is ongewijzigd. Nieuwe unitregressies behouden authority/source/lease/restart/priority/phase/AEG/Wallbox/batterij/UI/Recorder/retentie/export. Geen nieuwe directe Panasonic-writes of op basis van lage W gestuurde contactpulsen.

Canonieke guide/hash/mirrors, handoff en publieke privacy-preflight zijn opnieuw gecontroleerd op de finale bron; guidehash `95d0991aef98b0fd`, 339 actuele helpentries. Node-/helpassetset heeft 67 geslaagde controles; de gerichte UI-set 152 geslaagde cases (geen extra teller boven de volledige suite). Repositorystructuur, SG-grens, Python-/JSON-syntax, beide JavaScriptbestanden via Node en diffgate zijn eveneens geslaagd. Werkelijke browserrender is niet uitgevoerd: geen bruikbare browserbinary/download; pakketinstallatiefallback werd door automatische goedkeuringscontrole afgewezen. Geen claim van visuele browseracceptatie. Softwareproeven zijn geen live woning-, wifi-, Shelly-/Panasonic- of condensbeveiligingsproef.

Publicatie blijft gebonden aan groene repository-, HACS-, Hassfest- en real-ha-startup-CI, inclusief actuele general/splitfixture. HACS gebruikt echte CI; lokaal geen Docker. Beide ZIPs en vier werkelijk gedownloade assets moeten bytegelijk/SHA-256/grootte tegen de exacte annotated-tagbron worden gecontroleerd. Oude tags/assets worden niet vervangen. Dit dossier claimt geen toekomstige CI-/uploadsuccessen; de workflow en oplevering vermelden het exacte publicatiebewijs.

## 10. Bekende problemen / beperkingen

Geen live HA-installatie, Shellyfirmware, fysieke Panasonicreactie, meterdekking of condensbeveiliging is in deze bronwerkrondes geïnspecteerd. Externe writers zijn zonder lokale inzage niet bewezen afwezig. Timerondersteuning, mapping, algemeen bereik, niet-overlap en geschikte bestaande beveiliging moeten lokaal blijken. Een oudere native instelling wordt niet via herstelwrite teruggezet.

De historische stilstand en later zichtbaar compressorbedrijf hebben geen vastgestelde oorzaak. Niet bekend is of alleen het SG-contact of ook Panasonic werd uit-/aangezet, noch of tussendoor modus/menu/native vraag veranderde. Verschillende meetmomenten zonder passende logs bewijzen geen contactflankprobleem, SolarPilot-fout of SG-veroorzaakte start. Geen automatische pulsen of rebootoplossing hiervoor.

Een partieel gemeten vermogen is geen totaal. Een ontvangen SG-stand of compressorfrequentie bewijst niet hoeveel extra verbruik SG veroorzaakt. Voeding 1 is niet uitsluitend compressor; voeding 2 is alleen heater bij bevestigde dekking. SG-UIT stopt native bedrijf niet gegarandeerd en maakt gemeten watts niet onmiddellijk beschikbaar. Geen universele SG-formule, nulimportbelofte of garantie van compressor-only. Een lokale timer is geen elektrische beveiliging.

Nieuwe algemene beoordeling vereist rust en betekenisvol nieuw zon-/native bewijs; dezelfde samples/reload/tijd is onvoldoende. Zonder bruikbaar bewijs blijft beleidswacht staan, bewust hervatten na controle blijft mogelijk. Nieuwe lokale profielbevestiging wist echte handmatige/transport/veiligheidsblokkering niet. Bestaande historie/onderzoeksregistratie behoudt perioden/aantallimieten; geen onbeperkt archief/backfill.

## 11. Concrete openstaande ontwikkeling

De gerichte beta.64-software en actuele documentatie zijn afgerond. Beide volledige Python-suites, echte Core-fixtures, verwachte historische startupbaseline en officiële Hassfest zijn geslaagd; resultaten staan in het beta.64-testverslag. CI-/publicatie-/pakketverificatie blijft een afzonderlijke opgelegde releasegate. Werkelijke browserrender is in deze omgeving niet uitgevoerd; Node-/gerichte UI-controles claimen geen visuele acceptatie.

Fysieke lokale ingebruikname blijft open: privéback-up, native basis, externe writercontrole, juiste uitgang/transport, expliciet toepassingsbereik, contactmapping, bevestigde splitdekking en afzonderlijke condensbeveiliging. Vervolgens uitsluitend na expliciete toestemming lokale timerproef (verlengen zonder schakelen en echte afloop zonder HA) en natuurlijke SG-sessie. Geen geopende elektrische apparatuur, Panasonic-doel-/modustest of extra hardware.

De historische uit-/aanoorzaak blijft een open diagnosepunt. Objectieve profiel-/meetverbeteringen vereisen geen gok over die oorzaak. Toekomstige code mag geen direct Panasonic-writepad, tweede regeling, pulstruc of andere huidige regelbeschrijving invoeren. Bestaande behouden apparaatfuncties vereisen geen nieuwe hardware/controller; de releasewijziging blijft gericht op SG-bereik, nieuw bewijs en uitlezing.

## 12. Installatie/upgrade en rollback

Volledige privé HA-back-up vóór codeupdate, inclusief configuratie, eigen opslag, modellen, userfiles en herstelgegevens. Controleer native basis en laat beschermde cycli behouden; geen extra APP-aanvraag als updateproef. Beta.64 behoudt beta.63 immutable/geneste-optiesfix; bestaande entry niet verwijderen/hermaken.

HACS Integration naar exact beta.64 zodra gepubliceerd, volledige HA-herstart en browser/app heropenen. Backend-/kaartversie apart controleren. Lokaal uitsluitend `custom_components/solar_pilot` vervangen, userfiles/opslag bewaren. Nieuwe profiel-/split-/koelrechten worden niet automatisch bevestigd of geactiveerd. Behouden single-meterconfig blijft geldig. Migratie doet geen fysieke opdracht. Handleiding: `docs/BETA64_INSTELLEN.md`.

Rollback naar gecontroleerde beta.63 vereist code én de bij deze upgrade passende volledige privéback-up; alleen ZIP herstelt nieuwe opslag-/bewijsvelden niet exact. Eerst eigen SG-aanvraag vrijgeven en geopende stand/lokale terugval controleren, nieuwe runtime/vernieuwers stoppen, dan passende code en back-up terugzetten. Geen twee runtimes tegelijk. Terugkeer naar oude directe beta.61 blijft code én de volledige pre-beta.62-migratieback-up vereisen. Read-only herkomst is geen complete restore of fysieke replay.

## 13. Belangrijkste bestanden

- `runtime.py`: globale modus, bron-/toestelcoördinatie, data, presentatie en overige behouden actuators.
- `sg_config.py`, `sg_boost.py`, `sg_transport.py`: één toegewezen uitgang, begrensde policy en lokale toestemming; geen Panasonic-setpointbediening.
- `panasonic_authority.py`: centrale weigering van gebonden Panasonic-/SG-writes door andere SolarPilot-eigenaren; `panasonic_monitor.py` leest native bronnen zonder actuatorrecht.
- `panasonic_migration.py`: read-only archive/assessment, oude writerschema’s uitsluitend voor migratie.
- `config_flow.py`, `live_config.py`, `first_install.py`, `private_bundle.py`: nieuwe SG-opties, single-ownervalidatie en behoud overige gebruikersdata.
- `heatpump_budget.py`: read-only native warmtepompvermogen en enkelvoudige flexibele SG-begroting; geen oud comfortwriterbudget.
- `adapters.py`, `engine.py`, `dishwasher_runtime.py`, batterijmodules: behouden gewone/start-only/batterijbevoegdheden met commandobescherming.
- `action_notifications.py`: gerichte resterende controles, zonder vervallen DHW-/klimaatreview.
- `current_guide.py`, `option_help.py`, `frontend/option-help.json`, `translations/*`: releasegebonden huidige uitleg.
- `frontend/solar-pilot-card.js`: compacte SG-weergave en bestaande stabiele status/details/popupbediening.
- `analysis_export.py`, leer-/PV-/planner-/historiecomponenten: nuttige analysefuncties, eigen data en on-demand privé-export.
- `tools/check_real_ha_startup.py`: echte Core 2026.10-entrygrens, bekende beta.62-fout en productie setup/reload/unload zonder netwerkstart of fysieke servicecalls.
- `docs/ACTUELE_WERKING.md` en embedded mirror: uitsluitend gegenereerd; installatie/testverslag dezelfde mirrorregels.
- `tools/check_public_repository.py`, `check_handoff.py`, `check_current_explanation.py`, `update_current_explanation.py`, `update_option_help.py`, `check_release_packages.py`, `validate_repository.py`: releasegates.

## 14. Release-checklist

1. Verifieer actuele GitHub-basis/vrije versie en gebruik een eigen branch, zonder oude tags/assets te veranderen.
2. Bewijs met onveranderbare HA-opties dat runtime en migratie hun configuratie zonder verlies lezen; behoud de idempotente private SG-migratie zonder fysieke writes/replays of gegevensreset.
3. Handhaaf de bestaande SG-only bevoegdheidsgrens en alle overige apparaatfuncties; maak geen nieuwe native tank-/klimaatwriter.
4. Voer volledige toepasselijke suite plus mapping, source-/units-/lease-/state-/UI-regressies uit.
5. Werk canonieke guide, gegenereerde mirrors/help, versie, changelog, dit dossier, installatie/testverslag/rollback samen bij.
6. Voer privacy, structuur, handoff, hash/mirror, syntax en diffgates uit. Geen privéprompt/config/log in pakket.
7. Publiceer uitsluitend de geteste commit na repository-, HACS-, Hassfest- én real-ha-startup-gate; controleer de nieuwe CI en immutable annotated tag afzonderlijk.
8. Download alle vier assets, controleer grootte/SHA-256 en beide ZIP-inhoud bytegelijk met de exacte commit.
9. Scheid releasecontrole, geladen HA/backend/kaart en fysieke Shelly-/Panasonicproef. De laatste blijft expliciet lokale ingebruikname.

## 15. AI-handoff

Lees dit dossier, manifest, huidige guide en beta.64-installatie/testverslag vóór een vervolg. De nieuwe hoofdgrens is **Panasonic read-only, één gecontroleerde SG-uitgang als enige warmtepompactuator**. Reanimeer geen oude tank-/AUTO-controller of temperatuur-ACK-regel om een historisch testgeval groen te maken. Bewaar andere bestaande functies, gebruikersvolgorde, AEG-START-semantiek, batterijbescherming en privédata.

Controleer actuele GitHub-main/tag vóór verdere wijziging. Houd native comfort/sterilisatie autonoom, meterdekking/eenheden en echte bronversheid expliciet en eigen boostpermission lokaal begrensd. Een upload, serviceacceptatie, appdoel of unittestrun is geen bewezen fysiek SG-effect. Persoonlijke installatiecontext wordt niet publiek opgeslagen. Nieuwe codewijziging vereist dezelfde complete huidige uitleg, overdracht, test-/installatie-/rollback-/pakketgates.
