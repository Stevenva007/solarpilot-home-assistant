# SolarPilot beta.19 — HACS eerste installatie

Dit is de aanbevolen eerste installatie.

## 1. Vooraf

- Maak een volledige Home Assistant-back-up.
- Installeer/configureer HACS als dat nog niet gebeurd is.
- SolarPilot blijft tijdens de eerste controle in **Observatie**.

## 2. SolarPilot via HACS toevoegen

1. Open **HACS → Custom repositories**.
2. Voeg de publieke SolarPilot GitHub-repository toe als type **Integration**.
3. Download **SolarPilot**.
4. Herstart Home Assistant.
5. Ga naar **Instellingen → Apparaten & diensten → Integratie toevoegen → SolarPilot**.
6. Selecteer je netvermogensbron en optionele PV-bron en bevestig.

Daarna verschijnt de SolarPilot-interface automatisch. Er is geen aparte Lovelace-resource nodig.

## 3. Eerste controle

Controleer in Observatie achtereenvolgens P1/PV, Forecast.Solar/lokale schaduw, L1/L2/L3, Panasonic warm water, slim klimaat, Wallbox read-only en de Planning-tab.

Zet PV Excess Control en de twee oude boilerautomatiseringen pas uit wanneer SolarPilot daadwerkelijk klaar is om over te nemen.

## 4. Eerste fysieke test

Activeer eerst één niet-kritieke, goed meetbare flexlast. Breid pas daarna toestel per toestel uit.

## 5. Uitleg

De enige actuele regelbeschrijving is `docs/ACTUELE_WERKING.md` en dezelfde inhoud staat in Home Assistant onder SolarPilot → Uitleg.
