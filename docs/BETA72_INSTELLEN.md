# SolarPilot 1.0.0-beta.72 — minimale SG-aanvraagduur

Beta.72 voegt een instelbare minimale SG-aanvraagduur toe, standaard **1200 seconden, twintig minuten**. Aanhoudende gewone netafname geeft de aanvraag pas na dit effectieve minimum vrij. Het minimum betreft de SG-aanvraag: Panasonic bepaalt zelfstandig zijn compressorbedrijf. Harde guards en het behouden sessiemaximum kunnen eerder beëindigen.

## Update met behoud van gegevens

1. Maak een volledige privé Home Assistant-back-up, inclusief instellingen, eigen opslag, modellen, tickets, gewone en warmtepompgeschiedenis en userfiles. Bewaar gecontroleerde beta.71-code voor rollback.
2. Geef vóór codevervanging een eigen SG-aanvraag vrij en controleer de gemelde contactstand/lokale afloop. Onderbreek geen beschermde apparaatcyclus.
3. Update via HACS naar exact `1.0.0-beta.72` na publicatie. Bij lokale installatie vervang je uitsluitend `custom_components/solar_pilot`; behoud lokale userfiles en HA-opslag.
4. Herstart Home Assistant volledig. Herlaad de browser volledig, of sluit de app volledig af en open haar opnieuw. Controleer backend- en kaartversie afzonderlijk.
5. Controleer onder de bestaande geavanceerde SG-instellingen **Minimale SG-aanvraagduur (s)** en het behouden maximum. De nieuwe standaard geldt alleen als deze minimumoptie nog ontbreekt. Een expliciete bestaande waarde, ook nul, blijft behouden. Alle overige waarden, bindings, prioriteiten en geldige SG-/profiel-/split-/koelbevestigingen blijven staan.

Eerste installatie blijft HACS Integration, HA-herstart en toevoegen onder Apparaten & diensten. De kaart wordt automatisch geregistreerd; een aparte Lovelace-resource is niet nodig. Nieuwe SG-sturing blijft uit tot de bestaande lokale ingebruiknamevoorwaarden zijn bevestigd.

## Minimum, maximum en tekortvrijgave

| Onderdeel | Gedrag |
| --- | --- |
| Minimum | Standaard twintig minuten vanaf bevestigde contact-AAN. Alleen gewone zachte tekortvrijgave wordt uitgesteld. |
| Aanhoudende netafname | De bestaande kleine-importbuffer, standaard 300 W, en stopvertraging, standaard 60 s, blijven gelden. De vertraging loopt tijdens het minimum door. |
| Minimum verstreken | Als de tekortvertraging al is voldaan, kan de actuele beoordeling meteen vrijgeven. Geen verplichte extra 60 s na twintig minuten. Zonder tekort hoeft de aanvraag dan niet te stoppen. |
| Harde beëindiging | Bronverlies, elektrische/batterij-/koel-/prioriteitsgrenzen, handmatige overname, Pauze/uitschakelen, geverifieerde native voltooiing, bevestigd geen extra opname, lease-/transportfout en sessiemaximum houden hun bestaande vroege vrijgave. |
| Maximum | De behouden harde maximumduur loopt conservatief vanaf de oorspronkelijke verzending. Het effectieve minimum is hoogstens de bij bevestigde AAN nog beschikbare maximumtijd. Een bestaand korter maximum blijft dus eerder stoppen. |
| Instelbereik | `min_session_s`: 0–14400 s, formulierstap 60 s. Nul schakelt alleen dit minimum uit. Geen automatische verhoging van een bestaand maximum. |

Lage watts of een onbekende reactie alleen zijn geen bevestigd bewijs van native voltooiing of geen extra opname.

Een minimumduur kan tijdelijk gewone netafname toestaan binnen alle bestaande harde grenzen. Zij geeft geen extra fysieke fase-/netruimte, EV-krediet of nieuwe starttoestemming. Warmtepomp-zonnecredit blijft uitsluitend voor de startdrempel; de aparte conservatieve extra-vraagraming blijft behouden.

## Korte lokale toestemming blijft afzonderlijk

De Shelly-toestemming blijft kort en lokaal aflopend, standaard 300 s met vernieuwing elke 60 s. Tijdens uitsluitend de minimumwacht op zachte tekortvrijgave kan SolarPilot die veilig vernieuwen zonder fysieke UIT/AAN-cyclus. Alle actuele guards blijven bij iedere beoordeling en vernieuwing leidend. De lokale timer wordt **niet 1200 seconden**.

Na het effectieve minimum houdt een lopende gewone tekortcontrole de bestaande regel aan: geen leaseverlenging tijdens die controle. Bij HA-/netwerkuitval kan het contact dus vóór twintig minuten lokaal vervallen. Een leasevernieuwing reset het minimum niet; reload/herstart geeft geen nieuw minimum, AAN-herhaling of bedieningsrecht.

De bestaande vijfminutenbevestiging van een nieuwe zonneperiode/native aanleiding en de ingestelde startvertraging blijven afzonderlijke stappen vóór een nieuwe aanvraag. Nul bevestigingsseconden wacht op een passend nieuw eindrapport; nul startvertraging wacht op de bestaande actuele beoordeling.

## Panasonic, geschiedenis en privacy

Panasonic-percentages, koelwaarden, temperaturen, programma's en beveiligingen blijven ongewijzigd. SolarPilot gebruikt uitsluitend de bestaande toegewezen SG-uitgang. Twintig minuten aanvraag bewijst geen twintig minuten compressorbedrijf, warmteproductie of causale SG-energie.

De aparte warmtepompgeschiedenis en alle gewone geschiedenis, modellen en tickets blijven behouden. Dertig lokale kalenderdagen retentie staat los van het gekozen 1/24/168-uursanalysevenster. Alle overlappende lokale datums blijven opgenomen met volledige werkelijk geregistreerde kalenderdagtotalen, expliciete grensdatums en meetdekking. Geen energie naar rato, backfill of opslagreset.

Geschiedenis blijft read-only met READ-controles op actuele en bewaarde bronnen; privé-analyse-export blijft een bewuste lokale beheerderdownload. Geen huishoudelijke exports, bindings of back-ups in publieke GitHub-bron of release-assets.

## Rollback naar beta.71

Geef de eigen SG-aanvraag vrij, controleer contact/lokale afloop en stop beta.72. Herstel gecontroleerde beta.71-code met behoud van dezelfde entry, opslag en userfiles. Beta.71 kent de nieuwe minimumregeling niet: gewone aanhoudende netafname kan daar weer volgens de oude stopvertraging vrijgeven. Dezelfde geschiedenis en beta.71-export-/wachtweergave blijven beschikbaar.

Voor exact herstel van de pre-upgradetoestand herstel je code én de volledige passende privéback-up. Dit kan later geregistreerde data vervangen; bewaar gewenste nieuwe historie eerst. Een ZIP alleen herstelt geen eerder tijdstip van alle data. Verwijder de entry niet en laat nooit twee runtimes tegelijk werken.

Terugkeer naar de oude directe beta.61-regeling vereist nog steeds de volledige back-up van vóór de beta.62-migratie. Zie [TESTRESULTATEN_BETA72.md](TESTRESULTATEN_BETA72.md) voor het software-/publicatiebewijs en [ACTUELE_WERKING.md](ACTUELE_WERKING.md) voor de volledige werking.
