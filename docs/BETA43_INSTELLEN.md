# SolarPilot 1.0.0-beta.43 — instellen, controleren en rollback

Beta.43 is een cumulatieve uitlegbaarheids- en veiligheidsrelease. Zij maakt actuele activiteit, Wallbox-waarnemingen en automatische waardeschattingen controleerbaar, beveiligt navigatie met open formulieren en voegt een optionele maandagdeadline voor de AEG-afwasmachine toe. Zij geeft de Wallbox geen actuatorrecht en versoepelt geen AEG-, klimaat-, boiler- of elektrische beveiliging.

## Bewezen uitgangspunt

Vóór deze upgrade is op de echte installatie gecontroleerd dat Home Assistant Core **2026.9.4** SolarPilot **1.0.0-beta.42** werkelijk had geladen; backend en kaart zijn afzonderlijk bevestigd. Dat is de bewezen basis. Het is geen bewijs dat beta.43 al gepubliceerd, geladen of fysiek geaccepteerd is.

## Vooraf

1. Maak een volledige Home Assistant-back-up.
2. Kies een moment zonder actieve beschermde afwas- of andere niet-onderbreekbare cyclus.
3. Laat een lopende cyclus normaal afwerken. Gebruik geen STOPRESET om voor de update ruimte te maken.
4. Noteer de huidige globale modus, per-toestelmodus, actuele APP-aanvraag en boiler-/klimaatstatus.

## Upgrade

1. Installeer `1.0.0-beta.43` via de bestaande HACS-repository.
2. Herstart Home Assistant volledig.
3. Controleer in de SolarPilot-status dat de geladen backendversie exact `1.0.0-beta.43` is.
4. Vernieuw de browser geforceerd en controleer dat ook de kaart beta.43 toont.
5. Begin de controles in **Alleen bekijken** of **Pauze**. Geef niet meerdere nieuwe fysieke rechten tegelijk vrij.

## Nu actief eerlijk lezen

**Nu actief** gebruikt de werkelijk waargenomen status van een gekoppelde bron. Een ingestelde modus of gevraagde planning alleen is geen activiteit. Bij vermogen blijft zichtbaar of de waarde gemeten of geschat is. Een actieve regel betekent niet dat het toestel uitsluitend zonnestroom gebruikt of dat SolarPilot de start veroorzaakte.

Controleer na de upgrade daarom:

- alleen werkelijk actieve toestellen staan in de lijst;
- een ontbrekende, oude of ongeldige status niet als actief verschijnt;
- een helper of afgeleide waarde als geschat blijft aangeduid;
- een exclusieve, actuele vermogensmeter als gemeten kan worden aangeduid.

## Wallbox: waarnemen zonder bedienen

De Wallbox blijft volledig read-only. De actuele bekende native status kan uitleggen waarop de laadpaal nu wacht. SolarPilot bewaart lokaal maximaal dertig waargenomen eindes van laadperiodes.

Een historische native stopreden geldt uitsluitend wanneer de exacte bekende status ná het laatste laadrapport en binnen vijf seconden van het stop-vermogensrapport is ontvangen. Een meetgat, Home Assistant-herstart, oude status of toekomstige/onlogische opgeslagen tijd wordt niet tot een bevestigde oorzaak gemaakt. De getoonde tijden zijn Home Assistant-waarnemingen en hoeven niet exact het fysieke schakelogenblik te zijn.

Controleer dat geen SolarPilot-servicecall de Wallbox start, stopt of van laadstroom, fase of modus verandert. Onbekende of oude broninformatie blijft fail-closed.

## Veilige browsernavigatie

Browser **Terug** en **Vooruit** herstellen alleen SolarPilot-schermen en dialogen binnen dezelfde Home Assistant-URL. SolarPilot past de Home Assistant-router niet aan.

- Een ongewijzigd venster mag veilig sluiten en terugkeren.
- Een formulier met niet-opgeslagen wijzigingen moet eerst bevestiging vragen.
- Tijdens opslaan of een andere lopende actie mag navigatie het venster niet onderbreken.
- Formulierinhoud en fysieke opdrachten worden niet automatisch opnieuw afgespeeld.

## Automatisch voordeel is een schatting

De automatische-voordeelweergave begint voorwaarts vanaf de eigen eerste bruikbare meetperiode en bewaart maximaal negentig kalenderdagen. Alleen een door SolarPilot beheerde, werkelijk actieve Auto-verbruiker kan meetellen. Handmatige starts, boosts, autonoom autoladen, boiler en klimaat zijn uitgesloten.

Per bruikbaar interval wordt de toegerekende zonnestroom gewaardeerd tegen het verschil tussen afnameprijs en injectievergoeding. Netafname en batterijontlading worden eerst conservatief toegerekend. Ontbrekende meters of prijzen zijn geen nul en eerdere perioden worden niet gereconstrueerd. Het resultaat is een **opportunity-value-schatting**, geen bewezen extra besparing door SolarPilot en geen bedrag dat nogmaals van de elektriciteitskost mag worden afgetrokken.

## Avondvoorraad en actueel EV-zonnevermogen

De beschermde avondvoorraad blijft begrensd tot de ingestelde voorraadlimiet en maximaal 55 °C. Zij mag het actuele laadvermogen van de auto uitsluitend als voorwaardelijk vrijmaakbaar zonnevermogen meewegen wanneer de native Full Solar-sessie expliciet ingeschakeld, verbonden en vragend is, het vermogen minstens 50 W bedraagt en zowel sessiestatus als vermogen hoogstens 120 seconden oud zijn.

Handmatig laden en onbekende, strijdige of oude sessies geven geen EV-krediet. Extra opwarming naar 60 °C krijgt dit krediet nooit en blijft afhankelijk van werkelijke restinjectie. Comfortgrens, actieve of verwachte koeling, fabrikantsterilisatie en alle overige boiler- en elektrische beveiligingen blijven hoger. SolarPilot stuurt de Wallbox ook voor deze functie niet aan.

## Optionele maandagdeadline afwasmachine

Onder de planning van het AEG-profiel staat **Maandag: afwijkende uiterste starttijd (optioneel)**.

- Leeg betekent ook op maandag de gewone deadline, standaard `13:00`.
- `10:00` wijzigt uitsluitend maandag; dinsdag tot en met zondag behouden de gewone deadline.
- Een zondagse aanvraag na de gewone grens wordt voor maandag gepland en gebruikt dan de maandagdeadline.
- De Home Assistant-tijdzone blijft leidend, ook bij de overgang tussen zomer- en wintertijd.
- De bestaande toestemming voor netstroom op de deadline en alle programma-, deur-, verbinding-, prioriteits- en elektrische controles blijven verplicht.

Een bestaand APP-ticket houdt bij de update zijn vastgelegde dag en deadline. Alleen wanneer je expliciet bevestigt dat de wijziging op het huidige verzoek mag worden toegepast, wordt de deadline voor dezelfde geplande dag herberekend. Dat maakt geen nieuw ticket en verstuurt geen START. Tijdens een lopende beschermde cyclus wordt de instellingswijziging pas na het bevestigde einde toegepast.

## APP-start blijft eenmalig en fysiek

Een update of herstart bewaart een bestaand ticket maar maakt er geen nieuw. APP/remote-start dat bij startup al exact `Enabled` is, geldt niet als nieuwe aanvraag. Voor iedere nieuwe belading moet de fysieke toestand eerst uit en daarna opnieuw naar exact `Enabled` gaan.

SolarPilot verstuurt maximaal één native START per aanvraag. Deur gesloten, Ready To Start, geldig programma, actuele verbinding, bruikbare alarmcontrole indien gekoppeld, globale en per-toesteltoestemming en elektrische ruimte blijven verplicht. Een onzekere START wordt niet blind herhaald en een lopende cyclus blijft beschermd.

## Veilige activering

Behoud de bestaande lagen:

1. eerst globaal **Alleen bekijken**;
2. daarna alleen indien gecontroleerd globaal **Automatisch regelen**;
3. per toestel afzonderlijk **Uitgesloten** of **Auto**;
4. afzonderlijke bron-, meter-, eigenaarschap- en veiligheidsbevestiging.

Laat de oude afzonderlijke 60/50-boilerautomatiseringen uit zolang SolarPilot de gecontroleerde regelaar is. Een update, navigatieactie, deadlinewijziging, geschiedenisregistratie of waardeschatting geeft op zichzelf geen fysiek recht.

## Liveacceptatie na installatie

- Backend en kaart tonen werkelijk `1.0.0-beta.43` na volledige herstart en cache-refresh.
- **Nu actief** en de bronkwaliteit volgen de echte actuele states.
- Wallbox-wachtuitleg en een later waargenomen einde blijven read-only en verzinnen bij meetgaten geen oorzaak.
- Browsernavigatie bewaart de bevestigings- en busybeveiliging.
- Avondvoorraad gebruikt alleen een actuele bevestigde Full Solar-sessie binnen de 55 °C-grens; manueel/onbekend/oud laden en extra 60 °C krijgen geen EV-krediet.
- De maandaginstelling toont leeg als gewone 13:00 en kan bewust op 10:00 worden gezet zonder ticket of START te maken.
- Een bestaand ticket overleeft de update; APP dat bij startup al Enabled is, wordt niet opnieuw gewapend.
- De bestaande koelroute en onmiddellijke DHW-terugval tijdens een echte actieve koelcyclus blijven een afzonderlijke fysieke acceptatiestap.
- Een volledig nieuwe AEG-belading met APP uit→aan, maximaal één START en bescherming tot End Of Cycle blijft een afzonderlijke fysieke acceptatiestap.

Deze handleiding beweert niet dat de laatste twee fysieke scenario's al zijn uitgevoerd.

## Rollback

1. Zet SolarPilot op **Pauze**.
2. Laat een lopende beschermde cyclus veilig afwerken; verstuur geen STOPRESET vanuit SolarPilot.
3. Herstel de volledige back-up of installeer de geregistreerde beta.42 opnieuw.
4. Herstart Home Assistant en controleer de werkelijk geladen backend- en kaartversie.
5. Controleer bestaande APP-tickets, maandagdeadline, Voorrang, boiler-/klimaateigendom en Wallbox fail-closed gedrag opnieuw voordat je Automatisch regelen gebruikt.

Zie `TESTRESULTATEN_BETA43.md` voor de werkelijk uitgevoerde softwarecontrole en het liveacceptatieplan.
