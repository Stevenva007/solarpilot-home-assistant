# SolarPilot beta.35 — centrale voorrang en Export

**Versie:** 1.0.0-beta.35 · **Datum:** 30 september 2026  
**Basis:** het aangeleverde volledige beta.34-pakket. Deze update is cumulatief.

## Eerst weten

Installeren zet je bestaande voorrang **niet** terug op standaardwaarden. Zonder bevestigde wijziging in de nieuwe lijst blijven de bestaande verdeling, toestelkeuzes en regelrechten leidend. Temperaturen, minimumlooptijden, APP-aanvragen, deadlinebeleid en leerdata worden niet gereset. De update activeert geen nieuwe fysieke ruimteverwarmingsregeling.

Het pakket is lokaal gebouwd en getest. Het is niet naar GitHub gepubliceerd en niet op je Home Assistant geïnstalleerd. Er is geen praktijktest op je echte toestellen uitgevoerd.

## Installeren over beta.34

Maak eerst een volledige Home Assistant-back-up. Laat een eventuele lopende toestelopdracht of vermogensoverdracht afronden voordat je herstart. Gebruik de gewone software-updateprocedure; je hoeft SolarPilot niet te verwijderen of opnieuw toe te voegen.

Voor een handmatige installatie: pak het ZIP-bestand uit en kopieer **de inhoud van `custom_components/solar_pilot/`** naar `/config/custom_components/solar_pilot/`, met overschrijven van de programmabestanden. Behoud je bestaande **`userfiles/` met eventuele privébestanden**. Verwijder geen `.storage`-bestanden en geen bestaande integratieconfiguratie.

Voor publicatie naar je eigen GitHub/HACS-repository: plaats de inhoud van de buitenste pakketmap in de repositoryroot, niet de buitenste map zelf. Publiceer pas na je gebruikelijke repository-/HACS-controles. Het meegeleverde ZIP-bestand is een repositorypakket, geen melding dat HACS de release al aanbiedt.

Herstart Home Assistant. Controleer daarna dat SolarPilot **1.0.0-beta.35** toont. Ververs de browser volledig wanneer de oude kaart zichtbaar blijft. De actuele versie hoort ook op de tab Uitleg te staan. Een software-update vraagt een herstart; later instellingen wijzigen blijft zoals in beta.34 zonder volledige herlading mogelijk.

## Voorrang bekijken

De nieuwe tab **Voorrang** bevat twee aansluitende delen. Bovenaan zie je wat beschermd blijft: beveiliging en hygiëne, gewoon warm water, noodzakelijke avondvoorraad en gewoon ruimtecomfort. Daaronder staan de flexibele verbruikers, **Auto laden · Wallbox** en **Extra boilerwarmte** met het werkelijk ingestelde extra doel.

Het bekende voorkeursprofiel blijft behouden: warmtepompcomfort vóór afwas; afwas vóór Wallbox; Wallbox vóór de lager geplaatste verbruikers zoals de ontvochtiger. Extra boilerwarmte is afzonderlijk van normaal warm water en blijft na Wallbox en voorkeur-afwas. De lijst leest bestaande instellingen, niet een nieuw hardgecodeerd huisprofiel.

## Voorrang wijzigen

Open **Volgorde aanpassen** als beheerder. Sleep rijen op desktop of gebruik de pijlen omhoog en omlaag. De pijlen werken ook op mobiel en met toetsenbord. Per verbruiker staat **Mag de auto minder laten laden?** met de keuzes **Ja, als het veilig kan** en **Nee**.

Een toestemming is geen bewijs dat die mogelijkheid nu beschikbaar is. Het toestel moet vóór de Wallbox staan; metingen, bevestigde zonnelaadsessie en zijn technische adapter moeten de overname toelaten. Een toestel achter de Wallbox gebruikt geen autolaadvermogen, ook wanneer Ja als toekomstige toestemming bewaard is. De AEG heeft zijn eigen beschermde startroute. Handmatig of onzeker autoladen geeft geen overdraagbaar EV-vermogen.

De vaste bescherming is zichtbaar maar niet versleepbaar. Extra boilerwarmte kan tussen andere lagere verbruikers worden verschoven, **niet vóór de Wallbox of een voorkeur-afwasmachine**. Deze zonnebuffer krijgt nooit EV-vermogen toegewezen.

Vink de bevestiging aan en kies **Wijzigingen opslaan**. Slepen alleen doet niets aan de regeling. Ongewijzigd opslaan activeert geen andere rangorde. Na een echte opgeslagen wijziging wordt de centrale lijst leidend bij de volgende gewone regelcontrole. De planner en de gewone toestelverdeling gebruiken dezelfde toestelrangorde; passende kleinere lasten mogen onbenutte restjes blijven gebruiken.

Een lopende minimale draaitijd wordt niet afgeknipt en een gestart afwasprogramma wordt niet gestopt. Opslaan verstuurt geen rechtstreeks toestel- of Wallbox-commando. Een opdracht die nog bevestigd moet worden of een lopende vermogensoverdracht moet eerst afgerond zijn voordat een nieuwe volgorde wordt geaccepteerd.

## Nieuwe of vervangen toestellen

Via **Toestel toevoegen of beheren** ga je naar het bestaande toestelbeheer. Een nieuwe gewone verbruiker verschijnt onderaan de actieve centrale lijst; een nieuw voorkeur-AEG-profiel vóór de Wallbox. Je kunt de nieuwe rij meteen verplaatsen. Toevoegen of vervangen maakt het toestel niet automatisch actief: een nieuwe identiteit begint **Uitgesloten** en vereist bewuste vrijgave nadat de koppeling gecontroleerd is.

Verwijderde identiteiten verdwijnen uit de actieve lijst. Vervangen erft geen oude starttickets, Auto-deelname, bronkoppelingen of meetprofielen. Het bestaande archief- en bewaarbeleid blijft gelden.

## Niet-opgeslagen wijzigingen en oude instellingen

Live metingen mogen je geopende editor, gekozen volgorde, toestemming en bevestiging niet wissen. Bij wijzigingen vanuit een andere sessie of een gewijzigd toestelbestand wordt een ouder concept afgewezen. Het blijft zichtbaar zodat je je keuzes niet stilzwijgend kwijtraakt. **Lijst vernieuwen** vraagt eerst of je een gewijzigd concept wilt weggooien.

Bij **Opslag niet bevestigd** na een verbindingsfout kan een server de wijziging al ontvangen hebben. Vernieuw eerst de lijst en controleer de werkelijke opslag voordat je opnieuw bevestigt.

Na de eerste centrale wijziging worden de oudere rangorde-/overnametoestemmingsvelden in de toestelwizard verborgen. De oude getallen blijven voor migratie en onderzoek bewaard, maar zijn niet langer leidend. Een oude open wizard, prioriteitsgetal-entiteit of globale voorrangsschakelaar kan de centrale lijst niet overschrijven; zo'n wijziging verwijst terug naar Voorrang. Bestaande eigen automatiseringen die deze oude regelaars wijzigen moeten daarom worden nagekeken vóór je de centrale lijst activeert.

## Eén Export-pagina

Open **Export → Export samenstellen**. Kies 1 uur, 24 uur of 7 dagen. Het lokale JSON-bestand bundelt de actuele/effectieve configuratie, centrale volgorde en toestemmingen, bewaarde metingen, beslissingen, fouten, plannings-/leerdata en relevante status voor de geconfigureerde onderdelen. Niet-bewaarde historie wordt niet alsnog uitgevonden of geïmporteerd.

Namen en entiteiten worden standaard gepseudonimiseerd. Je kunt expliciet echte namen opnemen. Het bestand bevat nog steeds tijdstippen en gebruikspatronen; controleer het vóór delen. Er is geen automatische upload en er wordt geen toestel bediend. Dit onderzoeksbestand vervangt **geen herstelbare Home Assistant-back-up**.

## Controle na installatie

Controleer eerst zonder te verplaatsen of de bestaande volgorde, temperaturen, Auto/Uitgesloten-keuzes, APP-aanvraag en Wallbox-status kloppen. Controleer de actuele uitleg op versie beta.35. Probeer de editor te openen en te annuleren: de regeling mag daardoor niet veranderen.

Maak pas daarna een gewenste beperkte wijziging met bevestiging en controleer de eerstvolgende normale beslissingen. Bewaar bij een onverwacht resultaat een Export-bestand met het relevante tijdvenster. Een softwaretest is geen meting aan de echte installatie en vervangt deze acceptatiecontrole niet.

## Volledige werking en testverslag

De volledige actuele uitleg staat op **Uitleg** in Home Assistant en in `docs/ACTUELE_WERKING.md`. Het lokale testverslag staat in `docs/TESTRESULTATEN_BETA35.md`. Oudere BETA-documenten beschrijven historische releases; voor de huidige werking is uitsluitend de actuele uitleg leidend.
