<!-- solarpilot-handoff-schema: 1 -->
<!-- solarpilot-handoff-version: 1.0.0-beta.37 -->

# SolarPilot · Overdrachtsdossier

**Actuele productieversie:** `1.0.0-beta.37`  
**Status:** publieke HACS-beta, actuele codebasis = `main`  
**Laatst inhoudelijk gecontroleerd:** 2026-10-01  
**Minimale Home Assistant-versie:** 2026.9.0  
**Repository:** `Stevenva007/solarpilot-home-assistant`  
**Integratiedomein:** `solar_pilot`

Dit bestand is het technische overdrachtsdossier van de **huidige** SolarPilot-toestand. Het is geen changelog en geen archief van oude logica. Historische wijzigingen horen in `CHANGELOG.md`; gebruikersuitleg hoort in `docs/ACTUELE_WERKING.md`.

## AI-handoff

> **Instructie voor een nieuwe ChatGPT-chat of ontwikkelaar**
>
> Lees dit bestand eerst en behandel het samen met de actuele code op `main` als de technische uitgangssituatie. Gebruik oude gesprekken, oude ZIP-bestanden en oudere beta-documentatie nooit als bron voor de huidige werking wanneer die hiermee in tegenspraak zijn.
>
> Controleer vóór een wijziging de versie in `custom_components/solar_pilot/manifest.json`, `const.py` en `docs/ACTUELE_WERKING.md`. Behoud bestaande werkende functies, gebruikersinstellingen, leerdata, prioriteiten en expliciete bedieningsrechten tenzij de wijziging bewust een betere centrale implementatie introduceert.
>
> Iedere functionele codewijziging moet in dezelfde wijziging ook dit `OVERDRACHT.md` opnieuw inhoudelijk controleren en zo nodig aanpassen. Een release is niet compleet zolang code, migratie, tests, actuele gebruikersuitleg, changelog, dit overdrachtsdossier en rollback-informatie niet met elkaar overeenkomen.

**Belangrijk:** dit dossier bevat bewust geen privé-entiteitsnamen, adressen, tokens, exports of andere installatiegeheimen. Installatiespecifieke koppelingen blijven in Home Assistant of in het lokale private bundle.

## 1. Projectstatus

SolarPilot is een lokaal Home Assistant Energy Management System voor:

- realtime PV-overschot en netbalans;
- centrale voorrang van flexibele verbruikers;
- Wallbox-samenwerking zonder de Wallbox rechtstreeks te besturen;
- Panasonic Aquarea tapwaterbeleid en conservatieve warmtepompanalyse;
- AEG/Electrolux afwasmachine-startlogica;
- fasebelasting en capaciteitstariefbewaking;
- PV-voorspelling en lokale kalibratie;
- thermisch leren en klimaatadvies;
- dagkosten en plannerkwaliteit;
- verbruikershistoriek en analyse-export;
- toekomstige batterijplanning en optionele batterijbesturing.

De integratie is `single_config_entry`, gebruikt geen externe Python-runtimevereisten en exposeert native Home Assistant-entiteiten via sensor, binary_sensor, select, number, button en switch.

De dashboardmodus **Alleen bekijken** (`observe`) blijft de veilige observatiestand. Beta.37 activeert éénmalig beschikbare leer- en regelmodules waarvoor de bestaande koppelingen en vereiste bevestigingen al aanwezig zijn; nieuwe fysieke toestelrechten, ontbrekende bronnen en veiligheidsbevestigingen worden nooit verzonnen.

## 2. Bronnen van waarheid

Gebruik deze volgorde wanneer bronnen elkaar tegenspreken:

1. **Actuele code op `main`** en de persistente configuratiemigratie.
2. **`OVERDRACHT.md`** — technische overdracht, architectuur en vaste ontwikkelregels.
3. **`docs/ACTUELE_WERKING.md`** — enige actuele gebruikersuitleg voor de release; wordt gegenereerd vanuit `custom_components/solar_pilot/current_guide.py`.
4. **`CHANGELOG.md`** — historische wijzigingen per release.
5. **`README.md`** en instelhandleidingen — installatie, releasecontext en specifieke configuratiehulp.
6. Oudere beta-documenten en oude chats — alleen historische context, nooit automatisch actuele logica.

De actuele gebruikersuitleg moet bij iedere gedragswijziging samen met de code worden vernieuwd. De GitHub-controle `tools/check_current_explanation.py` bewaakt versie en gegenereerde uitleg.

## 3. Niet-onderhandelbare ontwerpregels

### Veiligheid en eigenaarschap

- Realtime P1/PV-metingen, apparaatvoorwaarden en beveiligingen gaan altijd vóór voorspellingen, planners en aangeleerde modellen.
- Eén actuator heeft maar één eigenaar.
- SolarPilot is geen elektrische beveiliging en mag zekeringen, fabrikantbeveiligingen of installatiebeveiliging nooit vervangen.
- Onzekere fysieke opdrachten worden niet blind of eindeloos herhaald.
- Na Home Assistant/SolarPilot-herstart wordt eerst de **werkelijke toesteltoestand** gereconcilieerd voordat regeling verdergaat.
- Nieuwe fysieke koppelingen of rechten worden nooit stilzwijgend geactiveerd.

### Bestaande gebruikersconfiguratie behouden

- Upgrades moeten bestaande entity-koppelingen, prijzen, apparaten, rechten, bevestigingen, plannerinstellingen, Wallbox-keuzes, prioriteiten en bruikbare leerdata behouden.
- Een migratie mag alleen het specifieke incompatibele model resetten wanneer daar technisch een aantoonbare reden voor is; geen brede reset als makkelijkste oplossing.
- De centrale prioriteitenlijst is na de beta.35→beta.36-migratie de leidende bron. Bestaande effectieve volgorde moet behouden blijven.
- Een nieuwe verbruiker wordt toegevoegd zonder automatisch nieuwe startrechten te krijgen en komt standaard onderaan de centrale flexibele voorrangslijst.

### Gebruiksvriendelijkheid

- Benamingen moeten begrijpelijk zijn voor niet-technische gebruikers.
- Alle gewone voorrangsregels horen samen in één centrale **Voorrang**-weergave.
- De gebruiker moet verbruikers kunnen verplaatsen in de prioriteitenvolgorde.
- Per relevante verbruiker is apart zichtbaar/instelbaar of deze zonnevermogen van een bevestigde Wallbox-zonnelaadsessie mag benutten. Die toestemming is alleen actief wanneer het toestel ook boven de Wallbox staat.
- **Export** heeft één hoofdactie voor een compleet analysebestand met instellingen, metingen, beslissingen, leerresultaten en fouten; aanvullende exportopties blijven ondergeschikt.
- Telemetrieverversing mag open pop-ups en configuratiecontext niet onnodig sluiten of resetten.
- Iedere gebruikersoptie moet uitlegbaar zijn via de bestaande hulpstructuur.

### Documentatie als release-eis

Een codewijziging die gedrag, configuratie, migratie of gebruikersinterface beïnvloedt is niet klaar voordat ook:

- `current_guide.py` en de gegenereerde `ACTUELE_WERKING.md` actueel zijn;
- `CHANGELOG.md` de releasewijziging correct beschrijft;
- dit `OVERDRACHT.md` de nieuwe huidige toestand beschrijft;
- tests en releasecontrole zijn aangepast waar nodig.

## 4. Huidige functionele toestand

### 4.1 Modi en realtime regeling

SolarPilot kent de modi `observe`, `solar` en `paused`.

- **Alleen bekijken (`observe`):** berekenen en leren, zonder gewone flexibele verbruikers fysiek te sturen.
- **Automatisch regelen (`solar`):** toegestane realtime regeling uitvoeren.
- **Pauze:** niets nieuws starten en eigen onderbreekbare lasten veilig afbouwen, met behoud van minimumlooptijden en beschermde cycli.

Er wordt maximaal één gewone fysieke wijziging tegelijk uitgevoerd; daarna wordt op terugmelding en nieuwe meetinformatie gewacht.

### 4.2 Centrale prioriteiten

Boven de verplaatsbare lijst blijven beschermd:

1. elektrische/fabrikantbeveiligingen en Panasonic-sterilisatie;
2. noodzakelijk warmwatercomfort;
3. noodzakelijk ruimtecomfort.

Daarna is de centrale gebruikersvolgorde leidend. Bij de beta.36-migratie wordt de voordien effectieve volgorde bewaard. De afgesproken referentievolgorde voor de huidige installatie is **AEG-afwasmachine → Wallbox → ontvochtiger → extra warm water tot 60 °C** wanneer het AEG-profiel aanwezig is. Zonder AEG begint de flexibele volgorde bij de Wallbox. De upgrade herschikt een reeds opgeslagen beta.36-volgorde niet.

Een reeds gestarte beschermde cyclus, zoals een afwasprogramma, wordt niet afgebroken om een hogere prioriteit vrij te maken. Voor zulke routes blijven de specifieke beschermingsregels gelden.

Een generiek toestel mag alleen zonnevermogen dat de Wallbox op dat moment gebruikt benutten wanneer het **boven Auto laden (Wallbox)** staat én de expliciete toestemming daarvoor aan staat. Onder de Wallbox blijft die toestemming opgeslagen maar inactief. Nieuwe gewone flexibele toestellen komen onderaan totdat de gebruiker ze bewust verplaatst.

### 4.3 Beta.37 automatische activering

Bij de eerste start van beta.37 wordt éénmalig een startprofiel toegepast:

- analyse-export, planner, basislastleren, lokaal PV-leren, Forecast.Solar-kalibratie en batterij-what-if worden actief;
- fasebewaking/-leren wordt actief wanneer L1/L2/L3 al gekoppeld zijn; nieuwe starts mogen dan de bevestigde fasegrenzen respecteren, maar lopende lasten worden niet automatisch afgeworpen;
- Wallbox-monitoring wordt actief wanneer een laadvermogensbron al gekoppeld is;
- slim klimaatmodel wordt actief bij gekoppelde zones; fysieke AUTO/OFF-regeling wordt alleen geactiveerd wanneer alle gekoppelde zones daadwerkelijk AUTO en OFF ondersteunen;
- DHW-regeling wordt alleen actief wanneer doel-, temperatuursensor én de bestaande veiligheidsbevestiging aanwezig zijn;
- apparaten met een afzonderlijke eigen vermogensmeter mogen hun cyclusprofiel leren;
- Leren & vragen gebruikt gemeten sampling, begrensde automatische adaptatie en meldingen.

De migratie heeft een persistente eenmalige marker. Latere handmatige uitschakelingen of beleidskeuzes worden bij een volgende herstart niet opnieuw overschreven. Een bestaand toestel wordt door deze migratie niet van Uitgesloten naar Auto gezet en fysieke batterijbesturing krijgt geen nieuw eigenaarschap.

De positie ten opzichte van de Wallbox en de toestemming **Mag de auto minder laten laden?** zijn twee afzonderlijke zaken. Een hogere positie alleen geeft geen recht op EV-vermogen.

### 4.3 Wallbox

De Wallbox Pulsar Max blijft vanuit SolarPilot **read-only**:

- geen start/stop/pauze/hervat-opdracht;
- geen laadstroom- of faseopdracht;
- geen wijziging van Full Solar door SolarPilot.

SolarPilot onderscheidt ingestelde modus, werkelijk gedetecteerde sessie, laadvermogen en actuele toestemming om zonnelaadvermogen indirect te laten teruglopen doordat een hogere eigen belasting wordt gestart.

Wallbox-vermogen mag alleen conditioneel worden meegenomen wanneer een effectieve zonnelaadsessie voldoende betrouwbaar bevestigd is. Manueel, onbekend of verouderd laden levert geen overneembaar EV-vermogen op. EV-vermogen telt nooit als extra fysieke net- of fasecapaciteit.

Het huidige terugvalprofiel is 1 fase / 25 A; het afzonderlijke Full Solar-minimum is ongeveer 1.380 W. Deze waarden blijven configureerbaar en mogen later niet als vaste hardwarewaarheid worden behandeld wanneer de installatie wijzigt.

### 4.4 Sanitair warm water / Panasonic Aquarea

De actuele centrale DHW-regelset gebruikt één persistente configuratiebron.

Huidige referentiewaarden:

- normaal tankdoel: **50 °C**;
- bewaakte comfortgrens: **46 °C**;
- fysieke Panasonic heropwarmdifferentie: **-5 °C**;
- gewoon zonnedoel: **50 °C**;
- extra PV-buffer: **60 °C**;
- maximum voor extra doelen bij actieve koeling: **50 °C**;
- Panasonic-sterilisatie: **62 °C**, fabrikantgestuurd en autonoom.

De 46 °C is een bewaakte comfortgrens, geen gegarandeerde fysieke ondergrens. Met 50 °C doel en -5 °C native differentie kan Panasonic nominaal pas rond 45 °C opnieuw starten.

SolarPilot stuurt geen Force DHW, Powerful, compressor, hoofdvoeding of HEAT/COOL-modus om deze grens kunstmatig af te dwingen.

De optionele ochtendcontrole gebruikt standaard 09:00 en 46 °C. Een optionele avondvoorraad kan uit zonne-energie worden gepland en is standaard begrensd op 55 °C. Extra 60 °C blijft luxe-opwarming uit echte resterende zonne-ruimte, niet uit virtueel EV-vermogen.

Panasonic kiest zelf HEAT versus COOL en behoudt autonome sterilisatie.

### 4.5 Warmtepomp- en klimaatleren

Beta.36 onderscheidt warmtepompactiviteit als gewone huishoudlast, ruimteverwarming, ruimtekoeling, tapwater, sterilisatie of onbekende warmtepompactiviteit.

Zonder aparte elektrische warmtepompmeter mag SolarPilot alleen een conservatieve planningsschatting leren uit stabiele P1+PV-veranderingen. Die schatting:

- mag basislastleren verbeteren;
- mag de planner informeren;
- mag **nooit** realtime elektrische ruimte creëren of een fysieke grens versoepelen.

Klimaatbetrouwbaarheid wordt afzonderlijk bijgehouden voor passieve drift, zonnewinst, verwarmingsrespons, koelrespons, reactievertraging, weerscorrectie en coast/off-feedback. Ontbrekende onderdelen mogen geen kunstmatige totaalscore van 100% veroorzaken.

### 4.6 AEG/Electrolux afwasmachine

De AEG-route is **start-only**:

- starten via de native AEG START-mogelijkheid;
- Remote Control moet werkelijk geldig/vrijgegeven zijn;
- geen plugrelais gebruiken als programmastart;
- geen STOP/RESET, PAUSE of RESUME door SolarPilot;
- maximaal één start per klaarzetaanvraag;
- geen blinde retry na een onzekere opdracht.

De APP-/deadline-logica plant vóór 13:00 standaard voor dezelfde dag en op/na 13:00 standaard voor de volgende kalenderdag. Expliciete nettoestemming op de geplande deadline kan bestaan, maar mag elektrische of apparaatvoorwaarden niet omzeilen.

Een lopende cyclus blijft beschermd. End Of Cycle wordt event-driven bewaard; Off/Unavailable/Disconnected of AirDry geldt niet automatisch als bewezen einde.

Volledige fasegewijze afwasoptimalisatie wacht op een betrouwbare exclusieve vermogensmeting; zonder zo'n meter worden onbekende fasen niet verzonnen.

### 4.7 PV-voorspelling en lokale kalibratie

Forecast.Solar kan als basisvoorspelling dienen, maar realtime P1/PV blijft leidend.

Huidig referentieprofiel:

- panelen: **13,8 kWp**;
- AC-omvormerlimiet: **10,0 kW**;
- minimaal vijf geldige vergelijkbare dagen voor normale lokale kalibratie;
- clipping, wolken/outliers en startupperioden worden uit structureel schaduwleren gehouden;
- lokale afwijkingen worden per zonnestand/seizoen geleerd;
- ontbrekende toekomstdekking blijft onbekend en wordt niet als 0 W behandeld.

Planberekeningen tellen nooit als extra leerdag.

### 4.8 Planner, fasebeheer en batterij

De Unified Planner gebruikt standaard:

- rolling horizon: **36 uur**;
- resolutie: **15 minuten**;
- alleen het huidige blok kan de realtime regelaar beïnvloeden.

De planner combineert voorspelde PV, geleerd basisverbruik, prijzen, kwartierpiek, flexibele lasten en toekomstige batterijruimte. Realtime regels en beschermingen blijven hoger in rang.

Faseherkenning maakt onderscheid tussen geleerd, betrouwbaar genoeg voor advies en expliciet vrijgegeven voor regeling. Geen fasecontrole op basis van onvoldoende bewijs.

Batterijfunctionaliteit is standaard adviserend/uitgeschakeld voor fysieke besturing en vereist expliciet eigenaarschap en toestemming.

### 4.9 Historiek, kosten en export

SolarPilot registreert lokaal begrensde verbruikerssessies met start-/stoptijden, duur en bevestigde reden waar die beschikbaar is.

De analyse-export gebruikt schema 2 en maakt onderscheid tussen:

- aangevraagde periode;
- beschikbare ruwe periode;
- werkelijk gedekte meettijd;
- meetgaten/offline tijd;
- herstarts;
- fast telemetry;
- bootstrapdata, live leerdata, berekende profielen en actuele metingen.

Een analyse-export is diagnostiek, geen Home Assistant-back-up en wordt niet automatisch geüpload.

## 5. Architectuur en belangrijke bestanden

| Bestand / module | Verantwoordelijkheid |
|---|---|
| `custom_components/solar_pilot/__init__.py` | Integratie-opstart, registratie en Home Assistant-lifecycle |
| `const.py` / `manifest.json` | Domein, versie, platforms en basisdefaults |
| `config_flow.py` | Installatie- en configuratieflows |
| `live_config.py` / `live_options.py` / `option_help.py` | Live configuratie, opties en begrijpelijke veldhulp |
| `runtime.py` / `engine.py` / `ems.py` | Realtime coördinatie en EMS-beslissingen |
| `priority_board.py` / `priority_api.py` | Centrale voorrangsbron en UI/API |
| `unified_planner.py` / `planner_quality.py` | 36-uursplanning, kwaliteit en replay/backtestbasis |
| `wallbox.py` / `wallbox_policy.py` / `wallbox_profile.py` / `consumer_wallbox.py` | Wallbox-detectie, read-only profiel en voorrang/reclaimregels |
| `dhw_config.py` / `dhw.py` / `dhw_runtime.py` / `dhw_schedule.py` | Centrale DHW-configuratie, beslissingen en planning |
| `heatpump_learning.py` | Classificatie en conservatief leren van warmtepompactiviteit |
| `thermal_climate.py` / `thermal_runtime.py` | Thermisch model en klimaatcontext |
| `dishwasher*.py` | AEG/Electrolux start-only adapter, APP/deadline en beschermde prioriteitslogica |
| `pv_forecast*.py` / `pv_calibration.py` / `pv_model.py` | Forecast.Solar-bron, lokale kalibratie en PV-model |
| `phase_learning.py` | Faseherkenning en betrouwbaarheidsstatus |
| `battery_*.py` | Batterijanalyse, vloot/runtime en beschermde toekomstige besturing |
| `consumer_history*.py` | Sessieregistratie en dagoverzicht |
| `electricity_cost.py` | Dagkosten en energieprijslogica |
| `analysis_export.py` / `analysis_api.py` / `diagnostics.py` | Analyse-export en diagnostiek |
| `learning*.py` | Centrale leerstatus, vragen en veilige modelupdates |
| `current_guide.py` | Canonieke bron voor de actuele gebruikersuitleg |
| `frontend/solar-pilot-card.js` | SolarPilot-dashboard/UI in Home Assistant |
| `tests/` | Software- en regressietests |
| `tools/` | Releasechecks, documentgeneratie, UI-checks en offline hulpmiddelen |

De actuele gebruikersuitleg bestaat zowel onder `docs/ACTUELE_WERKING.md` als ingebed in de integratie. Beide moeten uit dezelfde `current_guide.py` gegenereerd blijven.

## 6. Configuratie, migratie en persistente data

### Home Assistant-configuratie

- SolarPilot gebruikt één config entry.
- Programmacode wordt door HACS vervangen; configuratie en leerdata worden in Home Assistant opgeslagen.
- HACS bewaart de map `userfiles` als persistent directory.
- Een lokaal `custom_components/solar_pilot/userfiles/private_bundle.json` kan optioneel installatiespecifieke mappings en geaggregeerde bootstrapdata bevatten.
- Een private bundle mag nooit in de publieke repository terechtkomen.

### Migratie-eis

Bij iedere nieuwe release moet expliciet worden gecontroleerd dat bestaande installaties niet onnodig opnieuw moeten configureren.

Beta.36 bewaart onder meer:

- gekoppelde entiteiten;
- prijzen;
- Wallboxinstellingen;
- apparaten en profielen;
- leerdata;
- fase-/PV-/klimaat-/boilerdata;
- bevestigingen en fysieke rechten;
- centrale prioriteitsvolgorde.

Alleen incompatibele warmtepompleerdata mag specifiek worden gereset wanneer het model niet veilig naar de nieuwe classificatie kan worden vertaald.

### Herstart

Na herstart:

1. opgeslagen modus/configuratie laden;
2. echte toestelstatussen opnieuw lezen;
3. eigenaarschap en onzekere opdrachten reconciliëren;
4. alleen bij betrouwbare toestand automatisch verdergaan;
5. geen oude fysieke opdracht blind opnieuw uitvoeren.

## 7. Test- en releaseprocedure

### GitHub-validatie

`.github/workflows/validate.yml` draait automatisch alleen bij een push naar `main`, een pull request naar `main` en een handmatige start. Werkbranch-pushes, tags en een dagelijkse schedule starten bewust geen extra Validate-run, zodat ontwikkeling niet telkens nieuwe Actions-meldingen veroorzaakt. Na een groene Validate-run op de exacte releasecommit wordt de vaste branch `publish-release` naar diezelfde commit doorgeschoven. `.github/workflows/release.yml` voert daar opnieuw de releasechecks en volledige tests uit, maakt daarna de versie-tag uit `manifest.json`, bouwt het volledige GitHub/HACS-ZIP-pakket, voegt instelhandleiding en testverslag als assets toe en publiceert de prerelease. Een releasebranch mag nooit naar een andere commit wijzen dan de reeds gevalideerde `main`.

De repository-checks moeten minimaal uitvoeren:

1. publieke privacy-/structuurcontrole;
2. controle van dit overdrachtsdossier;
3. actuele gebruikersuitleg/version consistency;
4. installatie van testdependencies;
5. volledige `pytest`-suite;
6. Python `compileall`;
7. HACS-validatie;
8. Hassfest-validatie.

Het exacte aantal geslaagde tests wordt **niet** in dit dossier vastgepind; de actuele GitHub Actions-run is daarvoor de bron van waarheid. Daardoor veroudert het dossier niet alleen omdat er regressietests bijkomen.

### Lokale minimale controle

```bash
python tools/check_public_repository.py
python tools/check_handoff.py
python tools/check_current_explanation.py
python -m pytest -q -p no:cacheprovider
python -m compileall -q custom_components/solar_pilot
```

UI-specifieke checks in `tools/check_*.py` blijven behouden en moeten worden uitgebreid wanneer een relevante interfacefunctie wordt gewijzigd.

### Praktijktest

CI bestuurt geen echte thuisinstallatie. Voor een nieuwe functionele release:

- eerst in **Observatie**;
- bronwaarden en actualiteit controleren;
- migratie en bestaande koppelingen controleren;
- pas daarna fysieke rechten gefaseerd activeren;
- nooit meerdere nieuwe fysieke regelroutes tegelijk vrijgeven zonder afzonderlijke verificatie.

## 8. Installeren, upgraden en rollback

### Installeren/upgraden

Normale route:

1. SolarPilot als HACS Custom Repository van type Integration;
2. nieuwste release installeren/updaten;
3. Home Assistant herstarten;
4. migratie en bronstatus controleren;
5. eerst Observatie gebruiken na een grote regelwijziging.

Tussenliggende beta-versies hoeven niet één voor één te worden geïnstalleerd wanneer de nieuwste release expliciet cumulatieve migratie ondersteunt.

### Voor elke belangrijke upgrade

Maak een recente Home Assistant-back-up wanneer een release persistente configuratie of leerdata migreert. Bewaar minstens de vorige bekende goede SolarPilot-release/tag.

### Rollback

Rollback is een herstelpad, geen garantie dat elke toekomstige dataschemawijziging onbeperkt achterwaarts compatibel zal zijn.

Veilige werkwijze:

1. fysieke regeling pauzeren of naar Observatie;
2. Home Assistant-back-up veiligstellen;
3. vorige bekende goede tag/release installeren;
4. Home Assistant herstarten;
5. configuratie- en opslagcompatibiliteit controleren;
6. eerst Observatie valideren;
7. pas daarna fysieke regeling opnieuw activeren.

Wanneer een toekomstige release een niet-achterwaarts-compatibele opslagmigratie nodig heeft, moet dit **voor publicatie** expliciet in changelog én dit dossier staan, inclusief concreet herstelpad.

### Verwijderen

Gebruik de ingebouwde voorbereiding voor verwijderen, verwijder daarna de config entry/HACS-integratie en herstart Home Assistant. Onderliggende apparaten en hun native integraties mogen niet door SolarPilot verwijderd worden.

## 9. Privacy en secrets

Nooit committen:

- Home Assistant access tokens;
- API-sleutels of OAuth-secrets;
- wachtwoorden;
- privé-entiteitsnamen uit de persoonlijke installatie;
- Home Assistant-back-ups;
- ruwe energie-/analyse-exports;
- adressen, coördinaten of andere identificerende gegevens;
- `private_bundle.json` met installatiespecifieke mappings.

De publieke repository moet bruikbaar blijven zonder persoonlijke installatiegegevens.

`tools/check_public_repository.py` controleert de bekende privacy-/structuurregels en scant ook dit overdrachtsdossier.

## 10. Bekende grenzen en volgende aandachtspunten

- Zonder aparte warmtepomp-W-meter blijft geleerd warmtepompvermogen uitsluitend een conservatieve **planningsschatting**.
- SolarPilot bestuurt de Wallbox niet rechtstreeks; effectieve sessieherkenning en terugmelding blijven daarom essentieel.
- Volledige fasegewijze optimalisatie van de afwasmachine vereist een betrouwbare exclusieve vermogensmeting.
- Forecastdekking is niet altijd volledig; onbekende uren mogen niet als nul of gegarandeerd overschot worden geïnterpreteerd.
- Faseadvies en fasesturing moeten afzonderlijk betrouwbaar en expliciet vrijgegeven blijven.
- Batterijbesturing blijft standaard uit en vereist afzonderlijke toestemming/eigenaarschap.
- Open pop-ups, sleepvolgorde en onopgeslagen configuratie mogen niet door snelle telemetrie-refresh verloren gaan.
- Deze GitHub-borging kan alleen wijzigingen controleren die **in de repository worden gecommit**. Een lokale/offline codewijziging die nooit naar GitHub wordt gebracht kan technisch niet automatisch dit dossier aanpassen. Zodra de wijziging via deze ontwikkel-/releaseflow loopt, blokkeert CI een functionele codewijziging zonder bijgewerkt `OVERDRACHT.md`.

## 11. Release-checklist

Een SolarPilot-release is pas compleet wanneer alle toepasselijke vakken hieronder zijn afgewerkt:

- [ ] Nieuwe code werkt op de actuele codebasis; geen los prototype of pseudocode.
- [ ] Bestaande werkende functies zijn behouden of aantoonbaar centraal vervangen.
- [ ] Bestaande gebruikersinstellingen en relevante leerdata migreren correct.
- [ ] Centrale prioriteiten en Wallbox-reclaimrechten blijven behouden tenzij de gebruiker ze bewust wijzigt.
- [ ] Nieuwe fysieke rechten worden niet stilzwijgend geactiveerd.
- [ ] `manifest.json`, `const.py`, frontendversie en guide-versie lopen gelijk.
- [ ] `current_guide.py` is bijgewerkt en beide `ACTUELE_WERKING.md`-kopieën zijn opnieuw gegenereerd.
- [ ] Optie-uitleg/help is bijgewerkt wanneer instellingen veranderden.
- [ ] `CHANGELOG.md` beschrijft de nieuwe release.
- [ ] **`OVERDRACHT.md` is inhoudelijk opnieuw gecontroleerd en bijgewerkt.**
- [ ] Automatische tests slagen.
- [ ] Python compileert.
- [ ] HACS-validatie en Hassfest slagen.
- [ ] Publieke privacycontrole slaagt.
- [ ] Analyse-/diagnostische schemawijzigingen zijn gedocumenteerd.
- [ ] Installatie-/upgradepad is duidelijk.
- [ ] Rollbackrisico en eventuele opslagcompatibiliteit zijn beoordeeld.
- [ ] Release/tag wordt pas daarna gepubliceerd.

---

### Onderhoudsregel

Dit bestand beschrijft altijd **hoe SolarPilot nu werkt**. Verouderde werking wordt hier verwijderd of herschreven, niet eronder bijgeplakt. Wie historische verschillen nodig heeft, gebruikt `CHANGELOG.md` en Git.
