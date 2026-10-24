# SolarPilot 1.0.0-beta.106 installeren

Werk SolarPilot bij via HACS naar **1.0.0-beta.106**, herstart Home Assistant volledig en herlaad de app of browser. Backend en kaart moeten allebei beta.106 tonen. De update behoudt toestellen, koppelingen, modellen en historie.

## Voorrang

Open **Voorrang**. Een eerder automatisch gegenereerde standaard krijgt Auto laden als laatste rij. Een bewust opgeslagen eigen volgorde blijft behouden. Verplaats SG en gewone toestellen met de pijltjes of door te slepen, bevestig je keuze en kies **Voorrang opslaan**. Een beschermde afwasmachine blijft vóór de optionele SG-vraag.

De Wallbox regelt zelf het laden met het resterende zonneoverschot. SolarPilot verstuurt geen laadcommando. Staat SG vóór Auto laden, dan kan actuele gemeten laadruimte uit een bevestigde autonome zonnelaadsessie meewegen. Oude, ontbrekende of handmatige laadgegevens geven geen laadruimte. De elektrische startgrenzen blijven afzonderlijk gelden.

## Handmatig SG-contact

Een extern ingeschakeld contact wordt in Automatisch regelen herkend als **Handmatig aan · automatische overname**. De kaart toont een afteller van vijftien minuten. Gewoon uitlezen of een herstart verlengt die periode niet.

Na afloop beoordeelt SolarPilot de actuele zonnebijdrage, netafname, hogere toestellen, koeling en elektrische grenzen. Met voldoende zonnebijdrage en een toegestane netafname gaat het contact zonder voorafgaande UIT-puls over naar een bevestigde korte lokale toestemming. Anders wordt het vrijgegeven. Een harde grens kan eerder vrijgave vragen. Ontbrekende contactterugmelding geeft wachten op nieuw bewijs; een oude stand wordt niet herhaald.

Alleen bekijken en Pauze nemen een extern contact niet over. De oorspronkelijke herbeoordelingstijd blijft bewaard. Een echte handmatige UIT blijft beschermd tot **Hervatten**. Een bewuste tijdelijke Aan- of Uit-keuze kan het actuele externe AAN-contact rechtstreeks overnemen; eerst Hervatten kiezen is daarvoor niet meer nodig.

## Controle na de update

Controleer de volgorde en bekijk bij een natuurlijk handmatig ingeschakeld SG-contact de afteller en de beslissing na afloop. De update is met fictieve apparaten en automatische softwarecontroles getoetst; een plaatselijke bekabeling, fabrikantreactie of echte zonnelaadsessie wordt daarmee niet fysiek getest.

Een al bestaande melding over PV-voorspelfout of ontbrekende toestelmeter is afzonderlijke informatie. Deze update verandert geen sensorkoppelingen op basis van een vermoeden.

## Terugzetten

Maak vóór de update en vóór rollback een volledige privéback-up. Geef een eigen SG-aanvraag waar betrouwbaar mogelijk veilig vrij en controleer de plaatselijke terugval. Installeer vervolgens beta.105 met behoud van entry, opslag en userfiles, herstart Home Assistant volledig en herlaad de kaart. Beta.105 kent de nieuwe overnametijd niet en kan de nieuwe volgorde weer volgens de vroegere Wallbox-voor-SG-regel interpreteren. Verwijder de integratie niet en gebruik geen twee runtimes tegelijk.

De volledige actuele uitleg staat in [ACTUELE_WERKING.md](ACTUELE_WERKING.md) en in Home Assistant onder **Uitleg**. Uitgevoerd softwarebewijs en grenzen staan in [TESTRESULTATEN_BETA106.md](TESTRESULTATEN_BETA106.md).
