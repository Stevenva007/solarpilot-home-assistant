# SolarPilot 1.0.0-beta.109 installeren

Werk SolarPilot via HACS bij naar **1.0.0-beta.109**, herstart Home Assistant volledig en herlaad app/browser. Maak vooraf een volledige privéback-up met SolarPilot-opslag en userfiles. Verwijder de integratie niet.

Deze versie voorkomt recorderwaarschuwingen over te grote Wallbox-attributen. De vermogenssensor houdt het oorspronkelijke power_w en zijn watt-/meetmetadata. De statusinformatie houdt live profielen en diagnostiek, terwijl vier grote velden niet meer telkens in de geschiedenis worden opgeslagen. Bestaande instellingen, bronkoppelingen, modellen en regeling blijven behouden. Ontbrekend vermogen blijft onbekend en wordt geen nul.

Controleer na volledig opstarten het actuele laadvermogen, de Wallbox-details en het logboek. Deze correctie repareert geen externe netwerk-, camera- of providerfout.

## Rollback

Installeer indien nodig beta.107 via HACS en herstart volledig, met behoud van configuratie en private gegevens. Beta.107 mist de nieuwe recordercorrectie. Voer geen geforceerde laad- of SG-proef uit voor deze presentatie-/opslagwijziging.

[Actuele werking](ACTUELE_WERKING.md) · [Testresultaten](TESTRESULTATEN_BETA109.md)
