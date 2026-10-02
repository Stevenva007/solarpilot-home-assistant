"""Release-bound human help, shared by the dashboard and native option descriptions.

Source text, not executable user configuration. See tools/update_option_help.py.
No secrets, home-specific entity names or external URLs are embedded here.
"""
HELP_NOTES = {'participation': 'Automatisch laat dit toestel deelnemen aan de gewone SolarPilot-regeling; '
                  'Uitgesloten houdt het daarbuiten. Dit is geen directe aan/uit-schakelaar. In '
                  'Observatie worden geen gewone startopdrachten verstuurd; minimumtijden en beschermde '
                  'cycli blijven gelden.',
 'others_first': 'Globale standaard voor gewone verbruikers: Andere eerst of Wallbox eerst. Een '
                 'specifieke voorrang per toestel heeft voorrang op deze standaard. Gewoon '
                 'warmtepompcomfort heeft afzonderlijk voorrang; extra 60 °C gebruikt alleen werkelijk '
                 'restoverschot.',
 'manual_start': 'Vraagt na bevestiging handmatige bediening door SolarPilot. De toestelinformatie, '
                 'rusttijden en beveiligingen moeten bruikbaar zijn. Netstroom kan nodig zijn. De '
                 'status en reden blijven zichtbaar; deze knop is geen manier om fysieke bescherming te '
                 'omzeilen.',
 'manual_stop': 'Beëindigt de handmatige SolarPilot-vraag met bevestiging. Het vrijgeven van een '
                'beschermde of nog minimaal lopende cyclus kan wachten; de knop is geen noodstop of '
                'hoofdvoedingsschakelaar.',
 'boost': 'Tijdelijke boost van 30 minuten met expliciete nettoestemming binnen de softwaregrenzen. '
          'Toestelvraag, minimumtijden en foutcontroles blijven gelden. Afloop betekent terug naar '
          'normale regeling, niet gegarandeerd onmiddellijk uitschakelen.',
 'name': 'De herkenbare naam van deze koppeling in SolarPilot. Dit hernoemt het fysieke apparaat of de '
         'oorspronkelijke Home Assistant-entiteiten niet.',
 'kind': 'Kies hoe het toestel werkelijk wordt bediend: een aan/uit-schakelaar, een numeriek '
         'vermogen/stroomdoel, of start-/stopscripts met terugmelding. De keuze moet passen bij de '
         'mogelijkheden van het toestel.',
 'priority': 'Rangorde tussen gewone SolarPilot-verbruikers: 1 is het belangrijkst, 100 het minst '
             'belangrijk. Een kleiner toestel mag een onbenut restje gebruiken als een belangrijker '
             'toestel nog niet past. Minimumtijden en beveiligingen gaan altijd vóór rangorde. '
             'Wallbox-voorrang stel je afzonderlijk per toestel in.',
 'device_id': 'Selecteer het bestaande SolarPilot-toestel dat je wilt aanpassen of verwijderen. Dit '
              'is niet een opdracht om het fysieke toestel aan of uit te zetten. Verwijderen vraagt nog '
              'bevestiging.',
 'battery_id': 'Selecteer het opgeslagen batterijprofiel. De oorspronkelijke batterij-integratie wordt '
               'hierdoor niet gewijzigd of verwijderd.',
 'grid_entity': 'Netvermogen van de volledige aansluiting in W of kW. Het moet netto import/injectie '
                'meten, niet alleen één verbruiker of een energieteller in kWh. De tekenrichting wordt '
                'apart ingesteld.',
 'grid_sign': 'Bepaalt of een positieve waarde van de netmeter import of injectie betekent. Controleer '
              'met een echt bekend verbruiksmoment. Een verkeerd teken kan juist toestellen inschakelen '
              'tijdens netafname.',
 'export_entity': 'Optionele afzonderlijke exportvermogenssensor. Gebruik alleen actueel '
                  'injectievermogen in W/kW en niet geëxporteerde kWh. Zonder deze bron gebruikt '
                  'SolarPilot de gekozen netto netmeter.',
 'pv_entity': 'De werkelijk gemeten totale zonnepanelenproductie, in W of kW. Een voorspelling of '
              'dagopbrengst in kWh is hiervoor ongeschikt. Deze bron wordt onder andere gebruikt voor '
              'de gewone 50 °C-boilerregel.',
 'battery_power_entity': 'Werkelijk batterijvermogen. Hiermee voorkomt SolarPilot dat batterijontlading '
                         'als nieuwe zonne-energie wordt gezien. De tekenrichting moet kloppen. Zonder '
                         'thuisbatterij mag dit leeg blijven.',
 'battery_sign': 'Tekenafspraak van de batterijvermogensmeter: laden en ontladen moeten juist '
                 'onderscheiden worden. Dit verandert alleen de interpretatie; er wordt geen opdracht '
                 'naar de batterij gestuurd.',
 'battery_soc_entity': 'Actuele laadtoestand van een echte thuisbatterij, in procent. Geen '
                       'fietsbatterij of autobatterij kiezen voor de algemene thuisbatterijreserve.',
 'reserve_w': 'Injectiebuffer die SolarPilot niet opnieuw toewijst. Bij 600 W injectie en 150 W reserve '
              'blijft ongeveer 450 W over voor een nieuwe last. Hoger is voorzichtiger; lager benut '
              'meer zon maar geeft eerder korte netafname.',
 'max_import_w': 'Softwarematige bovengrens voor de totale netafname. Dit is geen zekeringbeveiliging '
                 'en beschermt niet zelfstandig elke fase. Lagere waarden beperken toegestane starts; '
                 'onbeheerde apparaten kunnen de grens toch overschrijden.',
 'battery_min_soc': 'Onder deze batterijlaadtoestand mag ontladen vermogen niet als beschikbare energie '
                    'voor gewone nieuwe zonnelasten worden behandeld. Dit is geen vervanging voor de '
                    'echte batterij-BMS-reserve.',
 'interval_s': 'Tijd tussen realtime regelberekeningen. Standaard 5 seconden. Korter vraagt meer '
               'rekenwerk en geeft niet vanzelf snellere cloudgegevens; langer reageert trager. Dit is '
               'geen verplicht schakelinterval en de interface mag hierdoor niet dichtklappen.',
 'settle_s': 'Wachttijd na een fysieke wijziging voordat een volgende verhoging mag worden uitgevoerd. '
             'Geeft meters en apparaten tijd om te reageren. Korter kan regelingen laten botsen; langer '
             'is rustiger.',
 'stale_s': 'Maximale ouderdom van een ontvangen bronrapport. Te oude gegevens worden niet als actuele '
            'waarheid gebruikt. Dit gaat om het laatste rapport, niet om de laatste keer dat de waarde '
            'veranderde. Verleng niet om een kapotte bron te verbergen.',
 'filter_s': 'Verzachting van korte variaties in het netvermogen. Een langer venster filtert meer ruis '
             'maar reageert trager op echte veranderingen. Veiligheidscontroles en toestelvoorwaarden '
             'blijven afzonderlijk bestaan.',
 'fault_grace_s': 'Korte buffer bij onbetrouwbare of ontbrekende informatie vóór de bijbehorende '
                  'foutreactie. Voorkomt reageren op één gemist rapport. Maak deze niet groot om '
                  'structurele meetproblemen te negeren.',
 'control_entity': 'De echte aan/uit-actuator. SolarPilot gebruikt die om het toestel te schakelen en '
                   'leest de toestand terug. Kies geen virtuele helper tenzij die bewust en betrouwbaar '
                   'de echte bediening vertegenwoordigt.',
 'number_entity': 'Numerieke actuator waarmee een ondersteund toestel werkelijk wordt aangestuurd. '
                  'Eenheid, teken, minimum, maximum en stap moeten overeenkomen met de '
                  'apparaatinterface. Dit veld geeft schrijfrecht aan de regeling.',
 'start_script': 'Bestaand Home Assistant-script dat het toestel veilig start. SolarPilot kan de inhoud '
                 'van het script niet als veilig bewijzen. Gebruik echte terugmelding en test eerst '
                 'onder toezicht.',
 'stop_script': 'Bestaand script dat het toestel veilig stopt. Een beschermd programma mag niet abrupt '
                'worden afgebroken. Controleer de inhoud; de naam van het script bewijst niet wat het '
                'doet.',
 'active_entity': 'Werkelijke aan/actief-terugmelding voor een scriptgestuurd toestel. Een succesvol '
                  'verstuurde opdracht is nog geen bevestigde fysieke start. Gebruik een bron die '
                  'onbeschikbaarheid ook doorgeeft.',
 'power_entity': 'Werkelijk actueel vermogen van dit ene apparaat, in W of kW. Dit is geen '
                 'energieteller in kWh. Een exclusieve meter maakt de vermogensschatting en historie '
                 'betrouwbaarder; een gedeelde meter kan verkeerd gedrag veroorzaken.',
 'condition_entity': 'Optionele vraag/startklaar-bron. Het toestel mag alleen meedoen als deze '
                     'toestemming geeft, bijvoorbeeld een gekozen taak of gemeten vochtvraag. Zonder '
                     'bron blijven de overige voorwaarden leidend.',
 'interlock_entity': 'Extra vrijgave voor veilige bediening. Een afwezige of niet-vrijgegeven '
                     'blokkering mag nooit als toestemming worden opgevat. Test de betekenis van on/off '
                     'voordat je deze als vergrendeling gebruikt.',
 'nominal_w': 'Realistische conservatieve planningswaarde voor het toestel. Gebruik ongeveer het '
              'werkelijk benodigde vermogen, niet bewust te laag. Een exclusieve meter kan na voldoende '
              'leren de schatting begrensd verhogen; het ingestelde veld wordt niet vanzelf '
              'herschreven.',
 'min_units': 'Kleinste bruikbare actieve instelling van de numerieke actuator. Dit kan bijvoorbeeld '
              'ampère zijn; het is niet automatisch watt. SolarPilot begint niet op een kleiner '
              'onbruikbaar doel.',
 'max_units': 'Hoogste toegestane actuatorinstelling binnen het fysieke apparaatbereik. De instelling '
              'is een softwaregrens, geen vervanging van apparaat- of installatiebeveiliging.',
 'step_units': 'Grootte van elke regelstap op de numerieke actuator. Kleine stappen zijn fijner maar '
               'vragen meer ingrepen; grote stappen reageren grover. Gebruik alleen stappen die het '
               'apparaat ondersteunt.',
 'watts_per_unit': 'Omrekening van één actuator-eenheid naar geschat elektrisch vermogen. Bijvoorbeeld '
                   'ampère naar watt met de juiste spanning en faseconfiguratie. Een foutieve '
                   'omrekening maakt de planning onbetrouwbaar.',
 'start_delay_s': 'Zolang moeten de startvoorwaarden stabiel geldig blijven vóór een nieuwe start. '
                  'Hoger voorkomt starts op korte zonnige pieken. De teller herbegint wanneer de '
                  'vereiste ruimte wegvalt.',
 'stop_delay_s': 'Zolang mag een gewoon energietekort aanhouden voordat een eigen onderbreekbare last '
                 'wordt teruggenomen. Hoger voorkomt stoppen voor een korte wolk, maar kan langer '
                 'netafname geven. Minimumlooptijd en aparte prioriteits-/veiligheidsregels blijven '
                 'gelden.',
 'min_on_s': 'Minimale looptijd na een bevestigde start. Belangrijk voor bijvoorbeeld compressoren. '
             'Deze tijd wordt niet verkort om Wallbox-voorrang of een goedkope elektriciteitsprijs te '
             'halen.',
 'min_off_s': 'Minimale rusttijd na uitschakelen voordat SolarPilot opnieuw mag starten. Kies op basis '
              'van het toestel. Een langere rusttijd vermindert korte aan/uit-cycli, maar laat sommige '
              'zonnepieken voorbijgaan.',
 'start_margin_w': 'Extra vermogen boven het verwachte toestelvermogen voor een nieuwe start. '
                   'Voorbeeld: 350 W toestel plus 100 W marge vraagt ongeveer 450 W bruikbare ruimte, '
                   'na de algemene reserve.',
 'ack_timeout_s': 'Maximale wachttijd op een echte terugmelding na een opdracht. Dit is geen '
                  'compressor-rusttijd en geen verplichte vertraging wanneer de bevestiging eerder '
                  'komt. Bij geen bevestiging volgt een fout-/onzekerheidscontrole, geen eindeloos '
                  'opnieuw schakelen.',
 'manual_hold_s': 'Rustperiode na herkende externe bediening of taakvoltooiing. SolarPilot probeert een '
                  'handmatige wijziging niet meteen ongedaan te maken. Dit is iets anders dan de '
                  'bevestigingstijd van een eigen opdracht.',
 'max_on_s': 'Maximale aaneengesloten looptijd die je voor deze last toestaat. 0 betekent geen '
             'opgelegde limiet. Een te korte limiet kan onnodige onderbrekingen veroorzaken; een '
             'bestaande veiligheidslimiet mag niet zomaar vervallen.',
 'non_interruptible': 'Een eenmaal bevestigde cyclus moet veilig kunnen afwerken, zoals een '
                      'vaatwasprogramma. AAN verhindert gewone energiebeslissingen die de cyclus abrupt '
                      'onderbreken. Gebruik dit niet als truc om voldoende startruimte te omzeilen.',
 'min_daily_runtime_min': 'Gewenste minimale totale draaitijd per dag, in minuten. 0 betekent geen '
                          'verplicht dagminimum. Dit is niet dezelfde instelling als minimumlooptijd per '
                          'start.',
 'max_daily_runtime_min': 'Hoogste totale draaitijd per dag, in minuten. 0 betekent geen daglimiet. Een '
                          'ingestelde limiet kan nieuwe starts blokkeren, ook wanneer er nog zon is.',
 'daily_deadline': 'Tijdstip waarop het ingestelde dagminimum bij voorkeur bereikt moet zijn. Een '
                   'deadline maakt geen netstroom vrij tenzij je die toestemming afzonderlijk geeft. '
                   '0-dagdoelen vragen geen verplichte taak.',
 'deadline_grid_allowed': 'Toestemming om zo nodig netstroom te gebruiken voor het dagminimum. UIT laat '
                          'een tekort aan zon mogelijk eindigen met een niet gehaald dagdoel. Net-, '
                          'fase- en toestelgrenzen blijven bestaan.',
 'daily_energy_goal_kwh': 'Gewenste dagenergie voor deze last. 0 zet dit doel uit, niet de gewone '
                          'zonnestroomregeling. De planner trekt reeds geregistreerde energie af en '
                          'plant het resterende deel.',
 'time_window_enabled': 'AAN beperkt de startvraag tot jouw eigen tijdvenster. UIT gebruikt geen extra '
                        'klokvenster. Een venster vervangt geen minimumlooptijd, terugmelding of '
                        'bescherming van een lopende cyclus.',
 'time_window_start': 'Begin van het toegestane dagvenster in de Home Assistant-tijdzone. Dit is '
                      'toestemming om te starten, geen gedwongen start op dat uur.',
 'time_window_end': 'Einde van het dagvenster in de Home Assistant-tijdzone. Houd rekening met de duur '
                    'van beschermde cycli en minimumlooptijden; dit is geen abrupte noodstop.',
 'forecast_deferrable': 'Een nieuwe start mag begrensd wachten op een gunstiger zonneblok. Een reeds '
                        'lopende last wordt niet door een nieuwe voorspelling gestopt. Zonder dagdoel '
                        'wordt de gewone overschotregeling niet permanent geblokkeerd.',
 'cheap_grid_allowed': 'Per-toesteltoestemming voor goedkope netfallback. Vereist ook de globale '
                       'planner-toestemming; alleen dit vinkje is niet voldoende. Geen garantie op '
                       'goedkoop laden bij ontbrekende prijsgegevens.',
 'phase_hint': 'Fase waarop het apparaat fysiek aangesloten is, of Auto voor voorzichtig lokaal leren. '
               'De 32 A-hoofdaansluiting blijft een grens per fase; netto optelling over fasen maakt '
               'één fase niet onbeperkt belastbaar.',
 'allow_wallbox_reclaim': 'In de gewone bediening kies je één duidelijke uitkomst bij Mag de auto minder '
                          'laden?. SolarPilot stuurt de Wallbox niet: '
                          'Full Solar moet zelf terugregelen en nieuwe metingen moeten dat bevestigen.',
 'wallbox_precedence': 'Bepaalt uitsluitend of dit toestel vóór of na Auto laden staat. In de centrale '
                       'Voorrang-lijst verplaats je de rij direct; minimumlooptijd en veiligheid blijven gelden.',
 'wallbox_energy_choice': 'Eén uitkomstkeuze: alleen vrij zonneoverschot, autoladen veilig laten afnemen '
                          'volgens de voorrang, of de strengere route voor een kort, gemeten en '
                          'onderbreekbaar toestel. Dit is nooit een garantie dat vermogen beschikbaar is.',
 'cycle_learning_enabled': 'Leert energie, duur en piek uit complete bevestigde apparaatcycli met een '
                           'eigen meter. Afgebroken of onvoldoende gemeten cycli vormen geen '
                           'betrouwbaar programma. Leren geeft geen extra bedieningsrecht.',
 'cycle_energy_kwh': 'Conservatieve energie-inschatting van één volledig programma zolang geen '
                     'bruikbaar geleerd cyclusprofiel bestaat. Dit is geen piekvermogen. Gebruik echte '
                     'programma-informatie of metingen.',
 'cycle_duration_min': 'Conservatieve duur van een volledige cyclus, in minuten. Nodig om een beschermd '
                       'programma als aaneengesloten blok te plannen. Zonder duur wordt geen '
                       'optimistische duur uit alleen het piekvermogen gegokt.',
 'cycle_program': 'Naam van het programma voor cyclusregistratie, bijvoorbeeld Eco. Verschillende '
                  'programma’s kunnen een verschillend verbruik en een andere duur hebben.',
 'cycle_program_entity': 'Optionele entiteit die het werkelijk gekozen programma rapporteert. Alleen '
                         'uitlezen. Hiermee worden geleerde cycli bij het juiste programma bewaard.',
 'wallbox:enabled': 'Zet de alleen-lezen Wallbox-monitor aan. Deze leest laadvermogen, vraag en modus '
                    'uit bestaande HA-entiteiten; SolarPilot verstuurt hier geen laadstroom-, start-, '
                    'stop- of fasecommando’s naar de Wallbox.',
 'status_entity': 'Tekststatus van de laadpaal. Exacte herkenningswoorden staan bij Geavanceerd. Een '
                  'aangesloten auto kan gepauzeerd, vol of niet startklaar zijn; een kabel alleen is '
                  'geen laadvraag.',
 'demand_entity': 'Optionele expliciete laadvraagbron. Gebruik een echte vraag/startklaar-terugmelding, '
                  'niet alleen kabel aangesloten. Laat leeg wanneer de betrouwbare tekststatus deze '
                  'informatie levert.',
 'mode_entity': 'De werkelijke zonnelaadmodus van de Wallbox, bijvoorbeeld Full Solar. Alleen uitlezen: '
                'SolarPilot herstelt of verandert de laadmodus niet automatisch.',
 'connected_entity': 'Optionele expliciete terugmelding dat er een auto op deze laadpaal aangesloten '
                     'is. Aanwezigheid geeft niet automatisch laadvraag; een volle of gepauzeerde auto '
                     'hoeft geen vermogen te reserveren.',
 'charging_threshold_w': 'Vanaf dit gemeten vermogen telt de Wallbox als daadwerkelijk ladend. '
                         'Standaard 50 W scheidt kleine standbywaarden van laden. Dit is niet het Full '
                         'Solar-startminimum van ongeveer 1380 W bij één fase.',
 'priority_min_power_w': 'Werkelijk benodigd minimum om autonoom Full Solar te beginnen. Bij bevestigd '
                         'éénfasig laden is 1380 W een uitgangspunt. Alleen gebruikt voor voorrang; '
                         'geen laadstroomopdracht. Automatisch profiel-afleiden kan deze handwaarde '
                         'vervangen.',
 'priority_start_margin_w': 'Extra ruimte boven het Full Solar-minimum voordat lagere verbruikers voor '
                            'de auto wijken. Bij 1380 W en 150 W marge is het voorrangsdoel circa 1530 '
                            'W. Hoger voorkomt starten op de grens, maar wacht langer.',
 'profile_auto': 'Leest de maximale laadstroom van dezelfde Wallbox via het HA-entiteitsregister. Geen '
                 'extra cloudverzoeken. Ontbrekende, verouderde of onduidelijke bronnen gebruiken een '
                 'zichtbaar gemarkeerde handmatige terugval. Er wordt niets naar de Wallbox geschreven.',
 'max_current_entity': 'Optionele expliciete bron voor maximale laadstroom in ampère. Bij voorkeur de '
                       'number-instelling of sensorspiegel Max charging current. ICP is de '
                       'hoofdaansluiting en is hiervoor fout. Leeg laat veilige herkenning op hetzelfde '
                       'Wallbox-apparaat toe.',
 'phases_entity': 'Alleen een bron die expliciet 1 of 3 laadfasen rapporteert. SolarPilot raadt het '
                  'aantal fasen niet uit watt, ampère of een driefasige huisaansluiting. Zonder geldige '
                  'bron geldt jouw bevestigde faseprofiel.',
 'charging_phases': 'Werkelijk gebruikte laadfasen: 1 of 3. Nu éénfase; verander pas na bevestiging van '
                    'de echte laadconfiguratie. Deze keuze stuurt geen fysieke faseschakelaar.',
 'max_current_a': 'Handmatig bevestigde terugval voor de maximale laadstroom wanneer live uitlezen niet '
                  'bruikbaar is. Uitgangspunt 25 A voor het huidige profiel. Het dashboard vermeldt dan '
                  'dat dit niet live bevestigd is. Geen elektrische beveiliging.',
 'voltage_v': 'Spanning per fase voor de vermogensschatting, standaard 230 V. 1 × 230 × 25 geeft 5750 '
              'W; 3 × 230 × 25 geeft 17250 W. Dit is een schatting, geen gemeten laadvermogen of '
              'installatiegoedkeuring.',
 'minimum_current_a': 'Minimale laadstroom per gebruikte fase voor de berekende Full Solar-grens. '
                      'Standaard 6 A; met 230 V is dat 1380 W bij 1 fase of 4140 W bij 3 fasen. Gebruik '
                      'de werkelijke laadconfiguratie.',
 'minimum_from_profile': 'AAN berekent het zonnelaadminimum uit fasen × rekenspanning × minimumstroom. '
                         'UIT behoudt het afzonderlijk ingestelde minimumvermogen. Je kunt later naar 3 '
                         'fasen zonder herschrijven van de regeling; pas het profiel bewust aan.',
 'demand_states': 'Puntkomma-gescheiden exacte laadstatussen die vraag betekenen. Gebruik geen komma '
                  'als scheiding: sommige Wallbox-statusnamen bevatten zelf een komma. Onbekende '
                  'teksten gelden niet zomaar als toestemming.',
 'idle_states': 'Puntkomma-gescheiden statusnamen zonder actuele laadvraag, bijvoorbeeld Ready of '
                'Paused. Verwar wachten op groene energie niet met klaar/geen vraag; dat zou de '
                'voorrang verkeerd om maken.',
 'full_solar_states': 'Puntkomma-gescheiden herkenningswaarden voor uitsluitend zonneladen, '
                      'bijvoorbeeld full_solar. Dit leest de modus, het verandert de modus niet. Een '
                      'onbekende modus geeft geen onbeperkt overneembaar vermogen.',
 'stable_s': 'Hoe lang werkelijk restoverschot stabiel moet zijn voordat extra lasten naast de autonome '
             'laadpaal mogen starten. Langer is rustiger; korter kan reageren vóór vertraagde '
             'laadrapporten binnenkomen.',
 'cooldown_s': 'Rust na vermoede wisselwerking tussen laadpaal en eigen lasten. Vermindert herhaald '
               'vermogen afpakken en teruggeven. De autonome Wallbox-regeling blijft ondertussen '
               'eigenaar van het laden.',
 'drop_tolerance_w': 'Kleinste relevante verandering in laadvermogen voor de wisselwerkingsbewaking. '
                     'Kleine meetruis wordt niet als een echte reactie behandeld. Te groot kan een '
                     'werkelijke daling missen.',
 'handover_s': 'Uiterste termijn om een gecontroleerde vermogensovername van de Wallbox te bevestigen. '
               'Een cloudrapport kan later komen dan de fysieke reactie. Verleng dit niet om een '
               'niet-reagerende laadpaal toch goed te keuren.',
 'handover_confirm_s': 'Vereiste duur van bevestigde stabiele netmetingen tijdens een overname. Pas '
                       'daarna wordt een volgende verhoging toegelaten. Een serviceaanroep alleen is '
                       'geen bewijs.',
 'handover_import_w': 'Kleine tolerantie op netafname bij de bevestiging van een overdracht. Geen doel '
                      'om stroom van het net af te nemen. Een grotere waarde kan een mislukte '
                      'overdracht verhullen.',
 'reclaim_max_age_s': 'Maximale leeftijd van het Wallbox-rapport voordat een nieuwe gecontroleerde '
                      'overname mag beginnen. Oude laadgegevens mogen niet als actueel vrijmaakbaar '
                      'vermogen worden gebruikt.',
 'max_takeover_w': 'Maximale vermogenstap bij het overnemen van laadvermogen. Alleen de eigen last '
                   'wordt gestuurd. Werkelijke importgrens, exclusieve meting en terugmelding blijven '
                   'ook bij een kleine stap verplicht.',
 'priority_stable_s': 'Hoe lang genoeg vermogen vrijgemaakt kan worden voor het EV-minimum voordat '
                      'lagere eigen lasten wijken. Standaard 120 s. Een lopende compressor krijgt eerst '
                      'zijn minimumlooptijd.',
 'priority_release_s': 'Wachttijd voordat lagere lasten opnieuw stabiel restoverschot mogen gebruiken. '
                       'Houdt de regelingen uit elkaars vaarwater; is niet dezelfde tijd als de eigen '
                       'compressor-rusttijd.',
 'priority_hysteresis_w': 'Vermogensband tussen voorrang vasthouden en vrijgeven. Vermindert '
                          'heen-en-weer schakelen rond de laadgrens. Te groot reserveert onnodig lang '
                          'vermogen.',
 'priority_start_timeout_s': 'Maximale kans voor de Wallbox om na daadwerkelijk vrijgeven te starten. '
                             'Standaard 600 s. Wanneer de auto toch niet laadt, mogen lagere lasten '
                             'later opnieuw meedoen met hun normale rusttijden.',
 'priority_retry_s': 'Rust vóór een nieuwe voorrangspoging na een niet-bevestigde EV-start. Standaard '
                     '1800 s. Voorkomt dat de ontvochtiger telkens stopt voor een auto die geen lading '
                     'accepteert.',
 'dhw:enabled': 'Geeft SolarPilot toestemming om het ondersteunde boiler-temperatuurdoel te regelen. '
                'Het schakelt niet de hoofdvoeding, compressor of Force DHW. Globale modus, '
                'bronkwaliteit, handmatige bescherming en veiligheidsbevestiging blijven verplicht.',
 'dhw:power_entity': 'Alleen een actuele elektrische vermogensmeter voor sanitair warm water, inW/kW. '
                     'Geen totale warmtepompmeter inclusief ruimteverwarming, geen kWh-teller en geen '
                     'geschatte 3200 W. Zonder geschikte meter leeg laten; niets erbij verzinnen.',
 'target_entity': 'De fabrikantentiteit voor het tank-temperatuurdoel. Niet de ruimtethermostaat of een '
                  'PV-helper. SolarPilot vraagt een setpoint; Panasonic bepaalt zelf wanneer en hoe het '
                  'opwarmen begint.',
 'temperature_entity': 'Werkelijk gemeten watertemperatuur in de tank. Het ochtenddoel gebruikt deze '
                       'waarde, niet alleen het ingestelde doel. Sensorpositie, stratificatie en '
                       'waterafname beperken de zekerheid.',
 'cooling_entities': 'Alle relevante ruimtekoelzones. Echte of onzekere koeling verhindert extra hoge '
                     'tankopwarming. Een kort idle-signaal tijdens sanitairwaterproductie is niet '
                     'automatisch het einde van de koelvraag.',
 'hygiene_entity': 'Alleen een expliciete betrouwbare melding dat een fabrikant-hygiënecyclus actief '
                   'is. Force DHW of ontdooien is niet vanzelf een hygiënesignaal. Zonder zo’n bron '
                   'blijven het bevestigde fabrikantprogramma en beschermde tijdvenster essentieel.',
 'manual_entity': 'Oud enkelvoudig handmatig/beschermd signaal. De meervoudige lijst verdient de '
                  'voorkeur. Actief betekent dat SolarPilot het tankdoel met rust moet laten.',
 'manual_entities': 'Handmatige of krachtige functies die voorrang hebben, bijvoorbeeld Powerful en '
                    'Force DHW. SolarPilot leest deze signalen alleen en schakelt ze niet zelf. '
                    'Actieve/onbetrouwbare signalen verhinderen eigen doelwijzigingen.',
 'manual_active_states': 'Komma-gescheiden echte statuswaarden voor handmatige bescherming, '
                         'bijvoorbeeld on,on-30 m,on-60 m,on-90 m. Gebruik de ruwe HA-waarden, niet '
                         'alleen een vertaalde naam op het scherm.',
 'safety_confirmed': 'Bevestigt dat de gebruiker de fabrikantgeschiktheid, onafhankelijke hygiëne en '
                     'verbrandingsrisico-informatie voor deze installatie heeft beoordeeld. Nieuwe '
                     'installaties krijgen deze toestemming nooit vanzelf. Bij de beta.35→beta.36-migratie '
                     'wordt een reeds actief en exact bevestigd 50/46/-5/50/60/62-profiel als bestaande '
                     'gebruikerskeuze behouden, zodat dezelfde eerder aanvaarde situatie niet opnieuw '
                     'onnodig blokkeert. Fabrikantbeveiligingen blijven altijd leidend.',
 'minimum_c': 'Bewaakte gemeten comfortgrens, standaard 46 °C. Onderschrijding geeft een zichtbare '
              'waarschuwing en laat alleen het gewone doel beschikbaar. Geen tijdelijke verhoging naar '
              '52 °C, geen Force DHW. Met normaal 50 °C en differentie -5 °C kan de fabrikant rond 45 '
              '°C herstarten: 46 °C is niet gegarandeerd en is geen hygiënegrens.',
 'tank_differential_c': 'Werkelijk in het toestel ingestelde heropwarmdifferentie, bijvoorbeeld -5 °C. '
                        'Deze waarde wordt alleen gebruikt om de nominale herstartgrens en haalbaarheid '
                        'te tonen. SolarPilot verandert de fysieke instelling niet en compenseert haar '
                        'niet met een hoger setpoint. 50 °C plus -5 °C betekent nominaal herstarten '
                        'rond 45 °C.',
 'minimum_buffer_c': 'Verouderde instelling, uitsluitend bewaard om een ouder normaal doel éénmalig te '
                     'migreren. Vanaf beta.28 verandert dit veld geen doeltemperatuur en is het niet '
                     'meer instelbaar. Gebruik Normale boilerdoeltemperatuur en Bewaakte '
                     'comfortondergrens afzonderlijk.',
 'solar_c': 'Gewoon tankdoel bij voldoende actuele PV-productie, standaard 50 °C. Dit normale '
            'warmtepompcomfort heeft voorrang op autonoom autoladen. Het mag netstroom aanvullen; de '
            'productiedrempel is geen garantie op uitsluitend zon.',
 'surplus_c': 'Extra opportunistisch doel, standaard 60 °C. Alleen op werkelijk resterende injectie, '
              'buiten de nacht en zonder actieve/onzekere/voorspelde koelblokkering. Dit extra doel '
              'krijgt géén voorrang op de Wallbox. Het fabrikant-hygiëneprogramma is een andere '
              'functie.',
 'cooling_cap_c': 'Hoogste door SolarPilot gevraagde doel bij actieve of onzekere koeling, standaard 50 '
                  '°C. Begrenst ook een extra avondvoorraad. Fabrikantsterilisatie en handmatige '
                  'bescherming worden niet door dit plafond overschreven.',
 'pv_threshold_w': 'Minimale werkelijk gemeten zonnepanelenproductie voor het gewone zonnedoel. '
                   'Standaard 1000 W productie, niet 1000 W vrije injectie. Andere huislast en de '
                   'Wallbox kunnen dit vermogen al gebruiken; nettoestemming is daarom relevant.',
 'surplus_threshold_w': 'Werkelijke netto-injectie moet voor een nieuwe extra hoge fase strikt boven '
                        'deze drempel liggen, standaard 3500 W. EV-laadvermogen wordt hier nooit als '
                        'vrije injectie bijgeteld.',
 'estimated_heat_power_w': 'Conservatieve elektrische planningsinschatting voor een opwarmperiode, '
                           'standaard 3200 W. Geen echte meter. De avondstart gebruikt deze inschatting '
                           'plus marge; werkelijk eigen boilervermogen wordt er niet mee nagemaakt.',
 'night_enabled': 'Activeert het ingestelde nachtvenster. De oude variant houdt het gewone '
                  'minimumsetpoint aan en blokkeert alleen zonne-opslag. De nieuwe nachtkeuze beperkt '
                  'tot de minimumdrempel en kan na het venster blijven wachten op zon; ochtendcomfort '
                  'kan netstroom vragen.',
 'night_start': 'Vanaf dit lokale uur geldt nachtrust. Dit verlaagt zo nodig het toegestane setpoint, '
                'maar schakelt de warmtepomp niet stroomloos en koelt een warme tank niet actief af.',
 'night_end': 'Einde van het lokale nachtvenster. Geen automatische verwarmingsopdracht. In de nieuwe '
              'nachtkeuze blijft normale bijverwarming wachten op stabiele zon; minimumherstel en '
              'tijdig ochtendcomfort zijn uitzonderingen.',
 'night_policy': 'Beide nachtkeuzes laten het normale doel staan. Geen verlaging of automatische '
                 'verhoging aan het einde van de nacht. Wachten op stabiele zon laat na de nacht alleen '
                 'extra buffer toe zodra de zonnevoorwaarden kloppen. Panasonic mag op het gewone doel '
                 'ook met netstroom herverwarmen; dit is geen nachtelijke netstroomvergrendeling.',
 'morning_enabled': 'Bewaakt de verwachte voorraad tegen het gekozen uur. Bij een tekort mag alleen het '
                    'normale doel worden hersteld; geen extra ochtendboost of Force DHW. Panasonic '
                    'kiest het verwarmmoment, ook als de voorspelling ongunstig is. UIT schakelt deze '
                    'deadlinecontrole uit; de algemene comfortgrens blijft zichtbaar.',
 'morning_time': 'Lokaal uur voor de beoordeling van de ochtendvoorraad, standaard 09:00. SolarPilot '
                 'kijkt vooraf naar het geschatte verlies en de opwarmsnelheid. Dit veroorzaakt geen '
                 'vaste opwarmopdracht om 06:00 of om het deadline-uur.',
 'morning_c': 'Gewenste gemeten tanktemperatuur tegen het ochtenduur, standaard 46 °C. De effectief '
              'bewaakte waarde is nooit lager dan de algemene comfortgrens. Dit doel verandert het '
              'normale setpoint niet; als de fabrikantdodeband of waterafname het doel verhindert, '
              'verschijnt een waarschuwing in plaats van een geforceerde verhoging.',
 'morning_margin_c': 'Extra reserve in de voorspelling en berekening van de avondvoorraad, standaard 1 '
                     '°C. Geen optelling bij het normale setpoint voor netopwarming in de ochtend. Een '
                     'hogere marge kan de avondbuffer verhogen, maar nooit boven de ingestelde '
                     'avondlimiet.',
 'morning_max_lead_min': 'Hoe vroeg vóór de deadline de ochtendcontrole het normale setpoint mag '
                         'herstellen en een tekort mag melden. Standaard 180 minuten. Er wordt niet '
                         'naar een hoger ochtenddoel geschakeld; een langere controleperiode forceert '
                         'geen warmtevraag.',
 'morning_extra_lead_min': 'Extra tijd bij de geschatte opwarmduur voor de deadlinecontrole, standaard '
                           '30 minuten. Dit helpt een onhaalbaar doel tijdig te melden, maar is geen '
                           'commando voor Force DHW en geen garantie op een eerdere fabrikantstart.',
 'morning_hold_min': 'Hoe lang ná het ochtenduur het doel nog bewaakt wordt. Standaard 30 minuten; '
                     'daarna geen daglange verplichting om het ochtenddoel te herstellen.',
 'morning_cap_c': 'Verouderde ochtendboostlimiet. Vanaf beta.28 wordt dit veld niet meer gebruikt of '
                  'aangeboden: een ochtendtekort kan uitsluitend het gewone setpoint herstellen.',
 'tank_loss_fallback_c_h': 'Voorzichtige aanname voor temperatuurverlies per uur zolang onvoldoende '
                           'schone metingen bestaan. Standaard 0,25 °C/uur; geen gemeten feit. Na '
                           'minstens 6 bruikbare monsters op 3 dagen gebruikt het model een hoge '
                           'verlieskwantiel. Waterafname wordt zoveel mogelijk uitgesloten; '
                           'stratificatie blijft onzeker.',
 'tank_heat_fallback_c_h': 'Voorzichtige opwarmsnelheid voor terugrekenen vanaf het ochtenduur zolang '
                           'onvoldoende leerdata bestaan. Standaard 6 °C/uur; lager begint eerder, '
                           'hoger later. Na voldoende verschillende meetdagen wordt een trage geleerde '
                           'kwantiel gebruikt.',
 'evening_enabled': 'Vraagt maximaal één begrensde avondvoorraad per dag met de laatste bruikbare zon, '
                    'óók wanneer de afzonderlijke ochtendcontrole uit staat. Het doel komt uit '
                    'voorspeld nachtverlies en reserves, niet uit een verhoging om de '
                    'fabrikantthermostaat te forceren. Extra opwarming wacht standaard op vrij '
                    'ruimteklimaat en stabiele echte zonne-ruimte.',
 'evening_cap_c': 'Maximum voor het berekende avondsetpoint, standaard 55 °C. De voorraadberekening kan '
                  'bijvoorbeeld 51, 52 of 54 °C opleveren: alleen met werkelijke zon, nooit als '
                  'noodboost bij een te koude tank. Het eenmaal gekozen avonddoel kruipt niet omhoog. '
                  'Na het bereiken ervan begint die dag geen tweede avondbuffer. Een limiet kan te laag '
                  'zijn om de nacht te overbruggen; dat wordt gemeld.',
 'evening_lookahead_h': 'Hoeveel uur vóór het laatste verwachte bruikbare zonneblok avondvoorraad mag '
                        'beginnen, standaard 3 uur. Dat blok komt uit bestaande lokaal gecorrigeerde '
                        'PV-verwachting minus geschatte basislast, niet alleen astronomische '
                        'zonsondergang. Het blijft een schatting.',
 'evening_fallback_start': 'Vanaf dit lokale uur mag avondvoorraad geprobeerd worden als geen bruikbare '
                           'zonne-horizon beschikbaar is. Uitgangspunt 14:00. Ook dan blijft '
                           'daadwerkelijk beschikbaar zonnevermogen verplicht; de klok alleen geeft '
                           'geen start.',
 'evening_draw_buffer_c': 'Extra reserve voor watergebruik in avond/nacht, uitgedrukt als '
                          'temperatuurmarge. Standaard 2 °C is een instelbare aanname, geen geleerd '
                          'verbruiksprofiel. Een grote douche of bad kan veel meer warmte onttrekken.',
 'evening_margin_w': 'Extra werkelijke zonne-ruimte boven het geschatte boilervermogen vóór een nieuwe '
                     'avondstart. Standaard 150 W. De gewone avondvoorraad mag huidige autonome '
                     'EV-zonneconsumptie meenemen als vrijmaakbaar, maar nooit als extra elektrische '
                     'netcapaciteit.',
 'predictive_cooling_enabled': 'AAN gebruikt betrouwbare bestaande thermische profielen en '
                               'weersverwachting om extra hoge tankopwarming uit te stellen als binnen '
                               'de horizon waarschijnlijk koelvraag ontstaat. Dit stuurt geen '
                               'ruimteverwarming/koeling en kiest nooit HEAT/COOL. Bij te weinig '
                               'modeldata geldt alleen de gemeten koelbewaking.',
 'predictive_cooling_horizon_h': 'Hoe ver vooruit naar mogelijke koelvraag wordt gekeken, standaard 2 '
                                 'uur (voorzichtig afgerond op hele modeluren). Groter blokkeert '
                                 'mogelijk langer extra tankopwarming; kleiner ziet een komende '
                                 'koelvraag later.',
 'hygiene_schedule_enabled': 'Beschermt het bekende tijdvenster van het zelfstandige '
                             'Panasonic-hygiëneprogramma tegen SolarPilot-setpointopdrachten. AAN voert '
                             'zelf géén sterilisatie uit. Het echte programma moet onafhankelijk in het '
                             'toestel actief zijn.',
 'hygiene_weekdays': 'Dagen van de echte fabrikantcyclus als komma-gescheiden nummers: maandag 0 tot '
                     'zondag 6. Deze instelling beschermt die dagen; ze programmeert de warmtepomp '
                     'niet.',
 'hygiene_start': 'Werkelijke starttijd van het zelfstandige fabrikantprogramma. SolarPilot plant '
                  'daaromheen een geen-opdrachtenvenster. Controleer de apparaatklok en het werkelijk '
                  'voltooide programma.',
 'hygiene_target_c': 'Referentietemperatuur van het fabrikant-hygiëneprogramma, bijvoorbeeld 62 °C. '
                     'Geen SolarPilot-opdracht om die temperatuur te halen en geen bewijs dat de hele '
                     'tank is behandeld. De fabrikantcyclus gaat vóór energiebesparing en EV-laden.',
 'hygiene_guard_before_s': 'Geen SolarPilot-boileropdrachten in deze tijd vóór de fabrikantcyclus. '
                           'Standaard 900 s is 15 minuten. Een buffer helpt een net gestarte '
                           'zonneregeling uit de cyclus te houden.',
 'hygiene_guard_after_s': 'Beschermtijd gerekend vanaf de start van de fabrikantcyclus, niet vanaf het '
                          'einde. Standaard 10800 s is 3 uur. Een groter venster is conservatiever maar '
                          'geeft langer geen zonne-optimalisatie.',
 'rise_delay_s': 'Zolang moeten de zonnevoorwaarden geldig blijven vóór een nieuwe extra '
                 'setpointverhoging, advies 300 seconden. Een normale doelherstelling kan zonder deze '
                 'zonne-wachttijd; een lage tank of ochtenddeadline mag nooit de stabiliteit voor 55/60 '
                 '°C omzeilen. Dit is geen compressorlooptijd.',
 'fall_delay_s': 'Wachttijd bij gewoon minder zon vóór setpointverlaging, aanbevolen 300 s. Filtert '
                 'korte wolken, maar kan tijdelijk netstroom betekenen. Werkelijke netafname boven '
                 'de ingestelde grens omzeilt deze wachttijd. Nacht-, koel-, hygiëne- en '
                 'storingsgrenzen hebben hun eigen, snellere bescherming.',
 'pv_hysteresis_w': 'Terugvalband onder de PV-productiedrempel. Bij 1000 W startgrens en 100 W '
                    'hysterese kan een reeds toegelaten 50 °C-fase tot circa 900 W blijven bestaan. '
                    'Geen extra vermogen bij de echte meting.',
 'surplus_hysteresis_w': 'Terugvalband onder de echte injectiedrempel voor een lopende hoge fase. Bij '
                         '3500/300 W is de gewone terugvalgrens circa 3200 W. Netafname- en '
                         'koelbewaking blijven daarnaast gelden.',
 'cooling_clear_s': 'Hoelang geen echte/onzekere koeling meer mag zijn voordat extra hoge tankopwarming '
                    'weer kan. Aanbevolen 1800 s (30 minuten). Recente koeling die voor tankopwarming '
                    'idle wordt, wordt niet meteen als vrijgave gezien; na herstart blijft recent '
                    'bekende koeling beschermd.',
 'cooling_detection': 'Actie kijkt primair naar werkelijk cooling. Bij een geldige idle-actie blokkeert '
                      'alleen geselecteerde COOL niet permanent. Modus is strenger en blokkeert zolang '
                      'COOL gekozen is. Onzekere gegevens geven geen hoge temperatuurvrijgave; uitloop '
                      'blijft gelden.',
 'compensate_own_power': 'Tijdens een reeds eigen hoge fase mag een exclusieve actuele '
                         'boilervermogensmeter het door de boiler zelf gebruikte zonnevermogen '
                         'reconstrueren. Geen gedeelde warmtepomp-/net-/EV-meter gebruiken. Zonder '
                         'passende meter wordt niets bijgeteld; geschatte 3200 W is geen '
                         'compensatiemeting.',
 'max_surplus_import_w': 'Bij werkelijke netafname boven deze grens laat SolarPilot een door zichzelf '
                         'beheerd extra 60 °C-doel onmiddellijk los; de gewone terugvalvertraging geldt '
                         'dan niet. Standaard 100 W. Noodzakelijk ochtend- en minimumcomfort worden '
                         'apart beoordeeld. Dit is geen elektrische beveiliging.',
 'average_demand_entity': 'Bron voor het lopende kwartiergemiddelde van de volledige aansluiting. Niet '
                          'het actuele vermogen en niet een kWh-teller. Hiermee wordt het resterende '
                          'kwartierbudget geschat.',
 'monthly_peak_entity': 'Gemeten maandpiek als referentie voor piekplanning. Geen veilige elektrische '
                        'bovengrens. Een reeds hogere piek kan optioneel het doel aanpassen.',
 'target_peak_w': 'Gewenst kwartierpiekdoel inW. Lagere waarden beperken nieuwe pieken maar kunnen '
                  'flexibel werk uitstellen. De regeling kan onbeheerde lasten niet wegregelen en dit '
                  'is geen zekeringbeveiliging.',
 'adaptive_to_month_peak': 'AAN laat een reeds hogere gemeten maandpiek meewegen in het piekdoel. UIT '
                           'houdt het vaste doel aan. Dit verandert niet de fysieke netgrenzen.',
 'margin_w': 'Extra conservatieve ruimte onder het bijbehorende piek- of faseplafond. Hoger geeft '
             'minder ruimte voor nieuwe lasten; lager reageert dichter bij de grens.',
 'minimum_elapsed_s': 'Minimale verstreken tijd in het kwartier voordat een extrapolatie bruikbaar '
                      'wordt. Te vroeg is de berekening gevoelig voor een kort inschakelmoment.',
 'respect_optional_dhw': 'AAN laat optionele zonne-opwarming van de boiler wachten bij te weinig '
                         'kwartierpiekruimte. Noodzakelijk minimum-/ochtendcomfort en '
                         'fabrikantbescherming blijven belangrijker.',
 'respect_billing_floor': 'Laat de ingestelde facturatievloer meewegen als ondergrens voor zinvolle '
                          'kostenoptimalisatie. Dit is geen elektrische aansluitwaarde.',
 'billing_floor_w': 'Instelbare ondergrens voor de tariefberekening. Gebruik de toepasselijke '
                    'contractsituatie. Dit getal begrenst niet het totale toegestane fysieke vermogen.',
 'import_price_entity': 'Actueel afnametarief in geld per kWh. Gebruik een eigen betrouwbare '
                        'energieprijsbron, niet een kostentotaal. Bij dynamische prijzen wordt waar '
                        'beschikbaar de passende prijsreeks gebruikt.',
 'export_price_entity': 'Actuele vergoeding voor injectie per kWh. Geen hoeveelheid geëxporteerde '
                        'energie. Een negatieve waarde betekent dat terugleveren geld kan kosten.',
 'fixed_import_eur_kwh': 'Terugvalprijs per kWh netafname als geen geldige prijsbron bestaat. Gebruik '
                         'de gewenste variabele prijscomponenten consequent. Vaste kosten en '
                         'capaciteitstarief worden niet hierdoor automatisch toegevoegd.',
 'fixed_export_eur_kwh': 'Terugvalvergoeding per kWh injectie. Deze wordt van de geschatte '
                         'netafnamekost afgetrokken. Direct zonneverbruik wordt niet nóg een tweede '
                         'keer van die netto kost afgetrokken.',
 'current_hour_entity': 'Forecast-energie voor dit uur in kWh. Dit is een verwachting, geen actuele '
                        'vermogensmeting. De realtime netmeter blijft leidend voor echte starts.',
 'next_hour_entity': 'Verwachte zonne-energie voor het volgende uur in kWh. Alleen een planningsbron; '
                     'bewijst niet dat er straks werkelijk voldoende overschot is.',
 'remaining_today_entity': 'Nog verwachte zonne-energie voor vandaag, in kWh. Geen reeds geproduceerde '
                           'dagenergie kiezen. Wordt ook gebruikt voor de geschatte laatste bruikbare '
                           'zonneperiode.',
 'forecast_power_entity': 'Voorspeld zonnevermogen op dit moment inW/kW, om met werkelijk PV te '
                          'vergelijken. Niet de energie voor een heel uur. Structurele afwijkingen '
                          'worden gekoppeld aan de zonnestand.',
 'sun_entity': 'Zonnestandbron met azimut en elevatie. Daarmee worden schaduwpatronen geleerd op '
               'positie in plaats van uitsluitend kloktijd.',
 'seed_enabled': 'AAN gebruikt een lokaal aangeleverde historische bootstrap als voorzichtig '
                 'beginprofiel. Geen privédata wordt naar GitHub verzonden. Zonder bestand leert '
                 'SolarPilot live; een bootstrap is geen zekerheid.',
 'min_forecast_w': 'Onder dit voorspelde vermogen wordt geen verhouding voor het lokale PV-model '
                   'geleerd. Kleine waarden veroorzaken te veel ruis, vooral rond zonsopkomst en '
                   'zonsondergang.',
 'min_elevation_deg': 'Onder deze zonnehoogte leert het schaduwmodel niet. Zo domineren schemering en '
                      'zeer kleine vermogens niet de correctie.',
 'azimuth_bin_deg': 'Breedte van een vak in horizontale zonnestand. Kleine vakken zijn preciezer maar '
                    'verzamelen trager voldoende verschillende dagen; grotere vakken zijn grover en '
                    'leren sneller.',
 'elevation_bin_deg': 'Breedte van een vak in zonnehoogte. Gebruik niet overdreven kleine vakken zonder '
                      'voldoende seizoensdata; grotere vakken middelen meer situaties samen.',
 'min_days': 'Vereist aantal verschillende meetdagen voor het betreffende leerprofiel. Hoger is minder '
             'gevoelig voor één uitzonderlijke dag maar leert trager. Meer monsters van dezelfde dag '
             'vervangen die dagspreiding niet.',
 'min_confidence': 'Onder deze interne leerscore mag de lokale correctie niet als betrouwbare '
                   'plannerinput worden gebruikt. De score is geen gekalibreerde kans dat de '
                   'voorspelling klopt.',
 'shadow_factor': 'Verhoudingsdrempel tussen werkelijke en voorspelde productie voor schaduwhints. Een '
                  'afwijking kan ook bewolking zijn; terugkerende zonnestand en meerdere dagen zijn '
                  'nodig.',
 'shadow_drop': 'Benodigde daling van het lokale correctieprofiel om een schaduwperiode te markeren. '
                'Kleiner reageert sneller op variatie; groter vraagt duidelijker verschil.',
 'recovery_delta': 'Benodigde stijging van het correctieprofiel om herstel na schaduw te herkennen. '
                   'Helpt geplande starts uitstellen tot bruikbaar herstel, zonder daarmee actuele '
                   'metercontroles te vervangen.',
 'horizon_min': 'Aantal minuten dat het lokale zonne-/schaduwmodel vooruit projecteert. Verder vooruit '
                'geeft meer context maar ook meer onzekerheid.',
 'projection_step_min': 'Tijdstap van de zonneprojectie, in minuten. Kleinere stappen geven meer '
                        'rekenpunten, niet noodzakelijk nauwkeurigere onderliggende voorspellingen.',
 'limit_w': 'Softwareplafond per fase. Ook bij een meter die fasen optelt blijven de stroomgrenzen '
            'fysiek per fase gelden. Watt is een benadering van stroom bij de werkelijke spanning en '
            'arbeidsfactor.',
 'start_headroom_w': 'Minimaal vrije faseruimte voor nieuwe starts. Laat ruimte voor onverwachte '
                     'huislasten. Geen toestemming om de fysieke automaat te vervangen door software.',
 'control_starts': 'AAN laat fasebewaking nieuwe starts blokkeren bij onvoldoende ruimte. Alleen '
                   'inschakelen nadat meterrichting en aansluiting gecontroleerd zijn. UIT maakt de '
                   'fase-informatie adviserend.',
 'shed_on_overlimit': 'AAN mag SolarPilot bij geverifieerde fase-overschrijding eigen onderbreekbare '
                      'lasten afbouwen. Fabrikantbeveiligingen, beschermde programma’s en echte '
                      'automaten blijven leidend. Niet aanzetten zonder fasecontrole.',
 'learning_enabled': 'Activeert lokaal leren voor dit onderdeel. Leren gebruikt echte, bruikbare '
                     'waarnemingen en verleent nooit zelfstandig nieuwe bedieningsrechten.',
 'monitor_power_entities': 'Aanvullende afzonderlijke vermogensmeters om fase-attributie te leren '
                           'zonder deze toestellen te bedienen. Geen verzamellijst van PV, net en '
                           'virtuele dubbeltellers gebruiken.',
 'learning_min_delta_w': 'Minimale duidelijke vermogenssprong om faseherkenning te leren. Kleine '
                         'sprongen zijn moeilijk van gewone huisruis te onderscheiden.',
 'learning_settle_s': 'Wachttijd na een vermogenssprong om de bijbehorende fasemetingen te laten '
                      'volgen. Te kort koppelt verschillende meetmomenten; te lang kan andere '
                      'veranderingen meenemen.',
 'learning_max_window_s': 'Langste tijdsafstand voor een leerbare vermogensverandering. Daarbuiten '
                          'wordt de toewijzing te onzeker en verworpen.',
 'learning_min_samples': 'Minimaal aantal bruikbare waarnemingen voordat een geleerd profiel gebruikt '
                         'mag worden. Verlagen maakt sneller resultaten maar kan een toevallige relatie '
                         'overwaarderen.',
 'learning_min_confidence': 'Minimale interne score voor faseherkenning. Deze score is geen elektrische '
                            'veiligheidsgoedkeuring of statistische kans.',
 'use_learned_device_map': 'AAN gebruikt voldoende betrouwbaar geleerde fase-toewijzing ook bij '
                           'planning. UIT houdt leren adviserend. Onbekende of onbetrouwbare toewijzing '
                           'blijft conservatief.',
 'roundtrip_efficiency': 'Efficiëntie over de volledige laad- én ontlaadcyclus.0,80 betekent 20% totaal '
                         'batterij-/omvormerverlies:1 kWh geladen zonne-energie levert circa 0,8 kWh '
                         'terug. Niet 20% per richting; dat zou 36% totaalverlies geven.',
 'reserve_pct': 'Deel van de virtuele batterijcapaciteit dat als reserve niet beschikbaar is voor de '
                'what-if. Hoger geeft minder benutbare opslag. Dit stuurt geen echte batterij.',
 'capacities_kwh': 'Te vergelijken virtuele batterijcapaciteiten in kWh. Dit bepaalt hoeveel energie '
                   'opgeslagen kan worden, niet hoe snel. Scenario’s blijven technische schattingen.',
 'powers_kw': 'Te vergelijken laad-/ontlaadvermogens in kW. Vermogen begrenst hoe snel een virtuele '
              'batterij overschot opvangt of import vermindert; het is niet de opslagcapaciteit.',
 'capacity_kwh': 'Bruikbare energiecapaciteit van deze echte batterij. Gebruik de toepasselijke '
                 'bruikbare waarde, niet automatisch het commerciële bruto getal. BMS-grenzen blijven '
                 'onaangeraakt.',
 'soc_entity': 'Actuele laadtoestand van dit batterijprofiel in procent. Bij ontbrekende gegevens wordt '
               'niet blind fysiek geregeld.',
 'power_sign': 'Tekenafspraak van deze batterijvermogensmeter. Laden en ontladen moeten kloppen om '
               'eigenverbruik en terugmelding juist te interpreteren.',
 'min_soc_pct': 'Absolute softwarematige ondergrens voor deze batterij. Geen versoepeling van de '
                'fabrikant-BMS. Een hogere waarde geeft minder ontlaadbare energie.',
 'reserve_soc_pct': 'Gewenste batterijreserve boven de harde ondergrens. Wordt behouden bij gewone '
                    'energiesturing, met de gekozen strategie.',
 'max_soc_pct': 'Hoogste gewenste laadtoestand voor deze batterij. De eigen fabrikantgrens blijft '
                'leidend; SolarPilot kan geen hogere fysieke capaciteit creëren.',
 'max_charge_w': 'Maximaal aangevraagd laadvermogen voor dit batterijprofiel. Blijft beperkt door '
                 'beschikbare energie, netvoorwaarden en fabrikantmogelijkheden.',
 'max_discharge_w': 'Maximaal aangevraagd ontlaadvermogen voor dit batterijprofiel. Mag een echte '
                    'omvormer- of BMS-limiet niet overstijgen.',
 'control_kind': 'Alleen uitlezen verstuurt niets. Numeriek setpoint of scripts maakt fysieke regeling '
                 'mogelijk, maar pas met beide toestemmingen en exclusief eigenaarschap.',
 'exclusive_control_confirmed': 'Bevestigt dat niet tegelijk een andere externe regeling '
                                'batterijsetpoints schrijft. Alleen werkelijk aanvinken na controle; '
                                'gelijktijdige regelaars kunnen elkaar tegenwerken.',
 'number_sign': 'Tekenafspraak van het numerieke batterijcommando. Positief moet het bedoelde laden of '
                'ontladen zijn. Verkeerd teken kan het tegenovergestelde gedrag veroorzaken.',
 'charge_script': 'Bestaand script voor werkelijk laden van de batterij, met overeengekomen '
                  'vermogenvariabelen. Controleer de scriptinhoud en terugmelding; de naam bewijst de '
                  'werking niet.',
 'discharge_script': 'Bestaand script voor werkelijk ontladen van de batterij. Respecteer reserve, '
                     'exporttoestemming en fysieke terugmelding.',
 'idle_script': 'Bestaand script dat eigen batterijsetpoints veilig neutraliseert. Dit is niet vanzelf '
                'hetzelfde als de batterij stroomloos zetten.',
 'strategy': 'Strategie voor echte batterijen: adviserend, verbruikers eerst, piekbeperking of '
             'gecombineerd. Geen strategie omzeilt de expliciete bedieningstoestemmingen of '
             'veiligheidsgrenzen.',
 'grid_target_w': 'Gewenst netto netvermogen voor de batterijstrategie. Dit is geen toegestaan extra '
                  'huisverbruik en geen gegarandeerd resultaat bij trage terugmelding.',
 'charge_reserve_w': 'Vermogensbuffer die bij het laden van echte batterijen als reserve blijft. Hoger '
                     'voorkomt sneller import, maar benut minder kleine overschotten.',
 'discharge_reserve_w': 'Vermogensbuffer bij het berekenen van ontlaaddoelen. Helpt onbedoelde injectie '
                        'voorkomen; een te grote buffer laat meer netafname over.',
 'allow_grid_charge': 'AAN staat opladen van een echte batterij uit het net toe binnen de gekozen '
                      'strategie. UIT beperkt gewone laadopdrachten tot zonneoverschot. Dit is een '
                      'bewuste financiële keuze, geen standaard noodzaak.',
 'allow_export_discharge': 'AAN staat ontladen van een echte batterij richting het net toe. UIT houdt '
                           'ontlading gericht op eigen importvermindering. Controleer contract, '
                           'omvormer en veiligheidsvoorwaarden.',
 'command_min_interval_s': 'Minimale tijd tussen echte batterijopdrachten. Na een verse start zonder '
                           'vorige opdracht wordt niet fictief gewacht; na een verzonden opdracht '
                           'blijft de intervalbescherming gelden.',
 'target_tolerance_w': 'Toegestane afwijking tussen gemeten batterijvermogen en aangevraagd doel bij '
                       'bevestiging. Te groot kan een fout als succes behandelen; te klein kan meetruis '
                       'als fout zien.',
 'apply_now': 'Importeert bewust de lokaal aanwezige privéconfiguratie en historische bootstrap. '
              'Controleer wat vervangen wordt. De private bestanden horen nooit in de publieke '
              'GitHub-repository.',
 'early_grid_enabled': 'Globale toestemming voor goedkope netfallback van daarvoor individueel '
                       'vrijgegeven lasten. Beide niveaus moeten toestemming geven. De actuele net-, '
                       'comfort- en toestelvoorwaarden blijven leidend.',
 'cheap_grid_limit_eur_kwh': 'Hoogste afnameprijs waarbij goedkope netfallback mag gelden. Zonder '
                             'betrouwbare reeks blijft de gekozen vaste terugval belangrijk; dit is '
                             'geen voorspelling van je hele factuur.',
 'early_grid_requires_forecast_shortfall': 'AAN laat goedkope netfallback alleen toe wanneer de '
                                           'zonneverwachting waarschijnlijk onvoldoende is voor het '
                                           'resterende doel. UIT kan prijsoptimalisatie eerder '
                                           'netstroom kiezen.',
 'adaptive_power_guard': 'Gebruikt na voldoende exclusieve metingen een begrensd hoger P '
                         '90-vermogensprofiel voor conservatievere planning. Verlaagt niet blind de '
                         'ingestelde basiswaarde en herschrijft het handmatige veld niet.',
 'adaptive_power_min_samples': 'Aantal goede exclusieve vermogensmonsters vóór de planningsschatting '
                               'mag worden verhoogd. Geen reden om het initiële vermogen te laag in te '
                               'vullen.',
 'adaptive_power_max_multiplier': 'Bovengrens op de aangeleerde vermogensverhoging ten opzichte van de '
                                  'ingestelde nominale waarde. Dit is geen nieuwe veilige fysieke '
                                  'vermogenslimiet.',
 'normal_c': 'Het gewone tapwaterdoel, standaard 50 °C. Panasonic bepaalt zelf wanneer hij herverwarmt '
             'en hoe hij ruimteklimaat en tank verdeelt. De comfortgrens, ochtendplanning of '
             'tankdifferentie verhogen dit doel niet. Hoger slaat meer warmte op maar kost doorgaans '
             'meer energie; kies een fabrikantgeschikt profiel. 50 °C is geen bewijs van '
             'legionellabeheersing.',
 'optional_raise_interval_s': 'Rust tussen extra doelverhogingen boven het normale doel, standaard 1800 '
                              'seconden (30 minuten), gerekend vanaf de laatste verstuurde '
                              'doelopdracht. Lager reageert sneller; hoger vermindert doelwisselingen. '
                              'Verlaging wegens echt energietekort, koeling, nacht of pauze wordt niet '
                              'uitgesteld. Het gewone doel blijft beschikbaar. Geen gegarandeerde '
                              'compressor-aan/uit-tijd.',
 'respect_space_climate': 'AAN: een nieuwe extra zonnebuffer boven het normale doel wacht zolang een '
                          'gekoppelde klimaatbron werkelijk heating/cooling/preheating/defrosting meldt '
                          'of geen betrouwbare actie doorgeeft. Een geselecteerde HEAT-modus met idle '
                          'is niet hetzelfde als actieve verwarming. Een al aangevraagd hoger doel '
                          'wordt niet uitsluitend om een nieuwe verwarmactie afgebroken. UIT heft '
                          'alleen deze extra voorzichtigheid op, nooit koel-, hygiëne- of andere '
                          'bescherming.',
 'dhw:cooling_entities': 'Bestaande klimaatbronnen voor de woning. Hun actuele acties bewaken koeling '
                         'én stellen optionele zonne-opwarming uit bij bezige ruimteverwarming. '
                         'SolarPilot schrijft hier geen klimaatopdrachten. Een binaire koelhulp bewijst '
                         'alleen koeling, niet of de vloerverwarming vrij is; koppel echte '
                         'climate-acties voor de extra taakbewaking.'}

HELP_NOTES.update({'kind': 'Kies de werkelijk ondersteunde actuator. Het afzonderlijke '
         'AEG/Electrolux-afwasmachinetype stuurt uitsluitend een native START-knop, met een '
         'expliciete eenmalige klaarzettoestemming en echte startklaar-bronnen. Het gebruikt '
         'nooit de slimme stekker als start/stopregeling.',
 'start_button': 'De actuele START-knop van de afwasmachine-integratie. Kies nooit PAUSE, '
                 'RESUME, STOPRESET of een slimme stekker. Oude herstelde knoppen worden '
                 'geweigerd. Een nooit ingedrukte knop kan unknown tonen; live gereedmelding, '
                 'verbinding, deur en afstandstoestemming blijven afzonderlijk verplicht. Test '
                 'de juiste knop eerst bewust met een geladen en geschikte machine.',
 'dishwasher_state_entity': 'De echte cyclus-/programmastatus van dezelfde afwasmachine. Deze '
                            'beslist of het programma gereed, bezig of voltooid is. Drogen, '
                            'pauzeren en een automatisch geopende droogdeur zijn geen nieuwe '
                            'startkans. Vermogen nul of een verdwenen cloudverbinding is nooit '
                            'bewijs dat het programma klaar is.',
 'dishwasher_connection_entity': 'Actuele verbindingsstatus van hetzelfde '
                                 'AEG/Electrolux-apparaat. Offline, onbekend of een rapport '
                                 'ouder dan de ingestelde grens blokkeert een nieuwe start. '
                                 'Tijdens een lopende cyclus wordt niet blind gestopt bij '
                                 'ontbrekende verbinding.',
 'dishwasher_remote_entity': 'Expliciete toestand die START op afstand toestaat. Controleer dit '
                             'in de fabrikantapp en de ruwe HA-toestand. Not Safety Relevant '
                             'Enabled wordt niet standaard aanvaard: dat label bewijst geen '
                             'startrecht. Deze optie omzeilt nooit fysieke of '
                             'fabrikantbeveiligingen.',
 'dishwasher_door_entity': 'Echte deurstatus van de afwasmachine. Een HA-binary_sensor met device_class door meldt '
                           'normaal on bij open en off bij dicht; bevestig dit op jouw toestel. '
                           'Een deur die na klaarzetten opent, trekt de toestemming in. AirDry '
                           'tijdens een al lopende cyclus wordt niet onderbroken.',
 'dishwasher_connection:cycle_program_entity': 'Het reeds gekozen afwasprogramma, alleen '
                                               'uitlezen. SolarPilot kiest of wijzigt geen '
                                               'programma. De eenmalige toestemming is aan deze '
                                               'keuze gekoppeld; een gewijzigde keuze vraagt '
                                               'opnieuw klaarzetten. Het programma dient ook als '
                                               'sleutel voor gemeten cyclusprofielen.',
 'dishwasher_connection:power_entity': 'Optionele exclusieve W/kW-sensor van de afwasmachine, '
                                       'bijvoorbeeld een Shelly. Het relais van de plug wordt '
                                       'nooit bediend. Zonder meter gebruikt planning een '
                                       'duidelijk geschatte conservatieve last; het stageprofiel '
                                       'wordt niet uit totale woningafname verzonnen. Gedeelde '
                                       'net/PV/Wallbox/boilermeters zijn ongeschikt.',
 'dishwasher_alert_entity': 'Optionele alarmbron. Bij koppeling moet deze actueel zijn en een '
                            'expliciet geconfigureerde vrij-toestand hebben. De fabrikant blijft '
                            'eigenaar van lek-, deur- en apparaatbeveiliging. Een generieke '
                            'OFF-waarde is alleen bruikbaar als de werkelijke bronbetekenis '
                            'gecontroleerd is.',
 'dishwasher_delay_entity': 'Optionele oorspronkelijke uitgestelde-starttijd. Alleen een actuele '
                            'numerieke nul laat SolarPilot starten. Een ingestelde native '
                            'vertraging of onbekende waarde blokkeert de extra start, om twee '
                            'planners te voorkomen. SolarPilot wist de fabrikantvertraging niet '
                            'zelf.',
 'dishwasher_ready_states': 'Puntkomma-gescheiden ruwe toestanden waarin nog geen cyclus loopt '
                            'en een start mogelijk is, bijvoorbeeld Ready of Idle alleen na '
                            'verificatie. Dit blijft onvoldoende zonder de overige bronnen en '
                            'een eenmalige Klaarzetten-toestemming. Voltooid en bezig mogen niet '
                            'ook als gereed worden gebruikt.',
 'dishwasher_running_states': 'Ruwe toestanden die een bestaande cyclus voorstellen: wassen, '
                              'spoelen, drogen en een gepauzeerd programma. Deze blijven '
                              'beschermd en mogen niet opnieuw gestart of voor energietekort '
                              'afgebroken worden. Neem alle werkelijk voorkomende fasen op, niet '
                              'onbekend/unavailable.',
 'dishwasher_finished_states': 'Expliciete ruwe eindtoestanden die een voltooid programma '
                               'bevestigen. Alleen hiermee wordt een volledig gemeten profiel '
                               'afgerond. Nul watt, een open droogdeur of een verbroken '
                               'verbinding is geen einde. Na voltooiing is een nieuwe '
                               'klaarzettoestemming nodig.',
 'dishwasher_connected_states': 'Ruwe verbindingswaarden die aantoonbaar online betekenen, '
                                'puntkomma-gescheiden. Disconnected, unknown en unavailable '
                                'mogen niet als verbonden worden geconfigureerd.',
 'dishwasher_remote_states': 'Ruwe waarden waarbij START op afstand daadwerkelijk beschikbaar '
                             'is. De standaardwoorden zijn voorlopige voorbeelden. Voeg een '
                             'onduidelijke waarde niet toe om de blokkering te laten verdwijnen; '
                             'test de toestemming in de fabrikantapp. Ontbrekende toestemming '
                             'voorkomt nieuwe starts.',
 'dishwasher_closed_states': 'Ruwe toestanden voor gesloten deur. Gebruik bij een geverifieerde '
                             'standaard binaire deurbron off. Neem geen open/on-waarde op als '
                             'gesloten. Opnieuw openen na klaarzetten trekt de eenmalige '
                             'starttoestemming in.',
 'dishwasher_safe_states': 'Ruwe toestanden van de optionele alarmbron waarbij geen blokkerend '
                           'alarm geldt. Dit is geen vervanging voor lekbeveiliging en de '
                           'fabrikantinterlocks. Zonder gekoppelde alarmbron blijven die '
                           'fabrikantbeveiligingen leidend.',
 'dishwasher_stale_s': 'Maximum ouderdom van iedere benodigde AEG-statusbron in seconden, '
                       'standaard 300. Te oud blokkeert nieuwe starts. Neem een grens die past '
                       'bij aantoonbare rapportage, niet steeds langer om offline apparaten te '
                       'accepteren. last_reported toont HA-rapportage, niet gegarandeerd het '
                       'fysieke meetmoment.',
 'dishwasher_ticket_hours': 'Geldigheidsduur van één klaarzettoestemming, standaard 24 uur en '
                            'maximaal 48. Verlopen, gewijzigde programmakeuze of opnieuw '
                            'geopende deur vraagt opnieuw klaarzetten. De toestemming wordt vóór '
                            'START duurzaam verbruikt; geen eindeloze nieuwe afwasbeurten.',
 'dishwasher_mapping_confirmed': 'Bevestig pas nadat START-knop, alle statuswaarden, verbonden '
                                 'toestel en deur-/remote-startbetekenis werkelijk zijn '
                                 'gecontroleerd. Dit zet het toestel niet automatisch op Auto en '
                                 'maakt geen cyclus klaar. Geen algemene toestemming om een leeg '
                                 'of niet voorbereid apparaat te starten.',
 'analysis:enabled': 'Bewaart lokaal begrensde meetgegevens, beslisredenen en '
                     'SolarPilot-waarschuwingen voor analyse. AAN verstuurt niets naar ChatGPT '
                     'of een andere dienst en bedient geen apparaat. UIT stopt nieuwe '
                     'registratie; reeds bewaarde data verloopt volgens de bewaartermijn. Een '
                     'handmatige actuele export blijft mogelijk.',
 'include_related_entities': 'Neemt ondersteunde, niet-uitgeschakelde bronentiteiten van '
                             'dezelfde gekoppelde apparaten mee, zodat bijvoorbeeld andere '
                             'warmtepomptemperaturen kunnen worden onderzocht. Camera, persoon-, '
                             'tracker-, slot- en media-entiteiten worden niet meegenomen. Er '
                             'geldt een zichtbare limiet van 250 bronnen, expliciete bronnen '
                             'eerst.',
 'retention_days': 'Maximale ouderdom van gedetailleerde opgeslagen analysedata: één tot zeven '
                   'dagen. Vast maximum 2016 meetrondes, 20000 bronwijzigingen en 6000 '
                   'gebeurtenissen kan de periode verder beperken. De export vermeldt de '
                   'werkelijk aanwezige periode en hiaten. Bestaande andere leer-/dagaggregaten '
                   'kunnen oudere samenvattingen bevatten.',
 'analysis:sample_interval_s': 'Gedetailleerde momentopname iedere 300 seconden standaard, '
                               'instelbaar 60–900. Dit verandert het gewone regelritme niet. '
                               'Korter geeft meer analysepunten maar meer opslag en een kortere '
                               'periode door maximaal 2016 meetrondes. De laatste maximaal 1440 '
                               'regelcycli/twee uur zijn aanvullende RAM-details en verdwijnen '
                               'bij herstart.',
 'extra_entities': 'Maximaal 50 bestaande, relevante extra bronentiteiten voor een gericht '
                   'onderzoek. Geen camera’s, locatie, personen, sloten, credentials of '
                   'volledige HA-database. De uiteindelijke bronlimiet blijft 250 en de export '
                   'meldt afgekapt bereik. Voeg geen persoonlijke vrije tekst of secrets toe.',
 'analysis_export': 'Opent de handmatige analyse-export: laatste uur, 24 uur of zeven dagen. '
                    'Alleen een HA-beheerder kan het JSON-bestand maken. Namen zijn standaard '
                    'per bestand gepseudonimiseerd; tijden en gebruikspatronen blijven gevoelig. '
                    'Controleer het bestand voor delen en plaats het nooit in de publieke '
                    'repository. Uploaden naar ChatGPT doe je zelf.',
 'dishwasher_arm': 'Bevestigt dat één afwasbeurt geladen, gekozen en geschikt is voor externe '
                   'start. SolarPilot wacht vervolgens op de normale zonne-/planningsvoorwaarden '
                   'en actuele deur-, verbinding- en remote-startbronnen. Geen onmiddellijke '
                   'geforceerde start. Een begonnen cyclus mag netstroom gebruiken als zon later '
                   'wegvalt.',
 'dishwasher_cancel': 'Trekt uitsluitend een nog niet gebruikte klaarzettoestemming in. Een '
                      'lopende of al verstuurde onzekere cyclus wordt niet gestopt, gepauzeerd, '
                      'gereset of stroomloos gemaakt. Het afwasprogramma stopt of annuleer je '
                      'met de fabrikantbediening.'})

HELP_NOTES.update({
 'learning_hub': 'Opent Leren & vragen met de meetbasis per model, ontbrekende broninformatie, voorstellen en jouw eerdere antwoorden. Alleen een Home Assistant-beheerder kan de keuzes aanpassen. De getoonde zekerheid is een technische maat, geen kans dat elke voorspelling of opdracht klopt. Meer planberekeningen zijn geen extra onafhankelijke leerdagen.',
 'learning_hub:sampling': 'Gemeten restlast: leer ook wanneer de Wallbox of beheerde apparaten draaien, maar trek alleen hun actuele, aparte W/kW-meting af. Ontbrekende, geschatte, dubbele, niet-synchrone of pas geschakelde bronnen worden geweigerd. Alleen rustig: blijf die perioden overslaan. Dit raakt de gegevens voor voorspellingen, niet de echte beschikbare netruimte of de grenzen voor een start. Een meter moet de bedoelde fysieke last exclusief meten; twee unieke namen bewijzen dat niet.',
 'learning_hub:adaptation': 'Eerst mijn toestemming verzamelt en vergelijkt een recent 14-dagen-basislastprofiel zonder dat recente alternatief te gebruiken. Begrensd automatisch mag dat profiel per uur/dagtype toepassen na minstens vier onafhankelijke vergelijkingsdagen met eerdere dagen als training, minimaal tien procent en twintig watt minder gemiddelde fout. De afwijking van het gewone profiel is begrensd op plus of min 25 procent. Bij onvoldoende of verslechterd bewijs valt de voorspelling terug op het gewone profiel. Je normale bestaande live basislastmodel blijft ook in adviesstand leren; dit is geen stilzetten van alle modellen. Temperaturen, deadlines, vermogensgrenzen, prioriteiten en toestemmingen worden niet gewijzigd.',
 'learning_hub:notifications': 'Toon nieuwe leervragen ook onder Home Assistant-meldingen. Standaard uit; de vragen staan altijd in de SolarPilot-popup. Maximaal eenmaal per 24 uur wordt een afzonderlijke melding bijgewerkt bij een gewijzigde vragenlijst; dezelfde vraag wordt niet iedere regelcyclus herhaald. Dit is geen mobiele push en geen bericht vanuit ChatGPT. Later stelt dezelfde vraag een dag uit; een bewuste behoud-keuze blijft bewaard tot de relevante bronconfiguratie verandert.',
})

GROUP_NOTES = {
'wallbox':'Alleen bestaande Wallbox-terugmelding wordt gelezen; SolarPilot regelt de laadpaal niet rechtstreeks. Gewoon warmtepompcomfort gaat vóór de EV; de extra 60 °C-fase niet.',
'dhw':'Dit onderdeel vraagt uitsluitend ondersteunde tanksetpoints. Panasonic-compressorbeveiliging, zelfstandige hygiëne en gecontroleerde verbrandingsbeveiliging blijven nodig. Instellen is niet hetzelfde als fysieke bevestiging of reeds opgewarmd water.',
'phase':'De meter kan import en injectie over fasen verrekenen, maar iedere fase behoudt haar eigen fysieke stroomgrens. Software is geen elektrische beveiliging.',
'battery':'Een simulatie is geen echte batterijbesturing. Echte regeling vereist passende bronnen, terugmelding, globale en individuele toestemming en exclusief extern eigenaarschap.',
'local_pv':'Forecast en leren zijn onzeker en geven nooit toestemming om actuele P1/PV, comfort of toestelbeveiligingen te negeren.',
'dishwasher':'Een gestart afwasprogramma blijft beschermd: geen stop/pauze/reset of stroomonderbreking voor energiesturing. Begin met gecontroleerde bronwaarden en één geschikte geladen afwasbeurt.',
'analysis':'Dit is een lokale diagnosefunctie, geen automatische upload of bewijs van een volledige foutvrije installatie. Perioden zonder metingen blijven onbekend.',
'device':'Toestelvoorwaarden, fysieke terugmelding, minimumtijden en beschermde programma’s gaan vóór energie-optimalisatie. Een ingeschakelde stekker bewijst niet dat een compressor continu draait.',
'limits':'Toestelvoorwaarden, fysieke terugmelding, minimumtijden en beschermde programma’s gaan vóór energie-optimalisatie.',
'connection':'Kies echte bestaande bronnen en test de betekenis. Gedeelde meters, virtuele dubbeltellers of een niet-terugmeldend script zijn geen betrouwbare vervanging.',
'capacity':'Pieksturing is een schatting voor kosten en planning, geen zekeringbeveiliging. Onbeheerde lasten en noodzakelijk comfort kunnen het doel overschrijden.',
'economy':'De dagkost is netafnamekost minus injectievergoeding. Direct zonneverbruik verlaagt de import al en wordt niet dubbel afgetrokken. Ontbrekende meetdekking blijft zichtbaar.',
'forecast':'Alleen voorspellingen. Werkelijk PV, netmeting en toestelvoorwaarden blijven leidend bij de echte uitvoering.',
'power':'Vermogensinstellingen zijn softwarematige planningsgrenzen. Ze verhogen nooit de echte capaciteit van de aansluiting.',
}

HELP_NOTES.update({'dishwasher_phase_entity': 'Aanvullende oorspronkelijke Cycle phase-sensor van dezelfde machine. Toont '
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
 'dishwasher_start_deadline': 'Uiterste starttijd op de geplande dag, standaard 13:00 volgens de Home '
                              'Assistant-tijdzone. Tot dat tijdstip geldt de stabiele zonnevoorwaarde. '
                              'Daarna mag met afzonderlijke nettoestemming gestart worden zonder vijf extra '
                              'minuten zonnevertraging. Het is een START-deadline, niet een tijdstip waarop '
                              'alles klaar moet zijn. Deur, verbinding, autorisatie, softwarelimieten en '
                              'Automatisch regelen blijven verplicht; storingen kunnen een start verhinderen.',
 'dishwasher_after_deadline': 'Wat gebeurt er als je een nieuwe APP-belading op of na de uiterste starttijd '
                              'klaarzet? Standaard Volgende dag: vandaag niet meer automatisch starten, '
                              'morgen eerst zon en uiterlijk morgen 13:00 met eventuele netstroom. Het gaat '
                              'om de volgende kalenderdag, niet onbeperkt wachten tot er ooit een zonnige '
                              'dag is. Zelfde dag is een bewuste alternatieve keuze: bij een late belading '
                              'vervalt de zonnevoorwaarde direct indien nettoestemming aanstaat. Een '
                              'geplande dag wordt vastgelegd en schuift niet iedere ochtend opnieuw op.',
 'dishwasher_deadline_grid_allowed': 'AAN: op de vastgelegde startdeadline mag netstroom de ontbrekende zon '
                                     'aanvullen. Dit is nodig voor uiterlijk beginnen op een bewolkte dag. '
                                     'UIT: ook na de deadline is voldoende werkelijk overschot nodig; een '
                                     'gemiste deadline wordt gemeld. De toestemming geeft geen hogere '
                                     'elektrische limieten en omzeilt geen deur-, fout-, bron- of '
                                     'remote-controle. Een actieve wasbeurt wordt in beide standen niet '
                                     'onderbroken wanneer later de zon wegvalt.',
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
 'dishwasher_ticket_hours': 'Geldigheidsduur voor een handmatig in SolarPilot klaargezette beurt. In '
                            'APP-modus geldt in plaats hiervan de vastgelegde geplande dag met startdeadline '
                            'en herstelvenster; zo kan een belading na 13:00 ook de volgende dag tot de '
                            'afgesproken deadline blijven wachten.',
 'dishwasher_state_entity': 'Oorspronkelijke Appliance state van de AEG/Electrolux-machine, niet de '
                            'afgeleide helper Afwasmachine actief. Ready To Start betekent gereed; Running '
                            'bevestigt een echte start. End Of Cycle wordt onmiddellijk bij de '
                            'statuswijziging vastgelegd en blijft bewaard na Off of Disconnected. Cycle '
                            'phase is een afzonderlijke aanvullende bron voor voorwas/drogen. Alleen Off of '
                            'een verbroken verbinding bewijst geen succesvolle afronding.'})

HELP_NOTES.update({
    'dishwasher_priority_enabled': 'Standaard AAN voor de gevraagde voorkeursvolgorde. Gewoon sanitair water, benodigde avondvoorraad en vloerverwarming blijven vóór de afwasmachine. Daarna krijgt de afwasmachine voorrang op de Wallbox, lagere automatische verbruikers zoals de ontvochtiger, en de extra 60 °C-zonnebuffer. Het prioriteitsgetal bepaalt alleen de volgorde binnen dezelfde groep. Kleine restjes mogen naar een lagere last zolang de afwasmachine nog niet past. Minimumlooptijden, handmatig overgenomen toestellen en een reeds begonnen afwas blijven beschermd. De warmtepomp wordt niet uitgezet en niet met Force DHW of 52 °C geforceerd. UIT herstelt de gewone numerieke/per-Wallbox rangorde; het stopt geen cyclus.',
    'dishwasher_ev_solar_priority': 'Standaard AAN voor deze update. Bij actuele bevestigde Full Solar, werkelijk gemeten zonneproductie en stabiele net-/Wallboxmetingen mag de ene afwasbeurt beginnen met zonnevermogen dat de auto nu verbruikt. SolarPilot verstuurt geen Wallbox-opdracht: de laadpaal moet zelf terugregelen. Voor het starten moet de afwasmachine volledig binnen de actuele net-, kwartierpiek- en fasegrenzen passen ALSOF de laadpaal nog niets terugregelt. EV-vermogen is nooit extra elektrische capaciteit. Tijdelijke netafname tijdens de reactie en latere netstroom bij bewolking zijn mogelijk. Omdat afwassen niet mag worden afgebroken, is dit GEEN terugneembare stekkerovername. Na 15 minuten zonder bevestigde netto balans volgt een melding en worden volgende starts op EV-vermogen geblokkeerd tot Herstart- en foutcontrole; de lopende beurt blijft afwerken. Zonder Shelly is de meter van het hele huis een balanscontrole, geen exact gemeten faseprofiel. UIT: vóór de deadline alleen werkelijk resterende injectie; de 13:00-nettoestemming blijft apart.',
})

HELP_NOTES.update({'pv_forecast:enabled': 'Gebruikt de al aanwezige Forecast.Solar-gegevens voor voorspellingen. '
                        'Standaard AAN als er een bruikbare bron wordt gevonden; een eerder expliciet '
                        'uitgeschakelde forecast wordt bij migratie niet ingeschakeld. Er worden geen '
                        'extra cloudoproepen gedaan. Zonder bron blijven net-/PV-meters, comfort en '
                        'deadlines werken; ontbrekende voorspellingen worden als onbekend gemeld.',
 'pv_forecast:auto_discover': 'Zoekt via het Home Assistant-register naar één ingeschakelde '
                              'Forecast.Solar-installatie, ongeacht aangepaste entiteitsnamen. Meerdere '
                              'installaties worden niet opgeteld of willekeurig gekozen: kies dan de '
                              'configuratie-ID uit PV-diagnose of koppel expliciet. Bestaande '
                              'expliciete bronkeuzes blijven behouden.',
 'pv_forecast:calibration_enabled': 'Vergelijkt werkelijk PV-vermogen met de ruwe forecast in volledige '
                                    'kwartieren. Pas na voldoende verschillende rustige dagen wordt een '
                                    'geleidelijk veranderende factor toegepast. Opstart, clipping, '
                                    'slechte dekking en snelle wolken worden niet als structurele '
                                    'schaduw geleerd. UIT houdt opgeslagen gegevens maar gebruikt '
                                    'factor 1. De actuele vermogensregeling wordt hierdoor niet '
                                    'herschreven.',
 'pv_forecast:shadow_enabled': 'AAN gebruikt grove zonne-azimut/elevatievakken met tweemaandelijkse '
                               'seizoensgroepen; zonder zonnepositie een kwartier/tijdvak. UIT gebruikt '
                               'alleen de globale kalibratie. Er is geen vaste schaduwfactor vanaf '
                               '16:00. Een geleerde terugkerende afwijking kan ook een andere oorzaak '
                               'hebben dan schaduw.',
 'pv_forecast:show_raw': 'Toont de originele vermogenscurve naast de lokaal gecorrigeerde curve. Ruwe '
                         'curvewaarden kunnen lineair tussen Forecast.Solar-tijdstempels geïnterpoleerd '
                         'zijn; de native nu-sensor kan trapsgewijs afwijken. PV-diagnose en de export '
                         'blijven beide bronnen tonen. Deze keuze verandert geen regeling.',
 'pv_forecast:learning_preset': 'Normaal vraagt minstens vijf verschillende vergelijkbare dagen en '
                                'verandert de factor maximaal 0,05 per dag. Rustig vraagt minstens '
                                'zeven dagen en maximaal 0,025; Vlotter minimaal vijf en maximaal '
                                '0,075. De factor blijft tussen 0,35 en 1,25, met correctie alleen bij '
                                'voldoende consistent bewijs. Dit is geen garantie op '
                                'voorspelnauwkeurigheid.',
 'pv_forecast:forecast_entry_id': 'Leeg laten bij precies één gevonden Forecast.Solar-configuratie. Bij '
                                  'meerdere bronnen staat de ID in de PV-diagnose bij gevonden bronnen. '
                                  'Kies één bron die dezelfde PV-installatie vertegenwoordigt als de '
                                  'actuele meter. Dit is geen entiteits-ID en geen API-key. Verander '
                                  'nooit coördinaten of API-keys in dit veld.',
 'pv_forecast:panel_peak_wp': 'Som van het nominale DC-piekvermogen van de panelen in wattpiek. Dit is '
                              'niet hetzelfde als de AC-omvormerlimiet. Voor het opgegeven profiel '
                              '13.800 Wp; maximaal AC blijft 10.000 W. SolarPilot wijzigt de '
                              'Forecast.Solar-configuratie hiermee niet: controleer beide instellingen.',
 'pv_forecast:inverter_limit_w': 'Maximaal bruikbaar AC-vermogen van de omvormer, voor het opgegeven '
                                 'profiel 10.000 W. Vanaf 98% van deze grens worden kwartieren niet als '
                                 'schaduw geleerd. Waarden boven 110% worden als onbetrouwbaar '
                                 'gemarkeerd. Gecorrigeerde voorspelling wordt hierop begrensd. Het is '
                                 'geen fysieke omvormersturing.',
 'pv_forecast:tilt_deg': 'Opgegeven hellingshoek van de panelen ten opzichte van horizontaal. Voor het '
                         'opgegeven profiel 25°. Dit is beschrijvende installatie-informatie; '
                         'SolarPilot wijzigt Forecast.Solar niet. Bij een gewijzigde installatie worden '
                         'geen incompatibele live correctiefactoren hergebruikt.',
 'pv_forecast:azimuth_deg': 'Paneelrichting in conventie noord=0°, oost=90°, zuid=180°, west=270°. Voor '
                            'het opgegeven profiel 180°. Dit is niet de dynamische zonne-azimut voor '
                            'het leren; die wordt uit lokale zonnegegevens bepaald. Geen automatisch '
                            'wijzigen van de Forecast.Solar-bron.',
 'pv_forecast:minimum_days': 'Minstens vijf verschillende dagen per vergelijkbaar zonnestand/tijdvak '
                             'voordat een factor wordt gebruikt. Hoger vraagt meer geduld maar meer '
                             'onafhankelijke waarnemingen. De rustige preset vraagt minstens zeven '
                             'dagen. Honderd metingen op dezelfde dag tellen niet als honderd '
                             'leerdagen.',
 'pv_forecast:history_days': 'Bewaart maximaal 30 dagen kwartierdiagnose met '
                             'ruwe/gecorrigeerde/werkelijke waarden en acceptatie- of afwijsreden, '
                             'begrensd op 2880 regels. Het compacte leerprofiel bewaart maximaal 45 '
                             'recente vergelijkbare dagen per vak, met evidence maximaal 120 dagen oud. '
                             'Dit is geen volledige Recorder-back-up.',
 'pv_forecast:stale_s': 'Ouderdomsgrens voor de forecast, niet voor de actuele PV-/netmeter. Standaard '
                        'twee uur, passend bij een uurlijkse bron. De ongewijzigde coordinatorcache '
                        'wordt niet fris gemaakt door hem opnieuw te lezen. Bij uitval blijven echte '
                        'meters leidend; onbekende uren worden niet door fictieve productie gevuld.',
 'pv_forecast:now_entity': 'Een echte ruwe forecastbron, niet de gemeten productie of een al door '
                           'SolarPilot gecorrigeerde sensor. Vermogen in W of kW; kW wordt éénmaal met '
                           '1000 vermenigvuldigd. Leeg laten voor eenduidige registerdetectie. Zonder '
                           'volledige forecasttijdreeks wordt een energietotaal niet verzonnen over '
                           'uren verdeeld en wordt een dagfactor niet blind op morgen toegepast.',
 'pv_forecast:next_hour_power_entity': 'Een echte ruwe forecastbron, niet de gemeten productie of een '
                                       'al door SolarPilot gecorrigeerde sensor. Vermogen in W of kW; '
                                       'kW wordt éénmaal met 1000 vermenigvuldigd. Leeg laten voor '
                                       'eenduidige registerdetectie. Zonder volledige forecasttijdreeks '
                                       'wordt een energietotaal niet verzonnen over uren verdeeld en '
                                       'wordt een dagfactor niet blind op morgen toegepast.',
 'pv_forecast:remaining_entity': 'Een echte ruwe forecastbron, niet de gemeten productie of een al door '
                                 'SolarPilot gecorrigeerde sensor. Energie in Wh of kWh; Wh wordt '
                                 'éénmaal door 1000 gedeeld. Leeg laten voor eenduidige '
                                 'registerdetectie. Zonder volledige forecasttijdreeks wordt een '
                                 'energietotaal niet verzonnen over uren verdeeld en wordt een '
                                 'dagfactor niet blind op morgen toegepast.',
 'pv_forecast:today_entity': 'Een echte ruwe forecastbron, niet de gemeten productie of een al door '
                             'SolarPilot gecorrigeerde sensor. Energie in Wh of kWh; Wh wordt éénmaal '
                             'door 1000 gedeeld. Leeg laten voor eenduidige registerdetectie. Zonder '
                             'volledige forecasttijdreeks wordt een energietotaal niet verzonnen over '
                             'uren verdeeld en wordt een dagfactor niet blind op morgen toegepast.',
 'pv_forecast:tomorrow_entity': 'Een echte ruwe forecastbron, niet de gemeten productie of een al door '
                                'SolarPilot gecorrigeerde sensor. Energie in Wh of kWh; Wh wordt '
                                'éénmaal door 1000 gedeeld. Leeg laten voor eenduidige '
                                'registerdetectie. Zonder volledige forecasttijdreeks wordt een '
                                'energietotaal niet verzonnen over uren verdeeld en wordt een dagfactor '
                                'niet blind op morgen toegepast.',
 'pv_forecast:current_hour_entity': 'Een echte ruwe forecastbron, niet de gemeten productie of een al '
                                    'door SolarPilot gecorrigeerde sensor. Energie in Wh of kWh; Wh '
                                    'wordt éénmaal door 1000 gedeeld. Leeg laten voor eenduidige '
                                    'registerdetectie. Zonder volledige forecasttijdreeks wordt een '
                                    'energietotaal niet verzonnen over uren verdeeld en wordt een '
                                    'dagfactor niet blind op morgen toegepast.',
 'pv_forecast:next_hour_entity': 'Een echte ruwe forecastbron, niet de gemeten productie of een al door '
                                 'SolarPilot gecorrigeerde sensor. Energie in Wh of kWh; Wh wordt '
                                 'éénmaal door 1000 gedeeld. Leeg laten voor eenduidige '
                                 'registerdetectie. Zonder volledige forecasttijdreeks wordt een '
                                 'energietotaal niet verzonnen over uren verdeeld en wordt een '
                                 'dagfactor niet blind op morgen toegepast.',
 'session_mode_entity': 'Bron die de werkelijk actieve sessie onderscheidt: zonne-auto, manueel of '
                        'gestopt. De ingestelde Full Solar-optie kan bij manueel starten aan blijven; '
                        'daarom is alleen die instelling standaard onvoldoende om EV-vermogen over te '
                        'nemen. Gebruik een actueel, gecontroleerd statusveld. Een dashboardhelper die '
                        'alleen netimport naar manueel vertaalt is onvoldoende. Bij een ontbrekende, te '
                        'oude of strijdige bron geen EV-overname; werkelijk restoverschot blijft '
                        'bruikbaar.',
 'trust_solar_setting': 'Deze terugvalkeuze staat standaard UIT. Alleen AAN na bewust bevestigen dat de configuratie de '
                        'effectieve sessie betrouwbaar weergeeft of dat er geen '
                        'manuele/plannings-overrides zijn. Anders kan netstroom ten onrechte als '
                        'vrijmaakbare zon worden gezien. Bij een expliciet gekoppelde sessiebron blijft '
                        'een onbekende of manuele toestand blokkerend, ook wanneer deze terugvaloptie '
                        'aanstaat.',
 'manual_suspend_extra_dhw': 'Standaard AAN: tijdens een actieve of onzekere autolaadvraag geen extra '
                             '60 °C-zonnebuffer. Een door SolarPilot beheerd hoog doel kan na de '
                             'terugvaltijd naar het gewone doel gaan, voor het afgesproken profiel 50 '
                             '°C. Gewoon sanitair water, benodigde avondvoorraad en ruimtecomfort '
                             'blijven onder hun eigen regels werken. Sterilisatie, Powerful en Force '
                             'DHW worden nooit verlaagd. Een aantoonbaar niet-aangesloten/voltooide '
                             'auto blokkeert niet onnodig. UIT laat de extra buffer weer toe bij '
                             'werkelijk resterend overschot, nooit door manueel EV-vermogen erbij te '
                             'tellen.',
 'session_solar_states': 'Volledige waarden, gescheiden door puntkomma. Alleen exact matchen, '
                         'hoofdletters worden genegeerd. Daarnaast moet de oorspronkelijke '
                         'zonnelaadinstelling Full Solar melden. Geen substring-match en geen onbekende '
                         'modecode raden.',
 'session_manual_states': 'Volledige waarden die werkelijk manueel of niet-zongeregeld laden betekenen. '
                          'Deze herkenning wint altijd van een Full Solar-instelling; het laadvermogen '
                          'is niet vrijmaakbaar. Geen maximumstroom, pauze of hervatopdracht wordt naar '
                          'de laadpaal gestuurd.',
 'session_stopped_states': 'Volledige waarden die een gestopte sessie aanduiden. SolarPilot rekent '
                           'alleen met echte injectie. Een nulvermogen alleen bewijst niet dat de '
                           'sessie gestopt is; de lader kan op zon wachten.',
 'wallbox_power_policy': 'De centrale lijst scheidt rangorde van toestemming. Een toestel kan '
                         'hoger dan Auto laden staan, lager staan maar toch veilig terugregelen mogen, '
                         'of uitsluitend werkelijk vrij zonneoverschot gebruiken. Terugnemen vereist een '
                         'bevestigde zonnelaadsessie, een eigen actuele vermogensmeter en alle bestaande '
                         'minimumlooptijd-, terugmeld-, fase-, net- en importgrenzen. Bij manueel, gestopt '
                         'of onbekend laden is er nooit EV-credit. Beschermde cycli gebruiken hun eigen '
                         'specifieke route.',
 'mode_entity': 'Oorspronkelijke instelling van de zonnelaadmodus. Die kan Full Solar blijven tonen '
                'tijdens een manuele override. Koppel daarom ook de effectieve laadsessie. Deze bron '
                'wordt alleen uitgelezen; geen laadmoduswijzigingen vanuit SolarPilot.',
 'allow_wallbox_reclaim': 'De gewone bediening toont één uitkomstkeuze bij Mag de auto minder laden?. '
                          'De positie alleen geeft geen vermogen vrij. '
                          'Zonder toestemming telt uitsluitend werkelijk vrij zonneoverschot. AEG '
                          'gebruikt zijn aparte beschermde route.'})

HELP_NOTES.update({'appliance_type': 'Dit is de herkenbare categorie: afwasmachine, wasmachine, droogkast of andere '
                   'verbruiker. Ze staat los van het bedieningstype en verleent geen nieuwe '
                   'fysieke rechten. Een AEG-afwasmachine gebruikt de gecontroleerde start-only '
                   'koppeling; voor andere merken of toestellen moeten een bestaande adapter of '
                   'echte scripts met terugmelding eerst gecontroleerd worden. Een '
                   'categoriewijziging neemt geen gemeten toestelvermogen aan.',
 'apply_changes:confirm': 'Controleer het overzicht vóór bevestigen. Gewone wijzigingen worden '
                          'zonder volledige herlading toegepast. Actieve toestelbronnen en '
                          'bescherming blijven bevroren tot het toestel vrij is. Annuleren bewaart '
                          'de bestaande werking. De bevestiging start of stopt niets; pas de '
                          'volgende normale regelbeslissing kan op basis van nieuwe effectieve '
                          'regels een opdracht geven.',
 'request_scope': 'Alleen volgende beurten behoudt de al opgeslagen dag, deadline en '
                  'nettoestemming van de huidige APP-aanvraag. Ook huidige beurt verandert '
                  'deadline en nettoestemming op dezelfde geplande kalenderdag, zonder een nieuwe '
                  'toestemming te maken. Een deadline die daardoor al voorbij is kan bij de '
                  'volgende regelcyclus tot starten leiden, maar alleen met alle normale apparaat- '
                  'en elektrische controles. Een al begonnen beurt wordt nooit opnieuw gestart.',
 'pending_changes:cancel': 'Selecteer opgeslagen voorstellen die je niet meer wilt toepassen. '
                           'Alleen die voorstellen worden verwijderd; de huidige werkende regels '
                           'blijven staan en geen apparaat wordt uitgezet. Een voorstel kan '
                           'bijvoorbeeld wachten op het einde van een wasbeurt, een bevestigde '
                           'stop of de uitkomst van een al verzonden opdracht. Onbekend is niet '
                           'hetzelfde als uit.',
 'confirm_replace:confirm': 'Bevestigt dat je een vervangend toestelprofiel wilt opbouwen. De '
                            'wizard begint met lege fysieke koppelingen en een nieuw ID; '
                            'controleer het voorgestelde vermogen en de start-/stopvoorwaarden '
                            'opnieuw. De oude historiek blijft apart. Oude APP-vrijgave, '
                            'automatische deelname en geleerd verbruik worden nooit automatisch '
                            'aan het nieuwe apparaat toegekend.',
 'manage_device:device_id': 'Kies het afzonderlijke SolarPilot-profiel dat je wilt bekijken of '
                            'wijzigen. Dit is niet het verwijderen of veranderen van de '
                            'oorspronkelijke merkintegratie. De huidige cyclus blijft gekoppeld '
                            'aan zijn bestaande bronnen; gevoelige wijzigingen kunnen na opslaan '
                            'wachten tot die cyclus is afgerond.',
 'manage_device:section': 'Instellingen opent de basis en bescherming; Koppelingen opent de '
                          'oorspronkelijke actuator en terugmelding; Planning opent de energie- en '
                          'prioriteitskeuzes. Je doorloopt de resterende wizard en bevestigt aan '
                          'het einde. Bekijken is altijd mogelijk terwijl Automatisch regelen actief is en doet op '
                          'zichzelf niets met toestellen.',
 'replace:device_id': 'Selecteer alleen het oude SolarPilot-toestel dat vervangen wordt. De '
                      'opvolger krijgt een nieuw ID zodat oude metingen of een oude '
                      'starttoestemming niet voor de nieuwe machine worden gebruikt. Bij een '
                      'lopende of onzekere cyclus wachten archiveren en toevoegen op veilige '
                      'vrijgave; de overige regeling loopt door.',
 'dashboard:manage_devices': 'Toestellen beheren toont actieve profielen, wachtende wijzigingen en '
                             'archieven. Toevoegen, koppelen, plannen en vervangen gebeurt via '
                             'dezelfde gecontroleerde Home Assistant-wizard. Andere apparaten '
                             'blijven actief; er is geen algemene pauze nodig om dit venster te '
                             'openen. Een nieuw of opnieuw gekoppeld profiel begint Uitgesloten.'})

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


# Central priority editor is authoritative only after an explicit saved change.
HELP_NOTES.update({
    "priority": "De rangorde staat op Voorrang → Voorrang instellen. Minimumtijden, passende vermogensruimte en bescherming blijven altijd gelden.",
    "others_first": "De volgorde tussen toestellen en de auto staat samen op Voorrang. De centrale lijst toont direct welke regel eerst komt.",
    "wallbox_precedence": "Bekijk en wijzig de gezamenlijke rangorde op Voorrang. De plaats boven of onder Auto laden bepaalt de relatieve volgorde.",
    "wallbox_energy_choice": "Kies één duidelijke uitkomst: de auto mag binnen de veiligheidsgrenzen minder laden, alleen vrij zonneoverschot telt, of de strengere route voor een kort en gemeten toestel geldt.",
    "wallbox_power_policy": "Op Voorrang kies je per verbruiker of de auto minder mag laden. Een toestel moet ook aan alle meet-, sessie- en veiligheidsvoorwaarden voldoen.",
    "dishwasher_priority_enabled": "Het bestaande AEG-voorkeursprofiel blijft behouden. Gewoon warmtepompcomfort gaat voor; de standaard afwasvolgorde is vóór de Wallbox en extra boilerwarmte. Na een bevestigde centrale wijziging bepaalt de lijst Voorrang de toestelvolgorde. De afwas blijft vóór de extra zonnebuffer en een lopende beurt wordt nooit afgebroken. Het oude groepsgetal is dan niet meer leidend.",
    "analysis_export": "Open Export → Export samenstellen voor één lokaal JSON-onderzoeksbestand. Kies 1 uur, 24 uur of 7 dagen. Instellingen, centrale voorrang, metingen, modellen en bewaarde beslissingen worden meegenomen voor zover aanwezig. Namen worden standaard gepseudonimiseerd; controleer altijd vóór delen. Geen automatische upload, geen toestelopdracht en geen herstelbare Home Assistant-back-up.",
    "priority_board": "Alle regels staan onder elkaar. Beschermde regels staan vast; apparaten, Auto laden en extra warm water zijn binnen de veilige grenzen verplaatsbaar. Per regel staat ‘Mag de auto minder laden?’. Dat is nooit een garantie dat er nu vermogen beschikbaar is. Opslaan vraagt bevestiging en stuurt op zichzelf geen toestel."
})
