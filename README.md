# SolarPilot

SolarPilot is a local Home Assistant Energy Management System (EMS) for PV surplus, flexible loads, Panasonic Aquarea hot-water policy, Wallbox Full Solar coexistence, phase analysis, capacity-tariff awareness, local PV/shade learning, slow thermal-climate learning, future home batteries and a unified rolling-horizon planner.

> **Status:** beta.20 · public HACS beta. Start in **Observatie**. Do not enable physical control for several devices at once.

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

Then open **SolarPilot → Configure → Advanced & system → Private profile & history** and apply/reload it. The importer only fills still-empty links to Home Assistant entities that actually exist. Monitoring/advisory modules may be enabled with safe defaults, but physical climate control, phase shedding and DHW control remain explicitly protected. SolarPilot still starts in **Observatie**. See `IMPORT_PRIVATE_BUNDLE.md`.

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
