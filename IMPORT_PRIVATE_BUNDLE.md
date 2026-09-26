# SolarPilot privéprofiel + historiek

SolarPilot werkt volledig zonder privébestand. Dit bestand is alleen bedoeld om een eigen Home Assistant-installatie sneller en consistenter te configureren.

## Eén bestand

Plaats je persoonlijke bestand als:

```text
/config/custom_components/solar_pilot/userfiles/private_bundle.json
```

HACS bewaart `userfiles` bij gewone SolarPilot-updates. Het bestand hoort **nooit** in de publieke GitHub-repository.

De bundel mag twee soorten informatie bevatten:

1. `profile.suggestions` — installatie-specifieke Home Assistant entity-ID's voor P1/PV, fasen, Forecast.Solar, prijzen, warm water, klimaat en Wallbox;
2. `historical_seed` — geaggregeerde historische PV-, net-, fase-, basislast- en batterij-what-ifdata.

Ruwe Home Assistant- of HomeWizard-exports horen niet in deze map of in GitHub.

## Importeren

Na plaatsen van het bestand:

1. open **Instellingen → Apparaten & diensten → SolarPilot → Configureren**;
2. open **Geavanceerd & systeem → Privéprofiel & historiek**;
3. zet **Privéprofiel en historiek nu importeren / herladen** aan en bevestig.

Bij een herstart wordt een nieuwe, nog niet toegepaste bundel eveneens automatisch en conservatief ingelezen.

## Veilig importbeleid

- Bestaande niet-lege keuzes worden niet overschreven.
- Een entity-ID wordt alleen overgenomen wanneer die entiteit werkelijk bestaat.
- Ontbrekende bron-groepen worden gerapporteerd en op een latere herstart/import opnieuw geprobeerd.
- Fasebewaking kan als monitor worden voorbereid, maar `control_starts` en `shed_on_overlimit` blijven uit.
- Slim klimaat kan als model/advies worden voorbereid, maar `control_enabled` blijft uit.
- Boilerbronnen worden ingevuld, maar `enabled` en `safety_confirmed` blijven uit totdat je de boilerwizard zelf bevestigt.
- Wallbox blijft read-only.
- SolarPilot start altijd in **Observatie**.

## Historiek

De historische bootstrap is optioneel en alleen adviserend. Live P1/PV-metingen en actuele apparaatvoorwaarden blijven altijd leidend. De bootstrap kan lokale PV-correctie, basislastleren, faseanalyse en batterij-what-if sneller op gang helpen.
