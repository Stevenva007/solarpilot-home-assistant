# SolarPilot 1.0.0-beta.69 — update en controle

De SG-startdrempel telt nu de bruikbare actuele warmtepompbijdrage mee in de gemeten zonnebalans. Een al draaiende warmtepomp hoeft niet opnieuw de hele drempel als extra injectie te hebben. Taakweergave, meetafkeur en leren bewaren de afzonderlijke bronnen. Panasonic blijft zelfstandig regelen; SolarPilot behoudt één bestaande toegewezen SG-uitgang.

## Update met behoud van gegevens

1. Maak een volledige privé Home Assistant-back-up, inclusief configuratie, SolarPilot-opslag, modellen, tickets en userfiles. Bewaar de beta.68-code voor rollback.
2. Geef een eigen SG-aanvraag vrij vóór codevervanging en controleer gemelde contactstand/lokale afloop. Laat beschermde apparaatcycli behouden.
3. Update in HACS naar exact `1.0.0-beta.69` na publicatie en herstart Home Assistant volledig. Herlaad de browserpagina volledig of sluit de app volledig af en open haar opnieuw.
4. Controleer backend- én kaartversie onder Instellingen & controle: beide moeten `1.0.0-beta.69` zijn. Een integratieherlading vervangt geen reeds geladen kaartcode.
5. Controleer behouden instellingen, volgorde, APP-tickets, modellen, historie en userfiles. Geldige ongewijzigde SG-/profiel-/split-/koelbevestigingen blijven staan. De update vraagt geen nieuwe verplichte sensoren of leervragen.

Lokaal vervangen: uitsluitend `custom_components/solar_pilot` uit het local-ZIP; behoud `userfiles` en alle HA-opslag. Verwijder of herschep de bestaande integratie niet. Eerste installatie blijft HACS Integration, HA-herstart en toevoegen onder Apparaten & diensten. De kaart wordt automatisch geregistreerd; een aparte Lovelace-resource is niet nodig.

## Wat de nieuwe SG-berekening doet

| Onderdeel | Betekenis |
| --- | --- |
| Werkelijk restoverschot | Actuele conservatieve netinjectie na batterijontlading en beschermde reserves. Dit blijft de ruimte voor gewone zonneverbruikers. |
| Meegetelde warmtepompbijdrage | Extra afgeleide bijdrage aan de gezamenlijke zonnebegroting op basis van complete actuele bevestigde exclusieve meting. Geen afzonderlijk gemeten PV-aandeel. |
| SG-startbijdrage | De gezamenlijke bijdrage, begrensd door gemeten PV en gecorrigeerd voor actuele netafname, batterijontlading en reserves. Deze wordt met jouw bestaande startdrempel vergeleken. |
| Raming extra SG-vraag | Jouw bestaande aparte conservatieve raming van mogelijke vermogensstijging. Het huidige warmtepompvermogen bewijst geen gegarandeerde SG-stijging. |
| Elektrische ruimte | Actuele ruimte binnen vaste import-, fase- en kwartiergrenzen, na reeds toegezegde vraag. Warmtepompcredit vergroot deze ruimte niet. |

Voorbeeld met fictieve waarden en zonder reserves/batterijontlading: 2000 W compleet gemeten warmtepompverbruik en 1000 W restinjectie kunnen samen 3000 W voor de SG-drempel opleveren, zolang gemeten PV dat ondersteunt. Er hoeft dus geen extra 3000 W injectie te zijn. De mogelijke extra SG-vraag moet daarnaast binnen de echte elektrische grenzen en hogere prioriteiten passen.

Een oude, ontbrekende, negatieve, geschatte, gedeeltelijke of overlappende warmtepompmeting levert geen extra credit. Eén bevestigde totaalmeter of twee complete actuele bevestigde niet-overlappende voedingen worden ondersteund. Afgeleide/leermodelwatts tellen niet mee.

Een actieve of gevraagde EV-laadsessie houdt zijn voorrang en actuele veilige restzonruimte. SG krijgt geen EV-overnamerecht, ook als gewone lasten dat onder voorwaarden hebben. Native Panasonic-comfort blijft autonoom. Lagere eigen lasten kunnen alleen onder de bestaande bescherming wijken; een stopopdracht is nog geen vrij vermogen.

De bestaande start-/stopvertraging, rusttijd, sessielimiet, lokale lease en vernieuwing blijven staan. Werkelijke netafname blijft bepalend voor tekort/vrijgave. Een nieuwe zonneperiode na een afgeronde algemene sessie gebruikt echte restinjectie, zodat gelijkblijvend warmtepompverbruik geen nieuwe herstartlus geeft. Panasonic-percentages, koelwaarden, temperaturen en programma's worden niet geschreven.

## Taak, bronnen en leren controleren

- Bekijk Warmtepomp in Overzicht, Toestellen en Warmtepomp. Verse getypeerde onafhankelijke tankstatus ON/WATER kan bij ruimtebedrijf OFF samen met complete actieve hoofdmeting **Boiler opwarmen · Afgeleid** tonen. De ruwe OFF en het bronbereik blijven in Details/export. Bevestigd globaal UIT, onbekend bereik, conflicten, ontdooien en onvolledige/oude/heater-only meting houden hun grenzen.
- Bekijk in Details de laatste echte rapportagetijd, eenheid en concrete afkeurreden per meter. Gemeten 0 W is geen ontbrekende waarde. Een nieuwe regelronde maakt een oud rapport niet vers.
- Bekijk in Energie/SG Details de gezamenlijke startbijdrage, echte restinjectie en concrete net-/fase-/kwartier-/EV-blokkering. Theoretisch resterend kwartierbudget is geen fysieke toestemming.
- Nieuwe afgeleide taakvoorbeelden blijven aparte diagnose. Nieuwe stabiele bevestigde native overgangen bouwen gevalideerde modelpools. Oude voorbeelden/dagen blijven bewaard; ontbrekende bewijsherkomst geeft geen bevestigde planningswaarde. Leren verandert geen realtime netruimte en vult oude gaten niet achteraf in.
- Het teruggelezen analyseantwoord behoudt zijn exacte bronbinding. Vier geïmplementeerde generieke logische voorstellen worden vanaf beta.69 door het geïnstalleerde register herkend; een upload zelf verandert geen code, instellingen of apparatuur.

Deze controle gebruikt bestaande HA-bronnen en vraagt geen fysieke proef. Softwaretests bewijzen geen echte bedrading, Shelly-afloop, condensbeveiliging, ontvangen SG of Panasonic-reactie. Werkelijk gewijzigde koppelingen/bereiken houden hun bestaande lokale bevestigingsvoorwaarden.

## Rollback

Geef de eigen SG-aanvraag vrij, controleer contactstand/lokale afloop en stop de nieuwe runtime. Zet gecontroleerde beta.68-code én de volledige passende privéback-up van vóór deze update terug. Alleen een oude ZIP herstelt gewijzigde opgeslagen bewijsvelden niet exact. Laat nooit twee runtimes het contact tegelijk beheren.

Terugkeer naar oude directe beta.61-regeling blijft de volledige pre-beta.62-migratieback-up vereisen. Het privéherkomstarchief is geen volledige restore en voert geen replay uit.

Volledige werking: `ACTUELE_WERKING.md` en SolarPilot → Uitleg. Werkelijke validatie: `TESTRESULTATEN_BETA69.md`. Privé-export, bronkoppelingen en huishoudelijke metingen horen niet in publieke code/pakketten.
