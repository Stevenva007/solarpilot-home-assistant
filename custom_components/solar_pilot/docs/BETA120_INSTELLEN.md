# SolarPilot beta.120 — installatie en rollback

## Wat deze versie oplost

Aquarea publiceerde v3.0.0 als prerelease met het integratiedomein `aquarea_smart_cloud`. De defaultbranch draaide die domeinverplaatsing dezelfde dag terug; stabiele v2.0.1 blijft `aquarea` gebruiken. De onderliggende uitleescontracten en de werkelijk vereiste `aioaquarea-ng` v1.6.0 veranderden niet.

Beta.120 kan één werkelijk geladen officiële provider onder een van beide exacte domeinen read-only volgen. Registryplatform, config-entry, apparaatidentifier, coordinator-module, unique-id, geladen SDK-capability, LIVE-status, bronwaarde en oorspronkelijke rapporttijd moeten hetzelfde domein en apparaat bewijzen. Twee geladen Aquarea-domeinen, een gemengde identiteit of een zelfgekozen variant blijven onbekend.

SolarPilot installeert, verwijdert, selecteert, migreert of hernoemt Aquarea niet. Er komt geen sensorbinding, extra polling of Panasonic-opdracht bij. Pompstatus, taak, richting en energieperioden behouden hun bestaande betekenis en voorwaarden.

## Bijwerken en controleren

1. Maak een volledige privé Home Assistant-back-up met SolarPilot-configuratie en -opslag.
2. Installeer na geslaagde publicatie **1.0.0-beta.120** via HACS.
3. Herstart Home Assistant volledig en herlaad browser of app. Controleer backend- en geladen kaartversie.
4. Laat de bestaande Aquarea-installatie en entity-id's ongewijzigd. Controleer dat de read-only warmtepomptaak alleen verschijnt bij actuele passende brongegevens.
5. Bij een onbekende taak: controleer lokaal welke Aquarea-provider werkelijk geladen is en of geen oude en nieuwe domeinen tegelijk actief zijn. Installeer niet automatisch een prerelease om alleen deze functie te testen.

De update wijzigt geen SolarPilot-opslagformaat, bronbinding of apparaatinstelling en vraagt geen fysieke SG-proef.

## Rollback

Installeer beta.119 via HACS, herstart Home Assistant en herlaad de browser of app. Het opslagformaat is gelijk. Beta.119 herkent `aquarea_smart_cloud` niet als gecontroleerde bron, zodat de read-only taakcontext bij een lokale v3-prerelease-installatie onbekend kan worden; het stabiele `aquarea`-domein blijft werken. Herstel voor een volledige rollback de passende privéback-up.

Zie [TESTRESULTATEN_BETA120.md](TESTRESULTATEN_BETA120.md) voor validatie en bewijsgrenzen.
