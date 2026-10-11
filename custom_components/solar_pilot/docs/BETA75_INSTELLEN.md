# SolarPilot 1.0.0-beta.75 — automatisch lokaal onderzoek

Beta.75 onderzoekt de bestaande meetbronnen verder en doet gerichte voorstellen op basis van het beschikbare bewijs. Onder Meetkwaliteit en Export → Analyse en advies verschijnt **Automatisch onderzoek** voor warmtepompmeting, Wallboxsessiebron, PV-voorspelling en toestelmetingen. De afzonderlijke SG-beoordeling benoemt de ingestelde regeling en wat nog ontbreekt om haar verloop te beoordelen.

## Update met behoud van gegevens

1. Maak een volledige privé HA-back-up met instellingen, eigen opslag, modellen, tickets, gewone en warmtepompgeschiedenis en userfiles. Bewaar gecontroleerde beta.74-code.
2. Geef vóór codevervanging een eigen SG-aanvraag vrij en controleer gemelde contactstand/lokale afloop. Onderbreek geen beschermde apparaatcyclus.
3. Update via HACS naar exact `1.0.0-beta.75` na publicatie. Lokaal vervang je uitsluitend `custom_components/solar_pilot`, met behoud van userfiles en HA-opslag.
4. Herstart HA volledig en herlaad browser/app volledig. Controleer backend- en kaartversie afzonderlijk.
5. Bekijk Automatisch onderzoek, bestaande meetdekking, SG-contact en geschiedenis. Er is geen nieuwe verplichte sensor, instellingenreset of algemene herbevestiging.

Behoud dezelfde entry, bindings, prioriteiten en geldige SG-/profiel-/split-/koelbevestigingen. Eerste installatie blijft HACS Integration en toevoegen onder Apparaten & diensten; nieuwe SG-sturing blijft uit tot de bestaande lokale voorwaarden bevestigd zijn.

## Wat automatisch wordt onderzocht

| Onderwerp | Beoordeling en vervolg |
| --- | --- |
| Warmtepompmeting | Controleert compleetheid, bronactualiteit en afkeur van de bestaande metingen. Herhaald afgekeurd vermogen vraagt gerichte controle; een negatieve waarde wordt niet omgekeerd of als nul gebruikt. |
| Wallboxsessiebron | Onderscheidt ontbrekende koppeling van oude, onbruikbare of tegenstrijdige gekoppelde rapporten. Actuele berichten tijdens daadwerkelijk laden leveren nieuw bewijs; stale-grenzen en autonome Wallboxbediening blijven behouden. |
| PV-voorspelling | Gebruikt beschikbare kwaliteitsinformatie en noemt tekort aan bruikbare vergelijking. Een foutmaat of één export bewijst geen schaduwoorzaak en rechtvaardigt geen vaste correctiefactor. Bestaand kalibratiebeleid blijft gelden. |
| Toestelmetingen | Maakt duidelijk waar een eigen actuele vermogensmeter ontbreekt of onbruikbaar is. Nominale watts blijven een schatting; het onderzoek koppelt geen sensor en verzint geen gemeten toestelenergie. |
| SG-beoordeling | Toont bestaande minimum-/wolkenbufferinstellingen en beperkingen van het beschikbare sessie-/reactiebewijs. Oude sessies bevestigen geen nieuwe timers; contact en elektrisch verbruik bewijzen geen causaal extra SG-effect. |

De statussen betekenen **Meer meetgegevens nodig**, **Controle nodig**, **Bron of functie niet ingesteld** of **Geen afwijking in deze metingen**. Daarbij staan bewijs, mogelijke oorzaken, voorstellen en een volgende actie. Een mogelijke oorzaak is een hypothese. Een status certificeert geen bedrading, fysieke meter, compressor of warmtepompreactie.

Het lokale onderzoek herbeoordeelt de vier brononderwerpen maximaal eenmaal per minuut. Verlopen bewijs of een gewijzigde relevante binding wordt ook tussen beoordelingen ongeldig. Alleen nieuwe werkelijke bruikbare bronrapporten leveren nieuwe meterwaarnemingen; een herhaalde schermweergave, regelronde of herstart is geen nieuw meetbewijs. Vier lokale onderwerprecords bevatten elk maximaal 32 rapportcursors; tellers verzadigen bij 1.000.000. De warmtepomp bewaart maximaal 64 negatieve diagnostische rapporten. Zulke verse oorspronkelijke afgekeurde rapporten tellen uitsluitend als diagnostisch bewijs, nooit als geldige regelwatts. Onbekende oude perioden worden niet aangevuld. Herstart bewaart tellingen en rapportcursors, maar herstelt geen actuele geldigheid of status. Een gewijzigde relevante bronbinding vraagt nieuw bewijs.

De controletijd staat bij de sectie. Een oude, herstelde of verlopen beoordeling is alleen eerdere evidence en bevestigt geen actuele bron. Een kleine negatieve meting kan aanleiding zijn voor een nulpuntcontrole: pas bij voldoende recente rapporten wordt dit als mogelijke verklaring genoemd. Dat bewijst geen offset of fysieke oorzaak en corrigeert de waarde niet.

De afzonderlijke SG-registratie observeert de bestaande regelronde met één passend tijdstip voor aanvraag, contact, P1 en PV. Maximaal twaalf afgeronde sessierecords bewaren versie, effectieve policy, vastgelegde aanvraagduur, dekking en stopinformatie. Een al actieve aanvraag bij begin van registratie heeft geen bewezen start. Herstart, een gat boven dertig seconden, verlopen bewijs of gewijzigde policy geeft geen complete vergelijkbare sessie. Opgeslagen records herstellen geen actieve aanvraag. Een passende sessie ondersteunt alleen de vergelijking van waargenomen timing; geen compressorlooptijd of causale extra SG-opname.

Lokaal onderzoek en de aparte warmtepompgeschiedenis werken ook bij Pauze en uitgeschakelde gedetailleerde analyseregistratie. Bestaande leer-/aanpassingskeuzes blijven gelden. Rapporttellingen zijn geen bewezen statistisch onafhankelijke meetproeven.

De export neemt de beschikbare onderzoeksstatus, bewijsgrenzen en voorstellen mee. Download en delen blijven bewuste beheerderacties. Er is geen automatische upload, ChatGPT-verbinding, softwareontwikkeling, meterreparatie of nieuwe sensorkoppeling in de integratie.

Een geïmporteerd rapport blijft een advies. Vertrouwde softwarevoorstellen houden de bestaande exacte release-/inhoudsstatus; overige adviezen tonen hun categorie. Een categorieaanduiding bevestigt geen uitgevoerde instelling of opgeloste controle. De actuele lokale onderzoeksstatus staat apart van de inhoud van een oud adviesrapport.

## Regeling en gegevens blijven behouden

Standaard geldt actueel gemeten netafname **strikt boven 600 W gedurende vijf continue minuten**, tegelijk met de **minimale SG-aanvraagduur van twintig minuten**. Bij 600 W of lager vervalt de tekorttimer. Een tekort vanaf minuut 18 kan bij aanhouden pas in minuut 23 gewone vrijgave geven; een eerder voltooide tekorttijd kan bij het minimum al gelden. Zonder tekort is twintig minuten geen verplichte stop. De aparte zonne-resetgrens blijft standaard 300 W.

De runtime-normalisatie uit beta.73 blijft hetzelfde: zonder nieuwe importoptie wordt de oude effectieve standaardcombinatie 300 W/60 s 600 W/300 s; oude afwijkingen en expliciete nieuwe waarden blijven behouden, zonder automatische optieswrite. Alle minimum-/maximumwaarden blijven staan.

Korte lokale toestemming blijft standaard 300 s, veilig vernieuwd iedere 60 s tijdens geldige minimum- en wolkenwachttijd. Geen UIT/AAN-cyclus of lokale twintigminutentimer. Bronverlies, harde net-/fase-/kwartier-/batterij-/koel-/Wallbox-/prioriteitsgrenzen, handmatige overname, Pauze/disable, geverifieerde native voltooiing/bevestigd geen extra opname, fouten en hardmaximum behouden vroege vrijgave. Lage watts of onbekende reactie zijn geen native beëindigingsbewijs. Renewal/reload geven geen nieuw aanvraagrecht.

Panasonic blijft eigenaar van programma's, percentages, koelwaarden, comfort en beveiligingen. Eén bestaande toegewezen SG-uitgang blijft de enige warmtepompactuator. Het minimum betreft de SG-aanvraag, geen gegarandeerde compressorlooptijd of levensduur. Het onderzoek verandert geen instelling, meterteken, binding, modeltoestemming, bron-/elektrische grens of fysiek regelrecht.

Alle overige apparaten, modellen, tickets en geschiedenis blijven behouden. Warmtepompgeschiedenis blijft read-only met bron-READ-controles en aparte opslag; onbekende perioden worden niet ingevuld. Private exports, bronidentiteiten en back-ups horen niet in publieke bron of assets.

## Rollback naar beta.74

Geef de eigen SG-aanvraag vrij, controleer contact/lokale afloop, stop beta.75 en herstel gecontroleerde beta.74-code. Behoud entry, opslag en userfiles. De SG-regeling blijft dezelfde; Automatisch onderzoek vervalt. Code terugzetten corrigeert geen meter, bedrading of fysieke toestand.

Exact herstel vraagt code én de passende volledige privéback-up; bewaar gewenste nieuwe historie eerst. Verwijder de entry niet en laat nooit twee runtimes tegelijk werken. Voor de oude directe beta.61-regeling blijft de volledige pre-beta.62-back-up nodig. Software-/publicatiebewijs: [TESTRESULTATEN_BETA75.md](TESTRESULTATEN_BETA75.md). Volledige werking: [ACTUELE_WERKING.md](ACTUELE_WERKING.md).
