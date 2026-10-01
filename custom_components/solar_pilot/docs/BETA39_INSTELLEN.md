# SolarPilot 1.0.0-beta.39 — afwasstart herstellen, upgrade en rollback

## Waarom deze release

Beta.38 herstelde het verdwenen bestaande AEG-afwasmachineprofiel, maar de praktijktest liet zien dat een klaargezette afwas nog steeds niet automatisch kon starten. De beta.39-code-audit vond drie regressies in het herstelde profiel en de live startcontrole:

1. Niet alleen de verbinding, maar ook onveranderde AEG-statussen zoals `Ready To Start`, deur gesloten, programmaselectie en `Enabled` moesten jonger dan vijf minuten zijn. Tijdens wachten op zonneoverschot konden die veilige statussen daardoor kunstmatig verlopen.
2. Het beta.38-herstelprofiel kende alleen `Running;Paused` als lopende cyclus en verloor de eerder afgesproken fasen zoals Washing, Rinsing, Drying en Ado Drying.
3. Beta.38 kon de numerieke AEG `Alerts`-sensor automatisch koppelen in `aeg_attributes`-modus. Wanneer die sensor geen echte technische `DISH_ALARM_*`-attributen aanbiedt, kon dat een permanente startblokkade geven.

Beta.39 corrigeert dit zonder de afgesproken startvoorwaarden te versoepelen.

## Wat beta.39 verandert

- `ConnectivityState` is de actuele bereikbaarheidsheartbeat. Die moet nog steeds vers en `Connected` zijn.
- `Ready To Start`, exacte APP-toestemming `Enabled`, deurstatus en programmaselectie mogen onveranderd blijven zolang ze bruikbaar zijn en de verbinding actueel blijft. `unknown`, `unavailable`, restored of een afwijkende waarde blokkeert nog steeds.
- Het volledige beschermde cyclusverloop is hersteld: Running, Washing, Prewash, Pre wash, Main wash, Rinsing, Drying, Ado Drying en Paused.
- Nieuwe automatische legacy-recovery koppelt een optionele numerieke Alerts-sensor niet meer als veiligheidsbron zonder bewezen bruikbare technische alarmvlaggen.
- Een éénmalige beta.39-migratie repareert uitsluitend het profiel dat aantoonbaar door beta.38 zelf als `recovered` werd aangemaakt. Handmatige afwasmachineprofielen worden niet generiek herschreven.
- De migratie maakt geen APP-aanvraag, verandert geen programma en verstuurt geen START.

## De bestaande regels blijven ongewijzigd

- Alleen een **nieuwe overgang naar exact `Enabled`** maakt één nieuwe afwasaanvraag. `Not Safety Relevant Enabled` telt niet.
- Als APP bij Home Assistant/SolarPilot-start al `Enabled` staat, ontstaat geen nieuwe aanvraag. Voor de volgende belading: APP uit en opnieuw aan.
- Voor 13:00 wordt vandaag gepland; vanaf 13:00 standaard de volgende kalenderdag.
- De standaarddeadline is 13:00 op de geplande dag. Netaanvulling gebeurt alleen als die bestaande optie aanstaat.
- Ready To Start, actuele verbinding, gesloten deur, geldig programma (niet `No Program`), eventueel bruikbare alarmcontrole, elektrische/fase-/kwartierpiegruimte en globale regelmodus blijven vereist.
- Eén belading krijgt maximaal één START. Een onzekere of mislukte opdracht wordt niet blind herhaald.
- SolarPilot gebruikt uitsluitend de native START-knop; nooit STOPRESET, PAUSE, RESUME, programmakeuze of een Shelly-relais om de beurt te starten/stoppen.
- End Of Cycle wordt eventgestuurd onthouden. AirDry/Ado Drying blijft onderdeel van de lopende cyclus; Off of Disconnected alleen is geen bevestigd einde.
- De bestaande centrale prioriteit blijft gelden. Een voorkeur-AEG kan vóór Auto laden (Wallbox) staan; noodzakelijk comfort en elektrische beveiligingen blijven erboven.

## Controle na installatie

1. Maak een volledige Home Assistant-back-up.
2. Installeer beta.39 en herstart Home Assistant.
3. Open **SolarPilot → Toestellen → Afwasmachine** en controleer dat het profiel aanwezig is en op de bedoelde modus staat.
4. Open **Voorrang** en controleer de bewaarde positie ten opzichte van **Auto laden (Wallbox)**.
5. Voor een nieuwe testbelading: kies fysiek het programma, sluit de deur en zet APP/remote-start **uit en opnieuw aan** zodat een nieuwe overgang naar exact `Enabled` ontstaat.
6. Controleer in SolarPilot de geplande dag/deadline en de reden waarom de machine wacht. Een statische Ready To Start/deur/programmakeuze mag na vijf minuten niet meer uitsluitend wegens ouderdom blokkeren zolang ConnectivityState actueel blijft.
7. Laat de startvoorwaarden ontstaan. Er mag maximaal één START worden verzonden.
8. Controleer na start dat Washing/Rinsing/Drying/Ado Drying als dezelfde beschermde beurt blijven gelden.
9. Controleer na afloop dat het korte `End Of Cycle`-signaal wordt onthouden en niet wordt vervangen door de latere `Off`/`Disconnected`-status.

## Rollback

1. Zet SolarPilot op **Pauze**.
2. Laat een reeds lopende afwasbeurt volledig afwerken; SolarPilot mag die niet afbreken.
3. Herstel beta.38 of je Home Assistant-back-up en herstart Home Assistant.
4. Controleer daarna afwasprofiel en centrale prioriteit opnieuw.

Beta.39 bewaart de bestaande configuratie en voegt alleen versiegebonden reparatiemetadata toe. Een door beta.39 herstelde volledige faselijst kan door oudere code worden gelezen. Houd er wel rekening mee dat beta.38 opnieuw zijn oude 5-minutencontrole en oude recoverygedrag gebruikt.
