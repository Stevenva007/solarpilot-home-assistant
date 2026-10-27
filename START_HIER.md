# SolarPilot starten of bijwerken

Installeer **1.0.0-beta.110** via HACS, herstart Home Assistant volledig en herlaad de app of browser.

SolarPilot gebruikt het echte huidige overschot zonder toekomstige toestelpieken te reserveren. Controleer onder **Voorrang** de centrale volgorde; een eerder bewust opgeslagen keuze blijft behouden. De SG-raming betreft vanaf deze versie het totale warmtepompvermogen bij SG, standaard 3000 W. Alleen compleet actueel gemeten HP-vermogen wordt eenmaal afgetrokken om de mogelijke extra opname te toetsen.

SG vóór een bevestigde autonome zonneladende Wallbox geeft de laadpaal standaard vier minuten om zelf terug te regelen. De begrensde uitzondering betreft de softwarematige totale netgrens. De gewone vijfminutenwolkenbuffer loopt parallel; actuele fase-, kwartier-, batterij- en broncontroles blijven gelden. Een handmatig ingeschakeld SG-contact behoudt zijn oorspronkelijke vijftien minuten waarneming.

Een **firmwareversiewijziging alleen** blokkeert SG niet en vraagt geen handmatige herbevestiging. SolarPilot controleert dezelfde fysieke uitgang en actuele configuratie/timer automatisch. Een oude firmware-only-blokkade herstelt bij passend bewaard hardwarebewijs en een verse geldige uitlezing; een echte andere koppeling of onbruikbare timer houdt haar afzonderlijke controlevoorwaarden.

[Installatie en rollback](docs/BETA110_INSTELLEN.md) · [Actuele werking](docs/ACTUELE_WERKING.md) · [Testverslag](docs/TESTRESULTATEN_BETA110.md) · [Overdracht](OVERDRACHT.md)
