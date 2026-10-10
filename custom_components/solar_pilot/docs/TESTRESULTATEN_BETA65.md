# SolarPilot 1.0.0-beta.65 — testresultaten

Datum: **2026-10-10**. De definitieve lokale softwaresuites en echte Home Assistant Core-proeven zijn geslaagd. De echte browsercontrole via CI, GitHub-publicatie, pakketverificatie en fysieke ingebruikname blijven afzonderlijke bewijsstappen.

## Bronbasis en wijziging

Bouwbasis: gepubliceerde [beta.64](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.64), main-commit `103399152d45017c621ca9e6af528c090bb96dec`. Bestaande tags en assets blijven onveranderd. De actuele bronversie is **1.0.0-beta.65**; canonieke guidehash **`4eadbf462b459467`**.

Beta.65 herstelt de warmtepompweergave in Warmtepomp en voegt haar toe tussen de andere blokken in Overzicht en Toestellen. Grafische activiteit volgt afzonderlijk read-only bedrijfsbewijs. Verse gevalideerde compressorfrequentie is leidend; alleen zonder gekoppelde compressorbron kan passende verse native activiteit bedrijf of rust bevestigen. Een gekoppelde maar onbetrouwbare compressorbron blijft onbekend. Vermogen, WATER-/klepstand en gekozen HEAT-programma bewijzen geen productie.

SolarPilot-aanvraag, gemelde SG-contactstand/lokale timer en ontvangen SG-status krijgen afzonderlijke aanduidingen. Iedere bron behoudt haar eigen actualiteitsgrens. Het zijbalkpaneel gebruikt de releasekaart; een reeds geladen gewone Lovelace-kaart vereist volledige pagina/app-herlading. Backend- en kaartversie zijn afzonderlijk zichtbaar onderaan bij **Instellingen & controle**. De nieuwe veranderlijke presentatiewaarnemingstijden zijn alleen van de herhaalde Recorder-attributenkopie uitgesloten; live attributen, sensorwaarden, eigen metingen en export blijven behouden.

## Definitieve lokale softwaregate

| Controle | Werkelijk resultaat |
| --- | --- |
| Volledige pytest, Python 3.12 | **3023 geslaagd in 41,64 s**. |
| Volledige pytest, Python 3.14.2 | **3023 geslaagd in 41,02 s**. |
| Officiële lokale Hassfest-validatie | **0 ongeldige integraties; geslaagd**. |
| Canonieke huidige uitleg | Versie **1.0.0-beta.65**, guidehash **`4eadbf462b459467`**. |

De twee volledige suites controleren dezelfde bron op verschillende Python-versies; tel ze niet op als afzonderlijke functionele cases. Echte Core-proeven hieronder staan apart van de pytest-teller. Historische beta.64-resultaten zijn geen beta.65-testbewijs.

De regressies controleren bedrijfsbewijs versus gekozen programma/vermogen, fallback alleen zonder gekoppelde compressorbron, afzonderlijke oude/onbeschikbare bronnen, nul en onbekend, gescheiden SG-aanvraag/contact/ontvangen, de warmtepompblokken en het ontbreken van vervallen boiler-/klimaatmeldingen. Ook versiegebonden paneelregistratie, zichtbare backend-/kaartversie, ongewijzigde SG-policy en behouden bestaande apparaat-/configuratie-/opslaggrenzen worden gecontroleerd.

## Echte Home Assistant Core-entrygate

Omgeving: **Home Assistant Core 2026.10.0 met Python 3.14.2**, fictieve configuratie en entiteiten. De proeven gebruiken echte productie-entry setup, reload en unload; geen live huisconfiguratie of fysiek apparaat.

| Werkelijke proef | Resultaat |
| --- | --- |
| Productie-entry setup, reload en unload | **Geslaagd**. |
| Actuele synthetische SG-fixture | **Geslaagd**; huidige SG-configuratie en bronbewijs gecontroleerd. |
| Registry-entiteiten | **58 entiteiten**. |
| Configuratie en privéarchief | **Behouden** door setup/reload/unload. |
| Fysieke servicecalls | **0**. |

De checker gebruikt fictieve bronwaarden en tijdelijke opslag; de SolarPilot-entry en productieplatforms zijn echt. Deze acceptatie bewijst dat de integratie binnen echte Core kan laden en herladen met behoud van haar gegevens. Zij bewijst geen lokaal geladen mobiele kaart, fysiek SG-contact, wifi-terugval of Panasonic-reactie.

De echte HA-log bevat wel een **`via_device`-deprecatiewaarschuwing met een aangekondigde grens bij Home Assistant 2027.8**. De huidige Core-proef slaagt; de waarschuwing blijft een toekomstige compatibiliteitsbeperking die vóór die versie onderzocht en opgelost moet worden. Deze release wijzigt dat registratiepad niet.

## Browsercontrole: nog te bevestigen via CI

Een echte lokale browserrender is **niet uitgevoerd**. De lokale browserinstallatie bleef geblokkeerd doordat de download onvolledig/afgekapt was en geen bruikbare browserbinary opleverde. Software-/DOM-/Node-controles vormen geen vervanging voor een echte gerenderde browserproef.

Een vijfde GitHub CI-gate voor echte browserweergave is toegevoegd. Haar geplande scope is Overzicht, Toestellen en Warmtepomp bij breedtes **320, 390, 768 en 1280 px**; activiteit/rust/onbekend, afzonderlijke SG-lagen, verlopen bron-/klok-/leasebewijs, gedeeltelijke meting en bekende nul, verminderde beweging, behoud van open Details en focus, en nul apparaatopdrachten in de fixture. Versieverschil en laden naast een oudere paneelklasse behoren afzonderlijk tot de pytest-/Node-/broncontroles, niet tot deze browserchecker. Het toevoegen van de gate is **geen bewijs van geslaagde uitvoering**. Werkelijk resultaat, workflow en exacte broncommit worden bij oplevering afzonderlijk vermeld.

Een bestaande oude Lovelace-kaart kan de nieuwe versieverschilwaarschuwing nog niet tonen. Daarom blijft na de update een volledige pagina-herlading of volledig afsluiten en heropenen van de app nodig, gevolgd door controle van beide versievelden.

## CI, publicatie en pakketintegriteit

De lokale resultaten claimen geen toekomstige CI- of uploadsuccessen. Publicatie blijft afhankelijk van vijf geslaagde gates: repositorytests, HACS, Hassfest, echte HA-startup en browser-UI. De release moet naar exact de geteste commit verwijzen; oudere tags/assets worden niet vervangen.

Beide installatie-ZIPs moeten byte voor byte worden vergeleken met de exacte Git-bron, inclusief versies, ledenlijst en documentmirrors. Na publicatie moeten alle vier gedownloade assets opnieuw op bronherkomst, grootte en SHA-256 worden gecontroleerd. Deze tekst claimt geen reeds geslaagde pakketupload of downloadverificatie.

Publieke bewijsplaatsen: [Actions](https://github.com/Stevenva007/solarpilot-home-assistant/actions) en de [beta.65-release](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.65) zodra gepubliceerd. De actuele uitleg, test-/installatiemirrors en releasepakketten horen bij dezelfde bron.

## Behouden gedrag en bewijsgrenzen

Panasonic blijft exclusief eigenaar van normaal comfort, tank-/kamertemperaturen, programma, compressor, pompen, elektrische ondersteuning en sterilisatie. SolarPilot heeft uitsluitend de bestaande expliciet toegewezen SG-uitgang als warmtepompactuator. De bestaande lokale timer, sessie-/herbeoordelings-/koel-/bron-/voorrangsvoorwaarden en andere apparaten blijven behouden. Een ongewijzigde geldige beta.64-configuratie vraagt geen nieuwe SG-ingebruikname wegens de codeupdate.

De fysieke gebruikersinstallatie is **niet uitgelezen of geaccepteerd**. Werkelijke elektrische meterdekking, contactmapping, lokale timerafloop, bestaande condensbeveiliging en Panasonic-reactie blijven lokale bewijsstappen. De echte optionele bronentiteit voor **ontvangen SG-status is niet aangeleverd**; synthetische softwaretests bevestigen geen fysiek ontvangen SG. Zonder passende echte actuele bron moet de kaart ontvangen status als onbekend tonen, ook bij een gemeld AAN-contact.

De historische stilstand heeft geen vastgestelde oorzaak. De presentatieverbeteringen geven geen recht op periodieke contactpulsen, reboottrucs, Force-opdrachten of directe Panasonic-writes. Publieke bron en fixtures bevatten generieke voorbeelden; private entiteitskoppelingen, netwerkgegevens, tokens, ruwe thuismetingen en back-ups horen daar niet in.

Installatie, read-only upgradecontrole en rollback naar beta.64 staan in `BETA65_INSTELLEN.md`. Fysieke SG-/timerproeven blijven afzonderlijk en vereisen hun eigen toestemming. De volledige actuele werking staat in de gegenereerde `ACTUELE_WERKING.md` en **SolarPilot → Uitleg**.
