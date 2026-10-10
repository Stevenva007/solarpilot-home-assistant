# SolarPilot 1.0.0-beta.64 — testresultaten

Datum: **2026-10-10**. De definitieve lokale software- en echte Core-gates zijn geslaagd. Publicatie/CI en fysieke ingebruikname zijn afzonderlijke bewijsstappen.

## Bronbasis en wijziging

Gecontroleerde bouwbasis: gepubliceerde [beta.63](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.63), commit `977f2fe1eb19c4944be7ee7125b911a473ef7c29`. Main, release en relevante open PR's zijn bij aanvang opnieuw gecontroleerd; beta.64 was vrij. De bestaande tag/assets blijven ongewijzigd.

Beta.64 voegt lokaal bevestigd algemeen/tapwater-only toepassingsbereik, profielgebonden herbeoordeling, afzonderlijke koelvrijgave, splitmeting en gescheiden read-only bedrijfs-/SG-bewijs toe. Elke beëindigde of onderbroken algemene sessie vraagt betekenisvol nieuw native-/zonnepisodebewijs; tijd, reload, timerafloop, bronverlies of dezelfde samples geeft geen eindeloze herstartlus. De tapwater-only tankafkoelregel blijft behouden. Bronwissel vormt eerst een referentie, geen nieuwe vraag. De eenmalige laagverbruikdiagnose geeft geen schakel- of foutrecht.

## Definitieve lokale softwaregate

| Controle op de afgeronde productiebron | Werkelijk resultaat |
| --- | --- |
| Volledige pytest, Python 3.12.14 | **2932 geslaagd in 33,97 s**. |
| Volledige pytest, Python 3.14.2 | **2932 geslaagd in 35,06 s**. |
| Onafhankelijke gerichte review-/regressieset | **430 geslaagd**; onderdeel van de volledige suite, geen extra tests bij de volledige teller optellen. |
| Officiële Hassfest-logica van HA 2026.10.0 | **23 validators, 1 integratie, 0 ongeldige integraties; geslaagd in 1,079 s**. |

Conventionele volledige opdracht: `PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider`. De aanvullende Python 3.14.2-run gebruikt dezelfde suite, met `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` en expliciet `-p pytest_asyncio.plugin`. Dit voorkomt dat een geïnstalleerde echte-HA-testplugin de voor de unit/protocoltests bedoelde doubles vervangt; het wijzigt de productiecode niet. Echte Core-proeven staan apart hieronder en tellen niet mee als pytest-cases.

Gerichte regressies dekken algemene sessieherbeoordeling met stabiele/ontbrekende tank, behoud tapwater-only, nieuwe echte zonne-/native episodes, constante zon/reload/brononderbreking, nul pulsen of Panasonic-writes, compressor/native context versus WATER-/klepstand, ontbrekend/stale SG-bewijs, complete/incomplete splitmeting, W/kW, gemeten nul, overlap en behoud single-meterconfig. Ook handmatig AAN zonder bewezen lease, lokale afloop/vernieuwing zonder relaiscyclus, late terugmelding, eigenaarschap, afzonderlijke condensbeveiliging en idempotente immutable/geneste-opties-/holdmigratie blijven afgedekt. De bestaande andere-toestel-, prioriteit-, fase-, batterij-, Recorder-, retentie-, popup- en exportregressies zijn behouden.

Hassfest is daadwerkelijk uitgevoerd met de officiële validatielogica uit Home Assistant 2026.10.0. Alleen de multiprocessing-startmethode is voor deze geïsoleerde omgeving van forkserver naar fork gezet, omdat de standaardroute geen UNIX-socket mocht openen. De validators en integratiebron zijn niet vervangen of vereenvoudigd. Dit is geen claim over een nog te draaien GitHub-Hassfestjob.

## Echte Home Assistant Core-entrygate

Omgeving: **Home Assistant Core 2026.10.0 en Python 3.14.2**, fictieve entiteiten/configuratie en tijdelijke Store; geen live huisconfiguratie of fysieke apparaten.

| Werkelijke proef | Resultaat |
| --- | --- |
| Ongewijzigde beta.62-baseline | Verwachte `TypeError: cannot pickle 'mappingproxy' object` en `SETUP_ERROR` gereproduceerd in **1,877 s**; originele opties en Store exact ongewijzigd, 0 fysieke servicecalls. |
| Beta.64 legacy-/migratiefixture | Productie-entry setup, reload en unload geslaagd in **2,017 s**; echte onveranderbare opties, geneste configuratie en exact privéarchief behouden. |
| Beta.64 actuele general/splitfixture | Productie-entry setup, reload en unload geslaagd in **1,927 s**; actuele algemene SG-configuratie, splitmeters, geneste immutable opties, exact privéarchief en manual/completion/new-evidence-holds behouden. |
| Beide beta.64-fixtures | Zes echte platforms en **58 registry-entiteiten** met states; **0 fysieke servicecalls** en geen opgevangen exceptions. |
| Actuele bron-/bewijswissels | W/kW-som, bekende nul, ontbrekende deelmeter en echte totaalmeting gecontroleerd; compressorfrequentie nul/onbekend/actief en WATER zonder compressorbewijs; ontvangen SG actief/onbekend blijft los van SG-veroorzaakt effect. |

Opdrachten: `python tools/check_real_ha_startup.py` en dezelfde checker met `--current-sg-fixture`; de beta.62-baseline gebruikt `--source-root` op de ongewijzigde bron en `--expect-mappingproxy-failure`.

De checker vervangt uitsluitend HTTP bind/start en source-IP discovery voor offline uitvoering. SolarPilot-entry, constructor, migratie, Store, platforms en entiteiten zijn echte productiecode. De fixtures staan in Alleen bekijken; zij openen geen HTTP-listener en benaderen geen fysiek apparaat. De actuele fixture gebruikt reeds gemigreerde opties en bewaart haar echte blokkeringen door reload heen. Deze startupacceptatie bewijst geen lokaal geladen mobiele kaart, wifi-terugval of fysieke Panasonic-reactie.

## Interface en overige releasegates

De compacte kaart houdt aanvraag/eigenaar/reden, Shelly-feedback/lokale timer, compressor/native context, complete/incomplete vermogen en ontvangen SG-status gescheiden. Onbekende relaisfeedback kan geen fictief geopend contact tonen. De gegenereerde actuele guide/mirrors, 339 helpentries, versiegebonden installatie/testmirrors en offlinevoorbeeld horen bij dezelfde bron.

De aanvullende Node-/helpassetset heeft **67 geslaagde controles** en de gerichte UI-set **152 geslaagde cases**; deze zijn geen extra tests bovenop de volledige pytest-teller. Een werkelijke browserrender is **niet uitgevoerd**: de omgeving had geen bruikbare browserbinary, de browserdownload leverde geen bruikbaar archief en de aanvullende pakketinstallatie werd door automatische goedkeuringscontrole afgewezen. Er wordt geen geslaagde visuele browser-/screenshotcontrole geclaimd. Node-/HTML-/helpcontroles vervangen die stap niet.

Canonieke uitleg/hash/help/mirrors, overdracht en publieke privacy-preflight zijn op de finale bron opnieuw geslaagd; actuele guidehash `95d0991aef98b0fd`, 339 helpentries. Repositorystructuur, SG-bevoegdheidsgrens, Python-/JSON-syntax, beide JavaScriptbestanden via Node en `git diff --check` zijn eveneens geslaagd. De publieke repository bevat generieke voorbeelden en fictieve fixtures; de persoonlijke opdracht, bindings, netwerkgegevens, tokens, ruwe thuismetingen en exports worden niet opgenomen.

## Reeds behouden gedrag

Geen nieuwe implementatie was nodig voor de bestaande SG-only deny-grens, één actuatoreigenaar, native Shelly-route, 300 s-lokale toestemming/60 s-vernieuwing zonder relaiscyclus, sessiebegrenzing, expliciete hervatting en geen oude opdrachtreplay. Panasonic blijft exclusief eigenaar van thermostaten, zones, stooklijnen, compressor, pompen, kleppen, ontdooien, normaal warmwatercomfort, elektrische ondersteuning en sterilisatie. Lokaal gekozen SG-percentages/koelwaarde worden niet geschreven.

Wallbox blijft read-only; AEG behoudt één START per belading, APP-ticket, deadlines en AirDry-bescherming. Ontvochtiger-minimumtijden, batterijen, centrale gebruikersvolgorde, protected loads, fase-/netgrenzen, kosten, historie, leren, retentie, Recorder-begrenzing en stabiele pop-ups blijven behouden. De beta.63-fix voor onveranderbare/geneste HA-opties blijft aanwezig. Geen tweede heaterrelais, extra hardware, directe warmtepompwriter, gegevensreset of ongevraagde herprioritering.

## CI, publicatie en release-integriteit

Lokale gates bewijzen geen toekomstige workflow- of uploadsuccessen. Publicatie is in de bestaande workflow afhankelijk van geslaagde repository-, HACS-, Hassfest- en echte Core-jobs, inclusief de nieuwe actuele general/splitfixture. HACS wordt door de echte CI gecontroleerd; lokaal was geen Docker beschikbaar. De nieuwe annotated tag/prerelease moet naar exact de geteste commit wijzen, zonder oude tags/assets te wijzigen.

`tools/check_release_packages.py` vergelijkt beide ZIP-inhouden byte voor byte met de exacte Git-bron, versies, ledenlijst en documentmirrors. De workflow controleert vóór upload en daarna opnieuw alle vier werkelijk gedownloade assets met bron-SHA, grootte en SHA-256. Bestaande, ontbrekende of afwijkende assets worden niet stil overschreven.

Publieke bewijsplaatsen: [Actions](https://github.com/Stevenva007/solarpilot-home-assistant/actions) en de [beta.64-release](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.64) zodra gepubliceerd. Exacte workflow-/tag-/downloadbewijzen worden bij oplevering vermeld; deze brongebonden tekst claimt geen toekomstige CI of upload en wijzigt achteraf geen immutable release.

## Bewijsgrenzen en lokale acceptatie

Geen live HA-installatie, Shelly, Panasonic, elektrische dekking of fysieke condensbeveiliging is uitgelezen/beproefd. De oorzaak van de historische stilstand en latere compressoractiviteit blijft open: precieze uit-/aanhandeling, tussenliggende native instellingen en passende logs ontbreken. Er is geen bewezen contactflankprobleem en geen aanleiding voor automatische OFF/ON-pulsen.

Installatie, lokale profiel-/meter-/koelbeveiligingscontrole, korte acceptatie zonder geopende apparatuur en rollback staan in `BETA64_INSTELLEN.md`. Fysieke timer-/SG-proef blijft een afzonderlijke lokale stap uitsluitend na expliciete toestemming. De actuele werking is de uit `current_guide.py` gegenereerde `ACTUELE_WERKING.md` en **SolarPilot → Uitleg**.
