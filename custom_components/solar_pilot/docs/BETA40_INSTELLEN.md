# SolarPilot 1.0.0-beta.40 — laat AEG-profiel herstellen, upgrade en rollback

## Waarom deze release

De live beta.39-diagnose bewees een opstartvolgordefout. Tijdens de enige herstelcontrole van SolarPilot waren de twee legacy-dashboardmarkers nog niet door Home Assistant geladen. De migratie noteerde daarom `not_applicable`. Later waren beide markers en alle verplichte AEG-rollen wel aanwezig op één Home Assistant-apparaat, inclusief de juiste native START-knop, maar beta.39 controleerde niet opnieuw. Daardoor verscheen de afwasmachine niet onder **Toestellen** of **Voorrang**.

Beta.40 herhaalt uitsluitend deze bestaande legacy-recovery gedurende een kort, begrensd venster na de SolarPilot-start. Dit is geen algemene toestelontdekking en geen fysieke bedieningsactie.

## Wat beta.40 verandert

- De directe recoverycontrole tijdens SolarPilot-setup blijft bestaan.
- Wanneer het legacy-profiel nog ontbreekt, blijft een gerichte retry maximaal tien minuten actief. Relevante state-events en een controle om de tien seconden kunnen de mapping opnieuw beoordelen.
- Na succes, timeout of unload worden de tijdelijke listeners gestopt.
- Een compleet laat gevonden profiel wordt persistent opgeslagen en live toegepast. Een extra integratie-reload is daarvoor niet nodig.
- `dishwasher_setup` toont per verplichte rol `missing`, `selected` of `ambiguous`, plus aantallen voor `disabled`, `restored`, `not_loaded` en `unavailable`, zonder het private Home Assistant-device-id te publiceren.
- Een eerder door deze migratie hersteld en later bewust verwijderd profiel wordt niet stil opnieuw aangemaakt.
- Alleen het exact gemarkeerde legacy-herstelprofiel kan de afgesproken eenmalige Auto-deelname terugkrijgen wanneer voor die identiteit nog geen opgeslagen gebruikersmodus bestaat. Gewone nieuwe toestellen blijven Uitgesloten.

## De herstelgrens blijft streng

Een automatisch profiel ontstaat alleen wanneer precies één volledig en eenduidig Home Assistant-apparaat alle verplichte rollen levert:

- native **START**-knop;
- `ApplianceState`;
- `ConnectivityState`;
- `RemoteControl`;
- `DoorState`;
- geldige programmaselectie.

`CyclePhase` en de native uitgestelde start zijn optioneel. Een numerieke Alerts-bron wordt niet automatisch als veiligheidswaarheid gekoppeld wanneer er geen verifieerbare technische alarmvlaggen zijn. PAUSE, RESUME, STOPRESET en starttijd kunnen nooit als START worden gekozen. Een ontbrekende of ambigue verplichte rol levert geen profiel en geen fysiek recht op.

## Wat de migratie nadrukkelijk niet doet

- Zij verstuurt geen START en roept geen andere fysieke service aan.
- Zij maakt geen APP-aanvraag en verandert geen programma.
- Zij zet APP/remote-start niet aan.
- Zij stopt, pauzeert of reset een lopende cyclus niet.
- Zij overschrijft geen handmatig afwasmachineprofiel of bestaande gebruikersmodus.

Ook na een succesvolle recovery moet per nieuwe belading een echte nieuwe overgang naar exact `Enabled` worden waargenomen. Een APP-status die bij startup al `Enabled` is, telt niet. Ready To Start, actuele `Connected`, gesloten deur, geldig programma, elektrische ruimte, centrale modus en alle bestaande comfort- en veiligheidslocks blijven vereist. Eén belading krijgt maximaal één START; een onzekere opdracht wordt niet blind herhaald.

## Upgrade en controle

1. Maak een volledige Home Assistant-back-up.
2. Installeer beta.40 via de bestaande HACS-repository en herstart Home Assistant.
3. Controleer in de SolarPilot-status de werkelijk geladen integratieversie. Die moet `1.0.0-beta.40` tonen. Vernieuw de browser geforceerd wanneer alleen de kaart nog een oude versie toont.
4. Wacht na de herstart maximaal tien minuten terwijl Home Assistant de template- en AEG-entiteiten laadt.
5. Open **SolarPilot → Toestellen**. Het veilig herkende AEG-profiel moet daar één keer verschijnen.
6. Open **Voorrang**. Het voorkeurprofiel hoort volgens de bestaande regel vóór **Auto laden (Wallbox)** te staan; noodzakelijke comfort- en veiligheidsregels blijven erboven.
7. Controleer `dishwasher_setup`. Bij een onvolledige mapping gebruikt u de rolinformatie om de ontbrekende of ambigue bron te vinden; forceer geen actuatorrecht.
8. Voor één gecontroleerde echte testbelading: kies fysiek het programma, sluit de deur en zet APP/remote-start uit en opnieuw aan zodat een nieuwe overgang naar exact `Enabled` ontstaat.
9. Controleer geplande dag/deadline, wachtrede, maximaal één START en het beschermde verloop tot het echte End Of Cycle-signaal.

## Als het profiel na tien minuten ontbreekt

- Controleer eerst of beide legacy-markers en alle zes verplichte AEG-rollen werkelijk geladen zijn.
- Bekijk de rolstatus in `dishwasher_setup`; `missing` of `ambiguous` is een bewuste veiligheidsblokkering, geen toestemming om een willekeurige entiteit te kiezen.
- Controleer of een vereist AEG-entity in het Home Assistant-entiteitenregister is uitgeschakeld of alleen als restored/onbeschikbaar bestaat.
- Herlaad of herstel eerst de onderliggende template-/AEG-integratie. Herstart daarna Home Assistant zodat een nieuw begrensd recoveryvenster begint.
- Maak bij blijvende twijfel een lokale SolarPilot-analyse-export. Deel geen tokens, adressen of private device-id's publiek.

## Rollback

1. Zet SolarPilot op **Pauze**.
2. Laat een reeds lopende afwascyclus volledig afwerken; gebruik geen STOPRESET.
3. Herstel beta.39 of de Home Assistant-back-up en herstart Home Assistant.
4. Controleer profiel, modus en centrale prioriteit opnieuw.

Een door beta.40 veilig opgeslagen profiel blijft gewone Home Assistant-configuratie. Beta.39 kent de begrensde post-start retry niet; wanneer het profiel vóór rollback nog niet bestond, kan dezelfde opstartvolgordefout daar dus opnieuw optreden.
