# SolarPilot beta.98 — schuiven door de warmtepompgeschiedenis

Versie: **1.0.0-beta.98** · 18 oktober 2026

Open bij Warmtepomp **Geschiedenis** en schuif horizontaal over een tijdsbalk. De gezamenlijke markering springt naar beschikbare meetpunten en toont de werkelijke tijd met vermogen, boilertemperatuur, doelen, taak en SG-contact. Op een computer kun je de muis of het toetsenbord gebruiken. Ontbrekende meetwaarden blijven onbekend; de huidige boilerwaarden worden niet op oude uren geplakt.

Nieuwe meetpunten bewaren een gevalideerde totale W-meting. Oudere punten kunnen afzonderlijke voedingen tonen zonder een bewezen totaal. Het dagelijkse gemeten kWh-verbruik blijft apart staan. De registratie blijft begrensd en er wordt geen geschiedenis achteraf aangevuld.

Deze versie verwerkt ook de nieuwe Aquarea 1.8.0 en SDK 1.4.0. De nieuwe statusbetekenis staat los van oudere historische contracten. Cachegegevens worden niet door een nieuwe poll als LIVE aangemerkt. De bestaande SG-regels en Panasonic-bevoegdheden blijven behouden.

## Bijwerken

1. Bewaar een actuele volledige privé Home Assistant-back-up.
2. Werk SolarPilot via HACS bij naar beta.98 zodra controles en publicatie geslaagd zijn. Behoud entry, instellingen, modellen, historie, opslag en userfiles.
3. Herstart Home Assistant volledig en herlaad de browser/app. Controleer backend- en kaartversie afzonderlijk.
4. Open Geschiedenis en controleer schuiven, een ontbrekend meetpunt en een oudere dag. De tijdmarkering leest alleen en schakelt niets.

[Installatie, controle en rollback](docs/BETA98_INSTELLEN.md) · [Actuele werking](docs/ACTUELE_WERKING.md) · [Testverslag](docs/TESTRESULTATEN_BETA98.md) · [Overdracht](OVERDRACHT.md)
