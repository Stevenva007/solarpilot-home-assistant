# SolarPilot 1.0.0-beta.66 — testresultaten

Datum: **2026-10-10**. De definitieve lokale softwaresuites, echte Home Assistant Core-proeven en lokale releasecontroles zijn geslaagd. De echte browsercontrole via CI, GitHub-publicatie en gedownloade pakketverificatie zijn afzonderlijke releasegates; dit verslag claimt geen toekomstige uitvoering daarvan.

## Bronbasis en gerichte wijziging

Gecontroleerde bouwbasis: gepubliceerde [beta.65](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.65), main-commit `e5bff1f81a1ba9e50da060fc961bbe7722d7da63`. Haar vijf CI-gates en publicatie zijn geslaagd in [workflow 38066255828](https://github.com/Stevenva007/solarpilot-home-assistant/actions/runs/38066255828). Dit is historisch basisbewijs, geen beta.66-validatie. Oude tags en assets blijven onveranderd. Actuele versie: **1.0.0-beta.66**, canonieke guidehash **`bcbf9dbd28d16615`**.

Beta.66 voegt afzonderlijke read-only meetactiviteit toe. Bestaande bronkoppelingen en standaard **200 W** werken zonder nieuwe configuratie voor deze update; voedingsrollen en weergaveverfijning zijn optioneel. Complete actieve/nul/lage meting en gedeeltelijke voedingsmeting blijven onderscheiden. Afgeleide activiteit bewijst geen aparte compressor-/warmteproductie.

Sanitair water opwarmen vereist complete verse actieve meting en expliciete verse tankactie of geverifieerde HEATING_WATER uit de actuele poll van het exact gebonden Aquarea-apparaat. Alleen een gekozen heating-tankstand volstaat niet. Dezelfde strikte displayreader kan HEATING (2)/COOLING (3) voor ruimtefunctie en HEATING_WATER (4) voor DHW gebruiken, uitsluitend met verse beschikbare gebonden WH en actueel pollbewijs. Echte actieconflicten geven geen functieclaim. De controllerprogrammalezing en SG-autoriteit veranderen niet.

Actief elektrisch verbruik kan het hoofdlabel blijven bij native rust/0 Hz; het afzonderlijke compressor-/rustbewijs blijft zichtbaar in de uitleg en er verschijnt geen draaiende ventilator. Zonder bruikbaar bewijs geen prominente Werking onbekend-badge of apart onbekend-bedrijfsblok. Metingen, SG-lagen, beslisreden, Details en technisch diagnose-/exportbewijs blijven behouden.

## Definitieve lokale softwaregate

| Controle | Werkelijk beta.66-resultaat |
| --- | --- |
| Volledige pytest, Python 3.12 | **3215 geslaagd in 42,45 s**. |
| Volledige pytest, Python 3.14 | **3215 geslaagd in 41,38 s**. |
| Officiële lokale Hassfest | **1 integratie, 0 ongeldige integraties; geslaagd in 1,05 s**. |
| Canonieke uitleg en exacte mirrors | **Geslaagd**; guidehash `bcbf9dbd28d16615`. |
| Overdracht, SG-bevoegdheidsgrens, syntax en diff | **Geslaagd**. |
| Privacy-/publieke repositorypreflight | **Geslaagd**, na verwijderen van gegenereerde Python-caches. |

Een eerdere volledige Python 3.12-run vond één fout in de releasegebonden optiehulpversie naast 3214 geslaagde cases. De assetheader en JSON-versiequery zijn gecorrigeerd; de gerichte reproductie slaagde met **1 test in 0,04 s**. Daarna slaagde de hierboven vermelde volledige herhaling. De gerichte test is onderdeel van de volledige suite en wordt niet extra bij de teller opgeteld. De twee volledige runs toetsen dezelfde cases op verschillende Python-versies.

Regressies toetsen complete/partiële actieve/nul/lage meting, de automatische 200 W-standaard, optionele voedingsrollen, expliciete tankactie versus gekozen heating-mode, exact gebonden verse native poll, alle drie DeviceAction-functies, oude/onbeschikbare/verkeerde/conflicterende bronnen, afgeleid verbruik versus Hz-bewijs en behoud van SG-policy, timer, autorisatie en bestaande configuratie. Frontend-/Node-/broncontroles zijn geen bewijs van een echte gerenderde browserproef.

## Echte Home Assistant Core-entrygate

Omgeving: **Home Assistant Core 2026.10.0**, fictieve bronnen en tijdelijke opslag; geen live huisconfiguratie of fysieke apparaten.

| Werkelijke proef | Resultaat |
| --- | --- |
| Legacyfixture: productie-entry setup/reload/unload | **Geslaagd**; opties en privéarchief behouden. |
| Actuele SG-fixture: productie-entry setup/reload/unload | **Geslaagd**; opties en privéarchief behouden. |
| Registry-entiteiten | Beide fixtures laden **58 entiteiten**. |
| Fysieke servicecalls | Beide fixtures: **0**. |
| Automatische meetweergave zonder nieuwe displayconfiguratievelden | **Geslaagd**: 1400 W → Warmtepomp werkt; 58 W + 0 W → Basisverbruik; 0 W + 0 W → Geen elektrisch verbruik. |

De productie-entry en platforms zijn echt; bronwaarden en apparaten zijn fictief. Deze proeven bevestigen laden, herladen en unload met behoud van gegevens en werking van de standaardweergave zonder extra invoer. Zij bewijzen geen lokaal geladen mobiele kaart, werkelijke elektrische meterdekking, ontvangen SG of fysieke Panasonic-reactie.

De eerder waargenomen `via_device`-deprecatiewaarschuwing met aangekondigde grens bij Home Assistant **2027.8** blijft een toekomstige compatibiliteitsbeperking. Deze presentatie-update wijzigt dat registratiepad niet.

## Echte browsercontrole via CI

Een echte lokale browserrender is **niet uitgevoerd**: er is geen bruikbare lokale Chromium beschikbaar. De actuele CI-browsergate moet de productiekaart renderen; lokaal geslaagde software-/DOM-/Node-controles vervangen die stap niet.

De browserchecker omvat Overzicht, Toestellen en Warmtepomp bij breedtes **320, 390, 768 en 1280 px**, met meetactiviteit, functiecontext, SG-/bron-/klok-/leasebewijs, gedeeltelijke meting/nul, verminderde beweging, Details/focus en nul apparaatopdrachten in de fixture. Versieverschil en laden naast een oudere paneelklasse behoren afzonderlijk tot de pytest-/Node-/broncontroles. Werkelijke CI-uitslag is te verifiëren bij [Actions](https://github.com/Stevenva007/solarpilot-home-assistant/actions); de historische beta.65-browsergate is geen beta.66-renderbewijs.

## CI, publicatie en pakketintegriteit

Publicatie is afhankelijk van **vijf geslaagde actuele gates** op de exact geteste bron: repositorytests, HACS, Hassfest, echte HA-startup en browser-UI. De workflow controleert de geteste bronherkomst. Exact workflow-/tag-/publicatiebewijs staat bij [Actions](https://github.com/Stevenva007/solarpilot-home-assistant/actions) en de [beta.66-release](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.66) zodra gepubliceerd. Deze links claimen geen reeds voltooide beta.66-publicatie.

`check_release_packages.py` moet beide installatie-ZIPs byte voor byte met de exacte geteste Git-bron vergelijken, inclusief versies, ledenlijst en documentmirrors. Na publicatie worden alle vier gedownloade assets op bronherkomst, grootte en SHA-256 gecontroleerd. Lokale softwarevalidatie bewijst geen pakketupload of geslaagde terugdownload; deze releasegates blijven afzonderlijk te verifiëren.

## Behouden grenzen en lokale acceptatie

Panasonic blijft exclusief eigenaar van zijn normale warmtepompregeling. Alleen de bestaande expliciet toegewezen SG-uitgang is een warmtepompactuator van SolarPilot. De read-only meetlaag en automatische native actie-uitlezing veranderen geen SG-policy, bronvalidatie, lease, koel-/native vrijgave of bestaande lokale bevestigingen. Een ongewijzigde geldige beta.65-configuratie vraagt geen nieuwe ingebruikname wegens de update.

De fysieke gebruikersinstallatie en een echte optionele ontvangen-SG-bron zijn niet geaccepteerd in deze softwareproeven. Zonder passende actuele SG-bron blijft ontvangen status onbekend. Technische onbekendheid blijft behouden in diagnose/export; afgeleide elektrische activiteit is geen aparte compressor-/warmteproductiemeting. De historische stilstand heeft geen bewezen oorzaak en rechtvaardigt geen contactpulsen, reboottrucs of directe Panasonic-writes.

Installatie, update/herstart/herladen en rollback naar beta.65 staan in `BETA66_INSTELLEN.md`. Voor de nieuwe weergave hoef je geen nieuw configuratieformulier in te vullen. Fysieke SG-/timerproeven blijven afzonderlijk en vereisen hun eigen toestemming. De volledige actuele werking staat in `ACTUELE_WERKING.md` en **SolarPilot → Uitleg**. Privé-entiteiten, netwerkgegevens, tokens, ruwe thuismetingen en back-ups horen niet in publieke bron of pakketten.
