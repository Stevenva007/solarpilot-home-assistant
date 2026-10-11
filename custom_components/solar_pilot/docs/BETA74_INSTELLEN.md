# SolarPilot 1.0.0-beta.74 — duidelijke diagnose zonder nieuwe regeling

Beta.74 verbetert drie uitleesmeldingen: na een bevestigde lage zonne- of rustige native resetfase geen herhaalde resetcountdown, een concrete oorzaak bij een oude/onbekende gekoppelde Wallboxsessiebron, en een scopebewuste warmtepompstatus. Native ruimte-/zone-UIT betekent niet vanzelf hele-warmtepomp-UIT. Onvolledige meters en onbewezen globaal UIT blijven onbekend.

## Update met behoud van gegevens

1. Maak een volledige privé HA-back-up met instellingen, eigen opslag, modellen, tickets, gewone en warmtepompgeschiedenis en userfiles. Bewaar gecontroleerde beta.73-code.
2. Geef vóór codevervanging een eigen SG-aanvraag vrij en controleer gemelde contactstand/lokale afloop. Onderbreek geen beschermde apparaatcyclus.
3. Update via HACS naar exact `1.0.0-beta.74` na publicatie. Lokaal vervang je uitsluitend `custom_components/solar_pilot`, met behoud van userfiles en HA-opslag.
4. Herstart HA volledig en herlaad browser/app volledig. Controleer backend- en kaartversie afzonderlijk.
5. Controleer de drie diagnosemeldingen, bestaande meetdekking, SG-contact en geschiedenis. Er is geen nieuwe verplichte sensor, stale-grens, algemene herbevestiging of instellingenreset.

Behoud dezelfde entry, bindings, prioriteiten en geldige SG-/profiel-/split-/koelbevestigingen. Eerste installatie blijft HACS Integration en toevoegen onder Apparaten & diensten; nieuwe SG-sturing blijft uit tot de bestaande lokale voorwaarden bevestigd zijn.

## Wat de diagnose nu betekent

| Weergave | Betekenis en grens |
| --- | --- |
| Zonne-/native resetfase al bevestigd | Geen telkens opnieuw getoonde laagfasecountdown. Wachten op nieuwe relevante native context/teruggekeerd overschot en een werkelijk lopende bevestiging blijven apart. De controller behoudt rolling bewijs en alle guards. |
| Gekoppelde Wallboxsessiebron oud/onbekend | De leervraag benoemt ontbrekende actualiteit/betrouwbaarheid van die bron. Geen aangenomen Full Solar, bevestigde stop of langere stale-grens. Wallbox blijft read-only. |
| Native ruimte-/zone-UIT | Heeft alleen het gemelde bereik; geen bewezen hele-warmtepomp-UIT. Een onvolledig totaal bevestigt geen elektrische rust; een losse native UIT-melding zonder passend globaal bewijs bevestigt geen rust. |
| Deelmeting op nul | Geldige nul blijft zichtbaar, maar vult de ongeldige/ontbrekende andere voeding niet in. Negatief blijft afgekeurd, geen absolute waarde of tekenomkering. |
| Taak- of effectuitleg | Verse native taak, elektrische activiteit en SG-aanvraag/contact blijven onderscheiden. Een taakovergang is geen meting van causale extra SG-energie, warmteproductie of compressorlooptijd. |

Een nieuwe zonneperiode vraagt nog steeds eerst vijf minuten laag restoverschot op of onder de behouden zonne-resetgrens, daarna vijf minuten teruggekeerd overschot vanaf de startdrempel, met echte nieuwe rapporten en de aparte startvertraging. De schermcorrectie bevestigt niets en verandert geen timer.

## SG-regeling en overige gegevens blijven behouden

Standaard geldt **actueel gemeten netafname strikt boven 600 W gedurende vijf continue minuten**, tegelijk met de **minimale SG-aanvraagduur van twintig minuten**. Bij 600 W of lager vervalt de tekorttimer. Een tekort vanaf minuut 18 kan bij aanhouden pas in minuut 23 gewone vrijgave geven; een eerder voltooide tekorttijd kan bij het minimum al gelden. Zonder tekort is twintig minuten geen verplichte stop. De aparte zonne-resetgrens blijft standaard 300 W.

De runtime-normalisatie uit beta.73 blijft hetzelfde: zonder nieuwe importoptie wordt de oude effectieve standaardcombinatie 300 W/60 s 600 W/300 s; oude afwijkingen en expliciete nieuwe waarden blijven behouden, zonder automatische optieswrite. Alle minimum-/maximumwaarden blijven staan.

Korte lokale toestemming blijft standaard 300 s, veilig vernieuwd iedere 60 s tijdens geldige minimum- en wolkenwachttijd, ook na het minimum. Geen UIT/AAN-cyclus of lokale twintigminutentimer. Bronverlies, harde net-/fase-/kwartier-/batterij-/koel-/Wallbox-/prioriteitsgrenzen, handmatige overname, Pauze/disable, geverifieerde native voltooiing/bevestigd geen extra opname, fouten en hardmaximum behouden vroege vrijgave. Lage watts of onbekende reactie zijn geen native beëindigingsbewijs. Kort maximum/ACK-reserve en de absolute grens vóór AAN/vernieuwing blijven leidend; reload geeft geen nieuw aanvraagrecht.

Panasonic blijft eigenaar van programma's, percentages, koelwaarden, comfort en beveiligingen. Eén bestaande toegewezen SG-uitgang blijft de enige warmtepompactuator. Het minimum beschermt de SG-aanvraag, niet gegarandeerde compressorlooptijd of levensduur. Geen nieuwe native schrijftoestemming of fysieke diagnose uit een schermlabel.

Alle overige apparaten, gebruikerswaarden, modellen, tickets en geschiedenis blijven behouden. Warmtepompgeschiedenis blijft read-only met bron-READ-controles en aparte opslag. Dertig lokale kalenderdagen retentie staat los van 1/24/168 rollende analyse-uren; alle overlappende datums behouden volledige geregistreerde dagtotalen en meetdekking, met expliciete grensdagen. Geen backfill of energie naar rato. Analyse-export blijft een bewuste lokale beheerderdownload; private exports/bindings/back-ups horen niet in publieke bron of assets.

## Rollback naar beta.73

Geef de eigen SG-aanvraag vrij, controleer contact/lokale afloop, stop beta.74 en herstel gecontroleerde beta.73-code. Behoud entry, opslag en userfiles. De SG-regeling blijft dezelfde; de eerdere diagnoseweergave keert terug. Code terugzetten corrigeert geen meter, bedrading of fysieke toestand.

Exact herstel vraagt code én de passende volledige privéback-up; bewaar gewenste nieuwe historie eerst. Verwijder de entry niet en laat nooit twee runtimes tegelijk werken. Voor de oude directe beta.61-regeling blijft de volledige pre-beta.62-back-up nodig. Software-/publicatiebewijs: [TESTRESULTATEN_BETA74.md](TESTRESULTATEN_BETA74.md). Volledige werking: [ACTUELE_WERKING.md](ACTUELE_WERKING.md).
