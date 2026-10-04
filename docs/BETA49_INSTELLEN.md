# SolarPilot 1.0.0-beta.49 — instellen en controleren

Beta.49 bouwt voort op de werkelijk gepubliceerde beta.48 en herstelt aanvullende bewezen fouten in batterijopdrachtbeheer, forecast-/tijdroosterbewijs, export en veilig opstarten/herladen. Er is geen nieuwe actuatortoestemming, comfortgrens of algemene leerreset. Alle beta.48-regels voor handmatige OFF, relevante klimaatmodelzekerheid, herstartherstel, DHW, AEG en Wallbox blijven gelden.

## Bronbasis en gegevensbehoud

De codebasis is beta.48 op commit `a7df7688806ee128242058631a000c640e1243dd`, tree `11ade811d25f296ab84d6e0209776a615ab0099d`. De onveranderlijke beta.48-release, haar geslaagde publicatieworkflow en gecontroleerde pakketten zijn de rollbackbasis. Geldige instellingen, toestelbindings, klimaat-/PV-/faseprofielen, historische gegevens en APP-aanvragen blijven behouden. Ongeldige afzonderlijke opgeslagen records worden veilig afgehandeld zonder geldige andere records te wissen. Een afgebroken integratiestart mag geen gedeeltelijk geladen toestand over goede opslag schrijven.

## Upgrade

1. Maak een actuele volledige Home Assistant-back-up en bewaar de gecontroleerde beta.48-release.
2. Laat een beschermde afwas- of andere cyclus afwerken. Gebruik geen STOPRESET voor de update.
3. Installeer exact `1.0.0-beta.49` via HACS zodra de release beschikbaar is of vervang uitsluitend `custom_components/solar_pilot` met het juiste lokale pakket. Behoud bestaande `userfiles` en Home Assistant-opslag.
4. Herstart Home Assistant volledig en controleer backendversie en vernieuwde kaart afzonderlijk.
5. Controleer eerst zonder extra fysieke proefopdrachten actuele bronnen, pending opdrachten, herstelredenen, eigen coastzones en apparaatbeveiligingen. Een update, test of versienummer bewijst geen fysieke respons.

## Modus wisselen en veilig vrijgeven

Alleen bekijken kan tijdens actief beheer worden geweigerd. Kies dan eerst **Pauze** en wacht tot de beheerde toestellen veilig zijn vrijgegeven. Pauze mag alleen bewezen eigen OFF/coast-zones naar Panasonic AUTO teruggeven; handmatige OFF blijft uit. Een bevestigd eigen numeriek batterijdoel mag alleen worden geneutraliseerd als het actuele doel nog exact past. Overgenomen, onbekende of foutieve doelen en willekeurige scripts worden niet op basis van een aanname overschreven; ontbrekend eigendom-/bronbewijs blijft beschermd. Pending opdrachten, fouten en ontbrekende bronnen blijven beschermd.

## Batterijopdrachten en concurrente lasten

Een lopende batterijopdracht blokkeert nieuwe gewone laststarts/verhogingen, AEG-deadline-START en nieuwe vermogensoverdracht. Ook veilige vrijgave van een SolarPilot-eigen klimaatzone bij verwijderen wacht op batterijbevestiging. Bestaande beschermde programma's blijven afwerken; veilige reductie van gewone lasten blijft onder de bestaande rust-/bevestigingsregels mogelijk.

De intentie wordt vóór actuatie duurzaam vastgelegd. Direct vóór verzending worden native doel/eenheid/grenzen, koppeling, toestemmingen en Wallboxbescherming opnieuw gecontroleerd. Een tussentijdse verandering breekt af zonder fysieke aanroep en bewaart een controlefout; het handmatige doel blijft behouden. Bevestiging vereist passende verse gemeten batterijpower van ná de opdracht, en bij numerieke aansturing een passend werkelijk gemeld doel. Daarna is ook een nieuwe P1-rapportage en de gewone wachttijd vereist voordat een nieuwe last op vermeende vrije ruimte kan starten. Een oude P1-meting wordt niet hergebruikt alleen omdat het batterijvermogen bevestigd is. Dit is HA-bronbewijs, geen onafhankelijke fysieke ACK.

Een native SoC-sensor moet procenten (`%`), een eindige waarde tussen 0 en 100 en een verse echte rapportage leveren. Een geldige input_number-helper mag onveranderd blijven maar mag niet restored, toekomstig of ongeldig zijn. Een ondersteund input_number-doel gebruikt de juiste Home Assistant-service. Native numerieke grenzen en stap moeten neutraal nul exact kunnen weergeven; anders blijft het profiel uitleesbaar zonder fysieke vrijgave. Een gekoppelde batterij-actuator of geselecteerd script mag niet aan het Wallbox-apparaat gekoppeld zijn. Controleer zelf scriptinhoud en terugmelding: willekeurige scriptinhoud is geen door SolarPilot bewezen veilige adapter.

Voor verwijderen is verse werkelijk neutrale batterijpower nodig; bij numerieke aansturing moet het actuele doel ook exact neutraal zijn. Stil gemeten vermogen bij een niet-neutraal setpoint is geen vrijgave. Ontbrekende power of een fouttoestand geeft geen onterechte klaarstatus of automatische retry. Een aantoonbaar al neutrale toestand kan read-only worden afgehandeld. Een vervangend laad-/ontlaaddoel houdt rekening met werkelijk aanwezige eigen batterijflow, zodat die niet dubbel wordt meegeteld of bij elke berekening onterecht op nul valt. Read-only/foutieve profielen houden hun gemeten stroom zonder nieuw bedieningsrecht; native actuatorgrenzen voorkomen herhaalde afgekapte doelopdrachten.

## Forecast, tijdroosters en kosten

Ontbrekende forecasturen, gaten en een ontbrekende staart blijven onbekend. Zij worden geen 0 W of nul-fout in een kwaliteitsscore. Alleen echt gedekte voorspellingsintervallen mogen planning, klimaatbeoordeling en forecastkwaliteit onderbouwen. Evaluatie mag zich beperken tot een volledig gemeenschappelijk weer-/PV-venster dat de benodigde coastvoorspelling dekt; een ontbrekende staart wordt niet ingevuld en interne gaten blijven blokkeren. Ontbrekend actueel PV-vermogen geeft ook geen thermisch leerbewijs van 0 W. Bij ingeschakelde zonnewinst moet PV op beide leerinterval-eindpunten bekend zijn; ontbrekend bewijs onderbreekt alleen het actuele interval, niet geldige opgeslagen samples of coëfficiënten. Twee geldige volgende eindpunten laten leren hervatten. Bij expliciet uitgeschakelde zonnewinst blijft leren zonder PV toegestaan en wordt geen zonnecoëfficiënt afgetrokken.

Plan-/forecaststappen volgen verstreken UTC-tijd; lokale labels en kalenderdeadlines behouden hun tijdzone. Zomer-/wintertijd levert daardoor geen dubbel verzonnen of overgeslagen uur. Dagreplay vergelijkt alleen volledige werkelijk gedekte lokale dagen: 92 kwartieren bij de korte zomertijdwisseldag, normaal 96 en 100 bij de lange wintertijdwisseldag. Een onvolledige dag krijgt geen volledige-dagprestatieclaim. Een werkelijke nulprijs blijft nul en wordt niet vervangen door een fallbacktarief. Booleans en niet als eindig getal te verwerken prijswaarden en ongeldige tijdstempels geven vaste terugval, geen herinterpreteerd gratis tarief.

## Export, opslag en veilig herladen

Export pseudonimiseert namen, IDs en hun verwijzingen consistent, inclusief korte en historische labels. Schema-sleutels, eenheden, enums en overige analysebetekenis blijven behouden. De gevraagde periode, beschikbare dekking en gaten blijven zichtbaar; geen fictieve historie toevoegen. Controleer het bestand vóór delen: tijden en gebruikspatronen blijven gevoelig. Export uploadt niets automatisch en is geen herstelbare HA-back-up.

Setup/unload sluiten oude callbacks en achterblijvende taken veilig af. Startafbreking schrijft geen gedeeltelijk geladen opslag over goede gegevens. Ongeldige afzonderlijke pending-, optie- of archiefrecords behouden geldige andere records.

Klimaat deactiveren of gekoppelde zones wijzigen wacht op veilig afronden van eigen OFF/coast en pending opdrachten, ook wanneer een eigen zone tijdelijk onbereikbaar is. Handmatige OFF blijft beschermd tot expliciete gebruikers-AUTO; een late AUTO-echo na geannuleerde AUTO geeft geen nieuw beheerrecht. Fysieke HEAT/COOL, gebruikersrust, comfort- en eigendomsregels blijven behouden.

## Test- en installatiestatus

De definitieve softwaregate staat in `TESTRESULTATEN_BETA49.md`. Er is in deze werksessie geen live Home Assistant-toegang; installatie en fysieke batterij-/klimaat-/DHW-/AEG-respons zijn niet bevestigd. Gebruik geen geforceerde opdrachten of leerreset om updateacceptatie te claimen.

## Rollback

Kies **Pauze**, laat beschermde cycli afwerken, herstel de onveranderlijke beta.48-release of een gecontroleerde volledige back-up en herstart Home Assistant. Controleer backend/kaart, actuele bronnen, eigendom en apparaatbeveiligingen. Beta.48 bevat de manual OFF-, relevante-confidence- en herstartherstelregels, maar niet de aanvullende beta.49-auditcorrecties.
