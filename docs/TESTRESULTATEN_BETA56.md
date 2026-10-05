# SolarPilot 1.0.0-beta.56 — testresultaten

Datum: **2026-10-05**

## Bronbasis en bewijsgrenzen

Basis is de gecontroleerde gepubliceerde beta.55: commit `83dda3b820b913ae191aedd9d3628c10eb342a68`, tree `105c808dcaebb88a45319bd84453102c29b9a4ce`, annotated tagobject `f5df4c6e406477e6777de49ae1e5aad66cf1caec`. Release `403676992`, workflow `37308059878`, vier geslaagde jobs en vier release-assets zijn gecontroleerd. Beide ZIP-pakketten zijn byte voor byte met de tagbron vergeleken. Haar 3064 tests zijn basisbewijs, geen beta.56-resultaat.

Een actuele privé-analyse bevat geschiedenis van verschillende updates. Oude samples hebben geen betrouwbare individuele versiemarker; zij worden niet achteraf aan beta.55 of beta.56 toegeschreven. Nieuwe meetpunten en gebeurtenissen bewaren vanaf beta.56 hun verzamelversie. Publieke regressies, bronnen en voorbeelden gebruiken fictieve gegevens. Geen privé-export, installatie-identiteit of echte huishoudelijke entiteit is gepubliceerd.

## Softwaregate

**3244 tests geslaagd in 35.92 s**, Python 3.12.14 en pytest 9.1.1. Uitgevoerd na de laatste codewijzigingen met `PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider`. De bestaande suite blijft behouden en bevat 180 extra regressiegevallen ten opzichte van beta.55. Onafhankelijke lezers controleerden uitvoeringsvoorwaarden, native programmabinding, opdrachtjournal, herstart, exportautorisatie en frontendgedrag; hun concrete bevindingen zijn hersteld en opnieuw getest.

| Onderdeel | Gecontroleerd gedrag | Resultaat |
| --- | --- | --- |
| Warm water vanaf 3000 W | Inclusieve grens, isolatiereserve, afwasvoorrang, eenmalige migratie van 3500 W; andere en later gekozen waarden behouden | Geslaagd |
| Warmwaterdiagnose | Meerdere voorwaarden afzonderlijk, geplande hygiëne-eindtijd, stabilisatie, afkoeling, bronkwaliteit, pending, ouderserialisatie; echte aanvraagreden tot na herstart en HA-doelbevestiging | Geslaagd |
| Passieve klimaattrend | Geen actieve of gemengde meetperiode als verse passieve trend; oude actieve slope niet na UIT hergebruiken | Geslaagd |
| Actuele comfortvraag | Toekomstig buitenweer bepaalt geen actuele reactieve richting; zachte nieuwe vraag vraagt tien minuten én nieuwe echte rapportage; herstel/uitval/herstart wist de kandidaat | Geslaagd |
| Werkelijk warmtepompprogramma | Exacte Aquarea-entry/toestel/zone en juiste libraryenum, nieuwe geslaagde poll, versheid, fout/reload/herbinding; gecontroleerde expliciete bron als alternatief | Geslaagd |
| Programma versus vraag | COOL/AUTO_COOL geeft geen automatische warmtestart; HEAT/AUTO_HEAT geen koelstart; onbekend programma blokkeert; controle vóór en na journal, ook bij legacy automatische hervatting | Geslaagd |
| Eigen pauze en hervatten | Bewezen eerdere programma-intentie, actuele verse OFF en passende binding; externe keuze trekt eigendom in; beschadigde late opgeslagen OFF-proof geeft geen hervatvrijgave | Geslaagd |
| Vertraagde AUTO | Terugmelding van bestaande OFF-baseline annuleert de opdracht niet als fictieve externe ingreep; expliciete externe bediening, late feedback, timeout en herstart blijven beschermd | Geslaagd |
| Begrensde diagnoselog | Exacte temperatuur/programma/beslissing/verzending/bevestiging, versie en context; overgangslog en heartbeat; maximaal 128 klimaatsporen | Geslaagd |
| Grote zeven-daagse export | Rapport boven oude 16 MiB-grens volledig teruggelezen uit gzip; geen exportafkapping; compressie buiten eventloop | Geslaagd |
| Echte lokale HTTP-route | aiohttp FileResponse, beheerder en dezelfde gebruiker/runtime, 200/403/404/206, DELETE, verloop en cleanup; geen transparante gzip-decodering | Geslaagd |
| Werkelijke kaartcode via Node | Centrale actuele doel-/wachtredenen, verschillende ruimtes, escaping, batterij alleen-lezen/pending/fout, authentieke downloadroute, late/sluitrespons en hangende cleanup | Geslaagd |
| Toestelgeschiedenis | Alleen bevestigde start/stop als verandering; meetonderbreking blijft onbekend; opdrachtpoging wordt geen fictieve waarneming | Geslaagd |
| Syntax en repository | 66 product-Pythonbestanden via AST, vier JSONbestanden, beide frontendmodules via Node; publieke preflight, handoff, actuele uitleg, repositorystructuur en diffcontrole | Geslaagd |
| Uitleg en voorbeeld | Backend/frontend beta.56, 439 hulpvelden, gelijke uitleg- en installatiekopieën, fictief offline voorbeeld opnieuw opgebouwd | Geslaagd |

Actuele regel-hash: `274ce31f86a2613b`. De softwaregate stuurt geen live apparaten aan.

## Betekenis voor diagnose

Een gemeld hoog boilerdoel bewijst geen opwarming en geen SolarPilot-opdracht. De onderzochte blokkade was een ingestelde fabrikantvoorzorgsperiode; zij bewijst niet dat sterilisatie gedurende het hele venster werkelijk actief is. De eindtijd en andere gelijktijdige voorwaarden zijn nu zichtbaar. De 3000 W-drempel heft bron-, prioriteits-, opdracht- en fabrikantbescherming niet op.

De onderzochte klimaathistorie toont reactieve AUTO-aanvragen en een geannuleerde aanvraag waarna AUTO later werd gemeld. Een vijfminutensample bewijst de temperatuur op het precieze opdrachtmoment niet. De trendcorrectie is afzonderlijk gereproduceerd; zij wordt niet als bewezen oorzaak van iedere historische AUTO gepresenteerd. Nieuwe sporen maken de gebruikte temperatuur, richting en programmacontext controleerbaar.

De native Aquarea-adapter leest zonder extra cloudverzoek de bestaande coordinator. Het ondersteunde contract is gecontroleerd tegen de primaire [Aquarea-coordinator](https://github.com/wpatrik14/home-assistant-aquarea/blob/main/custom_components/aquarea/coordinator.py), [HA-klimaatadapter](https://github.com/wpatrik14/home-assistant-aquarea/blob/main/custom_components/aquarea/climate.py) en [library-opdrachten](https://github.com/wpatrik14/aioaquarea/blob/main/aioaquarea/entities.py). Andere of onbekende shapes geven geen autonome startvrijgave. HA AUTO/UIT kan upstream globale programmecode 8/0 versturen. De opgeslagen richting na een eigen OFF bewijst eerdere intentie, geen garantie dat Panasonic fysiek dezelfde HEAT/COOL kiest bij AUTO. SolarPilot verzendt geen directe HEAT/COOL-keuze en verandert het thermostaatdoel niet.

Geen live Home Assistant- of fysieke toestelacceptatie is uitgevoerd. De HTTP-test gebruikt een echte lokale aiohttp-server met testauthenticatie; de kaarttests gebruiken de echte JavaScript-code met DOM/HA-doubles. Dit bewijst softwaregedrag, geen geladen telefoonapp, compressoractie, tankrespons of thermische voorspelnauwkeurigheid.

## Publicatie en installatie

Dit verslag legt de lokale gate vóór publicatie vast. De daaropvolgende CI/publicatie is afzonderlijk te controleren bij de [beta.56-release](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.56) en [Validate-workflow](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml). Vereist zijn vier geslaagde jobs, een annotated tag op de geteste commit, twee ZIP-pakketten en de twee beta.56-documenten. De afsluitende controle downloadt alle vier assets, controleert SHA-256 en vergelijkt beide volledige ZIP-inhouden met de exacte tagbron. Eerdere releases blijven onveranderd.

Installatie en rollback staan in `BETA56_INSTELLEN.md`. Na installatie: Home Assistant herstarten, app/webpagina opnieuw openen en backend-/kaartversie controleren. Bestaande geldige leerdata, eigen instellingen, dashboardkeuzes en beschermde programma's blijven behouden. Rollback naar beta.55 herstelt niet vanzelf de gemigreerde opgeslagen drempel; controleer die of herstel de passende volledige back-up. Publicatie is geen bewijs dat de update al op een installatie geladen is.
