# SolarPilot 1.0.0-beta.82 — werking, SG-contact en boilerwaarden

Beta.82 maakt de bedrijfsweergave en warmtepompgeschiedenis duidelijker. Verwarmen, Boiler opwarmen, Koelen en Ontdooien gebruiken hun eigen actuele bronbewijs. Elektrische ondersteuning staat daarnaast en vervangt die taak niet. Direct onder de taakbalk staat het gemelde SG-contact op dezelfde tijdas. Actuele en historische boilerwaarden behouden hun oorspronkelijke tijden en onbekende perioden.

Deze uitbreiding leest bestaande bronnen. Zij schrijft geen Panasonic-doel of programma, verandert geen sensorkoppeling en geeft geen nieuw leer- of SG-recht. Een bruikbare afzonderlijke voedingsmeting kan een presentatie ondersteunen zonder een onvolledig totaal compleet te maken. De behouden SG-policy, elektrische grenzen, instellingen en oude historie blijven staan.

## Upgrade

1. Maak een volledige privé Home Assistant-back-up met instellingen, eigen opslag, PV-factoren, modellen, APP-aanvragen, historie en userfiles. Bewaar gecontroleerde beta.81-code.
2. Geef vóór codevervanging een eigen SG-aanvraag veilig vrij en controleer contact en lokale afloop. Onderbreek geen beschermde apparaatcyclus.
3. Update via HACS naar exact `1.0.0-beta.82` nadat releasegates en publicatie geslaagd zijn. Lokaal vervang je uitsluitend `custom_components/solar_pilot`, met behoud van userfiles en HA-opslag.
4. Herstart Home Assistant volledig en herlaad app/browser volledig. Controleer backend- en kaartversie afzonderlijk onder **Instellingen & controle**.
5. Bekijk de warmtepompkaart en **Warmtepomp → Geschiedenis**. Controleer de primaire taak, afzonderlijke elektrische ondersteuning, SG-contactbalk en de huidige/ingestelde boilerwaarde. Een onbekende taak kan alleen verdwijnen als de daarvoor noodzakelijke bronnen daadwerkelijk actueel en passend zijn.

Verwijder of hermaak de integratie niet. Geldige instellingen, bronbindings, prioriteiten, lokale Panasonic SG-percentages/koelwaarde, APP-deadlines en verbruikte beladingen blijven staan. Geen extra package, sensor, add-on of nieuwe hardware is verplicht. Een software-update maakt geen nieuwe AEG-START beschikbaar.

## Betekenis van de nieuwe weergave

| Weergave | Bron en beperking |
|---|---|
| Verwarmen / Koelen / Boiler opwarmen | Een verse passende werkelijke Panasonic-actie is direct taakbewijs. Een geverifieerde verse ontdooimelding heeft voorrang. |
| Boiler opwarmen · Afgeleid | Verse exact herkende tankroute plus verse actieve toegewezen hoofd- of ondersteuningsvoeding. Watts of een gekozen tankprogramma alleen zijn onvoldoende. |
| Verwarmen / Koelen · Afgeleid | Verse eenduidige ruimtestand plus actieve hoofdvoeding en afzonderlijke verse expliciete tankrust. Zo krijgt gekozen HEAT geen voorrang boven mogelijk tankbedrijf. |
| Elektrische ondersteuning | Afzonderlijk gemeten activiteit van de toegewezen ondersteuningsvoeding. Zij mag tegelijk met de primaire taak zichtbaar zijn; de perioden worden niet bij elkaar opgeteld als totale draaitijd. |
| Actief · taak onbekend | Er is actuele activiteit, maar geen eenduidig bewijs voor een warmte-/koelfunctie. Oude, ontbrekende of tegenstrijdige gegevens worden niet gegokt. |
| SG-contactbalk | De werkelijk gemelde expliciet bevestigde contactstand: AAN, UIT of onbekend. Aanvraag, ontvangen SG en warmtepompverbruik zijn afzonderlijk en vullen geen ontbrekend contactbewijs in. |
| Boiler nu / Ingesteld doel | Verse huidige temperatuur en het gewone gemelde Panasonic-doel. Het gewone doel is geen bewezen effectief SG- of hygiënedoel. Ontbrekende of oude waarden blijven afzonderlijk onbekend. |
| Historische boilerwaarden | Brongebonden punten van de gekozen lokale dag. Geen lijn over meetgaten, geen huidig doel terugplaatsen op een vorige dag en geen ontbrekende geschiedenis aanvullen. |

De nieuwe classificatie is uitsluitend presentatie en historie. Leren en SG-veiligheidsbeoordeling houden hun bestaande conservatieve bronvoorwaarden. Een ontbrekende tweede voeding blijft een onbekend totaal; er komt geen gefingeerde totale energie, compressorlooptijd, sterilisatiebevestiging of extra SG-verbruik bij.

## Behouden regeling

De standaard SG-importbuffer blijft **600 W gedurende vijf continue minuten**, met **twintig minuten minimum SG-aanvraag**. Beide zachte tijden moeten verstreken zijn; de tekorttijd reset op of onder de importgrens. Harde bron-, net-, fase-, kwartier-, batterij-, lease-, handmatige en voorrangsvoorwaarden kunnen eerder vrijgeven. Dit is geen minimum compressorlooptijd. De lokale lease blijft kort, standaard 300 s met vernieuwing om de 60 s.

Panasonic blijft read-only behalve het expliciet toegewezen bestaande SG-contact. Wallbox blijft read-only. AEG behoudt maximaal één native START per geldige nieuwe belading en de zonne-onafhankelijke deadline binnen alle echte apparaat- en elektrische grenzen. Onderzoek, geschiedenis en temperatuurweergave verlenen geen actuatorrecht of nieuwe modeltoestemming.

## Rollback naar beta.81

Geef de eigen SG-aanvraag vrij, controleer contact/lokale afloop, stop beta.82 en herstel gecontroleerde beta.81-code met behoud van entry, actuele opslag en userfiles. Beta.81 behoudt de SG-onderzoeksinnamefix en eerdere bron-, forecast-, native- en elektriciteitsgegevens, maar mist de nieuwe taakclassificatie, afzonderlijke ondersteuningslijn, brongebonden contactbalk en temperatuurweergave.

De nieuwe velden en lanes zijn aanvullend. Beta.81 kan ondersteunde eerdere data lezen, maar kent deze nieuwe gegevens niet; een volgende opslagwrite van de oudere code kan aanvullende velden weglaten. Bewaar daarom gewenste nieuwe historie en een volledige privéback-up vóór rollback. Exact herstel vraagt de passende back-up, niet uitsluitend een oudere ZIP. Oude taakperioden worden bij upgrade niet opnieuw geïnterpreteerd; rollback verandert evenmin eerder opgeslagen feiten.

Herstel geen oude onverbruikte APP-aanvraag nadat dezelfde belading gestart of afgerond is. Laat nooit twee runtimes tegelijk werken en verwijder de entry niet.

Volledige werking: [ACTUELE_WERKING.md](ACTUELE_WERKING.md). Brongebonden tests en pakket/publicatiebewijs: [TESTRESULTATEN_BETA82.md](TESTRESULTATEN_BETA82.md). Softwareproeven bewijzen geen fysieke meterreparatie, compressorbedrijf, levensduurwinst, COP of causale SG-besparing.
