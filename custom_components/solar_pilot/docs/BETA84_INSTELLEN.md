# SolarPilot 1.0.0-beta.84 — tijdelijke SG-bediening en rustige herstart

Beta.84 voegt **Aan voor 30/60 minuten** en **Uit voor 30/60 minuten** toe aan de SG-boost. Na afloop wordt **Automatisch** gekozen. De keuze en haar absolute eindtijd worden bewaard: herladen of herstarten begint de tijd niet opnieuw.

Een echte Home Assistant-herstart kan een reeds bevestigde eigen AAN-sessie zonder onnodige UIT/AAN-wissel voortzetten. Dat vereist passende nieuwe contact-, timer-, bron- en veiligheidsgegevens, dezelfde binding/policy en een nog geldige lokale timer. De oorspronkelijke sessiestart en het harde maximum blijven leidend. De eerste upgrade vanuit beta.83 mist dit nieuwe sessiebewijs en kan daarom nog één veilige vrijgave vragen.

## Upgrade

1. Maak een volledige privé Home Assistant-back-up met instellingen, eigen opslag, PV-factoren, modellen, APP-aanvragen, historie en userfiles. Bewaar gecontroleerde beta.83-code.
2. Geef vóór codevervanging een eigen SG-aanvraag veilig vrij en controleer contact en lokale afloop. Onderbreek geen beschermde apparaatcyclus.
3. Update via HACS naar exact `1.0.0-beta.84` nadat releasegates en publicatie geslaagd zijn. Lokaal vervang je uitsluitend `custom_components/solar_pilot`, met behoud van userfiles en HA-opslag.
4. Herstart Home Assistant volledig en herlaad app/browser volledig. Controleer backend- en kaartversie afzonderlijk: beide moeten beta.84 zijn. Verwijder of hermaak de entry niet.
5. Bestaande geldige bronkeuzes, volgorde, timers en SG-/profiel-/split-/koelbevestigingen blijven staan. Een update verleent geen nieuwe ingebruikname of actuatorrechten. Controleer actuele beslisreden, contactstand, lokale timer, boilerwaarden en overige toestelstatussen.

## Tijdelijke bediening gebruiken

Naast de SG-contactstand kies je **Automatisch**, **Aan 30 min**, **Aan 1 uur**, **Uit 30 min** of **Uit 1 uur**, zowel in Overzicht als op het warmtepomptabblad. Dezelfde vijf keuzes staan in de native Home Assistant-select **SG-bediening**. De resterende tijd en concrete blokkering staan bij de SG-status; de werkelijk gemelde contactstand blijft afzonderlijk zichtbaar. De kaart verandert de gemelde stand niet alvast na een klik. Duurt een verzoek te lang, controleer dan de actuele bediening voordat je het herhaalt.

| Keuze | Werking | Bij afloop |
|---|---|---|
| Automatisch | Gewone zonnevoorwaarden en huidige policy bepalen de SG-aanvraag. | Blijft automatisch. |
| Aan · 30/60 minuten | Bewuste tijdelijke SG-vraag; vervangt zon, startvertraging, rust, beleidswacht en zachte importstop. Mogelijke netafname blijft binnen harde grenzen. | Automatisch; een passend al AAN-contact blijft aan als de actuele automatische voortzetting geldig is. |
| Uit · 30/60 minuten | Geeft de eigen SG-aanvraag veilig vrij en onderdrukt automatische SG-start. Panasonic mag zelfstandig verder werken. | Automatisch; een nieuwe start vereist de dan geldende verse voorwaarden en policy. |

Je kunt tussentijds **Automatisch** kiezen. Een andere tijdelijke keuze legt een nieuwe eindtijd voor die keuze vast; zij reset geen al lopende SG-sessie. Een uur Aan kiezen na bijvoorbeeld twintig minuten actief bedrijf maakt geen nieuw volledig uur binnen het harde sessiemaximum. Het vaste bestaande maximum kan eerder vrijgeven, evenals een echte veiligheidsblokkering. De gekozen duur is geen gegarandeerde contact- of compressorlooptijd.

**Aan omzeilt geen harde voorwaarden.** De bestaande SG-enabled, gecontroleerde ingebruikname, mapping, lokale timer, profiel, verse noodzakelijke bronnen, elektrische/net-/fase-/kwartiergrenzen, batterij-/Wallbox-/prioriteitsvoorwaarden, koelbeveiliging, eigenaarschap en globale regelmodus blijven gelden. Alleen bekijken, Pauze, echte fouten en externe handmatige overname worden niet door deze keuze opgeheven. Een geblokkeerde tijdelijke Aan-vraag toont haar concrete reden.

**Buiten SolarPilot gewijzigd contact.** Heeft iemand het SG-contact of de lokale timer buiten SolarPilot gewijzigd, kies dan eerst **Hervatten** voordat je tijdelijk Aan vraagt. De tijdelijke Aan-keuze neemt een externe overname niet stil terug en behoudt de bestaande beveiligingscontrole. Een bewuste tijdelijke Uit-keuze mag een daadwerkelijk AAN gemeld, gecontroleerd toegewezen SG-contact wel veilig vrijgeven; zij schakelt alleen dat contact en geen native warmtepompprogramma of hoofdvoeding.

Voor eigen HA-automatiseringen is de beheerdersservice `solar_pilot.sg_manual_control` beschikbaar met `config_entry_id`, `mode` (`auto`, `on`, `off`) en alleen voor tijdelijk Aan/Uit `duration_s` (`1800` of `3600`). Gebruik voor Automatisch geen duur. Deze service biedt hetzelfde beperkte SG-recht als de kaart en de select; geen native Panasonic-bediening.

## Herstart en lokale afloop

De korte lokale Shelly-toestemming blijft standaard **300 seconden**, met vernieuwing iedere **60 seconden**. Ook bij een half uur of uur tijdelijk Aan wordt zij niet tot die lange duur verlengd. Zonder geldige vernieuwing vervalt de lokale toestemming. Geen extra hardware, server, afhankelijkheid of tweede regelaar is nodig.

Een nieuwe volledig bevestigde beta.84-sessie kan na een echte HA-herstart doorgaan als het contact nog daadwerkelijk AAN is, de timer nog loopt, en nieuwe betrouwbare gegevens dezelfde eigen sessie onder actuele geldige voorwaarden bevestigen. Herstart reset geen oorspronkelijke minimum-, tekort-, sessie- of keuzetimer. Oude opgeslagen metingen of contactstanden gelden niet als verse bevestiging. Een vervallen timer, onzekere opdracht, gewijzigd contact/policy, externe overname of onvoldoende voorwaarden wordt niet blind als oude AAN herhaald.

Zijn opstartbronnen tijdelijk nog niet beschikbaar, dan kan alleen de reeds vastgestelde korte lokale timer blijven lopen tijdens het wachten op verse gegevens. SolarPilot vernieuwt haar dan niet en claimt geen bewezen eigendom of vrijgave uit ontbrekende gegevens. Een bekende harde blokkering vraagt veilige vrijgave.

Een nog niet verlopen bewaarde bewuste **Aan**-keuze met dezelfde binding blijft een gebruikersvraag. Na verlopen oude lokale toestemming mag zij opnieuw een huidige SG-beoordeling vragen als alle verse harde voorwaarden en veilige opdracht-/contactafhandeling passen. De oorspronkelijke maximale sessie-eindtijd blijft leidend: geen nieuw uur, verlopen eigendom of herhaling van een onzekere oude opdracht.

**Een oude beta.83-sessie wordt uitsluitend veilig vrijgegeven:** haar journal mist de vereiste oorspronkelijke sessie- en timerherkomst. De eerste upgrade biedt daardoor nog geen gegarandeerde contactcontinuïteit. Gewoon integratie-unload, uitschakelen, herbinding en verwijderen blijven de eigen aanvraag veilig vrijgeven. Een gewone herstart is geen manier om een beëindigde sessie, rust of beleidswacht te resetten.

De automatisch gekozen wolkenbuffer **600 W gedurende vijf continue minuten**, minimumaanvraagduur **twintig minuten**, harde sessiemaximum en alle expliciete geldige gebruikerswaarden blijven behouden. Tijdelijk Aan is het afzonderlijke bewuste verzoek hierboven; terugkeer naar Automatisch herstelt de gewone policy zonder verplichte contactpuls. SG-UIT schakelt geen hoofdvoeding, compressor of Panasonic-programma uit.

## Korte onderbreking tijdens inschakelvertraging

De aanvankelijk met geldige voorwaarden gestarte inschakelklok kan tijdens een korte zondip of tijdelijk ontbrekende/verouderde meting maximaal **vijf minuten** blijven doorlopen. De klok hoeft na passend herstel binnen dit venster niet helemaal opnieuw. Het contact gaat uitsluitend AAN wanneer nieuwe betrouwbare bronnen opnieuw voldoende zonnebijdrage en alle harde voorwaarden bevestigen. Een verstreken klok tijdens de onderbreking betekent **wachten op herstel**, geen starttoestemming. Ontbrekende data is geen nul en geen bewezen wolk. Een langere onderbreking, bekende harde limiet, Pauze of veranderde binding reset de opbouw.

## Behoud en praktische controle

Panasonic blijft zelfstandig verantwoordelijk voor warm water, verwarmen/koelen, ondersteuning, ontdooien en sterilisatie. SolarPilot bedient uitsluitend het toegewezen SG-contact. Wallbox blijft read-only; AEG blijft één START per geldige nieuwe belading met behoud van deadline en beschermde cyclus. De beta.83-bronherkenning, berekende doelvergelijking, PV-diagnose, leren en bestaande historie blijven behouden. Geen retrospectieve herindeling of terugvullen.

Controleer na installatie bij een passende gelegenheid de keuzeduur, terugkeer naar Automatisch, echte contactstand en lokale timer. Controleer een herstart uitsluitend met passende actuele bron- en timergegevens: softwaretests bewijzen niet het daadwerkelijke timergedrag van je Shelly. Bewaar privé meet-/contactgegevens voor analyse; publiceer geen woningdata of entiteits-ID's op GitHub.

## Rollback naar beta.83

1. Kies Automatisch, geef de eigen SG-aanvraag veilig vrij en controleer contact/lokale afloop. Bewaar eerst een volledige actuele privéback-up en eventuele nieuwe historie.
2. Stop beta.84 en herstel gecontroleerde beta.83-code, met behoud van entry, actuele opslag en userfiles. Laat nooit twee runtimes tegelijk werken.
3. Herstart HA volledig en herlaad app/browser. Beta.83 behoudt de bronsemantiekcorrectie, berekende SG-doelen en diagnose-/PV-weergave, maar mist tijdelijke SG-bediening en de nieuwe voortzetting bij echte HA-herstart. Oudere code kan de tijdelijke keuze niet uitvoeren en kan aanvullende opslagvelden bij schrijven verliezen.

Exact herstel vraagt code én een passende volledige privéback-up. Herstel geen oude onverbruikte APP-aanvraag bij een inmiddels gestart of afgerond programma. Code terugzetten mag geen tweede START of oude AAN-replay vrijgeven. Instellingen of Panasonic-native doelen worden niet door de rollback gecorrigeerd.

Actuele werking: [ACTUELE_WERKING.md](ACTUELE_WERKING.md). Brongebonden software-/CI-/pakketbewijs: [TESTRESULTATEN_BETA84.md](TESTRESULTATEN_BETA84.md). Publieke upstreamcontracten en de afzonderlijke wekelijkse ontwikkeltaak: [UPSTREAM_BRONNEN.md](UPSTREAM_BRONNEN.md).
