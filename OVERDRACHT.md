<!-- solarpilot-handoff-schema: 1 -->
<!-- solarpilot-handoff-version: 1.0.0-beta.39 -->

# OVERDRACHT — SolarPilot

Laatst bijgewerkt: **1 oktober 2026**  
Actuele/productieversie voor deze overdracht: **v1.0.0-beta.39**.

## 1. Projectdoel in gewone taal
SolarPilot is de centrale Home Assistant-regeling voor zonnestroom, Wallbox, Panasonic Aquarea warmtepomp/tapwater, klimaat, flexibele verbruikers, fasebelasting, voorspellingen, kostenanalyse, historiek en lokaal leren. De gebruiker moet de belangrijkste keuzes in gewone taal kunnen begrijpen en bedienen.

## 2. Actuele basis
Beta.39 is rechtstreeks opgebouwd op de in de Library geregistreerde volledige **beta.38**-bron. Beta.38 zelf was de gecontroleerde samenvoeging van beta.36, geldige beta.37-wijzigingen en het eerste AEG-profielherstel. Beta.39 vervangt die basis niet: het repareert drie concrete afwasmachine-regressies die tijdens de praktijktest zichtbaar werden.

Na registratie moeten `LATEST.zip`, `releases/SolarPilot-v1.0.0-beta.39-GitHub-HACS.zip`, `releases/SolarPilot-v1.0.0-beta.39-local.zip`, `CURRENT.json`, deze `OVERDRACHT.md` en `PROJECT_INDEX.json` allemaal naar beta.39 verwijzen.

## 3. Absolute ontwerpregels die niet stilzwijgend mogen wijzigen
- Behoud bestaande werkende functies, gebruikersinstellingen, leerdata en huidige koppelingen bij upgrade.
- Migreer oude configuraties automatisch waar dat veilig en eenduidig kan; bij twijfel niets fysiek activeren.
- Veiligheid, fabrikantbeveiliging, wekelijkse Panasonic-sterilisatie en noodzakelijk comfort staan boven energieoptimalisatie.
- De centrale flexibele prioriteitenlijst is leidend. Nieuwe gewone flexibele toestellen komen onderaan totdat de gebruiker ze bewust verplaatst.
- Een toestel mag zonnevermogen gebruiken dat de auto al gebruikt alleen wanneer het boven **Auto laden (Wallbox)** staat én de afzonderlijke toestemming aanstaat. Wallbox blijft read-only.
- Een voorkeurs-AEG-afwasmachine staat vóór de Wallbox wanneer die regel actief is; een al gestarte afwascyclus wordt nooit onderbroken.
- Extra warm water tot 60 °C is een flexibele zonnebuffer en gebruikt geen Wallbox-vermogen. Normaal DHW-comfort blijft apart beschermd.
- Panasonic kiest HEAT/COOL; SolarPilot mag geen agressieve modusswitching introduceren.
- Realtime P1/PV-metingen en fysieke grenzen gaan altijd vóór forecast of aangeleerde schattingen.
- Geen tokens, wachtwoorden, API-sleutels, private keys, adressen of private installatie-identiteiten in publieke bron/release.
- Codewijziging = dezelfde release ook tests, changelog, actuele gebruikersuitleg, installatie/upgrade, rollback en dit overdrachtsdossier bijwerken.

## 4. Actuele werking
### Modi en bediening
Dagelijkse modusnamen: **Alleen bekijken**, **Automatisch regelen**, **Pauze**. Belangrijkste groepen: Overzicht, Voorrang, Toestellen, Warmte & comfort, Planning, Energie, Auto & batterij, Export en Uitleg.

### Centrale voorrang
Veiligheid en noodzakelijk ruimte-/warmwatercomfort zijn niet versleepbaar. De flexibele lijst bepaalt de echte relatieve volgorde. Voor Wallbox-zonnevermogen zijn positie én toestemming vereist. Minimumlooptijden en lopende beschermde cycli blijven intact.

### AEG-afwasmachine
APP-start is start-only: alleen de bevestigde native START-knop, nooit STOPRESET/PAUSE/RESUME/programmakeuze of stekkerrelais. Alleen een nieuwe overgang naar exact `Enabled` maakt één aanvraag. Vóór 13:00: vandaag; vanaf 13:00: volgende kalenderdag. Standaarddeadline 13:00; netaanvulling alleen wanneer de bestaande optie dat toestaat. Startup met APP al aan maakt geen aanvraag. Eén belading krijgt maximaal één START; onzekere START wordt niet blind herhaald. End Of Cycle blijft eventgestuurd en persistent; AirDry/Ado Drying is geen einde.

Beta.39 gebruikt **ConnectivityState** als actuele bereikbaarheidsheartbeat. Ready To Start, exact Enabled, gesloten deur en geselecteerd programma zijn statische veiligheidswaarden die langer dan vijf minuten ongewijzigd mogen blijven terwijl op zon wordt gewacht. Unknown, Unavailable, restored of een werkelijk onveilige/afwijkende waarde blokkeert nog steeds. Het volledige lopende cyclusverloop omvat Running, Washing, Prewash, Pre wash, Main wash, Rinsing, Drying, Ado Drying en Paused.

### Beta.38→beta.39 herstel
Beta.38 kon een verdwenen legacy-AEG-profiel veilig same-device reconstrueren. Beta.39 behoudt dat pad maar koppelt bij nieuwe recovery geen optionele numerieke Alerts-sensor automatisch als veiligheidsbron zonder echte technische `DISH_ALARM_*`-vlaggen. Een éénmalige reparatie raakt uitsluitend het profiel dat beta.38 zelf als `recovered` markeerde: de verkorte `Running;Paused`-lijst wordt indien aanwezig hersteld en alleen een door beta.38 automatisch gekozen onbruikbare alarmbron wordt verwijderd. Handmatige profielen worden niet generiek herschreven. De migratie maakt geen ticket en verstuurt geen START.

### Beta.37/beta.36 en eerdere regels
Veilige éénmalige activering van reeds geconfigureerde analyse/leer-/regelmodules, centrale zichtbare prioriteit, gescheiden warmtepomp/basislastleren, PV-kalibratie, fasebewaking, eerlijke exportdekking en alle bestaande planner-/Wallbox-/DHW-regels blijven cumulatief behouden.

### DHW/klimaat/PV/fasen/planner
Behoud 50 °C normaal DHW, 46 °C bewaakte comfortgrens, Panasonic-differentie -5 °C, 50 °C zonnebuffer, 60 °C extra PV-buffer, max. 50 °C bij actieve koeling en autonome 62 °C-sterilisatie. PV: 13,8 kWp panelen, 10 kW omvormerlimiet, lokale schaduw/kalibratie, realtime PV als waarheid. Fase- en plannerregels mogen geen elektrische ruimte verzinnen. Warmtepompleren blijft gescheiden van gewone huishoudbasislast.

## 5. Configuratie, integraties en belangrijke entiteiten
Generieke integraties: Home Assistant, digitale meter/HomeWizard, PV/Forecast.Solar, Panasonic Aquarea, Wallbox, flexibele toestellen, toekomstige batterijprofielen. Exacte installatie-entity_ids altijd uit actuele HA/config lezen en niet in publieke documentatie hardcoderen.

Legacy AEG-recovery wordt lokaal via het HA-apparaatregister herleid. Verplichte same-device rollen: START, ApplianceState, ConnectivityState, RemoteControl, DoorState en programmaselectie. CyclePhase en native starttijd zijn optioneel; alarm is alleen optioneel bruikbaar wanneer de gekozen bron een verifieerbare veiligheidssemantiek heeft. Het HA-device-id wordt uitsluitend gehasht/fingerprinted in statusinformatie.

## 6. Belangrijke ontwerpbeslissingen + waarom
- **Beta.38 Library source als absolute basis**: voorkomt opnieuw ontwikkelen op een oudere versie.
- **Connectivity als heartbeat, statische waarden als state**: voorkomt dat een legitieme wachttijd op zonneoverschot vanzelf ongeldig wordt zonder een echte toestandwijziging.
- **Fail-closed blijft intact**: onbekend/onbeschikbaar/restored/afwijkend blokkeert; alleen kunstmatige leeftijd van statische waarden is verwijderd.
- **Geen numerieke Alerts-teller als automatische veiligheidswaarheid**: zonder expliciete technische vlaggen is `2` of een andere aggregate waarde onvoldoende om veilig/gevaarlijk af te leiden.
- **Beta.39-reparatie alleen op beta.38-marker**: voorkomt overschrijven van handmatig ingestelde profielen.
- **Same-device + unieke role mapping**: voorkomt verkeerde START-knop of ander keukenapparaat.
- **APP startup latch**: voorkomt onverwachte start na upgrade wanneer remote APP al aan stond.
- **Centrale zichtbare order = echte order**: voorkomt verborgen Wallbox-reclaim door een lagere load.

## 7. Automatische processen
- Runtime reconcilieert configuratie/toestand na start/reload zonder dubbele fysieke opdrachten.
- Beta.36-prioriteitsmigratie bewaart de bestaande effectieve volgorde.
- Beta.37-activeringsprofiel is éénmalig en overschrijft latere gebruikerskeuzes niet.
- Beta.38 legacy-recovery blijft idempotent en maakt geen fysieke opdracht.
- Beta.39-reparatie is idempotent, gemarkeerd met eigen schema en beperkt tot het beta.38 recovered-profiel.
- Analyse, leerdata, historiek en planners blijven lokaal/persistent volgens hun bestaande bewaartermijnen.

## 8. Geheimenbeleid
Nooit wachtwoorden, tokens, API-sleutels, private keys, exacte adressen, ruwe privé-analyses of private device-identiteiten in Git/release/OVERDRACHT. Analyse-export blijft lokaal en wordt alleen handmatig gedeeld. Publieke preflight moet groen zijn vóór publicatie.

## 9. Testprocedure + actuele teststatus
Op beta.39 uitgevoerd op 1 oktober 2026:
- `pytest -q`: **1434 passed**.
- Gerichte afwasmachinetests: **133 passed**.
- Nieuwe tests dekken lange wachttijd met verse ConnectivityState, volledig faseherstel, reparatie van onbruikbare beta.38-autoalarmkoppeling en niet-wijzigen van handmatige profielen.
- Releasechecks, compileall en publieke preflight moeten groen blijven in de finale cachevrije releaseboom; zie `docs/TESTRESULTATEN_BETA39.md` voor het finale verslag.

## 10. Bekende problemen / beperkingen
- De fysieke AEG-afwasmachine kan vanuit de bouwomgeving niet echt worden gestart. Na installatie is één gecontroleerde nieuwe belading nodig om live AEG-cloud/HA-terugmelding te bevestigen.
- Zonder exclusieve afwasmachinemeter blijft het elektrische programma-/faseprofiel conservatief geschat; geen fictieve meetdata toevoegen.
- Een incomplete/ambigue AEG-mapping wordt bewust niet automatisch hersteld. `dishwasher_setup` meldt dit en vereist dan handmatige controle.
- Een handmatig gekoppelde alarmbron blijft bewust fail-closed volgens de gekozen configuratie; beta.39 verwijdert alleen de specifieke onbewezen bron die beta.38 automatisch koos.

## 11. Concrete openstaande ontwikkeling
- Na installatie beta.39 één echte nieuwe AEG-belading controleren: APP uit→aan, geplande dag/deadline, wachten >5 min indien nodig, één START, Running/Washing/Drying/Ado Drying en End Of Cycle.
- Later eventueel exclusieve Shelly-vermogensmeting van de afwasmachine gebruiken voor gemeten programmafasen/planning; tot dan geen faseprofiel verzinnen.
- Ruimteverwarmingsfase en overige toekomstige SolarPilot-uitbreidingen alleen verderzetten vanaf de geregistreerde beta.39-basis en deze overdracht.

## 12. Installatie/upgrade en rollback
Zie `docs/BETA39_INSTELLEN.md`.

Upgrade: Home Assistant-back-up → beta.39 installeren → herstart → Toestellen/Afwasmachine/Voorrang/status controleren → voor een nieuwe testbelading APP uit en weer aan → fysieke start alleen onder de bestaande live voorwaarden.

Rollback: SolarPilot Pauze → lopende beschermde cyclus laten afwerken → vorige release/back-up herstellen → HA herstart → toestelconfiguratie en prioriteit opnieuw verifiëren. Nooit een lopende afwasbeurt met STOPRESET vanuit SolarPilot beëindigen.

## 13. Belangrijkste bestanden
- `custom_components/solar_pilot/dishwasher.py`: startveiligheid en statische guard/Connectivity-heartbeat.
- `custom_components/solar_pilot/dishwasher_recovery.py`: beta.38 recovery + gerichte beta.39-reparatiemigratie.
- `custom_components/solar_pilot/dishwasher_app.py`: APP-ticket, 13:00-planning en eventgestuurd einde.
- `custom_components/solar_pilot/runtime.py`: runtime, éénmalige Auto voor daadwerkelijk legacy-recovered profiel en fysieke commandoroute.
- `custom_components/solar_pilot/priority_board.py` / `wallbox_policy.py`: centrale voorrang en Wallbox-regels.
- `custom_components/solar_pilot/current_guide.py`: enige actuele gebruikersuitlegbron.
- `tests/test_dishwasher.py`, `tests/test_dishwasher_recovery.py`, `tests/test_dishwasher_app31.py`, volledige `tests/`-suite.
- `CHANGELOG.md`, `docs/BETA39_INSTELLEN.md`, `docs/TESTRESULTATEN_BETA39.md`.

## 14. Release-checklist
1. CURRENT/overdracht lezen en juiste basis bevestigen.
2. Manifest/const/current guide exact dezelfde versie.
3. Volledige tests groen.
4. Publieke preflight groen op schone bronboom.
5. Actuele uitleg + option-help opnieuw genereren.
6. Changelog + installatie/rollback + testverslag + OVERDRACHT actualiseren.
7. Geen caches/private data in pakket.
8. Release-zip bouwen + checksum vastleggen.
9. `releases/`, `LATEST.zip`, `CURRENT.json`, `OVERDRACHT.md`, `PROJECT_INDEX.json` atomair naar beta.39 bijwerken.
10. GitHub/HACS alleen vanaf deze gecontroleerde beta.39-bron publiceren, liefst één gecontroleerde commit/tag/release om ruis te vermijden.

## 15. AI-handoff
Start altijd bij `CURRENT.json` + deze `OVERDRACHT.md`; kies nooit een versie enkel omdat die later op GitHub of in een bestandsnaam staat. Beta.39 = geregistreerde beta.38 plus de afwas-delayed-start/phase/alarm-reparatie. Verander afwas-APP-, 13:00-, prioriteits-, DHW-, Wallbox- of veiligheidsregels niet zonder expliciete nieuwe gebruikersbeslissing en bijbehorende regressietests.
