# SolarPilot 1.0.0-beta.78 — afwasdeadline zonder zonnevoorwaarde

Beta.78 herstelt de AEG-startdeadline: een geldige APP-aanvraag mag op haar eenmaal vastgelegde deadline netstroom gebruiken, ook zonder zonneoverschot. Oudere zonne-/netvoorkeursvlaggen, zonne-stabiliteit, prijsplanning of lage batterij-SoC mogen deze start niet uitstellen. De update verhoogt geen fysieke vermogensgrens en verzendt geen tweede START bij onzekerheid.

## Update met behoud van gegevens

1. Maak een volledige privé HA-back-up met instellingen, eigen opslag, PV-factoren, modellen, tickets, gewone en warmtepompgeschiedenis en userfiles. Bewaar gecontroleerde beta.77-code.
2. Geef vóór codevervanging een eigen SG-aanvraag vrij en controleer contact/lokale afloop. Onderbreek geen beschermde apparaatcyclus.
3. Update via HACS naar exact `1.0.0-beta.78` na geslaagde releasegates en publicatie. Lokaal vervang je uitsluitend `custom_components/solar_pilot`, met behoud van userfiles en HA-opslag.
4. Herstart HA volledig en herlaad browser/app volledig. Controleer backend- en kaartversie afzonderlijk.
5. Controleer bij de afwasmachine de ontvangen aanvraag en oorspronkelijke geplande dag/startdeadline. Een bestaande aanvraag wordt niet naar later verschoven, herarmd of opnieuw aangemaakt door deze update.
6. Bekijk na deadline of startbevestiging de actuele reden, aanvraagcontext en melding. Controleer daarnaast Planning, PV-diagnose en bestaande Meetkwaliteit/geschiedenis.

Behoud dezelfde entry, bindings, prioriteiten en geldige SG-/profiel-/split-/koelbevestigingen. Geen extra installatie, nieuwe verplichte sensor, reset of algemene herbevestiging. Exacte actuele release-/pakketstatus staat in [TESTRESULTATEN_BETA78.md](TESTRESULTATEN_BETA78.md); bron in een branch bewijst nog geen publicatie.

## Wat de deadline betekent

| Situatie | Gedrag vanaf beta.78 |
| --- | --- |
| Geldige aanvraag, deadline nog niet bereikt | De bestaande zonne-/plannervoorwaarden blijven van toepassing. De opgeslagen geplande dag en deadline blijven vast. |
| Deadline bereikt, geen zonneoverschot | Netstroom is toegestaan voor deze beschermde belading; de start wacht niet op zon. |
| Oud `solar_only` of `allow_grid=False` bij de aanvraag | De deadline gebruikt de nieuwe nettoestemming zonder de opgeslagen aanvraag of gebruikersconfiguratie te herschrijven. |
| Zonne-stabiliteit, prijsvoorkeur, lage batterij-SoC | Deze voorkeuren zijn geen deadlineblokkering. Een vermogensactie die nog niet is bevestigd of afgehandeld blijft wel een uitvoeringsblokkering. |
| Onvoldoende net-/fase-/kwartier-/vermogensruimte | Er wordt niet buiten de bestaande grenzen gestart. De actuele reden benoemt de benodigde en werkelijk beschikbare ruimte. Een nog niet verzonden START wordt binnen de bestaande grace opnieuw beoordeeld. |
| Open deur, apparaatfout, onbetrouwbare bron, Pauze of Alleen bekijken | De deadline passeert deze voorwaarden niet. De concrete bekende blokkering blijft zichtbaar. |
| Eén START verzonden, resultaat onbekend | Geen blind retry, nieuwe belading of extra START. Betrouwbare native status blijft nodig om het resultaat te bevestigen. |
| Passende native Running-bevestiging voor dezelfde aanvraag | De achterhaalde melding over de gemiste deadline verdwijnt. Verbruikte aanvraag en beschikbare startcontext blijven bij de beurt zichtbaar. Het programma mag afwerken. |

Een geldige APP-aanvraag ontstaat uitsluitend via de bestaande nieuwe exacte `Enabled`-overgang. APP al Enabled bij startup geeft geen nieuwe belading. De bronnen van een bestaande aanvraag blijven gebonden; gewijzigde of onbekende bindings leveren geen nieuwe starttoestemming.

De netfallback begint op de opgeslagen deadline en blijft binnen de bestaande deadlinegrace, standaard **120 minuten** met behoud van expliciet ingestelde waarden. Zij geeft toestemming om netstroom te gebruiken, geen garantie dat de afwasmachine fysiek start bij een open deur, verbroken verbinding of onvoldoende elektrische ruimte. Als een geldige niet-verzonden start later binnen die termijn weer past, beoordeelt SolarPilot haar opnieuw. Een gemiste of onzekere START wordt niet achteraf tot succesvolle start gemaakt.

## Wat de kaart en meldingen tonen

Een deadlineblokkering krijgt de actuele oorzaak in plaats van alleen **Wacht op vermogen / hogere prioriteit**. De reden maakt het onderscheid tussen toegestane netstroom en ontbrekende fysieke ruimte zichtbaar. De start die in dezelfde regelronde geldig wordt geselecteerd veroorzaakt geen nieuwe gemiste-deadlinemelding.

Bij betrouwbaar bevestigd native bedrijf bewaart SolarPilot de verbruikte aanvraag, de oorspronkelijke deadline en beschikbare startcontext. Een lopende beurt wordt niet als **nog niet klaargezet / deadline onbekend** weergegeven alleen omdat haar ticket is verbruikt. De geconstateerde of verzonden starttijd blijft onderscheiden van een bewezen fysieke starttijd. De bestaande melding **Afwasmachine: startdeadline niet gehaald** wordt gericht verwijderd na een passende nieuwe native Running-bevestiging voor dezelfde aanvraag; Drying alleen is daarvoor onvoldoende. Overige foutmeldingen worden daarmee niet algemeen gewist. Nieuwe meldingen gebruiken de titel **Afwasmachine: startdeadline geblokkeerd** en vermelden de concrete oorzaak.

## Behouden instellingen, regeling en gegevens

De update reset geen aanvraag, prioriteit, bronbinding, model of meetgeschiedenis. Bestaande onzekere START-pogingen blijven beschermd; een codeupdate of reload herarmt ze niet. Uitgesloten toestellen, handmatige overname, Pauze, fouten en werkelijke elektrische grenzen behouden hun betekenis.

De PV-kalibratie en namiddagdiagnose uit beta.77, gezamenlijke dependencyvrije toestelplanner, geïsoleerde executorroute, chronologisch batterijadvies, onderzoek, exports, adviesrapporten en gewone/warmtepompgeschiedenis blijven behouden. Batterijadvies gebruikt de bestaande geconfigureerde roundtrip-efficiëntie uit de batterijanalyse, standaard 80% (20% verlies). Geen EMHASS-installatie, add-on, solver, tweede regelaar of cloud-AI.

Panasonic blijft eigenaar van comfort, warm water, compressor, kleppen, pompen, ondersteuning, percentages, koelwaarden en sterilisatie. Het bestaande toegewezen SG-contact blijft de enige warmtepompactuator. Wallbox blijft autonoom en read-only; AEG behoudt maximaal één native START per nieuwe geldige APP-belading, zonder PAUSE/RESUME/STOPRESET, programmakeuze, timerwrite of stekkeronderbreking.

SG blijft standaard netafname strikt boven **600 W gedurende vijf continue minuten**, met **minimum twintig minuten** en korte leases 300 s/60 s. Alle harde guards, handmatige overname, Pauze/disable, fouten, geverifieerde native voltooiing en hardmaximum behouden vroege vrijgave. Bestaande PV-/SG-instellingen, globale netafnamegrens, fase- en overige vermogensgrenzen veranderen niet. Een adviesupload blijft data en past geen instelling of code toe.

## Rollback naar beta.77

Geef de eigen SG-aanvraag vrij, controleer contact/lokale afloop, stop beta.78 en herstel gecontroleerde beta.77-code. Behoud entry, actuele opslag en userfiles, inclusief verbruikte of afgeronde aanvragen. Beta.77 kan de bestaande data blijven lezen, maar mist deze deadlinecorrectie en kan weer op oudere zonne-/netvoorkeuren wachten. Code terugzetten mag geen START opnieuw vrijgeven.

Exact herstel vraagt code én de passende volledige privéback-up; bewaar gewenste nieuwe historie eerst. Herstel geen oude onverbruikte ticketback-up bij een inmiddels gestart of afgerond programma. Verwijder de entry niet en laat nooit twee runtimes tegelijk werken. Voor de oude directe beta.61-regeling blijft de volledige pre-beta.62-back-up nodig. Software-/publicatiebewijs: [TESTRESULTATEN_BETA78.md](TESTRESULTATEN_BETA78.md). Volledige werking: [ACTUELE_WERKING.md](ACTUELE_WERKING.md).
