> **Nieuw: beta.36** — warmtepompactiviteit wordt uit de gewone basislast gehouden, Wallbox-sessies worden explicieter herkend, de centrale prioriteitenlijst is nu leidend, DHW gebruikt één configuratiebron en klimaat-/exportkwaliteit toont betrouwbaarheid en echte meetdekking duidelijker.

# SolarPilot

SolarPilot is a local Home Assistant Energy Management System (EMS) for PV surplus, flexible loads, Panasonic Aquarea hot-water policy, Wallbox Full Solar coexistence, phase analysis, capacity-tariff awareness, local PV/shade learning, slow thermal-climate learning, future home batteries and a unified rolling-horizon planner.

> **Status:** beta.36 · public HACS beta. Start in **Observatie**. Do not enable physical control for several devices at once.


> **Updates zijn cumulatief.** Je hoeft tussenliggende beta-versies niet één voor één te installeren of publiceren. Installeer de nieuwste release over je bestaande SolarPilot-installatie; Home Assistant-configuratie en lokale leerdata blijven behouden.

## Current DHW policy (preserved in beta.36)

Normal tank setpoint and monitored comfort floor are independent (new defaults 50/46 °C). No deadband-compensating 52 °C boost or Force DHW. A 50 °C target with a -5 °C native differential can reheat around 45 °C: 46 °C is monitored, not guaranteed and not a hygiene standard. Optional bounded evening solar storage waits for space climate; see `docs/BETA28_INSTELLEN.md`. Existing setpoints and permissions migrate without silent profile activation.


## Nieuw in beta.36

- Panasonic-activiteit wordt onderscheiden als gewone huishoudlast, ruimteverwarming, ruimtekoeling, tapwater, sterilisatie of onbekende warmtepompactiviteit. Zonder eigen warmtepomp-W-meter mag alleen een conservatieve planningsschatting uit stabiele P1+PV-stappen worden geleerd; die schatting verandert nooit de realtime netruimte.
- De Wallbox toont ingestelde modus, werkelijk gedetecteerde sessie, laadvermogen en waarom terugnemen van laadvermogen nu wel/niet mag. Zonder effectieve sessiesensor gebruikt SolarPilot uitsluitend werkelijk vrije injectie.
- De centrale prioriteitenlijst is na migratie de leidende bron: beveiliging/legionella, noodzakelijk warmwatercomfort en noodzakelijk ruimtecomfort zijn beschermd; daarna blijven standaard Wallbox → ontvochtiger → extra boilerwarmte 60 °C behouden. Per flexibele verbruiker staat los daarvan of Wallbox-vermogen mag worden teruggenomen.
- DHW centraliseert de afgesproken 50/46/-5/50/60/62 °C-regels in één configuratiebron en toont afzonderlijk configuratie, inschakeling, vrijgave, eigenaarschap en handmatige override.
- Klimaatbetrouwbaarheid is opgesplitst in passieve drift, zonnewinst, verwarmingsrespons, koelrespons, reactievertraging, weerscorrectie en coast-feedback. Ontbrekende onderdelen worden niet als 100% weergegeven.
- PV-kalibratie behoudt minimaal vijf geldige dagen, 13,8 kWp en 10 kW omvormerlimiet; diagnostiek voegt fout/bias per ochtend, middag en namiddag toe.
- Analyse-export vermeldt aangevraagde periode én werkelijk beschikbare/dekkende uren, gaten, herstarts en fast telemetry. Planberekeningen tellen nooit als extra leerdag.

## Install via HACS

This repository is intended to be added as a **HACS Custom Repository** of type **Integration**.

1. In HACS, open **Custom repositories**.
2. Add this repository URL and choose **Integration**.
3. Download **SolarPilot**.
4. Restart Home Assistant.
5. Go to **Settings → Devices & services → Add integration → SolarPilot**.
6. Select your grid-power source and optional PV source, then keep the integration in **Observatie** during the first checks.

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

Then open **SolarPilot → Configure → Advanced & system → Private profile & history** and apply/reload it. The importer only fills still-empty links to Home Assistant entities that actually exist. Monitoring/advisory modules may be enabled with safe defaults, but physical climate control, phase shedding and DHW control remain explicitly protected. A first setup starts in **Observatie**. On ordinary restart the stored mode resumes only after actual-state reconciliation; unresolved states remain protected. See `IMPORT_PRIVATE_BUNDLE.md`.

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

## Dagoverzicht: Dagoverzicht per verbruiker

Open **SolarPilot → Verbruikers → Dagoverzicht**. De popup toont geregistreerde draaitijd per dag, start-/stoptijden, sessieduur en de bevestigde start-/stopreden. Kies een datum of vergelijk de laatste 7/30 dagen. De popup blijft open tijdens live telemetrie.

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
