# Testmapping: Panasonic alleen-lezen en SG-zonneboost

Deze mapping is gebaseerd op de gepubliceerde beta.61-bron. Ze verklaart welke afspraken behouden blijven en welke tests door de bewust verwijderde warmtepompsturing worden vervangen. Het historische aantal geslaagde beta.61-tests is geen streefgetal voor de nieuwe release. Deze tabel is geen testresultaat en bewijst geen fysieke Shelly-/Panasonic-proef.

| Classificatie | Betekenis |
|---|---|
| Behouden | Bestaande afspraak blijft gelden; zo nodig verandert alleen de fixture of monitorpresentatie. |
| Vervangen | Verwijderde bediening wordt vervangen door SG-, migratie- of alleen-lezen monitoringtests. |
| Vervallen | Uitsluitend tests van bewust verwijderde tankdoel-/klimaatregels; geen reden om die controller actief te houden. |
| Behouden + vervangen | Een gemengd bestand: behoud generieke afspraken en vervang uitsluitend de oude warmtepompwriter-contracten. |

## Mapping per bestaand testbestand

`Testfuncties` telt definities in de bron, niet alle door parametrisatie gegenereerde uitvoeringen.

| Bestand | Testfuncties | Classificatie | Contract |
|---|---:|---|---|
| `test_action_notifications61.py` | 29 | Behouden + vervangen | Behoud generieke historie, bronactualiteit, foutisolatie, UI/cache, veilige levenscyclus en bestaande apparaatbevoegdheid; vervang actieve DHW-/klimaatregels door SG/monitor/migratie. |
| `test_active_value_runtime.py` | 10 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_activity_dashboard57.py` | 10 | Behouden + vervangen | Behoud generieke historie, bronactualiteit, foutisolatie, UI/cache, veilige levenscyclus en bestaande apparaatbevoegdheid; vervang actieve DHW-/klimaatregels door SG/monitor/migratie. |
| `test_allocation_diagnostics.py` | 12 | Behouden + vervangen | Behoud generieke historie, bronactualiteit, foutisolatie, UI/cache, veilige levenscyclus en bestaande apparaatbevoegdheid; vervang actieve DHW-/klimaatregels door SG/monitor/migratie. |
| `test_analysis_api.py` | 7 | Behouden + vervangen | Behoud generieke historie, bronactualiteit, foutisolatie, UI/cache, veilige levenscyclus en bestaande apparaatbevoegdheid; vervang actieve DHW-/klimaatregels door SG/monitor/migratie. |
| `test_analysis_download56.py` | 18 | Behouden + vervangen | Behoud algemene afspraken; vervang alleen oude DHW-/klimaatfixture en betrokken writer-contract. |
| `test_analysis_export.py` | 32 | Behouden + vervangen | Behoud generieke historie, bronactualiteit, foutisolatie, UI/cache, veilige levenscyclus en bestaande apparaatbevoegdheid; vervang actieve DHW-/klimaatregels door SG/monitor/migratie. |
| `test_analysis_mapping52.py` | 6 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_automatic_climate_model54.py` | 29 | Vervallen | Eigen tankdoelfasen, temperatuur-ACK, klimaat-AUTO/OFF, comfort/coast-model en hun herstelwrites zijn bewust verwijderd; relevante bron- en migratiebescherming wordt afzonderlijk vervangen. |
| `test_automatic_climate_runtime54.py` | 36 | Vervallen | Eigen tankdoelfasen, temperatuur-ACK, klimaat-AUTO/OFF, comfort/coast-model en hun herstelwrites zijn bewust verwijderd; relevante bron- en migratiebescherming wordt afzonderlijk vervangen. |
| `test_battery_analysis.py` | 6 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_battery_feedback49.py` | 8 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_battery_fleet.py` | 8 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_battery_runtime.py` | 5 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_battery_serialization48.py` | 5 | Behouden + vervangen | Behoud algemene afspraken; vervang alleen oude DHW-/klimaatfixture en betrokken writer-contract. |
| `test_battery_sources49.py` | 22 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_beta21_regressions.py` | 2 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_beta37_activation.py` | 3 | Behouden + vervangen | Behoud generieke historie, bronactualiteit, foutisolatie, UI/cache, veilige levenscyclus en bestaande apparaatbevoegdheid; vervang actieve DHW-/klimaatregels door SG/monitor/migratie. |
| `test_climate_dashboard54.py` | 24 | Vervallen | Eigen tankdoelfasen, temperatuur-ACK, klimaat-AUTO/OFF, comfort/coast-model en hun herstelwrites zijn bewust verwijderd; relevante bron- en migratiebescherming wordt afzonderlijk vervangen. |
| `test_climate_diagnostics56.py` | 27 | Vervallen | Eigen tankdoelfasen, temperatuur-ACK, klimaat-AUTO/OFF, comfort/coast-model en hun herstelwrites zijn bewust verwijderd; relevante bron- en migratiebescherming wordt afzonderlijk vervangen. |
| `test_climate_integration54.py` | 19 | Vervallen | Eigen tankdoelfasen, temperatuur-ACK, klimaat-AUTO/OFF, comfort/coast-model en hun herstelwrites zijn bewust verwijderd; relevante bron- en migratiebescherming wordt afzonderlijk vervangen. |
| `test_climate_journal_restore48.py` | 5 | Vervallen | Eigen tankdoelfasen, temperatuur-ACK, klimaat-AUTO/OFF, comfort/coast-model en hun herstelwrites zijn bewust verwijderd; relevante bron- en migratiebescherming wordt afzonderlijk vervangen. |
| `test_climate_serialization48.py` | 11 | Vervallen | Eigen tankdoelfasen, temperatuur-ACK, klimaat-AUTO/OFF, comfort/coast-model en hun herstelwrites zijn bewust verwijderd; relevante bron- en migratiebescherming wordt afzonderlijk vervangen. |
| `test_climate_service54.py` | 6 | Vervallen | Eigen tankdoelfasen, temperatuur-ACK, klimaat-AUTO/OFF, comfort/coast-model en hun herstelwrites zijn bewust verwijderd; relevante bron- en migratiebescherming wordt afzonderlijk vervangen. |
| `test_climate_solar57.py` | 19 | Vervallen | Eigen tankdoelfasen, temperatuur-ACK, klimaat-AUTO/OFF, comfort/coast-model en hun herstelwrites zijn bewust verwijderd; relevante bron- en migratiebescherming wordt afzonderlijk vervangen. |
| `test_climate_ui48.py` | 13 | Vervallen | Eigen tankdoelfasen, temperatuur-ACK, klimaat-AUTO/OFF, comfort/coast-model en hun herstelwrites zijn bewust verwijderd; relevante bron- en migratiebescherming wordt afzonderlijk vervangen. |
| `test_command_arbitration49.py` | 7 | Behouden + vervangen | Behoud generieke historie, bronactualiteit, foutisolatie, UI/cache, veilige levenscyclus en bestaande apparaatbevoegdheid; vervang actieve DHW-/klimaatregels door SG/monitor/migratie. |
| `test_consumer_engine_beta48.py` | 2 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_consumer_history.py` | 27 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_consumer_history_api.py` | 8 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_consumer_history_runtime.py` | 10 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_consumer_source_audit_beta48.py` | 11 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_consumer_wallbox.py` | 25 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_current_guide.py` | 5 | Behouden + vervangen | Behoud generieke historie, bronactualiteit, foutisolatie, UI/cache, veilige levenscyclus en bestaande apparaatbevoegdheid; vervang actieve DHW-/klimaatregels door SG/monitor/migratie. |
| `test_cycle_learning.py` | 3 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_decision_dashboard56.py` | 11 | Behouden + vervangen | Behoud generieke historie, bronactualiteit, foutisolatie, UI/cache, veilige levenscyclus en bestaande apparaatbevoegdheid; vervang actieve DHW-/klimaatregels door SG/monitor/migratie. |
| `test_dhw.py` | 30 | Vervallen | Eigen tankdoelfasen, temperatuur-ACK, klimaat-AUTO/OFF, comfort/coast-model en hun herstelwrites zijn bewust verwijderd; relevante bron- en migratiebescherming wordt afzonderlijk vervangen. |
| `test_dhw_auto_recovery61.py` | 20 | Vervallen | Eigen tankdoelfasen, temperatuur-ACK, klimaat-AUTO/OFF, comfort/coast-model en hun herstelwrites zijn bewust verwijderd; relevante bron- en migratiebescherming wordt afzonderlijk vervangen. |
| `test_dhw_comfort27.py` | 29 | Vervallen | Eigen tankdoelfasen, temperatuur-ACK, klimaat-AUTO/OFF, comfort/coast-model en hun herstelwrites zijn bewust verwijderd; relevante bron- en migratiebescherming wordt afzonderlijk vervangen. |
| `test_dhw_diagnostics_beta56.py` | 15 | Vervallen | Eigen tankdoelfasen, temperatuur-ACK, klimaat-AUTO/OFF, comfort/coast-model en hun herstelwrites zijn bewust verwijderd; relevante bron- en migratiebescherming wordt afzonderlijk vervangen. |
| `test_dhw_dispatch57.py` | 16 | Vervallen | Eigen tankdoelfasen, temperatuur-ACK, klimaat-AUTO/OFF, comfort/coast-model en hun herstelwrites zijn bewust verwijderd; relevante bron- en migratiebescherming wordt afzonderlijk vervangen. |
| `test_dhw_failure61.py` | 15 | Vervallen | Eigen tankdoelfasen, temperatuur-ACK, klimaat-AUTO/OFF, comfort/coast-model en hun herstelwrites zijn bewust verwijderd; relevante bron- en migratiebescherming wordt afzonderlijk vervangen. |
| `test_dhw_failure_history61.py` | 2 | Vervallen | Eigen tankdoelfasen, temperatuur-ACK, klimaat-AUTO/OFF, comfort/coast-model en hun herstelwrites zijn bewust verwijderd; relevante bron- en migratiebescherming wordt afzonderlijk vervangen. |
| `test_dhw_forecast59.py` | 2 | Vervallen | Eigen tankdoelfasen, temperatuur-ACK, klimaat-AUTO/OFF, comfort/coast-model en hun herstelwrites zijn bewust verwijderd; relevante bron- en migratiebescherming wordt afzonderlijk vervangen. |
| `test_dhw_gentle28.py` | 28 | Vervallen | Eigen tankdoelfasen, temperatuur-ACK, klimaat-AUTO/OFF, comfort/coast-model en hun herstelwrites zijn bewust verwijderd; relevante bron- en migratiebescherming wordt afzonderlijk vervangen. |
| `test_dhw_panasonic_ack.py` | 9 | Vervallen | Eigen tankdoelfasen, temperatuur-ACK, klimaat-AUTO/OFF, comfort/coast-model en hun herstelwrites zijn bewust verwijderd; relevante bron- en migratiebescherming wordt afzonderlijk vervangen. |
| `test_dhw_recovery61.py` | 6 | Vervallen | Eigen tankdoelfasen, temperatuur-ACK, klimaat-AUTO/OFF, comfort/coast-model en hun herstelwrites zijn bewust verwijderd; relevante bron- en migratiebescherming wordt afzonderlijk vervangen. |
| `test_dhw_recovery_barrier61.py` | 6 | Vervallen | Eigen tankdoelfasen, temperatuur-ACK, klimaat-AUTO/OFF, comfort/coast-model en hun herstelwrites zijn bewust verwijderd; relevante bron- en migratiebescherming wordt afzonderlijk vervangen. |
| `test_dhw_recovery_ui61.py` | 17 | Vervallen | Eigen tankdoelfasen, temperatuur-ACK, klimaat-AUTO/OFF, comfort/coast-model en hun herstelwrites zijn bewust verwijderd; relevante bron- en migratiebescherming wordt afzonderlijk vervangen. |
| `test_dhw_reports48.py` | 8 | Vervallen | Eigen tankdoelfasen, temperatuur-ACK, klimaat-AUTO/OFF, comfort/coast-model en hun herstelwrites zijn bewust verwijderd; relevante bron- en migratiebescherming wordt afzonderlijk vervangen. |
| `test_dhw_restart47.py` | 14 | Vervallen | Eigen tankdoelfasen, temperatuur-ACK, klimaat-AUTO/OFF, comfort/coast-model en hun herstelwrites zijn bewust verwijderd; relevante bron- en migratiebescherming wordt afzonderlijk vervangen. |
| `test_dhw_runtime.py` | 47 | Vervallen | Eigen tankdoelfasen, temperatuur-ACK, klimaat-AUTO/OFF, comfort/coast-model en hun herstelwrites zijn bewust verwijderd; relevante bron- en migratiebescherming wordt afzonderlijk vervangen. |
| `test_dhw_solar46.py` | 14 | Vervallen | Eigen tankdoelfasen, temperatuur-ACK, klimaat-AUTO/OFF, comfort/coast-model en hun herstelwrites zijn bewust verwijderd; relevante bron- en migratiebescherming wordt afzonderlijk vervangen. |
| `test_dhw_space_activity.py` | 13 | Vervallen | Eigen tankdoelfasen, temperatuur-ACK, klimaat-AUTO/OFF, comfort/coast-model en hun herstelwrites zijn bewust verwijderd; relevante bron- en migratiebescherming wordt afzonderlijk vervangen. |
| `test_dhw_stability50.py` | 5 | Vervallen | Eigen tankdoelfasen, temperatuur-ACK, klimaat-AUTO/OFF, comfort/coast-model en hun herstelwrites zijn bewust verwijderd; relevante bron- en migratiebescherming wordt afzonderlijk vervangen. |
| `test_dhw_sterilisation57.py` | 5 | Vervallen | Eigen tankdoelfasen, temperatuur-ACK, klimaat-AUTO/OFF, comfort/coast-model en hun herstelwrites zijn bewust verwijderd; relevante bron- en migratiebescherming wordt afzonderlijk vervangen. |
| `test_dhw_throttle50.py` | 8 | Vervallen | Eigen tankdoelfasen, temperatuur-ACK, klimaat-AUTO/OFF, comfort/coast-model en hun herstelwrites zijn bewust verwijderd; relevante bron- en migratiebescherming wordt afzonderlijk vervangen. |
| `test_dhw_ui50.py` | 6 | Vervallen | Eigen tankdoelfasen, temperatuur-ACK, klimaat-AUTO/OFF, comfort/coast-model en hun herstelwrites zijn bewust verwijderd; relevante bron- en migratiebescherming wordt afzonderlijk vervangen. |
| `test_dhw_weather_beta55.py` | 5 | Vervallen | Eigen tankdoelfasen, temperatuur-ACK, klimaat-AUTO/OFF, comfort/coast-model en hun herstelwrites zijn bewust verwijderd; relevante bron- en migratiebescherming wordt afzonderlijk vervangen. |
| `test_dishwasher.py` | 19 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_dishwasher_app31.py` | 51 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_dishwasher_beta55.py` | 7 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_dishwasher_config.py` | 9 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_dishwasher_priority32.py` | 67 | Behouden + vervangen | Behoud algemene afspraken; vervang alleen oude DHW-/klimaatfixture en betrokken writer-contract. |
| `test_dishwasher_recovery.py` | 15 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_dishwasher_runtime.py` | 12 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_electricity_cost.py` | 15 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_electricity_sensor.py` | 2 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_ems.py` | 17 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_engine.py` | 50 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_engine_phase_limits.py` | 2 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_entry_lifecycle49.py` | 8 | Behouden + vervangen | Behoud generieke historie, bronactualiteit, foutisolatie, UI/cache, veilige levenscyclus en bestaande apparaatbevoegdheid; vervang actieve DHW-/klimaatregels door SG/monitor/migratie. |
| `test_evening_wallbox.py` | 6 | Vervallen | Uitsluitend de verwijderde avond-/coastvoorspelling van de oude Panasonic-writer; SG gebruikt actuele elektriciteitsmetingen en de fabrikant regelt autonoom. |
| `test_frontend_registration51.py` | 5 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_heatpump_budget57.py` | 20 | Vervangen | SG-aanvraag en fysieke monitoring, actuele meterdekking, behoud oude gegevens en geen dubbel tellen of terugwinnen van native warmtepompverbruik. |
| `test_heatpump_learning36.py` | 6 | Vervangen | SG-aanvraag en fysieke monitoring, actuele meterdekking, behoud oude gegevens en geen dubbel tellen of terugwinnen van native warmtepompverbruik. |
| `test_heatpump_sources_beta55.py` | 10 | Vervangen | SG-aanvraag en fysieke monitoring, actuele meterdekking, behoud oude gegevens en geen dubbel tellen of terugwinnen van native warmtepompverbruik. |
| `test_house_first.py` | 24 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_house_runtime.py` | 18 | Behouden + vervangen | Behoud generieke historie, bronactualiteit, foutisolatie, UI/cache, veilige levenscyclus en bestaande apparaatbevoegdheid; vervang actieve DHW-/klimaatregels door SG/monitor/migratie. |
| `test_inventory.py` | 1 | Behouden + vervangen | Behoud generieke historie, bronactualiteit, foutisolatie, UI/cache, veilige levenscyclus en bestaande apparaatbevoegdheid; vervang actieve DHW-/klimaatregels door SG/monitor/migratie. |
| `test_isolation_reserves53.py` | 16 | Behouden + vervangen | Behoud algemene afspraken; vervang alleen oude DHW-/klimaatfixture en betrokken writer-contract. |
| `test_isolation_sensor53.py` | 2 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_isolation_ui53.py` | 13 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_learning.py` | 11 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_learning_api30.py` | 8 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_learning_hub30.py` | 37 | Behouden + vervangen | Behoud generieke historie, bronactualiteit, foutisolatie, UI/cache, veilige levenscyclus en bestaande apparaatbevoegdheid; vervang actieve DHW-/klimaatregels door SG/monitor/migratie. |
| `test_live_config34.py` | 6 | Behouden + vervangen | Behoud generieke historie, bronactualiteit, foutisolatie, UI/cache, veilige levenscyclus en bestaande apparaatbevoegdheid; vervang actieve DHW-/klimaatregels door SG/monitor/migratie. |
| `test_live_options34.py` | 41 | Behouden + vervangen | Behoud generieke historie, bronactualiteit, foutisolatie, UI/cache, veilige levenscyclus en bestaande apparaatbevoegdheid; vervang actieve DHW-/klimaatregels door SG/monitor/migratie. |
| `test_live_options49.py` | 9 | Behouden + vervangen | Behoud generieke historie, bronactualiteit, foutisolatie, UI/cache, veilige levenscyclus en bestaande apparaatbevoegdheid; vervang actieve DHW-/klimaatregels door SG/monitor/migratie. |
| `test_native_program56.py` | 20 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_option_help27.py` | 9 | Behouden + vervangen | Behoud generieke historie, bronactualiteit, foutisolatie, UI/cache, veilige levenscyclus en bestaande apparaatbevoegdheid; vervang actieve DHW-/klimaatregels door SG/monitor/migratie. |
| `test_overview_details60.py` | 22 | Behouden + vervangen | Behoud generieke historie, bronactualiteit, foutisolatie, UI/cache, veilige levenscyclus en bestaande apparaatbevoegdheid; vervang actieve DHW-/klimaatregels door SG/monitor/migratie. |
| `test_panel_module51.py` | 2 | Behouden + vervangen | Behoud generieke historie, bronactualiteit, foutisolatie, UI/cache, veilige levenscyclus en bestaande apparaatbevoegdheid; vervang actieve DHW-/klimaatregels door SG/monitor/migratie. |
| `test_phase_learning.py` | 5 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_phase_source_safety53.py` | 6 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_planner_pv_accuracy49.py` | 17 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_planner_quality.py` | 2 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_planner_restore49.py` | 8 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_planner_runtime49.py` | 20 | Behouden + vervangen | Behoud algemene afspraken; vervang alleen oude DHW-/klimaatfixture en betrokken writer-contract. |
| `test_platform_lifecycle49.py` | 5 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_power_overview60.py` | 8 | Behouden + vervangen | Behoud generieke historie, bronactualiteit, foutisolatie, UI/cache, veilige levenscyclus en bestaande apparaatbevoegdheid; vervang actieve DHW-/klimaatregels door SG/monitor/migratie. |
| `test_price_sources_beta48.py` | 8 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_priority_board35.py` | 33 | Behouden + vervangen | Behoud generieke historie, bronactualiteit, foutisolatie, UI/cache, veilige levenscyclus en bestaande apparaatbevoegdheid; vervang actieve DHW-/klimaatregels door SG/monitor/migratie. |
| `test_priority_dhw57.py` | 13 | Vervangen | SG-aanvraag en fysieke monitoring, actuele meterdekking, behoud oude gegevens en geen dubbel tellen of terugwinnen van native warmtepompverbruik. |
| `test_private_bundle.py` | 4 | Behouden + vervangen | Behoud generieke historie, bronactualiteit, foutisolatie, UI/cache, veilige levenscyclus en bestaande apparaatbevoegdheid; vervang actieve DHW-/klimaatregels door SG/monitor/migratie. |
| `test_public_first_install.py` | 4 | Behouden + vervangen | Behoud generieke historie, bronactualiteit, foutisolatie, UI/cache, veilige levenscyclus en bestaande apparaatbevoegdheid; vervang actieve DHW-/klimaatregels door SG/monitor/migratie. |
| `test_pv_api_config33.py` | 10 | Behouden + vervangen | Behoud algemene afspraken; vervang alleen oude DHW-/klimaatfixture en betrokken writer-contract. |
| `test_pv_calendar_beta55.py` | 12 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_pv_forecast33.py` | 39 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_pv_model.py` | 5 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_restart_auto47.py` | 24 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_restart_dashboard58.py` | 14 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_restart_dishwasher_beta48.py` | 1 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_restart_isolation53.py` | 20 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_restart_mode58.py` | 25 | Behouden + vervangen | Behoud algemene afspraken; vervang alleen oude DHW-/klimaatfixture en betrokken writer-contract. |
| `test_runtime.py` | 48 | Behouden + vervangen | Behoud generieke historie, bronactualiteit, foutisolatie, UI/cache, veilige levenscyclus en bestaande apparaatbevoegdheid; vervang actieve DHW-/klimaatregels door SG/monitor/migratie. |
| `test_runtime_guards49.py` | 7 | Behouden + vervangen | Behoud generieke historie, bronactualiteit, foutisolatie, UI/cache, veilige levenscyclus en bestaande apparaatbevoegdheid; vervang actieve DHW-/klimaatregels door SG/monitor/migratie. |
| `test_runtime_heatpump57.py` | 8 | Vervangen | SG-aanvraag en fysieke monitoring, actuele meterdekking, behoud oude gegevens en geen dubbel tellen of terugwinnen van native warmtepompverbruik. |
| `test_runtime_source_reports48.py` | 13 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_savings.py` | 22 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_sensor_recorder59.py` | 6 | Behouden + vervangen | Behoud generieke historie, bronactualiteit, foutisolatie, UI/cache, veilige levenscyclus en bestaande apparaatbevoegdheid; vervang actieve DHW-/klimaatregels door SG/monitor/migratie. |
| `test_source_wait52.py` | 8 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_source_wait_ui52.py` | 6 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_switch_recorder60.py` | 5 | Behouden + vervangen | Behoud generieke historie, bronactualiteit, foutisolatie, UI/cache, veilige levenscyclus en bestaande apparaatbevoegdheid; vervang actieve DHW-/klimaatregels door SG/monitor/migratie. |
| `test_thermal_climate.py` | 19 | Vervallen | Eigen tankdoelfasen, temperatuur-ACK, klimaat-AUTO/OFF, comfort/coast-model en hun herstelwrites zijn bewust verwijderd; relevante bron- en migratiebescherming wordt afzonderlijk vervangen. |
| `test_thermal_climate_confidence_beta48.py` | 19 | Vervallen | Eigen tankdoelfasen, temperatuur-ACK, klimaat-AUTO/OFF, comfort/coast-model en hun herstelwrites zijn bewust verwijderd; relevante bron- en migratiebescherming wordt afzonderlijk vervangen. |
| `test_thermal_feedback48.py` | 8 | Vervallen | Eigen tankdoelfasen, temperatuur-ACK, klimaat-AUTO/OFF, comfort/coast-model en hun herstelwrites zijn bewust verwijderd; relevante bron- en migratiebescherming wordt afzonderlijk vervangen. |
| `test_thermal_restore_beta48.py` | 16 | Vervallen | Eigen tankdoelfasen, temperatuur-ACK, klimaat-AUTO/OFF, comfort/coast-model en hun herstelwrites zijn bewust verwijderd; relevante bron- en migratiebescherming wordt afzonderlijk vervangen. |
| `test_thermal_runtime.py` | 17 | Vervallen | Eigen tankdoelfasen, temperatuur-ACK, klimaat-AUTO/OFF, comfort/coast-model en hun herstelwrites zijn bewust verwijderd; relevante bron- en migratiebescherming wordt afzonderlijk vervangen. |
| `test_thermal_runtime_beta48.py` | 16 | Vervallen | Eigen tankdoelfasen, temperatuur-ACK, klimaat-AUTO/OFF, comfort/coast-model en hun herstelwrites zijn bewust verwijderd; relevante bron- en migratiebescherming wordt afzonderlijk vervangen. |
| `test_thermal_sources49.py` | 10 | Vervallen | Eigen tankdoelfasen, temperatuur-ACK, klimaat-AUTO/OFF, comfort/coast-model en hun herstelwrites zijn bewust verwijderd; relevante bron- en migratiebescherming wordt afzonderlijk vervangen. |
| `test_ui_navigation.py` | 4 | Behouden + vervangen | Behoud generieke historie, bronactualiteit, foutisolatie, UI/cache, veilige levenscyclus en bestaande apparaatbevoegdheid; vervang actieve DHW-/klimaatregels door SG/monitor/migratie. |
| `test_ui_structure.py` | 21 | Behouden + vervangen | Behoud generieke historie, bronactualiteit, foutisolatie, UI/cache, veilige levenscyclus en bestaande apparaatbevoegdheid; vervang actieve DHW-/klimaatregels door SG/monitor/migratie. |
| `test_unified_planner.py` | 15 | Behouden + vervangen | Behoud generieke historie, bronactualiteit, foutisolatie, UI/cache, veilige levenscyclus en bestaande apparaatbevoegdheid; vervang actieve DHW-/klimaatregels door SG/monitor/migratie. |
| `test_wallbox.py` | 38 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_wallbox_activity.py` | 23 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_wallbox_policy33.py` | 23 | Behouden + vervangen | Behoud algemene afspraken; vervang alleen oude DHW-/klimaatfixture en betrokken writer-contract. |
| `test_wallbox_profile27.py` | 11 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_wallbox_runtime.py` | 16 | Behouden | Bestaande overige apparaat-, meet-, export-, planning-, herstel- of presentatieregel blijft van kracht. |
| `test_weather_forecast_beta55.py` | 12 | Vervallen | Uitsluitend de verwijderde avond-/coastvoorspelling van de oude Panasonic-writer; SG gebruikt actuele elektriciteitsmetingen en de fabrikant regelt autonoom. |

## Nieuwe verplichte dekking

| Afspraak | Nieuwe softwaredekking |
|---|---|
| Panasonic-entiteiten uitsluitend uitleesbaar | `test_sg_authority62.py`: native domeinen, oude tank-nummerbron, entiteiten van hetzelfde native apparaat, onwijzigbaar exact commandodoel. |
| Oude herstelwrites nooit herhalen | `test_sg_authority62.py`: restore, normale tick, Pauze, verwijderen en unload met oude pending/owned/recovery/manual-hold of beschadigde journaals. |
| Geen verborgen writer | Centrale actuatorautoriteit; inspectie van indirecte script-/helperdoelen en afwijzen van onbewijsbare routes. Losse battery-adapters moeten dezelfde Panasonic-grens houden. |
| Geen dubbele SG-eigenaar | SG-uitgang niet tegelijk als gewone last, batterijdoel of proxy bedienbaar; gewijzigde binding vernietigt oude renewals/toestemming. |
| SG-terugval is lokaal | Geteste native adapter met verlengbare toestemming; hardwareacceptatie moet bevestigen dat timerverlenging geen relaisklapper veroorzaakt en uitval de aanvraag laat aflopen. |
| Metingen blijven waarheid | Verse ontvangst/heartbeat, W/kW, importteken, meterdekking, bestaande fasegrenzen en ongewijzigde beschermde programma's. |
| Nieuwe aanvraag vereist nieuwe beslissing | Stabiele zon, stop-hysterese, rusttijd, sessielimiet, geen blinde hervatting na reload/crash, late meldingen geven geen nieuwe toestemming. |
| Geen gegevensverlies | Idempotente private archivering van oude configuratie/journaals/models; geen retentie- of leerreset; onbekende fouten blijven onderscheiden. |
| Overige apparaten beschermd | Wallbox blijft alleen-lezen; AEG maximaal één START per belading; batterij eigen bevoegdheid en ontvochtiger minlooptijd blijven gelden. |

## Uitvoering en beperkingen

Voer de baseline eerst op de vastgelegde beta.61-bron uit en noteer de werkelijk gevonden uitkomsten. Verplaats of verwijder oude testbestanden pas nadat hun behouden afspraken zijn toegewezen aan een vervangende test. Voer daarna alle toepasselijke tests uit op de exacte releasebron. Leg aantallen en tijden vast in het releaseverslag.

Een softwaretest gebruikt fictieve Home Assistant-doubles. Zij bewijst geen live Home Assistant-installatie, externe automatiseringscontrole, Shelly-firmwaretimer of fysieke Panasonic-SG-reactie. Voor automatische SG-bediening zijn afzonderlijke lokale ingebruiknamebevestigingen nodig.

## Werkelijk verwijderde en behouden broncontracten

De beta.61-baseline bevat 140 testbestanden met 2035 testfunctiedefinities. Er zijn 45 uitsluitend verouderde controllerbestanden verwijderd (673 definities). De 95 overige bestaande bestanden blijven aanwezig en bevatten nu 1296 definities. In 34 aangepaste bestaande bestanden zijn 103 oude namen vervallen of vervangen en 37 nieuwe namen toegevoegd. De tien nieuwe SG-bestanden voegen 205 definities toe; de afzonderlijke releasepakketproef voegt zeven definities toe. Samen zijn dit 106 actuele testbestanden met 1508 definities. Gemengde bestanden behouden hun overige apparaat-, opslag-, bron-, export-, prioriteits-, presentatie- en levenscyclusafspraken. Namen kunnen bij een equivalent SG-contract wijzigen; deze aantallen zijn geen parametriseerde testuitslagen.

| Gemengd aangepast bestand | Voorheen | Nu | Oude naam vervallen/vervangen | Nieuwe naam |
|---|---:|---:|---:|---:|
| `test_action_notifications61.py` | 29 | 19 | 11 | 1 |
| `test_activity_dashboard57.py` | 10 | 10 | 5 | 5 |
| `test_allocation_diagnostics.py` | 12 | 10 | 2 | 0 |
| `test_analysis_download56.py` | 18 | 18 | 1 | 1 |
| `test_analysis_export.py` | 32 | 36 | 0 | 4 |
| `test_battery_runtime.py` | 5 | 5 | 0 | 0 |
| `test_battery_serialization48.py` | 5 | 2 | 3 | 0 |
| `test_beta37_activation.py` | 3 | 3 | 3 | 3 |
| `test_command_arbitration49.py` | 7 | 6 | 1 | 0 |
| `test_decision_dashboard56.py` | 11 | 11 | 3 | 3 |
| `test_dishwasher_config.py` | 9 | 10 | 0 | 1 |
| `test_dishwasher_priority32.py` | 67 | 39 | 28 | 0 |
| `test_entry_lifecycle49.py` | 8 | 7 | 1 | 0 |
| `test_heatpump_learning36.py` | 6 | 6 | 0 | 0 |
| `test_heatpump_sources_beta55.py` | 10 | 10 | 1 | 1 |
| `test_isolation_reserves53.py` | 16 | 4 | 12 | 0 |
| `test_isolation_sensor53.py` | 2 | 2 | 0 | 0 |
| `test_learning_hub30.py` | 37 | 37 | 0 | 0 |
| `test_live_options49.py` | 9 | 6 | 3 | 0 |
| `test_native_program56.py` | 20 | 20 | 0 | 0 |
| `test_option_help27.py` | 9 | 11 | 3 | 5 |
| `test_overview_details60.py` | 22 | 22 | 3 | 3 |
| `test_planner_runtime49.py` | 20 | 18 | 2 | 0 |
| `test_power_overview60.py` | 8 | 8 | 3 | 3 |
| `test_priority_board35.py` | 33 | 32 | 5 | 4 |
| `test_private_bundle.py` | 4 | 4 | 0 | 0 |
| `test_pv_api_config33.py` | 10 | 10 | 0 | 0 |
| `test_restart_mode58.py` | 25 | 25 | 0 | 0 |
| `test_runtime.py` | 48 | 48 | 0 | 0 |
| `test_runtime_guards49.py` | 7 | 1 | 6 | 0 |
| `test_sensor_recorder59.py` | 6 | 6 | 0 | 0 |
| `test_switch_recorder60.py` | 5 | 5 | 0 | 0 |
| `test_ui_structure.py` | 21 | 21 | 3 | 3 |
| `test_wallbox_policy33.py` | 23 | 19 | 4 | 0 |

## Nieuwe controlebestanden

| Bestand | Testfunctiedefinities | Hoofdafspraak |
|---|---:|---|
| `test_sg_archive62.py` | 7 | Begrensde live samenvatting; volledige lokale/private oude gegevens blijven behouden en herstelbaar. |
| `test_sg_authority62.py` | 19 | Geen native writes via runtime, oude journals, generieke adapters, batterij of scripts; exact doel en één SG-eigenaar. |
| `test_sg_budget_priority62.py` | 26 | Uitsluitend werkelijk restoverschot; beschermde programma’s, capaciteit, fasen en één warmtepompmeting. |
| `test_sg_config62.py` | 20 | Volledige SG-instellingen, exclusieve koppeling, veilige ongecommissioneerde standaard en begrijpelijke uitleg. |
| `test_sg_controller62.py` | 63 | Toestandsmachine, lease, herstart zonder ON-herhaling, minimumtijd, bronverlies, uitschakelen, verse herbeoordeling en atomaire beslissingen bij tussentijdse wijzigingen. |
| `test_sg_diagnostics62.py` | 1 | Bevoegdheid en stroomscope zichtbaar zonder private bindings, historie of waarden te publiceren. |
| `test_sg_migration62.py` | 14 | Alle oude opties/journals/leerdata bewaren, geen nieuwe toestemming afleiden, idempotent en herstelbaar. |
| `test_sg_notifications62.py` | 10 | Actieverzoek alleen bij echte vereiste interventie; gewone wachttijd stil, herstartmelding eenmalig vernieuwen. |
| `test_sg_transport62.py` | 29 | Native get-status/ON-met-timer/OFF, exacte Shelly-identiteit, lokale klok en laatste controle vóór write. |
| `test_sg_ui_platforms62.py` | 16 | Drie bewijsniveaus, alleen-lezen Panasonic, SG-UI en native fabrieken zonder oude schrijvers. |

Het uitsluitend oude browserhulpmiddel `tools/check_dhw_gentle_ui.py` is vervangen door `tools/check_sg_ui.py`. De extra CI-grenscontrole `tools/check_sg_boundary.py` voorkomt terugkeer van native Panasonic-writers, controleert de centrale gewone/batterijroute en isoleert contact-RPC tot de SG-adapter. De bestaande algemene repository-, privacy-, documentatie- en volledige pytest-controles blijven gelden.

De volledige softwarecontrole gebruikt expliciete HA-doubles, fabrikantbronproeven en de werkelijk geleverde JavaScript-module. Een echte HA Core-installatie, browserrenderproef en fysieke Shelly/Panasonic-acceptatie zijn aparte proeven; deze mapping claimt die niet.

## Verificatie van de releasebestanden

`tests/test_release_packages62.py` voegt 13 onafhankelijke uitvoeringen toe met een echt tijdelijk Git-repository, Git-archive en lokale installatie-ZIP. Deze controleren exacte bronbytes, vier SHA256-/groottebewijzen, ontbrekende/gewijzigde/dubbele leden, verkeerde bron-SHA, teruggekeerde native controllers, afwijkende manifest-/const-/frontendversies, een beschadigd opnieuw gedownload document, reproduceerbare pakketten uit uitsluitend gecommitteerde bytes en een bestaande tag die naar een andere bron wijst. De bestaande-tagroute mag pakket- en downloadcontrole niet overslaan; ontbrekende assets of een bronverschil falen zonder tag of bestanden te overschrijven. Dit verandert geen historische testcounts. `tools/check_release_packages.py` draait vóór upload en na een geïsoleerde download van de vier daadwerkelijk gepubliceerde assets; CI wordt alleen groen als die tweede vergelijking met de exacte tag slaagt.

## Definitieve software-uitvoering

Op de bevroren beta.62-werkbron is de volledige toepasselijke suite uitgevoerd met `PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider`: **2809 geslaagd in 31,45 s**, zonder overgeslagen of mislukte tests. Deze definitieve run bevat alle 13 releasepakketgevallen en de vier aanvullende controllergevallen voor atomaire beslissingen. Dit zijn uitgevoerde, parametriseerde gevallen; de brondefinitietellingen hierboven beschrijven een andere grootheid. Privacy-, SG-grens-, overdrachts-, actuele-uitleg- en diffcontroles slagen. Echte publicatie-/downloadbewijzen komen uit de releasecontrole op de exacte gecommitteerde bron.
