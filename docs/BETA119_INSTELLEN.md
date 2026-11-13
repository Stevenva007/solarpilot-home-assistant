# SolarPilot beta.119 — installatie en rollback

## Wat deze versie oplost

Dezelfde volledige EMS-presentatie stond op 23 afzonderlijke EMS-sensoren, naast de bestaande complete EMS-statussensor en de algemene Status-sensor. Daardoor wijzigden ook sensoren over een ander onderwerp wanneer bijvoorbeeld batterijbronnen of planning werden bijgewerkt. Home Assistant verstuurt zulke entiteitswijzigingen ook naar verbonden dashboards zonder SolarPilot-kaart.

Beta.119 beperkt de attributen van iedere deelsensor tot het passende onderwerp. De complete actuele gegevens blijven op **EMS status**, onder `ems` van de algemene **Status**-sensor en in de analyse-export beschikbaar. Het SolarPilot-dashboard gebruikt die complete bron. Sensorwaarden, kwaliteit, oorspronkelijke rapporttijden en alle regelingen blijven gelijk.

| Deelsensoren | Beschikbare onderwerpdetails |
| --- | --- |
| Kwartierpiek | `capacity`, `phase`, `electrical_limits` |
| Fasen en faseherkenning | `phase`, `phase_learning`, `phase_attribution`, `historical_phase_profile` |
| Lokale PV | `local_pv`, `forecast` |
| Batterijvloot | `battery_fleet` |
| Batterijanalyse | `battery_analysis`, `economy` |
| EMS-dagtellingen | `today`, `economy`, `savings`, `electricity_today` |
| EMS status / Status → ems | Het volledige bestaande overzicht |

Algemene `ready`, `warnings` en `legacy_conflicts` blijven ook op de deelsensoren beschikbaar. Ontbrekende velden worden niet als nul ingevuld. De originele objecten en hun brongegevens blijven bewaard.

## Bijwerken en controleren

1. Maak een privé Home Assistant-back-up met SolarPilot-configuratie en -opslag.
2. Installeer na geslaagde publicatie **1.0.0-beta.119** via HACS.
3. Herstart Home Assistant volledig en herlaad de browser of app. Controleer integratie- en geladen kaartversie.
4. Controleer bestaande eigen templates. Een niet-gerelateerd attribuut dat eerder toevallig op een deelsensor stond, lees je voortaan van de bestaande EMS-statussensor of van Status → `ems`.
5. Vergelijk de SolarPilot-statuswaarden, volledige kaartdetails en de omvang van live-attributen. Controleer paneelverbindingen afzonderlijk gedurende normaal gebruik. Minder herhaalde data bewijst geen oplossing voor elk geheugen-, netwerk- of Android-probleem.

De update wijzigt geen instellingen of opslagformaat en vraagt geen nieuwe bronbevestiging of fysieke SG-proef.

## Rollback

Installeer beta.118 via HACS, herstart Home Assistant en herlaad de browser. Het opslagformaat is gelijk; de oude brede deelsensorattributen keren terug. Herstel voor een volledige rollback de passende privéback-up.

Zie [TESTRESULTATEN_BETA119.md](TESTRESULTATEN_BETA119.md) voor validatie en grenzen.
