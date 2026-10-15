# SolarPilot beta.88 — installatie en upgrade

Beta.88 voegt **Wallbox voorrang geven** toe, algemeen en per ondersteund flexibel toestel. Je kiest **30 min, 1 uur, 2 uur, 3 uur, 4 uur, 5 uur** of **tot ik terug op automatisch zet**. Tijdelijke keuzes tonen een aftelklok; de oorspronkelijke eindtijd blijft na herladen of herstart behouden.

**Begin met [BETA88_INSTELLEN.md](docs/BETA88_INSTELLEN.md).** Volledige werking: [ACTUELE_WERKING.md](docs/ACTUELE_WERKING.md) en **SolarPilot → Uitleg**. Uitgevoerde checks en publicatiestatus: [TESTRESULTATEN_BETA88.md](docs/TESTRESULTATEN_BETA88.md). Technische overdracht: [OVERDRACHT.md](OVERDRACHT.md). Oudere resultaten bewijzen geen beta.88-release.

## Wallbox-voorrang gebruiken

1. Schakel **Wallbox voorrang geven** in en kies de duur. Op de SolarPilot-kaart kies je die vóór activering; een gewone Home Assistant-schakelaar AAN kiest standaard 30 minuten.
2. De algemene keuze kopieert de duur en eindtijd naar de aanwezige ondersteunde toestelkeuzes. Daarna kun je ieder toestel afzonderlijk aanpassen, ook terug naar **Automatisch**.
3. Algemeen terug naar **Automatisch**, handmatig of door afloop, zet **alle individuele keuzes terug op Automatisch**, ook afwijkende blijvende keuzes. Alleen individuele uitzonderingen actief? Gebruik **Alle toestellen terug op Automatisch** om ze samen te wissen.

Automatisch volgt de huidige opgeslagen rangorde; je hoeft die niet opnieuw in te stellen. Een individuele afloop verandert de andere toestellen niet. De blijvende keuze toont **tot ik terug op automatisch zet**.

De afwasmachine krijgt deze keuze niet en krijgt hierdoor geen extra startblokkering. Haar bestaande klaarzettoestemming, deur-/apparaatvoorwaarden, deadline, elektrische ruimte en globale modus blijven gelden. Een lopende beurt mag afwerken. Bij de warmtepomp geldt deze keuze uitsluitend voor de optionele SG-zonneboost; Panasonic-comfort blijft zelfstandig. De nieuwe tijdelijke voorkeur blokkeert nieuwe SG-starts en respecteert de lopende oorspronkelijke SG-minimumduur. Bestaande vrijgavegronden, waaronder de bestaande Wallbox-/EV- en veiligheidsregels, blijven gelden en kunnen eerder vrijgeven.

SolarPilot start of versnelt de auto hiermee niet rechtstreeks. Wallbox blijft read-only. Bestaande actuele laadvraag, hysterese, klein overschot, minimumtijden, beschermde cycli, terugmelding en elektrische grenzen bepalen wanneer een flexibele last kan wijken. In Alleen bekijken of Pauze kun je de voorkeur bewaren, maar er ontstaat geen fysieke bedieningsvrijgave.

## Bestaande installatie bijwerken

1. Maak een volledige privé HA-back-up met instellingen, SolarPilot-opslag, modellen, APP-aanvragen, geschiedenis en userfiles. Bewaar gecontroleerde beta.87-code.
2. Geef vóór codevervanging een eigen SG-aanvraag veilig vrij waar betrouwbaar mogelijk; controleer contact of lokale afloop. Onderbreek geen beschermde apparaatcyclus.
3. Update via HACS naar exact `1.0.0-beta.88` nadat releasegates en publicatie zijn geslaagd. **Herstart Home Assistant volledig** en herlaad browser/app volledig.
4. Controleer backend- en kaartversie afzonderlijk. Behoud dezelfde entry, bindings, opgeslagen rangorde en geldige lokale SG-/profiel-/split-/koelbevestigingen.
5. Controleer de algemene en individuele Wallbox-voorkeur, resterende tijd en terugkeer naar Automatisch. De update zelf activeert geen nieuwe voorrangskeuze.
6. Controleer taak- en boilerwaarden, SG-contact/timers, oorspronkelijke AEG-aanvraag/deadline, Planning, Meetkwaliteit en geschiedenis. Een update maakt geen nieuwe belading of tweede START.

Lokaal vervang je uitsluitend `custom_components/solar_pilot`, met behoud van userfiles en HA-opslag. Verwijder of hermaak de entry niet. Geen extra installatie, verplichte nieuwe sensor, instellingenreset of parallelle regelaar.

Een bestaande interne foutpauze blijft beschermd. Controleer de concrete melding, kies **Controle afronden** en daarna bewust **Automatisch regelen** zodra actuele controles dat toelaten. De update wist de foutpauze niet automatisch.

## Wat behouden blijft

Verse, verder geldige negatieve warmtepompverbruikswaarden tellen als 0 W met oorspronkelijke bronwaarde en markering in de diagnose. Ontbrekend, oud of onvolledig blijft onbekend; P1-, net-, batterij- en fasetekens blijven behouden. De Aquarea-weergave, actuele bronnen en oude historie blijven gescheiden.

De aparte tijdelijke SG-Aan/Uit-bediening voor 30/60 minuten blijft beschikbaar. Automatische SG behoudt twintig minuten minimum voor zachte importvrijgave en de nieuwe tijdelijke voorkeursvrijgave, 600 W netafname gedurende vijf continue minuten, bestaande maximumduur, startbuffer, actuele herstartcontrole en korte lokale toestemming van standaard 300 seconden met vernieuwing iedere 60 seconden. Harde grenzen en echte eigendomsoverdracht blijven leidend; geen compressorlooptijdgarantie.

Panasonic blijft eigenaar van comfort, verwarmen/koelen, tank, ondersteuning en sterilisatie. SolarPilot bedient daarvoor uitsluitend het bewust gekoppelde SG-contact. Wallbox blijft autonoom en read-only; AEG behoudt maximaal één START per geldige nieuwe belading en haar bestaande deadline. PV-factoren, modellen, batterijadvies, kosten en geschiedenis blijven bewaard.

## Nieuwe installatie

Voeg `https://github.com/Stevenva007/solarpilot-home-assistant` toe in **HACS → Custom repositories** als **Integration**, download SolarPilot en herstart HA. Voeg de integratie toe onder **Instellingen → Apparaten & diensten**. Selecteer betrouwbare lokale bronnen en begin met **Alleen bekijken**. De kaart wordt automatisch geregistreerd. SG staat standaard uit tot gecontroleerde ingebruikname.

## Rollback naar beta.87

Zet algemeen en alle individuele Wallbox-keuzes terug op **Automatisch**. Geef de eigen SG-aanvraag veilig vrij waar betrouwbaar mogelijk en controleer contact of lokale afloop. Maak een actuele volledige privéback-up, stop beta.88 en herstel gecontroleerde beta.87-code met behoud van entry, opslag en userfiles. Herstart HA volledig en herlaad browser/app.

Beta.87 kent de nieuwe tijdelijke Wallbox-voorkeuren niet; zij voert ze niet uit en gebruikt haar bestaande prioriteitsregels. De HP-nulinterpretatie en eerdere SG-/Aquarea-fixes blijven beschikbaar. Exact herstel vraagt code én passende privéback-up. Geen twee runtimes tegelijk, tweede START, oude AAN-replay of entryverwijdering. Zie [BETA88_INSTELLEN.md](docs/BETA88_INSTELLEN.md).

Openbare broncontrole en de afzonderlijke geautoriseerde wekelijkse ontwikkeltaak staan in [UPSTREAM_BRONNEN.md](docs/UPSTREAM_BRONNEN.md). De taak verandert geen lokale Home Assistant-installatie of apparaten.
