# SolarPilot starten of bijwerken

Installeer **1.0.0-beta.108** via HACS, herstart Home Assistant volledig en herlaad de app of browser.

Open **Voorrang** om de centrale volgorde te controleren. De Wallbox staat standaard als laatste. Een eigen eerder opgeslagen volgorde blijft behouden.

Staat SG hoger, dan mag zij betrouwbaar gemeten zonnelaadvermogen van de Wallbox overnemen. De laadpaal krijgt standaard vier minuten om zelf terug te regelen; binnen een begrensde overdracht mag de softwarematige totale netgrens tijdelijk worden overschreden. Fase-, kwartier- en batterijcontroles blijven afzonderlijk gelden. De gewone vijfminutenwolkenbuffer loopt parallel op de ruwe netafname.

Een handmatig ingeschakeld SG-contact behoudt de oorspronkelijke afteller van vijftien minuten. De bestaande automatische overname- en handmatige UIT-voorwaarden blijven gelden.

[Installatie en rollback](docs/BETA108_INSTELLEN.md) · [Actuele werking](docs/ACTUELE_WERKING.md) · [Testverslag](docs/TESTRESULTATEN_BETA108.md) · [Overdracht](OVERDRACHT.md)
