# SolarPilot 1.0.0-beta.68 — testresultaten

Datum: **2026-10-11**. De definitieve lokale softwaresuites, echte Home Assistant Core-proeven en lokale releasecontroles zijn geslaagd. Echte browsercontrole via CI, publicatie en verificatie van gedownloade release-assets blijven afzonderlijke gates; dit verslag claimt geen toekomstige uitvoering daarvan.

## Bronbasis en gerichte wijziging

Bouwbasis: gepubliceerde [beta.67](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.67), main-commit **`ed9d6fe421c5fa940f910503082fb458d897f6e8`**, tree **`78b781e372a4e9b1045ebdce19212ae2885a03f8`**. Alle vijf CI-gates, publicatie en bron-/bytegelijke controle van vier teruggedownloade assets zijn bevestigd in [workflow 38091919639](https://github.com/Stevenva007/solarpilot-home-assistant/actions/runs/38091919639). Release **409247151** is gepubliceerd op **2026-10-10 om 22:35:57 UTC**. Dit is historisch basisbewijs, geen beta.68-validatie. Oude tags en assets blijven onveranderd.

Beta.68 maakt de read-only taakweergave dynamischer. Complete verse actieve hoofdmeting met passende verse eenduidige gekozen verwarmings-/koelcontext kan **Verwarmen** of **Koelen** tonen ondanks een native cloud-idle/rustmelding. Expliciete actuele OFF, oude niet gespecificeerde inactiviteit, watts/context alleen, onvolledige/oude/conflicterende gegevens en heater-only geven deze ruimteafleiding niet. Werkelijke actuele tapwater-/ontdooitaak houdt voorrang; bestaande tankroute-afleiding blijft behouden. De korte andere taaklabels zijn **Boiler opwarmen** en **Ontdooien**, met **Afgeleid** als korte aanduiding voor een afleiding.

De hoofdkaart blijft compact. Zonder bruikbare taak blijft het taakvak weg; verse actieve meting kan generiek Warmtepomp werkt tonen. Ruwe native meldingen, geselecteerde stand, compressorbewijs, afleidingsbronnen, voedingsprofielaannamen en onzekerheden blijven in Details/export. Nieuwe registraties behouden getypeerde gekozen context en raw OFF/IDLE afzonderlijk; ontbrekende oude historie wordt niet aangevuld. De volledige beta.67-analyse-/antwoordrapportflow, overige apparaten, SG-policy en controlgrenzen blijven behouden.

## Definitieve lokale softwaregate

| Controle | Werkelijk beta.68-resultaat |
| --- | --- |
| Volledige pytest, Python 3.12 | **3650 geslaagd in 56,56 s**. |
| Volledige pytest, Python 3.14.2 | **3650 geslaagd in 55,41 s**. |
| Officiële lokale Hassfest | **1 geldige integratie, 0 ongeldige; geslaagd**. |
| Canonieke uitleg, guidehash en exacte mirrors | **Geslaagd**; guidehash `ea76974dfc2ba682`. |
| Overdracht, SG-bevoegdheidsgrens, syntax en diff | **Geslaagd**; Node-controle van de kaart en AST-parse van alle **72** productie-Pythonbestanden. |
| Privacy-/publieke repositorypreflight | **Geslaagd**. |

De twee volledige runs toetsen dezelfde cases op verschillende Python-versies en worden niet bij elkaar opgeteld. Gerichte controles zijn eveneens geslaagd: **27** analysecases, **221** UI-cases en **351** onafhankelijke reviewcases zonder resterende blokkade. Zij worden niet extra bij de volledige suites geteld. Oude beta.67-resultaten zijn geen beta.68-validatie.

De regressies toetsen complete verse taakafleiding met passende actuele gekozen verwarmings-/koelcontext, tolerantie voor typed idle en de veto's voor OFF/legacyinactive. Passende actuele displaycontext blijft voor iedere ruimteafleiding vereist; alleen oude controllercontext geeft geen functie. Werkelijke tapwater-/ontdooitaak, tankroute, incomplete/stale/conflict/heater-only, metingen/animatie en bronprovenance zijn getoetst. Compacte weergave bewaart informatie in Details. Export/rapport, exacte bron-/bevindingrevisie, beheerderrechten, begrenzingen, opslagbehoud en nul instelling-/code-/service-/controlwijziging blijven behouden. Bron-/DOM-/Node-controles bewijzen geen echte browserrender.

## Echte Home Assistant Core-entrygate

Omgeving: **Home Assistant Core 2026.10.0**, fictieve bronnen en tijdelijke opslag; geen live huisconfiguratie of fysieke apparaten.

| Werkelijke proef | Resultaat |
| --- | --- |
| Legacy- en actuele SG-fixture: productie-entry setup/reload/unload | Beide **geslaagd**. |
| Registry-entiteiten/platforms | Beide fixtures laden **58 entiteiten op 6 platforms**. |
| Fysieke servicecalls | Beide fixtures: **0**. |
| Onveranderbare opties en privéarchief | **Exact behouden**. |
| Beheerderexport, bronhash, rapportopslag en reload | **Geslaagd**, zonder instelling-/regelwijziging. |
| Dynamische taak zonder extra displayconfiguratie | **Geslaagd** in de actuele SG-fixture: fictieve hoofdvoeding **1360 W**, ondersteuning **0 W** en passende verse gekozen verwarmingscontext geven de afgeleide ruimtefunctie; oorspronkelijke operation/context en SG blijven behouden. |

De productie-entry en platforms zijn echt; bronwaarden en apparaten zijn fictief. De rapportproef gebruikt synthetische gegevens en bewijst geen ontvangst of uitvoering van een echt gebruikersadvies.

Softwarefixtures bewijzen geen lokaal geladen mobiele kaart, werkelijke bedrading/meterdekking, ontvangen SG of fysieke Panasonic-reactie. De eerder waargenomen `via_device`-deprecatiewaarschuwing met aangekondigde grens bij Home Assistant **2027.8** blijft een toekomstige compatibiliteitsbeperking zolang het registratiepad niet is aangepast.

## Echte browsercontrole en CI

Een echte lokale beta.68-browserrender is **niet uitgevoerd**: bruikbare lokale Chromium ontbreekt. De actuele CI-browsergate moet Overzicht, Toestellen en Warmtepomp met de dynamische taak en compacte labels renderen. Werkelijke dekking/resultaten worden aan de uitgevoerde bron gebonden; historische beta.67-browserbeelden vervangen deze stap niet. Bron-/DOM-/Node-controles zijn geen bewijs van een echte browserrender.

Publicatie vereist **vijf geslaagde actuele gates** op de exact geteste bron: repositorytests, HACS, Hassfest, echte HA-startup en browser-UI. De workflow controleert bronherkomst. Het uiteindelijke workflow-/tag-/publicatiebewijs staat bij [Actions](https://github.com/Stevenva007/solarpilot-home-assistant/actions) en de [beta.68-release](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.68) zodra gepubliceerd. Deze links claimen geen reeds voltooide beta.68-publicatie.

## Pakketintegriteit

`check_release_packages.py` moet beide installatie-ZIPs byte voor byte met de exacte geteste Git-bron vergelijken, inclusief versies, ledenlijst en documentmirrors. Na publicatie worden alle vier gedownloade assets op bronherkomst, grootte en SHA-256 gecontroleerd. Lokale softwarevalidatie bewijst geen pakketupload of geslaagde terugdownload; deze gates volgen de daadwerkelijke bouw/publicatie.

## Behouden grenzen en lokale acceptatie

Panasonic blijft exclusief eigenaar van zijn normale warmtepompregeling. Alleen de bestaande expliciet toegewezen SG-uitgang is een warmtepompactuator van SolarPilot. Taakafleiding, compacte labels, beweging en exportgegevens veranderen geen SG-policy, bronvalidatie, lease, koel-/native vrijgave of bestaande lokale bevestigingen. Afgeleid bedrijf is geen apart compressor-/warmteproductie- of ontvangen-SG-bewijs. Een ongewijzigde geldige beta.67-configuratie vraagt geen nieuwe ingebruikname wegens de update.

De fysieke gebruikersinstallatie en een echte optionele ontvangen-SG-bron zijn niet geaccepteerd door softwarefixtures. Zonder passende actuele SG-bron blijft ontvangen technisch onbekend en verschijnt geen permanente onbekende ontvangstindicator op de kaart. De oorspronkelijke native OFF/IDLE, onzekerheden en voedingsprofielaannamen blijven in Details/export. Historische stilstand heeft geen bewezen oorzaak en rechtvaardigt geen contactpulsen, reboottrucs of directe Panasonic-writes.

Installatie, update/herstart/herladen en rollback naar beta.67 staan in `BETA68_INSTELLEN.md`. Bestaande koppelingen en standaard 200 W werken zonder nieuwe verplichte invoer. Meetkwaliteit, éénklikexport van beschikbare zeven dagen, JSON.GZ-analyse en optioneel lokaal read-only antwoordrapport blijven behouden. Rapportupload past nooit automatisch instellingen, code of apparatuur toe; fysieke SG-/timerproeven houden hun afzonderlijke toestemming. Volledige actuele werking: `ACTUELE_WERKING.md` en **SolarPilot → Uitleg**. Privé-entiteiten, netwerkgegevens, tokens, ruwe thuismetingen en back-ups horen niet in publieke bron of pakketten.
