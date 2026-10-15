# SolarPilot 1.0.0-beta.89 — restzon benutten tijdens afwassen

Een lopende afwasmachine zonder eigen vermogensmeter houdt een geschatte toekomstige piekreserve. Beta.89 laat gewone onderbreekbare SolarPilot-toestellen de **werkelijk resterende zonnestroom** benutten zonder die afwaspiek nog eens van hun zonnebudget af te trekken. De volledige piekraming blijft meetellen bij de totale elektrische ruimte. De afwasmachine blijft ononderbroken draaien.

## Wat verandert

Deze versoepeling geldt alleen voor een gewone schakelaar, numerieke actuator of gecontroleerd script dat in SolarPilot **onderbreekbaar** is ingesteld. De afwasmachine moet betrouwbaar als actief gemeld zijn en geen eigen vermogensmeter gekoppeld hebben. Een onbekende, oude of geïsoleerde afwasbron geeft deze versoepeling niet. Een gekoppelde maar onbruikbare vermogensmeter geeft evenmin vrijgave.

De P1-meter bevat het actuele afwasverbruik al. SolarPilot houdt voor een geschikte flexibele last daarom de zonnepot apart van de ruimte voor een mogelijke latere afwaspiek. Het meest voorzichtige van het actuele en gefilterde overschot blijft bepalend, na huisreserve en eventuele batterijontlading.

Fictief voorbeeld: er is **750 W** bruikbare restzon, een onderbreekbaar toestel vraagt **400 W inclusief startmarge**, en voor een actieve onbemeterde afwasmachine geldt een mogelijke piek van **2.000 W**. De zonnevoorwaarde kan dan passen. De start moet daarnaast binnen de bestaande totale elektrische ruimte mét die volledige piekreserve passen. Broncontrole, eigen startvoorwaarden, minimumtijden, voorrang en startvertraging blijven vereist. Dit is geen belofte van een onmiddellijke start.

## Uitleg op de kaart

Onder **Waarom wel of nog niet?** worden de toekomstige afwaspiek, het deel dat voor deze onderbreekbare last niet van de zonnepot wordt afgetrokken, het werkelijk toegepaste zonnebudget en de elektrische ruimte afzonderlijk getoond. Een piekraming blijft **geschat** en is geen gemeten actueel afwasverbruik.

De gehele mogelijke afwaspiek wordt niet als teruggewonnen elektrisch vermogen behandeld. Totale net-/kwartiergrenzen en bestaande fasecontroles blijven gelden. Zonder eigen meting is geen toekomstige faseverdeling of afwasfase bekend. Start de afwasverwarming later, dan kan tijdelijk netafname ontstaan terwijl de bestaande stopbuffer of minimumlooptijd van een flexibele last loopt. Deze update garandeert geen nulimport en verkort die tijden niet.

## Wat behouden blijft

- Beschermde en niet-onderbreekbare toestellen behouden hun volledige reservering. De optionele SG-zonneboost gebruikt haar bestaande strengere budget; Panasonic-comfort verandert niet.
- Onbekend verbruik blijft onbekend. Isolatiereserves en onbevestigde SG-vraag blijven gereserveerd. Met een bruikbare exclusieve afwasmeter blijft de bestaande berekening gelden.
- De gewone inschakel-/uitschakelbuffers, minimum aan/uit-tijden, vraag, interlocks, eigenaarschap en veilige terugmelding veranderen niet. De actuele vrijgave wordt ook na wachtende opdrachtopslag opnieuw gecontroleerd.
- Algemene en individuele Wallbox-voorkeuren, aftelklokken en Automatisch-terugkeer uit beta.88 blijven behouden. Wallbox blijft read-only.
- De afwasmachine behoudt maximaal één START per geldige APP-aanvraag, haar deadline en alle apparaatvoorwaarden. Een lopend programma wordt niet gestopt, gepauzeerd of via een stekker onderbroken.
- Instellingen, sensorkoppelingen, rangorde, modellen, historie en eigen bestanden blijven behouden. Er komt geen verplichte nieuwe sensor of instelling bij.

## Bestaande installatie bijwerken

1. Maak een volledige privé HA-back-up met instellingen, SolarPilot-opslag, modellen, APP-aanvragen, historie en userfiles. Bewaar gecontroleerde beta.88-code.
2. Geef vóór codevervanging een eigen SG-aanvraag veilig vrij waar betrouwbaar mogelijk en controleer contact of lokale afloop. Onderbreek geen beschermde cyclus en herhaal geen onzekere opdracht.
3. Update via HACS naar exact `1.0.0-beta.89` nadat de releasecontroles en publicatie geslaagd zijn. Lokaal vervang je uitsluitend `custom_components/solar_pilot`, met behoud van userfiles en HA-opslag.
4. **Herstart Home Assistant volledig** en herlaad browser/app volledig. Controleer backend- en kaartversie afzonderlijk. Verwijder of hermaak de entry niet.
5. Bekijk bij een geschikte flexibele last de afzonderlijke zonne- en elektrische reserve. Bewaarde minimumtijden en de bestaande startvertraging blijven van kracht. Een update maakt geen nieuwe afwasaanvraag of tweede START.

Een bestaande interne foutpauze blijft beschermd. Controleer de concrete melding en kies na herstel bewust **Controle afronden** en **Automatisch regelen**. De update heft die pauze niet automatisch op.

## Rollback naar beta.88

Bewaar eerst een actuele volledige privéback-up en geef de eigen SG-aanvraag veilig vrij waar betrouwbaar mogelijk; controleer de lokale afloop. Stop beta.89 en herstel gecontroleerde beta.88-code met behoud van entry, opslag en userfiles. Herstart HA volledig en herlaad app/browser. Gebruik nooit twee runtimes tegelijk.

Beta.88 trekt de onbemeterde toekomstige afwaspiek weer volledig af van de gewone zonnepot; een kleine last kan daardoor opnieuw wachten. De algemene en individuele Wallbox-voorkeuren en hun oorspronkelijke eindtijden blijven bij deze rollback ondersteund. Herstel nooit een oude onverbruikte APP-aanvraag nadat dezelfde belading al gestart is. Exact herstel vraagt code én een passende privéback-up.

Actuele werking: [ACTUELE_WERKING.md](ACTUELE_WERKING.md). Software-/CI-/pakketbewijs: [TESTRESULTATEN_BETA89.md](TESTRESULTATEN_BETA89.md). Privé-exports en woninggegevens horen niet op GitHub.
