# SolarPilot 1.0.0-beta.53 — instellen en controleren

Beta.53 voorkomt dat één tijdelijk onbeschikbaar eerder beheerd toestel de gewone herstartcontrole voor alle toestellen laat wachten. SolarPilot zet alleen dat toestel tijdelijk opzij, blijft automatisch controleren en laat de overige beschikbare toestellen onder geldige globale voorwaarden hervatten. Na echte betrouwbare terugmelding wordt het toestel vanzelf opnieuw beoordeeld. Deelname, prioriteit, minimumlooptijden en beschermde programma’s blijven behouden.

## Bronbasis en gegevensbehoud

De codebasis is de gepubliceerde beta.52 op commit `80402cd03b213334608d4ca0956ce662c5021216`, tree `d1cb08369429a66773ad226c2642baac86aecf46`. Haar onveranderlijke release en gecontroleerde pakketten zijn de rollbackbasis. Updates zijn cumulatief: geldige instellingen, toestelbindingen, prioriteiten, modellen, historiek en APP-aanvragen blijven behouden. Er is geen algemene reset, kortere bronversheid of nieuwe fysieke toestemming nodig.

## Upgrade

1. Maak een actuele volledige Home Assistant-back-up en bewaar de gecontroleerde beta.52-release.
2. Laat beschermde afwas- of andere cycli afwerken. Gebruik geen STOPRESET voor de update.
3. Installeer exact `1.0.0-beta.53` via HACS zodra de release beschikbaar is, of vervang uitsluitend `custom_components/solar_pilot` met het lokale pakket. Behoud bestaande `userfiles` en Home Assistant-opslag.
4. Herstart Home Assistant volledig. Herlaad daarna de webpagina; op Android stop je de Home Assistant-app volledig en open je haar opnieuw, op iOS kun je de weergave naar beneden trekken om te verversen.
5. Controleer backendversie en geladen kaart afzonderlijk. Open **Uitleg** en controleer beta.53 en hash `edf7d3b110363702`. Een download of manifestnummer bewijst geen geladen kaartcode.

SolarPilot registreert haar frontend zelf. Een extra Lovelace-resource, www-bestand of dashboard-YAML is niet nodig.

## Wat gebeurt er bij een onbeschikbaar toestel?

| Situatie | Automatische afhandeling |
| --- | --- |
| Een eerder beheerd toestel heeft ontbrekende, restored of onbeschikbare bediening | Alleen dit toestel wordt tijdelijk buiten de gewone regeling gehouden. Geen blinde ON/OFF, geen oude opdrachtreplay. SolarPilot bewaart de eerdere beheerinformatie en controleert opnieuw tijdens gewone regelrondes. |
| Andere toestellen en globale meetbronnen zijn betrouwbaar | De opgeslagen automatische modus kan voor die toestellen hervatten, mits actuele zon, reserves, net-, fase-, piek- en alle eigen voorwaarden dit toelaten. |
| Het wachtende toestel meldt weer betrouwbaar eigen ON | SolarPilot herkent de lopende last zonder nieuwe start. De minimumlooptijd wordt conservatief vanaf de nieuwe waarneming beschermd. |
| Het wachtende toestel meldt betrouwbaar OFF | Oud eigendom wordt losgelaten. Opnieuw starten volgt de gewone deelname, prioriteit, minimum-uittijd en actuele startvoorwaarden. |
| Een numeriek toestel heeft een ander doel gekregen | SolarPilot overschrijft dit doel niet en behoudt de bestaande handmatige rusttijd. |
| Je kiest later Alleen bekijken of Pauze | Bronterugkeer zet SolarPilot niet alsnog naar Auto. De bewuste moduskeuze blijft gelden. |
| Er is een echte opdrachtfout of onzekere START | De bestaande fout-/bevestigingsvoorwaarden blijven gelden. Deze update geeft geen algemene foutreset of tweede START. |

De tijdelijke bescherming verandert de instelling **Automatisch / Uitgesloten** en de centrale prioriteit niet. Je hoeft het toestel dus niet handmatig uit de lijst te verwijderen, zijn instellingen te wijzigen of op **Controle afronden** te drukken om de overige toestellen te laten werken. Een verkeerde vereiste bronkoppeling moet wel gecorrigeerd worden; betrouwbaar opnieuw lezen kan een verkeerde configuratie niet repareren.

## Waarom kan een ander toestel toch nog wachten?

Een onbereikbaar toestel kan nog stroom gebruiken of later opnieuw gaan vragen. SolarPilot rekent onbekend vermogen niet als 0 W. Werkelijk huidig verbruik staat al in de P1-meting. Daarnaast blijft een conservatieve reserve gelden voor mogelijk niet gemeten of later toenemend verbruik van de wachtende last. Alleen een verse betrouwbare exclusieve vermogensmeting kan het reeds in P1 opgenomen deel aantonen; een geschatte, oude of ontbrekende meting levert geen vrij vermogen op.

De reserve verlaagt de beschikbare ruimte voor gewone toestellen, warm water en batterijladen. Een lage momentmeting is geen garantie op blijvend laag verbruik. Daardoor kunnen lasten wachten tot er na de reserve echt voldoende ruimte overblijft. Dit is een actuele vermogensvoorwaarde; één ontbrekende toestelstatus houdt de overige herstartcontrole niet meer onnodig vast.

Globale ongeldige P1- of veiligheidsbronnen, actieve elektrische begrenzing, echte fouten en pending/onzekere opdrachten kunnen nog steeds nieuwe starts of verhogingen blokkeren. Bij actieve fasebewaking blijven ontbrekende of ongeldige actuele fasemetingen blokkerend, ook wanneer een aangeleerde fasekaart wordt gebruikt. Beschermde afwascycli worden niet gestopt; de Wallbox blijft volledig read-only.

## Meldingen en diagnose

De kaart noemt welke toestellen tijdelijk wachten, waarom en hoeveel reserve wordt aangehouden. Zij geeft aan dat automatisch opnieuw wordt gecontroleerd en dat de overige toestellen hun eigen voorwaarden blijven volgen. Bronterugkeer ruimt de tijdelijke bescherming automatisch op; **Controle afronden** blijft uitsluitend voor een echte fout of vereiste handmatige controle.

Deze update repareert geen fysieke verbindingsstoring. Controleer bij langdurige onbeschikbaarheid het genoemde toestel en zijn gekoppelde HA-integratie. Gebruik **Export → Export samenstellen** voor een nieuwe actuele analyse. De volledige configuratie, gekoppelde brongegevens, individuele wachtstatus en reserve worden meegenomen voor zover aanwezig. Privacyfilters en pseudoniemen blijven behouden; plaats privé-analyses niet op publieke GitHub.

## Behouden boiler- en toestelregels

Zonnestabiliteit en de minimumtijd sinds de laatste werkelijk verstuurde boilerdoelopdracht blijven afzonderlijk lopen. Een geldig afgeronde stabiliteitscontrole begint niet opnieuw alleen vanwege opdrachtrust. Het standaard interval van 1800 seconden sinds de laatste opdracht, koeling, hygiëne, eigendom, doelbevestiging en zichtbare uitvoeringswachtreden blijven gelden. Voorstel, gemeld Panasonic-doel en gemeten tanktemperatuur blijven apart.

Handmatige OFF-zones blijven uit tot expliciete gebruikers-AUTO. Beschermde cycli worden niet onderbroken; onzekere opdrachten worden niet blind herhaald. Geldige leerdata en alle bestaande comfort- en prioriteitsgrenzen blijven behouden. Geen Force DHW, Powerful, extra APP-aanvraag, Wallbox-opdracht of algemene datareset.

## Teststatus en rollback

De definitieve softwaregate staat in `TESTRESULTATEN_BETA53.md`. HA-API-/DOM-doubles bewijzen softwaregedrag, niet een fysieke verbinding of live installatie. Er is in deze werksessie geen live Home Assistant-toegang of fysieke toestelactie uitgevoerd.

Rollback: **Pauze → beschermde cycli afwerken → onveranderlijke beta.52-release of gecontroleerde volledige back-up herstellen → Home Assistant herstarten → webpagina/app opnieuw openen → backend/kaart, actuele bronnen, eigendom en beveiligingen controleren**. Beta.52 behoudt de correcte bronclassificatie en volledige export, maar kan bij ontbrekende eerder beheerde status nog globaal op herstartcontrole wachten. Historische releasedocumenten blijven onveranderd; `OVERDRACHT.md` beschrijft de huidige bron.
