# Testresultaten SolarPilot 1.0.0-beta.75

Dit verslag onderscheidt de gepubliceerde beta.74-bouwbasis van nieuwe beta.75-uitvoeringen. De wijziging voegt lokaal read-only onderzoek en concrete voorstellen toe. Zij verandert geen actuator, hardgrens, meetwaarde, sensorkoppeling, Panasonic-instelling of SG-regelstrategie.

## Bewezen bouwbasis beta.74

Main en annotated tag staan op commit `0f7e35e1f894a8706ccb5aa744a20db61a5b61ed`, tree `159acc79010fa19eff579e628f5f1b8218819bf4`. De lokale suite slaagde met **4421 cases in 82,01 s**. PR-run `38163869747` doorliep alle vijf gates met 4421 tests in 50,74 s; main-run `38164027681` slaagde met alle vijf gates plus Publish, 4421 tests in 49,66 s. Alle vier werkelijk teruggedownloade release-assets zijn onafhankelijk met de exacte bron gecontroleerd. Oude tags/assets blijven ongewijzigd. Dit is basisbewijs, geen beta.75-validatie.

## Actuele beta.75-status

| Controle | Beta.75-uitvoeringsbewijs |
| --- | --- |
| Volledige lokale suite | **4565 tests geslaagd in 84,37 s** op de functionele bron vóór de browserfixture-scopecorrectie, met bytecode en pytestcache uitgeschakeld. Dit is geen geslaagde uitvoering van de gecorrigeerde echte browsergate. |
| Nieuwe gerichte regressies | **144 nieuwe cases** ten opzichte van 4421 in beta.74. Bronactualiteit/cursors, restore/rebind, begrensde opslag, status/voorstellen, exportprivacy, SG-sessies en read-only UI/catalogus worden afzonderlijk bewaakt. |
| Actuele guide/help, mirrors, handoff en syntax | Guidehash **4c69536f8d0071d7**, 344 helpvelden, drie bytegelijke documentmirrors; actuele uitleg, handoff, 106 productie-/tool-ASTs, kaart/hulpmodule-Node-syntax en diffcontrole geslaagd. Na de browserfixture-scopecorrectie zijn **186 inline browser-JS-fixtures** syntactisch gecontroleerd; dat vervangt geen echte browseruitvoering. |
| Privacy-, repository- en SG-grenscontrole | Privacy-, repositorystructuur- en SG-bevoegdheidsgrenscontroles geslaagd. Names-off-export controleert ook opgeslagen rapportcursors na restore: een private verbruikeridentiteit of naam wordt geen ongefilterde JSON-objectsleutel. Private bronpakketten zijn geen testfixtures of release-assets. |
| Eerste echte Chromium-PR-uitvoering | Run **38172631070** op `b18b58dad888278c9cc6179721909a6368c30cca` mislukte op een dubbele strikte Playwright-locator. Het nieuwe onderzoekspaneel was tegelijk aanwezig in het DOM van Export en Meetkwaliteit; het foutlog bewijst niet dat de popup nog zichtbaar was. De test selecteerde `.automatic-investigation` zonder de bedoelde weergave te begrenzen. |
| Tussenbewijs uit die eerste PR-run | Repositorysuite **4565 geslaagd in 86,19 s**; echte Home Assistant Core **2026.10.0**-opstart met **58 entiteiten, 6 platforms en nul fysieke servicecalls** geslaagd. Dit vervangt de mislukte browsergate niet en is geen definitieve volledige CI-validatie van de herziene bron. |
| Gerichte lokale controle na locatorcorrectie | **52 UI-tests geslaagd in 4,26 s**, 186 inline-JS-fixtures compileerbaar, Python-AST en diffcontrole geslaagd. Productcode bleef gelijk; de echte browsergate moet op de herziene bron opnieuw slagen. |
| Vijf CI-gates op exact dezelfde commit | Brongebonden uitvoering in [Actions](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml). Echte Home Assistant-opstart en echte browserweergave blijven afzonderlijk vereist; publicatie blijft geblokkeerd tot alle vijf gates slagen op dezelfde exacte bron. |
| Nieuwe tag, publicatie en vier teruggedownloade assets | Brongebonden bewijs in de Publish-job bij de exacte tagged commit: assets worden vóór upload en na geïsoleerde download met de Git-bron vergeleken. |

Deze immutable bronbijlage voorspelt geen toekomstige run-ID of uitslag. Beta.74-basisresultaten of tussentijdse beta.75-runs zijn geen definitieve beta.75-validatie.

## Regressiescope

- Vier lokale onderzoeksonderwerpen met afzonderlijke status, bewijs, expliciete hypotheses, gerichte voorstellen en een volgende actie. Geen generieke automatische foutreparatie of fysieke defectclaim.
- Begrensde voortgang, maximaal één beoordeling van de vier brononderwerpen per minuut en onderscheid tussen oorspronkelijke verse bronrapporten en herhaalde uitlezingen. Bronverloop en rebind verliezen ook tussentijds actuele geldigheid. Herstart of oude/restored/ongeldige rapporten leveren geen nieuwe bevestiging. Opgeslagen cursors tellen hetzelfde rapport niet opnieuw; restore bewaart geen actuele status. Names-off-export schermt ook cursoridentiteiten na restore af.
- SG-beoordeling met maximaal twaalf afgeronde records, behouden instellingen en expliciete bewijsgrenzen. Eén coherent tijdstip verbindt aanvraag/contact/P1/PV; onbekende start, gat boven dertig seconden, bronverloop, herstart en gewijzigde policy leveren geen complete vergelijkbare sessie. Oude sessies valideren geen nieuwe timers; elektrisch verbruik of contactstand bewijst geen causale extra SG-opname.
- Read-only status in Meetkwaliteit en export. Niet-logische geïmporteerde adviezen krijgen een categorieaanduiding zonder toegepaste instelling of opgelost onderzoek te claimen.
- Behoud van 600 W/300 s continue tekorttimer, reset op of onder de grens, overlap met minimum 20 minuten, korte leases, bron-/contact-/lease-/hardmaxbewijs en alle harde/native/manual/prioriteits-/foutvrijgaven.
- Behoud van configuratie, modellen, tickets, Panasonic-native waarden, overige apparaten, aparte histories/Store/READ-API/ACL en kalenderdag-export. Nieuwe fixtures zijn fictief, zonder gekopieerde private export of huishoudelijke bronidentiteit.

## CI en publicatie

De vijf bestaande gates zijn repositorytests, HACS, Hassfest, echte Home Assistant Core 2026.10 setup/reload/unload en browser-UI op 320/390/768/1280 px. Warmtepomp-, warmtepompgeschiedenis- en verbruikerhistorieproeven blijven in de browsergate. Alleen dezelfde exacte commit met vijf geslaagde gates mag worden gepubliceerd.

De eerste echte Chromium-proef in [PR-run 38172631070](https://github.com/Stevenva007/solarpilot-home-assistant/actions/runs/38172631070) vond een testscopeprobleem: de strikte locator trof twee geldige onderzoekspanelen aan. De browserfixtures begrenzen de locator nu tot Export respectievelijk de Meetkwaliteit-popup. Deze gerichte testcorrectie verandert geen productcode, regeling of bevoegdheid. De lokale 4565/84,37 s-proef betreft de functionele bron vóór die locatorcorrectie. De 106 ASTs, 344 helpvelden en guidehash blijven gelijk. De herziene bron heeft 186 syntactisch gecontroleerde inline fixtures en 52 geslaagde gerichte UI-tests; die bewijzen geen geslaagde echte Chromium-uitvoering.

Een nieuwe echte browser- en volledige CI-uitvoering op de definitieve gecorrigeerde bron moet nog slagen. Brongebonden uitvoering staat in [Actions](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml). Deze immutable bronbijlage voorspelt geen toekomstige run-ID of uitslag. Oude of tussentijdse resultaten zijn geen definitieve beta.75-validatie.

De workflow maakt een nieuwe immutable annotated tag, bouwt beide ZIPs en vergelijkt alle vier assets vóór upload en na geïsoleerde download bytegelijk met de commit. Naam, grootte, SHA-256 en broninhoud worden afzonderlijk gecontroleerd. Daadwerkelijke uitslag en publicatiestappen staan bij de exacte broncommit in Actions.

## Beperkingen

Lokale broncontrole kan gegevensproblemen zichtbaar maken en gericht vervolg voorstellen. Zij bewijst geen fysieke meter-, heater- of klepstoring, warmteproductie, COP, compressorlooptijd, levensduur of causale SG-besparing. Niet aangesloten meetapparatuur en verkeerde bindings worden niet vanzelf hersteld. Een afgekeurde negatieve waarde wordt niet softwarematig omgekeerd of als nul gebruikt. Software-/Core-/browser-/pakketbewijs is geen fysieke Shelly-/Panasonic-/meter- of condensacceptatie.

De bestaande `via_device`-deprecatiewaarschuwing richting Home Assistant 2027.8 blijft afzonderlijk open. Installatie, behoud en rollback naar beta.74: [BETA75_INSTELLEN.md](BETA75_INSTELLEN.md).
