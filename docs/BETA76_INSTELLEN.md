# SolarPilot 1.0.0-beta.76 — gezamenlijke planning zonder extra installatie

Beta.76 neemt de gezamenlijke vergelijking van flexibele toestellen op in dezelfde SolarPilot-integratie. Er is geen EMHASS-pakket, externe solver, add-on, aparte dienst of handmatige dependency-installatie. Panasonic en Wallbox houden hun bestaande eigenaar; alleen de bestaande SolarPilot-uitvoeringsroute kan een toegestane opdracht geven.

## Update met behoud van gegevens

1. Maak een volledige privé HA-back-up met instellingen, eigen opslag, modellen, tickets, gewone en warmtepompgeschiedenis en userfiles. Bewaar gecontroleerde beta.75-code.
2. Geef vóór codevervanging een eigen SG-aanvraag vrij en controleer contact/lokale afloop. Onderbreek geen beschermde apparaatcyclus.
3. Update via HACS naar exact `1.0.0-beta.76` na geslaagde releasegates en publicatie. Lokaal vervang je uitsluitend `custom_components/solar_pilot`, met behoud van userfiles en HA-opslag.
4. Herstart HA volledig en herlaad browser/app volledig. Controleer backend- en kaartversie afzonderlijk.
5. Bekijk Planning, Automatisch onderzoek, bestaande meetdekking, SG-contact en geschiedenis.

Behoud dezelfde entry, bindings, prioriteiten en geldige SG-/profiel-/split-/koelbevestigingen. Geen instellingenreset, algemene herbevestiging of nieuwe verplichte sensor. De actuele release-/pakketstatus staat uitsluitend in [TESTRESULTATEN_BETA76.md](TESTRESULTATEN_BETA76.md); code of documentatie in een branch bewijst nog geen gepubliceerde release.

## Wat de gezamenlijke planner doet

| Stap | Werking en grens |
| --- | --- |
| Bestaand basisplan | Behoudt de centrale prioriteiten, vensters, deadlines, beschermde cycli en bestaande nettoestemming. |
| Gezamenlijke vergelijking | Onderzoekt begrensd verschuivingen en uitwisselingen tussen toestellen. Vergelijkt de volledige geraamde huishoudelijke import-/exportkost plus de ingestelde zachte piekpenalty. |
| Overname | Alleen een opnieuw gevalideerde verbetering wordt overgenomen. De al ingeplande energie per toestel blijft minstens behouden; een lopende beschermde cyclus verschuift niet. |
| Begrensde rekentaak | Rekent buiten de HA-eventloop op een geïsoleerde momentopname, met maximaal één lopende planberekening. Een gewijzigde configuratie of afgesloten runtime maakt het resultaat ongeldig. |
| Terugval | Geen verbetering, onbruikbare invoer of rekenfout geeft geen nieuw onveilig plan; het bestaande bruikbare basisplan blijft beschikbaar. |
| Actuele uitvoering | P1/PV, elektrische grenzen, bronkwaliteit, toesteleigendom, tickets en actuele toestemming blijven leidend. Een gepland slot verleent geen nieuw actuatorrecht. |

**Gezamenlijke toestelplanning** (`joint_optimisation`) staat standaard aan. Zet deze optie uit om alleen de gezamenlijke verbeterstap over te slaan; de bestaande planner, analyse en actuele uitvoeringsguards blijven werken. Zonder prijsoptimalisatie behoudt de planner zijn bestaande voorkeur in plaats van een kostenverbetering te claimen.

Dit is een begrensde lokale zoekmethode met het beste gevonden geldige voorstel. Het is geen globale MILP-optimalisatie en biedt geen certificaat dat alle mogelijke combinaties zijn onderzocht. De piekpenalty is een planningsweging, geen exacte berekening of garantie van het Belgische capaciteitstarief. Een lager voorspeld doelbedrag is geen gemeten besparing; forecastafwijkingen en werkelijk gebruik blijven relevant.

## Batterijadvies

Na toestelplanning rekent het batterijadvies elk tijdslot in volgorde door. Het respecteert begin-SoC, minimum-/maximum-SoC uit de bestaande batterijconfiguratie, capaciteit, aparte laad-/ontlaadgrenzen en laad-/ontlaadverlies. De adviesroute gebruikt de bestaande roundtrip-efficiëntie uit de batterijanalyse, standaard 80% (20% verlies). Latere zonnestroom wordt niet eerder geleend; alleen beschikbare zonnestroom kan laden en netladen wordt niet voorgesteld.

Het advies geeft geen batterijopdracht en is geen gezamenlijk geoptimaliseerd toestel-plus-batterijplan. De bestaande realtime batterijbediening behoudt haar eigen toestemming, commandobescherming en eigenaarschap. De aparte batterij-what-if-simulatie behoudt haar bestaande verliesinstelling; haar 80%-default wordt door deze adviesroute niet stil gewijzigd.

## Behouden werking en grenzen

- Panasonic regelt comfort, programma's, percentages, koelwaarden, compressor, kleppen, pompen, ondersteuning en sterilisatie. Eén bestaande toegewezen SG-uitgang blijft de enige warmtepompactuator. Geen directe temperatuur-, modus- of heaterwrite en geen actieve thermische planning.
- De Wallbox blijft autonoom en read-only. AEG houdt één native START per nieuwe geldige APP-belading, zonder stop, programmakeuze of stekkeronderbreking.
- SG houdt standaard netafname strikt boven 600 W gedurende vijf continue minuten en minimum twintig minuten. De tekorttimer reset op of onder de grens; beide zachte timers moeten verstreken zijn. De aparte zonne-resetgrens blijft standaard 300 W.
- Korte leases blijven standaard 300 s met veilige vernieuwing iedere 60 s. Alle harde bron-/elektrische-/koel-/batterij-/Wallbox-/prioriteitsgrenzen, handmatige overname, Pauze/disable, fouten, geverifieerde native voltooiing en hardmaximum behouden vroege vrijgave. Het minimum betreft de aanvraag, geen compressorlooptijd.
- Instellingen, modellen, tickets, geschiedenis, lokaal automatisch onderzoek, exports en geüploade adviesrapporten blijven behouden. Een upload ontwikkelt geen software en past geen instelling of apparaatopdracht toe. Geen automatische upload of cloud-AI.

## Rollback naar beta.75

Geef de eigen SG-aanvraag vrij, controleer contact/lokale afloop, stop beta.76 en herstel gecontroleerde beta.75-code. Behoud entry, opslag en userfiles. Planner en batterijadvies gebruiken opnieuw de beta.75-werking; de behouden SG-regeling en het lokale onderzoek blijven beschikbaar. Code terugzetten corrigeert geen meter, bedrading of fysieke toestand.

Exact herstel vraagt code én de passende volledige privéback-up; bewaar gewenste nieuwe historie eerst. Verwijder de entry niet en laat nooit twee runtimes tegelijk werken. Voor de oude directe beta.61-regeling blijft de volledige pre-beta.62-back-up nodig. Software-/publicatiebewijs: [TESTRESULTATEN_BETA76.md](TESTRESULTATEN_BETA76.md). Volledige werking: [ACTUELE_WERKING.md](ACTUELE_WERKING.md).
