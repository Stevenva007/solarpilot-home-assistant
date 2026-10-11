# Testresultaten SolarPilot 1.0.0-beta.73

Dit verslag onderscheidt de gepubliceerde beta.72-bouwbasis van nieuwe beta.73-uitvoeringen. Oude resultaten zijn geen nieuwe testuitslag.

## Bewezen bouwbasis beta.72

Main en annotated tag staan op commit `060249c6aa44656d8ecac119df5316e0bcb6437a`, tree `e8b72bffff8e7513109a5469e83284dd66d35c87`. De lokale suite slaagde met **4153 cases in 69,10 s**. PR-run `38146963486` en main-run `38147198891` zijn gecontroleerd; main doorliep alle vijf gates plus Publish met **4153 tests in 74,67 s**. Alle vier werkelijk teruggedownloade release-assets zijn onafhankelijk met de exacte bron gecontroleerd. Oude tags/assets blijven ongewijzigd.

## Actuele beta.73-status

| Controle | Beta.73-uitvoeringsbewijs |
| --- | --- |
| Volledige lokale suite | **4320 geslaagd in 78,75 s**, zonder failures of skips, met `PYTHONDONTWRITEBYTECODE=1 python -B -m pytest -q -p no:cacheprovider`. |
| Nieuwe gerichte regressies | **167 nieuwe gevallen** boven de 4153-case bouwbasis: 39 configuratie, 36 controller, 57 onafhankelijke grens/raceproeven, 33 UI en 2 release/digest. Inbegrepen in de volledige suite; geen tweede optelling. |
| Actuele guide/help, mirrors, handoff en syntax | Geslaagd: guidehash `cf61a2522a2cd258`, 344 helpentries, drie bytegelijke documentmirrors, actuele handoff, AST van 104 bron/toolbestanden en Node-syntax van kaart/help. |
| Privacy-, repository- en SG-grenscontrole | Geslaagd: public-repositorypreflight, repositorystructuur, SG-commandogrens en diffcontrole. Geen private export of gegenereerde cache in de releasebron. |
| Vijf CI-gates op exact dezelfde commit | Brongebonden uitvoering in [Actions](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml). Controleer de exacte commit van de PR/tag; de workflow blokkeert publicatie tot alle vijf gates slagen. |
| Nieuwe tag, publicatie en vier teruggedownloade assets | Brongebonden bewijs in de Publish-job bij de exacte tagged commit: vier assets worden vóór upload en na geïsoleerde download met de Git-bron vergeleken. |

Deze immutable bronbijlage voorspelt geen toekomstige run-ID of uitslag. Eerdere beta.72-resultaten of tussentijdse beta.73-runs worden niet als definitieve beta.73-validatie gebruikt.

## Regressiescope

- Strikt boven de importbuffer, standaard 600 W, gedurende vijf continue minuten. Exact de grens of lager wist de lopende tekorttimer; een volgende overschrijding start opnieuw.
- Softtimer gebruikt actueel gemeten P1-netafname. Resterende wolkentijd blijft begrensd door oorspronkelijke P1-bronactualiteit, bevestigde lease en hardmaximum; schermtijd of herlezen maakt de bron niet vers.
- Tekorttijd overlapt minimum20: vanaf minuut 18 pas in minuut 23 gewone vrijgave; eerder voltooide vijf minuten kunnen bij minuut 20 al gelden. Minimumafloop zonder tekort is geen verplichte stop.
- Korte veilige leasevernieuwing tijdens geldige wolkenwachttijd, ook na het minimum. Bij bevestigd tekort én minimumafloop geen verlenging die de gewone vrijgave overslaat; geen fysieke relaiscyclus.
- Absolute hardmaximumgrens vóór eerste AAN en vernieuwing, opnieuw na opslag-/netwerkvoorcontrole. ACK-reserve, korte lokale afloop, hardmaxresttijd en ontbreken van nieuw AAN-/minimumrecht bij reload blijven behouden.
- Nieuwe `import_threshold_w` los van behouden `hysteresis_w` voor zonne-resetbewijs. Runtime-only omzetting van oude standaardcombinatie 300 W/60 s naar 600 W/300 s; oude afwijkingen en expliciete nieuwe waarden behouden, zonder optieswrite of gegevensreset.
- Bronwissel, teruglopende rapporttijd of verlopen oorspronkelijk P1-bewijs kan bij aanhoudende import geen nieuwe buffer kopen. Actuele watts, rapporttijd en bron blijven één waarneming na asynchrone wachttijd; actuele overschrijding van vaste net-/kwartiergrenzen geeft direct vrij, ook binnen het minimum.
- Alle harde bron-/elektrische-/batterij-/koel-/Wallbox-/prioriteits- en foutvrijgaven, handmatige overname, Pauze/disable, geverifieerde native voltooiing/bevestigd geen extra opname en korter behouden maximum kunnen eerder beëindigen.
- Read-only cloud-/minimumweergave, echte bron-/leaseactualiteit en onderscheid tussen SG-aanvraag, compressorbedrijf en levensduurclaim. Beta.71-wachtfasen/export, beta.70-geschiedenis/Store/API/ACL en overige apparaten, modellen/tickets blijven behouden. Fixtures blijven fictief.

## CI en publicatie

De vijf bestaande CI-gates zijn repositorytests, HACS, Hassfest, echte Home Assistant Core 2026.10 setup/reload/unload en browser-UI op 320/390/768/1280 px. De warmtepomp-, warmtepompgeschiedenis- en verbruikerhistorieproeven blijven in de browsergate. Alleen dezelfde exacte commit met vijf geslaagde gates mag worden gepubliceerd.

De workflow maakt een nieuwe immutable annotated tag, bouwt beide ZIPs en vergelijkt alle vier assets vóór upload en na geïsoleerde download bytegelijk met de commit. Naam, grootte, SHA-256 en broninhoud worden afzonderlijk gecontroleerd. De daadwerkelijke uitslag en publicatiestappen staan bij de exacte broncommit in Actions.

## Beperkingen

Een rustigere SG-aanvraag bewijst geen compressorlooptijd, gegarandeerde levensduur, warmteproductie, COP of causale besparing. Harde vrijgave, lokaal verlopen toestemming en een korter maximum kunnen eerder beëindigen. Software-/Core-/browser-/pakketbewijs is geen fysieke Shelly-/Panasonic-/meter- of condensacceptatie.

De bestaande `via_device`-deprecatiewaarschuwing richting Home Assistant 2027.8 blijft afzonderlijk open. Installatie, behoud en rollback naar beta.72: [BETA73_INSTELLEN.md](BETA73_INSTELLEN.md).
