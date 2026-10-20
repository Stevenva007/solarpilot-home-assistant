# SolarPilot beta.102 — test- en publicatieverslag

Versie: **1.0.0-beta.102** · 20 oktober 2026

Bouwbasis: gepubliceerde beta.101 `08d8c1f7446c78cc38bbb83f635491f429d1cdf2`, tree `c2e12dd9aaee2237370027df87b90c3759b98df5`. De definitieve lokale tests hieronder gebruiken de bevroren productcode. Regressies, Core-fixtures en browserproeven gebruiken fictieve gegevens; huishoudelijke bronidentiteiten en privé-exportbestanden staan niet in deze repository.

## Afgebakende correcties

**PV:** `PlanQualityTracker.overview()` gebruikt dezelfde daglicht-MAE, minimum twaalf daglichtvergelijkingen en strikt meer dan 700 W als de bestaande PV-vraag. Onvoldoende, ontbrekend of legacy-daglichtbewijs wordt geen positieve beoordeling. Basislast- en uitvoeringswaarschuwingen, oorspronkelijke cijfers, kwaliteitsscore en plannerbeleid blijven behouden.

**Warmtepomp:** gedeclareerde operation_status-enablementsemantiek kan niet via onvolledig of ongeldig bewijs terugvallen op de oudere native-confirmedroute. De oorspronkelijke detached snapshot, gevalideerd contract- en meterbewijs en zuivere bestaande displayvalidatie bepalen de afleiding. Afgeleid bewijs blijft `model_eligible=False`; ontbrekend bewijs blijft onbekend. Opgeslagen labels, pomp UIT of nul watt geven geen zelfstandige leer- of normale-basislasttoestemming. Oudere onafhankelijke contracten en bestaande modellen blijven behouden.

**Water:** begrensde rolling vensters herkennen kleine opeenvolgende boilerdalingen samen vanaf 2 °C binnen dertig minuten. Hoogste eerdere geldige temperatuur, oudste referentie bij gelijke waarden en verbruikte referenties voorkomen overlappende intervallen/liters. Alleen expliciet nieuw debietgatbewijs kan een onafhankelijk geldig teller-/boilervenster ongemoeid laten. Generieke of ongeldige rollen en echte teller-/temperatuurgaten blijven barrières. Capturetijd en oorspronkelijke rapporttijd voorkomen heropening van een venster met later vastgelegde oude gegevens. Contextwijzigingen blijven zichtbaar zonder continue extra numerieke sampling.

De aanvullende waterdiagnose projecteert uit dezelfde momentopname de afzonderlijke bronactualiteit van stromingsbewaking en native lekindicatie. Zij leest of bedient geen bron en maakt geen nieuwe periodieke melding of algemene foutpauze. Frontendveroudering, conditionele bronhulp, waterexportmetadata en gesloten protocolrollen behouden privacy en bronrechten. Geen automatische MQTT-/force_update-aanpassing.

De generieke catalogus bevat vanaf deze versie uitsluitend exacte voorstellen `water.boiler_window_source_roles`, `planner.pv_daylight_summary_consistency` en `heatpump.learning_enablement_contract`. Alleen passende inhoud én daadwerkelijk geladen versie kunnen de implementatiestatus bevestigen.

## Uitgevoerde validatie

Gerichte sets **overlappen** en worden niet opgeteld.

| Controle | Vastgelegd resultaat |
|---|---|
| Gerichte PV-kwaliteit, bestaande plannerkwaliteit, LearningHub en restoregevallen | **106 geslaagd** op Python 3.12, inclusief **11 nieuwe synthetische regressies**: nachtverdunning, grenzen 11/12 en 700/700,1 W, legacy/onbekend, overige waarschuwingen, ongewijzigde cijfers en echte LearningHub-overeenkomst zonder toestelopdrachten. |
| Definitieve volledige testsuite | **8443 geslaagd** op **Python 3.13.16 in 193,86 seconden**, met `PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider`. Alle nieuwe backend- en onafhankelijke grensgevallen zijn hierin opgenomen. |
| Echte Home Assistant Core 2026.10.0 / Python 3.14.2 | **Beide fixtures geslaagd**, gewone en huidige SG-configuratie: setup, reload en unload, elk **67 geregistreerde entiteiten** en **0 fysieke serviceaanroepen**. Inclusief de nieuwe warmtepompleergrens en waterbronkwaliteitsdiagnose. |
| Echte Chromium 153 | **Vier gates geslaagd**: Water102, bestaande Water101, verbruikershistorie en warmtepomphistorie. Geen toestelwrites. Nieuwe Water-weergaven op **320 en 390 pixels visueel gecontroleerd**. |
| Onafhankelijke eindcontrole | Read-only diff- en grenscontrole akkoord, zonder open blokkerende bevinding. |
| Actuele upstreamcontrole | Echte lokale online Python-gate **geslaagd**; acht primaire GitHub-records opnieuw gecontroleerd op **20 oktober 2026 om 13:19:24 UTC**. |
| Canonieke gids | Versie beta.102, hash **`40d9fcedbdaa6010`**. De finale document-/pakketcontrole en CI moeten dezelfde bron bevestigen. |

De upstreambronnen blijven Aquarea **1.8.0**, commit `8722cf22e5a5752406aea1ba79b2cf48d4deedf3`, en SDK **1.4.0**, commit `893065a81c014cb9aa1d3350446d61c01bccf3b9`. Er zijn geen nieuwe onverwerkte wijzigingen vastgesteld. Zie [UPSTREAM_BRONNEN.md](UPSTREAM_BRONNEN.md) en `upstream_review.json`. Een publicatieversie of geslaagde upstreamgate bewijst niet welke software bij een gebruiker geladen is; het bestaande geladen-codecontract blijft vereist.

De nul fysieke serviceaanroepen in Core en browserproeven is geen live hardwareacceptatie. Er is geen lek opgewekt, kraan of toestel bediend, MQTT-configuratie gewijzigd of Panasonic-/Shelly-proef uitgevoerd. PV-scores bewijzen geen schaduwoorzaak; watervergelijkingen bewijzen geen warmwaterliters, fysiek lek of oorzaak.

De eerste main-herhaling na PR #42 vond één bestaande tijdsafhankelijke fixturefout: een fractionele testklok kon na de seconden/millisecondenconversie 120,99999976 seconden geven, waarna de leeftijd correct naar 120 werd afgerond. De bron bleef wel als verouderd afgewezen; geen productiebron werd vernieuwd. De betrokken test gebruikt nu een exact representeerbare hele-secondenklok en eist exact 121 seconden, met behoud van alle onbekend-/nul-/bronherkomstasserties. De gecorrigeerde fixture en bestaande warmtepomp-/SG-bronregressies behalen lokaal **173 geslaagde tests in 18,13 s**. De gecorrigeerde testbron moet opnieuw alle vereiste gates doorlopen.

## Opslag en rollback

Bestaande instellingen, modellen, PV-factoren, tickets, opnamepunten, teller-/dagsommen, geschiedenis en userfiles blijven behouden. Het nieuwe optionele meetgatveld `source_role` houdt waterschema **1**. Beta.101 kan de opslag lezen, maar projecteert dat extra veld weg bij een volgende opslag. Alleen de volledige privéback-up bewaart deze aanvullende herkomst voor terugkeer naar beta.102. Oude generieke meetgaten blijven conservatieve barrières; ontbrekende historische herkomst wordt niet verzonnen.

## Publicatievoorwaarden en status

Dit verslag beschrijft voltooide **lokale** controles vóór afronding van definitieve CI en publicatie. De [Validate-workflow](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml) geeft de brongebonden CI-uitslagen. De [beta.102-prerelease](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.102) is pas beschikbaar na geslaagde publicatie.

Alle **vijf gates op de definitieve PR-bron** moeten slagen vóór merge: repository/privacy/documentatie met PowerShell en volledige testsuite; HACS; Hassfest; echte Home Assistant setup/reload/unload; Chromium. Dezelfde main-bron moet die gates opnieuw doorlopen vóór publicatie. Dit vooraf opgeslagen verslag claimt PR-/main-CI, merge, tag of uploads niet als voltooid.

De immutable annotated tag **`v1.0.0-beta.102`** moet naar de geteste main-commit wijzen. De prerelease krijgt vier bestanden:

- `SolarPilot-v1.0.0-beta.102-GitHub-HACS.zip`
- `SolarPilot-v1.0.0-beta.102-local.zip`
- `BETA102_INSTELLEN.md`
- `TESTRESULTATEN_BETA102.md`

Voor upload én na opnieuw downloaden worden alle vier bestanden gecontroleerd tegen die exacte bron op bytegelijkheid, grootte en SHA-256. Bestaande tags of assets worden niet overschreven. De twee releasedocumenten hebben bytegelijke componentmirrors. De HACS-bewaarmap `userfiles` blijft behouden.

Softwaretests en GitHub-publicatie bewijzen geen uitgevoerde installatie bij een gebruiker, volledige fysieke meetdekking, lekvrijheid of gegarandeerde hardwarewerking. Zie [installatie en rollback](BETA102_INSTELLEN.md) voor de vereiste back-up en herstart.
