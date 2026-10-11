# SolarPilot 1.0.0-beta.73 — wolkenbuffer voor de SG-aanvraag

Beta.73 laat gewone actueel gemeten netafname standaard **continu boven 600 W gedurende vijf minuten** aanhouden voordat zachte SG-vrijgave mogelijk is. Die timer loopt tegelijk met het behouden minimum van twintig minuten. Korte lokale leases blijven veilig vernieuwd tijdens de wolkenwachttijd, ook na het minimum. Harde guards en het behouden maximum blijven leidend.

## Update met behoud van gegevens

1. Maak een volledige privé HA-back-up met instellingen, eigen opslag, modellen, tickets, gewone en warmtepompgeschiedenis en userfiles. Bewaar gecontroleerde beta.72-code.
2. Geef vóór codevervanging een eigen SG-aanvraag vrij en controleer gemelde contactstand/lokale afloop. Onderbreek geen beschermde apparaatcyclus.
3. Update via HACS naar exact `1.0.0-beta.73` na publicatie. Lokaal vervang je uitsluitend `custom_components/solar_pilot`, met behoud van userfiles en HA-opslag.
4. Herstart HA volledig en herlaad browser/app volledig. Controleer backend- en kaartversie afzonderlijk.
5. Controleer bij geavanceerde SG-instellingen de nieuwe **Toegestane netafname vóór stopvertraging (W)** en **Netafname moet continu aanhouden (s)**, naast het behouden minimum en maximum. De zonne-resetgrens staat apart.

Behoud dezelfde entry, bindings, prioriteiten en geldige SG-/profiel-/split-/koelbevestigingen. Geen algemene herbevestiging, nieuwe sensor of automatische native Panasonic-instelling. Eerste installatie blijft HACS Integration en toevoegen onder Apparaten & diensten; nieuwe SG-sturing blijft uit tot de bestaande lokale voorwaarden bevestigd zijn.

## Twee voorwaarden voor gewone tekortvrijgave

| Voorwaarde | Standaardgedrag |
| --- | --- |
| Wolkenbuffer | Alleen strikt meer dan 600 W actueel gemeten netafname start de tekorttimer. |
| Aaneengesloten tijd | Boven de grens blijven gedurende 300 s, vijf minuten. Bij 600 W of lager vervalt die lopende timer; een latere overschrijding begint opnieuw. |
| Minimum | Twintig minuten vanaf bevestigde contact-AAN, begrensd door de bij AAN nog beschikbare harde maximumtijd. |
| Samenwerking | Beide voorwaarden moeten zijn verstreken. De tekorttimer loopt tijdens het minimum door. |
| Geen tekort | Minimumafloop is geen verplichte stop. Normale actuele voorwaarden bepalen of de aanvraag doorgaat. |

Begint netafname boven 600 W in minuut 18, dan kunnen vijf continue minuten pas in minuut 23 voltooid zijn. Blijft een eerder begonnen tekort vijf minuten onafgebroken boven de grens tot voorbij minuut 20, dan kan de actuele beoordeling bij het minimum al vrijgeven. Terugkeer naar 600 W of lager wist de tekorttimer, zonder het aanvraagminimum opnieuw te starten.

Deze buffer kan tijdelijk gewone netafname binnen alle bestaande harde grenzen toelaten. Zij vergroot geen fase-/net-/kwartiercapaciteit, geeft geen EV-krediet en verlaagt de aparte conservatieve extra-vraagraming niet.

## Afzonderlijke instellingen en upgrade

| Instelling | Betekenis |
| --- | --- |
| `import_threshold_w` | Nieuwe netafname-/wolkenbuffer, standaard 600 W. Instelbereik 0–20000 W, formulierstap 50 W. |
| `stop_delay_s` | Aaneengesloten tijd boven die importgrens, standaard 300 s. |
| `hysteresis_w` | Behouden zonne-resetgrens voor restoverschot, standaard 300 W. Geen netafnamebuffer. Bestaande afwijkende waarde blijft staan. |
| `min_session_s` / `max_session_s` | Behouden minimum en hardmaximum; een bestaand korter maximum wordt niet verhoogd. Expliciet minimum nul blijft behouden. |

Ontbreekt het nieuwe importveld bij de oude standaardcombinatie 300 W/60 s, dan gebruikt de runtime effectief 600 W/300 s. Andere oude expliciete beleidscombinaties behouden hun importgrens en tekortvertraging. Een aanwezige nieuwe importwaarde blijft behouden. Nieuwe configuratie gebruikt 600 W/300 s. Dit gebeurt door normalisatie bij uitlezen, zonder automatische write naar opgeslagen opties of gegevensreset.

Het bewijs van een nieuwe zonneperiode blijft afzonderlijk: eerst vijf minuten werkelijk laag restoverschot op of onder de behouden zonne-resetgrens, daarna vijf minuten teruggekeerd restoverschot vanaf de startdrempel, met echte nieuwe bronrapporten. De gewone startvertraging blijft daarnaast gelden. De 600 W-wolkenbuffer verruimt die start-/resettoestemming niet.

## Korte lease en harde vrijgave

Lokale toestemming blijft standaard 300 s, met vernieuwing iedere 60 s zonder UIT/AAN-cyclus. Tijdens geldige minimum- en wolkenwachttijd kan zij veilig worden vernieuwd, ook na het minimum. Bij volledig bevestigd tekort én verstreken minimum geeft de actuele beoordeling vrij; er is geen eindeloze verlenging voorbij een harde grens.

Bronverlies, elektrische/batterij-/koel-/Wallbox-/prioriteitsgrenzen, handmatige overname, Pauze/uitschakelen, geverifieerde native voltooiing/bevestigd geen extra opname, transport-/leasefout en hardmaximum behouden vroege vrijgave. Lage watts of onbekende reactie alleen zijn geen native beëindigingsbewijs.

De lokale timer is geen twintigminutentimer of vijfminutengarantie. Bij uitval kan zij eerder vervallen. Vernieuwen reset minimum of tekorttijd niet; reload geeft geen nieuwe AAN- of minimumtoestemming. Een kort hardmaximum reserveert bevestigingsruimte in de lease en kan conservatief eerder aflopen. De absolute grens wordt opnieuw getoetst vóór eerste AAN en vernieuwing, na opslag-/netwerkvoorcontrole.

De wolkentimer gebruikt de actuele P1-netmeting. Resterende schermtijd blijft begrensd door de geldigheid vanaf de oorspronkelijke P1-rapportagetijd, de bevestigde lease en het harde maximum; een schermklok maakt oude brondata niet vers.

## Panasonic, geschiedenis en privacy

De regeling beschermt de **SG-aanvraag**, niet een gegarandeerde compressorlooptijd of levensduur. Panasonic blijft eigenaar van programma's, percentages, koelwaarden, comfort en beveiligingen. Eén bestaande toegewezen SG-uitgang blijft de enige warmtepompactuator.

Alle overige apparaten, gebruikerswaarden, modellen, tickets en geschiedenis blijven behouden. Dertig lokale kalenderdagen warmtepompretentie staat los van 1/24/168 rollende analyse-uren; alle overlappende datums behouden volledige geregistreerde kalenderdagtotalen, expliciete grensdatums en meetdekking. Geen backfill of energie naar rato.

Geschiedenis blijft read-only met bron-READ-controles; analyse-export blijft een bewuste lokale beheerderdownload. Geen huishoudelijke exports, bindings of back-ups in publieke bron of release-assets. Softwaretests bewijzen geen fysieke SG-/meter-/condens-/Panasonicacceptatie.

## Rollback naar beta.72

Geef de eigen SG-aanvraag vrij, controleer contact/lokale afloop, stop beta.73 en herstel gecontroleerde beta.72-code. Behoud entry, opslag en userfiles. Beta.72 kent de nieuwe importbuffer en leasevernieuwing tijdens wolkenwachttijd na het minimum niet; lokale toestemming kan daar eerder aflopen. Code alleen herstelt niet de oude instellingenwaarden.

Voor exact herstel gebruik je code én de passende volledige privéback-up; bewaar gewenste nieuwe historie eerst. Verwijder de entry niet en laat nooit twee runtimes tegelijk werken. Voor de oude directe beta.61-regeling blijft de volledige pre-beta.62-back-up nodig. Software-/publicatiebewijs: [TESTRESULTATEN_BETA73.md](TESTRESULTATEN_BETA73.md). Volledige werking: [ACTUELE_WERKING.md](ACTUELE_WERKING.md).
