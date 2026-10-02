> **Nieuw: beta.43** — maakt actuele activiteit en besparingsschattingen controleerbaar, bewaart read-only Wallbox-waarnemingen zonder oorzaken te verzinnen, beveiligt browsernavigatie met open formulieren en voegt een optionele maandagdeadline voor de AEG-afwasmachine toe.

# SolarPilot

SolarPilot is a local Home Assistant Energy Management System (EMS) for PV surplus, flexible loads, Panasonic Aquarea hot-water policy, Wallbox Full Solar coexistence, phase analysis, capacity-tariff awareness, local PV/shade learning, slow thermal-climate learning, future home batteries and a unified rolling-horizon planner.

> **Status:** beta.43 is gepubliceerd onder de onveranderlijke release-tag `v1.0.0-beta.43` (commit `a50c62e269a44f61b432af5cdda2522e1e6cb7ce`). GitHub-workflow `37005461399`, beide release-ZIP's en de inhoud tegenover die tag zijn gecontroleerd. Na een bestaande NAS-back-up, installatie via HACS en de door de gebruiker goedgekeurde Home Assistant-herstart zijn backend en kaart `1.0.0-beta.43` werkelijk geladen op Home Assistant Core 2026.9.4. De liveacceptatie is nog niet volledig: SolarPilot blijft **Alleen bekijken** zolang de gerichte boilercontrole openstaat en maandag 10:00 is nog niet live toegepast en bevestigd. Start nieuwe installaties in **Alleen bekijken**. Do not enable physical control for several devices at once.


> **Updates zijn cumulatief.** Je hoeft tussenliggende beta-versies niet één voor één te installeren of publiceren. Installeer de nieuwste release over je bestaande SolarPilot-installatie; Home Assistant-configuratie en lokale leerdata blijven behouden.

## Current DHW policy (preserved in beta.43)

Normal tank setpoint and monitored comfort floor are independent (new defaults 50/46 °C). No deadband-compensating 52 °C boost or Force DHW. A 50 °C target with a -5 °C native differential can reheat around 45 °C: 46 °C is monitored, not guaranteed and not a hygiene standard. Optional bounded evening solar storage waits for space climate; see `docs/BETA28_INSTELLEN.md`. Existing setpoints and permissions migrate without silent profile activation.


## Nieuw in beta.43

- **Nu actief** gebruikt de werkelijk waargenomen toestelstatus en maakt gemeten versus geschat vermogen zichtbaar. Activiteit bewijst niet dat alle energie op dat moment van PV komt of dat SolarPilot de start veroorzaakte.
- De Wallbox blijft read-only, maar toont nu de actuele bekende wachtstatus en maximaal dertig lokaal waargenomen laadperiodes. Een historische native stopreden wordt alleen gekoppeld bij een aantoonbaar nieuwe status uit dezelfde rapportagebatch; gaten, herstarts of oude/onlogische tijden blijven onbekend.
- Browser **Terug** en **Vooruit** herstellen uitsluitend SolarPilot-schermen op dezelfde Home Assistant-URL. Niet-opgeslagen formulieren vragen bevestiging en opslaan of een lopende actie wordt niet onderbroken.
- De aparte automatische-voordeelweergave bewaart maximaal negentig dagen vanaf activering. Het is een opportunity-value-schatting op bruikbare meetintervallen, geen bewezen extra besparing en geen bedrag dat nogmaals van de elektriciteitskost mag worden afgetrokken.
- De AEG-afwasmachine krijgt een optionele afzonderlijke maandagdeadline. Leeg houdt ook maandag de gewone 13:00; bijvoorbeeld 10:00 geldt alleen op maandag. Bestaande tickets blijven bevroren tenzij je expliciet dezelfde geplande dag laat herberekenen; dat maakt geen ticket en verstuurt geen START.
- De beschermde avondvoorraad tot de ingestelde limiet en maximaal 55 °C mag alleen actuele, expliciet bevestigde Full Solar-lading als vrijmaakbaar zonnevermogen meewegen: verbonden en vragend, minstens 50 W, sessiestatus én vermogen hoogstens 120 seconden oud. Handmatig/onbekend/oud laden telt niet; extra 60 °C krijgt nooit EV-krediet en comfort-, koel- en fabrikantbeveiliging blijven hoger.
- Alle beta.42-veiligheidsgrenzen blijven cumulatief behouden: gerichte DHW-Hervat, eerlijke effectieve Voorrang, begrensde leerreset, handmatig OFF gezette klimaatzones, extra boilerwarmte alleen onder eigendom en een volledig read-only Wallbox.
- De definitieve softwaregate voor beta.43 is groen met **1656 geslaagde Python-tests** en **veertien geslaagde browsercontroles**. Publicatie en installatie veranderen die softwarecontrole niet in een fysieke acceptatietest.
- Na de goedgekeurde herstart rapporteerde de AEG-afwasmachine nog steeds `Running`. Er is bij de upgrade geen nieuwe APP-aanvraag, START of STOP verstuurd. De globale modus blijft voorlopig **Alleen bekijken**, omdat de fail-closed DHW-herstartcontrole eerst bewust moet worden afgerond; **Automatisch regelen** is dus nog niet als hersteld geclaimd.
- Het SolarPilot-logo in het HACS-updatevenster ontbreekt nog, hoewel de lokale integratiebeelden aanwezig zijn. HACS haalt dit beeld via de centrale brands-CDN; een Home Assistant-`entity_picture`-customisatie of upstream HACS-ondersteuning is daarvoor nog nodig. Dit is geen ontbrekende beta.43-code of reden voor een extra installatie. Zie de [HACS 2.0.5-bron](https://github.com/hacs/integration/blob/2.0.5/custom_components/hacs/update.py) en [ondersteunde Home Assistant-customisatie](https://www.home-assistant.io/integrations/homeassistant/#editing-entity-settings-in-yaml).

Zie `docs/BETA43_INSTELLEN.md` en `docs/TESTRESULTATEN_BETA43.md`.

## Behouden uit beta.40: gericht AEG-herstel

- De live diagnose bewees dat beta.39 tijdens zijn enige setupcontrole nog geen legacy-marker zag, terwijl beide markers en alle verplichte AEG-rollen kort daarna volledig op hetzelfde Home Assistant-apparaat aanwezig waren.
- De bestaande legacy-recovery blijft daarom na SolarPilot-start maximaal tien minuten gericht actief, reageert op relevante states en controleert begrensd opnieuw. Na succes, timeout of unload worden de tijdelijke listeners verwijderd.
- Alleen één complete, eenduidige same-device mapping kan een profiel opleveren. Ontbrekende of ambigue verplichte rollen geven geen fysiek recht; `dishwasher_setup` maakt de rolstatus zichtbaar zonder private device-id.
- Een laat hersteld profiel wordt persistent en live toegepast, verschijnt onder Toestellen en volgens de bestaande voorkeursregel onder Voorrang. Alleen de exacte eenmalige legacy-recovery kan Auto herstellen wanneer geen eerdere gebruikersmodus bestaat.
- De migratie maakt geen APP-aanvraag, verandert geen programma en verstuurt geen START. Exacte nieuwe `Enabled`-overgang, deur, programma, Ready To Start, actuele verbinding, elektrische ruimte en alle overige veiligheidslocks blijven verplicht.
- Een later bewust verwijderd herstelprofiel wordt niet stil opnieuw gemaakt. Handmatige profielen en bestaande gebruikerskeuzes worden niet overschreven.
- De beta.39-fixes voor ConnectivityState als heartbeat, volledige beschermde cyclusfasen en de onbewezen automatische alarmbron blijven cumulatief behouden, evenals centrale prioriteiten, Wallbox-read-onlybeleid, Panasonic/DHW, fasebewaking, planner, analyse en leerdata.
- De beta.40-bron werd met haar toenmalige regressiesuite vrijgegeven. Zie `docs/BETA40_INSTELLEN.md` en `docs/TESTRESULTATEN_BETA40.md` voor die historische releasecontrole.

## Install via HACS

This repository is intended to be added as a **HACS Custom Repository** of type **Integration**.

1. In HACS, open **Custom repositories**.
2. Add this repository URL and choose **Integration**.
3. Download **SolarPilot**.
4. Restart Home Assistant.
5. Go to **Settings → Devices & services → Add integration → SolarPilot**.
6. Select your grid-power source and optional PV source, then keep the integration in **Alleen bekijken** during the first checks.

The SolarPilot frontend is shipped inside the integration. No `/config/www` file, Lovelace resource or manual dashboard YAML is required for normal use.

## Updates

HACS manages the integration files. A normal update is:

**HACS → SolarPilot → Update → Restart Home Assistant**

SolarPilot configuration and learned runtime data are stored in Home Assistant, not in the program files replaced by HACS. The optional `userfiles` directory is marked persistent so a local private bundle survives ordinary HACS updates.


## Optional private profile + history

A private bundle is optional. Place exactly one local file at:

```text
/config/custom_components/solar_pilot/userfiles/private_bundle.json
```

Then open **SolarPilot → Configure → Advanced & system → Private profile & history** and apply/reload it. The importer only fills still-empty links to Home Assistant entities that actually exist. Monitoring/advisory modules may be enabled with safe defaults, but physical climate control, phase shedding and DHW control remain explicitly protected. A first setup starts in **Alleen bekijken**. On ordinary restart the stored mode resumes only after actual-state reconciliation; unresolved states remain protected. See `IMPORT_PRIVATE_BUNDLE.md`.

## Safe removal

1. In SolarPilot choose **Verwijderen voorbereiden** and wait for **Verwijderen gereed**.
2. Remove the SolarPilot config entry under **Settings → Devices & services**.
3. Remove SolarPilot in HACS.
4. Restart Home Assistant.

SolarPilot does not remove the underlying grid meter, heat-pump, wallbox, inverter, smart-plug or other integrations/devices.

## Current behaviour

The canonical current explanation is [docs/ACTUELE_WERKING.md](docs/ACTUELE_WERKING.md). The same explanation is available inside the SolarPilot Home Assistant panel.

## Important fixed design rules

- Current P1/PV measurements and device protection override forecasts and plans.
- Wallbox Pulsar Max remains read-only and controls its own Full Solar mode.
- Panasonic chooses HEAT versus COOL; SolarPilot never chooses those modes.
- Panasonic sterilisation remains autonomous.
- Battery control is disabled by default and requires explicit ownership/permission.
- An EMS decision is not an electrical safety device.

## Repository privacy

This repository may be public because HACS requires public GitHub repositories. Do not commit Home Assistant backups, access tokens, raw energy-history exports, addresses or other private files. The public repository contains no household-specific entity IDs. SolarPilot can learn live without private data. For a faster installation-specific start, one local `custom_components/solar_pilot/userfiles/private_bundle.json` may contain entity mappings plus an aggregated historical bootstrap. HACS preserves `userfiles` across ordinary upgrades, and the private bundle must never be committed to GitHub.

## Inbegrepen: dagkosten en Wallbox-voorrang

Afzonderlijke elektriciteitskost vandaag met netto afname/injectie en directe PV, naast de behouden 36-uurskostprognose. Wallbox-voorrang is per verbruiker instelbaar, met klein-overschotfallback en behoud van minimumlooptijden. De generieke Wallbox-voorrang per verbruiker wordt bewust gekozen; de nieuwe AEG-voorkeurgroep is in beta.32 standaard aan, zonder fysieke startrechten te activeren. Lees `docs/KOSTEN_EN_WALLBOXVOORRANG.md`. Deze cumulatieve release behoudt ook de eerdere stabiliteits- en interfacecorrecties.

## Geschiedenis per toestel

Open **SolarPilot → Toestellen → Geschiedenis**. De popup toont geregistreerde draaitijd per dag, start-/stoptijden, sessieduur en altijd afzonderlijk Startreden en Stopreden. Kies een datum of vergelijk de laatste 7/30 dagen. De popup blijft open tijdens live telemetrie.

Draaitijd volgt de gekoppelde aan-/actiefstatus: een ingeschakelde slimme stekker bewijst niet dat een compressor continu draait. Externe bediening, onbekende begintijd, meetgaten en herstarts worden apart gemarkeerd. De historiekfunctie registreert sinds beta.25; bestaande opgeslagen sessies blijven behouden. Eerdere niet-geregistreerde redenen worden niet verzonnen. De opslag blijft lokaal, is begrensd en overleeft gewone updates. De volledige historie wordt alleen opgevraagd wanneer de popup wordt gebruikt.

Deze release is cumulatief en bevat ook alle correcties en uitbreidingen uit beta.22, beta.23 en beta.24. Tussenliggende releases hoeven niet apart gepubliceerd of geïnstalleerd te worden. De volledige actuele uitleg staat in `docs/ACTUELE_WERKING.md` en in het Home Assistant-tabblad **Uitleg**.

## Nieuw in beta.28

- Vraagtekens met uitgebreide Nederlandse optie-uitleg via **Configureren met uitleg ?**; dezelfde HA-optiesflow en serverbeveiligingen, geen globale HA-DOM-patch.
- Automatisch alleen-lezen Wallbox-laadprofiel, met expliciete bron-/terugvalstatus, huidige 1-fase/25-A-terugval en toekomstige 3-fasenondersteuning.
- Optionele nacht-/ochtendbewaking: om 09:00 de gewenste gemeten voorraad controleren (standaard 46 °C). Het normale doel blijft 50 °C; geen verhoogde hersteltemperatuur of vaste klokstart. Panasonic mag volgens zijn eigen regeling ook netstroom gebruiken.
- Optionele avondvoorraad op laatste bruikbare zon, begrensd tot standaard 55 °C en gebaseerd op voorzichtig tankleren.
- Normaal warmtepompcomfort vóór Wallbox; extra 60 °C uitsluitend uit echte restinjectie. Recente en optioneel voorspelde koeling begrenzen extra tankopwarming.

Nieuwe comfortfuncties staan na upgrade niet ongemerkt aan. Bestaande instellingen, gebruikersbestanden en lokale leerdata blijven behouden. De fabrikant-hygiëne en verbrandingsbeveiliging blijven onafhankelijk vereist; een ochtendtemperatuur is een doel, geen garantie na waterafname of storingen. Zie **docs/ACTUELE_WERKING.md** en **docs/BETA28_INSTELLEN.md**.

## Nieuw in beta.29: AEG en analyse

Afwasmachine-start met eenmalige klaarzettoestemming en native AEG-START, nooit via de netstekker. Een gestart programma blijft beschermd. De knop **Analyse-export** onderaan het dashboard maakt een lokaal JSON-bestand voor handmatige probleem- en modelanalyse. Zie [instellen en beperkingen](docs/AFWASMACHINE_EN_ANALYSE.md). Nieuwe fysieke koppelingen worden niet automatisch geactiveerd.


## Nieuw in beta.30: Leren & vragen

De meetbasis, ontbrekende gegevens en gerichte beslisvragen staan in een aparte
popup. Basislastleren kan nu doorgaan tijdens EV/eigen lasten wanneer aparte,
actuele meters een betrouwbare restbalans geven. Geen nul voor onbekende data.
Een recente voorspelling wordt in de achtergrond getoetst en alleen na jouw
toestemming en voldoende bewijs begrensd toegepast; veiligheids-/comfortregels
worden niet door leren herschreven. Nieuwe daglichtfouten en meetdekking maken de
kwaliteit begrijpelijker.

Zie [beta.30 instellen](docs/BETA30_INSTELLEN.md) en de release-gebonden actuele
uitleg. De APP-knopgestuurde AEG-start en 13:00-deadline zijn sinds beta.31 inbegrepen;
zie [APP instellen](docs/BETA31_INSTELLEN.md). De huidige cumulatieve release
bevat zowel die startlogica als de leerupdate.

## Afwasmachinevoorrang in beta.32

Zie [de actuele beta.32-instelhandleiding](docs/BETA32_INSTELLEN.md).
Normaal warmtepompcomfort gaat voor, vervolgens de afwasmachine en daarna de
lagere automatische lasten, Wallbox en extra 60 °C-zonnebuffer. De twee nieuwe
voorkeuren staan standaard aan voor AEG-profielen; fysieke rechten blijven staan.
Programmafaseplanning volgt pas met de afzonderlijke latere Shelly-update.
