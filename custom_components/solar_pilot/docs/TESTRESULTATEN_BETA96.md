# SolarPilot beta.96 — test- en publicatieverslag

Versie: **1.0.0-beta.96** · 17 oktober 2026

Bouwbasis: gepubliceerde beta.95-commit `bc57c8ae3e0d111a0909632a14f107bcb90cf4eb`. Publieke regressies gebruiken uitsluitend fictieve entiteiten, apparaten en waarnemingen.

## Problemen en correcties

De Panasonic-presentatie werd door meerdere sensorwaarden en attributen herhaald berekend. De vijf Panasonic-sensoren en het Panasonic-detail van de algemene status hergebruiken nu een gezamenlijk presentatieframe per runtimepublicatie. Eerder gevraagde frames worden vóór de volgende callbacks ververst. Directe regelingslezingen en SG-contactwaarnemingen blijven live. Een nieuwe presentatie behoudt oorspronkelijke bronrapporttijden en creëert geen actualiteits-, leer- of actuatorbewijs.

De virtuele apparaten gebruikten de verouderde `via_device`-koppeling. Moderne Core krijgt eerst dezelfde geregistreerde virtuele hub en daarna koppelingen met `via_device_id`. Moderne identificatie is beperkt tot de eigen configuratie-entry. De legacy-terugval en bestaande identifiers blijven behouden; bronapparaten worden niet gewijzigd.

De actuele Aquarea 1.6.0 verandert vroegere dagsensoren naar per-fetch intervaldelta's zonder ENERGY-deviceclass of `period_being_processed`. De bestaande SolarPilot-bewijscontrole weigert deze al als dagperiode. Een expliciete regressie borgt dit; de providerupdate geeft geen automatische dagtotalen of bronrechten. De maandmeters en SDK-semantiek veranderen in deze upstreamvergelijking niet.

## Regressies en lokale verificatie

De vier oorspronkelijke onderhoudsregressies zijn uitgebreid met afzonderlijke moderne en legacy-apparaatopzoeking. Zij toetsen gedeelde waarden/attributen, vernieuwing vóór callbacks, oorspronkelijke tijden, rechtstreeks actuele controllerlezingen, registratievolgorde, entry-afbakening, behoud van bronapparaten en weigering van gewijzigde Aquarea-intervalenergie als dagbewijs.

De volledige definitieve lokale suite slaagde: **7.184 tests in 139,09 seconden** (`PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider`). De zes beta.96-regressies zijn onderdeel van dit totaal. Python-syntaxis, repository/privacy, het overdrachtsdossier, de gegenereerde actuele uitleg en de Panasonic/SG-grenscontrole slaagden eveneens. De online upstreamcontrole bevestigde de vastgelegde actuele broncommits en releasetags. De afzonderlijke GitHub-gates voor PowerShell, HACS, Hassfest, Chromium en echte Home Assistant blijven hieronder als publicatievoorwaarden staan.

De bestaande SG-bevoegdheids-, presentatie-/recordertijd-, platform-lifecycle-, bron-/eenheden-, geschiedenis-, opslag-, afwas-, Wallbox- en resttijdregressies blijven vereist. Oude resultaten zijn geen extra onafhankelijke tests en worden niet bij deze suite opgeteld.

## Upstream en publicatie

Beide actuele defaultbranches en stabiele releasetags/commits zijn online gecontroleerd: Aquarea v1.6.0 `f127489774c61c1e97ee5eb5097257748d55d510` en aioaquarea-ng v1.3.1 `d859f3727556c8a07964affd61a038edfd2d353a`. SDK PR12 blijft open en ongepubliceerd. Het beoordeelde broncheckpoint staat in `docs/upstream_review.json` en wordt door de verplichte CI-gate opnieuw gecontroleerd.

De [Validate-workflow](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml) moet alle vijf gates op de definitieve bron uitvoeren: repository/privacy/documentatie met volledige suite en PowerShell-proeven, HACS, Hassfest, echte Home Assistant setup/reload/unload en Chromium. Alleen na geslaagde gates op `main` maakt de publicatiejob een nieuwe immutable annotated tag en deze vier assets:

- `SolarPilot-v1.0.0-beta.96-GitHub-HACS.zip`
- `SolarPilot-v1.0.0-beta.96-local.zip`
- `BETA96_INSTELLEN.md`
- `TESTRESULTATEN_BETA96.md`

De job vergelijkt beide ZIPs en beide documentassets vóór publicatie en na opnieuw downloaden bytegelijk met de exacte broncommit, inclusief grootte en SHA-256. Bestaande tags en assets worden niet overschreven. De oorspronkelijke lokale onderhoudspatch krijgt zo een normale onderhoudbare versiegeschiedenis; privé Home Assistant-configuratie, back-ups en logs worden niet gepubliceerd.

Software- en pakketcontroles zijn geen fysieke AEG-, Panasonic-, Shelly- of Wallbox-acceptatie. Deze release vraagt geen nieuwe lokale bevoegdheid en bevat geen fysieke testopdrachten.
