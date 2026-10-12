# SolarPilot 1.0.0-beta.77 — PV-kalibratie per zonnestand en seizoen

Beta.77 verbetert het leren en uitleggen van terugkerende snelle PV-overgangen, zoals een namiddagdaling of herstel. De bestaande zonnestandberekening gebruikt de lokale Home Assistant-locatie. Factoren blijven gescheiden per tweemaandsseizoen, met kwartier als tijdvakfallback. Er wordt geen vaste correctie om 16:00 toegevoegd en een afwijking wordt niet als bewezen boomschaduw benoemd.

## Update met behoud van gegevens

1. Maak een volledige privé HA-back-up met instellingen, eigen opslag, PV-factoren, modellen, tickets, gewone en warmtepompgeschiedenis en userfiles. Bewaar gecontroleerde beta.76-code.
2. Geef vóór codevervanging een eigen SG-aanvraag vrij en controleer contact/lokale afloop. Onderbreek geen beschermde apparaatcyclus.
3. Update via HACS naar exact `1.0.0-beta.77` na geslaagde releasegates en publicatie. Lokaal vervang je uitsluitend `custom_components/solar_pilot`, met behoud van userfiles en HA-opslag.
4. Herstart HA volledig en herlaad browser/app volledig. Controleer backend- en kaartversie afzonderlijk.
5. Bekijk PV-diagnose, relevante namiddagkwartieren, Planning en bestaande meetkwaliteit/geschiedenis.

Behoud dezelfde entry, bindings, prioriteiten en geldige SG-/profiel-/split-/koelbevestigingen. Geen extra installatie, nieuwe verplichte sensor, reset of algemene herbevestiging. Exacte actuele release-/pakketstatus staat in [TESTRESULTATEN_BETA77.md](TESTRESULTATEN_BETA77.md); bron in een branch bewijst nog geen publicatie.

## Wat er leert en wat er wacht

| Onderdeel | Betekenis |
| --- | --- |
| Zonnestand en seizoen | Bestaande ligging, zonneazimut en zonnehoogte bepalen het relevante tweemaandse leervak. Een kwartier-/seizoensvak blijft fallback; winter en zomer worden niet als hetzelfde profiel behandeld. |
| Overgangskandidaat | Alleen een volledig gedekt kwartier met verse onafhankelijke geldige PV-/forecastmetingen zonder clipping kan een snelle overgang vastleggen. Afgekeurde of onvolledige kwartieren worden niet bruikbaar gemaakt door hun rustige staart te selecteren. |
| Herhaling | De ingestelde minimumdagen blijven gelden, normaal minstens vijf verschillende vergelijkbare dagen, met voldoende zekerheid. Richting, overgangsfase en de stabiele niveaus voor/na de overgang moeten voldoende overeenkomen. Eén screenshot of dag is onvoldoende. |
| Factorwijziging | Alleen reeds ingeschakelde automatische kalibratie mag de empirische factor aanpassen. Het normale preset blijft maximaal ±0,05 per leerdag; bestaande presets, grenzen en factorondergrens 0,35 blijven behouden. |
| Onzeker bewijs | Onvoldoende of wisselende vergelijkbare dagen houden de bestaande uitleg en begrensde factorroute. Er volgt geen vaste 16:00-factor of bewijsclaim over een boom, wolk of exacte fysieke oorzaak. |

Een herhaalbare overgang is empirisch bewijs voor een correctie, geen garantie dat bewolking verdwenen is uit de meetreeks. Nieuwe kandidaten vragen nieuw vergelijkbaar dagbewijs na de update. Oude bins, factoren en historie blijven bewaard; ontbrekend bewijs uit oude historie wordt niet achteraf ingevuld.

## Uitleg in PV-diagnose en planner

PV-diagnose toont de periode **15:00–18:00** per kwartier voor de lokale datum, met ruwe en gecorrigeerde voorspelling, factor, relevante vergelijkbare dagen en de reden voor toepassing of behoud. Het factoroverzicht (`factor_details`) onderscheidt het passende zonnestand-/seizoensvak van een fallback en maakt de lokale bewijsgrens zichtbaar.

Het globale aantal leerdagen en het aantal dagen voor één relevant kwartier betekenen iets verschillends: tien dagen in het totale model bewijzen niet dat het huidige namiddagvak vijf vergelijkbare dagen heeft. Een ontbrekende geldige forecast blijft onbekend; een factor kan ontbrekende brondekking niet vervangen.

De bestaande planner gebruikt de volledige gecorrigeerde vermogenscurve voor zijn ingestelde horizon. Hij ontvangt geen afzonderlijke vaste namiddagregel. Alle actuele elektrische, bron-, toestel- en commandogrenzen blijven leidend; een voorspelde opbrengst is geen beschikbaar realtime vermogen.

## Behouden instellingen, regeling en gegevens

Uitgeschakelde PV-/kalibratiefuncties en expliciete gebruikerskeuzes blijven gerespecteerd. Deze update reset geen model en activeert geen uitgeschakelde functie. Nieuwe kandidaat-evidence staat optioneel in `edge_evidence` binnen de bestaande versie-1-opslag met gevalideerde restore. Er zijn maximaal 1600 vakken met elk maximaal 45 verschillende dagen binnen 120 dagen; één kandidaat per dag/vak telt. Oudere gegevens blijven leesbaar; er is geen terugwerkende conversie van oude historie naar nieuwe kandidaat-evidence.

De gezamenlijke dependencyvrije toestelplanner uit beta.76, de geïsoleerde executorroute, chronologisch batterijadvies, onderzoek, exports, adviesrapporten, tickets, leerdata en geschiedenis blijven behouden. Batterijadvies gebruikt de bestaande geconfigureerde roundtrip-efficiëntie uit de batterijanalyse, standaard 80% (20% verlies). Geen extra EMHASS-installatie, add-on, solver, dienst of cloud-AI.

Panasonic blijft eigenaar van comfort, warm water, compressor, kleppen, pompen, ondersteuning, percentages, koelwaarden en sterilisatie. Het bestaande toegewezen SG-contact blijft de enige warmtepompactuator. Wallbox blijft autonoom en read-only; AEG behoudt één native START per nieuwe geldige APP-belading.

SG blijft standaard netafname strikt boven **600 W gedurende vijf continue minuten**, met **minimum twintig minuten** en korte leases 300 s/60 s. Alle harde guards, handmatige overname, Pauze/disable, fouten, geverifieerde native voltooiing en hardmaximum behouden vroege vrijgave. Bestaande PV-/SG-instellingen, globale netafnamegrens, fase- en overige vermogensgrenzen worden niet aangepast. De update voegt geen actuator, Panasonic-regelaar of nieuw bedieningsrecht toe. Een adviesupload blijft data en past geen instelling of code toe.

## Rollback naar beta.76

Geef de eigen SG-aanvraag vrij, controleer contact/lokale afloop, stop beta.77 en herstel gecontroleerde beta.76-code. Behoud entry, opslag en userfiles. Beta.76 negeert de nieuwe optionele kandidaat-evidence; bestaande ondersteunde PV-factoren en overige gegevens blijven beschikbaar. Terugzetten verwijdert niet automatisch een intussen geldig geleerde factor in ondersteund formaat.

Exact herstel vraagt code én de passende volledige privéback-up; bewaar gewenste nieuwe historie eerst. Verwijder de entry niet en laat nooit twee runtimes tegelijk werken. Voor de oude directe beta.61-regeling blijft de volledige pre-beta.62-back-up nodig. Software-/publicatiebewijs: [TESTRESULTATEN_BETA77.md](TESTRESULTATEN_BETA77.md). Volledige werking: [ACTUELE_WERKING.md](ACTUELE_WERKING.md).
