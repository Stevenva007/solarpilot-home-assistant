# SolarPilot 1.0.0-beta.38 — upgrade, afwasmachinecontrole en rollback

## Waarom deze release

De analyse-export van de actieve beta.35-installatie liet zien dat de afwasmachinemodule niet actief was: er stond geen afwasmachine in `devices`, er waren geen APP-tickets en de centrale prioriteitenlijst bevatte de afwasmachine niet. De AEG-entiteiten bestonden wel in Home Assistant. Daardoor kon de bestaande automatische startlogica nooit worden bereikt.

Beta.38 herstelt deze specifieke configuratieregressie zonder de afgesproken startregels te versoepelen.

## Wat beta.38 éénmalig doet

- Alleen wanneer de installatie al de bekende afwasmachine-dashboardhelpers bevat en nog géén afwasmachineprofiel in SolarPilot heeft, probeert SolarPilot de bestaande AEG/Electrolux-koppeling te reconstrueren.
- Alle verplichte bronnen moeten eenduidig op hetzelfde Home Assistant-apparaat zitten: START, ApplianceState, ConnectivityState, RemoteControl, DoorState en programmaselectie.
- Oude/onbruikbare dubbele START-knoppen worden genegeerd. PAUSE, RESUME, STOPRESET en een starttijdveld kunnen nooit als START worden gekozen.
- Bij ontbrekende of ambigue bronnen wordt niets automatisch gekoppeld en wordt geen fysiek recht verleend.
- Een succesvol hersteld legacy-profiel wordt alleen éénmalig op Auto gezet wanneer er voor die nieuwe identiteit nog geen opgeslagen gebruikerskeuze bestaat.
- De migratie verstuurt geen START, verandert geen programma en maakt geen APP-aanvraag.

## De afgesproken APP-regels blijven hetzelfde

- Alleen een **nieuwe overgang naar exact `Enabled`** is een aanvraag voor één belading.
- `Not Safety Relevant Enabled` is geen starttoestemming.
- APP dat bij Home Assistant/SolarPilot-start al `Enabled` is, wordt niet als nieuwe druk geïnterpreteerd. Zet APP voor de volgende belading eerst uit en opnieuw aan.
- Vóór 13:00 wordt dezelfde kalenderdag gepland; vanaf 13:00 standaard de volgende kalenderdag.
- De standaarddeadline is 13:00 op de geplande dag. Netstroom mag alleen aanvullen wanneer die bestaande optie expliciet aanstaat.
- Ready To Start, actuele verbinding, gesloten deur, geldig programma, alarmcontrole en elektrische ruimte blijven verplicht.
- Maximaal één START per belading. Een onzekere/mislukte START wordt niet blind herhaald.
- Een lopend programma wordt nooit onderbroken door SolarPilot; End Of Cycle wordt eventgestuurd bewaard en AirDry blijft onderdeel van de cyclus.

## Prioriteit na upgrade

Veiligheid en noodzakelijk comfort blijven beschermd. Binnen de flexibele lijst geldt de opgeslagen centrale volgorde. Voor een voorkeur-AEG-profiel blijft de bedoelde positie vóór **Auto laden (Wallbox)** behouden. Een toestel mag zonnevermogen gebruiken dat de auto al gebruikt alleen wanneer het boven de Wallbox staat én de aparte toestemming aanstaat. Extra 60 °C-warmwaterbuffer gebruikt geen Wallbox-vermogen.

## Controle na installatie

1. Maak vóór de update een Home Assistant-back-up.
2. Installeer beta.38 en herstart Home Assistant.
3. Controleer **SolarPilot → Toestellen**: de AEG-afwasmachine moet zichtbaar zijn of de status moet duidelijk melden waarom automatische reconstructie niet kon.
4. Controleer **Voorrang** en de toestemming ten opzichte van de Wallbox.
5. Controleer zonder fysieke start eerst verbinding, deur, remote-control en Ready To Start.
6. Voor een echte nieuwe testbelading: zet de AEG APP-toestemming uit en opnieuw aan, zodat SolarPilot een nieuwe aanvraag ziet.
7. Controleer de geplande dag/deadline voordat je een fysieke test laat uitvoeren.

## Rollback

Als beta.38 onverwacht gedrag geeft:

1. Zet SolarPilot op **Pauze**. Laat een reeds lopende afwascyclus afwerken; SolarPilot hoort die niet te stoppen.
2. Herstel de vorige SolarPilot-release (beta.36) uit het release-archief of je Home Assistant-back-up.
3. Herstart Home Assistant.
4. Controleer de toestelconfiguratie en centrale prioriteiten opnieuw. De beta.38-migratie gebruikt gewone config-entryopties en geen geheim extern opslagformaat.

Een rollback naar beta.36 verwijdert uiteraard de nieuwe automatische afwasmachineherstelcode. Wanneer het profiel door beta.38 al in de Home Assistant-configuratie is opgeslagen, controleer na rollback de zichtbare toestelconfiguratie in plaats van aan te nemen dat oude code die nieuwe migratiemetadata begrijpt.
