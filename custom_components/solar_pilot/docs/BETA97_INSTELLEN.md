# SolarPilot beta.97 — eerder opnieuw beoordelen bij werkelijk restoverschot

Versie: **1.0.0-beta.97** · 18 oktober 2026 · Bouwbasis: gepubliceerde beta.96.

## Wat verandert

Na een beëindigde algemene SG-aanvraag met onbekend effect wachtte SolarPilot eerst de ingestelde rusttijd, standaard vijftien minuten. Pas daarna begonnen vijf minuten overschotbevestiging en de gewone startvertraging. Die extra wachttijd bewaakte het herhalen van SG-aanvragen; zij bewees geen compressorstop en was geen door Panasonic gemelde compressorbescherming.

Bij een aantoonbaar eigen beëindigde aanvraag kan SolarPilot nu direct vijf minuten nieuwe, voldoende werkelijke restinjectie beoordelen. Als het SG-contact opnieuw betrouwbaar UIT is, het oorspronkelijke opdrachtbewijs nog bij dezelfde uitgang past en alle actuele voorwaarden gelden, vervangt deze bevestiging de resterende SG-herhaalwacht. Daarna volgt de gewone startvertraging, standaard twee minuten. Bij voortdurend voldoende verse metingen wordt de normale route dus ongeveer **vijf plus twee minuten**, in plaats van vijftien plus vijf plus twee.

Deze verkorting geldt uitsluitend voor het bevestigde algemene SG-profiel met onbekende eerdere reactie. Onzekere of ontbrekende opdrachtherkomst, een onbekend contact, handmatige overname en echte blokkeringen geven geen verkorting. Andere voltooiingsredenen, het sessiemaximum en het profiel Uitsluitend tapwater houden hun bestaande aparte voorwaarden. De ingestelde rustwaarde blijft bewaard als terugval. Een aanvraag die onder een oudere versie is vastgelegd zonder de benodigde oorspronkelijke identiteit houdt eenmaal de oude wacht. De update vult dat ontbrekende historische bewijs niet achteraf in; nieuw vastgelegde passende aanvragen kunnen de kortere route gebruiken.

SG blijft een extra toestemming. SolarPilot stelt niet vast dat Panasonic daardoor moet starten en gebruikt ontbrekend startbewijs niet als bewijs van een defect. Er komen geen periodieke UIT/AAN-pulsen of Panasonic-instelopdrachten.

## Aquarea-controle

De nieuwe Aquarea **1.7.0** en de werkelijk gepubliceerde SDK **1.3.1** zijn opnieuw op hun actuele GitHub-bronnen gecontroleerd. Het nieuwe attribuut `auto_mode` toont de gekozen AUTO-richting, ook tijdens stilstand. SolarPilot blijft compatibel zonder dit attribuut als compressor-, actief bedrijfs- of SG-vrijgavebewijs te behandelen. De bestaande getypeerde bron- en actualiteitscontroles blijven gelden. De provider wordt niet door deze update geïnstalleerd.

## Installeren en controleren

1. Bewaar een actuele volledige privéback-up van Home Assistant.
2. Installeer beta.97 via HACS zodra de vijf vereiste controles en publicatie zijn geslaagd. Behoud dezelfde integratie-entry, instellingen, modellen, historie, opslag en userfiles.
3. Herstart Home Assistant volledig en herlaad de app/browser volledig. Controleer backend- en kaartversie afzonderlijk.
4. Bekijk bij een volgende werkelijk beëindigde aanvraag de oorspronkelijke stopreden, SG-herhaalwacht en nieuwe overschotbevestiging. Een herstart alleen geeft geen nieuwe toestemming; het bewijsvenster begint opnieuw met actuele bronrapporten.

Een tekort, brononderbreking, bindingwijziging of actuele blokkering kan de vijfminutencontrole opnieuw laten beginnen. De gebruikelijke elektrische grenzen, koelvoorwaarde, lokale aflooptimer, minimumduur en maximumduur blijven beschermd. Geen instelling of bronkoppeling hoeft voor deze update opnieuw ingevuld te worden.

## Rollback

Herstel zo nodig de oorspronkelijke beta.96-code met behoud van entry, instellingen, opslag en userfiles; herstart Home Assistant volledig. Geef een eigen SG-aanvraag vooraf veilig vrij waar betrouwbaar mogelijk en onderbreek geen beschermde apparaatcyclus. De oude versie gebruikt opnieuw de langere SG-herhaalwacht. Er is geen nieuw opslagschema of historische herindeling.

[Actuele werking](ACTUELE_WERKING.md) · [Testverslag](TESTRESULTATEN_BETA97.md) · [Upstreamcontrole](AQUAREA_UPSTREAM_REVIEW_BETA97.md) · [Overdracht](../OVERDRACHT.md)
