# SolarPilot beta.91 — installatie en upgrade

Versie: **1.0.0-beta.91** · 15 oktober 2026

Beta.91 verwerkt Aquarea 1.5.4, bronvaste cloudenergieperioden, tijdelijke leerwacht, aparte vooruitvoorspelreeksen, SG-sessieherkomst en herstelbewijs. Het bewaart een geldig opgeslagen lager vermogen van een regelbaar toestel bij herstart. De beta.90-route voor tijdelijk offline toestellen blijft behouden: globale Auto is kiesbaar, elke 300 seconden herbeoordeling, geen onzekere opdracht herhalen en geen extra hypothetische offline-zonreserve.

## Bijwerken

1. Bewaar een actuele volledige privé Home Assistant-back-up met instellingen, SolarPilot-opslag, modellen, APP-aanvragen, historie en userfiles.
2. Geef een eigen SG-aanvraag veilig vrij waar betrouwbaar mogelijk en controleer contact of lokale afloop. Onderbreek geen beschermde apparaatcyclus.
3. Download exact **1.0.0-beta.91** via HACS zodra de release gepubliceerd is. Lokaal vervang je uitsluitend `custom_components/solar_pilot`, met behoud van userfiles en HA-opslag.
4. **Herstart Home Assistant volledig** en herlaad browser/app volledig. Controleer backend- en kaartversie afzonderlijk. Behoud dezelfde integratie-entry en bestaande sensorkoppelingen.
5. Controleer de actuele taakweergave, SG-details, Meetkwaliteit en de volgende bewuste analyse-export. Nieuwe prognosereeksen verzamelen vanaf deze versie; er is nog geen bewijs voor een gewijzigde correctiefactor of gerealiseerde besparing.

Bestaande instellingen, rangorde, Wallbox-voorkeuren met eindtijden, minimumtijden, deadlines, modellen en historie blijven behouden. Nieuwe SG-vrijgave, providerupdate of hardwareproef wordt niet door deze update uitgevoerd. Een echte interne foutpauze blijft gericht beschermd.

## Berekend SG-boilerdoel

Bij een geldig normaal doel van **50 °C** en een lokaal vastgelegd **115%** weergaveprofiel is het berekende SG-doel **57,5 °C**. Dit blijft een berekening, ook als de contactstand onbekend is. Panasonic hoeft dit berekende doel niet terug te melden.

Is het weergavepercentage of de bronbinding lokaal nog niet vastgelegd? Open bij de boilerwaarden **SG-doel voor weergave instellen**, of **Instellen → Warmtepomp → SG-leesbronnen**. Selecteer de juiste native tankdoelbron, vul het reeds op Panasonic ingestelde percentage in en bevestig de weergave. Dit wijzigt geen Panasonic-instelling. Een algemene SG-profielvrijgave of geïmporteerd advies is geen vastgelegd percentage voor alle installaties. Bestaande geldige bevestigingen blijven staan; de update zet een 115%-profiel niet terug naar 100%.

## Bron- en bewijsgrenzen

Aquarea 1.5.4 met aioaquarea-ng 1.3.1 is de actuele gecontroleerde bron. Toelating volgt de daadwerkelijk geladen semantiek en gegevensstructuur, zodat toekomstige compatibele versies blijven werken zonder nieuwe versielijst. Een bewezen semantiekwijziging geeft één afzonderlijke compatibiliteitsmelding; gewone offline-/brongaten doen dat niet. Historische punten behouden hun eigen oorspronkelijke contractbewijs. De conservatieve leerclassificatie en SG-koelvrijgave blijven dezelfde. Een presentatie die een taak toont bewijst geen nieuwe koel- of actuatorvrijgave.

Cloudenergie gebruikt alleen een daadwerkelijk uitgelezen native periode. UTC-cloudtotalen en lokale SolarPilot-dagen worden niet automatisch met elkaar gelijkgesteld. Ontbrekende periodegegevens en oorspronkelijke provideruitgiftetijden blijven onbekend.

Nieuwe PV-vergelijkingen leggen vooraf per doel/binding/termijn de eerste geldige voorspelling vast. Hetzelfde oorspronkelijke meterbericht wordt binnen dat doel gedeeld. Oude gegevens worden niet teruggevuld. Daglicht, unieke doelen, verschillende dagen en afhankelijkheid staan afzonderlijk in de diagnose.

Nieuwe SG-sessies bewaren de regels van hun eigen start; een huidige exportversie vult geen oude sessie aan. Aanvraag, gemelde contactstand, stopbesluit en transportuitkomst blijven verschillende bewijzen. De berekende temperatuurvergelijking bestuurt geen warmtepomp.

## Rollback naar beta.90

Maak eerst een actuele volledige privéback-up, geef de eigen SG-aanvraag veilig vrij waar betrouwbaar mogelijk en controleer de lokale afloop. Stop beta.91 en herstel gecontroleerde beta.90-code met behoud van entry, opslag en userfiles. Herstart Home Assistant volledig en herlaad browser/app.

Beta.90 behoudt de automatische toestelherstelroute, restzonverdeling en Wallbox-voorkeuren. De nieuwe bron-/sessie-/prognosevelden worden door oudere code mogelijk niet getoond of bij nieuwe opslag bewaard; exact herstel vraagt passende code én een volledige privéback-up. De fix voor het lagere opgeslagen number-doel en Aquarea 1.5.4-presentatie vervallen. Gebruik geen twee runtimes tegelijk en herstel nooit een oude onverbruikte APP-aanvraag nadat dezelfde belading fysiek gestart is.

Volledige werking: [ACTUELE_WERKING.md](ACTUELE_WERKING.md). Tests en publicatiestatus: [TESTRESULTATEN_BETA91.md](TESTRESULTATEN_BETA91.md). Technische overdracht: [OVERDRACHT.md](../OVERDRACHT.md).

## Controle bij iedere update

Iedere nieuwe SolarPilot-update controleert de actuele Aquarea-defaultbranch, laatste gepubliceerde release en werkelijke SDK-bron. Vergelijk met docs/upstream_review.json, beoordeel alle relevante nieuwe verschillen en verwerk noodzakelijke wijzigingen met regressies in dezelfde release. tools/check_upstream_review.py blokkeert publicatie bij onbeoordeelde bronwijzigingen of mislukte controle. Een open PR of prerelease wordt niet automatisch geïnstalleerd. De bestaande onderhoudstaak onderzoekt compatibiliteitswijzigingen zelfstandig, bouwt en test de noodzakelijke SolarPilot-correctie en kan een GitHub/HACS-release publiceren met een melding en release-link. Deze taak installeert geen software in Home Assistant; volg HACS. Lokale meldingen worden niet automatisch geüpload.
