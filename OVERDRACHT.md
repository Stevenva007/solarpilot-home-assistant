<!-- solarpilot-handoff-schema: 1 -->
<!-- solarpilot-handoff-version: 1.0.0-beta.62 -->

# OVERDRACHT — SolarPilot

Laatst bijgewerkt: **10 oktober 2026**. Actuele bron: **v1.0.0-beta.62**. Panasonic is exclusief eigenaar van zijn warmtepompregeling; SolarPilot mag daarvoor uitsluitend één expliciet toegewezen SG-contact aanvragen/vrijgeven. De voormalige directe tank-/klimaatsturing en haar uitvoerende herstelcomplexiteit zijn verwijderd. Andere apparaatfuncties en bestaande privédata blijven behouden. Werkelijke software-/publicatiestatus staat in `docs/TESTRESULTATEN_BETA62.md`; ingebruikname, installatie en rollback in `docs/BETA62_INSTELLEN.md`. Geen live fysieke acceptatie is uit deze softwarewerkrondes af te leiden.

## 1. Projectdoel in gewone taal

SolarPilot verdeelt beschikbare zonnestroom tussen flexibele verbruikers, een beschermde afwasmachine, autonoom autoladen en optionele extra warmwaterproductie via SG. Het combineert actuele P1/PV, fysieke fase-/netgrenzen, voorspellingen, basislast, kosten, lokaal leren en begrijpelijke beslisredenen. Panasonic verzorgt zelfstandig comfort en beveiligingen, ook zonder SolarPilot. Eén overzicht vertelt wat actief is, wacht of gerichte controle nodig heeft.

## 2. Actuele basis

De geverifieerde minimum-, bouw- en rollbackbasis is [beta.61](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.61), commit `6c7e77b75e09b1c8bc9c4b24e7b9ce693b4a974d`, tree `7aecb76027e3c1c5cd3de6d22d10b4cd9a3b6a04`. Aan het begin van deze wijziging waren `main` en tag gelijk; beta.62 was vrij. Deze bronbasis is zelfstandig opnieuw getest: 3814 tests geslaagd in 49,76 s. De baseline en nieuwe toepasselijke suite worden afzonderlijk geregistreerd in het beta.62-testverslag.

Ontwikkeling gebeurt op een aparte branch vanaf deze bron. Bestaande tags, release-assets en andermans werk blijven ongewijzigd. Een lager aantal tests na bewuste functieverwijdering is alleen verantwoord met een mapping van behouden, vervangen en vervallen contracten; een oud uitvoeringspad blijft niet leven om de teller te behouden.

De canonieke gebruikersuitleg is `custom_components/solar_pilot/current_guide.py`; `docs/ACTUELE_WERKING.md` en de ingebedde mirror worden gegenereerd. Dit dossier beschrijft actuele technische waarheid. Historische temperatuur-/AUTO-regels horen bij oudere versies in CHANGELOG/Git, niet bij deze actieve regeling. Er is geen extra CURRENT.json/LATEST-mechanisme toegevoegd.

## 3. Absolute ontwerpregels

- Voor Panasonic uitsluitend de toegewezen bestaande SG-uitgang; Panasonic-entiteiten verder read-only. Geen set_temperature, AUTO/OFF, HEAT/COOL, Powerful/Force, kamertemperatuur-, stooklijn-, heater- of herstelwrite, ook niet via generieke helpers, scripts, planner, opstart, Pauze, unload of verwijdering.
- Panasonic bezit normaal warm water, hysterese, ruimte-/zoneregeling, compressor, kleppen, pompen, ontdooien, elektrische ondersteuning en sterilisatie. Geen tweede heaterrelais of nieuwe hardware-/DIP-functie.
- Eén actuator heeft één eigenaar. Het gekozen SG-contact kan geen gewone flexlast- of batterijactuator zijn. Geladen gewone/batterijscripts worden per dispatch statisch op vaste onafhankelijke doelen gecontroleerd; niet inspecteerbare inhoud/dynamische/proxydoelen zijn geblokkeerd. Geen bewijs over externe dubbele writers zonder afzonderlijke lokale inzage.
- Automatische SG staat standaard uit. Uitgang, mapping, Panasonic-reactie/native basis, geen dubbele sturing en echte lokale aflooptimer moeten bevestigd zijn. Een globale Auto-/hervatvoorkeur vervangt dit bewijs niet.
- Een opdracht is geen bevestiging. Aanvraag, gemelde relaisstand/lokale toestemming en fysieke Panasonic-reactie blijven gescheiden. Een normaal app-tankdoel bewijst geen effectieve SG-temperatuur; stijgende tanktemperatuur alleen bewijst geen eigenaar.
- Lokale communicatietoestemming standaard 300 s, vernieuwing 60 s zonder fysieke uit/aan-cyclus. Power-on UIT geldt alleen herstart, niet wifi-uitval. Geen werkende geteste terugval: geen automatische SG.
- Expliciete AAN/UIT, geen toggle, oude replay, onbegrensde retries of late callback die nieuwe toestemming creëert. Onbereikbaar blijft onbekend. Echte handmatige overname wordt gerespecteerd en hervatten vraagt een nieuwe actuele beoordeling.
- Harde fysieke-/bronlimieten gaan vóór minimale boostduur. Pauze/uitschakelen trekt alleen eigen SG-aanvraag in, niet native warmtepompbedrijf. Een native cyclus en verbruik kunnen doorgaan.
- P1/PV en elektrische grenzen gaan vóór forecast/leren. Actualiteit volgt bruikbare echte ontvangst/heartbeat; last_changed alleen is onvoldoende. Ontbrekend is niet nul. W/kW en tekenrichting worden gevalideerd.
- Warmtepompvermogen slechts eenmaal tellen. Deelvoeding is geen totaal; al inbegrepen heater niet toevoegen. Het hele warmtepompvermogen is niet terugwinbaar door SG uit. Toekomstige ruimte pas na bevestigde vrijgave en nieuwe metingen toekennen.
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

**SG.** Eén kleine toestandmachine: normaal, wachten, aangevraagd, rusttijd, geblokkeerd. Nieuwe standaardwaarden: startdrempel 3000 W, afzonderlijke raming 3200 W, startvertraging 120 s, stopvertraging 60 s, rust 900 s, sessie maximaal 3600 s. Lease 300 s/renew 60 s beschermt communicatie onafhankelijk van de langere sessie en wordt altijd tot de resterende sessie begrensd; tegen het einde geen nieuwe volle lease. De ingestelde ACK-marge kan de aanvraag iets eerder laten eindigen. Een actieve toegelaten boost hoeft de oorspronkelijke restinjectiedrempel niet te houden; netafname boven de afzonderlijke buffer van standaard 300 W gedurende 60 s geeft de eigen aanvraag vrij. Tijdens die tekortcontrole wordt de lease niet vernieuwd. Deze waarden zijn beleidsdefaults, geen fabrikantvermogen of gegarandeerd totaal. De adapter gebruikt alleen de gekozen lokale Shelly-route. Stop opent de eigen aanvraag; geen native reset/doelwijziging. Ingebruikname blijft expliciet uit tot lokaal bewijs bestaat. Max-session/geverifieerde voltooiing zet een opgeslagen completion hold en alleen bij geldige same-binding eindtankmeting een referentie. Na rust laat ≥2 °C gemeten afkoeling, bevestigd door ≥2 nieuwe echte rapporten over 300 s, een verse zonbeoordeling toe. Dit bewijst extra opslagruimte, geen comfortvraag/SG-succes/SG-doel. Na reload moet de vijfminutenbevestiging met nieuwe rapporten opnieuw plaatsvinden en ook de volledige startvertraging/actuele guards gelden. Geen referentie, bronwisseling of ongeldige data houden vast; bewuste Resume blijft mogelijk na controle. Restart/rust alleen heft dit niet op. Gewone importvrijgave kan na rust opnieuw worden beoordeeld.

**Metingen/prioriteiten.** Volledige aansluiting P1 is waarheid. PV, batterijflow, beschermde afwasreserves, open opdrachttoezeggingen en fase-/piekgrenzen beperken toewijzing. Warmtepompmeterdekking wordt expliciet total/deelvoeding getoond, zonder heaterdubbeltelling. Native warmtepompbedrijf is niet-afschakelbaar verbruik. Extra SG volgt de bestaande flexibele rij en krijgt geen EV-krediet. Een lower-load-stopreserve wordt niet onmiddellijk vrije ruimte.

**Gewone lasten.** Ontvochtiger en andere eigen lasten behouden minimumlooptijd/rust, start/stopvertraging, mode, bron-/interlock-/opdrachtbevestiging en dagdoelen. Afwezige eerder beheerde lasten worden individueel geïsoleerd en bij bronherstel beoordeeld. Een gezonde andere last wordt niet door een uitsluitend vervallen warmtepompfout tegengehouden.

**Afwas/Wallbox.** AEG behoudt APP-edge/ticket/calendar, standaard 13:00, afzonderlijke optionele maandagdeadline, bewuste netaanvulling en maximaal één START. Beschermde cyclus blijft afwerken. Wallbox blijft autonoom; effectieve sessie en echte power zijn afzonderlijk nodig voor toegestane andere EV-overname. SG gebruikt alleen restzon.

**Planner/kosten/leren.** Bestaande niet-warmtepompplanning, PV-kalibratie, basislast, batterijscenario’s, kwartierpiek, dagkost, gewone historie en geauthenticeerde JSON.GZ-export blijven behouden. Oude thermische/tankmodellen zijn privé-archief/diagnose, geen actieve klimaat- of tankplanner. Géén leerreset of retentiewijziging.

**Interface/meldingen.** Eén compact Warmtepomp — Panasonic-regeling, met Automatische zonneboost, exacte backendreden, tanktemperatuur, bekende W/dekking en Details voor afzonderlijke bewijslagen. Native doelen/programma’s zijn uitlezing. Stabiele ids bewaren open details, scroll en formulieren. PV/netkleuren en blauwe bewezen activiteit blijven behouden. `SolarPilot: controle nodig` bevat nog geldige toestel-/batterij-/interne/SG-koppelingsfouten; geen vervallen boilerreview.

## 5. Configuratie, integraties en belangrijke entiteiten

Publieke documentatie bevat uitsluitend generieke rollen. Koppel lokale entiteiten via HA-selectors; verzin geen entity_id. `sg_boost` beschrijft precies één bestaande switchuitgang, enabled/commissioning/watchdog-bevestiging en begrensde policy-/leasewaarden. `comfort_hub` bevat `sg_boost`, `sg_sources` en `sg_advanced`. Monitorrollen zijn tanktemperature, native tanktarget, totaal/deelvoedingspower, activity en zones. De power_scope is unconfirmed/total/supply1/supply2; onbekende dekking is geen totale meter.

Andere bestaande blokken houden hun betekenis: P1/PV/prijs-/forecastbron, fasemetingen, gewone devices, AEG-bronrollen, Wallbox effectieve sessie/vermogen en batterijprofielen. Gebruikersvolgorde/toestemmingen blijven in de centrale lijst. Nieuwe SG-koppeling krijgt geen permissie uit een oude boiler enabled- of klimatoverrideoptie. Oude threshold/raming staan als kandidaten in het private archief; de nieuwe SG-waarden worden afzonderlijk beoordeeld en SG-ingebruikname moet bewust bevestigd blijven.

`private_bundle.json` blijft optioneel uitsluitend lokaal in de bewaarde userfilesmap. Het kan lege geldige bronnen aanvullen, nooit automatische SG of nieuw actuatorrecht activeren. Home Assistant-configuratie en eigen opslag staan buiten de vervangen HACS-programmabestanden. `panasonic_archive` bewaart de versiegebonden read-only migratiesnapshot en beoordeling; `_panasonic_migration` voorkomt herhaalde omzetting. Een volledige pre-upgrade-back-up blijft nodig voor exact rollbackherstel.

## 6. Belangrijke ontwerpbeslissingen + waarom

| Besluit | Reden |
| --- | --- |
| Native Panasonic exclusief eigenaar | Vermindert tegenstrijdige doelen, AUTO-keuzes en herstelwrites; comfort blijft autonoom. |
| Eén SG-commandoroute en centrale deny-grens | Generieke adapters/planners mogen de verwijderde writer niet opnieuw introduceren. |
| Lokale kortlopende toestemming | Een netwerkonderbreking is iets anders dan power-on; aanvraag moet zonder HA kunnen vervallen. |
| Aanvraag, relais en reactie apart | HA-serviceacceptatie of app-tankdoel bewijst geen fysieke SG-respons. |
| Totaal/deelvoeding expliciet | Voorkomt schijn-totaal en dubbele heater-/warmtepompwatts. |
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

Uitgevoerd onder de aanwezige Python-runtime met `PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider`. De verse beta.61-baseline heeft 3814 geslaagde tests in 49,76 s. De definitieve volledige toepasselijke beta.62-suite heeft **2809 geslaagde tests in 31,45 s**, inclusief de laatste sessie-/atomicity- en publicatieworkflowregressies. De contractmapping onderscheidt behoud, SG-/migratievervanging en bewust obsolete directe Panasonic-functie. Behouden AEG/Wallbox/batterij/ordinary/Recorder/export/priority-dekking is in deze gate gecontroleerd.

Controleer nul Panasonic-writes vanuit alle actieve routes, één SG-eigenaar, lease-renewal zonder toggle, timerverloop, oude ACK/callback/restart, bronunits/versheid/heartbeat, fasegrens, import en blijvend native verbruik, gedeeltelijke meter en dubbeltelling. Ook idempotente migratie, gemengde fouten, opgeslagen Pauze/hervatkeuze, manual override, lokale meldingen en stabiele UI horen bij de gate.

Publieke preflight, SG-grens, handoff/guidehash/mirrors, optiehulp, repositorystructuur, Python-/JS-/JSON-syntax en `git diff --check` zijn geslaagd. Guidehash: `22d95cd9bbdeeab5`; 68 Python-productiemodules gecontroleerd. Nieuwe CI, annotated tag, release-assets/SHA-256 en beide ZIP-inhouden moeten afzonderlijk exact met de geteste bron overeenkomen. Het publicatiepad valideert beide ZIPs vóór upload en alle vier gedownloade assets erna, ook bij bestaande-tagretry. Definitieve lokale aantallen/resultaten en externe bewijsplaatsen staan in `TESTRESULTATEN_BETA62.md`. Volledige browser/renderacceptatie is niet uitgevoerd wegens ontbrekende Chromium/afgebroken download; fysieke Panasonic/Shelly-acceptatie blijft een afzonderlijke lokale stap.

## 10. Bekende problemen / beperkingen

Geen live Home Assistant-, Shellyfirmware- of fysieke Panasoniccontrole uitgevoerd in deze bronwerkrondes. Native timerondersteuning/mapping en feitelijke SG-reactie moeten lokaal blijken vóór activering. Externe automatiseringen zijn zonder live inzage niet geïnspecteerd. Een oude native doel-/zonestand kan achtergebleven zijn; softwareverwijdering herstelt die niet automatisch.

Een partieel gemeten warmtepompvermogen is geen bewezen totaal. SG-UIT betekent geen onmiddellijke compressorstop, geen gegarandeerd nulimport en geen gegarandeerd compressor-only bedrijf. Een lokale timer is geen elektrische beveiliging of garantie tegen mechanisch vastgelast contact. Geen universele SG-temperatuurformule in code. Nieuwe beoordeling na de maximale sessie vraagt betrouwbare nieuwe same-binding tankafkoeling ten opzichte van de eindmeting. Zonder bruikbaar bewijs blijft de wachtstand staan; bewuste hervatting na controle is dan de mogelijke route.

Bestaande historie/onderzoeksregistratie heeft haar eerdere perioden/aantallimieten; meer schijfruimte maakt haar niet onbeperkt. Geen backfill of herstel van eerder niet opgeslagen Recorderattributen. Een testfixture is geen live hardwarebewijs; een geverifieerd releasepakket is geen bewijs van geladen mobiele kaart.

## 11. Concrete openstaande ontwikkeling

De beschreven softwarewijziging en lokale regressiegate zijn voltooid. Publicatiecontrole en fysieke lokale ingebruikname blijven afzonderlijke stappen; er is geen live installatiebewijs uit de softwaretests.

Voor lokale ingebruikname: volledige privéback-up, native basis op Panasonic controleren, inspectie externe writerconflicten, juiste uitgang/transport selecteren, contactmapping controleren en de lokale timer inclusief verlengen zonder schakelen en aflopen zonder HA bewijzen. Laat automatische SG tot die controles uit. Voer fysieke proef uitsluitend met expliciete toestemming uit.

Andere bestaande regeling kan onder haar eigen geldige instellingen werken. Uitgebreidere SG/Panasonic-reactiemeting is optioneel read-only; onbekend bewijs blijft onbekend. Nieuwe toekomstige code mag geen direct Panasonic-writepad of tweede huidige regelbeschrijving invoeren. Herhaal toepasselijke regressies bij iedere vervolgwijziging.

## 12. Installatie/upgrade en rollback

Volledige privé HA-back-up **vóór** de codeupdate, inclusief configuratie, eigen opslag, userfiles en benodigde restore-informatie. Controleer bestaande native instellingen; een oude SolarPilot-start/OFF/doel kan niet door de nieuwe runtime worden teruggezet. Laat een beschermde cyclus afwerken of behoud haar lopende status; geen extra APP-aanvraag als updateproef.

HACS installeert deze Integration; herstart HA en heropen browser/app. Controleer backend-/kaartversie apart. Lokale installatie vervangt uitsluitend `custom_components/solar_pilot`, bewaart userfiles en opslag. Migratie doet geen fysieke opdracht; SG blijft uit. Stel bronnen in en voer alleen de toegestane lokale read-only controles, vervolgens na expliciete toestemming de fysieke ingebruikname uit. Handleiding: `BETA62_INSTELLEN.md`.

Rollbackbasis beta.61 vereist de passende **pre-migratie privé-opslag/back-up**, niet alleen haar ZIP. Trek eerst de eigen SG-aanvraag in en bevestig open contact/lokale terugval. Stop nieuwe SG-runtime/vernieuwers voordat de oude schrijvers terugkomen. Herstel code én passende back-up, gewenste globale modus/hervatkeuze, controleer native basis en voorkom oud/nieuw tegelijk. Gearchiveerde data ondersteunen beoordeling, maar zijn geen automatische fysieke replay of complete HA-back-up.

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
- `docs/ACTUELE_WERKING.md` en embedded mirror: uitsluitend gegenereerd; installatie/testverslag dezelfde mirrorregels.
- `tools/check_public_repository.py`, `check_handoff.py`, `check_current_explanation.py`, `update_current_explanation.py`, `update_option_help.py`, `check_release_packages.py`, `validate_repository.py`: releasegates.

## 14. Release-checklist

1. Verifieer actuele GitHub-basis/vrije versie en gebruik een eigen branch, zonder oude tags/assets te veranderen.
2. Archiveer privébeta.61-schema’s idempotent; bewijstest nul oude fysieke writes/replays en geen algemene fout-/gegevensreset.
3. Verwijder actieve tank-/klimaatwriters/opties/timers/herstelroutes echt; handhaaf centrale SG-onlygrens en overige apparaatfuncties.
4. Voer volledige toepasselijke suite plus mapping, source-/units-/lease-/state-/UI-regressies uit.
5. Werk canonieke guide, gegenereerde mirrors/help, versie, changelog, dit dossier, installatie/testverslag/rollback samen bij.
6. Voer privacy, structuur, handoff, hash/mirror, syntax en diffgates uit. Geen privéprompt/config/log in pakket.
7. Publiceer uitsluitend geteste commit; nieuwe CI en immutable annotated tag afzonderlijk controleren.
8. Download alle vier assets, controleer grootte/SHA-256 en beide ZIP-inhoud bytegelijk met de exacte commit.
9. Scheid releasecontrole, geladen HA/backend/kaart en fysieke Shelly-/Panasonicproef. De laatste blijft expliciet lokale ingebruikname.

## 15. AI-handoff

Lees dit dossier, manifest, huidige guide en beta.62-installatie/testverslag vóór een vervolg. De nieuwe hoofdgrens is **Panasonic read-only, één gecontroleerde SG-uitgang als enige warmtepompactuator**. Reanimeer geen oude tank-/AUTO-controller of temperatuur-ACK-regel om een historisch testgeval groen te maken. Bewaar andere bestaande functies, gebruikersvolgorde, AEG-START-semantiek, batterijbescherming en privédata.

Controleer actuele GitHub-main/tag vóór verdere wijziging. Houd native comfort/sterilisatie autonoom, meterdekking/eenheden en echte bronversheid expliciet en eigen boostpermission lokaal begrensd. Een upload, serviceacceptatie, appdoel of unittestrun is geen bewezen fysiek SG-effect. Persoonlijke installatiecontext wordt niet publiek opgeslagen. Nieuwe codewijziging vereist dezelfde complete huidige uitleg, overdracht, test-/installatie-/rollback-/pakketgates.
