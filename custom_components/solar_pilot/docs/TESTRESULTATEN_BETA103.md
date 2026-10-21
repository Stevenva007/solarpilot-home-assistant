# SolarPilot beta.103 — test- en publicatieverslag

Versie: **1.0.0-beta.103** · 21 oktober 2026

Bouwbasis: gepubliceerde beta.102 `637032107a71798b3a181076e531d5eeb76c238f`, tree `7d27bd7d346031aebecb3cd8d567f239da8571c0`. Regressies en fixtures gebruiken generieke gegevens. Privé-exportbestanden, bronidentiteiten en installatiegegevens zijn niet in deze repository opgenomen.

## Correctie en bewijsgrens

De frontend gebruikte voor samenhangende afgeleide warmtepomptaken uitsluitend het oudere special_status-contract. De backend ondersteunde de bestaande split operation_status-semantiek al. De kaart accepteert nu beide exacte contractcombinaties, met behoud van de oorspronkelijke provider-, bindings-, tijd-, cache- en metercontroles.

Onvolledige, tegenstrijdige, verlopen of niet-herkende gegevens krijgen geen extra toestemming. Een taak blijft afgeleid; de kaart maakt daarvan geen bevestigde compressorwerking of leerbewijs. Het bijschrift in Details volgt het werkelijke oorspronkelijke contract, zonder oude special-status- of globale-UIT-claim voor de split-route.

Backendclassificatie, leren, SG/controllers, modellen, opslag, historische gegevens en instellingen veranderen niet. Rollback naar beta.102 gebruikt dezelfde opslag en instellingen en brengt de oude frontendfout terug; er is geen migratie.

## Vastgelegde validatie

Onderstaande gerichte sets overlappen en worden niet opgeteld.

| Controle | Resultaat op dit moment |
|---|---|
| Gerichte bestaande en nieuwe regressies | **507 geslaagd**, inclusief **65 nieuwe status-UI-gevallen** en **41 onafhankelijke adversarial gevallen**. |
| Behouden bewijsgrenzen | Gerichte regressies toetsen beide contracten, afgeleide labels, ongeldige combinaties, ontbrekende of verlopen gegevens, binding, cache- en metergrenzen en semantisch passend bronbijschrift. |
| Implementatiecatalogus | **41 geslaagd**, waaronder **5 nieuwe beta.103-gevallen**; exacte inhoud en werkelijk geladen release blijven vereist. |
| Volledige definitieve testsuite | **8554 geslaagd** op Python **3.13.16** in **181,92 s**, met `PYTHONDONTWRITEBYTECODE=1 python -B -m pytest -q -p no:cacheprovider`. |
| Echte Home Assistant Core | **Beide fixtures geslaagd** op Core 2026.10.0/Python 3.14.2: setup, reload, unload, elk **67 entiteiten** en **0 fysieke serviceaanroepen**. |
| Echte Chromium 153 | Nieuwe status103-gate geslaagd: beide contracten; verwarmen, koelen en boiler in drie schermen op **320/390 px**; bron-details, oorspronkelijke historie, 40 statusupdates met open dialoog, toetsenbord en nul bedieningswrites. Screenshots visueel gecontroleerd. |
| Online-upstreamgate en definitieve document-/pakketcontrole | Online Python 3.13-gate **geslaagd**, document-/privacy-/SG-grenscontroles slagen; pakket- en CI-bewijs blijft vereist vóór publicatie. |

Canonieke gids: **1.0.0-beta.103**, hash **`24b193266d1804d6`**. Broncode, installatie, testverslag en bytegelijke mirrors horen bij dezelfde release.

Op **21 oktober 2026 om 08:07:03 UTC** zijn alle **acht primaire GitHub-records** opnieuw gecontroleerd. Aquarea **1.8.0**, commit `8722cf22e5a5752406aea1ba79b2cf48d4deedf3`, en SDK **1.4.0**, commit `893065a81c014cb9aa1d3350446d61c01bccf3b9`, zijn ongewijzigd. Dit bewijst niet welke software bij een gebruiker geladen is. Het bestaande geladen-codecontract blijft vereist. Zie [UPSTREAM_BRONNEN.md](UPSTREAM_BRONNEN.md) en `upstream_review.json`.

## Publicatievoorwaarden en status

Dit verslag beschrijft beschikbare controles vóór definitieve CI en publicatie. De [Validate-workflow](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml) moet alle vijf gates op de definitieve PR-bron laten slagen: repository/privacy/documentatie en volledige testsuite, HACS, Hassfest, echte Home Assistant en Chromium. Dezelfde main-bron moet de gates opnieuw doorlopen vóór publicatie.

PR-/main-CI, merge, tag en uploads zijn hier niet als voltooid geclaimd. De immutable annotated tag **`v1.0.0-beta.103`** moet naar de geteste main-commit wijzen. De [prerelease](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.103) krijgt vier bestanden:

- `SolarPilot-v1.0.0-beta.103-GitHub-HACS.zip`
- `SolarPilot-v1.0.0-beta.103-local.zip`
- `BETA103_INSTELLEN.md`
- `TESTRESULTATEN_BETA103.md`

Voor upload én na opnieuw downloaden worden de vier bestanden gecontroleerd tegen dezelfde bron op bytegelijkheid, grootte en SHA-256. Bestaande tags of assets worden niet overschreven. Beide releasedocumenten hebben bytegelijke componentmirrors.

Softwaretests bewijzen geen uitgevoerde gebruikersinstallatie, fysieke compressorwerking, warmtelevering of live hardwareacceptatie. Zie [installatie en rollback](BETA103_INSTELLEN.md).
