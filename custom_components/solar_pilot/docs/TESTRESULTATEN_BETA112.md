# SolarPilot beta.112 — softwarevalidatie

## Gereproduceerde problemen en correcties

De runtime kon een lopende, volledig op zon modulerende warmtepomp als tekort behandelen omdat het gezamenlijke budget opnieuw de startdrempel minus marge moest halen. De behoudsregel vraagt nu actueel bruikbaar zonnebudget groter dan nul na de bestaande correcties. De eigen ruwe-P1-importbuffer bepaalt afzonderlijk of de actuele opname te veel net vraagt. Startvoorwaarden blijven ongewijzigd.

Een tweede reproduceerbaar probleem ontstond wanneer een nog actuele warmtepompmeting na een korte P1/PV-tegenstrijdigheid weer passend werd. De oudste bijdragende rapporttijd van het gezamenlijke budget kon dan teruggaan. Dat veroorzaakte onmiddellijke vrijgave vóór minimum en wolkenbuffer. De correctie houdt oorspronkelijke bronactualiteit en rapportvoortgang apart en geeft geen nieuwe tijd aan een reeds lopende tekortdeadline.

## Vereiste regressies

Fictieve runtimefixtures toetsen moduleren bij actuele zon, doorlopen voorbij het oude uurmaximum zonder startreset, korte en herhaalde wolken, herstel van de juiste tekortklok, langdurige echte import, nul zonnebudget en nacht. Bronnen die op verschillende momenten rapporteren, tijdelijk niet-passende HP/EV-bijdragen, herhaalde oude rapporten, nieuwe P1-rapporten en ongeldige noodzakelijke bronnen krijgen afzonderlijke controles. Bestaande minimum-, handmatige-, lokale lease-, harde elektrische en native voorwaarden blijven gelden.

Op uitdrukkelijk verzoek wordt de gedeelde gewone zonne-/importbuffer standaard 900 seconden; 600 W zachte importgrens en 1200 seconden minimumduur blijven behouden. De bestaande lokale lease houdt terugmeldruimte vóór de tekort-/minimumdeadline, standaard maximaal 20 seconden; de regressies mogen geen exact 900 seconden fysieke AAN beloven. De zichtbare reden benoemt een actieve zonnebuffer en de resterende minimumduur. De vroegere standaard van 300 seconden migreert eenmaal naar 900 seconden. Andere bewaarde aangepaste waarden en latere eigen keuzes blijven behouden; een al vastgelegde actieve tekortdeadline mag niet langer worden. Configuratiebereik, beleidsbewijs, lange wolk, bufferherstel en migratie vragen eigen regressies. De korte lokale lease blijft 300 seconden met hercontrole om de 60 seconden. Geen nieuwe Panasonic- of Wallboxbediening.

## Uitgevoerde controles

Op 30 oktober 2026 zijn de canonieke actuele uitleg en gegenereerde optiehulp op versie 1.0.0-beta.112 gecontroleerd. De officiële upstreamcontrole bevestigde dat beide actuele defaultbranch-HEADs en nieuwste stabiele tagcommits nog overeenkomen met de inhoudelijk beoordeelde pins; zie UPSTREAM_BETA112.md.

De definitieve lokale volledige suite is op 30 oktober 2026 geslaagd: **9238 tests, 0 fouten, 0 overgeslagen**, in 237,83 seconden met `PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider`. De vijf nieuwe beta.112-testbestanden bevatten 79 regressiegevallen. De functionele bron bleef tijdens deze laatste volledige run ongewijzigd.

De echte Chromium-SG-controle slaagde op 320, 390, 768 en 1280 pixels, inclusief de vijftienminutenbuffer, actuele aftellers, korte lokale toestemming en bestaande bediening. Ook uitleg/optiehulp, overdracht, openbare repositorycontrole, SG-opdrachtgrens, beide JavaScript-syntaxcontroles, diffcontrole en actuele online upstreamreview zijn geslaagd. Guidehash: `35bbe4479df8b4f4`.

De onafhankelijke migratieregressies bevestigen dat tijdelijke handmatige AAN/UIT-keuzes en extern AAN hun oorspronkelijke eindtijd behouden. De eenmalige beleidsmigratie wijzigt uitsluitend een exact passende identiteit van die bestaande keuzes; historische sessies, eigendom en actieve lease-/tekortbewijzen worden niet opgewaardeerd. Afwijkende koppelingen of andere beleidswijzigingen krijgen geen dergelijke overname.

De commitgebonden GitHub-controles volgen op de pull request. Deze lokale resultaten claimen geen gepubliceerde release of geslaagde fysieke installatie.

## Publicatievoorwaarden en bewijsgrenzen

Alle vijf bestaande commitgebonden Validate-gates blijven vereist: repository/full-suite, HACS, Hassfest, echte Chromium-interacties en echte Home Assistant-startup. Main herhaalt ze vóór automatische publicatie; de vier gedownloade release-assets worden daarna tegen exacte tag en bron-SHA vergeleken. Een oudere groene commit of alleen een ZIP vervangt dat bewijs niet.

Er is geen fysieke SG-, warmtepomp- of laadproef uitgevoerd. Softwaretests certificeren geen bekabeling, kalibratie, fysieke opname, lokale timer of gerealiseerde besparing. Privé-installatiegegevens en screenshots zijn geen openbare fixtures.
