# SolarPilot 1.0.0-beta.76 — testresultaten

Datum: **12 oktober 2026**. Bouwbasis: gepubliceerde beta.75, commit `289bfc27ff486028bc69037b3d97ef4e771b12ff`. Dit verslag registreert werkelijk uitgevoerde lokale controles; brongebonden GitHub-CI en publicatie blijven afzonderlijk. Oudere resultaten gelden niet als beta.76-validatie.

## Gecontroleerde wijziging

Eén ingebouwde, dependencyvrije gezamenlijke toestelplanner verbetert bestaande combinaties via begrensde verschuivingen en uitwisselingen. Iedere toestel-/kalenderdaghoeveelheid, volledige cyclus, venster en nettoestemming blijft behouden. De huishoudelijke voorspellingsscore combineert import/export en een zachte piekvermijdingsstraf. Beste gevonden is geen globaal optimum, gemeten besparing of capaciteitstarieffactuur. EMHASS is een ontwerp-/documentatiereferentie; er is geen EMHASS-broncode gekopieerd, package ingebed of solvercompatibiliteit geclaimd.

Batterijadvies verwerkt SoC chronologisch met verlies, aparte vermogenslimieten en bestaande geconfigureerde reserve/maxima. Het runtime-rendement volgt de bestaande batterijanalyse, standaard 80% (20% verlies). Ontbrekende of onvolledige batterijgegevens verlenen geen scenario; meerdere batterijen blijven een herkenbaar geaggregeerd advies, geen individuele dispatchsimulatie. Batterij en toestellen worden niet gezamenlijk wiskundig geoptimaliseerd.

De rekentaak gebruikt uitsluitend een geïsoleerde momentopname via de HA-executor. Maximaal één worker, ook na annulering; gewijzigde instellingen/configuratie, afgesloten runtime of fouten kunnen geen nieuwe toestemming creëren. Na het await leest de regelronde tijd, apparaatvoorwaarden en netbronnen opnieuw. Panasonic/Wallbox en alle bestaande uitvoeringsgrenzen blijven behouden.

## Definitieve lokale uitvoering

| Controle | Uitgevoerd resultaat |
| --- | --- |
| Volledige pytest, Python 3.12.14 | **4635 geslaagd in 85,43 s**; bytecode en pytestcache uitgeschakeld. |
| Nieuwe gerichte gevallen | **70 cases**: 21 joint optimizer, 27 batterij, 19 executor/runtime en 3 end-to-end planner. Dit is onderdeel van de volledige suite, geen extra opgetelde suite. |
| Python-productiesyntax | AST-parse van alle **79** productiemodules geslaagd. |
| Kaart en optiehulp | Beide JavaScript-bestanden geslaagd voor Node-syntax; UI-regressies onderdeel van pytest. |
| Canonieke uitleg en mirrors | Geslaagd; guidehash `8be962f4c2674595`, **345** optiehulpvelden. |
| Overdracht, SG-bevoegdheidsgrens, publieke preflight en diff | Geslaagd. |

Een eerdere volledige run vond één achtergebleven versieheader in de optiehulp-JavaScript. Die is gecorrigeerd vóór deze definitieve volledige herhaling. Sterkere executorproeven vonden een uitstelregel die na uitschakelen kon terugkeren; de helper maakt alle plannerholds vrij wanneer de planner uitgeschakeld is. Gerichte onafhankelijke review vond vaste batterijgrenzen; de runtime gebruikt nu bestaande reserve/maxima en verwerpt onvolledige vlootgegevens. De definitieve suite toetst deze gecorrigeerde bron.

## Wat de regressies bewijzen

- De end-to-end planner verbetert een fictieve ongunstige basiscombinatie met **0,27 euro voorspelde horizonenergiekost**, bij exact dezelfde voorspelling, prijzen en geplande energie. Dit is een gecontroleerd tegenvoorbeeld, geen thuisbesparing of jaarlijkse prognose.
- Paaruitwisseling ontsnapt aan een lokaal gulzig plan; kostenverbetering zonder verlies van geplande energie of verschuiving naar morgen. Gehele slots, beschermde cycli, prioriteitsgebonden zonnevoorwaarden, ontbrekende voorspelling en niet-bevoegde apparaten blijven beschermd.
- Ongeldige basisplannen blijven onveranderd. Tijd/evaluatiegrenzen stoppen de zoekfase; finale validatie en transactionele commit herstellen zelfs een geïnjecteerde setterfout.
- Energie van latere zon kan een vroeger batterijslot niet voeden. Rendement, aparte vermogensgrenzen, beginlading en SoC-reserves zijn conserveerbaar; reserve 50% en maximum 80% worden expliciet doorgetest.
- Eventloop-respons, geïsoleerde inputs, behoud van levende kwaliteits-/leermodellen, één worker, annulering en weggegooide resultaten zijn werkelijk in async-proeven gecontroleerd. Een gewijzigde P1-/vraagbron tijdens rekenen wordt opnieuw gelezen vóór een mogelijke dispatch.

## CI, release en praktische grens

Op het moment dat deze immutable bronbijlage werd geschreven waren de nieuwe GitHub-gates en release nog niet uitgevoerd. De actuele brongebonden status staat in [Validate Actions](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml). Vereist: repositorysuite, HACS, officiële Hassfest, echte Core **2026.10.0** setup/reload/unload en Chromium op 320/390/768/1280 px. De bestaande main-workflow publiceert uitsluitend na alle vijf gates en controleert vier releasebestanden tegen de commit. Deze bijlage voorspelt geen run-ID, uitslag of toekomstige publicatie.

Lokale mocks/Node-controles vervangen geen echte Core-/browsergate. Geen live huisconfiguratie, fysieke Shelly/Panasonicreactie, compressorbedrijf, bedrading of werkelijke besparing is hier geaccepteerd. Installatie en rollback: [BETA76_INSTELLEN.md](BETA76_INSTELLEN.md).
