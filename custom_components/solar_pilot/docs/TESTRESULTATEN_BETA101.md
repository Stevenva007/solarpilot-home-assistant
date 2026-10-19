# SolarPilot beta.101 — test- en publicatieverslag

Versie: **1.0.0-beta.101** · 19 oktober 2026

Bouwbasis: gepubliceerde beta.100 `20f3567f4f1ff7aa6de82565ac0257e5b511e68d`, tree `6263307bae66f87e595e5d5ce103addb550db1a6`. De lichte SG-getters uit die versie blijven behouden. Alle regressies en Core-smokes gebruiken fictieve bronnen en toestellen. Persoonlijke bronidentiteiten, installatiegegevens en privé-exportbestanden worden niet opgenomen.

## Wijziging en bewijsgrens

Een optioneel ingeschakelde watermonitor leest uitsluitend expliciet gekozen cumulatieve volume-, debiet- en/of vocht-/lekbronnen. Zij valideert bronrollen, eenheden, oorspronkelijke HA-rapporttijden, waarden en actualiteit. Tellerdelta's, actueel debiet en een bestaande lekindicatie blijven afzonderlijke gegevens. Een eigen vermoeden van aanhoudend debiet is geen bewezen fysiek lek. De functie heeft geen afsluiter-, toestel-, SG- of Panasonic-schrijfroute.

De eigen begrensde historie bewaart werkelijke opnamepunten, tellerintervallen, gedeeltelijke lokale dagsommen en beschikbare boiler-/afwascontext. Context is samenloop van rapporten, geen oorzaak of verdeling van huishoudelijke liters. Huidige getoonde waarden vullen oudere punten niet aan. Historiecontrole gebruikt huidige en bewaarde bronrechten; de afzonderlijke broncatalogus geeft alleen toegestane huidige waterrollen terug.

## Gericht getoetst gedrag

- Standaard uit, geen automatische bronkeuze; de drie rollen zijn onafhankelijk optioneel. Configuratie valideert strikt booleans, bereiken, rollen en eenheden en bewaart overige bestaande instellingen.
- Echte nul blijft nul. Boolean als getal, NaN, oneindig, negatieve waarden, onbruikbare metadata, onbeschikbaarheid, herstelde/geschatte gegevens en verlopen of ongeldige tijden worden geen actuele meting.
- Nieuwe oorspronkelijke debietrapporten ondersteunen de duurbevestiging. Een vastgehouden eerste bericht, herhaalde uitlezingen, tellerpulsen, onderbreking, bronwissel en herstart leveren geen fictieve verstreken bevestigingstijd.
- Cumulatieve delta's worden eenmaal verwerkt. Tellerdaling, meetgat, lokale daggrens en nieuwe bron krijgen geen negatief verbruik, telleromloop, achteraf toegekend volledig dagverbruik of verdeelde liters. Grote geldige tellers behouden hun numerieke verschil; ontbrekend wordt geen nul.
- Native lekindicatie en eigen vermoeden blijven apart. Oude, teruglopende of onder hetzelfde rapporttijdstip gewijzigde gegevens kunnen een episode niet wissen of opnieuw activeren. Triggerbewijs loopt niet terug. Een verse negatieve waarde van een vervangende bron heft de eerdere episode niet op.
- Meldingsontvangsten blijven begrensd bewaard; een normale herstart verzendt dezelfde episode niet opnieuw. Onbekend of oud wist een melding niet. Alleen een passende verse beëindiging van dezelfde episode, of bewust uitschakelen, ruimt het eigen bericht op. Transportfalen blijft gescheiden van de regeling.
- Historie heeft maximaal dertig lokale dagen, 8192 punten, 8192 tellerintervallen en 512 gebeurtenissen. Aantalsverdringing en werkelijke dekking blijven zichtbaar. Tijdzone-/DST-grenzen volgen echte kalenderdagen. Onleesbare of toekomstige opslag wordt niet stil overschreven; runtime en cleanup blijven geïsoleerd van actuatorwerk.
- Boilervergelijkingen vragen passende verse oorspronkelijke bronnen en dezelfde contextidentiteit; herstart, meetgat en bronwissel breken de vergelijking. Een temperatuurdaling en gedeeld water bewijzen geen warmwaterliters. Afwascontext blijft huishoudelijke samenloop, geen toesteltoerekening.
- Historie-API en huidige broncatalogus zijn entry-gebonden en alleen-lezen. Anoniem, ongeldige query's, geïnjecteerde entiteiten, verkeerde/afgesloten runtime, bronwissel tijdens controle en ontbrekende rechten geven geen extra toegang. Private ACL-identiteiten worden niet naar frontend of historie-API gekopieerd.
- De bestaande SG-/Panasonic-bevoegdheden, bronactualiteit, elektrische grenzen, afwasbescherming, overige apparaten, timers, modellen, historie en userfiles blijven behouden.

## Actuele upstreamcontrole

Op **19 oktober 2026 om 18:30:51 UTC** zijn alle **acht GitHub-records** opnieuw gecontroleerd. Aquarea **1.8.0**, commit `8722cf22e5a5752406aea1ba79b2cf48d4deedf3`, en SDK **1.4.0**, commit `893065a81c014cb9aa1d3350446d61c01bccf3b9`, zijn ongewijzigd ten opzichte van het inhoudelijk verwerkte broncontract. Dit geeft geen bewijs dat een bepaalde versie lokaal is geïnstalleerd. Het actuele checkpoint en de primaire bronverwijzingen staan in [UPSTREAM_BRONNEN.md](UPSTREAM_BRONNEN.md) en `upstream_review.json`; de waterbronbeoordeling staat in [WATER_BRONNEN_BETA101.md](WATER_BRONNEN_BETA101.md). Ook de echte lokale online-upstreamgate is geslaagd. Dezelfde onlinegate blijft in CI vóór publicatie vereist.

## Uitgevoerde validatie

Onderstaande sets **overlappen** en worden niet bij elkaar opgeteld. De aantallen zijn gericht bewijs; zij vervangen de volledige suite en definitieve releasegates niet.

| Controle | Vastgelegd resultaat |
|---|---|
| Gerichte watermodel-/historiekset, met gerelateerde API-/meldingsgevallen, Python 3.13.16 | **448 tests geslaagd**. Inclusief oorspronkelijke-tijdcorrectie voor wissen/heractiveren van waarschuwingen. |
| Onafhankelijke adversarial model-/runtimecontrole | **119 tests geslaagd**. Onder meer meetgaten, herstart, bronwissel, herstelgrenzen, opslag en behouden bronrechten. |
| Gerichte meldings- en configuratiesets | **80 tests geslaagd**. Inclusief ontvangstbewaring, overeenkomende episode en bron-/typevalidatie. |
| Gerichte API-/exportcontrole | **442 tests geslaagd**. Huidige en historische rechten, gesloten query's en read-only export. |
| Echte Home Assistant Core 2026.10.0, Python 3.14.2: gewone en huidige-SG-fixture | **Beide geslaagd**: echte setup, reload en unload, **67 geregistreerde entiteiten** per fixture en **0 fysieke serviceaanroepen**. Inclusief geregistreerd waterschema, leesrechten, broncatalogus, opslag en afgesloten-runtimecontrole. Entryverwijdering verwijdert de eigen watermelding en behoudt andere meldingen. |
| Runtime-integratie en behouden platformregistry | **137 tests geslaagd**: 119 onafhankelijke gevallen, 11 runtimehooks en 7 registrygevallen; deze set overlapt met bovenstaande. |
| Verwijdering, watermeldingen en runtime na de laatste opruimcorrectie | **91 tests geslaagd**. De oude geïsoleerde verwijderfixture kent nu de nieuwe opslag; verwijderen ruimt ook uitsluitend de eigen watermelding op. |
| Volledige definitieve testsuite | **8217 tests geslaagd** op Python 3.13.16 in 173,30 seconden, met `PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider`. |
| Chromium/browsercontrole van de definitieve waterweergave | **Alle drie geslaagd**: Water101, bestaande verbruikershistorie en warmtepomphistorie; watergebaren, toetsenbord, verticaal scrollen, oorspronkelijke meetpunten, bronlinks, herladen en nul toestelopdrachten. Visueel gecontroleerd op 320 en 390 pixels. Daarnaast **23 nieuwe water-UI-tests** geslaagd. |
| Gegenereerde actuele gids, optiehulp en overdracht | **Geslaagd**; gidshash **c0e6d2a9c60f0933**. Release-identiteit en bytegelijke documentmirrors gecontroleerd. |
| Openbare privacy/structuur, SG-bevoegdheden, bronactualiteit en syntaxis | **Geslaagd**: echte online-upstreamcontrole, SG-grenscontrole, 100 Python-componentmodules en JSON-/JavaScript-syntaxis. Definitieve pakketcontroles volgen in CI vóór upload en na downloaden. |

De eerste volledige run vond één verouderde geïsoleerde verwijderfixture naast 8216 geslaagde tests. De fixture is uitgebreid met de wateropslag; de verwijderroute ruimt ook de eigen watermelding op. De gerichte 91 tests, beide Corefixtures en de volledige definitieve 8217-testherhaling slagen daarna.

De Core-proef gebruikt de echte geregistreerde WebSocket-schema's en HA-authenticatie-/leesrechten. `water_registered_read_only_acl_store_reload_unload` registreert de waterspecifieke proef; `water_owned_notice_removed_on_entry_removal` bevestigt de afzonderlijke meldingsopruiming. De nul fysieke serviceaanroepen is geen live apparaatacceptatie. Er is geen lek opgewekt, waterkraan bediend, gatewayfirmware gewijzigd of Panasonic-/Shelly-proef uitgevoerd.

## Publicatievoorwaarden en status

Dit verslag legt het beschikbare bewijs **vóór afronding van de definitieve CI/publicatie** vast. De [Validate-workflow](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml) geeft de brongebonden uitslagen; de [beta.101-prerelease](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.101) verschijnt pas na geslaagde publicatie.

Alle **vijf gates op de definitieve PR-bron** moeten slagen vóór merge: repository/privacy/documentatie met PowerShell en volledige testsuite; HACS; Hassfest; echte Home Assistant setup/reload/unload; Chromium. Dezelfde main-bron moet die gates opnieuw doorlopen vóór publicatie. PR-/main-gates, merge, tag en assets zijn met dit vooraf opgeslagen verslag niet als voltooid geclaimd. De volledige lokale suite is hierboven met haar voltooide uitslag vastgelegd.

De immutable annotated tag **`v1.0.0-beta.101`** moet naar de geteste main-commit wijzen. De prerelease krijgt vier bestanden:

- `SolarPilot-v1.0.0-beta.101-GitHub-HACS.zip`
- `SolarPilot-v1.0.0-beta.101-local.zip`
- `BETA101_INSTELLEN.md`
- `TESTRESULTATEN_BETA101.md`

Voor upload én na opnieuw downloaden worden de vier bestanden tegen die bron gecontroleerd op bytegelijkheid, grootte en SHA-256. Bestaande tags of assets worden niet overschreven. De twee releasedocumenten hebben bytegelijke componentmirrors. De HACS-bewaarmap `userfiles`, bestaande entry, instellingen, eigen opslag, modellen en historie blijven behouden.

Softwaretests en GitHub-publicatie bewijzen geen uitgevoerde update op een gebruikersinstallatie, gegarandeerde lekdetectie, volledig gemeten dagverbruik of fysieke hardwarewerking. De gekoppelde CI-runs geven de definitieve brongebonden uitslagen en assetcontrole; dit vooraf opgeslagen verslag loopt niet op publicatie vooruit.
