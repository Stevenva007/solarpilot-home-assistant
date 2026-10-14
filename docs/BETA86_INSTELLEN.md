# SolarPilot 1.0.0-beta.86 — herbeoordelen op verse resterende zon

Beta.86 voorkomt dat een **onbekende eerdere SG-reactie** binnen het **lokaal bevestigde algemene SG-profiel** alleen op een ontbrekende warmtepompvermogensmeting blijft wachten. Genoeg werkelijk overblijvende zon kan een nieuwe beoordeling dragen, met volledige conservatieve extra-vraagraming en behoud van alle harde voorwaarden. Het profiel Uitsluitend tapwater krijgt geen uitbreiding.

## Wat verandert

De aanvullende route geldt uitsluitend bij **Onbekende reactie**:

1. De bestaande rusttijd moet eerst helemaal verlopen zijn, standaard **900 seconden**.
2. Daarna bevestigen minstens **twee nieuwe oorspronkelijke betrouwbare rapporten** gedurende **300 seconden** genoeg werkelijk resterend overschot. Vereist is minstens de hoogste van de ingestelde SG-startdrempel en de volledige conservatieve extra-vraagraming. Reeds gebruikt warmtepompvermogen telt niet voor deze specifieke bevestiging.
3. Vervolgens geldt de gewone startvertraging, standaard **120 seconden**, met opnieuw alle actuele voorwaarden vóór een echte aanvraag.

De vijfminutenbevestiging begint na de rust; er is geen parallel rustkrediet. Oude rapporten herlezen, een klok laten aflopen of Home Assistant herstarten levert geen nieuw bewijs. Een tekort, oude/ontbrekende noodzakelijke bron of relevante bindingwijziging verbreekt de bevestiging. Deze route bewijst beschikbare zon, geen extra warmteopname of compressorbedrijf.

**Geen extra opname bevestigd**, **Native voltooid**, **Sessielimiet bereikt**, **Profiel gewijzigd** en echte handmatige, transport- of veiligheidsblokkeringen behouden hun aparte voorwaarden. Er komen geen nieuwe quota of instellingen.

## Welke bronnen noodzakelijk zijn

| Bron of voorwaarde | Voor SG | Bij ontbrekend, oud of onbruikbaar bewijs |
|---|---|---|
| Volledige net-/PV-begroting | Noodzakelijk | Geen nieuwe SG-vrijgave; geen oude data als actueel behandelen. |
| Eventuele batterijbron en ingeschakelde fasecontrole | Noodzakelijk waar ingesteld | Geen ruimte of zon uit onbekende waarden afleiden. |
| Bevestigde ingebruikname, profiel en relevante koelcontext/beveiliging | Noodzakelijk | Geen stilzwijgende toestemming; watts vervangen deze controle niet. |
| Werkelijke SG-contactstand en korte lokale timer | Noodzakelijk | Geen blind AAN-herhalen of verzonnen eigendom. |
| Exclusieve warmtepompvermogensmeting | Aanvullend voor krediet, verbruik en diagnose | Geen warmtepompcredit, compleet totaal of fictieve nul. Voldoende echte restzon kan wel worden beoordeeld; de volledige extra-vraagraming blijft gereserveerd. |
| Compressor-/taak-/reactiegegevens | Aanvullend voor hun eigen diagnose | Geen causale extra SG-opname of compressorwerking afleiden. Relevante native koelcontext blijft afzonderlijk noodzakelijk. |

Een terugkerende warmtepompvermogensbron wordt vanaf haar nieuwe huidige kwaliteit weer gebruikt. De update blijft haar niet permanent overslaan en vult vroegere meetgaten niet in. **Een verse negatieve vermogenswaarde is ongeldig** en vraagt onderzoek naar bron, tekenafspraak of aansluiting; zij wordt niet automatisch positief gemaakt en is geen bewezen ontbrekende fysieke meter. Beoordeel zo een probleem met een nieuwe privé-export.

## Actuele Aquarea-taakweergave

De ondersteunde Aquarea-SDK kan na een nieuwe poll haar getypeerde status/tank vervangen terwijl eerdere zoneobjecten nog oudere waarden vasthouden. De presentatie gebruikt nu de actuele vastgelegde getypeerde providerpoll, met gecontroleerde bronbinding en verse overeenkomende HA-bronnen. Onbekende of tegenstrijdige gegevens blijven onbekend. Dit verandert geen providerobject, native uitlezing voor SG-koelcontrole, apparaatinstelling of oude taakgeschiedenis.

## Upgrade

1. Maak een volledige privé HA-back-up met instellingen, opslag, modellen, APP-aanvragen, historie en userfiles. Bewaar gecontroleerde beta.85-code.
2. Geef een eigen SG-aanvraag veilig vrij waar betrouwbaar mogelijk en controleer contact/lokale afloop. Onderbreek geen beschermde apparaatcyclus en herhaal geen onzekere opdracht.
3. Update via HACS naar exact `1.0.0-beta.86` nadat releasegates en publicatie geslaagd zijn. Lokaal vervang je alleen `custom_components/solar_pilot`, met behoud van userfiles en HA-opslag.
4. **Herstart Home Assistant volledig** en herlaad browser/app volledig. Controleer backend- en kaartversie afzonderlijk. Programmabestanden vervangen bewijst geen geladen nieuwe Python-module.
5. Een bestaande interne foutpauze blijft beschermd: controleer de melding, kies **Controle afronden** en daarna bewust **Automatisch regelen** zodra actuele controles dit toelaten. De update wist deze pauze niet automatisch.
6. Controleer de concrete SG-wachtreden, nieuwe bevestiging, echte contactstand/timer en actuele bronkwaliteit. Behoud dezelfde entry, bindings, volgorde en geldige bevestigingen. Verwijder of hermaak de entry niet.

## Wat behouden blijft

De beta.85-callbackfix, tijdelijke **Aan/Uit voor 30/60 minuten**, absolute deadline/Auto-terugkeer, oorspronkelijke sessiegrenzen/importtimer, vijfminutenbuffer van de inschakelklok en verse herstartcontrole blijven intact. Gewone automatische SG behoudt minimum **twintig minuten** en **600 W gedurende vijf continue minuten**, met bestaande harde maximum en expliciete geldige gebruikerswaarden. De lokale toestemming blijft standaard 300 seconden, vernieuwd iedere 60 seconden.

Panasonic blijft zelfstandig eigenaar van comfort, warm water, verwarmen/koelen, ondersteuning, ontdooien en sterilisatie. SolarPilot bedient uitsluitend het toegewezen SG-contact. Wallbox blijft read-only; AEG krijgt maximaal één START per geldige nieuwe belading en mag afwerken. Geen gegevensreset, metercorrectie, native Panasonic-write of automatische opheffing van foutpauze.

## Rollback naar beta.85

Geef de eigen SG-aanvraag veilig vrij en controleer contact/lokale afloop. Bewaar een actuele volledige privéback-up, stop beta.86 en herstel gecontroleerde beta.85-code met behoud van entry, opslag en userfiles. Herstart HA volledig en herlaad app/browser.

Beta.85 behoudt callbackfix en eerdere bediening/timers, maar mist de nieuwe response_unknown-herbeoordeling op voldoende verse restzon. Exact herstel vraagt code én een passende privéback-up. Herstel geen oude onverbruikte APP-aanvraag bij een gestart programma; code terugzetten mag geen tweede START of oude AAN-replay vrijgeven. Geen twee runtimes tegelijk of entryverwijdering.

Actuele werking: [ACTUELE_WERKING.md](ACTUELE_WERKING.md). Eigen software-/CI-/pakketbewijs: [TESTRESULTATEN_BETA86.md](TESTRESULTATEN_BETA86.md). Privé-exports, entiteiten en woninggegevens horen niet op GitHub.
