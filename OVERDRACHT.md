<!-- solarpilot-handoff-schema: 1 -->
<!-- solarpilot-handoff-version: 1.0.0-beta.43 -->

# OVERDRACHT — SolarPilot

Laatst bijgewerkt: **2 oktober 2026**
Actuele software-/publicatieversie voor deze overdracht: **v1.0.0-beta.43**. De release is gepubliceerd onder de exacte, onveranderlijke tag `v1.0.0-beta.43` (commit `a50c62e269a44f61b432af5cdda2522e1e6cb7ce`); GitHub-workflow `37005461399` en beide onveranderlijke release-ZIP's zijn gecontroleerd. Na een bestaande NAS-back-up, HACS-installatie en de door de gebruiker goedgekeurde Home Assistant-herstart zijn backend én kaart `1.0.0-beta.43` werkelijk geladen op Home Assistant Core 2026.9.4. Dit bewijst de geladen versie, niet dat alle fysieke acceptatiescenario's al zijn uitgevoerd.

Publicatie en installatie waren expliciet toegestaan en zijn afgerond. Beta.43 omvat startdiagnostiek, actieve toestellen, Wallbox-wacht-/stopgeschiedenis, veilige terugnavigatie, geschat automatisch zonnevoordeel, een aparte maandagdeadline en duidelijke Wallbox-toestemming voor de avondvoorraad. De geregistreerde beta.42-tag en pakketten blijven ongewijzigde historie. De gebruiker gaf de herstart tijdens de beschermde AEG-cyclus bewust vrij; na de herstart rapporteerde de afwasmachine nog steeds `Running`. Er is daarvoor geen geforceerde START/STOP of APP-herarming uitgevoerd.

## 1. Projectdoel in gewone taal
SolarPilot is de centrale Home Assistant-regeling voor zonnestroom, Wallbox, Panasonic Aquarea warmtepomp/tapwater, klimaat, flexibele verbruikers, fasebelasting, voorspellingen, kostenanalyse, historiek en lokaal leren. De gebruiker moet de belangrijkste keuzes in gewone taal kunnen begrijpen en bedienen.

## 2. Actuele basis
De werkelijk geladen **beta.43** bouwt rechtstreeks voort op de geregistreerde en eerder live gecontroleerde beta.42-bron. Alle beta.42-functies, bestaande instellingen en leerdata blijven behouden. De oude afzonderlijke 60/50-boilerautomatiseringen stonden tijdens de live basiscontrole uit. De nieuwe avondvoorraadregel maakt het bestaande vóór-Wallbox-budget expliciet, maar telt alleen verse, bevestigde Full Solar-sessies met laadvraag en werkelijk laadvermogen mee. Zij verleent geen Wallbox-actuatorrecht of algemeen nieuw configuratierecht. Extra 60 °C gebruikt dit budget nooit. De globale modus staat na de herstart bewust op **Alleen bekijken**, omdat de DHW-status `needs_review` eerst via de gerichte boilercontrole moet worden afgerond; herstel van **Automatisch regelen** is nog niet bevestigd.

De GitHub-release en beide beta.43-assets zijn werkelijk gepubliceerd en tegen de exacte tag gecontroleerd: `SolarPilot-v1.0.0-beta.43-GitHub-HACS.zip` en `SolarPilot-v1.0.0-beta.43-local.zip`. De externe Library was in deze werkfase niet toegankelijk; `CURRENT.json`, `LATEST.zip` en `PROJECT_INDEX.json` zijn daar daarom niet bijgewerkt en mogen niet als geregistreerd worden voorgesteld. Bestaande tags/assets blijven ongewijzigde historie. De hieronder gedateerde beta.42-controles beschrijven de vorige live basis en blijven als zodanig behouden.

## 3. Absolute ontwerpregels die niet stilzwijgend mogen wijzigen
- Behoud bestaande werkende functies, gebruikersinstellingen, leerdata en huidige koppelingen bij upgrade.
- Migreer oude configuraties automatisch waar dat veilig en eenduidig kan; bij twijfel niets fysiek activeren.
- Veiligheid, fabrikantbeveiliging, wekelijkse Panasonic-sterilisatie en noodzakelijk comfort staan boven energieoptimalisatie.
- De centrale flexibele prioriteitenlijst is leidend. Nieuwe gewone flexibele toestellen komen onderaan totdat de gebruiker ze bewust verplaatst.
- De toestelwizard mag bij een actieve centrale prioriteitenlijst geen tweede rangorde- of Wallbox-toestemming tonen of terugschrijven, ook niet vanuit een oud geopend formulier.
- Een toestel mag zonnevermogen gebruiken dat de auto al gebruikt alleen wanneer het boven **Auto laden (Wallbox)** staat én de afzonderlijke toestemming aanstaat. Een bewaarde Ja onder Auto laden blijft opgeslagen maar is effectief Nee. Wallbox blijft read-only.
- Een voorkeurs-AEG-afwasmachine staat vóór de Wallbox wanneer die regel actief is; een al gestarte afwascyclus wordt nooit onderbroken.
- Extra warm water tot 60 °C is een flexibele zonnebuffer en gebruikt geen Wallbox-vermogen. Normaal DHW-comfort blijft apart beschermd.
- De afzonderlijke avondvoorraad (standaard maximaal 55 °C) mag indien nodig zonnevermogen van een actuele, bevestigde autonome Full Solar-laadsessie benutten. Manueel, onbekend of oud autoladen levert geen avondvoorraadkrediet; temperatuurgrenzen, koeling, noodzakelijk woningcomfort, sterilisatie en kwartierpiekruimte blijven leidend.
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

Live controle op 2 oktober toonde een ontbrekende bronheartbeat: de werkelijk geïnstalleerde Electrolux Status 2.3.5 werkt met cloud-push, maar de coordinator heeft geen periodiek opvraaginterval. Daardoor bleef ook ConnectivityState bij een legitiem wachtend toestel ouder worden. Een echte cloudstatusopvraag via Home Assistant herstelde onmiddellijk de bestaande APP-aanvraag; de vijfminutengrens en overige startbeveiligingen zijn niet versoepeld. Zie de live herstelnotitie in onderdeel 11.

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
- **Connectivity als heartbeat, statische waarden als state**: statische veiligheidswaarden hoeven tijdens wachten niet te wijzigen; de actuele verbinding moet wel werkelijk opnieuw worden bevestigd. De aangetroffen cloud-pushkoppeling levert zelf geen periodieke heartbeat en heeft hiervoor een echte statusopvraag nodig, geen kunstmatig opgefriste template.
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
Definitieve lokale beta.43-controle op 2 oktober 2026: **1656 geslaagde Python-tests in 9.95 s** en **veertien geslaagde browsercontroles**. Actuele-uitlegcontrole (hash `2072294edfd69fb0`), handoff, repositoryvalidatie, publieke preflight, JavaScript-syntax en diffcontrole zijn groen. Testverslag: `docs/TESTRESULTATEN_BETA43.md`. Browserproeven gebruiken fictieve gegevens zonder fysieke opdrachten. GitHub-workflow `37005461399` is groen; de release op tag `a50c62e269a44f61b432af5cdda2522e1e6cb7ce`, beide ZIP-assets en hun inhoud zijn daarna gecontroleerd. HACS-installatie en werkelijk geladen backend/kaart `1.0.0-beta.43` zijn bevestigd. De fysieke liveacceptatie blijft afzonderlijk en is nog niet volledig afgerond.

De volgende beta.42- en eerdere vervolgresultaten zijn gedateerde ontwikkelingshistorie:
Beta.42 is op 2 oktober 2026 softwarematig releaseklaar gemaakt. De definitieve samengevoegde Python-regressiesuite is groen met **1472 geslaagde tests in 8.88 s**. Alle elf browsercontroles, actuele-uitlegcontrole (hash `813423dab59557a1`), handoff, repositoryvalidatie en publieke preflight zijn groen. De GitHub-publicatieworkflow en beide releasepakketten zijn onafhankelijk gecontroleerd. Beta.42 is daarna via de exacte HACS-tag geïnstalleerd en werkelijk als backend én kaart op Core 2026.9.4 bevestigd. Het AEG-profiel en de leerdata zijn behouden. De gezamenlijke Voorrang, startvoorwaarden en opgeslagen start-/stopredenen zijn live gecontroleerd. Handmatig boilerovernemen en Hervat zijn in Pauze gecontroleerd: de handmatige bescherming verdween, de toesteltemperatuur bleef 50 °C en de boilerregeling is opnieuw ingeschakeld. Automatisch regelen is hersteld. Er is geen live leerreset uitgevoerd: bestaande leerdata zijn bewust behouden. Op 2 oktober is vervolgens één echte automatische AEG-start met Running-terugmelding, verbruikte APP-aanvraag en opgeslagen startreden bevestigd. Het volledige cyclus-einde en een actieve koelcyclus zijn nog niet fysiek geaccepteerd.

Gerichte regressiedekking is toegevoegd of uitgebreid voor:

- DHW-Hervat uitsluitend buiten Automatisch regelen en zonder pending opdracht, zonder temperatuurwrite;
- eerlijke effectieve Voorrang onder/boven Auto laden met behoud van de opgeslagen keuze;
- begrensde leerreset met behoud van configuratie, bootstrap, operationele klimaatstate en andere modellen;
- gecorrigeerde interface-/hulpteksten in beide talen en de gegenereerde optiehulp;
- behoud van de beta.41-klimaat-/DHW-eigendomsgrenzen;
- bestaande beta.40-AEG-recovery en Wallbox fail-closed gedrag.

Werkelijke aantallen en alle releasecontroles worden uitsluitend na uitvoering vastgelegd in `docs/TESTRESULTATEN_BETA42.md`; de huidige 1472/8,88 s is het werkelijk uitgevoerde Python-resultaat, geen afleiding.

De huidige, nog niet uitgebrachte vervolgcode is afzonderlijk gecontroleerd: **1627 geslaagde Python-tests in 10.05 s** en **veertien geslaagde browsercontroles**, inclusief nieuwe vermogensuitleg, actieve toestellen/voordeel/Wallbox-geschiedenis en terugnavigatie bij 320/390/768/1440 px. Actuele-uitlegcontrole (nog de geregistreerde beta.42-uitleg), handoff, repositoryvalidatie, publieke preflight en diffcontrole zijn groen. De browserproeven gebruiken uitsluitend fictieve gegevens en versturen geen fysieke opdrachten. Dit is geen nieuwe beta.42-release of bewijs van een volledig afgeronde fysieke afwascyclus. De eerder gemeten 1486 tests/twaalf browserproeven betroffen alleen de eerdere startdiagnostiek, niet deze uitgebreidere bronboom.

## 10. Bekende problemen / beperkingen
- De bouwomgeving bevat geen echte hardware. Afzonderlijk is in de werkelijk geïnstalleerde Home Assistant één automatische AEG-start met native Running-terugmelding en opgeslagen startreden bevestigd. End Of Cycle en de uiteindelijke stopreden moeten bij deze lopende beurt nog worden bevestigd; geen tweede belading of START forceren.
- Zonder exclusieve afwasmachinemeter blijft het elektrische programma-/faseprofiel conservatief geschat; geen fictieve meetdata toevoegen.
- Een incomplete/ambigue AEG-mapping wordt bewust niet automatisch hersteld. `dishwasher_setup` meldt dit en vereist dan handmatige controle.
- Een handmatig gekoppelde alarmbron blijft bewust fail-closed volgens de gekozen configuratie; beta.39 verwijdert alleen de specifieke onbewezen bron die beta.38 automatisch koos.
- De beta.40-retry stopt na tien minuten. Wanneer de onderliggende template-/AEG-integratie nog later beschikbaar wordt, moet die oorzaak eerst worden hersteld en een nieuwe Home Assistant-start een nieuw begrensd venster openen.
- Klimaatrespons, koelrespons en reactievertraging kunnen niet uit code worden afgeleid. Bij onvoldoende echte cycli blijft modelzekerheid laag en gebruikt SolarPilot de zichtbare conservatieve fallback; dit is geen reden om comfortgrenzen te verruimen.
- De fysieke koelroute en onmiddellijke DHW-terugval tijdens een echte actieve koelcyclus zijn nog niet live bewezen.
- De gestopte én zonne-auto Wallbox-bronversheid zijn live bevestigd. Bij slechts 6 W vrije injectie telde SolarPilot 2,38 kW voorwaardelijk zonnevermogen uit autoladen mee en begon de gewone stabiliteitswachttijd; vervolgens startte de AEG automatisch. De nieuwe afwasstatus en netto energiebalans zijn bevestigd, niet het exclusieve fasevermogen. Manuele laadovergangen moeten nog afzonderlijk worden gecontroleerd; geen backend-versheidsgrens versoepelen.
- Batterijbediening blijft zonder gekoppelde hardware en afzonderlijke globale/individuele/eigenaarschaptoestemming adviserend. Wallbox blijft read-only.

## 11. Concrete openstaande ontwikkeling
- Backend en kaart beta.43 zijn na HACS-installatie en herstart werkelijk geladen. De gerichte DHW-herstartcontrole staat nog open; SolarPilot blijft daarom **Alleen bekijken** en herstel van **Automatisch regelen** is nog niet geaccepteerd. Begrensde leerreset is softwarematig getest maar niet op de echte leerdata uitgevoerd.
- De gewijzigde Wallbox-sessiebron is na groene Home Assistant-configuratiecontrole/reload als actueel gestopt zonder EV-krediet en later als actueel zonne-auto met voorwaardelijk EV-krediet bevestigd. Doorloop later nog manueel plus versheid/heartbeat. Geen status afleiden uit alleen de Full Solar-select of netimport.
- De oude 60/50-boilerautomatiseringen zijn reeds uitgeschakeld; laat ze uit om gelijktijdige regelaars te voorkomen.
- De huidige AEG-beurt startte automatisch om 12:24 op 2 oktober. De gebruiker stond de noodzakelijke beta.43-herstart tijdens die cyclus uitdrukkelijk toe; daarna rapporteerde de afwasmachine nog steeds `Running`. Volg later het echte End Of Cycle en de opgeslagen stopreden. Geen nieuwe APP-aanvraag maken en geen START herhalen.
- Later eventueel exclusieve Shelly-vermogensmeting van de afwasmachine gebruiken voor gemeten programmafasen/planning; tot dan geen faseprofiel verzinnen.
- Thermisch model, PV-kalibratie en faseprofielen uitsluitend uit voldoende echte meetdagen/cycli verder laten leren; geen ontbrekend bewijs kunstmatig invullen.
- Overige toekomstige SolarPilot-uitbreidingen alleen verderzetten vanaf de exacte gepubliceerde beta.43-tag en deze overdracht; behandel ontbrekende externe Library-registratie niet als bewijs van een andere bronversie.

### Historie vóór beta.43: live AEG-herstel en toen nog niet uitgebrachte uitleg — 2 oktober 2026
- De APP-aanvraag bestond al en bleef behouden. De blokkering ontstond door de ouder dan vijf minuten geworden verbindingsterugmelding van de eventgestuurde native koppeling, niet door ontbrekende APP-toestemming of het opnieuw verdwijnen van het profiel.
- De werkelijk geïnstalleerde native coordinator is in Home Assistant gelezen en bevestigd als cloud-push zonder periodieke opvraag. Een gewone `homeassistant.update_entity`-actie vraagt via die coordinator de echte cloudstatus op. Geen START, programmawijziging, APP-vrijgave of fysieke Wallbox-opdracht is hiervoor verstuurd.
- Een normale Home Assistant-automatisering is opgeslagen en ingeschakeld. Zij vraagt om de twee minuten de echte status op zolang start op afstand aanstaat, een cyclus actief is of de verbinding onbekend/onbeschikbaar is. Hiermee kan de cloudbron ook na een storing herstellen. De eerste gecontroleerde tijdtrigger om 12:28 werd binnen 0,48 s voltooid. Er is geen native integratiecode gepatcht en geen nepheartbeat toegevoegd. De installatie-specifieke configuratie blijft buiten de publieke bron.
- De oorspronkelijke APP-aanvraag is vervolgens volgens de bestaande regels automatisch gebruikt. Om 12:24 startte Eco; native Running, een verbruikte aanvraag en de balanscontrole zijn bevestigd. De geschiedenis bevat één start en nog geen stop, met de startreden: "Afwasmachine vóór Wallbox; autonoom terugregelen, tijdelijke netafname mogelijk". De cyclus liep bij de laatste controle nog. Zonder eigen meter blijft het getoonde toestelvermogen een schatting.
- Lokale vervolgcode maakt de vermogensuitleg nauwkeurig: vrije zonnestroom na huisreserve, voorwaardelijk beschikbaar zonnevermogen uit autoladen, eventueel veilig vrij te maken lagere lasten en het door de echte PV-opbrengst begrensde totaal. Ook een nog onvoldoende totaal is zichtbaar, zonder reeds vermogensovername toe te kennen of een start te garanderen. Een ontvangen APP-aanvraag heet niet meer ten onrechte ontbrekend als alleen de status te oud is. Een lopend toestel toont geen misleidende startchecklist voor een volgende beurt.
- Deze vervolgcode en de twaalfde browsercontrole zijn getest maar nog niet gepubliceerd, geregistreerd of geïnstalleerd. Live blijft beta.42; de huidige afwasbeurt heeft geen herstart of geforceerde bediening gekregen. Werk voor de volgende echte release eerst versienummer, actuele gebruikersuitleg, changelog, installatie/rollback en testverslag samen bij en registreer nieuwe pakketten onder een nieuw versienummer.

### Versienummers en logo: eerdere wens en actuele status — 2 oktober 2026
- De eerdere live update-entiteit meldde geïnstalleerd `v1.0.0-beta.42` en beschikbaar `403c3f0`; die laatste wijziging corrigeerde uitsluitend één route in de handleiding, geen ontbrekende SolarPilot-code. Voor de echte beta.43-update is alleen de ondersteunde SolarPilot Pre-release-entiteit ingeschakeld en op **Pre-releases preferred** gezet. Daarna bood HACS werkelijk `v1.0.0-beta.43` aan en bevestigde het na installatie **Up-to-date** met geïnstalleerd én beschikbaar beta.43. Andere repositories en toegangsrechten zijn niet gewijzigd. Behoud deze bewuste beta-kanaalkeuze; markeer een beta niet als stabiel om alleen de weergave te veranderen.
- Toon het bestaande SolarPilot-logo bij de integratie en de HACS-updatekaart. De vier correcte lokale `brand/`-PNG's bestaan al en zijn meegeleverd. Home Assistant ondersteunt deze lokale integratiebranding, maar de HACS-update-entiteit verwijst aantoonbaar naar het oude publieke brands-adres. De definitieve upstream oplossing is de nog open HACS PR `https://github.com/hacs/integration/pull/5524`: gebruik van de lokale Home Assistant brands-proxy. Het centrale brands-register accepteert geen nieuwe custom-integratiebeelden meer; vraag daar dus geen zinloze registratie aan. Voor de updatekaart is een HACS-versie met die fix nodig, of een bewust toegepaste, ondersteunde lokale `entity_picture`-aanpassing via Home Assistant-customisatie. Geen HACS-codepatch, verborgen globale frontend-aanpassing of verzonnen manifest/hacs-brandkey. Beloof geen werkend HACS-logo voordat de gekozen route daadwerkelijk is getest. Publiceer of installeer geen onuitgebrachte HACS-code als normale SolarPilot-update.
- Beta.43 is inmiddels gepubliceerd en toont na installatie het semantische versienummer. Het lokale SolarPilot-merkbeeld is op de Home Assistant-integratiepagina zichtbaar. Het HACS-updatevenster toont het logo nog niet, doordat HACS daar de centrale brands-CDN gebruikt. De HACS-kanaalvoorkeur is zoals hierboven beschreven wél gewijzigd; de lokale Home Assistant-`entity_picture`-customisatie is nog niet toegepast. Het updatekaartlogo vereist nog zo'n ondersteunde customisatie of upstream HACS-ondersteuning; dit lost niet automatisch ook het afzonderlijke HACS-repositoryoverzicht op.

### Historie vóór beta.43: geteste vervolgcode en toenmalige live basis — 2 oktober 2026
- Overzicht toont daadwerkelijk actieve, beschikbare verbruikers, AEG-programma/fase en de werkelijk gemeten Wallbox. Alle actieve kaarten volgen dezelfde accentkleur/rand en hebben een duidelijke status. Geschat vermogen is zichtbaar onderscheiden van gemeten vermogen, ook bij expliciete estimated/is_estimated/restored-metadatavlaggen of een als geschat benoemde bron; oude/onbeschikbare bronnen worden niet als actief bevestigd. Dit verandert geen bestaande actuator- of meterrechten. Een hoge boilertemperatuur of ingeschakelde regeling wordt niet als bewijs van een draaiende warmtepomp gepresenteerd.
- Instellingen heeft een zichtbare Terug-knop. Browser-/muis-Terug volgt formulier → categorie → hoofdmenu → SolarPilot; geneste vensters sluiten eerst. Niet-opgeslagen wijzigingen vereisen bevestiging, een lopende opslag blokkeert teruggaan. Vooruit heropent uitsluitend veilige menu's en herhaalt geen oude formulierinvoer, opslag of fysieke opdracht. Bestaande Home Assistant-historie blijft behouden; telemetry-updates voegen geen stappen toe.
- `savings.py` bewaart maximaal 90 gemeten dagen met een afzonderlijke automatische telling: uitsluitend eigen, actieve Auto-verbruikers, zonder handmatige start/boost, en uitsluitend geldige korte meetintervallen. Prijsverschil wordt per interval toegepast; ontbrekende PV/prijzen, herstartgaten en oude perioden worden niet gereconstrueerd. Dashboard toont Vandaag, bewaarde periode, meetkwaliteit en berekening. De bredere bestaande EMS-telling blijft apart, omdat die ook handmatige bediening kan bevatten. Dit is geschat zonnevoordeel tegenover netafname/injectie, geen bewezen extra besparing door SolarPilot. Autonoom autoladen, DHW en klimaat zijn niet in dit eurobedrag opgenomen; trek het bedrag niet opnieuw van de bestaande netkost af.
- `wallbox_activity.py` leest bestaande native berichten, zonder netwerkopvraag of Wallbox-opdracht. De actuele fabrikantstatus verklaart bijvoorbeeld wachten op zonnestroom, eigen laadschema of vraag van de auto. De SolarPilot-verdelingsregel staat afzonderlijk, niet als automatisch bewezen fysieke stopoorzaak. Een historische fabrikantreden vereist de aparte statustijd na het laatste laadrapport en maximaal vijf seconden van het stopvermogensrapport; een oudere of ontbrekende statustijd blijft oorzaak niet bevestigd. Laatste laadstop blijft bewaard na hervatten en in maximaal 30 laadperioden. Een ontbrekende oorzaak heet onbekend; een herstart, oude meting of lange onderbreking heet einde niet bevestigd. Eerste controle met nul vermogen verzint geen eerdere stop. Herstelde onlogische/toekomstige tijdankers mogen geen toekomstige waarnemingen blokkeren of een fictieve laadperiode maken. Tijdstippen zijn HA-waarnemingen, geen exact fysiek meetmoment. Opstart leest eerst bestaande opslag voordat deze recorder gegevens mag bewaren.
- De laatste live controle in deze werkfase bleef beta.42: Wallbox laadde werkelijk circa 3,85 kW met negen seconden oude bronrapportage; de AEG was nog Eco/Running, circa 62 minuten actief. Geen herstart, geforceerde START, APP-herarming of fysieke Wallbox-opdracht is uitgevoerd. Alle nieuwe schermbewijzen gebruiken fictieve gegevens en tonen niet de geïnstalleerde Home Assistant.

### Expliciete gebruikerswijziging: maandag uiterlijk 10:00 starten
- Nieuwe optionele sleutel `dishwasher_monday_start_deadline` valt bij een lege waarde terug op `dishwasher_start_deadline`. Voor deze installatie is maandag **10:00:00** gevraagd; de gewone deadline blijft **13:00:00** voor de overige dagen. Dit is geen universele standaard voor andere installaties en de live waarde is na de beta.43-installatie nog niet toegepast en bevestigd.
- Verzoeken vóór de maandaggrens plannen maandag 10:00; de bestaande morgenregel kiest na die grens dinsdag met diens gewone deadline. Een zondags verzoek na de gewone deadline kiest maandag 10:00. Kalenderdag en zomertijd worden gerespecteerd. Bestaande absolute aanvragen worden niet bij upgrade stilzwijgend vervroegd; uitsluitend de expliciete keuze om het huidige verzoek aan te passen herberekent de deadline van dezelfde plandag. Geen nieuwe APP-aanvraag, herarming, datumverschuiving of START. Een lopend toestel stelt configuratiewijziging uit tot bevestigd cycluseinde; toestemming voor netstroom blijft de bestaande voorwaarde.
- Historisch kende beta.42 dit veld nog niet. Beta.43 met het veld is nu werkelijk geladen, maar de installatiekeuze maandag 10:00 is nog niet live toegepast en bevestigd. Sla die buiten de beschermde cyclus via de normale gevalideerde toestelinstellingen op. Alleen wanneer er dan nog een klaargezette APP-aanvraag bestaat, vraagt de wizard om een bereik; kies voor uitsluitend toekomstige planning **Alleen volgende beurten; huidige aanvraag blijft ongewijzigd**. Zonder zo'n aanvraag verschijnt die bereikvraag niet. De fabrikantsterilisatie blijft ongewijzigd en beschermd; vroeger starten garandeert op zichzelf niet dat ieder programma vóór de sterilisatie klaar is.
- De bestaande NAS-verbinding is op 2 oktober opnieuw verbonden. Home Assistant toont de schijfcapaciteit weer en de netwerkopslagreparatie is verdwenen. Netwerkopslag op de NAS is door de gebruiker uitdrukkelijk toegestaan; geen NAS-aanmeldgegevens of private adressen in publieke bron opnemen.

## 12. Installatie/upgrade en rollback
Zie `docs/BETA43_INSTELLEN.md`.

Uitgevoerd: Home Assistant-back-up op de bestaande NAS → exacte beta.43-tag via HACS geïnstalleerd → expliciete toestemming voor de herstart tijdens de beschermde cyclus → backendversie én kaartversie `1.0.0-beta.43` bevestigd. Nog open: gerichte DHW-herstartcontrole afronden, daarna pas **Automatisch regelen** herstellen; actieve toestellen, Wallbox-uitleg, veilige Terug-navigatie, Voorrang/avondvoorraad en voordeel verder live accepteren; maandagdeadline bewust op 10:00 opslaan en bevestigen. Geen APP-herarming, proefstart, leerreset of Wallbox-opdracht gebruiken om deze acceptatie af te dwingen.

Rollback: SolarPilot Pauze → lopende beschermde cyclus laten afwerken → geregistreerde beta.42/back-up herstellen → HA herstart → centrale prioriteit, toestelconfiguratie, klimaat-eigendom en DHW-eigendom opnieuw verifiëren. Nooit een lopende afwasbeurt met STOPRESET vanuit SolarPilot beëindigen.

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
- `custom_components/solar_pilot/wallbox_activity.py`: begrensde waarnemingshistoriek zonder onbewezen stopoorzaken.
- `custom_components/solar_pilot/savings.py`: afzonderlijke 90-dagenregistratie van geschat automatisch zonnevoordeel, geen bewezen extra besparing.
- `CHANGELOG.md`, `docs/BETA43_INSTELLEN.md`, `docs/TESTRESULTATEN_BETA43.md`.

## 14. Release-checklist
1. CURRENT/overdracht lezen en juiste basis bevestigen.
2. Manifest/const/current guide exact dezelfde versie.
3. Volledige tests groen.
4. Publieke preflight groen op schone bronboom.
5. Actuele uitleg + option-help opnieuw genereren.
6. Changelog + installatie/rollback + testverslag + OVERDRACHT actualiseren.
7. Geen caches/private data in pakket.
8. Release-zip bouwen + checksum vastleggen.
9. De externe projectregistratie naar beta.43 bijwerken zodra de Library weer toegankelijk is; tot dan eerlijk vastleggen dat `CURRENT.json`, `LATEST.zip` en `PROJECT_INDEX.json` niet zijn bijgewerkt en geen lokale schijnregistratie maken.
10. De gecontroleerde beta.43-commit/tag/release is gepubliceerd en geïnstalleerd. Bestaande tag en assets blijven onveranderlijk; vervolgcorrecties vereisen een nieuwe versie.

## 15. AI-handoff
Start bij de exacte gepubliceerde beta.43-tag en deze `OVERDRACHT.md` zolang de externe Library niet toegankelijk en bijgewerkt is; kies nooit een versie enkel omdat die later op GitHub of in een bestandsnaam staat. Beta.43 bouwt voort op de werkelijk gecontroleerde beta.42 en de hierboven beschreven vervolgfuncties. Beta.40 blijft de bron van de begrensde post-start AEG-recovery. Behoud alle veiligheidsgrenzen en lees publicatie, installatie op schijf, werkelijk geladen backend/kaart en fysieke acceptatie als afzonderlijke feiten.

De normale Home Assistant-statusopvraagautomatisering houdt de echte native AEG-bron tijdens aanvragen/cycli actueel. De huidige beurt is automatisch gestart en beschermd; na de uitdrukkelijk toegestane beta.43-herstart rapporteerde zij nog steeds `Running`, maar End Of Cycle en de uiteindelijke stopreden zijn nog niet opnieuw bevestigd. De softwaregate, publicatie, pakketten, HACS-installatie en geladen backend/kaart zijn afgerond. Open blijven de gerichte DHW-review vóór herstel van **Automatisch regelen**, live toepassing/bevestiging van maandag uiterlijk 10:00 (overige dagen 13:00), verdere fysieke acceptatie en de externe Library-registratie. Geen fysieke proefopdrachten gebruiken om diagnosevelden te vullen.
