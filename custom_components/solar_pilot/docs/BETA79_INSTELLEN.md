# SolarPilot 1.0.0-beta.79 — upgrade na brede code-audit

Beta.79 herstelt gereproduceerde fouten in uitvoering, planner, meten/leren, opslag, configuratie, leesrechten en frontend. De bestaande installatie houdt dezelfde entry, bronbindings, apparaatrollen, prioriteiten, modellen, historie en geldige toestemmingen. Geen extra add-on, solver, package, handmatige dependency of tweede regelaar.

De concrete auditdekking en bevindingen staan in [AUDIT_BETA79.md](AUDIT_BETA79.md). Uitgevoerde checks, exacte bron en publicatiestatus staan in [TESTRESULTATEN_BETA79.md](TESTRESULTATEN_BETA79.md). Bron in een branch of een geslaagde eerdere release bewijst nog geen beta.79-publicatie. De audit is geen garantie dat iedere mogelijke fout, verborgen externe writer of hardwareoorzaak is uitgesloten.

## Update met behoud van gegevens

1. Maak een volledige privé HA-back-up met instellingen, eigen opslag, PV-factoren, modellen, tickets, gewone en warmtepompgeschiedenis, adviesrapporten en userfiles. Bewaar gecontroleerde beta.78-code.
2. Geef vóór codevervanging een eigen SG-aanvraag vrij en controleer contact/lokale afloop. Onderbreek geen beschermde apparaatcyclus.
3. Update via HACS naar exact `1.0.0-beta.79` nadat releasegates en publicatie zijn geslaagd. Lokaal vervang je uitsluitend `custom_components/solar_pilot`, met behoud van userfiles en HA-opslag.
4. Herstart HA volledig en herlaad browser/app volledig. Controleer backend- en geladen kaartversie afzonderlijk onder **Instellingen & controle**.
5. Controleer de actuele bronkwaliteit en beslisredenen, Planning, PV-diagnose, Meetkwaliteit, kosten en beide geschiedenissen. Een gewone update maakt geen nieuwe AEG-belading of gewijzigde deadline.
6. Bij een onbekende of beschadigde oude opslag: behoud de oorspronkelijke gegevens en de privéback-up. Wis geen store, model of ticket om een waarschuwing weg te krijgen. Een concrete laadfout kan nieuwe duurzame registratie of adviesimport tegenhouden; de oorspronkelijke opslag blijft beschermd.

Verwijder of hermaak de entry niet. Geldige SG-/profiel-/split-/koelbevestigingen blijven behouden. Geen nieuwe verplichte sensor, configuratiereset of algemene herbevestiging alleen door deze codeupdate.

## Veranderingen die je kunt merken

| Situatie | Gedrag in beta.79 |
| --- | --- |
| Meting, deur, toestemming of vermogen verandert tijdens opdrachtvoorbereiding | Actuele voorwaarden worden vóór de fysieke verhoging opnieuw gecontroleerd. Een aantoonbaar niet-verzonden aanvraag kan worden ingetrokken; een onzekere werkelijk verzonden opdracht wordt niet blind herhaald. |
| SG-contact of lokale aflooptimer handmatig gewijzigd | De handmatige wijziging houdt voorrang op een oudere SolarPilot-aanvraag. Een oude AAN-aanvraag wordt bij herstart niet opnieuw uitgevoerd. |
| SG-bron ontbreekt bij herstart en wordt later weer bruikbaar | De oude aanvraag kan alsnog veilig worden beoordeeld voor één passende vrijgave; terugkerende communicatie geeft geen nieuw AAN-recht. |
| Wallbox-monitoring uit of gewone script-/batterijroute gekozen | De lader blijft read-only. Uitgeschakelde monitoring geeft geen andere SolarPilot-route schrijfrecht op de Wallbox. |
| Plannerslot raakt een venster- of deadlinegrens | Het gehele slot moet passen; alleen de begintijd binnen het venster is onvoldoende. Lopende beschermde cycli blijven vast. |
| Prijsoptimalisatie bewust uit, lagere toestellen concurreren om zon | De prijsoptie blijft gerespecteerd. Reeds toegewezen zonnestroom wordt niet nogmaals aan een lager toestel toegekend. De zachte piekpenalty volgt de slotduur. |
| Meetgaten tijdens een nieuwe cyclus of meerdere veranderingen bij faseherkenning | Onvoldoende gedekte cycli worden geen compleet geleerd profiel. Ontbrekende of bijkomende meters vormen geen bewezen geïsoleerde fasegebeurtenis. |
| Ongeldig getal, boolean als vermogen of beschadigd modelveld | Ongeldige waarden worden geen bruikbare meting. Geldige ondersteunde gegevens blijven behouden; onbekende versiegebonden kosten-, PV- en besparingsopslag blijft privé bewaard en wordt niet tot een leeg actueel model gemaakt. |
| Geregelde energie kan niet door gemeten zon, net of batterij worden verklaard | Het restant wordt apart als niet toegeschreven geboekt, zonder verzonnen zonne-energie of besparing. |
| Optionele bron wordt in een formulier gewist | De werkelijk gekozen nieuwe waarden worden vóór het opslaan gevalideerd. Niet getoonde plannerkeuzes, waaronder uitgeschakelde gezamenlijke optimalisatie, blijven behouden. |
| API-vraag of browserantwoord komt na sluiten/herladen/nieuwe vraag terug | De oude actie of weergave kan de nieuwe context niet meer gebruiken of overschrijven. Onbekende frontendgetallen worden niet als nul voorgesteld. |
| Publieke HA-diagnostiek wordt gedownload | Generieke samenvattingen en tellingen blijven zichtbaar; geneste apparaatnamen, bron-ID’s en monitoridentiteiten worden niet opgenomen. |
| Historie bestaat na een bronwijziging | Andere gebruikers hebben leesrechten op de huidige én geregistreerde historische bronnen nodig. Oude historie zonder betrouwbare oorspronkelijke bronherkomst blijft behouden en voor beheerders toegankelijk. |
| Bestaande historie-/analyse-/adviesopslag kan niet veilig worden geladen | De oorspronkelijke opslag wordt niet stil overschreven. Tijdelijke nieuwe waarnemingen vormen geen bewijs van duurzaam opgeslagen historie. |

## Afwasdeadline blijft gelden

Een geldige nieuwe APP-overgang geeft één belading vrij. De eenmaal vastgelegde deadline staat netstroom toe, ook zonder zonneoverschot en bij oudere zonne-/netvoorkeursvlaggen. Geplande dag, deadline en bronbindings blijven bij update/reload vast. De bestaande deadlinegrace blijft standaard 120 minuten met behoud van expliciete waarden.

Net-/fase-/kwartier-/vermogensgrenzen, betrouwbare bronnen, deur-/apparaatvoorwaarden, Pauze/Alleen bekijken, pending/settling en maximaal één native START blijven vereist. De deadline vergroot geen elektrische capaciteit. Een nog niet verzonden START kan na herstel van een blokkering binnen de bewaarde termijn opnieuw worden beoordeeld. Een onzekere verzonden START blijft beschermd en wordt niet herhaald.

Een passende nieuwe native Running-bevestiging voor dezelfde aanvraag verwijdert gericht de achterhaalde deadlinewaarschuwing. De verbruikte aanvraag en oorspronkelijke deadline blijven bij de lopende beurt zichtbaar. Een meldingstransportfout mag de regelcyclus niet laten crashen; zij verandert geen apparaatbevestiging.

## Behouden regeling en opslag

Panasonic blijft eigenaar van comfort, warm water, verwarmen/koelen, compressor, kleppen, pompen, ondersteuning, percentages, koelwaarden en sterilisatie. Het toegewezen SG-contact is de enige warmtepompactuator. Wallbox blijft autonoom en read-only. AEG behoudt maximaal één native START per nieuwe geldige APP-belading, zonder PAUSE/RESUME/STOPRESET, programmakeuze, timerwrite of stekkeronderbreking.

SG behoudt netafname strikt boven 600 W gedurende vijf continue minuten, minimum twintig minuten, korte leases 300 s/60 s en het bestaande maximum. Expliciete geldige gebruikerswaarden en alle harde guards, handmatige overname, Pauze/disable, fouten en geverifieerde native voltooiing blijven leidend. De globale softwarematige netafnamegrens, fasegrenzen en PV-/kalibratietoestemming veranderen niet.

Ondersteunde geldige modellen en meet-/historieretentie blijven behouden. Nieuwe extra herkomstvelden blijven lokaal en geven geen actuatorrecht. Bij onbekende versiegebonden kosten-/PV-/besparingsopslag blijft het oorspronkelijke snapshot opgeslagen zonder de onbekende inhoud als geldig leerbewijs te gebruiken; nieuwe observaties kunnen dan slechts tijdelijk in geheugen beschikbaar zijn. Exact herstel van alle gegevens vraagt de passende volledige privéback-up. Bestaande onbekende perioden worden niet gevuld met veronderstelde energie of activiteit.

Gezamenlijke toestelplanning blijft een begrensde adviseringsroute zonder globale optimaliteits- of besparingsgarantie. Het afzonderlijke chronologische batterijadvies houdt SoC, laad-/ontlaadgrenzen en de bestaande ingestelde roundtrip-efficiëntie, standaard 80% (20% verlies). De actieve batterijbediening houdt haar eigen expliciete toestemming en bevestiging. Analyse-/adviesupload blijft data en past geen instelling, bronbinding, code of apparaatopdracht toe.

## Rollback naar beta.78

Geef de eigen SG-aanvraag vrij, controleer contact/lokale afloop, stop beta.79 en herstel gecontroleerde beta.78-code. Behoud entry, actuele opslag en userfiles, inclusief verbruikte of afgeronde aanvragen. Beta.78 behoudt de eerdere AEG-deadlinecorrectie en bestaande dataformaten, maar mist de auditcorrecties. Code terugzetten kan deze beschermingen dus weer verliezen; het mag geen START opnieuw vrijgeven.

Exact herstel vraagt code én de passende volledige privéback-up; bewaar gewenste nieuwe historie eerst. Herstel geen oude onverbruikte ticketback-up bij een inmiddels gestart of afgerond programma. Een oudere versie kan onbekende opslag of nieuwe herkomstmetadata anders verwerken: bewaar de originele back-up voordat je teruggaat. Verwijder de entry niet en laat nooit twee runtimes tegelijk werken. Voor de oude directe beta.61-regeling blijft de volledige pre-beta.62-back-up nodig.

Volledige actuele werking: [ACTUELE_WERKING.md](ACTUELE_WERKING.md). Technische overdracht: [OVERDRACHT.md](https://github.com/Stevenva007/solarpilot-home-assistant/blob/v1.0.0-beta.79/OVERDRACHT.md). Uitgevoerde software- en releasechecks bewijzen geen fysieke AEG-/Shelly-/Panasonicacceptatie, schaduwoorzaak, afwezige externe writer of werkelijke besparing.
