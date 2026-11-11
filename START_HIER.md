# SolarPilot starten of bijwerken

Installeer **1.0.0-beta.117** via HACS, herstart Home Assistant volledig en herlaad de app of browser.

Aquarea 2.0.1 verplaatst de pompstatus naar een binaire sensor. SolarPilot beta.117 volgt die upstreammigratie read-only op dezelfde unieke bronidentiteit en apparaatbinding. De getypeerde LIVE-poll, richting, zones, tankcontext en oorspronkelijke rapporttijden blijven verplicht; bij een dubbele of onvoltooide migratie blijft de taak onbekend.

Kies **Marstek-monitor openen** om een bestaande monitor aan te passen. Bij één monitor staan je opgeslagen waarden direct ingevuld; bij meerdere kies je eerst het profiel. **Extra Marstek-monitor toevoegen** is alleen voor een extra batterij. Zoek en selecteer de sensor uit de begrensde lijst. Kies **Verder**, controleer het overzicht en bevestig daarna met **Wijzigingen opslaan**. Open hetzelfde profiel opnieuw om de bewaarde keuzes te zien. Annuleren slaat niets op; een veldfout bewaart je invoer om haar te verbeteren.

Bij een batterijbronmelding kies je **Batterijbron controleren**. Kies de getekende batterij-AC-sensor, bij de ondersteunde native Marstek-koppeling **Vermogen netaansluiting (AC OnGrid)** met **Positief = ontladen naar huis**. Controleer en bevestig de AC-meetdekking. De update zet een ontbrekende bevestiging niet aan. Verkeerde meetsoort of ontbrekend actueel veldbewijs blijven afzonderlijk zichtbaar. SoC is optioneel; Marstek blijft autonoom regelen.

Volledig betrouwbare, afzonderlijk bevestigde AC-batterijmetingen kunnen nu worden meegenomen in het basislastleren. Alle actieve bronnen, oorspronkelijke rapporttijden en overlapcontroles blijven nodig. Een onvolledige bron wordt geen nul of modelbewijs.

SG/warmtepomp heeft vaste toegang tot actueel coherent bevestigd autonoom Wallbox-zonnelaadvermogen. De centrale volgorde en tijdelijke Wallboxvoorkeuren van gewone toestellen veranderen niet, maar kunnen SG niet van die zonnestroom uitsluiten. De Wallbox regelt zelf terug; SolarPilot geeft geen laadcommando.

Een toegestaan AAN-contact in automatisch algemeen SG-zonbedrijf mag aanblijven zolang actuele voorwaarden voldoen. Er is geen verplichte uurstop, geen administratieve sessiereset en geen steeds nieuwe startbuffer tijdens geldige korte leasevernieuwing. De oorspronkelijke verstreken tijd blijft bewaard; de kaart toont de lopende automatische zonneboost en de echte korte lokale toestemming. Een lopend contact hoeft de startdrempel niet opnieuw te halen. Lager moduleren op nog bruikbare zon veroorzaakt geen stop. Een geldig bruikbaar zonnebudget van nul begint de vijftienminutenzonnebuffer; meer dan 600 W netafname begint apart de vijftienminutenimportbuffer. Gewone tekortvrijgave volgt ook het oorspronkelijke minimum van twintig minuten, met de bestaande terugmeldmarge in de lokale timer. Nacht geeft geen doorlopende toestemming. De maximumduur blijft gelden voor handmatige en andere begrensde routes.

Na een bewezen beëindigde automatische sessie door het sessiemaximum of onbekende SG-reactie kan een nieuwe aanvraag op actueel bruikbaar P1-/HP-/EV-zonnebudget worden bevestigd. Een eerdere zonnedip of Panasonic-contextwissel is niet nodig voor deze route. Actuele UIT, minstens twee nieuwe oorspronkelijke bronrapporten, eenmaal de ingestelde startstabiliteit en alle finale voorwaarden blijven vereist. Een al geopend oud contact krijgt een nieuwe gecontroleerde korte lokale toestemming; doorlopend automatisch algemeen zonbedrijf vraagt actuele voorwaarden, geen nieuwe uurdeadline.

Het echte huidige overschot blijft leidend, zonder toekomstige toestelreserveringen. Geraamd totaalvermogen bij SG blijft standaard 3000 W. Alleen compleet actueel passend HP-vermogen verlaagt de mogelijke extra opname. Gewone vijftienminutenwolkenbuffer, begrensde Wallboxreactietijd en actuele fase-, kwartier-, batterij- en broncontroles blijven afzonderlijk. Firmwaremetadata blijft informatief; het bestaande bewezen firmwareherstel is behouden.

Bij een upgrade uit een oudere versie wordt de vroegere standaardbuffer van 300 seconden eenmaal omgezet naar 900 seconden. Andere bewaarde aangepaste duurtijden en latere eigen keuzes blijven behouden. De lokale Shelly-toestemming blijft 300 seconden met actuele vernieuwing om de 60 seconden.

[Installatie en rollback](docs/BETA117_INSTELLEN.md) · [Actuele werking](docs/ACTUELE_WERKING.md) · [Testverslag](docs/TESTRESULTATEN_BETA117.md) · [Overdracht](OVERDRACHT.md)
