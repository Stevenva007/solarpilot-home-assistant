# SolarPilot beta.79 — codeaudit en herstel

Versie: **1.0.0-beta.79** · 12 oktober 2026

Alle 79 productie-Pythonmodules, beide frontendmodules, hun koppeling met configuratie/API/opslag en de releaseketen zijn nagekeken. De audit gebruikte bronlezing, afzonderlijke regressies voor aangetoonde fouten en een tweede beoordeling van de gewijzigde paden. Dit is geen formeel bewijs dat alle mogelijke fouten afwezig zijn. Testresultaten en CI-grenzen staan in [TESTRESULTATEN_BETA79.md](TESTRESULTATEN_BETA79.md); de volledige werking staat in [ACTUELE_WERKING.md](ACTUELE_WERKING.md).

## Herstelde fouten

| Onderdeel | Aangetoonde fout en herstel | Bewijs |
|---|---|---|
| Opdrachtverzending | Opslagawait kon modus, bronnen, deelname, voorrang of elektrische ruimte wijzigen. Gewone starts, AEG-zonnestarts en batterijdoelen controleren de actuele toestemming opnieuw vóór verzending; bij een reeds verzonden deelopdracht blijft onzekerheid bewaard. | `test_audit_dispatch79.py`, `test_audit_planner79.py`, `test_audit_battery_physical79.py` |
| Batterij-importgrenzen | Laden of minder ontladen kon de bestaande fase-/net-/kwartiergrens overschrijden ondanks voldoende totale injectie. Actuele grenzen en nog niet gemeten eigen reserves worden vóór en na opslag getoetst; onbekende faseverdeling krijgt geen fictieve spreiding. De bestaande importpolicy en neutrale vrijgave blijven gelden; er is geen nieuwe absolute exportgrens of fysieke zekeringsgarantie. | `test_audit_battery_physical79.py` |
| Ontvochtiger/startbudget | Een zonnepot vóór toewijzing werd als beschikbaar toestelvermogen getoond; een tekort door reserve/filter/voorrang/elektrische ruimte werd als ontbrekende vrije zon benoemd. De uitleg toont nu de actuele starttoewijzing en afzonderlijke beperkingen. Een reeds apart gereserveerde toekomstige afwaspiek telt bij toestel- en batterijdispatch één keer. De bestaande beschermde cyclusbuffer blijft gelden. | `test_audit_dispatch79.py`, `test_audit_battery_physical79.py`, `test_audit_ui79.py`, `check_audit_ui79.py` |
| Gereserveerde apparaten | Gewone, batterij- of geneste scripts konden gekoppelde Wallbox-/AEG-uitgangen bedienen. De centrale grens beschermt ook geregistreerde apparaatuitgangen; uitsluitend de exact gekoppelde native AEG-START heeft haar eigen actuele, duurzaam vastgelegde toestemming. | `test_audit_native79.py`, `test_audit_dispatch79.py` |
| SG-eigenaarschap | Een handmatige contact-/timerwijziging tijdens netwerkcontrole kon worden overschreven. Verse eigendomscontrole beschermt de handmatige stand. Eerste onleesbare herstartstatus kan later de bestaande vrijgave afronden zonder oude AAN te herhalen. | `test_audit_native79.py` |
| Onzekere SG-opdracht | Taakannulering na mogelijk toegepaste AAN/vernieuwing omzeilde foutafhandeling en kon een volgende AAN toelaten. Annulering volgt nu de bestaande onzekerheidsafhandeling en veilige vrijgave, daarna blijft de taak geannuleerd. Geannuleerde UIT finaliseert de bestaande onzekerheid, rusttijd en sessieafsluiting; later echt UIT-bewijs behoudt de normale herstelregel. Een onbekende timer of numerieke overloop wordt geen bewijs van handmatige overname. | `test_audit_native79.py` |
| APP-deadline | Een expliciete wijziging naar vóór de bestaande vrijgave maakte een onmogelijk tijdvenster. Een nog geldige aanvraag wordt op dezelfde vastgelegde dag meteen opeisbaar; alle aanvragen worden vóór mutatie gevalideerd. | `test_audit_dispatch79.py` |
| Afwastoestemming | Misvormde toestemmingsopslag kon startup laten crashen. De oorspronkelijke opslag blijft exact behouden, nieuwe afwasaanvragen/START blijven geblokkeerd, andere geldige functies kunnen verder. Review maakt geen nieuwe toestemming. Een opgeslagen future-Running-rapport kan geen huidige START bevestigen; extreme APP-tijden laten startup niet crashen. | `test_audit_dispatch79.py` |
| Planning | Verschillende slotgrenzen konden een cyclus buiten haar venster plannen; prijsoptout en nettoestemming waren niet overal consistent. Beide planners gebruiken volledige slots, bestaande rechten en dezelfde al toegewezen hogere lasten. | `test_audit_planner79.py` |
| Leren en boekhouding | Een ander bronprofiel kon nog vermogen beïnvloeden, onvolledige cycli/fasemetingen konden bewijs worden en beheerde zonne-energie kon beschikbare PV overstijgen. Herkomst, meetdekking en energiebalans zijn aangescherpt; geldige eerdere modellen blijven behouden. | `test_audit_planner79.py` |
| Numerieke SG-opties | Validatie accepteerde geldige numerieke tekst, terwijl runtime en prioriteiten die soms als tekst vergeleken of formatteerden. Alleen de los gekopieerde effectieve waarde wordt naar hetzelfde getal genormaliseerd; originele opties, ongeldige waarden, grenzen en rechten blijven behouden. | `test_audit_native79.py` |
| Opslagherstel | Onbekende kosten-/PV-/besparings-/advies-/warmtepompmodellen konden bij een volgende save worden vervangen. Onbekende snapshots blijven exact privé bewaard en geven geen bekende modelrechten. Beschadigde optionele velden laten geldige buurrecords intact. Onleesbare historie/analyse/feedback wordt niet automatisch overschreven. | `test_audit_storage79.py`, `test_audit_planner79.py` |
| Sluiten en herladen | Uitgestelde consumer-/analysesaves en callbacks konden na sluiten oude gegevens schrijven. Timers/listeners worden opgeruimd vóór afsluiten; alleen de gevraagde laatste save blijft toegestaan. | `test_audit_storage79.py` |
| Historische toegang | Herkoppeling verwijderde oorspronkelijke bronrechten uit geschiedeniscontrole. Historische en huidige bronnen worden samen getoetst; oude historie zonder complete herkomst blijft voor beheerder toegankelijk. Privé herkomstmetadata verlaat de gewone API niet. | `test_audit_storage79.py`, `test_audit_api_config79.py` |
| Configuratie en API | Getoonde lege optionele velden werden na validatie soms teruggezet; verborgen planneroptout kon verloren gaan. Validatie en opgeslagen vorm zijn nu gelijk. API-mutaties controleren na lock/opslag opnieuw de actuele runtime. Publieke diagnostiek lekt geen geneste private apparaatlabels. | `test_audit_api_config79.py`, `check_audit_config_schema79.py` |
| Weergave | Lege/boolean/niet-eindige waarden werden nul of oneindige uren; P1/PV/Wallbox bleef zonder HA-update vers lijken. De kaart bewaart de oorspronkelijke rapporttijd, laat oud bewijs vervallen en houdt open details/concepten intact. | `test_audit_ui79.py`, `check_audit_ui79.py` |
| Popup-lifecycle | Oude aanvragen konden nieuw geopende instellingen overschrijven of ontgrendelen; een oude close-gebeurtenis kon een heropende popup sluiten. Releasegebonden constructors en sessiecontrole voorkomen deze races. | `test_audit_ui79.py`, `check_audit_ui79.py` |
| Publicatietools | Repositoryconfiguratie sneed latere README-inhoud weg; PowerShell kon na een mislukte privacy-/uitleggate doorgaan en uploadsuccess melden. Alleen gegenereerde HACS-regels worden vervangen; native fouten stoppen publicatie en een afwijkende origin wordt geweigerd. | `test_audit_tooling79.py`, `check_audit_publisher79.ps1` |

## Behouden grenzen

Geen nieuwe add-on, solver of dependency voor de gebruiker. Panasonic blijft uitleesbaar met uitsluitend het gekoppelde SG-contact als schrijfroute. Wallbox blijft uitsluitend uitleesbaar. AEG blijft één native START per geldige vrijgegeven belading, zonder STOP, programmawijziging of stekkeronderbreking. Een APP-deadline gebruikt zo nodig netstroom onafhankelijk van zonneoverschot; actuele elektrische grenzen en fabrikantvoorwaarden blijven gelden. Een codeaudit kan de fysieke start bij een defecte/cloud-onbereikbare machine of onvoldoende elektrische ruimte niet afdwingen.

Geldige instellingen, prioriteiten, bronkoppelingen, historie en modellen blijven behouden. Onbekende opslag is geen bewijs van herstel en wordt niet gewist om de regeling groen te maken. Herstel van een onleesbaar afwasjournaal vraagt geldige private opslag; nooit een oude onverbruikte aanvraag herstellen nadat die belading fysiek al gestart is.

## Dekking van de productiecode

### Regelaar, lifecycle en afwasmachine (12)

`__init__.py`, `runtime.py`, `engine.py`, `live_options.py`, `live_config.py`, `consumer_wallbox.py`, `house_first.py`, `dishwasher.py`, `dishwasher_app.py`, `dishwasher_priority.py`, `dishwasher_recovery.py`, `priority_board.py`.

### Planning, energie en modellen (18)

`battery_analysis.py`, `battery_fleet.py`, `battery_plan.py`, `battery_runtime.py`, `cycle_learning.py`, `electricity_cost.py`, `ems.py`, `historical.py`, `joint_optimizer.py`, `learning.py`, `phase_learning.py`, `planner_quality.py`, `pv_calibration.py`, `pv_forecast.py`, `pv_forecast_source.py`, `pv_model.py`, `savings.py`, `unified_planner.py`.

### Opslag, analyse en geschiedenis (12)

`action_notifications.py`, `analysis_export.py`, `analysis_review.py`, `feedback_store.py`, `consumer_history.py`, `consumer_history_runtime.py`, `heatpump_history.py`, `heatpump_history_runtime.py`, `heatpump_learning.py`, `investigation.py`, `learning_hub.py`, `sg_investigation.py`.

### Native bronnen, SG en Wallbox (12)

`heatpump_budget.py`, `native_program.py`, `panasonic_authority.py`, `panasonic_monitor.py`, `power_activity.py`, `sg_boost.py`, `sg_config.py`, `sg_transport.py`, `wallbox.py`, `wallbox_activity.py`, `wallbox_policy.py`, `wallbox_profile.py`.

### API, configuratie en HA-platforms (22)

`analysis_api.py`, `analysis_implementations.py`, `binary_sensor.py`, `button.py`, `config_flow.py`, `const.py`, `diagnostics.py`, `dishwasher_config.py`, `entity.py`, `first_install.py`, `heatpump_history_api.py`, `learning_api.py`, `number.py`, `panasonic_migration.py`, `platforms.py`, `priority_api.py`, `private_bundle.py`, `pv_forecast_api.py`, `select.py`, `sensor.py`, `switch.py`, `consumer_history_api.py`.

### Frontendregistratie en uitleg (3)

`frontend.py`, `option_help.py`, `current_guide.py`.

Daarnaast volledig beoordeeld: `frontend/solar-pilot-card.js`, `frontend/option-help.js`, de gegenereerde hulp en actuele uitleg, `manifest.json`, `services.yaml`, releaseworkflow, README-/publicatietools en privacy-/handoff-/bronpakketcontroles. Python-/JSON-syntax en bestaande vertaal-/configuratieconsistentie worden door de volledige suite en repositorygates getoetst. Test- en previewtools leveren fictieve gegevens; er zijn geen huisexporten of werkelijke apparaatopdrachten aan de publieke bron toegevoegd.

## Grenzen van het bewijs

De audit vond en herstelde concrete softwarefouten. Lokale unitproeven gebruiken HA-doubles; de aparte CI start echte Home Assistant Core en een echte Chromium-browser. Ook die tests bewijzen geen juiste bedrading, native cloudwerking, Shelly-firmware, volledige productiebronkwaliteit of werkelijk opgenomen SG-zonne-energie. Er is geen live woning bediend of als hardwareproef gebruikt. Niet-aangetoonde externe foutoorzaken worden niet als opgelost voorgesteld.
