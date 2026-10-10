# SolarPilot 1.0.0-beta.67 — testresultaten

Datum: **2026-10-11**. De definitieve lokale softwaresuites, echte Home Assistant Core-proeven en lokale releasecontroles zijn geslaagd. Echte browsercontrole via CI, publicatie en verificatie van de gedownloade release-assets blijven afzonderlijke gates; dit verslag claimt geen toekomstige uitvoering daarvan.

## Bronbasis en gerichte wijziging

Gecontroleerde bouwbasis: gepubliceerde [beta.66](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.66), main-commit `16d78d94cd95063211d86ef6524dee43156188eb`. Haar vijf CI-gates en publicatie zijn geslaagd in [workflow 38085386498](https://github.com/Stevenva007/solarpilot-home-assistant/actions/runs/38085386498); de release is gepubliceerd op **2026-10-10 om 20:53:14 UTC**. Dit is historisch basisbewijs, geen beta.67-validatie. Oude tags en assets blijven onveranderd.

Beta.67 werkt de automatische read-only uitleg van warmtepomptaak, elektrische activiteit, beide voedingsmetingen en animaties verder uit. De gemelde SG-contactstand staat prominent, aanvraag in Details en ontvangen SG uitsluitend bij actueel bevestigd bronbewijs. Zij breidt tevens lokale analyse-export en optionele read-only JSON-adviesupload uit; herkomstmatch en rapportvalidatie geven geen toepasrecht. De precieze bronbetekenis staat in `ACTUELE_WERKING.md`; SG-aanvraag, gemelde uitgang en werkelijk ontvangen SG blijven afzonderlijke lagen. Bestaande koppelingen worden gebruikt zonder nieuwe verplichte gebruikersinvoer. Verse werkelijke native taak staat los van de metergrens; tankroute-afleiding vereist verse actieve hoofdvoeding en compleet totaal. Heater-only geeft geen thermische functie. Werkelijke actieconflicten en geverifieerde verse ontdooiing onderdrukken gewone functieclaims; een gekozen koelprogramma met tankmogelijkheid is geen zelfstandig actieconflict. Een presentatie-afleiding levert geen controllerrecht of afzonderlijke warmteproductiemeting.

De regressies toetsen Meetkwaliteit/éénklikexport zonder leervragen, exacte geëxporteerde én actuele bevindingrevisie, reviewed tegenover needs_more_data zonder beleidswijziging, begrensde exportinhoud, bronassociatie, schema-/grootte-/beheerdersvalidatie en rapportbehoud. Zij toetsen tevens nul instelling-/code-/service-/controlwijzigingen bij rapportupload, vertrouwde voorstelstatus tegenover uploadclaims en de vergelijking van voorstelinhoud en geïnstalleerde release.

## Definitieve lokale softwaregate

| Controle | Werkelijk beta.67-resultaat |
| --- | --- |
| Volledige pytest, Python 3.12 | **3534 geslaagd in 52,50 s**. |
| Volledige pytest, Python 3.14 | **3534 geslaagd in 52,28 s**. |
| Officiële lokale Hassfest | **1 geldige integratie, 0 ongeldige; geslaagd in 1,326 s**. |
| Canonieke uitleg, guidehash en exacte mirrors | **Geslaagd**; guidehash `5879c0b8cd8905d4`. |
| Overdracht, SG-bevoegdheidsgrens, Python-/Node-syntax en diff | **Geslaagd**; AST-parse van alle 72 productie-Pythonbestanden en Node-controle van de kaart. |
| Privacy-/publieke repositorypreflight | **Geslaagd**. |

De twee volledige runs toetsen dezelfde cases op verschillende Python-versies; de aantallen worden niet bij elkaar opgeteld. Eerder gevonden fixture-, bronredactie- en klokgrensfouten zijn gecorrigeerd vóór deze volledige herhalingen. De onafhankelijke gerichte eindcontrole slaagde met **132 tests** zonder resterende blokkade; gerichte controles tellen niet extra bij een volledige suite. Testresultaten van beta.66 zijn geen beta.67-validatie. Software-/DOM-/Node-/broncontroles zijn geen bewijs van een echte gerenderde browserproef.

## Echte Home Assistant Core-entrygate

Omgeving: **Home Assistant Core 2026.10.0**, fictieve bronnen en tijdelijke opslag; geen live huisconfiguratie of fysieke apparaten.

| Werkelijke proef | Resultaat |
| --- | --- |
| Legacyfixture: productie-entry setup/reload/unload | **Geslaagd in 2,099 s**; opties en privéarchief behouden. |
| Actuele SG-fixture: productie-entry setup/reload/unload | **Geslaagd in 2,188 s**; opties en privéarchief behouden. |
| Registry-entiteiten | Beide fixtures laden **58 entiteiten**. |
| Fysieke servicecalls | Beide fixtures: **0**. |
| Beheerderexport en antwoordrapport | **Geslaagd** in beide fixtures: exporthash gecontroleerd, brongekoppelde import, Store-behoud over reload en rapport verwijderen. |
| Bevoegdheden en read-only grenzen | **Geslaagd**: onbevoegde export/import en uitvoerbare extra rapportvelden geweigerd; opties, SG-toestand, leerbeleid en bestaande antwoorden behouden. |
| Onveranderbare beta.62-opties als regressiereproductie | **Geslaagd in 2,009 s**; configuratie behouden. |

De productie-entry en platforms zijn echt; bronwaarden en apparaten zijn fictief. De analyseproef gebruikt een synthetisch rapport en bewijst geen ontvangst of uitvoering van een echt gebruikersadvies. Het implementatieregister begint leeg.

Een productie-entryproef bewijst geen lokaal geladen mobiele kaart, werkelijke elektrische meterdekking, ontvangen SG of fysieke Panasonic-reactie. De eerder waargenomen `via_device`-deprecatiewaarschuwing met aangekondigde grens bij Home Assistant **2027.8** blijft een toekomstige compatibiliteitsbeperking zolang het registratiepad niet is aangepast.

## Echte browsercontrole en CI

Een echte lokale browserrender is **niet uitgevoerd**: er is geen bruikbare lokale Chromium beschikbaar. De actuele CI-browsergate moet de productiekaart renderen; lokaal geslaagde software-/DOM-/Node-controles vervangen die stap niet. Historische beta.66-browserresultaten zijn geen beta.67-renderbewijs.

De browserchecker omvat Overzicht, Toestellen en Warmtepomp bij **320, 390, 768 en 1280 px**, afzonderlijke taak-/heater-/meter-/SG-bronnen, animaties en verminderde beweging, onvolledige/nulmetingen, bron-/klok-/leaseverloop en behoud van Details/focus. De analysefixture controleert éénklikexport, het exact gekoppelde sjabloon, begrensde escaped rapportweergave, herladen/verwijderen, beheerdersgrenzen en nul apparaatopdrachten. Versieverschil en laden naast een oudere paneelklasse behoren afzonderlijk tot pytest-/Node-/broncontroles. De werkelijke browseruitslag volgt de actuele CI-gate.

Publicatie vereist **vijf geslaagde actuele gates** op de exact geteste bron: repositorytests, HACS, Hassfest, echte HA-startup en browser-UI. De workflow controleert de geteste bronherkomst. Exact workflow-/tag-/publicatiebewijs staat bij [Actions](https://github.com/Stevenva007/solarpilot-home-assistant/actions) en de [beta.67-release](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.67) zodra gepubliceerd. Deze links claimen geen reeds voltooide beta.67-publicatie.

## Pakketintegriteit

`check_release_packages.py` moet beide installatie-ZIPs byte voor byte met de exacte geteste Git-bron vergelijken, inclusief versies, ledenlijst en documentmirrors. Na publicatie worden alle vier gedownloade assets op bronherkomst, grootte en SHA-256 gecontroleerd. Lokale softwarevalidatie bewijst geen pakketupload of geslaagde terugdownload; deze gates worden na de daadwerkelijke bouw/publicatie afzonderlijk geverifieerd.

## Behouden grenzen en lokale acceptatie

Panasonic blijft exclusief eigenaar van zijn normale warmtepompregeling. Alleen de bestaande expliciet toegewezen SG-uitgang is een warmtepompactuator van SolarPilot. Read-only taak-/vermogen-/voedingsuitleg verandert geen SG-policy, bronvalidatie, lease, koel-/native vrijgave of bestaande lokale bevestigingen. Een ongewijzigde geldige beta.66-configuratie vraagt geen nieuwe ingebruikname wegens de update.

De fysieke gebruikersinstallatie en een echte optionele ontvangen-SG-bron zijn niet geaccepteerd in softwarefixtures. Zonder passende actuele SG-bron blijft ontvangen status onbekend. Technische onzekerheid blijft zichtbaar in Details/export; aangenomen voedingsrollen zijn geen bevestigde bedrading, heaterstatus of warmteproductie. De historische stilstand heeft geen bewezen oorzaak en rechtvaardigt geen contactpulsen, reboottrucs of directe Panasonic-writes.

Installatie, update/herstart/herladen en rollback naar beta.66 staan in `BETA67_INSTELLEN.md`. Voor de nieuwe weergave en automatische analysegegevens hoef je geen nieuw configuratieformulier in te vullen. Een bewust gedownload JSON.GZ-bestand kan hier worden geanalyseerd; een teruggegeven JSON-adviesrapport blijft optioneel en lokaal read-only. Adviezen wijzigen nooit automatisch instellingen, code of apparatuur. Fysieke SG-/timerproeven blijven afzonderlijk en vereisen hun eigen toestemming. De volledige actuele werking staat in `ACTUELE_WERKING.md` en **SolarPilot → Uitleg**. Privé-entiteiten, netwerkgegevens, tokens, ruwe thuismetingen en back-ups horen niet in publieke bron of pakketten.
