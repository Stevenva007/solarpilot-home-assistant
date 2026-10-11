# Testresultaten SolarPilot 1.0.0-beta.74

Dit verslag onderscheidt de gepubliceerde beta.73-bouwbasis van nieuwe beta.74-uitvoeringen. Oude resultaten zijn geen nieuwe testuitslag. De wijzigingen zijn begrensde diagnosecorrecties; geen nieuwe regelstrategie, hardgrens of meetcorrectie.

## Bewezen bouwbasis beta.73

Main en annotated tag staan op commit `37729bce6dc679e8b18bea6a5f44c9d2348f5aab`, tree `eda14b034ae75cbd259db2a2e90606cf25628fb0`. De lokale suite slaagde met **4320 cases in 78,75 s**. PR-run `38152405538` slaagde met 4320 tests in 76,05 s; main-run `38152632550` doorliep alle vijf gates plus Publish met 4320 tests in 80,13 s. Alle vier werkelijk teruggedownloade release-assets zijn onafhankelijk met de exacte bron gecontroleerd. Oude tags/assets blijven ongewijzigd.

## Actuele beta.74-status

| Controle | Beta.74-uitvoeringsbewijs |
| --- | --- |
| Volledige lokale suite | **4421 tests geslaagd in 82,01 s** op de definitieve lokale bron, met Python 3.12, bytecode en pytestcache uitgeschakeld. |
| Nieuwe gerichte regressies | **101 nieuwe cases** ten opzichte van 4320 in beta.73: 11 resetweergave, 12 onafhankelijke adversarial, 19 Wallboxvragen, 53 scope-/UI-cases en 6 catalogusgevallen. Bestaande verwachtingen zijn gericht op de juiste compressor-/circuitscope afgestemd. |
| Actuele guide/help, mirrors, handoff en syntax | Guidehash **155b4a654446aabd**, 344 helpvelden, drie bytegelijke documentmirrors; actuele uitleg, handoff, 104 productie-/tool-ASTs, kaart/hulpmodule-Node-syntax en diffcontrole geslaagd. |
| Privacy-, repository- en SG-grenscontrole | Alle privacy-, repositorystructuur- en SG-bevoegdheidsgrenscontroles geslaagd. Private bronpakketten zijn geen testfixtures of release-assets. |
| Vijf CI-gates op exact dezelfde commit | Brongebonden uitvoering in [Actions](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml). Controleer de exacte commit van PR/tag; publicatie blijft geblokkeerd tot alle vijf gates slagen. |
| Nieuwe tag, publicatie en vier teruggedownloade assets | Brongebonden bewijs in de Publish-job bij de exacte tagged commit: assets worden vóór upload en na geïsoleerde download met de Git-bron vergeleken. |

Deze immutable bronbijlage voorspelt geen toekomstige run-ID of uitslag. Beta.73-basisresultaten of tussentijdse beta.74-runs zijn geen definitieve beta.74-validatie.

## Regressiescope

- Read-only `_wait_progress`: vóór bevestigde lage zonne-/rustige native resetfase een passende resetcountdown; daarna geen terugkerende laagfasecountdown. Werkelijk lopende hoge/native bevestiging en startvertraging behouden hun betekenis. Bestaand rolling resetbewijs, twee echte rapporten, geldigheid, controllergates en commandogedrag blijven gelijk.
- Gekoppelde Wallboxsessiebron: oude, onbeschikbare en ongeldige bron benoemen als oorzaak bij de vraag. Geen stale-grensverlenging, gegokte Full Solar/gestopt-status, extra EV-krediet of Wallboxwrite; actuele bruikbare bronnen behouden bestaande gedrag.
- Scopebewuste bedrijfsweergave: native ruimte-/zone-UIT is geen globaal UIT. Onvolledig/ongeldig totaal met onbewezen globaal UIT blijft onbekend; geldige deelwaarde nul blijft nul zonder totaal te verzinnen. Verse passende taak, activiteit en bewezen globaal UIT houden afzonderlijke bewijskracht.
- Beperkte taak-/effectuitleg: een native taakovergang bewijst geen causaliteit, extra SG-energie, compressorbedrijf of fysiek defect. Oorspronkelijke broninformatie en onzekerheid blijven beschikbaar.
- Behoud van beta.73 600 W/300 s continue tekorttimer, reset op of onder de grens, overlap met minimum 20 minuten, veilige korte leases, oorspronkelijk P1-/contact-/lease-/hardmaxbewijs en alle harde/native/manual/prioriteits-/foutvrijgaven.
- Behoud van instellingen, bevestigingen, Panasonic-native waarden, SG-only actuatorgrens, overige apparaten, modellen/tickets, aparte histories/Store/READ-API/ACL, retentie en juiste kalenderdag-export. Nieuwe fixtures zijn fictief en bevatten geen gekopieerde huishoudelijke bronidentiteit of export.

## CI en publicatie

De vijf bestaande gates zijn repositorytests, HACS, Hassfest, echte Home Assistant Core 2026.10 setup/reload/unload en browser-UI op 320/390/768/1280 px. Warmtepomp-, warmtepompgeschiedenis- en verbruikerhistorieproeven blijven in de browsergate. Alleen dezelfde exacte commit met vijf geslaagde gates mag worden gepubliceerd.

De workflow maakt een nieuwe immutable annotated tag, bouwt beide ZIPs en vergelijkt alle vier assets vóór upload en na geïsoleerde download bytegelijk met de commit. Naam, grootte, SHA-256 en broninhoud worden afzonderlijk gecontroleerd. Daadwerkelijke uitslag en publicatiestappen staan bij de exacte broncommit in Actions.

## Beperkingen

Een duidelijke diagnosemelding bewijst geen fysieke heater-/klep-/meterstoring, warmtelevering, COP, compressorlooptijd of causale SG-besparing. Een afgekeurde negatieve meterwaarde wordt niet softwarematig gecorrigeerd. Harde guards en onzekere/lokaal verlopen toestemming behouden hun effect. Software-/Core-/browser-/pakketbewijs is geen fysieke Shelly-/Panasonic-/meter- of condensacceptatie.

De bestaande `via_device`-deprecatiewaarschuwing richting Home Assistant 2027.8 blijft afzonderlijk open. Installatie, behoud en rollback naar beta.73: [BETA74_INSTELLEN.md](BETA74_INSTELLEN.md).
