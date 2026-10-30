# SolarPilot starten of bijwerken

Installeer **1.0.0-beta.112** via HACS, herstart Home Assistant volledig en herlaad de app of browser.

SG/warmtepomp heeft vaste toegang tot actueel coherent bevestigd autonoom Wallbox-zonnelaadvermogen. De centrale volgorde en tijdelijke Wallboxvoorkeuren van gewone toestellen veranderen niet, maar kunnen SG niet van die zonnestroom uitsluiten. De Wallbox regelt zelf terug; SolarPilot geeft geen laadcommando.

Een toegestaan AAN-contact in automatisch algemeen SG-zonbedrijf mag aanblijven zolang actuele voorwaarden voldoen. Er is geen verplichte uurstop, geen administratieve sessiereset en geen steeds nieuwe startbuffer tijdens geldige korte leasevernieuwing. De oorspronkelijke verstreken tijd blijft bewaard; de kaart toont de lopende automatische zonneboost en de echte korte lokale toestemming. Een lopend contact hoeft de startdrempel niet opnieuw te halen. Lager moduleren op nog bruikbare zon veroorzaakt geen stop. Een geldig bruikbaar zonnebudget van nul begint de vijftienminutenzonnebuffer; meer dan 600 W netafname begint apart de vijftienminutenimportbuffer. Gewone tekortvrijgave volgt ook het oorspronkelijke minimum van twintig minuten, met de bestaande terugmeldmarge in de lokale timer. Nacht geeft geen doorlopende toestemming. De maximumduur blijft gelden voor handmatige en andere begrensde routes.

Na een bewezen beëindigde automatische sessie door het sessiemaximum of onbekende SG-reactie kan een nieuwe aanvraag op actueel bruikbaar P1-/HP-/EV-zonnebudget worden bevestigd. Een eerdere zonnedip of Panasonic-contextwissel is niet nodig voor deze route. Actuele UIT, minstens twee nieuwe oorspronkelijke bronrapporten, eenmaal de ingestelde startstabiliteit en alle finale voorwaarden blijven vereist. Een al geopend oud contact krijgt een nieuwe gecontroleerde korte lokale toestemming; doorlopend automatisch algemeen zonbedrijf vraagt actuele voorwaarden, geen nieuwe uurdeadline.

Het echte huidige overschot blijft leidend, zonder toekomstige toestelreserveringen. Geraamd totaalvermogen bij SG blijft standaard 3000 W. Alleen compleet actueel passend HP-vermogen verlaagt de mogelijke extra opname. Gewone vijftienminutenwolkenbuffer, begrensde Wallboxreactietijd en actuele fase-, kwartier-, batterij- en broncontroles blijven afzonderlijk. Firmwaremetadata blijft informatief; het bestaande bewezen firmwareherstel is behouden.

De update zet de vroegere standaardbuffer van 300 seconden eenmaal om naar 900 seconden. Andere bewaarde aangepaste duurtijden en latere eigen keuzes blijven behouden. De lokale Shelly-toestemming blijft 300 seconden met actuele vernieuwing om de 60 seconden.

[Installatie en rollback](docs/BETA112_INSTELLEN.md) · [Actuele werking](docs/ACTUELE_WERKING.md) · [Testverslag](docs/TESTRESULTATEN_BETA112.md) · [Overdracht](OVERDRACHT.md)
