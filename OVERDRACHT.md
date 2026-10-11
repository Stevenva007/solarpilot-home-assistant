<!-- solarpilot-handoff-schema: 1 -->
<!-- solarpilot-handoff-version: 1.0.0-beta.69 -->

# OVERDRACHT — SolarPilot

Laatst bijgewerkt: **11 oktober 2026**. Actuele bron: **v1.0.0-beta.69**. Panasonic beheert zijn native regeling; SolarPilot gebruikt uitsluitend de bestaande toegewezen SG-uitgang. Deze versie telt betrouwbaar gemeten warmtepompverbruik mee voor de SG-zonnestartdrempel, bewaart de afzonderlijke echte elektrische grenzen en verbetert taak-, meet- en leerbewijs. Actuele test-/publicatiestatus: `docs/TESTRESULTATEN_BETA69.md`; upgrade en rollback: `docs/BETA69_INSTELLEN.md`. Fysieke gebruikersacceptatie is niet uit softwaretests afgeleid.

## 1. Projectdoel in gewone taal

SolarPilot verdeelt beschikbare zonnestroom tussen flexibele verbruikers, een beschermde afwasmachine, autonoom autoladen en optionele extra opname via één lokaal bevestigde SG-zonneboost warmtepomp. Het combineert actuele P1/PV, fysieke fase-/netgrenzen, voorspellingen, basislast, kosten, lokaal leren en begrijpelijke beslisredenen. Panasonic verzorgt zelfstandig comfort en beveiligingen, ook zonder SolarPilot. Eén overzicht vertelt wat actief is, wacht of gerichte controle nodig heeft.

## 2. Actuele basis

Bouwbasis: gepubliceerde beta.68, main-commit `bb8852d6516fd6df4b79a5dac79263648b2e4499`, tree `c96a5b743250ca157e7f440e1eee308e2cea8e71`. GitHub main en release v1.0.0-beta.68 zijn bij aanvang gecontroleerd. Oude tags/assets blijven ongewijzigd. Dit is bronherkomst, geen nieuwe beta.69-validatie.

De canonieke gebruikersuitleg blijft `custom_components/solar_pilot/current_guide.py`; `docs/ACTUELE_WERKING.md`, de ingebedde mirror en optiehulp worden gegenereerd. Dit dossier beschrijft actuele waarheid; historische ontwikkeling staat in CHANGELOG/Git en eerdere releaseverslagen. Beta.63 immutable/geneste HA-opties, beta.64 SG-profiel/reassessment, beta.65–68 read-only bronnen/interface en analyse-/antwoordrapport blijven behouden. Vier concrete generieke voorstel-ID's hebben na implementatie/regressies een vertrouwde beta.69-registervermelding; een import kan die status niet zelf creëren.

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
- De SG-startdrempel mag de complete actuele bevestigde warmtepompbijdrage in de gemeten zonnebalans meetellen. Dit is uitsluitend starteligibiliteit: bestaande watts blijven in P1, geven geen fysiek vermogen terug en verlagen de aparte extra-vraagraming niet. Netafname, batterijontlading, reserves, PV-cap en beschermde hogere verbruikers blijven gelden.
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

**Modi en eigenaren.** Alleen bekijken registreert; Automatisch regelen gebruikt uitsluitend bestaande toegestane writers; Pauze geeft eigen aanvragen veilig vrij. Hervatten na herstart behoudt de bestaande afzonderlijke guards en geeft SG geen replay of nieuwe ingebruiknamerechten. Eén actuator heeft één eigenaar. Panasonic en Wallbox zijn read-only; één toegewezen SG-contact is de enige warmtepompactuator.

**SG-zonnebijdrage.** `sg_solar_budget.available_w` blijft werkelijk resterend overschot na beschermde reserves. `eligible_w` is de gemeten gezamenlijke zonnebijdrage voor starten: complete actuele exclusieve HP-totalen worden gecombineerd met conservatieve netbalans, batterijontlading en reserves, begrensd door gemeten PV. `hp_solar_w` is de extra afgeleide bijdrage aan die startbegroting, geen apart gemeten fysiek PV-aandeel. Onvolledige/oude/niet bevestigde/overlappende HP-meting krijgt geen credit. Expliciet geschatte/herstelde noodzakelijke zon-/netbronnen geven geen bruikbare startbegroting. Single total en bevestigde complete split werken beide. Gewone toestellen blijven echte `available_w` gebruiken.

Een draaiende HP met 2000 W op zon en 1000 W bruikbaar restoverschot kan dus 3000 W voor de drempel meetellen. Mogelijke extra SG-vraag blijft afzonderlijk conservatief geraamd met behouden `expected_power_w`; actuele P1, vaste importgrens, fasen, kwartiergrens, al toegezegde vraag en voorrang moeten die volledige extra raming toelaten. Geen HP-credit in elektrische headroom of EV-overname. Een eigen read-only SG-Wallboxguard beoordeelt de bestaande echte Wallboxlezing onder priority-policy, ook als gewone lasten andere EV-rechten hebben. Actieve/gevraagde Full solar-laadsessie houdt zijn stabiele extra-vermogensgrens. Definitieve dispatch leest bronnen en Wallbox opnieuw.

**SG-policy.** Defaults blijven 3000 W startdrempel, 3200 W aparte extra-raming, 120 s startvertraging, 60 s stopvertraging, 900 s rust en 3600 s sessielimiet; bestaande gebruikerswaarden blijven staan. Lease 300 s / renew 60 s blijft begrensd tot de sessie, zonder contactpulsen. Startvertraging gebruikt gezamenlijke zonnebijdrage; tekort/vernieuwen gebruikt echte netafname. Een nieuwe zonneperiode na general completion-hold wordt uitsluitend uit werkelijke restinjectie bewezen. Vijfminuten-/nieuwe native aanleiding, dhw_only afkoelregel, handmatige overname, toepassingsbereik en afzonderlijke koelbescherming blijven behouden. Constant HP-verbruik, reload of tijd geeft geen nieuwe sessie. Vrijgeven van SG stopt normale Panasonic-cycli niet gegarandeerd.

**Taak en bronbewijs.** Native taak, gekozen programma, SG-veiligheidscontext en afgeleide actuele taak blijven apart. De provider kan DeviceAction OFF teruggeven voor uitgeschakeld ruimtebedrijf, voordat hij de onafhankelijke tank beoordeelt. Alleen één verse getypeerde poll met main OFF, aanwezige tank ON en richting WATER ondersteunt bereik `space_circuit`; complete verse actieve hoofdmeting met passende verse tankroute kan dan Boiler opwarmen afleiden. De ruwe OFF blijft behouden. Globaal geverifieerd UIT, onbekend bereik, echte actieconflicten, ontdooien, oude/onvolledige meters en heater-only verlenen geen nieuwe thermische taak. Dit wijzigt geen SG-native/koelcontext. Overzicht blijft compact, bronbereik/profiel/uitleg in Details/export.

**Metingen en budgetweergave.** Per meter blijven laatste echte rapportagetijd, tijdsoort, eenheid, ruwe waarde, genormaliseerde ruwe watts, ouderdom en concrete afkeurreden bewaard. Ongeldig blijft onbekend voor regelen; geldige nul is nul. Een nieuwe regelronde maakt geen nieuw rapport. Het theoretische resterende kwartierbudget wordt apart getoond van actuele begrensde instantane ruimte. Concrete SG-blokkeerredenen benoemen net-, fase-, kwartier-, Wallbox- of bronlimiet. Veranderende bronkwaliteit blijft live/eigen export, uitgesloten van zware herhaalde Recorderkopieën.

**Leren.** Verse bevestigde native taak/rust kan stabiele gevalideerde overgangsmodellen opbouwen. Verse meter-/contextafleiding krijgt eigen begrensde voorbeelden/tellingen zonder bevestigde planningswaarde. Oud schema-1 samples/days blijven bewaard; ontbreken van bewijsherkomst geeft ze geen nieuwe bevestiging. Afgeleide tankroute wordt niet als gekozen ruimteverwarming geleerd. Unknown/conflict/ontdooien/actief zonder taak wordt geen normale basislast. Geen historische backfill, modelreset of realtime aftrek van geleerd warmtepompvermogen.

**Overige functies.** De opgeslagen prioriteiten, gewone lasten, minimumtijden, deadlines, overrides, bescherming en tickets blijven behouden. AEG houdt precies één native START per verse APP-belading, geen herhaalde START of stop/steckeronderbreking. Wallbox blijft autonoom; SG krijgt geen EV-krediet. PV-kalibratie behoudt vergelijkbare-dagenkwaliteit; geen vaste huishoudelijke correctie uit één export. Batterijwrites houden hun bestaande commandobescherming. Analyse nodig exporteert op één klik beschikbare zeven dagen; optioneel antwoordrapport is exact bron-/revisiegebonden read-only data, nooit code/settings/bediening. Vier geïmplementeerde logische voorstellen worden alleen door exacte generic digest + geïnstalleerde release herkend.

## 5. Configuratie, integraties en belangrijke entiteiten

Publieke documentatie bevat uitsluitend generieke rollen. Koppel echte lokale entiteiten via HA-selectors; namen/schermafbeeldingen bewijzen dekking niet. `sg_boost` bevat één bestaande switchuitgang, enabled/commissioning/watchdog, `profile` (dhw_only/general), `profile_confirmed`, afzonderlijke `cooling_protection_confirmed` en behouden policy-/leasewaarden. `comfort_hub` gebruikt de bestaande sg_boost/sg_sources/sg_advanced-paden; geen nieuwe controller.

Read-only rollen: tank_temperature_entity, tank_target_entity, activity_entity, zone_entities, bestaande power_entity/power_scope, power_supply1_entity/power_supply2_entity met split_power_confirmed, compressor_frequency_entity en sg_status_entity. Single-meterconfig blijft behouden. Split totaal vereist beide actuele plausibele nonnegatieve W/kW-waarden en volledige niet-overlap. Passieve displayvelden zijn power_activity_threshold_w, power_supply_profile en power_supply1/2_role. Default panasonic_standard vult alleen op twee verschillende gebonden sensor-entiteiten de onbevestigde rollen main/heater in; dit geeft geen dekkings- of SG-bevestiging. Expliciete afwijkingen blijven staan. Bij nieuwe meters volgt het standaardpaar hetzelfde model; afwijkende rollen worden niet als bewijs van de nieuwe meterbinding meegenomen. Het gewijzigde meterpaar houdt de bestaande dekkingsreview. Formulierlabels Functie voeding 1/2 — automatische weergave maken verfijning optioneel; de update gebruikt bestaande bindings en defaults zonder nieuwe invoer. Exacte automatische native taak-/contextuitlezing blijft display-only; een gekozen stand wordt geen afzonderlijk actie-/productiebewijs en geeft geen SG-vrijgave. Gelijke/reserved bronnen, bekende verklaarde dependencies en inspecteerbare template-overlap worden begrensd gecontroleerd; verborgen overlap blijft lokaal. Compressorbron vereist echte actuele Hz en plausibiliteit; ontvangen-SG-bron heeft expliciete actief/inactief-semantiek, geen gegokte numerieke stand.

Andere blokken houden hun betekenis: P1/PV/prijs-/forecast, fasen, gewone devices, AEG, Wallbox en batterijen. De centrale gebruikersvolgorde blijft behouden. Nieuwe profiel- of splitvelden krijgen geen permission uit oude boiler enabled-, AUTO- of importingestellingen. Lokaal gekozen Panasonic-percentages/koelwaarden worden niet door SolarPilot geschreven of als publieke installatie-default bewaard.

`private_bundle.json` blijft optioneel uitsluitend lokaal in de bewaarde userfilesmap; lege geldige bronnen kunnen worden aangevuld, nooit nieuwe actuator-/profielrechten. HA-configuratie/eigen opslag staan buiten vervangen HACS-programmabestanden. `panasonic_archive` en migratiemarker bewaren read-only herkomst; de aangepaste algemene completion-hold behoudt relevante oude herkomst voor rollback. Geen fysieke migratiewrite of oude opdracht replay. Een complete passende privéback-up blijft noodzakelijk.

## 6. Belangrijke ontwerpbeslissingen + waarom

| Besluit | Reden |
| --- | --- |
| Native Panasonic exclusief eigenaar | Vermindert tegenstrijdige doelen, AUTO-keuzes en herstelwrites; comfort blijft autonoom. |
| Eén SG-commandoroute en centrale deny-grens | Generieke adapters/planners mogen de verwijderde writer niet opnieuw introduceren. |
| Lokale kortlopende toestemming | Een netwerkonderbreking is iets anders dan power-on; aanvraag moet zonder HA kunnen vervallen. |
| Aanvraag, relais en reactie apart | HA-serviceacceptatie of app-tankdoel bewijst geen fysieke SG-respons. |
| Taak, elektrische activiteit en compressor apart | Verse native taak geeft taakcontext; actuele watts geven elektrische activiteit en animatie. Alleen echte Hz, of zonder gekoppelde compressorbron passende native hvac_action, geeft afzonderlijk bedrijfsbewijs. |
| Automatisch Panasonic-voedingsprofiel | Bruikbare uitleg zonder nieuwe invoer; herkenbare aanname, modelafwijkingen mogelijk, geen bedrading-/heater-/SG-bewijs. |
| Paneel en kaartversie apart | Een oude custom-elementklasse mag zich niet achter een nieuwe backendversie verbergen. |
| Bevestigd algemeen bereik naast tapwater-only | Verwijdert een onterechte permanente tankvoorwaarde zonder extra thermostaat of stilzwijgende toestemming. |
| Nieuwe aanleiding in plaats van periodieke herstart | Begrensde sessies blijven rustig, ook bij reload en constante zon zonder opnamebewijs. |
| Koelbeveiliging apart van profielkeuze | Gewenste extra koeling bewijst geen condensveiligheid; native beveiliging blijft extern bevestigd. |
| Complete bevestigde splitmeting | Voorkomt schijn-totaal, verborgen overlap en dubbele heater-/warmtepompwatts. |
| HP-zonnebijdrage uitsluitend voor starteligibiliteit | Vermijdt een tweede volledige injectiedrempel bij draaiende HP; bestaande P1/fasevraag blijft werkelijk aanwezig. |
| Extra SG-raming apart van huidige HP-watts | Huidig verbruik voorspelt geen gegarandeerde maximale SG-stijging. |
| Eigen read-only SG-Wallboxprioriteitsguard | Gewone EV-overnamerechten worden geen SG-overnamerecht. |
| Afgeleide voorbeelden apart van native bevestiging | Gekozen stand of tankroute wordt geen stil gevalideerd planningsmodel. |
| Bronafkeur met oorspronkelijk rapport | Oude/negatieve waarden blijven uitlegbaar zonder bruikbare watts te verzinnen. |
| Migratiearchief buiten uitvoerende runtime | Behoud rollback/evidentie zonder oud pending/ACK-writepad. |
| Bestaande lijst en overige guards behouden | Gerichte vereenvoudiging, geen algemene herschrijving of reset. |
| Eén canonieke uitleg | HA, Markdown en releasehulp geven dezelfde actuele betekenis. |

## 7. Automatische processen

De gewone regelcyclus leest actuele bronnen en eigen actuatorstatussen, verzoent toegestane open opdrachten, registreert bruikbare data en beslist onder globale/per-device voorwaarden. Alleen de SG-adapter kan een SG-aanvraag vernieuwen, en uitsluitend voor de huidige geldige sessie. Pauze, rebind/unload of oude epoch maakt eerdere callbacks ongeldig. Bij crash/open communicatie blijft de lokaal ingestelde toestemming begrensd.

Planner, PV-diagnose, basislastleren, dagkosten en historie blijven onder hun bestaande cadans en retentie. Recorder/presentatiecorrecties bewaren volledige live-/eigen data en vermijden zware herhaalde kopieën. De nieuwe veranderlijke warmtepompwaarnemingstijden worden uitsluitend uit de Recorder-attributenkopie uitgesloten; dit voorkomt vijfseconden-detailspam bij onveranderde rust. Live attributen, actuele sensorwaarden, eigen meetopslag en export blijven volledig beschikbaar. Geauthenticeerde export blijft on-demand lokaal. Meldingen volgen werkelijke veranderde controleoorzaken en worden bij afhandeling verwijderd; transportfout blokkeert de regelcyclus niet.

Startup-migratie archiveert eenmaal zonder fysieke actie. Alleen aantoonbaar uitsluitend vervallen actieve warmtepomp-opdrachtfouten verliezen hun blokkaderecht. Gerichte AEG-legacydetectie kan volgens haar bestaande begrensde same-device route een ontbrekend profiel herkennen, maar maakt geen belading. Een normale restart/isolation meldt automatische controle, geen verplichte generieke reset.

## 8. Geheimenbeleid

Publiek: generieke broncode, generieke vertalingen/help, fictieve testdata, actuele handleidingen, changelog en overdracht. Privé: userfiles, HA-back-ups, opslag/modelarchief, entitybindings, auth, netwerkgegevens, persoons-/locatiegegevens en ruwe analyse-export. Niets daarvan committen, in workflowlogs drukken of als release-asset opnemen. Een SG-installatieprompt met persoonlijke context blijft buiten repository en pakketten.

Geheimen komen uitsluitend uit bestaande HA-koppelingen/lokale configuratie; geen token in frontend of voorbeeld. Export blijft beheerdergeauthenticeerd, pseudonimiseert standaard namen en filtert gevoelige gegevens. Tijdstippen/gebruikspatronen blijven privé te beoordelen. Publieke preflight is noodzakelijk maar geen garantie dat ieder denkbaar privéveld automatisch wordt herkend.

## 9. Testprocedure + actuele teststatus

Voer volledige pytest uit zonder cache/bytecode, samen met privacy-/repositorypreflight, handoff, canonieke guide/help/mirrors, SG-bevoegdheidsgrens, Python-AST, Node-syntax en diffcontrole. Actuele aantallen/tijden staan uitsluitend in `docs/TESTRESULTATEN_BETA69.md`. De definitieve lokale beta.69-suite slaagde met 3829 cases in 60,40 s op Python 3.12, inclusief 179 nieuwe cases. Privacy/structuur, handoff, guide/hash/mirrors, SG-grens, AST van 72 productie-Pythonbestanden, Node-syntax en diff zijn geslaagd. Echte HA/browser/HACS/Hassfest blijven afzonderlijke CI-gates; zie het actuele testverslag.

Nieuwe regressies omvatten echte restinjectie versus HP-startcredit, batterij/import/PV-cap/reserves, single/split/no-overlap/freshness, opdracht/toezegging/vertraagde callback, EV-prioriteit zonder krediet, echte bronrapportage, raw OFF-bereik/tankroute, globaal UIT/conflict/ontdooien, onbekend/afgeleid/native leren, archiefbehoud en read-only importcatalogus. Export en frontend spiegelen dezelfde nieuwe bronnen en actualiteit. Fictieve fixtures bevatten geen huishoudelijke gegevens.

De CI-workflow toetst vijf onafhankelijke gates: repositorytests, HACS, Hassfest, echte Core 2026.10 setup/reload/unload en echte browser op 320/390/768/1280 px. Alleen de exacte bron met alle vijf geslaagde gates mag door de bestaande main-workflow worden gepubliceerd. Die workflow maakt immutable annotated nieuwe tag, bouwt beide ZIPs en vergelijkt alle vier assets vóór en na upload bytegelijk met de commit. Lopende/onuitgevoerde gates zijn geen succesclaim. Software/CI is geen fysieke gebruikersacceptatie.

## 10. Bekende problemen / beperkingen

Geen live HA-installatie, Shellyfirmware, fysieke Panasonicreactie, meterdekking of condensbeveiliging is in deze bronwerkrondes geïnspecteerd. Externe writers zijn zonder lokale inzage niet bewezen afwezig. Timerondersteuning, mapping, algemeen bereik, niet-overlap en geschikte bestaande beveiliging moeten lokaal blijken. Een oudere native instelling wordt niet via herstelwrite teruggezet.

De historische stilstand en later zichtbaar compressorbedrijf hebben geen vastgestelde oorzaak. Niet bekend is of alleen het SG-contact of ook Panasonic werd uit-/aangezet, noch of tussendoor modus/menu/native vraag veranderde. Verschillende meetmomenten zonder passende logs bewijzen geen contactflankprobleem, SolarPilot-fout of SG-veroorzaakte start. Geen automatische pulsen of rebootoplossing hiervoor.

Een partieel gemeten vermogen is geen totaal. Een ontvangen SG-stand of compressorfrequentie bewijst niet hoeveel extra verbruik SG veroorzaakt. Voeding 1 is geen zuivere compressormeting; het automatische voeding-2-heaterprofiel is een presentatie-aanname. De [Panasonic-installatiehandleiding 2023](https://www.panasonicproclub.com/uploads/GB/catalogues/2023/UK_INSTALLATION_MANUAL_H%202023v3.pdf), p. 7, beschrijft hoofdvoeding en ondersteuning; de [F-generatie servicehandleiding](https://www.panasonicproclub.com/uploads/CZ/catalogues/aquarea/service-manual/SXC9,12_F_E8_service%20manual_PAPAMY1311028CE.pdf), p. 43, toont varianten met andere verdeling. Meterwatts onderscheiden backupheater en tapwaterbooster niet. Het profiel verifieert geen fysieke aansluiting. SG-UIT stopt native bedrijf niet gegarandeerd en maakt gemeten watts niet onmiddellijk beschikbaar. Geen universele SG-formule, nulimportbelofte of garantie van compressor-only. Een lokale timer is geen elektrische beveiliging.

Nieuwe algemene beoordeling vereist rust en betekenisvol nieuw zon-/native bewijs; dezelfde samples/reload/tijd is onvoldoende. Zonder bruikbaar bewijs blijft beleidswacht staan, bewust hervatten na controle blijft mogelijk. Nieuwe lokale profielbevestiging wist echte handmatige/transport/veiligheidsblokkering niet. Bestaande historie/onderzoeksregistratie behoudt perioden/aantallimieten; geen onbeperkt archief/backfill.

## 11. Concrete openstaande ontwikkeling

Voltooi actuele beta.69-gates en bron-/assetcontrole volgens het nieuwe testverslag. Vier geïmplementeerde voorstellen hebben generieke digest/releasevermelding in `analysis_implementations.py`; privébronidentiteiten/rapportbewijs staan er niet in. Een gewijzigde voorsteltekst blijft niet uitgevoerd totdat expliciet geïmplementeerd en getest.

De echte optionele ontvangen-SG-bron is niet aangeleverd; ontvangen blijft zonder passende verse bron onbekend. Fysieke timer-/Panasonicreactie, meterdekking en condensbeveiliging zijn niet door software geaccepteerd. Historische stilstand/tankafkoeling heeft geen bewezen hardwareoorzaak. Geen pulstruc, heaterrelais, directe Panasonic-write of vaste PV-correctie invoeren. Eventgestuurde Wallbox-modusbron blijft een open bronsemantiekpunt; deze release verlengt geen stale-grens om onbekend Full solar te maken.

De eerder waargenomen `via_device`-deprecatiewaarschuwing met grens Home Assistant 2027.8 blijft te onderzoeken; deze versie verandert dat registratiepad niet.

## 12. Installatie/upgrade en rollback

Volledige privé HA-back-up vóór update, inclusief instellingen, eigen opslag, modellen, tickets en userfiles. Geef een eigen SG-aanvraag vrij vóór codevervanging; onderbreek geen beschermde cyclus. Update via HACS naar exact beta.69 na geslaagde publicatie, volledige HA-herstart en volledige browser/app-herlading. Backend-/kaartversie apart controleren. Lokaal uitsluitend `custom_components/solar_pilot` vervangen met behoud van userfiles en opslag; entry niet verwijderen/hermaken. Bestaande geldige beta.68-SG-/profiel-/split-/koelbevestigingen blijven staan; nieuwe wijzigingen houden hun bestaande voorwaarden. Geen nieuwe verplichte entiteiten of learningvragen.

Controleer berekende SG-zonnebijdrage, echte restinjectie en aparte elektrische blokkeerreden. Een veranderde berekening verleent geen onbekende hardware-/profielrechten. Alle behouden gebruikerswaarden en Panasonic-native SG-percentages blijven staan; SolarPilot schrijft ze niet.

Rollback: eigen SG-aanvraag vrijgeven, contact/lokale afloop controleren, nieuwe runtime stoppen en gecontroleerde beta.68-code met de volledige passende privéback-up van vóór deze update terugzetten. Alleen ZIP herstelt opgeslagen bewijsvelden niet exact. Geen twee runtimes tegelijk. Terugkeer naar oude directe beta.61 vereist nog steeds de volledige pre-beta.62-migratieback-up. Volledige stappen: `docs/BETA69_INSTELLEN.md`.

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
- `analysis_export.py`, `analysis_review.py`, `analysis_api.py`, `feedback_store.py`, `analysis_implementations.py`: begrensde lokale observaties/exportherkomst en read-only advies-/bevindingreview zonder control-/settingswrites.
- Leer-/PV-/planner-/historiecomponenten: nuttige analysefuncties, eigen data en on-demand privé-export.
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
7. Publiceer uitsluitend de geteste commit na repository-, HACS-, Hassfest-, real-ha-startup- én browser-UI-gate; controleer de nieuwe CI en immutable annotated tag afzonderlijk.
8. Download alle vier assets, controleer grootte/SHA-256 en beide ZIP-inhoud bytegelijk met de exacte commit.
9. Scheid releasecontrole, geladen HA/backend/kaart en fysieke Shelly-/Panasonicproef. De laatste blijft expliciet lokale ingebruikname.

## 15. AI-handoff

Lees dit dossier, manifest, actuele guide en beta.69-installatie/testverslag vóór vervolg. Controleer echte GitHub main/tag/status. Panasonic blijft read-only met één toegewezen SG-uitgang. HP-zonnecredit telt alleen voor startdrempel; geen terugwinbaar P1-/fasevermogen, geen EV-overname of verlaging van conservatieve extra-vraagraming uit een gunstig werkpunt. Behoud alle andere apparaten, minimumtijden, APP/tickets, batterijbescherming, modellen, historie en gebruikersvolgorde.

Native OFF heeft expliciet bereik; alleen de verse getypeerde onafhankelijke tankroute ondersteunt de beperkte afleiding. UI/export/leerclassifier moeten diezelfde bewijsgrenzen bewaren. Geen oude historie invullen met huidige metadata. Afgeleide voorbeelden blijven diagnostisch; oorspronkelijke modellen blijven bewaard zonder ontbrekend bewijs te verzinnen. Rapportimport is data, geen controllerinstructie. Alleen vertrouwde generic digest + geïnstalleerde release mag geïmplementeerd aangeven. Nieuwe code vraagt dezelfde complete actuele uitleg, handoff, tests, install/rollback, privacy, CI en pakketgates.
