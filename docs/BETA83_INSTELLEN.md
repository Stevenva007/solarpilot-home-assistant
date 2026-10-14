# SolarPilot 1.0.0-beta.83 — bronsemantiek, berekend SG-doel en consistente diagnose

Beta.83 verbetert de uitsluitend uitlezende warmtepompweergave op basis van gecontroleerde publieke Aquarea-broncode. De bekende library kan een globale OFF uit een Eco/Comfort-veld afleiden terwijl afzonderlijke zones of de tank ingeschakeld zijn. SolarPilot behandelt deze specifieke bronsemantiek afzonderlijk en gebruikt actuele richting, pomp-, zone- en tankgegevens voor presentatie. Een onbekende bronvorm krijgt geen automatische uitzondering; leer- en SG-veiligheidsvoorwaarden blijven behouden.

De boilerweergave onderscheidt gemeten temperatuur, het gewone ingestelde doel en een **berekend SG-doel** uit een lokaal bevestigd Panasonic-tapwaterpercentage. De diagnose houdt een eerdere beoordeling en actuele bronwaarneming op hun eigen tijdstip. Vooruit vastgelegde PV-vergelijkingen onderscheiden daglicht en nacht; ontbrekende of ongeldige uitgiftetijden blijven onbekend.

## Upgrade

1. Maak een volledige privé Home Assistant-back-up met instellingen, eigen opslag, PV-factoren, modellen, APP-aanvragen, historie en userfiles. Bewaar gecontroleerde beta.82-code.
2. Geef vóór codevervanging een eigen SG-aanvraag veilig vrij en controleer contact en lokale afloop. Onderbreek geen beschermde apparaatcyclus.
3. Update via HACS naar exact `1.0.0-beta.83` nadat releasegates en publicatie geslaagd zijn. Lokaal vervang je uitsluitend `custom_components/solar_pilot`, met behoud van userfiles en HA-opslag.
4. Herstart Home Assistant volledig en herlaad app/browser volledig. Controleer backend- en kaartversie afzonderlijk onder **Instellingen & controle**.
5. Als je een berekend tapwater-SG-doel wilt tonen: controleer het tapwaterpercentage van de gebruikte SG-capaciteit rechtstreeks op Panasonic. Kies onder Warmtepomp — uitleesbronnen de passende bestaande geregistreerde native tankbron voor deze afzonderlijke vergelijking, neem precies dat percentage over en bevestig de overeenkomst. De bronselectie is uitsluitend voor weergave en verandert de bestaande regelbron niet. Deze handeling schrijft geen Panasonic-instelling en verandert geen SG-bedieningsrecht.
6. Controleer warmtepomptaak, afzonderlijke ondersteuning, gemeld contact en boilerwaarden. Bekijk daarnaast **Meetkwaliteit → Automatisch onderzoek** en de gescheiden vooruit-PV-scores. Een lokaal doel of provider wordt niet uit een screenshot of softwareversie gegokt.

Verwijder of hermaak de integratie niet. Geldige instellingen, bronbindings, prioriteiten, lokale Panasonic SG-percentages/koelwaarde, APP-deadlines en verbruikte beladingen blijven staan. Het nieuwe percentage begint als onbevestigde weergavewaarde; een update geeft het niet automatisch geldige lokale herkomst. Een software-update maakt geen nieuwe AEG-START beschikbaar.

## Taak- en doelweergave

| Weergave | Betekenis |
|---|---|
| Verwarmen / Koelen / Boiler opwarmen | Passende verse acties of expliciet herkenbare afleiding uit gecontroleerde bronvelden. Richting alleen is geen actuele opwarming; gekozen HEAT/COOL alleen is geen werkelijke taak. |
| Ontdooien | Een passende geverifieerde actuele ontdooimelding houdt voorrang op gewone taken. |
| Elektrische ondersteuning | Apart gemeten ondersteuningsactiviteit naast de primaire taak. Zij vervangt de taak niet en maakt een ontbrekend totaal niet compleet. |
| Boilertemperatuur / Ingesteld boilerdoel | Actuele temperatuur en het gewone gemelde Panasonic-doel, ieder met eigen brontijd en actualiteit. |
| SG-doel · berekend | Gewoon vers doel × lokaal bevestigd tapwaterpercentage / 100, wanneer het contact daadwerkelijk actueel bevestigd AAN is. Dit is een berekening, geen ontvangen SG- of toegepaste-doelterugmelding. |
| SG-doel bij AAN · berekend | Dezelfde geldige berekening als vergelijking wanneer het gemelde contact UIT is. Zij beweert niet dat Panasonic dit doel nu toepast. |
| Onbekend contact of doelbron | Geen compact actueel SG-doel. Een eventuele voorwaardelijke vergelijking staat apart in uitgebreide diagnose; ontbrekende gegevens worden niet ingevuld. |
| Historisch SG-doel | Alleen toen vastgelegde gewone doelbron, lokaal bevestigd percentage en daadwerkelijk gemeld contact. Het huidige percentage wordt niet op eerdere gegevens toegepast. |

Het berekende tapwaterdoel vergt geen afzonderlijke native doelterugmelding om de formule te tonen. Die ontbrekende terugmelding begrenst wel wat zij bewijst: effectief door Panasonic toegepast doel, SG-ontvangst, native voltooiing en sterilisatieresultaat zijn afzonderlijke feiten. SolarPilot begrenst de berekening niet stil naar het gewone native min/max-doel en schrijft geen temperatuur. Ongeldige of niet-actuele invoer geeft geen berekende waarde.

De herkenningscorrectie is uitsluitend presentatie. Onbekende providers, oude polls, tegenstrijdige echte acties en optimistisch gewijzigde lokale velden krijgen geen actueel betrouwbaar bewijs. Panasonic blijft eigenaar van comfort, programma, compressor, pompen, kleppen, ondersteuning en hygiëne.

## Behouden regeling en onderzoek

De standaard SG-importbuffer blijft **600 W gedurende vijf continue minuten**, met **twintig minuten minimum SG-aanvraag**. Beide zachte tijden moeten verstreken zijn; de tekorttijd reset op of onder de importgrens. Harde bron-, net-, fase-, kwartier-, batterij-, lease-, handmatige en voorrangsvoorwaarden kunnen eerder vrijgeven. Dit is geen minimum compressorlooptijd. De lokale lease blijft kort, standaard 300 s met vernieuwing om de 60 s.

De eerdere onderzoeksuitleg en nieuwe bronwaarneming krijgen afzonderlijke herkenbare tijdstippen. Een gewoon nieuw meterbericht is geen wijziging van bronidentiteit of beleidscontext. PV-daglichtscores worden niet beter voorgesteld doordat veel nachtelijke nulpunten aan dezelfde populatie worden toegevoegd. Daglicht/nacht vereist passend oorspronkelijk zonnestandbewijs; zonder dat bewijs blijven vergelijkingen apart onbekend of overige. Unieke doelen en UTC-brondagen zijn geen bewezen onafhankelijke statistische proeven. Oudere ontbrekende forecastuitgifte blijft onbekend; er komt geen 1970-datum uit een nulsentinel en geen nieuwe modeltoestemming uit diagnosemetadata.

Panasonic blijft read-only behalve het expliciet toegewezen bestaande SG-contact. Wallbox blijft read-only. AEG behoudt maximaal één native START per geldige nieuwe belading en de zonne-onafhankelijke deadline binnen alle echte apparaat- en elektrische grenzen. Geen nieuwe verplichte sensor, add-on of handmatig te installeren dependency.

## Upstream-opvolging

Het openbare [UPSTREAM_BRONNEN.md](UPSTREAM_BRONNEN.md) bewaart gecontroleerde versies, vaste commits, PR-status en relevante contracten. De afzonderlijke geautoriseerde wekelijkse ChatGPT-taak kan relevante geteste SolarPilot-correcties volgens de bestaande releaseprocedure publiceren. Zij wijzigt geen geïnstalleerde Home Assistant-provider, sensorkoppeling of apparaat. De integratie zelf ontwikkelt geen nieuwe software op de achtergrond.

## Rollback naar beta.82

Geef de eigen SG-aanvraag vrij, controleer contact/lokale afloop, stop beta.83 en herstel gecontroleerde beta.82-code met behoud van entry, actuele opslag en userfiles. Beta.82 behoudt de taak-/ondersteuningsweergave, SG-contactbalk en gewone temperatuurhistorie, maar mist de specifieke bronsemantiekcorrectie, berekende SG-doelvergelijking en nieuwe diagnose-/PV-presentatie.

Nieuwe doel- en diagnosevelden zijn aanvullend. Oudere code kent ze niet; een volgende opslagwrite kan aanvullende velden weglaten. Bewaar daarom gewenste nieuwe historie en een volledige privéback-up vóór rollback. Exact herstel vraagt de passende back-up, niet uitsluitend een oudere ZIP. Oude taakperioden worden bij upgrade niet opnieuw geïnterpreteerd.

Herstel geen oude onverbruikte APP-aanvraag nadat dezelfde belading gestart of afgerond is. Laat nooit twee runtimes tegelijk werken en verwijder de entry niet.

Volledige werking: [ACTUELE_WERKING.md](ACTUELE_WERKING.md). Brongebonden tests en pakket/publicatiebewijs: [TESTRESULTATEN_BETA83.md](TESTRESULTATEN_BETA83.md). Softwareproeven bewijzen geen fysieke meterreparatie, compressorlooptijd, levensduurwinst, COP of causale SG-besparing.
