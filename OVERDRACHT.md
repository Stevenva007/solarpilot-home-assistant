<!-- solarpilot-handoff-schema: 1 -->
<!-- solarpilot-handoff-version: 1.0.0-beta.42 -->

# OVERDRACHT — SolarPilot

Laatst bijgewerkt: **2 oktober 2026**
Actuele software-/publicatieversie voor deze overdracht: **v1.0.0-beta.42**. Werkelijk geïnstalleerde en gecontroleerde live basis: **v1.0.0-beta.41** op Home Assistant Core 2026.9.4; beta.42-liveacceptatie volgt na installatie.

## 1. Projectdoel in gewone taal
SolarPilot is de centrale Home Assistant-regeling voor zonnestroom, Wallbox, Panasonic Aquarea warmtepomp/tapwater, klimaat, flexibele verbruikers, fasebelasting, voorspellingen, kostenanalyse, historiek en lokaal leren. De gebruiker moet de belangrijkste keuzes in gewone taal kunnen begrijpen en bedienen.

## 2. Actuele basis
Beta.42 bouwt rechtstreeks voort op de geregistreerde en werkelijk geïnstalleerde **beta.41**-bron. Beta.41 had 1465 geslaagde Python-tests en elf geslaagde browsercontroles; publicatieworkflow en release-assets zijn daarna onafhankelijk geverifieerd. Zij is op Home Assistant Core 2026.9.4 geladen en gecontroleerd; veilige modules waren gericht geactiveerd en de oude afzonderlijke 60/50-boilerautomatiseringen stonden uit. Beta.42 verandert de AEG-migratie-, APP-, klimaat- of DHW-veiligheidsregels niet, maar voegt een veilige DHW-Hervatroute, eerlijke effectieve Voorrang, gecorrigeerde hulptekst/labels en een begrensde lokale leerreset toe.

Na registratie moeten `LATEST.zip`, `releases/SolarPilot-v1.0.0-beta.42-GitHub-HACS.zip`, `releases/SolarPilot-v1.0.0-beta.42-local.zip`, `CURRENT.json`, deze `OVERDRACHT.md` en `PROJECT_INDEX.json` allemaal naar beta.42 verwijzen. De bestaande beta.41- en eerdere tags/assets blijven ongewijzigde historie.

## 3. Absolute ontwerpregels die niet stilzwijgend mogen wijzigen
- Behoud bestaande werkende functies, gebruikersinstellingen, leerdata en huidige koppelingen bij upgrade.
- Migreer oude configuraties automatisch waar dat veilig en eenduidig kan; bij twijfel niets fysiek activeren.
- Veiligheid, fabrikantbeveiliging, wekelijkse Panasonic-sterilisatie en noodzakelijk comfort staan boven energieoptimalisatie.
- De centrale flexibele prioriteitenlijst is leidend. Nieuwe gewone flexibele toestellen komen onderaan totdat de gebruiker ze bewust verplaatst.
- De toestelwizard mag bij een actieve centrale prioriteitenlijst geen tweede rangorde- of Wallbox-toestemming tonen of terugschrijven, ook niet vanuit een oud geopend formulier.
- Een toestel mag zonnevermogen gebruiken dat de auto al gebruikt alleen wanneer het boven **Auto laden (Wallbox)** staat én de afzonderlijke toestemming aanstaat. Een bewaarde Ja onder Auto laden blijft opgeslagen maar is effectief Nee. Wallbox blijft read-only.
- Een voorkeurs-AEG-afwasmachine staat vóór de Wallbox wanneer die regel actief is; een al gestarte afwascyclus wordt nooit onderbroken.
- Extra warm water tot 60 °C is een flexibele zonnebuffer en gebruikt geen Wallbox-vermogen. Normaal DHW-comfort blijft apart beschermd.
- Panasonic kiest HEAT/COOL; SolarPilot mag geen agressieve modusswitching introduceren.
- Een handmatig of extern OFF gezette klimaatzone is niet van SolarPilot. Gewone AUTO-beslissingen en verwijderen mogen uitsluitend SolarPilot-eigen coast-zones vrijgeven; een harde comfortgrens mag alleen de werkelijk overschrijdende zone naar AUTO zetten.
- DHW-terugvalhysterese mag alleen een bewezen door SolarPilot uitgegeven en teruggemeld hoog doel vasthouden. Handmatige/fabrikantbediening blijft leidend en echte netafname of koeling mag een luxe-doel niet kunstmatig vasthouden.
- Realtime P1/PV-metingen en fysieke grenzen gaan altijd vóór forecast of aangeleerde schattingen.
- Geen tokens, wachtwoorden, API-sleutels, private keys, adressen of private installatie-identiteiten in publieke bron/release.
- Codewijziging = dezelfde release ook tests, changelog, actuele gebruikersuitleg, installatie/upgrade, rollback en dit overdrachtsdossier bijwerken.

## 4. Actuele werking
### Modi en bediening
Dagelijkse modusnamen: **Alleen bekijken**, **Automatisch regelen**, **Pauze**. Belangrijkste dashboardgroepen: Overzicht, Voorrang, Toestellen, Warmte & comfort, Planning, Energie, Batterij, Export en Uitleg. Het configuratiecentrum behoudt de bredere groep **Auto & batterij**.

### Centrale voorrang
Veiligheid en noodzakelijk ruimte-/warmwatercomfort zijn niet versleepbaar. De vaste regels en de verplaatsbare toestellen, Auto laden en extra warm water staan in één verticale lijst. De flexibele lijst bepaalt de echte relatieve volgorde. Voor Wallbox-zonnevermogen zijn positie én toestemming vereist. Beta.42 toont de bewaarde keuze en het effectieve resultaat afzonderlijk: Ja onder Auto laden blijft bewaard maar geldt zichtbaar als Nee. Dit is voorwaardelijke toestemming, geen vermogensgarantie of nieuw actuatorrecht. De toestelwizard verbergt bij centrale schema's 1 en 2 de oude dubbele rangorde-/Wallboxvelden en bewaart centrale waarden tegen een oud geopend formulier. Minimumlooptijden en lopende beschermde cycli blijven intact.

### Toestellen, startvoorwaarden en geschiedenis
De doorslaggevende samenvatting blijft exact de actuele `result.reason` van de regelaar. Beta.41 toont daarnaast gestructureerde startinvoer: globale modus, Auto-deelname, beschikbaarheid/storing, vrijgave, vraag/tijdvenster, minimumrust, beschermde-cyclusvrijgave, daglimiet, planner-, Wallbox- en runtimeblokkering, benodigd vermogen/startmarge, geldige vrije-vermogensmeting en resterende stabiliteitstijd. Een volledige checklist is nadrukkelijk geen aparte startgarantie en mag de engine-uitkomst niet tegenspreken.

De apparaatgeschiedenis toont altijd een afzonderlijke Startreden en Stopreden. Alleen werkelijk opgeslagen redenen worden getoond. Een ontbrekende externe oorzaak blijft expliciet onbekend; herstarts, meetgaten en oude sessies worden niet achteraf verzonnen.

### AEG-afwasmachine
APP-start is start-only: alleen de bevestigde native START-knop, nooit STOPRESET/PAUSE/RESUME/programmakeuze of stekkerrelais. Alleen een nieuwe overgang naar exact `Enabled` maakt één aanvraag. Vóór 13:00: vandaag; vanaf 13:00: volgende kalenderdag. Standaarddeadline 13:00; netaanvulling alleen wanneer de bestaande optie dat toestaat. Startup met APP al aan maakt geen aanvraag. Eén belading krijgt maximaal één START; onzekere START wordt niet blind herhaald. End Of Cycle blijft eventgestuurd en persistent; AirDry/Ado Drying is geen einde.

Beta.39 gebruikt **ConnectivityState** als actuele bereikbaarheidsheartbeat. Ready To Start, exact Enabled, gesloten deur en geselecteerd programma zijn statische veiligheidswaarden die langer dan vijf minuten ongewijzigd mogen blijven terwijl op zon wordt gewacht. Unknown, Unavailable, restored of een werkelijk onveilige/afwijkende waarde blokkeert nog steeds. Het volledige lopende cyclusverloop omvat Running, Washing, Prewash, Pre wash, Main wash, Rinsing, Drying, Ado Drying en Paused.

Beta.40 houdt uitsluitend de bestaande legacy-recovery maximaal tien minuten na SolarPilot-start actief. Relevante state-events en een begrensde controle om de tien seconden geven laat geladen Home Assistant-entiteiten een nieuwe kans. Na succes, timeout of unload worden de tijdelijke listeners verwijderd. Een laat hersteld profiel wordt persistent en live toegepast, maar de migratie maakt geen APP-aanvraag en verstuurt geen START.

### Beta.38→beta.40 herstel
Beta.38 kon een verdwenen legacy-AEG-profiel veilig same-device reconstrueren. Beta.39 behield dat pad en koppelde bij nieuwe recovery geen optionele numerieke Alerts-sensor automatisch als veiligheidsbron zonder echte technische `DISH_ALARM_*`-vlaggen. Beta.40 lost daarbovenop uitsluitend de opstartvolgordefout op. Eén compleet, eenduidig apparaat met START, ApplianceState, ConnectivityState, RemoteControl, DoorState en programmaselectie blijft vereist. Een éénmalige reparatie raakt uitsluitend het profiel dat beta.38 zelf als `recovered` markeerde: de verkorte `Running;Paused`-lijst wordt indien aanwezig hersteld en alleen een door beta.38 automatisch gekozen onbruikbare alarmbron wordt verwijderd. Handmatige profielen en bestaande gebruikersmodi worden niet generiek herschreven. Een later bewust verwijderd herstelprofiel wordt niet stil opnieuw aangemaakt.

### Beta.37/beta.36 en eerdere regels
Veilige éénmalige activering van reeds geconfigureerde analyse/leer-/regelmodules, centrale zichtbare prioriteit, gescheiden warmtepomp/basislastleren, PV-kalibratie, fasebewaking, eerlijke exportdekking en alle bestaande planner-/Wallbox-/DHW-regels blijven cumulatief behouden.

### DHW/klimaat/PV/fasen/planner
Behoud 50 °C normaal DHW, 46 °C bewaakte comfortgrens, Panasonic-differentie -5 °C, 50 °C zonnebuffer, 60 °C extra PV-buffer, max. 50 °C bij actieve koeling en autonome 62 °C-sterilisatie. Beta.41 houdt de bredere overschothysterese alleen vast wanneer SolarPilot het hoge doel werkelijk bezit. Werkelijke netafname boven de ingestelde grens, actieve koeling en een onbeheerde/onbevestigde 60 °C-beslissing slaan de gewone terugvalvertraging over; `manual_hold`, sterilisatie en fabrikantbescherming blijven elke SolarPilot-write blokkeren. Beta.42 kan een herkende manual hold gericht hervatten, uitsluitend buiten Automatisch regelen en zonder wachtende opdracht. Hervatten wist alleen die rusttoestand, schrijft geen temperatuur en start geen regelcyclus.

Voor klimaat betekent Panasonic AUTO alleen dat de fabrikant mag regelen; `hvac_action` bepaalt of er werkelijk wordt verwarmd of gekoeld. De harde comfortband gebruikt een echte overschrijding; exact op de grens is nog geen hard override. Een gewone winter-AUTO mag uitsluitend een door SolarPilot zelf in OFF/coast gezette zone terugzetten. Een handmatige/onbeheerde OFF-zone blijft uit, behalve wanneer precies die zone de harde comfortgrens overschrijdt. Verwijderen herstelt eveneens alleen eigen coast-zones. Bij 0% modelzekerheid blijft automatisch coast conservatief uit en blijft de ingestelde reactievertraging een zichtbare fallback totdat echte cycli voldoende bewijs leveren.

PV: 13,8 kWp panelen, 10 kW omvormerlimiet, lokale schaduw/kalibratie, realtime PV als waarheid. Fase- en plannerregels mogen geen elektrische ruimte verzinnen. Warmtepompleren blijft gescheiden van gewone huishoudbasislast.

### Wallbox live-koppeling
De live installatie beschikt over één afgeleide effectieve-sessiebron met de volledige categorieën zonne-auto laden/wachten, manueel laden/klaar/solar uit en laden gestopt. Koppel deze bron als `session_mode_entity`; hardcodeer het installatie-specifieke entity-id niet in publieke bron. De standaard waardelijsten herkennen deze statussen al. De aangetroffen oorzaak van een oude afgeleide status was een te zwakke bronbeschikbaarheid: alleen de afgeleide tekstwaarde werd gecontroleerd, terwijl actuele fysieke status-, vermogen- en ruwe rapportage niet gezamenlijk op versheid werden bewaakt. De lokale package-definitie is vervangen door fail-closed bronvalidatie met niet-restored waarden, een maximale leeftijd van vijf minuten en een minuutheartbeat in een controle-attribuut. Home Assistant-configuratiecontrole en template-reload slaagden; daarna meldde het dashboard actueel gestopt met ongeveer tien seconden oude fysieke rapportage en zonder EV-vermogenskrediet. De ingestelde Full Solar-select is afzonderlijk en bewijst de huidige sessie niet. Manueel, oud, restored of onbekend laden blijft fail-closed en SolarPilot verstuurt nooit een Wallbox-opdracht.

## 5. Configuratie, integraties en belangrijke entiteiten
Generieke integraties: Home Assistant, digitale meter/HomeWizard, PV/Forecast.Solar, Panasonic Aquarea, Wallbox, flexibele toestellen, toekomstige batterijprofielen. Exacte installatie-entity_ids altijd uit actuele HA/config lezen en niet in publieke documentatie hardcoderen.

Legacy AEG-recovery wordt lokaal via het HA-apparaatregister herleid. Verplichte same-device rollen: START, ApplianceState, ConnectivityState, RemoteControl, DoorState en programmaselectie. CyclePhase en native starttijd zijn optioneel; alarm is alleen optioneel bruikbaar wanneer de gekozen bron een verifieerbare veiligheidssemantiek heeft. Het HA-device-id wordt uitsluitend gehasht/fingerprinted in statusinformatie.

## 6. Belangrijke ontwerpbeslissingen + waarom
- **Beta.38 Library source als absolute basis**: voorkomt opnieuw ontwikkelen op een oudere versie.
- **Connectivity als heartbeat, statische waarden als state**: voorkomt dat een legitieme wachttijd op zonneoverschot vanzelf ongeldig wordt zonder een echte toestandwijziging.
- **Fail-closed blijft intact**: onbekend/onbeschikbaar/restored/afwijkend blokkeert; alleen kunstmatige leeftijd van statische waarden is verwijderd.
- **Geen numerieke Alerts-teller als automatische veiligheidswaarheid**: zonder expliciete technische vlaggen is `2` of een andere aggregate waarde onvoldoende om veilig/gevaarlijk af te leiden.
- **Beta.39-reparatie alleen op beta.38-marker**: voorkomt overschrijven van handmatig ingestelde profielen.
- **Begrensde beta.40-retry in plaats van permanente discovery**: vangt late Home Assistant-setup op zonder SolarPilot tot een algemene apparaat-autoconfigurator te maken.
- **Geen migratie-opdracht**: ook een laat gevonden complete mapping wordt alleen opgeslagen en live gekoppeld; START vereist daarna nog steeds een nieuwe fysieke APP-overgang naar exact Enabled.
- **Same-device + unieke role mapping**: voorkomt verkeerde START-knop of ander keukenapparaat.
- **APP startup latch**: voorkomt onverwachte start na upgrade wanneer remote APP al aan stond.
- **Centrale zichtbare order = echte order**: voorkomt verborgen Wallbox-reclaim door een lagere load.
- **Engine-reden blijft doorslaggevend**: de beta.41-checklist maakt invoer controleerbaar maar introduceert geen tweede beslisalgoritme of impliciet startrecht.
- **Eigendom per klimaatzone**: voorkomt dat een globale AUTO-beslissing of verwijderen een handmatig OFF gezette ruimte wakker maakt.
- **DHW-hysterese vereist eigendom**: voorkomt dat een nooit verzonden, extern gekozen of niet bevestigde 60 °C-stand als SolarPilot-zonnebuffer wordt vastgehouden.
- **Hervat wist alleen manual hold**: een gerichte gebruikersactie buiten Automatisch regelen mag geen temperatuurwrite of impliciete regelcyclus veroorzaken.
- **Begrensde leerreset**: onderhoud aan lokale afgeleide modellen mag operationele klimaatveiligheid, configuratie, historische bootstrap of afzonderlijke cyclus-/DHW-/plannermodellen niet wissen.

## 7. Automatische processen
- Runtime reconcilieert configuratie/toestand na start/reload zonder dubbele fysieke opdrachten.
- Beta.36-prioriteitsmigratie bewaart de bestaande effectieve volgorde.
- Beta.37-activeringsprofiel is éénmalig en overschrijft latere gebruikerskeuzes niet.
- Beta.38 legacy-recovery blijft idempotent en maakt geen fysieke opdracht.
- Beta.39-reparatie is idempotent, gemarkeerd met eigen schema en beperkt tot het beta.38 recovered-profiel.
- Beta.40 activeert een tijdelijke post-start retry van maximaal tien minuten, stopt listeners na succes/timeout/unload en past alleen een exact complete legacy-mapping live toe.
- Beta.41 bewaart één centrale prioriteitseditor; openen of opslaan stuurt geen actuator. Alleen bekijken, Automatisch regelen en Pauze blijven globale keuzes; Uitgesloten/Auto blijft afzonderlijk per toestel.
- Beta.41 bewaart klimaat- en DHW-eigendom over gewone regelcycli. Handmatige overrides worden niet door een algemene herstelopdracht overschreven.
- Beta.42 toont DHW-Hervat alleen onder veilige modus-/pendingvoorwaarden, maakt effectieve Voorrang expliciet en begrenst leerreset tot lokale afgeleide modellen zonder tick of actuatoropdracht.
- Analyse, leerdata, historiek en planners blijven lokaal/persistent volgens hun bestaande bewaartermijnen.

## 8. Geheimenbeleid
Nooit wachtwoorden, tokens, API-sleutels, private keys, exacte adressen, ruwe privé-analyses of private device-identiteiten in Git/release/OVERDRACHT. Analyse-export blijft lokaal en wordt alleen handmatig gedeeld. Publieke preflight moet groen zijn vóór publicatie.

## 9. Testprocedure + actuele teststatus
Beta.42 is op 2 oktober 2026 softwarematig releaseklaar gemaakt. De definitieve samengevoegde Python-regressiesuite is groen met **1472 geslaagde tests in 8.88 s**. Alle elf browsercontroles, actuele-uitlegcontrole (hash `813423dab59557a1`), handoff, repositoryvalidatie en publieke preflight zijn groen. Beta.42 is nog niet als werkelijk geladen versie op de live Home Assistant-installatie bevestigd; beta.41 op Core 2026.9.4 blijft de bewezen live basis.

Gerichte regressiedekking is toegevoegd of uitgebreid voor:

- DHW-Hervat uitsluitend buiten Automatisch regelen en zonder pending opdracht, zonder temperatuurwrite;
- eerlijke effectieve Voorrang onder/boven Auto laden met behoud van de opgeslagen keuze;
- begrensde leerreset met behoud van configuratie, bootstrap, operationele klimaatstate en andere modellen;
- gecorrigeerde interface-/hulpteksten in beide talen en de gegenereerde optiehulp;
- behoud van de beta.41-klimaat-/DHW-eigendomsgrenzen;
- bestaande beta.40-AEG-recovery en Wallbox fail-closed gedrag.

Werkelijke aantallen en alle releasecontroles worden uitsluitend na uitvoering vastgelegd in `docs/TESTRESULTATEN_BETA42.md`; de huidige 1472/8,88 s is het werkelijk uitgevoerde Python-resultaat, geen afleiding.

## 10. Bekende problemen / beperkingen
- De fysieke AEG-afwasmachine kan vanuit de bouwomgeving niet echt worden gestart. Na installatie is één gecontroleerde nieuwe belading nodig om live AEG-cloud/HA-terugmelding te bevestigen.
- Zonder exclusieve afwasmachinemeter blijft het elektrische programma-/faseprofiel conservatief geschat; geen fictieve meetdata toevoegen.
- Een incomplete/ambigue AEG-mapping wordt bewust niet automatisch hersteld. `dishwasher_setup` meldt dit en vereist dan handmatige controle.
- Een handmatig gekoppelde alarmbron blijft bewust fail-closed volgens de gekozen configuratie; beta.39 verwijdert alleen de specifieke onbewezen bron die beta.38 automatisch koos.
- De beta.40-retry stopt na tien minuten. Wanneer de onderliggende template-/AEG-integratie nog later beschikbaar wordt, moet die oorzaak eerst worden hersteld en een nieuwe Home Assistant-start een nieuw begrensd venster openen.
- Klimaatrespons, koelrespons en reactievertraging kunnen niet uit code worden afgeleid. Bij onvoldoende echte cycli blijft modelzekerheid laag en gebruikt SolarPilot de zichtbare conservatieve fallback; dit is geen reden om comfortgrenzen te verruimen.
- De fysieke koelroute en onmiddellijke DHW-terugval tijdens een echte actieve koelcyclus zijn nog niet live bewezen.
- De actuele gestopte Wallbox-bronversheid is live bevestigd, maar zonne-auto- en manuele overgangen moeten nog afzonderlijk worden doorlopen; SolarPilot versoepelt hiervoor geen backend-versheidsgrens.
- Batterijbediening blijft zonder gekoppelde hardware en afzonderlijke globale/individuele/eigenaarschaptoestemming adviserend. Wallbox blijft read-only.

## 11. Concrete openstaande ontwikkeling
- Na installatie werkelijk geladen beta.42 en geforceerd vernieuwde kaart controleren; daarna DHW-Hervat, effectieve Voorrang en begrensde leerreset afzonderlijk accepteren.
- De gewijzigde Wallbox-sessiebron is na groene Home Assistant-configuratiecontrole/reload als actueel gestopt en zonder EV-krediet bevestigd. Doorloop nog zonne-auto en manueel plus versheid/heartbeat. Geen status afleiden uit alleen de Full Solar-select of netimport.
- De oude 60/50-boilerautomatiseringen zijn reeds uitgeschakeld; laat ze uit om gelijktijdige regelaars te voorkomen.
- Eén echte nieuwe AEG-belading controleren: APP uit→aan, geplande dag/deadline, wachten >5 min indien nodig, één START, Running/Washing/Drying/Ado Drying en End Of Cycle.
- Later eventueel exclusieve Shelly-vermogensmeting van de afwasmachine gebruiken voor gemeten programmafasen/planning; tot dan geen faseprofiel verzinnen.
- Thermisch model, PV-kalibratie en faseprofielen uitsluitend uit voldoende echte meetdagen/cycli verder laten leren; geen ontbrekend bewijs kunstmatig invullen.
- Overige toekomstige SolarPilot-uitbreidingen alleen verderzetten vanaf de na release geregistreerde beta.42-basis en deze overdracht.

## 12. Installatie/upgrade en rollback
Zie `docs/BETA42_INSTELLEN.md`.

Upgrade: Home Assistant-back-up → beta.42 installeren → herstart → geladen backendversie controleren → browser geforceerd vernieuwen → DHW-Hervat en Voorrang in Alleen bekijken/Pauze controleren → begrensde leerreset alleen bewust testen → Wallbox-sessiebron en versheid bevestigen → pas daarna globale regeling en afzonderlijke toestellen gericht vrijgeven. Voor een nieuwe AEG-testbelading APP uit en weer aan; fysieke start alleen onder de bestaande live voorwaarden.

Rollback: SolarPilot Pauze → lopende beschermde cyclus laten afwerken → geregistreerde beta.41/back-up herstellen → HA herstart → centrale prioriteit, toestelconfiguratie, klimaat-eigendom en DHW-eigendom opnieuw verifiëren. Nooit een lopende afwasbeurt met STOPRESET vanuit SolarPilot beëindigen.

## 13. Belangrijkste bestanden
- `custom_components/solar_pilot/dishwasher.py`: startveiligheid en statische guard/Connectivity-heartbeat.
- `custom_components/solar_pilot/dishwasher_recovery.py`: beta.38 recovery, beta.39-reparatie en begrensde beta.40 post-start retry.
- `custom_components/solar_pilot/dishwasher_app.py`: APP-ticket, 13:00-planning en eventgestuurd einde.
- `custom_components/solar_pilot/runtime.py`: runtime, fysieke commandoroute, DHW-Hervat en begrensde leerreset zonder tick/actuatoropdracht.
- `custom_components/solar_pilot/priority_board.py` / `wallbox_policy.py`: centrale voorrang en Wallbox-regels.
- `custom_components/solar_pilot/thermal_runtime.py`: per-zone SolarPilot-eigendom en gerichte AUTO/OFF-opdrachten; `thermal_climate.py`: begrensd wissen van thermische leerdata met behoud van operationele state.
- `custom_components/solar_pilot/dhw.py` / `dhw_runtime.py`: doelbeleid, eigendom, koeling en veilige terugval.
- `custom_components/solar_pilot/current_guide.py`: enige actuele gebruikersuitlegbron.
- `tests/test_runtime.py`, `tests/test_thermal_runtime.py`, `tests/test_dhw.py`, `tests/test_dhw_runtime.py`, `tests/test_ui_structure.py` en volledige `tests/`-suite.
- `CHANGELOG.md`, `docs/BETA42_INSTELLEN.md`, `docs/TESTRESULTATEN_BETA42.md`.

## 14. Release-checklist
1. CURRENT/overdracht lezen en juiste basis bevestigen.
2. Manifest/const/current guide exact dezelfde versie.
3. Volledige tests groen.
4. Publieke preflight groen op schone bronboom.
5. Actuele uitleg + option-help opnieuw genereren.
6. Changelog + installatie/rollback + testverslag + OVERDRACHT actualiseren.
7. Geen caches/private data in pakket.
8. Release-zip bouwen + checksum vastleggen.
9. `releases/`, `LATEST.zip`, `CURRENT.json`, `OVERDRACHT.md`, `PROJECT_INDEX.json` atomair naar beta.42 bijwerken.
10. GitHub/HACS alleen vanaf deze gecontroleerde beta.42-bron publiceren, liefst één gecontroleerde commit/tag/release om ruis te vermijden. Bestaande beta.41- en eerdere tags/assets nooit herschrijven.

## 15. AI-handoff
Start altijd bij `CURRENT.json` + deze `OVERDRACHT.md`; kies nooit een versie enkel omdat die later op GitHub of in een bestandsnaam staat. Beta.42 = de werkelijk op HA Core 2026.9.4 gecontroleerde beta.41-basis plus veilige DHW-Hervat, eerlijke effectieve Voorrang, gecorrigeerde hulptekst/labels en begrensde lokale leerreset. Beta.40 blijft de bron van de begrensde post-start AEG-recovery. Verander afwas-APP-, 13:00-, prioriteits-, DHW-, klimaat-, Wallbox- of veiligheidsregels niet zonder expliciete nieuwe gebruikersbeslissing en bijbehorende regressietests.
