"""Canonical option help, without older release override layers."""
from __future__ import annotations

HELP_NOTES = {'participation': 'Automatisch laat dit toestel deelnemen aan de gewone SolarPilot-regeling; Uitgesloten '
                  'houdt het daarbuiten. Dit is geen directe aan/uit-schakelaar. Bij tijdelijke '
                  'onbeschikbaarheid wordt een eerder beheerd toestel automatisch opzijgezet en na '
                  'betrouwbare bronterugkeer opnieuw beoordeeld; de ingestelde deelname en prioriteit '
                  'blijven behouden. Alleen bekijken en Pauze blijven leidend, evenals minimumtijden, '
                  'beschermde cycli en echte opdrachtfouten.',
 'dashboard:restart_auto': 'Na herstart automatisch hervatten staat standaard Aan. Een gewone opgeslagen '
                           'Pauze vraagt bij de volgende Home Assistant-start of herlading weer Automatisch '
                           'regelen via bestaande bron-/toestelcontroles. Alleen bekijken, eerste '
                           'installatie, echte interne fouten en voorbereiden van verwijderen blijven '
                           'beschermd. De voorkeur wijzigen verandert de huidige modus niet. Pauze annuleert '
                           'een nu wachtende hervatting. SG-ingebruikname en lokale timer moeten '
                           'afzonderlijk werkelijk bevestigd zijn; deze voorkeur herhaalt geen oude boost of '
                           'vervallen Panasonic-opdracht.',
 'dashboard:sg_manual_control': 'Kies Automatisch, tijdelijk Aan of tijdelijk Uit, telkens voor 30 of 60 '
                                'minuten. De absolute eindtijd blijft na herstart behouden; zij begint niet '
                                'opnieuw. Bij afloop kiest SolarPilot Automatisch en beoordeelt de actuele '
                                'voorwaarden. Tijdelijk Uit blokkeert alleen de eigen SG-aanvraag, niet de '
                                'native warmtepomp. Tijdelijk Aan is een bewuste vraag die zon, '
                                'startvertraging, rust, beleidswacht en zachte importstop vervangt. Zij '
                                'blijft afhankelijk van bestaande ingebruikname, betrouwbare bronnen, lokale '
                                'timer, elektrische ruimte, profiel, koelbeveiliging, globale modus en '
                                'voorrang. Een nog gemeld AAN wordt na herstart alleen behouden bij passend '
                                'eigen sessiebewijs en verse geldige voorwaarden. Onzekere opdrachten worden '
                                'niet blind herhaald. Bij tijdelijk handmatig Aan blijft de maximumduur voor '
                                'begrensde bediening leidend; de eindtijd begint niet opnieuw. Automatisch '
                                'algemeen SG-zonbedrijf kan aanblijven zolang actuele voorwaarden voldoen, '
                                'met behoud van oorspronkelijke starttijd en korte lokale lease. Alleen een '
                                'bevestigd beta.84-sessiecheckpoint kan een nog lopende korte lokale timer '
                                'bij echte HA-herstart voortzetten; oude journals houden de veilige '
                                'vrijgave. De gemelde contactstand blijft afzonderlijk van deze gekozen '
                                'bediening. Een extern ingeschakeld SG-contact wordt automatisch als '
                                'handmatig Aan herkend. Na vijftien minuten beoordeelt SolarPilot met '
                                'actuele metingen of het contact mag aanblijven. De oorspronkelijke eindtijd '
                                'blijft na herstart staan. Je hoeft hiervoor niet eerst Hervatten te kiezen. '
                                'Binnen de oorspronkelijke externe vijftienminutenperiode kan de begrensde '
                                'Wallbox-reactietijd een exact passend actueel AAN-contact behouden zonder '
                                'eigendom, ON-opdracht, leasevernieuwing of nieuw minimum. De '
                                'oorspronkelijke deadline en de daaropvolgende beoordeling op ruwe netafname '
                                'blijven ongewijzigd.',
 'others_first': 'Globale standaard voor gewone verbruikers: Andere eerst of Wallbox eerst. Bewust '
                 'opgeslagen centrale toestelkeuzes blijven leidend. Panasonic regelt noodzakelijk comfort '
                 'zelfstandig. De warmtepomp/SG heeft vaste toegang tot actueel coherent bevestigd autonoom '
                 'Wallbox-zonnelaadvermogen, ongeacht deze globale voorkeur; voor gewone toestellen blijven '
                 'hun eigen rechten gelden.',
 'dashboard:wallbox_priority': 'Wallbox voorrang geven kiest tijdelijk 30 min, 1 uur, 2 uur, 3 uur, 4 uur, 5 '
                               'uur of tot terug naar Automatisch voor de bestaande ondersteunde gewone '
                               'flexibele toestellen. Ieder gewoon toestel blijft apart wijzigbaar; de '
                               'oorspronkelijke eindtijden blijven na herstart behouden. Algemeen '
                               'Automatisch of afloop wist de individuele uitzonderingen volgens de '
                               'bestaande regels. De opgeslagen gewone volgorde blijft behouden. SG en de '
                               'beschermde afwasmachine zijn uitgesloten: de warmtepomp houdt vaste toegang '
                               'tot betrouwbaar bevestigd autonoom zonnelaadvermogen. De keuze bedient de '
                               'Wallbox niet en versoepelt geen minimumtijd, beschermde cyclus of actuele '
                               'grens.',
 'dashboard:wallbox_priority_device': 'Laat dit ondersteunde gewone flexibele toestel volgens de bestaande '
                                      'voorwaarden plaatsmaken voor autonoom autoladen. Kies een tijdelijke '
                                      'duur of tot terug naar Automatisch. De voorkeur herschrijft de '
                                      'opgeslagen rangorde niet, forceert geen laadstart en behoudt '
                                      'minimumtijden, beschermde cycli en actuele grenzen. SG/warmtepomp en '
                                      'de afwasmachine hebben deze keuze niet; SG houdt vaste zonnevoorrang '
                                      'op bevestigd autonoom zonneladen.',
 'manual_start': 'Vraagt na bevestiging handmatige bediening door SolarPilot. De toestelinformatie, '
                 'rusttijden en beveiligingen moeten bruikbaar zijn. Netstroom kan nodig zijn. De status en '
                 'reden blijven zichtbaar; deze knop is geen manier om fysieke bescherming te omzeilen. Een '
                 'fout of interlock blijft blokkeren; bestaande minimumlooptijden en beschermde cycli '
                 'blijven gelden.',
 'manual_stop': 'Beëindigt de handmatige SolarPilot-vraag met bevestiging. Het vrijgeven van een beschermde '
                'of nog minimaal lopende cyclus kan wachten; de knop is geen noodstop of '
                'hoofdvoedingsschakelaar.',
 'boost': 'Tijdelijke boost van 30 minuten met expliciete nettoestemming binnen de softwaregrenzen. '
          'Toestelvraag, minimumtijden en foutcontroles blijven gelden. Afloop betekent terug naar normale '
          'regeling, niet gegarandeerd onmiddellijk uitschakelen.',
 'name': 'De herkenbare naam van deze koppeling in SolarPilot. Dit hernoemt het fysieke apparaat of de '
         'oorspronkelijke Home Assistant-entiteiten niet.',
 'kind': 'Kies de werkelijk ondersteunde actuator. Het afzonderlijke AEG/Electrolux-afwasmachinetype stuurt '
         'uitsluitend een native START-knop, met een expliciete eenmalige klaarzettoestemming en echte '
         'startklaar-bronnen. Het gebruikt nooit de slimme stekker als start/stopregeling.',
 'priority': 'De rangorde staat op Voorrang → Voorrang instellen. Minimumtijden, passende vermogensruimte en '
             'bescherming blijven altijd gelden.',
 'device_id': 'Selecteer het bestaande SolarPilot-toestel dat je wilt aanpassen of verwijderen. Dit is niet '
              'een opdracht om het fysieke toestel aan of uit te zetten. Verwijderen vraagt nog bevestiging.',
 'battery_id': 'Selecteer het opgeslagen batterijprofiel. De oorspronkelijke batterij-integratie wordt '
               'hierdoor niet gewijzigd of verwijderd.',
 'grid_entity': 'Netvermogen van de volledige aansluiting in W of kW. Het moet netto import/injectie meten, '
                'niet alleen één verbruiker of een energieteller in kWh. De tekenrichting wordt apart '
                'ingesteld.',
 'grid_sign': 'Bepaalt of een positieve waarde van de netmeter import of injectie betekent. Controleer met '
              'een echt bekend verbruiksmoment. Een verkeerd teken kan juist toestellen inschakelen tijdens '
              'netafname.',
 'export_entity': 'Optionele afzonderlijke exportvermogenssensor. Gebruik alleen actueel injectievermogen in '
                  'W/kW en niet geëxporteerde kWh. Zonder deze bron gebruikt SolarPilot de gekozen netto '
                  'netmeter.',
 'pv_entity': 'Werkelijk totale zonnepanelenproductie in W/kW. Een voorspelling of dagopbrengst in kWh is '
              'geen actuele vermogensbron. Actuele P1/PV en fysieke grenzen blijven leidend voor nieuwe '
              'starts en SG-zonneboost.',
 'battery_power_entity': 'Werkelijk batterijvermogen. Hiermee voorkomt SolarPilot dat batterijontlading als '
                         'nieuwe zonne-energie wordt gezien. De tekenrichting moet kloppen. Zonder '
                         'thuisbatterij mag dit leeg blijven.',
 'battery_sign': 'Tekenafspraak van de batterijvermogensmeter: laden en ontladen moeten juist onderscheiden '
                 'worden. Dit verandert alleen de interpretatie; er wordt geen opdracht naar de batterij '
                 'gestuurd.',
 'battery_soc_entity': 'Actuele laadtoestand van een echte thuisbatterij, in procent. Geen fietsbatterij of '
                       'autobatterij kiezen voor de algemene thuisbatterijreserve.',
 'reserve_w': 'Vaste huisbuffer die SolarPilot niet opnieuw toewijst. Bij 600 W actuele injectie en 150 W '
              'buffer blijft ongeveer 450 W over voor een nieuwe last. Hoger is voorzichtiger; lager benut '
              'meer zon maar geeft eerder korte netafname. Dit is geen reservering voor een toestel of '
              'toekomstige afwaspiek. Nieuwe aanvragen gebruiken de actuele P1-balans na batterijcorrectie '
              'en filtering. Bestaande fasecontroles, minimumtijden en start-/stopbuffers blijven gelden; '
              'geen nulimportgarantie.',
 'max_import_w': 'Softwarematige bovengrens voor de totale netafname, geen zekeringbeveiliging en geen '
                 'afzonderlijke fasebeveiliging. Vanaf beta.110 mag alleen SG met een bevestigde autonome '
                 'zonneladende Wallbox deze grens tijdens een begrensde overdracht tijdelijk overschrijden. '
                 'De uitzondering blijft beperkt door actuele coherente laadmetingen, de SG-raming, '
                 'max_takeover_w en de oorspronkelijke handover_s-eindtijd. Daarbuiten geeft overschrijding '
                 'een eigen SG-aanvraag direct vrij. Fase-, kwartier-, batterij- en broncontroles blijven '
                 'afzonderlijk gelden; onbeheerde apparaten kunnen de softwaregrens toch overschrijden.',
 'battery_min_soc': 'Onder deze batterijlaadtoestand mag ontladen vermogen niet als beschikbare energie voor '
                    'gewone nieuwe zonnelasten worden behandeld. Dit is geen vervanging voor de echte '
                    'batterij-BMS-reserve.',
 'interval_s': 'Tijd tussen realtime regelberekeningen. Standaard 5 seconden. Korter vraagt meer rekenwerk '
               'en geeft niet vanzelf snellere cloudgegevens; langer reageert trager. Dit is geen verplicht '
               'schakelinterval en de interface mag hierdoor niet dichtklappen.',
 'settle_s': 'Wachttijd na een fysieke wijziging voordat een volgende verhoging mag worden uitgevoerd. Geeft '
             'meters en apparaten tijd om te reageren. Korter kan regelingen laten botsen; langer is '
             'rustiger.',
 'stale_s': 'Maximale ouderdom van een ontvangen bronrapport. Te oude gegevens worden niet als actuele '
            'waarheid gebruikt. Dit gaat om het laatste rapport, niet om de laatste keer dat de waarde '
            'veranderde. Verleng niet om een kapotte bron te verbergen.',
 'filter_s': 'Verzachting van korte variaties in het netvermogen. Een langer venster filtert meer ruis maar '
             'reageert trager op echte veranderingen. Veiligheidscontroles en toestelvoorwaarden blijven '
             'afzonderlijk bestaan.',
 'fault_grace_s': 'Korte buffer bij onbetrouwbare of ontbrekende informatie vóór de bijbehorende '
                  'foutreactie. Voorkomt reageren op één gemist rapport. Maak deze niet groot om structurele '
                  'meetproblemen te negeren.',
 'control_entity': 'De echte aan/uit-actuator. SolarPilot gebruikt die om het toestel te schakelen en leest '
                   'de toestand terug. Kies geen virtuele helper tenzij die bewust en betrouwbaar de echte '
                   'bediening vertegenwoordigt.',
 'number_entity': 'Numerieke actuator waarmee een ondersteund toestel werkelijk wordt aangestuurd. Eenheid, '
                  'teken, minimum, maximum en stap moeten overeenkomen met de apparaatinterface. Dit veld '
                  'geeft schrijfrecht aan de regeling.',
 'start_script': 'Bestaand Home Assistant-script om dit toestel te starten. De geladen inhoud moet vaste '
                 'onafhankelijke doelapparaten tonen en mag Panasonic of het gereserveerde SG-contact niet '
                 'bedienen. Niet controleerbare of dynamische doelen worden geblokkeerd. Deze controle '
                 'bewijst geen fysieke veiligheid; gebruik echte terugmelding en test onder toezicht.',
 'stop_script': 'Bestaand script voor het veilig stoppen van dit toestel. De geladen vaste doelapparaten '
                'worden op afzonderlijk eigenaarschap gecontroleerd; onbekende of dynamische bediening wordt '
                'geblokkeerd. Een beschermd programma mag niet abrupt worden afgebroken. De naam van het '
                'script bewijst geen fysieke veilige stop.',
 'active_entity': 'Werkelijke aan/actief-terugmelding voor een scriptgestuurd toestel. Een succesvol '
                  'verstuurde opdracht is nog geen bevestigde fysieke start. Gebruik een bron die '
                  'onbeschikbaarheid ook doorgeeft.',
 'power_entity': 'Werkelijk actueel vermogen van dit ene apparaat, in W of kW. Dit is geen energieteller in '
                 'kWh. Een exclusieve meter maakt de vermogensschatting en historie betrouwbaarder; een '
                 'gedeelde meter kan verkeerd gedrag veroorzaken.',
 'condition_entity': 'Optionele vraag/startklaar-bron. Het toestel mag alleen meedoen als deze toestemming '
                     'geeft, bijvoorbeeld een gekozen taak of gemeten vochtvraag. Zonder bron blijven de '
                     'overige voorwaarden leidend.',
 'interlock_entity': 'Extra vrijgave voor veilige bediening. Een afwezige of niet-vrijgegeven blokkering mag '
                     'nooit als toestemming worden opgevat. Test de betekenis van on/off voordat je deze als '
                     'vergrendeling gebruikt.',
 'nominal_w': 'Realistische raming voor een nieuwe start en de toestelplanning. Gebruik ongeveer het '
              'werkelijk benodigde vermogen, niet bewust te laag. Een lopend toestel reserveert zijn '
              'ongebruikte nominale vermogen of toekomstige piek niet opnieuw: de actuele netmeting bevat '
              'het huidige huisverbruik al. Ontbrekend toestelvermogen blijft onbekend en wordt geen gemeten '
              'nul. Een exclusieve meter kan na voldoende leren de schatting begrensd verhogen; het '
              'ingestelde veld wordt niet vanzelf herschreven. Beschermde cycli worden niet gestopt voor een '
              'nieuwe aanvraag.',
 'min_units': 'Kleinste bruikbare actieve instelling van de numerieke actuator. Dit kan bijvoorbeeld ampère '
              'zijn; het is niet automatisch watt. SolarPilot begint niet op een kleiner onbruikbaar doel.',
 'max_units': 'Hoogste toegestane actuatorinstelling binnen het fysieke apparaatbereik. De instelling is een '
              'softwaregrens, geen vervanging van apparaat- of installatiebeveiliging.',
 'step_units': 'Grootte van elke regelstap op de numerieke actuator. Kleine stappen zijn fijner maar vragen '
               'meer ingrepen; grote stappen reageren grover. Gebruik alleen stappen die het apparaat '
               'ondersteunt.',
 'watts_per_unit': 'Omrekening van één actuator-eenheid naar geschat elektrisch vermogen. Bijvoorbeeld '
                   'ampère naar watt met de juiste spanning en faseconfiguratie. Een foutieve omrekening '
                   'maakt de planning onbetrouwbaar.',
 'start_delay_s': 'Zolang moeten de startvoorwaarden stabiel geldig blijven vóór een nieuwe start. Hoger '
                  'voorkomt starts op korte zonnige pieken. De teller herbegint wanneer de vereiste ruimte '
                  'wegvalt.',
 'stop_delay_s': 'Zolang mag een gewoon energietekort aanhouden voordat een eigen onderbreekbare last wordt '
                 'teruggenomen. Hoger voorkomt stoppen voor een korte wolk, maar kan langer netafname geven. '
                 'Minimumlooptijd en aparte prioriteits-/veiligheidsregels blijven gelden.',
 'min_on_s': 'Minimale looptijd na een bevestigde start. Belangrijk voor bijvoorbeeld compressoren. Deze '
             'tijd wordt niet verkort om Wallbox-voorrang of een goedkope elektriciteitsprijs te halen.',
 'min_off_s': 'Minimale rusttijd na uitschakelen voordat SolarPilot opnieuw mag starten. Kies op basis van '
              'het toestel. Een langere rusttijd vermindert korte aan/uit-cycli, maar laat sommige '
              'zonnepieken voorbijgaan. Bij een herstart blijft de bewaarde bevestigde UIT-tijd leidend en '
              'telt alleen het restant, na controle van de actuele toestelstatus. Zonder betrouwbaar eerder '
              'bewijs kan nog een volledige rusttijd nodig zijn.',
 'start_margin_w': 'Extra vermogen boven het verwachte toestelvermogen voor een nieuwe start. Voorbeeld: 350 '
                   'W toestel plus 100 W marge vraagt ongeveer 450 W bruikbare ruimte, na de algemene '
                   'reserve.',
 'ack_timeout_s': 'Maximale wachttijd op een echte terugmelding na een opdracht. Dit is geen '
                  'compressor-rusttijd en geen verplichte vertraging wanneer de bevestiging eerder komt. Bij '
                  'geen bevestiging volgt een fout-/onzekerheidscontrole, geen eindeloos opnieuw schakelen.',
 'manual_hold_s': 'Rustperiode na herkende externe bediening of taakvoltooiing. SolarPilot probeert een '
                  'handmatige wijziging niet meteen ongedaan te maken. Dit is iets anders dan de '
                  'bevestigingstijd van een eigen opdracht.',
 'max_on_s': 'Maximale aaneengesloten looptijd die je voor deze last toestaat. 0 betekent geen opgelegde '
             'limiet. Een te korte limiet kan onnodige onderbrekingen veroorzaken; een bestaande '
             'veiligheidslimiet mag niet zomaar vervallen.',
 'non_interruptible': 'Een eenmaal bevestigde cyclus moet veilig kunnen afwerken, zoals een '
                      'vaatwasprogramma. AAN verhindert gewone energiebeslissingen die de cyclus abrupt '
                      'onderbreken. Gebruik dit niet als truc om voldoende startruimte te omzeilen.',
 'min_daily_runtime_min': 'Gewenste minimale totale draaitijd per dag, in minuten. 0 betekent geen verplicht '
                          'dagminimum. Dit is niet dezelfde instelling als minimumlooptijd per start.',
 'max_daily_runtime_min': 'Hoogste totale draaitijd per dag, in minuten. 0 betekent geen daglimiet. Een '
                          'ingestelde limiet kan nieuwe starts blokkeren, ook wanneer er nog zon is.',
 'daily_deadline': 'Tijdstip waarop het ingestelde dagminimum bij voorkeur bereikt moet zijn. Een deadline '
                   'maakt geen netstroom vrij tenzij je die toestemming afzonderlijk geeft. 0-dagdoelen '
                   'vragen geen verplichte taak.',
 'deadline_grid_allowed': 'Toestemming om zo nodig netstroom te gebruiken voor het dagminimum. UIT laat een '
                          'tekort aan zon mogelijk eindigen met een niet gehaald dagdoel. Net-, fase- en '
                          'toestelgrenzen blijven bestaan.',
 'daily_energy_goal_kwh': 'Gewenste dagenergie voor deze last. 0 zet dit doel uit, niet de gewone '
                          'zonnestroomregeling. De planner trekt reeds geregistreerde energie af en plant '
                          'het resterende deel.',
 'time_window_enabled': 'AAN beperkt de startvraag tot jouw eigen tijdvenster. UIT gebruikt geen extra '
                        'klokvenster. Een venster vervangt geen minimumlooptijd, terugmelding of bescherming '
                        'van een lopende cyclus.',
 'time_window_start': 'Begin van het toegestane dagvenster in de Home Assistant-tijdzone. Dit is toestemming '
                      'om te starten, geen gedwongen start op dat uur.',
 'time_window_end': 'Einde van het dagvenster in de Home Assistant-tijdzone. Houd rekening met de duur van '
                    'beschermde cycli en minimumlooptijden; dit is geen abrupte noodstop.',
 'forecast_deferrable': 'Een nieuwe start mag begrensd wachten op een gunstiger zonneblok. Een reeds lopende '
                        'last wordt niet door een nieuwe voorspelling gestopt. Zonder dagdoel wordt de '
                        'gewone overschotregeling niet permanent geblokkeerd.',
 'cheap_grid_allowed': 'Per-toesteltoestemming voor goedkope netfallback. Vereist ook de globale '
                       'planner-toestemming; alleen dit vinkje is niet voldoende. Geen garantie op goedkoop '
                       'laden bij ontbrekende prijsgegevens.',
 'phase_hint': 'Fase waarop het apparaat fysiek aangesloten is, of Auto voor voorzichtig lokaal leren. De 32 '
               'A-hoofdaansluiting blijft een grens per fase; netto optelling over fasen maakt één fase niet '
               'onbeperkt belastbaar.',
 'wallbox_precedence': 'Bekijk en wijzig de gezamenlijke rangorde op Voorrang. De plaats boven of onder Auto '
                       'laden bepaalt de relatieve volgorde.',
 'wallbox_energy_choice': 'Kies één duidelijke uitkomst: de auto mag binnen de veiligheidsgrenzen minder '
                          'laden, alleen vrij zonneoverschot telt, of de strengere route voor een kort en '
                          'gemeten toestel geldt.',
 'cycle_learning_enabled': 'Leert energie, duur en piek uit complete bevestigde apparaatcycli met een eigen '
                           'meter. Afgebroken of onvoldoende gemeten cycli vormen geen betrouwbaar '
                           'programma. Leren geeft geen extra bedieningsrecht.',
 'cycle_energy_kwh': 'Conservatieve energie-inschatting van één volledig programma zolang geen bruikbaar '
                     'geleerd cyclusprofiel bestaat. Dit is geen piekvermogen. Gebruik echte '
                     'programma-informatie of metingen.',
 'cycle_duration_min': 'Conservatieve duur van een volledige cyclus, in minuten. Nodig om een beschermd '
                       'programma als aaneengesloten blok te plannen. Zonder duur wordt geen optimistische '
                       'duur uit alleen het piekvermogen gegokt.',
 'cycle_program': 'Naam van het programma voor cyclusregistratie, bijvoorbeeld Eco. Verschillende '
                  'programma’s kunnen een verschillend verbruik en een andere duur hebben.',
 'cycle_program_entity': 'Optionele entiteit die het werkelijk gekozen programma rapporteert. Alleen '
                         'uitlezen. Hiermee worden geleerde cycli bij het juiste programma bewaard.',
 'wallbox:enabled': 'Zet de alleen-lezen Wallbox-monitor aan. Deze leest laadvermogen, vraag en modus uit '
                    'bestaande HA-entiteiten; SolarPilot verstuurt hier geen laadstroom-, start-, stop- of '
                    'fasecommando’s naar de Wallbox. Ontbrekende of oude Wallbox-gegevens blokkeren geen '
                    'andere toestellen wanneer hun actuele netmeting en gewone voorwaarden geldig zijn.',
 'wallbox:power_entity': 'Werkelijk Wallbox-laadvermogen in W of kW voor laadweergave en bewezen '
                         'vermogensovername. Een ontbrekende of oude waarde blijft onbekend. Gewone '
                         'toestellen en SG-zonneboost gebruiken dan uitsluitend werkelijk gemeten vrij '
                         'netoverschot. De auto wordt niet als 0 W verondersteld en er ontstaat geen '
                         'EV-vermogenskrediet. Actuele net-, batterij-, fase- en vermogensgrenzen blijven '
                         'gelden.',
 'status_entity': 'Tekststatus van de laadpaal. Exacte herkenningswoorden staan bij Geavanceerd. Een '
                  'aangesloten auto kan gepauzeerd, vol of niet startklaar zijn; een kabel alleen is geen '
                  'laadvraag.',
 'demand_entity': 'Optionele expliciete laadvraagbron. Gebruik een echte vraag/startklaar-terugmelding, niet '
                  'alleen kabel aangesloten. Laat leeg wanneer de betrouwbare tekststatus deze informatie '
                  'levert.',
 'mode_entity': 'Oorspronkelijke instelling van de zonnelaadmodus. Die kan Full Solar blijven tonen tijdens '
                'een manuele override. Koppel daarom ook de effectieve laadsessie. Deze bron wordt alleen '
                'uitgelezen; geen laadmoduswijzigingen vanuit SolarPilot.',
 'connected_entity': 'Optionele expliciete terugmelding dat er een auto op deze laadpaal aangesloten is. '
                     'Aanwezigheid geeft niet automatisch laadvraag; een volle of gepauzeerde auto hoeft '
                     'geen vermogen te reserveren.',
 'charging_threshold_w': 'Vanaf dit gemeten vermogen telt de Wallbox als daadwerkelijk ladend. Standaard 50 '
                         'W scheidt kleine standbywaarden van laden. Dit is niet het Full Solar-startminimum '
                         'van ongeveer 1380 W bij één fase.',
 'priority_min_power_w': 'Werkelijk benodigd minimum om autonoom Full Solar te beginnen. Bij bevestigd '
                         'éénfasig laden is 1380 W een uitgangspunt. Alleen gebruikt voor voorrang; geen '
                         'laadstroomopdracht. Automatisch profiel-afleiden kan deze handwaarde vervangen.',
 'priority_start_margin_w': 'Extra ruimte boven het Full Solar-minimum voordat lagere verbruikers voor de '
                            'auto wijken. Bij 1380 W en 150 W marge is het voorrangsdoel circa 1530 W. Hoger '
                            'voorkomt starten op de grens, maar wacht langer.',
 'profile_auto': 'Leest de maximale laadstroom van dezelfde Wallbox via het HA-entiteitsregister. Geen extra '
                 'cloudverzoeken. Ontbrekende, verouderde of onduidelijke bronnen gebruiken een zichtbaar '
                 'gemarkeerde handmatige terugval. Er wordt niets naar de Wallbox geschreven.',
 'max_current_entity': 'Optionele expliciete bron voor maximale laadstroom in ampère. Bij voorkeur de '
                       'number-instelling of sensorspiegel Max charging current. ICP is de hoofdaansluiting '
                       'en is hiervoor fout. Leeg laat veilige herkenning op hetzelfde Wallbox-apparaat toe.',
 'phases_entity': 'Alleen een bron die expliciet 1 of 3 laadfasen rapporteert. SolarPilot raadt het aantal '
                  'fasen niet uit watt, ampère of een driefasige huisaansluiting. Zonder geldige bron geldt '
                  'jouw bevestigde faseprofiel.',
 'charging_phases': 'Werkelijk gebruikte laadfasen: 1 of 3. Nu éénfase; verander pas na bevestiging van de '
                    'echte laadconfiguratie. Deze keuze stuurt geen fysieke faseschakelaar.',
 'max_current_a': 'Handmatig bevestigde terugval voor de maximale laadstroom wanneer live uitlezen niet '
                  'bruikbaar is. Uitgangspunt 25 A voor het huidige profiel. Het dashboard vermeldt dan dat '
                  'dit niet live bevestigd is. Geen elektrische beveiliging.',
 'voltage_v': 'Spanning per fase voor de vermogensschatting, standaard 230 V. 1 × 230 × 25 geeft 5750 W; 3 × '
              '230 × 25 geeft 17250 W. Dit is een schatting, geen gemeten laadvermogen of '
              'installatiegoedkeuring.',
 'minimum_current_a': 'Minimale laadstroom per gebruikte fase voor de berekende Full Solar-grens. Standaard '
                      '6 A; met 230 V is dat 1380 W bij 1 fase of 4140 W bij 3 fasen. Gebruik de werkelijke '
                      'laadconfiguratie.',
 'minimum_from_profile': 'AAN berekent het zonnelaadminimum uit fasen × rekenspanning × minimumstroom. UIT '
                         'behoudt het afzonderlijk ingestelde minimumvermogen. Je kunt later naar 3 fasen '
                         'zonder herschrijven van de regeling; pas het profiel bewust aan.',
 'demand_states': 'Puntkomma-gescheiden exacte laadstatussen die vraag betekenen. Gebruik geen komma als '
                  'scheiding: sommige Wallbox-statusnamen bevatten zelf een komma. Onbekende teksten gelden '
                  'niet zomaar als toestemming.',
 'idle_states': 'Puntkomma-gescheiden statusnamen zonder actuele laadvraag, bijvoorbeeld Ready of Paused. '
                'Verwar wachten op groene energie niet met klaar/geen vraag; dat zou de voorrang verkeerd om '
                'maken.',
 'full_solar_states': 'Puntkomma-gescheiden herkenningswaarden voor uitsluitend zonneladen, bijvoorbeeld '
                      'full_solar. Dit leest de modus, het verandert de modus niet. Een onbekende modus '
                      'geeft geen onbeperkt overneembaar vermogen.',
 'stable_s': 'Hoe lang werkelijk restoverschot stabiel moet zijn voordat extra lasten naast de autonome '
             'laadpaal mogen starten. Langer is rustiger; korter kan reageren vóór vertraagde laadrapporten '
             'binnenkomen.',
 'cooldown_s': 'Rust na vermoede wisselwerking tussen laadpaal en eigen lasten. Vermindert herhaald vermogen '
               'afpakken en teruggeven. De autonome Wallbox-regeling blijft ondertussen eigenaar van het '
               'laden.',
 'drop_tolerance_w': 'Kleinste relevante verandering in laadvermogen voor de wisselwerkingsbewaking. Kleine '
                     'meetruis wordt niet als een echte reactie behandeld. Te groot kan een werkelijke '
                     'daling missen.',
 'handover_s': 'Uiterste termijn om een gecontroleerde vermogensovername van de Wallbox te bevestigen. Voor '
               'SG met een bevestigde autonome zonneladende Wallbox begrenst dit vanaf beta.110 ook de '
               'tijdelijke uitzondering op de softwarematige totale netgrens: standaard 240 seconden, in de '
               'SG-route hoogstens 600 seconden. De oorspronkelijke episode begint bij het eerste actuele '
               'P1-rapport boven de grens tijdens een bevestigde SG-aanvraag of een exact actueel '
               'waargenomen extern AAN-contact binnen zijn oorspronkelijke vijftien minuten. Laadrapporten, '
               'leasevernieuwing en herstart verlengen haar niet. De gewone wolkenbuffer loopt parallel op '
               'ruwe P1. Fase-, kwartier- en batterijgrenzen blijven direct gelden. Deze softwaretijd is '
               'geen nieuwe lokale Shelly-timer; de bestaande korte eigen SG-lease blijft apart, standaard '
               '300 seconden. Bij HA-uitval is fysieke UIT exact na 240 seconden niet gegarandeerd.',
 'handover_confirm_s': 'Vereiste duur van bevestigde stabiele netmetingen tijdens een gewone overdracht. '
                       'Voor een nieuwe SG-/Wallbox-reactie-episode moet de ruwe P1-netafname minstens deze '
                       'tijd, standaard vijftien seconden, op of onder de SG-importdrempel liggen, met '
                       'minstens twee verschillende nieuwe bronrapporten. Alleen even onder de '
                       'softwarematige totale netgrens komen herstart de reactietijd niet. Een '
                       'serviceaanroep of schermklok is geen meetbewijs.',
 'handover_import_w': 'Kleine tolerantie op netafname bij de bevestiging van een overdracht. Geen doel om '
                      'stroom van het net af te nemen. Een grotere waarde kan een mislukte overdracht '
                      'verhullen.',
 'reclaim_max_age_s': 'Maximale leeftijd van het Wallbox-rapport voordat een nieuwe gecontroleerde overname '
                      'mag beginnen. Oude laadgegevens mogen niet als actueel vrijmaakbaar vermogen worden '
                      'gebruikt.',
 'max_takeover_w': 'Maximale vermogenstap bij het overnemen van laadvermogen. Voor de begrensde '
                   'SG-/Wallbox-reactietijd is de extra ruimte boven de softwarematige netgrens nooit groter '
                   'dan het minimum van deze waarde, de geraamde SG-opname en het actuele coherente autonome '
                   'zonnelaadvermogen. De eerste toegelaten bijdrage blijft het plafond voor die episode. De '
                   'Wallbox krijgt geen opdracht; afzonderlijke fase-, kwartier-, batterij- en broncontroles '
                   'blijven gelden.',
 'priority_stable_s': 'Hoe lang genoeg vermogen vrijgemaakt kan worden voor het EV-minimum voordat lagere '
                      'eigen lasten wijken. Standaard 120 s. Een lopende compressor krijgt eerst zijn '
                      'minimumlooptijd.',
 'priority_release_s': 'Wachttijd voordat lagere lasten opnieuw stabiel restoverschot mogen gebruiken. Houdt '
                       'de regelingen uit elkaars vaarwater; is niet dezelfde tijd als de eigen '
                       'compressor-rusttijd.',
 'priority_hysteresis_w': 'Vermogensband tussen voorrang vasthouden en vrijgeven. Vermindert heen-en-weer '
                          'schakelen rond de laadgrens. Te groot reserveert onnodig lang vermogen.',
 'priority_start_timeout_s': 'Maximale kans voor de Wallbox om na daadwerkelijk vrijgeven te starten. '
                             'Standaard 600 s. Wanneer de auto toch niet laadt, mogen lagere lasten later '
                             'opnieuw meedoen met hun normale rusttijden.',
 'priority_retry_s': 'Rust vóór een nieuwe voorrangspoging na een niet-bevestigde EV-start. Standaard 1800 '
                     's. Voorkomt dat de ontvochtiger telkens stopt voor een auto die geen lading '
                     'accepteert.',
 'average_demand_entity': 'Bron voor het lopende kwartiergemiddelde van de volledige aansluiting. Niet het '
                          'actuele vermogen en niet een kWh-teller. Hiermee wordt het resterende '
                          'kwartierbudget geschat.',
 'monthly_peak_entity': 'Gemeten maandpiek als referentie voor piekplanning. Geen veilige elektrische '
                        'bovengrens. Een reeds hogere piek kan optioneel het doel aanpassen.',
 'target_peak_w': 'Gewenst kwartierpiekdoel inW. Lagere waarden beperken nieuwe pieken maar kunnen flexibel '
                  'werk uitstellen. De regeling kan onbeheerde lasten niet wegregelen en dit is geen '
                  'zekeringbeveiliging.',
 'adaptive_to_month_peak': 'AAN laat een reeds hogere gemeten maandpiek meewegen in het piekdoel. UIT houdt '
                           'het vaste doel aan. Dit verandert niet de fysieke netgrenzen.',
 'margin_w': 'Extra conservatieve ruimte onder het bijbehorende piek- of faseplafond. Hoger geeft minder '
             'ruimte voor nieuwe lasten; lager reageert dichter bij de grens.',
 'minimum_elapsed_s': 'Minimale verstreken tijd in het kwartier voordat een extrapolatie bruikbaar wordt. Te '
                      'vroeg is de berekening gevoelig voor een kort inschakelmoment.',
 'respect_billing_floor': 'Laat de ingestelde facturatievloer meewegen als ondergrens voor zinvolle '
                          'kostenoptimalisatie. Dit is geen elektrische aansluitwaarde.',
 'billing_floor_w': 'Instelbare ondergrens voor de tariefberekening. Gebruik de toepasselijke '
                    'contractsituatie. Dit getal begrenst niet het totale toegestane fysieke vermogen.',
 'import_price_entity': 'Actueel afnametarief in geld per kWh. Gebruik een eigen betrouwbare '
                        'energieprijsbron, niet een kostentotaal. Bij dynamische prijzen wordt waar '
                        'beschikbaar de passende prijsreeks gebruikt. Onbeschikbare, restored, toekomstige '
                        'of meer dan 36 uur oude prijsbronnen vallen terug op het vaste tarief; ontbrekende '
                        'rijen verschuiven het tijdrooster niet.',
 'export_price_entity': 'Actuele vergoeding voor injectie per kWh. Geen hoeveelheid geëxporteerde energie. '
                        'Een negatieve waarde betekent dat terugleveren geld kan kosten.',
 'fixed_import_eur_kwh': 'Terugvalprijs per kWh netafname als geen geldige prijsbron bestaat. Gebruik de '
                         'gewenste variabele prijscomponenten consequent. Vaste kosten en capaciteitstarief '
                         'worden niet hierdoor automatisch toegevoegd.',
 'fixed_export_eur_kwh': 'Terugvalvergoeding per kWh injectie. Deze wordt van de geschatte netafnamekost '
                         'afgetrokken. Direct zonneverbruik wordt niet nóg een tweede keer van die netto '
                         'kost afgetrokken.',
 'current_hour_entity': 'Forecast-energie voor dit uur in kWh. Dit is een verwachting, geen actuele '
                        'vermogensmeting. De realtime netmeter blijft leidend voor echte starts.',
 'next_hour_entity': 'Verwachte zonne-energie voor het volgende uur in kWh. Alleen een planningsbron; '
                     'bewijst niet dat er straks werkelijk voldoende overschot is.',
 'remaining_today_entity': 'Nog verwachte zonne-energie voor vandaag, in kWh. Geen reeds geproduceerde '
                           'dagenergie kiezen. Wordt ook gebruikt voor de geschatte laatste bruikbare '
                           'zonneperiode.',
 'forecast_power_entity': 'Voorspeld zonnevermogen op dit moment inW/kW, om met werkelijk PV te vergelijken. '
                          'Niet de energie voor een heel uur. Structurele afwijkingen worden gekoppeld aan '
                          'de zonnestand.',
 'sun_entity': 'Zonnestandbron met azimut en elevatie. Daarmee worden schaduwpatronen geleerd op positie in '
               'plaats van uitsluitend kloktijd.',
 'seed_enabled': 'AAN gebruikt een lokaal aangeleverde historische bootstrap als voorzichtig beginprofiel. '
                 'Geen privédata wordt naar GitHub verzonden. Zonder bestand leert SolarPilot live; een '
                 'bootstrap is geen zekerheid.',
 'min_forecast_w': 'Onder dit voorspelde vermogen wordt geen verhouding voor het lokale PV-model geleerd. '
                   'Kleine waarden veroorzaken te veel ruis, vooral rond zonsopkomst en zonsondergang.',
 'min_elevation_deg': 'Onder deze zonnehoogte leert het schaduwmodel niet. Zo domineren schemering en zeer '
                      'kleine vermogens niet de correctie.',
 'azimuth_bin_deg': 'Breedte van een vak in horizontale zonnestand. Kleine vakken zijn preciezer maar '
                    'verzamelen trager voldoende verschillende dagen; grotere vakken zijn grover en leren '
                    'sneller.',
 'elevation_bin_deg': 'Breedte van een vak in zonnehoogte. Gebruik niet overdreven kleine vakken zonder '
                      'voldoende seizoensdata; grotere vakken middelen meer situaties samen.',
 'min_days': 'Vereist aantal verschillende meetdagen voor het betreffende leerprofiel. Hoger is minder '
             'gevoelig voor één uitzonderlijke dag maar leert trager. Meer monsters van dezelfde dag '
             'vervangen die dagspreiding niet.',
 'min_confidence': 'Onder deze interne leerscore mag de lokale correctie niet als betrouwbare plannerinput '
                   'worden gebruikt. De score is geen gekalibreerde kans dat de voorspelling klopt.',
 'shadow_factor': 'Verhoudingsdrempel tussen werkelijke en voorspelde productie voor schaduwhints. Een '
                  'afwijking kan ook bewolking zijn; terugkerende zonnestand en meerdere dagen zijn nodig.',
 'shadow_drop': 'Benodigde daling van het lokale correctieprofiel om een schaduwperiode te markeren. Kleiner '
                'reageert sneller op variatie; groter vraagt duidelijker verschil.',
 'recovery_delta': 'Benodigde stijging van het correctieprofiel om herstel na schaduw te herkennen. Helpt '
                   'geplande starts uitstellen tot bruikbaar herstel, zonder daarmee actuele metercontroles '
                   'te vervangen.',
 'horizon_min': 'Aantal minuten dat het lokale zonne-/schaduwmodel vooruit projecteert. Verder vooruit geeft '
                'meer context maar ook meer onzekerheid.',
 'projection_step_min': 'Tijdstap van de zonneprojectie, in minuten. Kleinere stappen geven meer '
                        'rekenpunten, niet noodzakelijk nauwkeurigere onderliggende voorspellingen.',
 'limit_w': 'Softwareplafond per fase. Ook bij een meter die fasen optelt blijven de stroomgrenzen fysiek '
            'per fase gelden. Watt is een benadering van stroom bij de werkelijke spanning en arbeidsfactor.',
 'start_headroom_w': 'Minimaal vrije faseruimte voor nieuwe starts. Laat ruimte voor onverwachte huislasten. '
                     'Geen toestemming om de fysieke automaat te vervangen door software.',
 'control_starts': 'AAN laat fasebewaking nieuwe starts blokkeren bij onvoldoende ruimte. Alleen inschakelen '
                   'nadat meterrichting en aansluiting gecontroleerd zijn. UIT maakt de fase-informatie '
                   'adviserend.',
 'shed_on_overlimit': 'AAN mag SolarPilot bij geverifieerde fase-overschrijding eigen onderbreekbare lasten '
                      'afbouwen. Fabrikantbeveiligingen, beschermde programma’s en echte automaten blijven '
                      'leidend. Niet aanzetten zonder fasecontrole.',
 'learning_enabled': 'Activeert lokaal leren voor dit onderdeel. Leren gebruikt echte, bruikbare '
                     'waarnemingen en verleent nooit zelfstandig nieuwe bedieningsrechten.',
 'monitor_power_entities': 'Aanvullende afzonderlijke vermogensmeters om fase-attributie te leren zonder '
                           'deze toestellen te bedienen. Geen verzamellijst van PV, net en virtuele '
                           'dubbeltellers gebruiken. Een gecontroleerde toestelstap vereist bruikbare '
                           'beginmetingen en stabiele andere meters om als eigen fasebewijs te tellen.',
 'learning_min_delta_w': 'Minimale duidelijke vermogenssprong om faseherkenning te leren. Kleine sprongen '
                         'zijn moeilijk van gewone huisruis te onderscheiden.',
 'learning_settle_s': 'Wachttijd na een vermogenssprong om de bijbehorende fasemetingen te laten volgen. Te '
                      'kort koppelt verschillende meetmomenten; te lang kan andere veranderingen meenemen.',
 'learning_max_window_s': 'Langste tijdsafstand voor een leerbare vermogensverandering. Daarbuiten wordt de '
                          'toewijzing te onzeker en verworpen.',
 'learning_min_samples': 'Minimaal aantal bruikbare waarnemingen voordat een geleerd profiel gebruikt mag '
                         'worden. Verlagen maakt sneller resultaten maar kan een toevallige relatie '
                         'overwaarderen.',
 'learning_min_confidence': 'Minimale interne score voor faseherkenning. Deze score is geen elektrische '
                            'veiligheidsgoedkeuring of statistische kans.',
 'use_learned_device_map': 'AAN gebruikt voldoende betrouwbaar geleerde fase-toewijzing ook bij planning. '
                           'UIT houdt leren adviserend. Onbekende of onbetrouwbare toewijzing blijft '
                           'conservatief.',
 'roundtrip_efficiency': 'Efficiëntie over de volledige laad- én ontlaadcyclus.0,80 betekent 20% totaal '
                         'batterij-/omvormerverlies:1 kWh geladen zonne-energie levert circa 0,8 kWh terug. '
                         'Niet 20% per richting; dat zou 36% totaalverlies geven.',
 'reserve_pct': 'Deel van de virtuele batterijcapaciteit dat als reserve niet beschikbaar is voor de '
                'what-if. Hoger geeft minder benutbare opslag. Dit stuurt geen echte batterij.',
 'capacities_kwh': 'Te vergelijken virtuele batterijcapaciteiten in kWh. Dit bepaalt hoeveel energie '
                   'opgeslagen kan worden, niet hoe snel. Scenario’s blijven technische schattingen.',
 'powers_kw': 'Te vergelijken laad-/ontlaadvermogens in kW. Vermogen begrenst hoe snel een virtuele batterij '
              'overschot opvangt of import vermindert; het is niet de opslagcapaciteit.',
 'capacity_kwh': 'Bruikbare energiecapaciteit van deze echte batterij. Gebruik de toepasselijke bruikbare '
                 'waarde, niet automatisch het commerciële bruto getal. BMS-grenzen blijven onaangeraakt.',
 'soc_entity': 'Actuele laadtoestand van dit batterijprofiel. Native sensoren vereisen %, een eindige waarde '
               'van 0 tot 100 en verse echte rapportage. Een geldige input_number-helper mag onveranderd '
               'blijven maar niet restored, toekomstig of ongeldig zijn. Ontbrekend bewijs geeft geen '
               'fysieke vrijgave.',
 'power_sign': 'Tekenafspraak van deze batterijvermogensmeter. Laden en ontladen moeten kloppen om '
               'eigenverbruik en terugmelding juist te interpreteren.',
 'min_soc_pct': 'Absolute softwarematige ondergrens voor deze batterij. Geen versoepeling van de '
                'fabrikant-BMS. Een hogere waarde geeft minder ontlaadbare energie.',
 'reserve_soc_pct': 'Gewenste batterijreserve boven de harde ondergrens. Wordt behouden bij gewone '
                    'energiesturing, met de gekozen strategie.',
 'max_soc_pct': 'Hoogste gewenste laadtoestand voor deze batterij. De eigen fabrikantgrens blijft leidend; '
                'SolarPilot kan geen hogere fysieke capaciteit creëren.',
 'max_charge_w': 'Maximaal aangevraagd laadvermogen voor dit batterijprofiel. Blijft beperkt door '
                 'beschikbare energie, netvoorwaarden en fabrikantmogelijkheden.',
 'max_discharge_w': 'Maximaal aangevraagd ontlaadvermogen voor dit batterijprofiel. Mag een echte omvormer- '
                    'of BMS-limiet niet overstijgen.',
 'control_kind': 'Alleen uitlezen verstuurt niets. Ondersteund number/input_number-setpoint of scripts maakt '
                 'fysieke regeling mogelijk, maar pas met beide toestemmingen en exclusief eigenaarschap. De '
                 'actuator of het geselecteerde script mag niet aan een Wallbox-apparaat gekoppeld zijn; '
                 'controleer willekeurige scriptinhoud zelf. Numerieke native grenzen en stap moeten '
                 'neutraal nul exact kunnen weergeven; anders blijft fysieke regeling uit.',
 'exclusive_control_confirmed': 'Bevestigt dat niet tegelijk een andere externe regeling batterijsetpoints '
                                'schrijft. Alleen werkelijk aanvinken na controle; gelijktijdige regelaars '
                                'kunnen elkaar tegenwerken.',
 'number_sign': 'Tekenafspraak van het numerieke batterijcommando. Positief moet het bedoelde laden of '
                'ontladen zijn. Verkeerd teken kan het tegenovergestelde gedrag veroorzaken.',
 'charge_script': 'Bestaand script voor werkelijk laden van de batterij, met overeengekomen '
                  'vermogenvariabelen. Controleer de scriptinhoud en terugmelding; de naam bewijst de '
                  'werking niet.',
 'discharge_script': 'Bestaand script voor werkelijk ontladen van de batterij. Respecteer reserve, '
                     'exporttoestemming en fysieke terugmelding.',
 'idle_script': 'Bestaand script dat eigen batterijsetpoints veilig neutraliseert. Dit is niet vanzelf '
                'hetzelfde als de batterij stroomloos zetten. Verwijderen vereist daarna verse gemeten '
                'neutrale power en, bij numerieke aansturing, een werkelijk neutraal doel; ontbrekend bewijs '
                'of een fout geeft geen blinde retry.',
 'strategy': 'Strategie voor echte batterijen: adviserend, verbruikers eerst, piekbeperking of gecombineerd. '
             'Geen strategie omzeilt de expliciete bedieningstoestemmingen of veiligheidsgrenzen.',
 'grid_target_w': 'Gewenst netto netvermogen voor de batterijstrategie. Dit is geen toegestaan extra '
                  'huisverbruik en geen gegarandeerd resultaat bij trage terugmelding.',
 'charge_reserve_w': 'Vermogensbuffer die bij het laden van echte batterijen als reserve blijft. Hoger '
                     'voorkomt sneller import, maar benut minder kleine overschotten.',
 'discharge_reserve_w': 'Vermogensbuffer bij het berekenen van ontlaaddoelen. Helpt onbedoelde injectie '
                        'voorkomen; een te grote buffer laat meer netafname over.',
 'allow_grid_charge': 'AAN staat opladen van een echte batterij uit het net toe binnen de gekozen strategie. '
                      'UIT beperkt gewone laadopdrachten tot zonneoverschot. Dit is een bewuste financiële '
                      'keuze, geen standaard noodzaak.',
 'allow_export_discharge': 'AAN staat ontladen van een echte batterij richting het net toe. UIT houdt '
                           'ontlading gericht op eigen importvermindering. Controleer contract, omvormer en '
                           'veiligheidsvoorwaarden.',
 'command_min_interval_s': 'Minimale tijd tussen echte batterijopdrachten. Na een verse start zonder vorige '
                           'opdracht wordt niet fictief gewacht; na een verzonden opdracht blijft de '
                           'intervalbescherming gelden.',
 'target_tolerance_w': 'Toegestane afwijking tussen verse gemeten batterijpower van ná de opdracht en het '
                       'aangevraagde doel. Een eerder passende meting is geen ACK. Te groot kan een fout als '
                       'succes behandelen; te klein kan meetruis als fout zien. Bij verwijderen moet het '
                       'numerieke doel ook exact neutraal zijn.',
 'apply_now': 'Importeert bewust de lokaal aanwezige privéconfiguratie en historische bootstrap. Controleer '
              'wat vervangen wordt. De private bestanden horen nooit in de publieke GitHub-repository.',
 'early_grid_enabled': 'Globale toestemming voor goedkope netfallback van daarvoor individueel vrijgegeven '
                       'lasten. Beide niveaus moeten toestemming geven. De actuele net-, comfort- en '
                       'toestelvoorwaarden blijven leidend.',
 'cheap_grid_limit_eur_kwh': 'Hoogste afnameprijs waarbij goedkope netfallback mag gelden. Zonder '
                             'betrouwbare reeks blijft de gekozen vaste terugval belangrijk; dit is geen '
                             'voorspelling van je hele factuur.',
 'early_grid_requires_forecast_shortfall': 'AAN laat goedkope netfallback alleen toe wanneer de '
                                           'zonneverwachting waarschijnlijk onvoldoende is voor het '
                                           'resterende doel. UIT kan prijsoptimalisatie eerder netstroom '
                                           'kiezen.',
 'adaptive_power_guard': 'Gebruikt na voldoende exclusieve metingen een begrensd hoger P 90-vermogensprofiel '
                         'voor conservatievere planning. Verlaagt niet blind de ingestelde basiswaarde en '
                         'herschrijft het handmatige veld niet.',
 'adaptive_power_min_samples': 'Aantal goede exclusieve vermogensmonsters vóór de planningsschatting mag '
                               'worden verhoogd. Geen reden om het initiële vermogen te laag in te vullen.',
 'adaptive_power_max_multiplier': 'Bovengrens op de aangeleerde vermogensverhoging ten opzichte van de '
                                  'ingestelde nominale waarde. Dit is geen nieuwe veilige fysieke '
                                  'vermogenslimiet.',
 'start_button': 'De actuele START-knop van de afwasmachine-integratie. Kies nooit PAUSE, RESUME, STOPRESET '
                 'of een slimme stekker. Oude herstelde knoppen worden geweigerd. Een nooit ingedrukte knop '
                 'kan unknown tonen; live gereedmelding, verbinding, deur en afstandstoestemming blijven '
                 'afzonderlijk verplicht. Test de juiste knop eerst bewust met een geladen en geschikte '
                 'machine.',
 'dishwasher_state_entity': 'Oorspronkelijke Appliance state van de AEG/Electrolux-machine, niet de '
                            'afgeleide helper Afwasmachine actief. Ready To Start betekent gereed; Running '
                            'bevestigt een echte start. End Of Cycle wordt onmiddellijk bij de '
                            'statuswijziging vastgelegd en blijft bewaard na Off of Disconnected. Cycle '
                            'phase is een afzonderlijke aanvullende bron voor voorwas/drogen. Alleen Off of '
                            'een verbroken verbinding bewijst geen succesvolle afronding.',
 'dishwasher_connection_entity': 'Actuele verbindingsstatus van hetzelfde AEG/Electrolux-apparaat. Offline, '
                                 'onbekend of een rapport ouder dan de ingestelde grens blokkeert een nieuwe '
                                 'start. Tijdens een lopende cyclus wordt niet blind gestopt bij ontbrekende '
                                 'verbinding.',
 'dishwasher_remote_entity': 'Expliciete toestand die START op afstand toestaat. Controleer dit in de '
                             'fabrikantapp en de ruwe HA-toestand. Not Safety Relevant Enabled wordt niet '
                             'standaard aanvaard: dat label bewijst geen startrecht. Deze optie omzeilt '
                             'nooit fysieke of fabrikantbeveiligingen.',
 'dishwasher_door_entity': 'Echte deurstatus van de afwasmachine. Een HA-binary_sensor met device_class door '
                           'meldt normaal on bij open en off bij dicht; bevestig dit op jouw toestel. Een '
                           'deur die na klaarzetten opent, trekt de toestemming in. AirDry tijdens een al '
                           'lopende cyclus wordt niet onderbroken.',
 'dishwasher_connection:cycle_program_entity': 'Het reeds gekozen afwasprogramma, alleen uitlezen. '
                                               'SolarPilot kiest of wijzigt geen programma. De eenmalige '
                                               'toestemming is aan deze keuze gekoppeld; een gewijzigde '
                                               'keuze vraagt opnieuw klaarzetten. Het programma dient ook '
                                               'als sleutel voor gemeten cyclusprofielen.',
 'dishwasher_connection:power_entity': 'Exclusieve fysieke vermogensmeter van deze afwasmachine in W/kW. '
                                       'Naast bestaand verbruik voor regeling maakt deze bron elektrische '
                                       'activiteit zichtbaar wanneer de cloudstatus ontbreekt. De schakelaar '
                                       'wordt nooit bediend door deze waarneming. Een gedeelde, geschatte of '
                                       'oude bron wordt niet als bewijs gebruikt.',
 'dishwasher_alert_entity': 'Optionele alarmbron. Bij koppeling moet deze actueel zijn en een expliciet '
                            'geconfigureerde vrij-toestand hebben. De fabrikant blijft eigenaar van lek-, '
                            'deur- en apparaatbeveiliging. Een generieke OFF-waarde is alleen bruikbaar als '
                            'de werkelijke bronbetekenis gecontroleerd is.',
 'dishwasher_delay_entity': 'Optionele oorspronkelijke uitgestelde-starttijd. Alleen een actuele numerieke '
                            'nul laat SolarPilot starten. Een ingestelde native vertraging of onbekende '
                            'waarde blokkeert de extra start, om twee planners te voorkomen. SolarPilot wist '
                            'de fabrikantvertraging niet zelf.',
 'dishwasher_ready_states': 'Puntkomma-gescheiden ruwe toestanden waarin nog geen cyclus loopt en een start '
                            'mogelijk is, bijvoorbeeld Ready of Idle alleen na verificatie. Dit blijft '
                            'onvoldoende zonder de overige bronnen en een eenmalige Klaarzetten-toestemming. '
                            'Voltooid en bezig mogen niet ook als gereed worden gebruikt.',
 'dishwasher_running_states': 'Ruwe toestanden die een bestaande cyclus voorstellen: wassen, spoelen, drogen '
                              'en een gepauzeerd programma. Deze blijven beschermd en mogen niet opnieuw '
                              'gestart of voor energietekort afgebroken worden. Neem alle werkelijk '
                              'voorkomende fasen op, niet onbekend/unavailable.',
 'dishwasher_finished_states': 'Expliciete ruwe eindtoestanden die een voltooid programma bevestigen. Alleen '
                               'hiermee wordt een volledig gemeten profiel afgerond. Nul watt, een open '
                               'droogdeur of een verbroken verbinding is geen einde. Na voltooiing is een '
                               'nieuwe klaarzettoestemming nodig.',
 'dishwasher_connected_states': 'Ruwe verbindingswaarden die aantoonbaar online betekenen, '
                                'puntkomma-gescheiden. Disconnected, unknown en unavailable mogen niet als '
                                'verbonden worden geconfigureerd.',
 'dishwasher_remote_states': 'Ruwe waarden waarbij START op afstand daadwerkelijk beschikbaar is. De '
                             'standaardwoorden zijn voorlopige voorbeelden. Voeg een onduidelijke waarde '
                             'niet toe om de blokkering te laten verdwijnen; test de toestemming in de '
                             'fabrikantapp. Ontbrekende toestemming voorkomt nieuwe starts.',
 'dishwasher_closed_states': 'Ruwe toestanden voor gesloten deur. Gebruik bij een geverifieerde standaard '
                             'binaire deurbron off. Neem geen open/on-waarde op als gesloten. Opnieuw openen '
                             'na klaarzetten trekt de eenmalige starttoestemming in.',
 'dishwasher_safe_states': 'Ruwe toestanden van de optionele alarmbron waarbij geen blokkerend alarm geldt. '
                           'Dit is geen vervanging voor lekbeveiliging en de fabrikantinterlocks. Zonder '
                           'gekoppelde alarmbron blijven die fabrikantbeveiligingen leidend.',
 'dishwasher_stale_s': 'Maximum ouderdom van iedere benodigde AEG-statusbron in seconden, standaard 300. Te '
                       'oud blokkeert nieuwe starts. Neem een grens die past bij aantoonbare rapportage, '
                       'niet steeds langer om offline apparaten te accepteren. last_reported toont '
                       'HA-rapportage, niet gegarandeerd het fysieke meetmoment.',
 'dishwasher_ticket_hours': 'Geldigheidsduur voor een handmatig in SolarPilot klaargezette beurt. In '
                            'APP-modus geldt in plaats hiervan de vastgelegde geplande dag met startdeadline '
                            'en herstelvenster; zo kan een belading na 13:00 ook de volgende dag tot de '
                            'afgesproken deadline blijven wachten.',
 'dishwasher_mapping_confirmed': 'Bevestig pas nadat START-knop, alle statuswaarden, verbonden toestel en '
                                 'deur-/remote-startbetekenis werkelijk zijn gecontroleerd. Dit zet het '
                                 'toestel niet automatisch op Auto en maakt geen cyclus klaar. Geen algemene '
                                 'toestemming om een leeg of niet voorbereid apparaat te starten.',
 'analysis:enabled': 'Bewaart lokaal begrensde meetgegevens, beslisredenen en SolarPilot-waarschuwingen voor '
                     'analyse. AAN verstuurt niets naar ChatGPT of een andere dienst en bedient geen '
                     'apparaat. UIT stopt nieuwe gedetailleerde analyseregistratie; reeds bewaarde data '
                     'verloopt volgens de bewaartermijn. Lokaal brononderzoek en de aparte '
                     'warmtepompgeschiedenis blijven werken; leer-/aanpassingsbeleid houdt zijn eigen '
                     'werking. Een handmatige actuele export blijft mogelijk.',
 'include_related_entities': 'Neemt ondersteunde, niet-uitgeschakelde bronentiteiten van dezelfde gekoppelde '
                             'apparaten mee, zodat bijvoorbeeld andere warmtepomptemperaturen kunnen worden '
                             'onderzocht. Camera, persoon-, tracker-, slot- en media-entiteiten worden niet '
                             'meegenomen. Er geldt een zichtbare limiet van 250 bronnen, expliciete bronnen '
                             'eerst.',
 'retention_days': 'Maximale ouderdom van gedetailleerde opgeslagen analysedata: één tot zeven dagen. Vast '
                   'maximum 2016 meetrondes, 20000 bronwijzigingen en 6000 gebeurtenissen kan de periode '
                   'verder beperken. De export vermeldt de werkelijk aanwezige periode en hiaten. Bestaande '
                   'andere leer-/dagaggregaten kunnen oudere samenvattingen bevatten.',
 'analysis:sample_interval_s': 'Gedetailleerde momentopname iedere 300 seconden standaard, instelbaar '
                               '60–900. Dit verandert het gewone regelritme niet. Korter geeft meer '
                               'analysepunten maar meer opslag en een kortere periode door maximaal 2016 '
                               'meetrondes. De laatste maximaal 1440 regelcycli/twee uur zijn aanvullende '
                               'RAM-details en verdwijnen bij herstart.',
 'extra_entities': 'Maximaal 50 bestaande, relevante extra bronentiteiten voor een gericht onderzoek. Geen '
                   'camera’s, locatie, personen, sloten, credentials of volledige HA-database. De '
                   'uiteindelijke bronlimiet blijft 250 en de export meldt afgekapt bereik. Voeg geen '
                   'persoonlijke vrije tekst of secrets toe.',
 'analysis_export': 'Open Export → Export samenstellen voor één lokaal gecomprimeerd '
                    'JSON.GZ-onderzoeksbestand. Kies 1 uur, 24 uur of 7 dagen; de beschikbare geschiedenis '
                    'wordt niet verkort wegens de vroegere 16 MB-berichtgrens. Alleen dezelfde ingelogde '
                    'Home Assistant-beheerder kan het bestand tien minuten lang downloaden. Na uitpakken is '
                    'het gewone JSON. Instellingen, centrale voorrang, metingen, modellen en bewaarde '
                    'beslissingen worden meegenomen voor zover aanwezig. Namen, IDs en verwijzingen worden '
                    'standaard consistent gepseudonimiseerd; schema-sleutels, eenheden en statuswaarden '
                    'blijven behouden. Controleer altijd vóór delen. Geen automatische upload, geen '
                    'toestelopdracht en geen herstelbare Home Assistant-back-up.',
 'dishwasher_arm': 'Bevestigt dat één afwasbeurt geladen, gekozen en geschikt is voor externe start. '
                   'SolarPilot wacht vervolgens op de normale zonne-/planningsvoorwaarden en actuele deur-, '
                   'verbinding- en remote-startbronnen. Geen onmiddellijke geforceerde start. Een begonnen '
                   'cyclus mag netstroom gebruiken als zon later wegvalt.',
 'dishwasher_cancel': 'Trekt uitsluitend een nog niet gebruikte klaarzettoestemming in. Een lopende of al '
                      'verstuurde onzekere cyclus wordt niet gestopt, gepauzeerd, gereset of stroomloos '
                      'gemaakt. Het afwasprogramma stopt of annuleer je met de fabrikantbediening.',
 'learning_hub': 'Toont Meetkwaliteit met de meetbasis per model, open analysebevindingen en Automatisch '
                 'onderzoek. Het lokale onderzoek beoordeelt maximaal eenmaal per minuut de bestaande '
                 'warmtepompmeters, Wallboxsessiebron, PV-voorspelling en toestelmetingen. Alleen nieuwe '
                 'werkelijke bruikbare bronrapporten leveren nieuwe meterwaarnemingen. Status, bewijs, '
                 'mogelijke oorzaken, voorstellen en vervolgstappen zijn uitleesgegevens; het onderzoek '
                 'wijzigt geen koppelingen, metertekens, instellingen of apparaatbediening. Bij Analyse '
                 'nodig download je onder Export met één klik de analyse van 7 dagen. Laat het bestand hier '
                 'analyseren en upload desgewenst het JSON-adviesrapport. Alleen een beheerder beheert die '
                 'rapporten. Een antwoord handelt een bevinding alleen af bij dezelfde uitgegeven export en '
                 'de nog actuele bevindingversie. Meer gegevens nodig houdt de bevinding open. Adviezen voor '
                 'Panasonic, SolarPilot-instellingen en logica blijven voorstellen; een upload wijzigt geen '
                 'leerbeleid, instellingen, code of apparaten. Logica met een proposal_id wordt alleen als '
                 'uitgevoerd getoond als het vertrouwde register van de geïnstalleerde release dat '
                 'bevestigt. Andere categorieaanduidingen bevestigen geen toegepaste instelling. '
                 'Modelzekerheid is een technische maat; meer planberekeningen zijn geen extra '
                 'onafhankelijke leerdagen.',
 'learning_hub:sampling': 'Gemeten restlast: leer ook wanneer de Wallbox of beheerde apparaten draaien, maar '
                          'trek alleen hun actuele, aparte W/kW-meting af. Ontbrekende, geschatte, dubbele, '
                          'niet-synchrone of pas geschakelde bronnen worden geweigerd. Alleen rustig: blijf '
                          'die perioden overslaan. Dit raakt de gegevens voor voorspellingen, niet de echte '
                          'beschikbare netruimte of de grenzen voor een start. Een meter moet de bedoelde '
                          'fysieke last exclusief meten; twee unieke namen bewijzen dat niet.',
 'learning_hub:adaptation': 'Eerst mijn toestemming verzamelt en vergelijkt een recent '
                            '14-dagen-basislastprofiel zonder dat recente alternatief te gebruiken. Begrensd '
                            'automatisch mag dat profiel per uur/dagtype toepassen na minstens vier '
                            'onafhankelijke vergelijkingsdagen met eerdere dagen als training, minimaal tien '
                            'procent en twintig watt minder gemiddelde fout. De afwijking van het gewone '
                            'profiel is begrensd op plus of min 25 procent. Bij onvoldoende of verslechterd '
                            'bewijs valt de voorspelling terug op het gewone profiel. Je normale bestaande '
                            'live basislastmodel blijft ook in adviesstand leren; dit is geen stilzetten van '
                            'alle modellen. Temperaturen, deadlines, vermogensgrenzen, prioriteiten en '
                            'toestemmingen worden niet gewijzigd.',
 'learning_hub:notifications': 'Gewone analysebevindingen blijven bij Meetkwaliteit en Export; zij maken '
                               'geen Home Assistant-melding, ook niet wanneer deze vroegere voorkeur '
                               'aanstaat. Een bestaande algemene melding Analyse nodig wordt opgeruimd. '
                               'Dringende regelingsfouten en bewezen Aquarea-incompatibiliteit houden hun '
                               'eigen gerichte melding, die na herstel verdwijnt. Download desgewenst de '
                               'analyse van zeven dagen. Onderzoek en gegevensverzameling blijven doorgaan.',
 'dishwasher_phase_entity': 'Aanvullende oorspronkelijke Cycle phase-sensor van dezelfde machine. Toont '
                            'bijvoorbeeld Prewash, Drying of Ado Drying en wordt gebruikt voor het gemeten '
                            'faseprofiel. Appliance state blijft de bron voor gereed, werkelijk gestart en '
                            'voltooid. Unavailable bij Ready To Start is bij deze AEG een normale wachtfase, '
                            'geen reden om starten te blokkeren. Zonder deze bron blijven fasen onbekend; er '
                            'worden geen nulvermogens verzonnen.',
 'dishwasher_arming_mode': 'APP gebruikt een nieuw waargenomen overgang naar exact Enabled op de fysieke '
                           'Delay Start/APP-knop als toestemming voor één belading. Er is geen AEG-timer en '
                           'geen extra SolarPilot-klaarzetknop nodig. Het schema wordt onmiddellijk '
                           'opgeslagen; de start wacht op gesloten deur, actuele Connected/Ready To Start en '
                           'bevestigde koppelingen. Handmatig behoudt de eerdere expliciete klaarzetknop. Na '
                           'een eerste installatie met APP al Enabled vraagt SolarPilot eenmaal APP uit/aan; '
                           'een herstart of reconnect is geen nieuwe knopdruk.',
 'dishwasher_start_deadline': 'Gewone uiterste starttijd op de geplande dag, standaard 13:00 volgens de Home '
                              'Assistant-tijdzone. Tot dat tijdstip geldt de stabiele zonnevoorwaarde. Voor '
                              'maandag kan hieronder een andere tijd worden ingesteld. Daarna mag met '
                              'afzonderlijke nettoestemming gestart worden zonder vijf extra minuten '
                              'zonnevertraging. Het is een START-deadline, niet een tijdstip waarop alles '
                              'klaar moet zijn. Deur, verbinding, autorisatie, softwarelimieten en '
                              'Automatisch regelen blijven verplicht; storingen kunnen een start '
                              'verhinderen.',
 'dishwasher_monday_start_deadline': 'Optionele afwijkende START-deadline voor maandag; leeg gebruikt ook op '
                                     'maandag de gewone uiterste starttijd. Met bijvoorbeeld 10:00 wordt een '
                                     'aanvraag die zondag na de gewone grens wordt klaargezet aan maandag '
                                     'gekoppeld met 10:00 als uiterste starttijd; dinsdag en alle andere '
                                     'dagen houden de gewone deadline. De bestaande toestemming voor '
                                     'netstroom bij de deadline en alle deur-, verbinding-, programma-, '
                                     'prioriteits- en elektrische controles blijven ongewijzigd.',
 'dishwasher_after_deadline': 'Wat gebeurt er als je een nieuwe APP-belading op of na de uiterste starttijd '
                              'klaarzet? Standaard Volgende dag: vandaag niet meer automatisch starten, '
                              'morgen eerst zon en uiterlijk de deadline die voor die dag geldt, met '
                              'eventuele netstroom. Een maandagafwijking wordt ook gebruikt als je zondag '
                              'klaarzet. Het gaat om de volgende kalenderdag, niet onbeperkt wachten tot er '
                              'ooit een zonnige dag is. Zelfde dag is een bewuste alternatieve keuze: bij '
                              'een late belading vervalt de zonnevoorwaarde direct en mag netstroom '
                              'aanvullen. Een geplande dag wordt vastgelegd en schuift niet iedere ochtend '
                              'opnieuw op.',
 'dishwasher_deadline_grid_allowed': 'Op de APP-startdeadline vult netstroom altijd ontbrekende zon aan '
                                     'binnen de elektrische grenzen; de oude keuze is vervallen. Een '
                                     'opgeslagen UIT-waarde kan de deadline niet langer uitstellen. De '
                                     'deur-, fout-, bron- en remote-controles blijven gelden. Een lopende '
                                     'wasbeurt wordt niet onderbroken wanneer later de zon wegvalt.',
 'dishwasher_deadline_grace_min': 'Begrensd herstelvenster na de startdeadline, standaard 120 minuten. Als '
                                  'een tijdelijke blokkering verdwijnt, mag de nog niet verstuurde start '
                                  'binnen dit venster alsnog doorgaan. Na 30 seconden overschrijding '
                                  'verschijnt eenmaal een HA-melding. Na het venster vervalt de aanvraag en '
                                  'vraagt SolarPilot opnieuw APP-vrijgave. Dit is geen toestemming om een '
                                  'onzekere of mislukte START-opdracht automatisch opnieuw te sturen.',
 'dishwasher_alert_mode': 'Toestand gebruikt de bestaande expliciete lijst veilige alarmwaarden. AEG-vlaggen '
                          'beoordeelt de oorspronkelijke DISH_ALARM-attributen: alle technische alarmvlaggen '
                          'moeten OFF zijn; een onbekende of ontbrekende vlagset blokkeert. Alleen de twee '
                          'bekende zout-/glansmiddelmeldingen zijn geen startblok. Het totaalgetal Alerts=2 '
                          'wordt dus niet als twee technische storingen en ook niet blind als veilig '
                          'beschouwd. Er wordt geen alarm op de machine gewist.',
 'dishwasher_priority_enabled': 'Het bestaande AEG-voorkeursprofiel blijft behouden. Een beschermde '
                                'afwasbeurt krijgt haar bestaande plek ten opzichte van Wallbox en lagere '
                                'flexibele lasten; na een bevestigde centrale wijziging is de lijst Voorrang '
                                'leidend. Extra SG neemt geen afwasvermogen af. Een lopende cyclus wordt '
                                'nooit onderbroken. De voorkeur verandert geen Panasonic-instelling of '
                                'native START-recht.',
 'dishwasher_ev_solar_priority': 'Standaard AAN voor deze update. Bij actuele bevestigde Full Solar, '
                                 'werkelijk gemeten zonneproductie en stabiele net-/Wallboxmetingen mag de '
                                 'ene afwasbeurt beginnen met zonnevermogen dat de auto nu verbruikt. '
                                 'SolarPilot verstuurt geen Wallbox-opdracht: de laadpaal moet zelf '
                                 'terugregelen. Voor het starten moet de afwasmachine volledig binnen de '
                                 'actuele net-, kwartierpiek- en fasegrenzen passen ALSOF de laadpaal nog '
                                 'niets terugregelt. EV-vermogen is nooit extra elektrische capaciteit. '
                                 'Tijdelijke netafname tijdens de reactie en latere netstroom bij bewolking '
                                 'zijn mogelijk. Omdat afwassen niet mag worden afgebroken, is dit GEEN '
                                 'terugneembare stekkerovername. Na 15 minuten zonder bevestigde netto '
                                 'balans volgt een melding en worden volgende starts op EV-vermogen '
                                 'geblokkeerd tot Herstart- en foutcontrole; de lopende beurt blijft '
                                 'afwerken. Zonder Shelly is de meter van het hele huis een balanscontrole, '
                                 'geen exact gemeten faseprofiel. UIT: vóór de deadline alleen werkelijk '
                                 'resterende injectie; de 13:00-nettoestemming blijft apart.',
 'pv_forecast:enabled': 'Gebruikt de al aanwezige Forecast.Solar-gegevens voor voorspellingen. Standaard AAN '
                        'als er een bruikbare bron wordt gevonden; een eerder expliciet uitgeschakelde '
                        'forecast wordt bij migratie niet ingeschakeld. Er worden geen extra cloudoproepen '
                        'gedaan. Zonder bron blijven net-/PV-meters, comfort en deadlines werken; '
                        'ontbrekende voorspellingen worden als onbekend gemeld.',
 'pv_forecast:auto_discover': 'Zoekt via het Home Assistant-register naar één ingeschakelde '
                              'Forecast.Solar-installatie, ongeacht aangepaste entiteitsnamen. Meerdere '
                              'installaties worden niet opgeteld of willekeurig gekozen: kies dan de '
                              'configuratie-ID uit PV-diagnose of koppel expliciet. Bestaande expliciete '
                              'bronkeuzes blijven behouden.',
 'pv_forecast:calibration_enabled': 'Vergelijkt werkelijk PV-vermogen met de ruwe forecast in volledige '
                                    'kwartieren. Pas na voldoende verschillende rustige dagen wordt een '
                                    'geleidelijk veranderende factor toegepast. Opstart, clipping, slechte '
                                    'dekking en snelle wolken worden niet als structurele schaduw geleerd. '
                                    'UIT houdt opgeslagen gegevens maar gebruikt factor 1. De actuele '
                                    'vermogensregeling wordt hierdoor niet herschreven.',
 'pv_forecast:shadow_enabled': 'AAN gebruikt grove zonne-azimut/elevatievakken met tweemaandelijkse '
                               'seizoensgroepen; zonder zonnepositie een kwartier/tijdvak. UIT gebruikt '
                               'alleen de globale kalibratie. Er is geen vaste schaduwfactor vanaf 16:00. '
                               'Een geleerde terugkerende afwijking kan ook een andere oorzaak hebben dan '
                               'schaduw.',
 'pv_forecast:show_raw': 'Toont de originele vermogenscurve naast de lokaal gecorrigeerde curve. Ruwe '
                         'curvewaarden kunnen lineair tussen Forecast.Solar-tijdstempels geïnterpoleerd '
                         'zijn; de native nu-sensor kan trapsgewijs afwijken. PV-diagnose en de export '
                         'blijven beide bronnen tonen. Deze keuze verandert geen regeling.',
 'pv_forecast:learning_preset': 'Normaal vraagt minstens vijf verschillende vergelijkbare dagen en verandert '
                                'de factor maximaal 0,05 per dag. Rustig vraagt minstens zeven dagen en '
                                'maximaal 0,025; Vlotter minimaal vijf en maximaal 0,075. De factor blijft '
                                'tussen 0,35 en 1,25, met correctie alleen bij voldoende consistent bewijs. '
                                'Dit is geen garantie op voorspelnauwkeurigheid.',
 'pv_forecast:forecast_entry_id': 'Leeg laten bij precies één gevonden Forecast.Solar-configuratie. Bij '
                                  'meerdere bronnen staat de ID in de PV-diagnose bij gevonden bronnen. Kies '
                                  'één bron die dezelfde PV-installatie vertegenwoordigt als de actuele '
                                  'meter. Dit is geen entiteits-ID en geen API-key. Verander nooit '
                                  'coördinaten of API-keys in dit veld.',
 'pv_forecast:panel_peak_wp': 'Som van het nominale DC-piekvermogen van de panelen in wattpiek. Dit is niet '
                              'hetzelfde als de AC-omvormerlimiet. Voor het opgegeven profiel 13.800 Wp; '
                              'maximaal AC blijft 10.000 W. SolarPilot wijzigt de '
                              'Forecast.Solar-configuratie hiermee niet: controleer beide instellingen.',
 'pv_forecast:inverter_limit_w': 'Maximaal bruikbaar AC-vermogen van de omvormer, voor het opgegeven profiel '
                                 '10.000 W. Vanaf 98% van deze grens worden kwartieren niet als schaduw '
                                 'geleerd. Waarden boven 110% worden als onbetrouwbaar gemarkeerd. '
                                 'Gecorrigeerde voorspelling wordt hierop begrensd. Het is geen fysieke '
                                 'omvormersturing.',
 'pv_forecast:tilt_deg': 'Opgegeven hellingshoek van de panelen ten opzichte van horizontaal. Voor het '
                         'opgegeven profiel 25°. Dit is beschrijvende installatie-informatie; SolarPilot '
                         'wijzigt Forecast.Solar niet. Bij een gewijzigde installatie worden geen '
                         'incompatibele live correctiefactoren hergebruikt.',
 'pv_forecast:azimuth_deg': 'Paneelrichting in conventie noord=0°, oost=90°, zuid=180°, west=270°. Voor het '
                            'opgegeven profiel 180°. Dit is niet de dynamische zonne-azimut voor het leren; '
                            'die wordt uit lokale zonnegegevens bepaald. Geen automatisch wijzigen van de '
                            'Forecast.Solar-bron.',
 'pv_forecast:minimum_days': 'Minstens vijf verschillende dagen per vergelijkbaar zonnestand/tijdvak voordat '
                             'een factor wordt gebruikt. Hoger vraagt meer geduld maar meer onafhankelijke '
                             'waarnemingen. De rustige preset vraagt minstens zeven dagen. Honderd metingen '
                             'op dezelfde dag tellen niet als honderd leerdagen.',
 'pv_forecast:history_days': 'Bewaart maximaal 30 dagen kwartierdiagnose met ruwe/gecorrigeerde/werkelijke '
                             'waarden en acceptatie- of afwijsreden, begrensd op 2880 regels. Het compacte '
                             'leerprofiel bewaart maximaal 45 recente vergelijkbare dagen per vak, met '
                             'evidence maximaal 120 dagen oud. Dit is geen volledige Recorder-back-up.',
 'pv_forecast:stale_s': 'Ouderdomsgrens voor de forecast, niet voor de actuele PV-/netmeter. Standaard twee '
                        'uur, passend bij een uurlijkse bron. De ongewijzigde coordinatorcache wordt niet '
                        'fris gemaakt door hem opnieuw te lezen. Bij uitval blijven echte meters leidend; '
                        'onbekende uren worden niet door fictieve productie gevuld.',
 'pv_forecast:now_entity': 'Een echte ruwe forecastbron, niet de gemeten productie of een al door SolarPilot '
                           'gecorrigeerde sensor. Vermogen in W of kW; kW wordt éénmaal met 1000 '
                           'vermenigvuldigd. Leeg laten voor eenduidige registerdetectie. Zonder volledige '
                           'forecasttijdreeks wordt een energietotaal niet verzonnen over uren verdeeld en '
                           'wordt een dagfactor niet blind op morgen toegepast.',
 'pv_forecast:next_hour_power_entity': 'Een echte ruwe forecastbron, niet de gemeten productie of een al '
                                       'door SolarPilot gecorrigeerde sensor. Vermogen in W of kW; kW wordt '
                                       'éénmaal met 1000 vermenigvuldigd. Leeg laten voor eenduidige '
                                       'registerdetectie. Zonder volledige forecasttijdreeks wordt een '
                                       'energietotaal niet verzonnen over uren verdeeld en wordt een '
                                       'dagfactor niet blind op morgen toegepast.',
 'pv_forecast:remaining_entity': 'Een echte ruwe forecastbron, niet de gemeten productie of een al door '
                                 'SolarPilot gecorrigeerde sensor. Energie in Wh of kWh; Wh wordt éénmaal '
                                 'door 1000 gedeeld. Leeg laten voor eenduidige registerdetectie. Zonder '
                                 'volledige forecasttijdreeks wordt een energietotaal niet verzonnen over '
                                 'uren verdeeld en wordt een dagfactor niet blind op morgen toegepast.',
 'pv_forecast:today_entity': 'Een echte ruwe forecastbron, niet de gemeten productie of een al door '
                             'SolarPilot gecorrigeerde sensor. Energie in Wh of kWh; Wh wordt éénmaal door '
                             '1000 gedeeld. Leeg laten voor eenduidige registerdetectie. Zonder volledige '
                             'forecasttijdreeks wordt een energietotaal niet verzonnen over uren verdeeld en '
                             'wordt een dagfactor niet blind op morgen toegepast.',
 'pv_forecast:tomorrow_entity': 'Een echte ruwe forecastbron, niet de gemeten productie of een al door '
                                'SolarPilot gecorrigeerde sensor. Energie in Wh of kWh; Wh wordt éénmaal '
                                'door 1000 gedeeld. Leeg laten voor eenduidige registerdetectie. Zonder '
                                'volledige forecasttijdreeks wordt een energietotaal niet verzonnen over '
                                'uren verdeeld en wordt een dagfactor niet blind op morgen toegepast.',
 'pv_forecast:current_hour_entity': 'Een echte ruwe forecastbron, niet de gemeten productie of een al door '
                                    'SolarPilot gecorrigeerde sensor. Energie in Wh of kWh; Wh wordt éénmaal '
                                    'door 1000 gedeeld. Leeg laten voor eenduidige registerdetectie. Zonder '
                                    'volledige forecasttijdreeks wordt een energietotaal niet verzonnen over '
                                    'uren verdeeld en wordt een dagfactor niet blind op morgen toegepast.',
 'pv_forecast:next_hour_entity': 'Een echte ruwe forecastbron, niet de gemeten productie of een al door '
                                 'SolarPilot gecorrigeerde sensor. Energie in Wh of kWh; Wh wordt éénmaal '
                                 'door 1000 gedeeld. Leeg laten voor eenduidige registerdetectie. Zonder '
                                 'volledige forecasttijdreeks wordt een energietotaal niet verzonnen over '
                                 'uren verdeeld en wordt een dagfactor niet blind op morgen toegepast.',
 'session_mode_entity': 'Bron die de werkelijk actieve sessie onderscheidt: zonne-auto, manueel of gestopt. '
                        'De ingestelde Full Solar-optie kan bij manueel starten aan blijven; daarom is '
                        'alleen die instelling standaard onvoldoende om EV-vermogen over te nemen. Gebruik '
                        'een actueel, gecontroleerd statusveld. Een dashboardhelper die alleen netimport '
                        'naar manueel vertaalt is onvoldoende. Bij een ontbrekende, te oude of strijdige '
                        'bron geen EV-overname; werkelijk restoverschot blijft bruikbaar. Een al gekoppelde '
                        'maar oude of ongeldige bron blijft onbekend; de leervraag benoemt deze oorzaak '
                        'zonder de actualiteitsgrens te verlengen.',
 'trust_solar_setting': 'Deze terugvalkeuze staat standaard UIT. Alleen AAN na bewust bevestigen dat de '
                        'configuratie de effectieve sessie betrouwbaar weergeeft of dat er geen '
                        'manuele/plannings-overrides zijn. Anders kan netstroom ten onrechte als '
                        'vrijmaakbare zon worden gezien. Bij een expliciet gekoppelde sessiebron blijft een '
                        'onbekende of manuele toestand blokkerend, ook wanneer deze terugvaloptie aanstaat.',
 'session_solar_states': 'Volledige waarden, gescheiden door puntkomma. Alleen exact matchen, hoofdletters '
                         'worden genegeerd. Daarnaast moet de oorspronkelijke zonnelaadinstelling Full Solar '
                         'melden. Geen substring-match en geen onbekende modecode raden.',
 'session_manual_states': 'Volledige waarden die werkelijk manueel of niet-zongeregeld laden betekenen. Deze '
                          'herkenning wint altijd van een Full Solar-instelling; het laadvermogen is niet '
                          'vrijmaakbaar. Geen maximumstroom, pauze of hervatopdracht wordt naar de laadpaal '
                          'gestuurd.',
 'session_stopped_states': 'Volledige waarden die een gestopte sessie aanduiden. SolarPilot rekent alleen '
                           'met echte injectie. Een nulvermogen alleen bewijst niet dat de sessie gestopt '
                           'is; de lader kan op zon wachten.',
 'appliance_type': 'Dit is de herkenbare categorie: afwasmachine, wasmachine, droogkast of andere '
                   'verbruiker. Ze staat los van het bedieningstype en verleent geen nieuwe fysieke rechten. '
                   'Een AEG-afwasmachine gebruikt de gecontroleerde start-only koppeling; voor andere merken '
                   'of toestellen moeten een bestaande adapter of echte scripts met terugmelding eerst '
                   'gecontroleerd worden. Een categoriewijziging neemt geen gemeten toestelvermogen aan.',
 'apply_changes:confirm': 'Controleer het overzicht vóór bevestigen. Gewone wijzigingen worden zonder '
                          'volledige herlading toegepast. Actieve toestelbronnen en bescherming blijven '
                          'bevroren tot het toestel vrij is. Annuleren bewaart de bestaande werking. De '
                          'bevestiging start of stopt niets; pas de volgende normale regelbeslissing kan op '
                          'basis van nieuwe effectieve regels een opdracht geven.',
 'request_scope': 'Alleen volgende beurten behoudt de al opgeslagen dag, deadline en nettoestemming van de '
                  'huidige APP-aanvraag. Ook huidige beurt verandert deadline en nettoestemming op dezelfde '
                  'geplande kalenderdag, zonder een nieuwe toestemming te maken. Een deadline die daardoor '
                  'al voorbij is kan bij de volgende regelcyclus tot starten leiden, maar alleen met alle '
                  'normale apparaat- en elektrische controles. Een al begonnen beurt wordt nooit opnieuw '
                  'gestart.',
 'pending_changes:cancel': 'Selecteer opgeslagen voorstellen die je niet meer wilt toepassen. Alleen die '
                           'voorstellen worden verwijderd; de huidige werkende regels blijven staan en geen '
                           'apparaat wordt uitgezet. Een voorstel kan bijvoorbeeld wachten op het einde van '
                           'een wasbeurt, een bevestigde stop of de uitkomst van een al verzonden opdracht. '
                           'Onbekend is niet hetzelfde als uit.',
 'confirm_replace:confirm': 'Bevestigt dat je een vervangend toestelprofiel wilt opbouwen. De wizard begint '
                            'met lege fysieke koppelingen en een nieuw ID; controleer het voorgestelde '
                            'vermogen en de start-/stopvoorwaarden opnieuw. De oude historiek blijft apart. '
                            'Oude APP-vrijgave, automatische deelname en geleerd verbruik worden nooit '
                            'automatisch aan het nieuwe apparaat toegekend.',
 'manage_device:device_id': 'Kies het afzonderlijke SolarPilot-profiel dat je wilt bekijken of wijzigen. Dit '
                            'is niet het verwijderen of veranderen van de oorspronkelijke merkintegratie. De '
                            'huidige cyclus blijft gekoppeld aan zijn bestaande bronnen; gevoelige '
                            'wijzigingen kunnen na opslaan wachten tot die cyclus is afgerond.',
 'manage_device:section': 'Instellingen opent de basis en bescherming; Koppelingen opent de oorspronkelijke '
                          'actuator en terugmelding; Planning opent de energie- en prioriteitskeuzes. Je '
                          'doorloopt de resterende wizard en bevestigt aan het einde. Bekijken is altijd '
                          'mogelijk terwijl Automatisch regelen actief is en doet op zichzelf niets met '
                          'toestellen.',
 'replace:device_id': 'Selecteer alleen het oude SolarPilot-toestel dat vervangen wordt. De opvolger krijgt '
                      'een nieuw ID zodat oude metingen of een oude starttoestemming niet voor de nieuwe '
                      'machine worden gebruikt. Bij een lopende of onzekere cyclus wachten archiveren en '
                      'toevoegen op veilige vrijgave; de overige regeling loopt door.',
 'dashboard:manage_devices': 'Toestellen beheren toont actieve profielen, wachtende wijzigingen en '
                             'archieven. Toevoegen, koppelen, plannen en vervangen gebeurt via dezelfde '
                             'gecontroleerde Home Assistant-wizard. Andere apparaten blijven actief; er is '
                             'geen algemene pauze nodig om dit venster te openen. Een nieuw of opnieuw '
                             'gekoppeld profiel begint Uitgesloten. De uitklapbare uitleg op Overzicht toont '
                             'dezelfde startvoorwaarden, bekend vermogen en wachttijden zonder een tweede '
                             'regeling of toestelactie.',
 'priority_board': 'Verplaats de gewone flexibele regels met pijltjes of slepen en sla de volgorde op. Auto '
                   'laden staat standaard achteraan. Ongeacht de positie van Auto laden en tijdelijke '
                   'Wallboxkeuzes heeft de warmtepomp/SG vaste toegang tot actueel coherent bevestigd '
                   'autonoom zonnelaadvermogen. Dat is voorwaardelijk overdraagbaar vermogen, geen vrije '
                   'injectie. De gewone toestelvolgorde en hun eigen overnamerechten blijven behouden; de '
                   'afwasmachine blijft beschermd.',
 'sg_boost:entity_id': 'Kies de bestaande fysieke Shelly-uitgang die de SG-aanvraag bedient. Eén uitgang '
                       'krijgt één eigenaar. Een gewijzigde koppeling schakelt automatische boost uit en '
                       'vereist opnieuw bevestiging; een helper, script of tweede schakelentiteit is geen '
                       'geschikte vervanging.',
 'sg_boost:enabled': 'Staat standaard uit. Aan staat uitsluitend extra SG-zonneboost toe in Automatisch '
                     'regelen, na bevestigde ingebruikname, werkende lokale aflooptimer en actuele bronnen. '
                     'Panasonic blijft zelfstandig comfort en beveiligingen regelen.',
 'sg_boost:profile': 'Kies het lokaal gecontroleerde toepassingsbereik: uitsluitend tapwater of algemene '
                     'SG-boost volgens de actieve Panasonic-bedrijfsmodus. Eén contact geeft toestemming; '
                     'het kiest geen twee gelijktijdige warmtevragen. Een ander profiel vraagt nieuwe '
                     'expliciete lokale bevestiging en wijzigt geen native percentages of temperaturen.',
 'sg_boost:profile_confirmed': 'Bevestig dat het geselecteerde toepassingsbereik overeenkomt met de lokaal '
                               'ingestelde SG-capaciteit. Bij profielwisseling verschijnt eerst een nieuwe '
                               'bevestiging zonder vinkje; een oud vinkje wordt niet overgenomen. Dit is '
                               'afzonderlijk van de condens-/dauwpuntbeveiliging.',
 'sg_boost:cooling_protection_confirmed': 'Bevestig alleen een geschikte bestaande '
                                          'condens-/dauwpuntbeveiliging voor extra koeling. Een losse '
                                          'luchtvochtigheidssensor of vaste minimumtemperatuur bewijst geen '
                                          'volledige bescherming. Zonder bevestiging blokkeert algemene SG '
                                          'bij koelbedrijf of onzekere koelcontext; normale '
                                          'Panasonic-koeling en SG-instellingen blijven behouden.',
 'sg_boost:commissioning_confirmed': 'Bevestig pas na lokale controle van de juiste SG-trap, gewenste native '
                                     'basisinstellingen, gekozen toepassingsbereik en afwezigheid van '
                                     'dubbele automatiseringen. Bewust gekozen ruimteboost is geen '
                                     'configuratiefout. Deze keuze is geen bewijs van een geslaagde fysieke '
                                     'proef door SolarPilot. Een firmwareversiewijziging alleen vraagt geen '
                                     'nieuwe handmatige bevestiging; dezelfde fysieke uitgang wordt '
                                     'automatisch opnieuw gecontroleerd.',
 'sg_boost:watchdog_confirmed': 'Bevestig pas na een echte lokale proef: de Shelly opent het contact wanneer '
                                'vernieuwing uitblijft, en tijdige vernieuwing verlengt de timer zonder '
                                'UIT/AAN-geklapper. Opstartstand UIT beschermt niet tegen elke '
                                'communicatie-uitval. Een firmwareversiewijziging alleen wist deze '
                                'bevestiging niet: actuele configuratie en timerbewijs blijven automatisch '
                                'gecontroleerd.',
 'sg_boost:threshold_w': 'Benodigde zonnebijdrage voor een nieuwe SG-aanvraag, standaard 3000 W. Het '
                         'bruikbare budget kan echte restinjectie, de afgeleide bijdrage uit compleet '
                         'actueel HP-vermogen en voorwaardelijk actueel coherent autonoom '
                         'EV-zonnelaadvermogen omvatten. Oude, handmatige, onbekende of tegenstrijdige '
                         'laadgegevens geven geen EV-credit. Netafname, batterijontlading en de vaste '
                         'huisbuffer worden eenmaal verwerkt; het budget is door actuele PV begrensd. Voor '
                         'de nieuwe herstart na een bewezen automatische sessielimiet of onbekende reactie '
                         'geldt minstens de hoogste waarde van deze drempel en de SG-totaalraming. Een '
                         'budget verruimt geen afzonderlijke fase- of kwartiergrens.',
 'sg_boost:expected_power_w': 'Geraamd totaalvermogen van de warmtepomp met SG, standaard 3000 W. Vanaf '
                              'beta.110 betreft dit bewust het totaal, niet dat vermogen nogmaals bovenop '
                              'bestaand warmtepompverbruik. Bestaande ingestelde getallen blijven behouden. '
                              'Alleen een complete verse exclusieve warmtepompmeting verlaagt de getoetste '
                              'mogelijke toename: max(0, totaalraming min huidige opname). Bij ontbrekende, '
                              'oude, onvolledige of overlappende meting wordt de volle totaalraming '
                              'getoetst. Geen gegarandeerd fysiek maximum of nulimportgarantie.',
 'sg_sources:power_scope': 'Selecteer wat deze fysieke meter werkelijk omvat: het gehele toestel of '
                           'uitsluitend voeding 1/2. Onbevestigde of gedeeltelijke dekking blijft zichtbaar. '
                           'Een inbegrepen heater wordt niet nogmaals opgeteld.',
 'sg_sources:tank_target_entity': 'Alleen-lezen weergave van het gewone native tankdoel. SolarPilot schrijft '
                                  'geen temperatuur; een gelijkblijvende appweergave is geen SG-relaisfout '
                                  'en geen bewijs van het effectieve SG-doel.',
 'sg_sources:tank_temperature_entity': 'Werkelijke tanktemperatuur uit een geschikte bron. De interne '
                                       'Shelly-temperatuur is niet de watertemperatuur. Een stijgende '
                                       'tanktemperatuur alleen bewijst geen SG-eigendom.',
 'sg_sources:zone_entities': 'Alleen uitlezen van kamertemperaturen en native standen. Panasonic blijft '
                             'eigenaar; SolarPilot schakelt deze thermostaten niet tussen AUTO en UIT. Zone- '
                             'of ruimte-UIT bewijst geen gehele warmtepomp-UIT; bronbereik, elektrische '
                             'activiteit en native bedrijfsbewijs blijven apart.',
 'sg_sources:activity_entity': 'Alleen-lezen fysieke bedrijfsinformatie van Panasonic. Een boostaanvraag, '
                               'bevestigde relaisstand en werkelijke Panasonic-reactie zijn afzonderlijke '
                               'statussen.',
 'sg_sources:power_entity': 'Een fysieke W/kW-meter met expliciet aangegeven dekking. Het totale '
                            'toestelvermogen is geen gegarandeerd terugwinbaar SG-vermogen: normaal comfort '
                            'kan na vrijgeven doorgaan. Gebruik één bevestigde totaalmeter of de twee '
                            'deelmeters hieronder; geen totaalmeter plus nogmaals een inbegrepen voeding. '
                            'Beta.87 gebruikt een verse eindige negatieve HP-verbruikswaarde binnen het '
                            'bestaande plausibele bereik na volledige broncontrole als 0 W. Ruwe bronwaarde, '
                            'watts en normalisatiemarkering blijven bewaard. Ontbrekend, oud, geschat, '
                            'hersteld, toekomstig, overlap of onvolledige dekking blijft onbekend. Net-, '
                            'export-, batterij- en fasetekens veranderen niet; dit is geen kalibratiebewijs.',
 'sg_sources:power_supply1_entity': 'Optionele fysieke W/kW-meter voor voeding 1. Deze voeding kan naast de '
                                    'compressor ook andere onderdelen omvatten. Gebruik samen met voeding 2 '
                                    'alleen na bevestiging van volledige niet-overlappende dekking. Beta.87 '
                                    'gebruikt een verse eindige negatieve HP-verbruikswaarde binnen het '
                                    'bestaande plausibele bereik na volledige broncontrole als 0 W. Ruwe '
                                    'bronwaarde, watts en normalisatiemarkering blijven bewaard. Ontbrekend, '
                                    'oud, geschat, hersteld, toekomstig, overlap of onvolledige dekking '
                                    'blijft onbekend. Net-, export-, batterij- en fasetekens veranderen '
                                    'niet; dit is geen kalibratiebewijs.',
 'sg_sources:power_supply2_entity': 'Optionele fysieke W/kW-meter voor voeding 2. Het automatische '
                                    'Panasonic-profiel duidt deze voeding als elektrische bijverwarming, met '
                                    'een zichtbare profielaanname; een eerder bewust gekozen andere functie '
                                    'blijft behouden. Alleen actueel geldig vermogen telt: gemeten 0 W is '
                                    'nul, een ontbrekende of verouderde bron blijft onbekend en maakt de som '
                                    'onvolledig. Totale niet-overlappende dekking wordt afzonderlijk '
                                    'bevestigd; de profielrol is geen heater-terugmelding of SG-toestemming. '
                                    'Beta.87 gebruikt een verse eindige negatieve HP-verbruikswaarde binnen '
                                    'het bestaande plausibele bereik na volledige broncontrole als 0 W. Ruwe '
                                    'bronwaarde, watts en normalisatiemarkering blijven bewaard. Ontbrekend, '
                                    'oud, geschat, hersteld, toekomstig, overlap of onvolledige dekking '
                                    'blijft onbekend. Net-, export-, batterij- en fasetekens veranderen '
                                    'niet; dit is geen kalibratiebewijs.',
 'sg_sources:power_activity_threshold_w': 'Actief verbruik wordt vanaf deze waarde per geldige voeding '
                                          'weergegeven, standaard 200 W. Deze drempel verandert uitsluitend '
                                          'de uitleg en grafische weergave; hij schakelt niets en verandert '
                                          'de SG-startdrempel niet. Kies een waarde boven het gemeten '
                                          'rustverbruik. Vermogen toont elektrische activiteit; alleen '
                                          'aanvullende actuele Panasonic-informatie kan tapwater, '
                                          'ruimteverwarming of koeling onderscheiden. Complete verse actieve '
                                          'hoofdmeting met passende actuele gekozen verwarmings-/koelcontext '
                                          'kan een taak afleiden ondanks een cloud-rustmelding; bronuitleg '
                                          'en ruwe melding blijven in Details/export. Een expliciete actuele '
                                          'UIT-melding geeft deze idle-afleiding niet. Dit verandert geen '
                                          'SG-vrijgave.',
 'sg_sources:power_supply1_role': 'Het bestaande meterpaar gebruikt automatisch het Panasonic-profiel: '
                                  'voeding 1 is de warmtepompvoeding inclusief regeling en pompen. Hiervoor '
                                  'hoef je niets opnieuw in te vullen. Dit is een herkenbare '
                                  'weergave-aanname, geen afzonderlijke compressor-terugmelding. Een eerder '
                                  'bewust gekozen andere functie blijft behouden. De totale meetdekking en '
                                  'SG-toestemming blijven afzonderlijk; deze optionele keuze bedient niets.',
 'sg_sources:power_supply2_role': 'Het bestaande meterpaar gebruikt automatisch het Panasonic-profiel: '
                                  'voeding 2 is de elektrische bijverwarming. Hiervoor hoef je niets opnieuw '
                                  'in te vullen. De grafiek duidt de opgenomen elektrische hulp aan op basis '
                                  'van het vermogen; dit is geen afzonderlijke heater-terugmelding. Een '
                                  'eerder bewust gekozen andere functie blijft behouden. De totale '
                                  'niet-overlappende meetdekking wordt apart bevestigd. Deze keuze geeft '
                                  'geen nieuwe SG-toestemming.',
 'sg_sources:split_power_confirmed': 'Bevestig lokaal dat beide meters samen de twee volledige voedingen '
                                     'meten zonder overlap. Namen bewijzen die dekking niet. Gelijke of '
                                     'inspecteerbaar overlappende bronnen worden geweigerd. Een gewijzigd '
                                     'meterpaar vraagt nieuwe bevestiging; de bestaande totale meting wordt '
                                     'nooit dubbel opgeteld.',
 'sg_sources:compressor_frequency_entity': 'Optionele bestaande compressorfrequentiebron in Hz; uitsluitend '
                                           'uitlezen. Een handmatig bekeken waarde wordt geen sensor. '
                                           'Actuele frequentie kan compressorbedrijf bevestigen, geen effect '
                                           'van SG.',
 'sg_sources:sg_status_entity': 'Optionele bestaande bron die werkelijk de ontvangen SG-status op Panasonic '
                                'meldt. Relaisstand, programma WATER, stijgende temperatuur of '
                                'compressorbedrijf zijn daarvoor geen vervanging. Zonder geschikte actuele '
                                'bron blijft ontvangen SG onbekend; extra verbruik door SG is niet '
                                'afzonderlijk bewezen.',
 'sg_sources:sg_dhw_capacity_percent': 'Het door jou op Panasonic ingestelde tapwaterpercentage van SG '
                                       'capaciteit 1, alleen voor de doelweergave. Bijvoorbeeld: 115% van '
                                       'een normaal doel van 50 °C geeft een berekend SG-doel van 57,5 °C. '
                                       'SolarPilot schrijft dit percentage niet naar Panasonic en gebruikt '
                                       'het niet voor SG-toestemming, responsebewijs of het thermische '
                                       'model. Het standaardveld 100% is nog geen bevestigde instelling.',
 'sg_sources:sg_dhw_capacity_target_entity': 'Selecteer de native tankbron waarop het bevestigde SG '
                                             'tapwaterpercentage betrekking heeft. Dit is alleen een binding '
                                             'voor de berekende doelweergave; de gewone tankdoelbron, '
                                             'koelcontext en SG-regeling worden niet gewijzigd. De exacte '
                                             'geregistreerde apparaatidentiteit wordt lokaal vastgelegd. Een '
                                             'andere of vervangen tank krijgt geen oude bevestiging.',
 'sg_sources:sg_dhw_capacity_confirmed': 'Bevestig dat het ingevulde tapwaterpercentage overeenkomt met jouw '
                                         'Panasonic SG-capaciteit 1. Selecteer hiervoor het exacte native '
                                         'water_heater- of climate-tankdoel met geregistreerde '
                                         'apparaatidentiteit. Een automatisch gevonden of vervangen tank '
                                         'erft geen eerder percentage. Vanaf dit lokale bevestigingsmoment '
                                         'wordt het SG-doel berekend uit een vers normaal tankdoel; er is '
                                         'geen aparte Panasonic-doelterugmelding nodig. Oude geschiedenis '
                                         'wordt niet aangevuld. De actuele contactstand blijft afzonderlijk: '
                                         'bij UIT toont de kaart een doel voor bij AAN. Native prioriteiten, '
                                         'afronding en SG-grenzen worden niet automatisch afgeleid of '
                                         'aangepast.',
 'sg_advanced:lease_s': 'Korte lokaal aflopende toestemming, standaard 300 seconden. Zonder tijdige actuele '
                        'vernieuwing opent het contact ook bij HA-uitval. Automatisch algemeen SG-zonbedrijf '
                        'kan hiermee doorlopen zolang huidige zonne-, bron-, koel-, elektrische en '
                        'contactvoorwaarden passen; er is geen oneindige hardwaretoestemming. De lease reset '
                        'oorspronkelijke start of minimum niet. Voor handmatige en andere begrensde routes '
                        'wordt de lease ook vóór eerste AAN en vernieuwing binnen hun oorspronkelijke '
                        'eindtijd en bevestigingsruimte gehouden. Alleen actueel gecontroleerde vernieuwing '
                        'behoudt de aanvraag.',
 'sg_advanced:renew_s': 'Vernieuw de korte lokale toestemming standaard iedere 60 seconden zolang de huidige '
                        'SG-voorwaarden dit toelaten. Dat gebeurt zonder verplichte UIT/AAN-cyclus. '
                        'Automatisch algemeen zonbedrijf heeft geen uurstop: oorspronkelijke start en '
                        'verstreken tijd blijven behouden. Onvoldoende bruikbare zon wordt ook bij lage '
                        'P1-afname via gewone tekortvertraging/minimum beoordeeld. Harde voorwaarden, '
                        'bron-/contactkwaliteit, handmatige keuzes en eindtijden van begrensde routes '
                        'blijven leidend.',
 'sg_advanced:start_delay_s': 'De gewone SG-startstabiliteit, standaard 120 seconden. Voor een nieuwe '
                              'aanvraag moet het bruikbare actuele zonnebudget passend zijn. Na een bewezen '
                              'beëindigde automatische sessielimiet of onbekende reactie bevestigen minstens '
                              'twee nieuwe oorspronkelijke rapporten dat budget gedurende dezezelfde tijd; '
                              'daarna wordt geen tweede identieke startbuffer toegevoegd. Gewone korte '
                              'bron-/wolkenoverbrugging bij een bestaande initiële startklok houdt haar '
                              'aparte voorwaarden. Gewijzigde binding, harde blokkering of ontbreken van '
                              'actuele herstartbewijs geeft geen geleende tijd. De overige '
                              'context-/zonne-resetroutes gebruiken hun afzonderlijke bewijsduur.',
 'sg_advanced:min_session_s': 'Minimale SG-aanvraagduur, standaard 1200 seconden, voor gewone zachte '
                              'tekortvrijgave. Het minimum begint bij bevestigde AAN en wordt niet door een '
                              'leasevernieuwing of uurpassage gereset. Ook onvoldoende bruikbaar gezamenlijk '
                              'zonnebudget telt als tekort wanneer ruwe P1 onder de importbuffer blijft. Na '
                              'voltooide gewone tekortduur en minimum kan vrijgave volgen. Automatisch '
                              'algemeen zonbedrijf mag zonder uurstop doorgaan zolang actuele voorwaarden '
                              'passen. Bij handmatige/begrensde routes is het minimum hoogstens hun '
                              'resterende maximumtijd. Harde guards en afzonderlijke native, handmatige, '
                              'bron- en contactvoorwaarden blijven leidend; Panasonic bepaalt de '
                              'compressorlooptijd.',
 'sg_advanced:stop_delay_s': 'Gewone tekortbevestiging, standaard 300 seconden. De ruwe P1-importbuffer '
                             'houdt haar eigen timer. Automatisch algemeen zonbedrijf heeft daarnaast een '
                             'eigen tekorttimer zodra geldig bruikbaar P1-/HP-/EV-zonnebudget onder max(0, '
                             'startdrempel - hysteresis_w) komt, ook bij lage netafname. Vrijgave wacht op '
                             'deze tekortduur en het oorspronkelijke effectieve minimum; die lopen parallel '
                             'en hun begin wordt niet door leasevernieuwing verschoven. Daardoor kan het '
                             'minimum een tekort nog begrensd overbruggen. Tijdelijke overbrugging vernieuwt '
                             'alleen een korte lokale lease onder passende voorwaarden. Harde guards, '
                             'onbruikbare noodzakelijke bronnen, native voorwaarden, handmatige overname en '
                             'eindtijden van begrensde routes blijven leidend. De Wallboxreactie blijft '
                             'afzonderlijk begrensd en verandert geen ruwe fase-, kwartier- of '
                             'batterijmeting. Bij bruikbare-zontekort wordt de lokale toestemming ook binnen '
                             'de oorspronkelijke tekort-/minimumdeadline en bevestigingsruimte gehouden; '
                             'herstart, klokterugloop of een herhaald oud hoog sample geeft geen nieuwe '
                             'gratieperiode.',
 'sg_advanced:import_threshold_w': 'Wolkenbuffer voor ruwe actueel gemeten netafname, standaard 600 W. '
                                   'Strikt hogere afname start de importtekorttimer, standaard 300 seconden; '
                                   'bij de grens of lager wordt die importtimer gewist. Het gewone minimum '
                                   'en tekortduur blijven parallel gelden. Automatisch algemeen '
                                   'SG-zonbedrijf controleert daarnaast bruikbaar gezamenlijk zonnebudget, '
                                   'zodat te weinig zon of nacht ook bij minder dan 600 W afname tot '
                                   'begrensde vrijgave kan leiden. Lage import alleen is geen bewijs van '
                                   'zon. Dit verruimt geen fysieke capaciteit of afzonderlijke grens.',
 'sg_advanced:hysteresis_w': 'Marge onder de SG-startdrempel voor het bruikbare-zontekort in automatisch '
                             'algemeen bedrijf: geldig gezamenlijk zonnebudget onder max(0, startdrempel - '
                             'deze marge) start de eigen tekorttimer. Stopvertraging en de oorspronkelijke '
                             'minimumduur blijven afzonderlijk gelden; een ontbrekende bron geeft geen '
                             'doorlopend zonrecht. Dit veld behoudt ook zijn alternatieve '
                             'nieuwe-zonneperioderoute, standaard 300 W echte restinjectie, met het '
                             'bestaande vijfminutenbewijs van lage en later teruggekeerde zon. Een eerdere '
                             'zonnedip is niet verplicht voor actuele herstart na een bewezen automatische '
                             'sessielimiet of onbekende reactie. Dit is geen ruwe-P1-importbuffer of nieuwe '
                             'toestemming uit alleen timerafloop.',
 'sg_advanced:rest_s': 'Standaard 900 seconden verzoekrust als terugval voor een nieuwe SG-aanvraag; een '
                       'toegestaan doorlopend automatisch algemeen AAN-contact wordt niet eerst geopend om '
                       'deze rust te starten. Dit is geen door SolarPilot bewezen compressorbeveiliging. '
                       'Vóór afloop kan alleen volledig passend oorspronkelijk bewijs van een beëindigde '
                       'automatische sessielimiet of onbekende reactie die rust vervangen: actuele UIT na '
                       'einde en minstens twee nieuwe bruikbare-zonrapporten over eenmaal de ingestelde '
                       'startstabiliteit. Na gewone rust kan de huidige geldige configuratie met actuele UIT '
                       'en nieuwe stabiele bronnen een nieuwe aanvraag dragen, ook bij onvolledige oude '
                       'historie of gewijzigde configuratie; een oude beleidshash blokkeert dan niet '
                       'blijvend. Bruikbaar budget omvat echte injectie, compleet actueel passend '
                       'HP-vermogen en actueel coherent bevestigd autonoom EV-zonneladen en moet minstens '
                       'max(startdrempel, SG-totaalraming) halen. Native voltooiing, aantoonbaar geen '
                       'opname, profielwijziging, handmatige UIT en onzekere opdrachten houden hun eigen '
                       'voorwaarden. Geen nieuwe sessie door alleen tijd of reload; elke nieuwe lease wordt '
                       'actueel gecontroleerd.',
 'sg_advanced:max_session_s': 'Maximumduur voor tijdelijk handmatige en andere begrensde SG-routes, '
                              'standaard 3600 seconden. De instelling blijft voor die routes vóór het '
                              'minimum gelden en wordt niet door opnieuw kiezen, uitlezen of herstart '
                              'verlengd. Automatisch algemeen SG-zonbedrijf heeft deze uurstop niet: een '
                              'toegestaan AAN-contact mag blijven zolang actuele bruikbare zon en alle '
                              'overige voorwaarden passen, met korte lokaal aflopende toestemming en actuele '
                              'hercontrole bij vernieuwing. De oorspronkelijke start/elapsed wordt niet '
                              'administratief gereset. De instelling is geen aftelklok voor dit automatische '
                              'zonbedrijf. Een al geopende oude sessiewachtstand kan wel via het nieuwe '
                              'actuele herstartpad worden beoordeeld.',
 'sg_advanced:ack_timeout_s': 'Korte begrensde wachttijd voor fysieke relaisterugmelding, standaard 20 '
                              'seconden. Een geslaagde servicecall of ongewijzigd tankdoel geldt niet als '
                              'relaisbevestiging.',
 'sg_advanced:stale_s': 'Maximale ouderdom van benodigde metingen, standaard 120 seconden. Een nieuwe '
                        'ontvangst of betrouwbare heartbeat houdt een onveranderde waarde actueel; '
                        'last_changed alleen is onvoldoende.',
 'dashboard:analysis_export': 'Maakt uitsluitend voor een ingelogde Home Assistant-beheerder één lokaal '
                              'gecomprimeerd JSON.GZ-onderzoeksbestand met actuele bronnen, instellingen, '
                              'modellen, beslisredenen en werkelijk beschikbare historie. Het gekozen '
                              'rollende venster is 1, 24 of 168 uur. Warmtepompgeschiedenis bewaart apart '
                              'maximaal dertig lokale kalenderdagen en exporteert alle overlappende datums. '
                              'Geregistreerde dagtotalen blijven volledige kalenderdagtotalen; gedeeltelijke '
                              'grensdatums en meetdekking worden afzonderlijk vermeld. Geen energie naar '
                              'rato, backfill, automatische upload of toestelopdracht. Pseudonimisering en '
                              'privacyfilters vervangen niet het controleren vóór delen; nooit publiek op '
                              'GitHub zetten.',
 'water:enabled': 'Activeert uitsluitend het uitlezen en lokaal bijhouden van de bewust gekozen '
                  'waterbronnen. Minstens één waterbron is nodig. UIT beëindigt de actuele meetcontext '
                  'zonder opgeslagen historie te wissen; opnieuw inschakelen vraagt nieuwe actuele metingen. '
                  'SolarPilot opent of sluit geen waterkraan en verandert de energie- of toestelregeling '
                  'niet.',
 'water:volume_entity': 'Kies de cumulatieve watermeterstand van de bestaande meter, met passende '
                        'volume-eenheid en tellerkenmerken. SolarPilot gebruikt alleen bevestigde '
                        'verschillen tussen passende metingen. Een tellerreset, nieuwe bron of '
                        'meetonderbreking krijgt een nieuwe baseline; ontbrekende liters worden niet geschat '
                        'of uit actueel debiet aangevuld. De eerste meting is een beginpunt en geen '
                        'dagverbruik.',
 'water:flow_entity': 'Kies het werkelijk gemeten actuele waterdebiet van de bedoelde meter, met een '
                      'ondersteunde volume-per-tijd-eenheid. SolarPilot rekent de waarde om naar liter per '
                      'minuut. Een verse gemeten nul is geldig; een ontbrekend, oud of ongeldig rapport '
                      'wordt geen nul. Het debiet wordt niet opgeteld bij de cumulatieve watermeterstand en '
                      'vormt geen bewijs van een specifieke kraan of gebruiker.',
 'water:leak_entity': 'Kies een bestaande waterleksensor met de passende binaire bronbetekenis. Een actueel '
                      'AAN-signaal betekent dat de bron een mogelijk lek meldt; UIT is alleen de gemelde '
                      'toestand van die bron. Onbekend of onbeschikbaar wordt niet als droog bevestigd. '
                      'SolarPilot maakt geen fysiek lekbewijs uit een hoge watermeterstand en geeft nooit '
                      'een afsluitopdracht.',
 'water:source_stale_s': 'Maximale ouderdom van een werkelijk ontvangen waterbronrapport, in seconden. Een '
                         'betrouwbare nieuwe ontvangst kan ook een ongewijzigde waarde actueel houden; '
                         'alleen het veranderen van de waarde is niet vereist. Oudere, herstelde of '
                         'ongeldige waarnemingen blijven onbekend en onderbreken het bewijs voor doorlopend '
                         'watergebruik. Bij MQTT kunnen identieke waarden zonder force_update een oude '
                         'HA-rapporttijd houden. Controleer de afzonderlijke publicatie, beschikbaarheid en '
                         'bronconfiguratie; een verse totaalteller maakt debiet of lekmelding niet actueel. '
                         'Bronouderdom blind verhogen herstelt dat bewijs niet. Dit versnelt de bron zelf '
                         'niet.',
 'water:continuous_flow_l_min': 'Ondergrens voor het apart signaleren van aanhoudend gemeten waterdebiet, in '
                                'liter per minuut. Alleen actuele geldige debietrapporten boven deze drempel '
                                'tellen mee. Lager ziet kleinere aanhoudende stromen maar kan ook normaal '
                                'verbruik aanduiden; hoger mist kleinere stromen. Het signaal zegt '
                                'aanhoudend watergebruik en stelt de oorzaak of een fysiek lek niet vast.',
 'water:continuous_flow_minutes': 'Zolang moet het actuele gemeten debiet onafgebroken boven de ingestelde '
                                  'drempel blijven voordat SolarPilot aanhoudend watergebruik signaleert. '
                                  'Ontbrekende of oude rapporten, een bronwissel en een onderbreking geven '
                                  'geen doorlopende bevestiging. Een lagere waarde reageert eerder; een '
                                  'hogere waarde wacht langer. Een herstart of opgeslagen periode verleent '
                                  'geen nieuw actueel bewijs.',
 'water:notifications': 'Sta de afzonderlijke blijvende Home Assistant-waarschuwing voor een actueel gemeld '
                        'mogelijk waterlek of voldoende bewezen aanhoudend watergebruik toe. Dit geldt '
                        'alleen zolang de watermonitor is ingeschakeld. Uitschakelen trekt deze toestemming '
                        'in zonder historie te wissen. Deze optie verstuurt geen mobiele melding en bedient '
                        'geen afsluiter; ontbrekende brondata krijgt geen bevestiging dat er geen lek is.',
 'dishwasher_connection:energy_entity': 'Optionele cumulatieve energieteller van dezelfde afwasmachine in '
                                        'Wh/kWh met state_class total of total_increasing. Alleen geldige '
                                        'opeenvolgende tellerstappen tellen als geregistreerde deelenergie. '
                                        'De totale tellerstand is geen dagverbruik; gaten, reset en '
                                        'middernacht worden niet ingevuld. Koppel ook de exclusieve '
                                        'vermogensmeter.',
 'dishwasher_meter_start_w': 'Minimaal gemeten vermogen voor een afgeleide activiteitsstart. Voorlopig 10 W, '
                             'nog te toetsen aan een echte afwasbeurt. Lager kan stand-by of deurverlichting '
                             'meetellen; hoger kan kleine pompfasen missen. Geen START-opdracht of '
                             'starttoestemming.',
 'dishwasher_meter_idle_w': 'Bovengrens voor een stille elektrische fase; voorlopig 5 W en altijd lager dan '
                            'de startdrempel. Pas na de ingestelde stille duur stopt de afgeleide '
                            'activiteit. Laag vermogen betekent niet dat het afwasprogramma klaar is.',
 'dishwasher_meter_start_s': 'Benodigde tijd boven de startdrempel; voorlopig 60 seconden. Alleen '
                             'opeenvolgende verse oorspronkelijke meterberichten tellen. Korter ziet ook '
                             'korte pieken; langer vertraagt de registratie. Herstart en meetgaten beginnen '
                             'opnieuw zonder een begin in het verleden te verzinnen.',
 'dishwasher_meter_end_s': 'Benodigde stille duur om afgeleide activiteit af te sluiten; voorlopig 900 '
                           'seconden. Korte stille fasen blijven hierdoor één waargenomen sessie. Een native '
                           'actieve of gepauzeerde status blijft leidend. Ook na deze duur is succesvol '
                           'programma-einde niet bewezen.',
 'dishwasher_meter_stale_s': 'Maximale ouderdom en afstand van opeenvolgende meterberichten; voorlopig 120 '
                             'seconden. Oude of ontbrekende berichten worden onbekend, niet 0 W. Verlengen '
                             'maakt een bron niet betrouwbaarder. Het scherm verversen vernieuwt geen '
                             'oorspronkelijke rapporttijd.',
 'wallbox': 'SolarPilot leest de Wallbox; de laadpaal regelt zelf het laden. Gewone toestellen volgen hun '
            'opgeslagen volgorde en tijdelijke Wallboxkeuzes. Warmtepomp/SG heeft onafhankelijk daarvan '
            'vaste toegang tot actueel coherent bevestigd autonoom zonnelaadvermogen. Een oude, handmatige '
            'of onbekende laadsessie levert geen voorwaardelijke EV-credit; onafhankelijk gemeten '
            'P1-restoverschot blijft bruikbaar.'}

GROUP_NOTES = {'water': 'De watermonitor leest uitsluitend de geselecteerde bronnen. Meterstanden, debiet en leksignalen '
          'behouden hun eigen betekenis en meetdekking. Historische perioden worden niet met actuele waarden '
          'aangevuld.',
 'wallbox': 'SolarPilot leest de Wallbox; de laadpaal regelt zelf het laden. Auto laden staat standaard als '
            'laatste in de centrale volgorde. Hogere toegestane toestellen en SG krijgen eerst zonnestroom. '
            'Onbekende laadgegevens geven geen laadvermogen om over te nemen en blokkeren echt '
            'P1-restoverschot niet.',
 'phase': 'De meter kan import en injectie over fasen verrekenen, maar iedere fase behoudt haar eigen '
          'fysieke stroomgrens. Software is geen elektrische beveiliging.',
 'battery': 'Een simulatie is geen echte batterijbesturing. Echte regeling vereist passende bronnen, '
            'terugmelding, globale en individuele toestemming en exclusief extern eigenaarschap.',
 'local_pv': 'Forecast en leren zijn onzeker en geven nooit toestemming om actuele P1/PV, comfort of '
             'toestelbeveiligingen te negeren.',
 'dishwasher': 'Een gestart afwasprogramma blijft beschermd: geen stop/pauze/reset of stroomonderbreking '
               'voor energiesturing. Begin met gecontroleerde bronwaarden en één geschikte geladen '
               'afwasbeurt.',
 'analysis': 'Dit is een lokale diagnosefunctie, geen automatische upload of bewijs van een volledige '
             'foutvrije installatie. Perioden zonder metingen blijven onbekend.',
 'device': 'Toestelvoorwaarden, fysieke terugmelding, minimumtijden en beschermde programma’s gaan vóór '
           'energie-optimalisatie. Een ingeschakelde stekker bewijst niet dat een compressor continu draait.',
 'limits': 'Toestelvoorwaarden, fysieke terugmelding, minimumtijden en beschermde programma’s gaan vóór '
           'energie-optimalisatie.',
 'connection': 'Kies echte bestaande bronnen en test de betekenis. Gedeelde meters, virtuele dubbeltellers '
               'of een niet-terugmeldend script zijn geen betrouwbare vervanging.',
 'capacity': 'Pieksturing is een schatting voor kosten en planning, geen zekeringbeveiliging. Onbeheerde '
             'lasten en noodzakelijk comfort kunnen het doel overschrijden.',
 'economy': 'De dagkost is netafnamekost minus injectievergoeding. Direct zonneverbruik verlaagt de import '
            'al en wordt niet dubbel afgetrokken. Ontbrekende meetdekking blijft zichtbaar.',
 'forecast': 'Alleen voorspellingen. Werkelijk PV, netmeting en toestelvoorwaarden blijven leidend bij de '
             'echte uitvoering.',
 'power': 'Vermogensinstellingen zijn softwarematige planningsgrenzen. Ze verhogen nooit de echte capaciteit '
          'van de aansluiting.',
 'sg': 'Panasonic regelt zelfstandig comfort en beveiligingen. SolarPilot mag alleen de toegewezen '
       'SG-uitgang bedienen, na gecontroleerde mapping en lokale aflooptimer. Een aanvraag, gemeld contact '
       'en fysieke Panasonic-reactie zijn afzonderlijke bewijslagen.'}

def help_for(step, key, label, spec=None):
    """A complete explanation for a known schema option; HTML is escaped by UI."""
    spec = spec or {}
    text = HELP_NOTES.get(f'{step}:{key}') or HELP_NOTES.get(key) or spec.get('description')
    if text is None:
        # Group-level enable flags differ intentionally from physical permissions.
        if key == 'enabled':
            text = f'Activeert het onderdeel {step.replace("_", " ")}. Een analyse-/monitorfunctie stuurt hiermee nog geen apparaat; fysieke bediening vraagt daarnaast de bijbehorende expliciete toestemming. UIT maakt het onderdeel inactief, maar schakelt gekoppelde fysieke apparatuur niet vanzelf uit.'
        elif key == 'control_enabled':
            text = 'Geeft dit onderdeel toestemming om ondersteunde fysieke opdrachten uit te voeren. De algemene modus, eigen profieltoestemming, actuele terugmelding en fabrikantbeveiligingen blijven verplicht. Alleen inschakelen na controle; UIT is niet hetzelfde als de apparatuur stroomloos maken.'
        elif key.startswith('phase_') and key.endswith('_entity'):
            text = f'Werkelijk netto vermogen van de juiste afzonderlijke fase ({label}). Gebruik W/kW, dezelfde tekenrichting als de aansluiting en niet de totale P1-waarde voor elke fase. Verkeerde koppeling maakt fasebewaking onbetrouwbaar.'
        elif key == 'tomorrow_entity':
            text = 'Verwachte zonne-energie voor morgen in kWh. Gebruikt om werk te spreiden, niet om nu een last zonder werkelijk vermogen te starten.'
        elif key == 'sample_interval_s':
            text = 'Minimale afstand tussen leerwaarnemingen, in seconden. Dit bepaalt het leermeetritme, niet hoe vaak een apparaat wordt geschakeld. Korter geeft meer monsters van bijna dezelfde situatie; langer is lichter maar ziet minder detail.'
        else:
            raise ValueError(f'Missing specific help: {step}.{key}')
    paragraphs = [text]
    for field, title in [('recommendation','Uitgangspunt'),('on_effect','AAN'),('off_effect','UIT'),('lower_effect','Lagere waarde'),('higher_effect','Hogere waarde'),('change_effect','Bij wijzigen')]:
        if spec.get(field): paragraphs.append(f'{title}: {spec[field]}')
    if spec.get('unit'): paragraphs.append(f'Eenheid: {spec["unit"]}.')
    context = next((v for k,v in GROUP_NOTES.items() if step.startswith(k)), '')
    if context and context not in text: paragraphs.append(context)
    paragraphs.append('Wijzig dit bewust. Openen van deze uitleg bedient niets en slaat geen instelling op. In de configuratiewizard worden wijzigingen pas toegepast na de laatste bevestiging; directe dashboardbediening kan meteen actief zijn.')
    return {'title':label, 'short':text.split('. ')[0].rstrip('.')+'.', 'paragraphs':paragraphs}
