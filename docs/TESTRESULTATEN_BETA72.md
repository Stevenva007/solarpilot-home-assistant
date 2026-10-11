# Testresultaten SolarPilot 1.0.0-beta.72

Dit verslag onderscheidt de gepubliceerde beta.71-bouwbasis van de nieuwe beta.72-uitvoeringen. Oude resultaten zijn geen nieuwe testuitslag.

## Bewezen bouwbasis beta.71

Main en annotated tag staan op commit `03ff51bfbe710eb9d20e40834b703fc68febf85e`, tree `f57dba4233970e9d01320ee980d80eb66cba1158`. De lokale suite slaagde met **4049 cases in 66,04 s**. PR #11 op head `8b2e7520ceba5ef27ac9c2e7125e35c1564fed7d` doorliep Actions-run `38144731057`: alle vijf gates geslaagd, 4049 tests in 74,16 s. Main-run `38144889493` doorliep alle vijf gates plus publicatie, 4049 tests in 53,81 s. De annotated tag en vier werkelijk teruggedownloade release-assets zijn met de exacte bron gecontroleerd. Oude tags/assets blijven ongewijzigd.

## Actuele beta.72-status

| Controle | Beta.72-uitvoeringsbewijs |
| --- | --- |
| Volledige lokale suite | **4153 tests geslaagd in 69,10 s** met `PYTHONDONTWRITEBYTECODE=1 python -B -m pytest -q -p no:cacheprovider` op de definitieve productiebronboom. |
| Nieuwe gerichte regressies | **104 nieuwe gevallen** ten opzichte van de 4049-cases bouwbasis, inbegrepen in de volledige suite: 21 minimumregeling, 28 onafhankelijke grens-/lease-races, 29 configuratie/upgrade, 24 weergave en 2 catalogusgevallen; geen tweede optelling. |
| Actuele guide/help, mirrors, handoff en syntax | Geslaagd: canonical guide/help hash `6ccd1493c5efda80`, 343 helpentries en gelijke mirrors; handoff/structuur, 104 Python-ASTs, beide frontend-JS-bestanden en diffcheck. |
| Privacy-, repository- en SG-grenscontrole | Geslaagd: openbare repository-preflight, repositorystructuur en SG-only opdrachtgrens. Alleen fictieve nieuwe regressies; privé-export en brongebonden advies blijven buiten de repository. |
| Vijf CI-gates op exact dezelfde commit | Brongebonden uitvoering in [Actions](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml). Controleer de exacte commit van de PR/tag; de workflow blokkeert publicatie tot alle vijf gates slagen. |
| Nieuwe tag, publicatie en vier teruggedownloade assets | Brongebonden bewijs in de Publish-job bij de exacte tagged commit: vier assets worden vóór upload en na geïsoleerde download met de Git-bron vergeleken. |

Geen eerdere beta.71-uitslag of tussentijdse beta.72-run wordt als definitief beta.72-bewijs gebruikt. Deze immutable bronbijlage voorspelt geen toekomstige run-ID of uitslag.

## Regressiescope

- Minimumduur vanaf bevestigde contact-AAN; echte verstreken tijd, geen reset door vernieuwing of nieuw minimum/replayrecht bij reload. Ontbrekende optie krijgt 1200 s, expliciete waarden inclusief nul blijven behouden.
- Gewone importvertraging loopt tijdens het minimum door. Vroege zachte vrijgave wordt uitgesteld, en na het minimum kan al bevestigd tekort meteen worden beoordeeld. Geen extra verplichte stopvertraging en geen verplichte stop zonder tekort.
- Harde bron-/elektrische-/batterij-/koel-/Wallbox-/prioriteitsgrenzen, handmatige overname, Pauze/uitschakelen, geverifieerde native voltooiing, bevestigd geen extra opname, lease-/transportfout en maximaalduur blijven eerder beëindigen.
- Veilige vernieuwing van korte lokale leases tijdens uitsluitend de minimumwacht, zonder relaiscyclus of lokale twintigminutentimer. Gewone tekortcontrole na het minimum behoudt de bestaande vernieuwingstop.
- Absolute hardmaximumgrens vóór de eerste AAN én leasevernieuwing, opnieuw getoetst na await op eigen opslag en netwerkvoorcontrole. Een kort maximum reserveert bevestigingsruimte in de lokale lease; geen toestemming die door verstreken preflight-/bevestigingstijd voorbij het maximum wordt verlengd.
- Een behouden korter hardmaximum begrenst het effectieve minimum; geen stille maximumverhoging, invalidconfig of algemene gegevens-/rechtenreset. Configuratie, native formulier en kaart tonen de SG-aanvraagduur apart van compressorbedrijf.
- Beta.71-wachtfasen, exportvenster/grensdagtotalen, beta.70-geschiedenis/Store/API/ACL en alle overige verbruikers, modellen, tickets en fysieke SG-only grenzen blijven behouden. Fixtures blijven fictief.

## CI en publicatie

De vijf bestaande CI-gates zijn repositorytests, HACS, Hassfest, echte Home Assistant Core 2026.10 setup/reload/unload en browser-UI op 320/390/768/1280 px. De bestaande warmtepomp-, warmtepompgeschiedenis- en verbruikerhistorieproeven blijven in de browsergate. Alleen dezelfde exacte commit met vijf geslaagde gates mag worden gepubliceerd.

De bestaande workflow maakt een nieuwe immutable annotated tag, bouwt beide ZIPs en vergelijkt alle vier assets vóór upload en na geïsoleerde download bytegelijk met de commit. Naam, grootte, SHA-256 en broninhoud worden afzonderlijk gecontroleerd. De daadwerkelijke CI-uitslag en publicatiestappen staan bij de exacte broncommit in Actions.

## Beperkingen

Een minimale SG-aanvraagduur bewijst geen compressorlooptijd, warmteproductie, COP of causale SG-besparing. Software-/Core-/browser-/pakketbewijs is geen fysieke Shelly-/Panasonic-/meter- of condensacceptatie. Harde vrijgave, lokaal verlopen toestemming en een korter maximum kunnen de aanvraag vóór twintig minuten beëindigen.

De bestaande `via_device`-deprecatiewaarschuwing richting Home Assistant 2027.8 blijft afzonderlijk open; beta.72 verandert dat pad niet. Installatie, gegevensbehoud en rollback naar beta.71 staan in [BETA72_INSTELLEN.md](BETA72_INSTELLEN.md).
