# SolarPilot beta.78 — installatie en upgrade

Beta.78 herstelt de AEG-startdeadline. Op de vastgelegde deadline van een geldige APP-aanvraag mag de afwasmachine netstroom gebruiken, ook zonder zonneoverschot en ongeacht oudere zonne-/netvoorkeursvlaggen. Zonne-stabiliteit, prijsplanning en zonnevoorkeur kunnen deze start niet uitstellen. De bestaande fysieke ruimte, actuele bronnen, apparaatvoorwaarden, regelmodus en commandobescherming blijven vereist.

**Begin met [BETA78_INSTELLEN.md](docs/BETA78_INSTELLEN.md).** Geen extra installatie, sensor, solver of parallelle regelaar. Volledige werking: [ACTUELE_WERKING.md](docs/ACTUELE_WERKING.md) en **SolarPilot → Uitleg**. Actueel software-/publicatiebewijs: [TESTRESULTATEN_BETA78.md](docs/TESTRESULTATEN_BETA78.md). Oudere tests bewijzen geen geslaagde beta.78-release.

## Bestaande installatie bijwerken

1. Maak een volledige privé HA-back-up met instellingen, eigen opslag, PV-factoren, modellen, tickets, geschiedenis en userfiles. Bewaar gecontroleerde beta.77-code.
2. Geef vóór codevervanging een eigen SG-aanvraag vrij en controleer contact/lokale afloop. Onderbreek geen beschermde apparaatcyclus.
3. Update via HACS naar exact `1.0.0-beta.78` nadat releasegates en publicatie zijn geslaagd. Herstart HA volledig en herlaad browser/app volledig.
4. Controleer backend- en kaartversie apart. Behoud dezelfde entry, bindings, volgorde en geldige SG-/profiel-/split-/koelbevestigingen.
5. Controleer bij de afwasmachine de ontvangen APP-aanvraag, de oorspronkelijke geplande dag en deadline. Een nog geldige wachtende aanvraag behoudt deze gegevens; de update maakt geen nieuwe belading of verschoven deadline.
6. Na de deadline toont een geblokkeerde start de concrete oorzaak, bijvoorbeeld onvoldoende elektrische ruimte of een apparaatvoorwaarde. Na een passende nieuwe native Running-bevestiging voor dezelfde aanvraag verdwijnt de achterhaalde deadlinewaarschuwing en blijft de verbruikte aanvraag herkenbaar.
7. Controleer daarnaast Planning, PV-diagnose, Meetkwaliteit en geschiedenis. Alle functies en leerdata uit beta.77 blijven behouden.

Lokaal vervang je uitsluitend `custom_components/solar_pilot`, met behoud van userfiles en HA-opslag. Verwijder of hermaak de entry niet. Geen instellingenreset, nieuwe verplichte bron of algemene herbevestiging.

## Deadline en veilige uitvoering

Een geldige nieuwe APP-overgang geeft één belading vrij. De eenmaal vastgelegde startdeadline staat netstroom toe, ongeacht zonneoverschot, oude `solar_only`-/`allow_grid`-voorkeuren of lage batterij-SoC. Dit schrijft geen nieuwe configuratie. Een update herberekent de deadline of geplande dag van die bestaande aanvraag niet.

De deadline vergroot geen elektrische capaciteit. Werkelijke net-/fase-/kwartier-/vermogensgrenzen, bronbetrouwbaarheid, deur-/apparaatvoorwaarden, Pauze/Alleen bekijken, onbekende opdrachten en de wachttijd na een vermogensactie blijven gelden. Een nog niet verzonden START wordt na verdwijnen van een blokkering binnen de bestaande deadlinegrace opnieuw beoordeeld; standaard is die termijn 120 minuten en een expliciet ingestelde waarde blijft staan. Maximaal één native START per aanvraag; een onzekere verzonden opdracht wordt niet opnieuw verstuurd.

Een passende nieuwe native Running-bevestiging voor dezelfde aanvraag verwijdert de oude melding **startdeadline niet gehaald**. De lopende beurt bewaart de verbruikte aanvraag en beschikbare startcontext; een opdrachtverzendtijd of eerste waarneming is geen bewezen fysieke starttijd. Het programma wordt nooit onderbroken om stroom vrij te maken.

## Behouden regeling en gegevens

Panasonic blijft native geregeld met uitsluitend het bestaande toegewezen SG-contact; Wallbox blijft autonoom en read-only. SG600 W gedurende vijf continue minuten, minimum twintig minuten, korte leases en alle harde guards blijven staan. Bestaande PV-/SG-instellingen en globale net-/fase-/vermogensgrenzen veranderen niet.

PV-kalibratie per zonnestand, seizoen en kwartier, de gezamenlijke toestelplanner, chronologisch batterijadvies, lokaal onderzoek, exports, adviesrapporten en geschiedenis blijven behouden. Geen extra integratie, dienst of handmatige dependency-installatie.

## Gegevens en rollback

Voor rollback: geef de eigen SG-aanvraag vrij, controleer lokale afloop, stop beta.78 en herstel gecontroleerde beta.77-code. Behoud entry, opslag, verbruikte/afgeronde aanvragen, modellen en userfiles; een rollback mag geen START opnieuw vrijgeven. Beta.77 behoudt de bestaande dataformaten, maar mist de deadlinecorrectie en kan weer op oude zonne-/netvoorkeuren wachten.

Exact herstel vraagt code én de passende volledige privéback-up; bewaar gewenste nieuwe historie eerst. Geen twee runtimes tegelijk. Herstel geen oude onverbruikte ticketback-up bij een inmiddels gestart of afgerond programma. Volledige stappen: [BETA78_INSTELLEN.md](docs/BETA78_INSTELLEN.md).
