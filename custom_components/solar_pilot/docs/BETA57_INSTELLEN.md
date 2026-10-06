# SolarPilot 1.0.0-beta.57 — instellen en controleren

Beta.57 verdeelt één warmtepomp beter over warm water en ruimteklimaat. Het gewone warmwaterdoel kan ook tijdens de bekende sterilisatieplanning naar 60 °C. Extra warm water krijgt voorrang op veilige onderbreekbare gewone lasten. Vanaf 2500 W werkelijk bruikbaar zonneoverschot mag Panasonic AUTO beschikbaar zijn, ook zonder actuele temperatuurvraag of volledig geleerd model. Het overzicht toont bevestigde activiteit met een doorlopende blauwe rand en beschikbaarheid met een gestippelde rand.

## Basis en upgrade

Basis en rollback zijn de gecontroleerde gepubliceerde [beta.56-release](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.56): commit `cdc17f3a18d82c30a30967b044565a2819439f42`, tree `dc282d67a4cefcfed2854d83687cab9f5bcce039`. Haar 3244 tests, workflow `37316780333`, vier geslaagde jobs en vier tegen de tag gecontroleerde assets zijn basisbewijs; de nieuwe softwaregate staat afzonderlijk in `TESTRESULTATEN_BETA57.md`.

1. Maak een actuele volledige Home Assistant-back-up en bewaar beta.56 voor rollback.
2. Laat een lopende beschermde afwascyclus afwerken. Gebruik geen STOPRESET of stroomonderbreking.
3. Installeer exact `1.0.0-beta.57` via HACS, of vervang uitsluitend `custom_components/solar_pilot` met het lokale pakket. Behoud `userfiles` en Home Assistant-opslag.
4. Herstart Home Assistant volledig. Herlaad de webpagina; stop op Android de Home Assistant-app volledig en open haar opnieuw, of ververs op iOS de weergave.
5. Controleer backend én kaartversie. Open **Uitleg** en controleer beta.57 en de actuele regel-hash. Een manifestnummer alleen bewijst geen geladen kaartcode.

SolarPilot registreert de kaart en het paneel zelf. Een extra Lovelace-resource, www-bestand of dashboard-YAML is niet nodig. Geldige leerdata, bronkoppelingen, APP-aanvragen, dashboardoverrides en bestaande veiligheidsvoorwaarden blijven behouden. Er is geen algemene leerreset.

## Eén centrale voorrang

Bij een geconfigureerde boiler zet de update **Extra warm water** éénmalig achter **Auto laden** en alle bestaande afwasrijen, vóór gewone flexibele verbruikers. Ook gewone rijen die vroeger boven de Wallbox stonden schuiven daarbij onder extra warm water. Controleer de nieuwe lijst onder **Voorrang**. Opgeslagen toestemming om autovermogen te benutten blijft bewaard, maar heeft onder Auto laden geen werking. Latere bewust opgeslagen wijzigingen worden niet opnieuw door deze migratie vervangen.

| Regel | Wat extra 60 °C mag doen |
| --- | --- |
| Veiligheid en noodzakelijk comfort | Altijd beschermd |
| Afwasmachine | Geen lopend programma stoppen; een passend startklare beurt krijgt eerst de kans |
| Ruimteverwarming/koeling | Geen capaciteit afpakken door zones hiervoor uit te zetten |
| Wallbox | Alleen de echte restzon gebruiken; geen EV-vermogen bijtellen of laadopdracht sturen |
| Gewone onderbreekbare eigen last | Lager in de lijst veilig laten wijken als werkelijk nodig |
| Handmatige last, boost, deadline, minimumlooptijd of onbetrouwbare bron | Bestaande bescherming respecteren |

Een last wijkt alleen wanneer SolarPilot haar zelf beheert, haar echte vermogen vers gemeten is en veilig stoppen is toegestaan. De mogelijke zonne-ruimte moet eerst gedurende de ingestelde boilerstabiliteit geldig blijven. Daarna volgt hoogstens één stopopdracht. Pas bevestigde UIT, nieuwe P1-rapportage en verse PV maken werkelijk vrijgekomen ruimte beschikbaar. De gewone boilerstabiliteit en rust tussen doelopdrachten blijven daarna gelden. Aangevraagd stopvermogen telt nooit alvast als injectie. Als er genoeg is voor beide, blijft de gewone last werken.

## Warm water: 3000 W en maandagsterilisatie

Extra warm water start standaard vanaf **3000 W** werkelijk bruikbaar overschot; exact 3000 W telt mee. De vroegere gerichte drempelmigratie van 3500 W blijft éénmalig; eigen waarden blijven behouden. De afzonderlijke elektrische raming blijft standaard **3200 W** en fase-/piekgrenzen blijven gelden. Totale paneelproductie of vermogen waarmee de auto laadt is geen restoverschot.

De boiler behoudt de normale voorwaarden: module en bediening vrijgegeven, **Automatisch regelen**, betrouwbare bronnen, passend native doelbereik, geen blokkering door echte koeling/ruimteactie of fabrikant-/handmatige bescherming, stabiele zon en een afgeronde opdrachtrust. Standaard zijn de twee afzonderlijke tijden vijf minuten stabiliteit en dertig minuten sinds de laatste werkelijk verstuurde doelopdracht. Blijvend geldig bewijs wordt niet alleen door die opdrachtrust opnieuw gewist.

De bekende sterilisatieplanning, standaard maandag om 12:00 naar 62 °C, is vanaf beta.57 **informatie**. Panasonic kan de cyclus intern uitvoeren zonder het gewone HA/display-doel te verhogen. Het oude klokvenster 11:45–15:00 blokkeert daarom geen gewone 60 °C-opdracht. SolarPilot verandert de sterilisatie niet; Panasonic kan haar intern voorrang geven. Een echt gekoppelde actieve hygiënebron, onbetrouwbare vereiste bescherming, Powerful, Force DHW, gewijzigd eigen doel of pending opdracht houdt wel haar afzonderlijke guard.

Houd **SolarPilot-voorstel**, **gemeld Panasonic-doel** en **gemeten tanktemperatuur** apart. Een voorstel is nog geen write. Een werkelijk gemeld 60 °C-doel betekent een hogere instelling, geen bewijs dat het vat opwarmt of al 60 °C is. Een gewone doelwrite forceert geen compressorstart. De normale 50 °C, bewaakte 46 °C en Panasonic-differentie -5 °C blijven behouden; het bewaakte minimum is geen gegarandeerde native herstarttemperatuur.

## Eén warmtepomp en de juiste meter

Controleer onder **Warmte & comfort → Koppelingen** de optionele elektrische W/kW-bron en **Wat meet deze vermogensmeter?**. Kies **De hele warmtepomp** voor het gezamenlijke verbruik van ruimteklimaat en tapwater. Dat is de standaard. Kies **Uitsluitend de boiler** alleen bij een werkelijk exclusieve tankmeter. Een kWh-teller of vermogen dat elders al als ander toestel wordt geboekt is ongeschikt.

Het bestaande verbruik van dezelfde warmtepomp staat al eenmaal in P1. SolarPilot reserveert voor nieuwe mogelijke belasting alleen het ontbrekende deel van de grootste passende warmtepomptaak, in plaats van ruimteklimaat en tapwater als twee volledige apparaten op te tellen. Zonder passende verse meting blijft de raming conservatief. Batterijontlading is geen zon. Na een fysieke wijziging zijn nieuwe P1, verse geldige PV en de gewone meetrust nodig.

Een gedeelde warmtepompmeter bewijst geen specifieke tankopwarming. Voor het vasthouden van een bewezen eigen hoog tankdoel mag zij alleen passend compenseren wanneer ruimtebedrijf betrouwbaar inactief is. Bij echte of onzekere ruimteactie krijgt tapwater hierdoor geen dubbel stroomkrediet. Een exclusieve tankmeter en native tapwateractie zijn afzonderlijk opwarmbewijs.

## Ruimteklimaat: zon of noodzakelijke comfortvraag

Laat per zone **Handmatig bedienen: Uit** staan voor autonome AUTO/UIT-regeling. Aan bewaart de expliciete dashboardkeuze **AUTO / UIT** over herstarts. Dashboard-UIT blijft leidend, ook bij veel zon. Een externe native wijziging krijgt de bestaande tijdelijke gebruikersrust. Bronproblemen, pending/onzekere opdrachten, minimum aan-/uittijden en fabrikantbescherming blijven gelden. Oudere expliciet uitgezette autonome zonebediening wordt niet stilzwijgend aangezet.

Bij **2500 W** bruikbaar echt restoverschot gedurende **60 seconden**, met nieuwe echte P1- en PV-rapportage, mag AUTO beschikbaar worden. Dit vraagt geen temperatuurvraag of 55%-modelscore. Het native programma moet wel vers en bekend zijn: HEAT, COOL, hun AUTO-varianten of bekende UIT zijn geldige context. Unknown is geen startvrijgave. Panasonic beslist vervolgens zelf of verwarmen/koelen nodig is; AUTO mag idle blijven.

Een later bevestigde eigen zonne-AUTO houdt haar beschikbaarheid tot **2000 W**. Haar verse gezamenlijke warmtepompverbruik wordt daarvoor hoogstens eenmaal teruggeteld, begrensd door echte PV-productie. Dit voorkomt dat haar eigen stroomvraag onmiddellijk een nieuwe UIT veroorzaakt. Een nieuwe start vanuit UIT krijgt deze terugtelling niet. Wanneer zon wegvalt, bepalen gewone comfortbewaking, verantwoord voorspellend bewijs en minimumtijden of AUTO nog nodig is.

Het gewone comfortpad blijft afzonderlijk: een warmtevraag geeft geen autonome warmtestart bij een koelprogramma en omgekeerd. Een zachte nieuwe vraag wacht standaard tien minuten plus een nieuwe native rapportage; harde relevante comfortbehoefte en verantwoord urgente voorspelling behouden hun bestaande route. Leren gebruikt normale comfortabele AUTO-/UIT-perioden. Veel passieve samples bewijzen geen geleerde koelrespons of tweedaagse bouwschilvoorkoeling.

SolarPilot stuurt alleen HA **AUTO/UIT**. De onderliggende Aquarea-adapter kan dit vertalen naar globale operationMode8/0; een ongewijzigd bestaand HEAT/COOL-programma is geen gegarandeerd fysiek effect. Het ruimtedoel wordt niet gewijzigd en er komt geen directe HEAT/COOL-, Powerful- of Force-DHW-opdracht bij.

## Het overzicht lezen

Op **Overzicht → Wat gebeurt er en waarom?** staan stand, start-/wachtreden en laatste vastgelegde verandering op één plek. Technische waarden blijven achter **Details**.

| Uiterlijk | Betekenis |
| --- | --- |
| Doorlopende blauwe rand — **Bevestigd actief** | Bevestigd aan/programma, actuele verwarm-/koel-/tapwateractie of echte lading |
| Gestippelde blauwe rand — **Beschikbaar of extra voorraad ingesteld** | AUTO beschikbaar zonder gemelde actie, of werkelijk hoger gemeld tankdoel |
| Grijs — **Activiteit onbekend** / **Niet bereikbaar** | Onvoldoende verse bruikbare terugmelding |

Een hoog voorstel krijgt geen actieve rand. AUTO op zichzelf bewijst geen compressoractie. Een gedeelde W-meter bewijst geen specifieke tankverwarming. Ook een blauw actief apparaat kan gedeeltelijk netstroom gebruiken; de rand is geen zonne-energiegarantie.

## Analyse, teststatus en rollback

De volledige beschikbare zeven dagen blijven als lokale beheerderdownload **JSON.GZ** beschikbaar. Privacyfilters, versie per nieuw record en begrensde bewaartermijnen blijven gelden; ontbrekende oude gegevens worden niet verzonnen. Deze werksessie voert geen live Home Assistant- of fysieke toestelactie uit. Softwaregate en publicatie-/pakketcontrole staan in `TESTRESULTATEN_BETA57.md`; een release bewijst geen geladen backend, telefoonapp of fysieke tankrespons.

Rollback: **Pauze → beschermde cycli afwerken → onveranderlijke beta.56-release of passende volledige back-up herstellen → Home Assistant herstarten → webpagina/app opnieuw openen → backend/kaart, bronnen, eigendom en beveiligingen controleren**. Beta.56 mist de nieuwe gezamenlijke begroting, zonne-AUTO, prioriteitsreclaim en activiteitenranden en gebruikt nog het oude klokvenster. Programmabestanden terugzetten herstelt de gemigreerde opgeslagen prioriteit en meterscope niet vanzelf. Controleer de effectieve waarden of herstel de volledige bijbehorende back-up. Gebruik geen fysieke proefopdracht om update of rollback af te dwingen.
