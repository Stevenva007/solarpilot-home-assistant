# Optionele privé historische bootstrap

SolarPilot werkt volledig zonder historisch bootstrapbestand; het leert na installatie live verder.

Wil je eigen historische data als voorzichtige startkennis gebruiken, genereer lokaal een geaggregeerde seed met `tools/build_historical_seed.py` en plaats die daarna als:

```text
/config/custom_components/solar_pilot/userfiles/historical_seed.json
```

Herstart Home Assistant daarna. HACS bewaart `userfiles` bij gewone updates. Ruwe exports en jouw gegenereerde `historical_seed.json` horen niet in de publieke GitHub-repository.
