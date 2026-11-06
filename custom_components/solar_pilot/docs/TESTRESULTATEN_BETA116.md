# SolarPilot beta.116 — softwarevalidatie

## Gedrag dat wordt getoetst

De SG-bronstopherstelroute onderscheidt een eerste bewuste tijdelijke handmatige aanvraag van herhaald inschakelen na noodzakelijk meetverlies. Een bronstop krijgt bestaande niet-vervangbare rust, bevestigde actuele UIT en meerdere werkelijk nieuwe bronrapporten gedurende de startstabiliteit. Flapperende rapporten mogen geen nieuwe AAN-pulsen veroorzaken. Herstart, opnieuw kiezen en Automatisch mogen de wacht niet wissen; oude stabiliteit mag niet worden herhaald. De oorspronkelijke handmatige eindtijd blijft absoluut en harde grenzen blijven leidend.

De native Marstek-proef onderscheidt een herkenbare lopende poll van een expliciete mislukking. Eerder volledig bewezen AC-/SoC-velden behouden alleen hun oorspronkelijke ontvangsttijd, maximale leeftijd van 120 seconden, waarde en bronbinding. Een eerste uitlezing zonder eerder voltooid bewijs blijft onbewezen. Gedeeltelijke antwoorden geven geen nieuw veldbewijs. Verlopen waarden, foutstatus, ongeldige kwaliteit en gewijzigde identiteit blijven ongeldig. Deze softwaretest bewijst geen fysieke pakketinhoud of huishoudelijke verbindingskwaliteit.

De analyse-export wordt getoetst op veilige begrensde oorspronkelijke batterijbrondiagnostiek en beperkte gebeurtenissen. Diagnostiek mag geen aflopende secondenstroom veroorzaken, geen ruwe native cache publiceren en geen extra bron- of actuatorrecht verlenen. De SG-gebeurtenistekst houdt programma/veiligheidscontext en werkelijke native actie apart; geen gemeten compressor- of warmteclaim uit alleen watts.

## Grenzen en bronnen

De twintigminutenminimumaanvraag en gewone vijftienminutenbuffers veranderen niet. Noodzakelijke broncontrole en onafhankelijke net-, fase-, kwartier-, koel-, contact-, timer- en eigendomsgrenzen blijven vereist. De Marstek-route blijft uitsluitend uitlezen; Panasonic en Wallbox krijgen geen nieuwe opdrachten. Geen PV-correctie of bronbinding wordt automatisch uit analysefeedback overgenomen. Alle nieuwe tests gebruiken fictieve bronnen.

De volledige Aquarea v1.9.1→v1.10.0-diff is inhoudelijk beoordeeld en de acht officiële bronrecords zijn op 6 november 2026 online hercontroleerd. De wijziging verhoogt het minimum naar HA 2026.3/Python 3.14 en verandert syntaxis/CI, geen taak-/poll-/energiecontract. SDK v1.5.0 is ongewijzigd. Het afzonderlijke native Marstek-contract blijft v1.12.0. Zie [UPSTREAM_BETA116.md](UPSTREAM_BETA116.md).

## Uitgevoerde lokale controles

Op 6 november 2026 slaagden onder de lokale Python 3.12-testomgeving:

- **649 tests** in de batterij-/Marstek-/analyse-exportregressie: `test_marstek*.py`, `test_battery_source*.py`, `test_battery_baseline114.py` en `test_analysis*.py`.
- **83 tests** in `test_current_guide.py`, `test_option_help27.py` en `test_upstream_review91.py`.
- De actuele-uitlegcontrole, handoffcontrole, upstreamschemastructuur (`--offline`) en `git diff --check`. De afzonderlijke online upstreamversheidscontrole slaagde eveneens; de offlinecontrole vervangt die niet.

Deze gerichte runs kunnen overlappende tests bevatten en vormen geen opgeteld suiteaantal. De volledige eindvalidatie en SG-regressies horen bij de definitieve wijziging en de exacte CI-commit; een eerdere lokale suite vóór aanvullende correcties geldt daarvoor niet als eindbewijs.

## Commitgebonden validatie en publicatie

Gerichte regressies en de volledige suite worden op de concrete wijziging uitgevoerd. De uiteindelijke Actions-run levert het commitgebonden bewijs; dit document verklaart een niet-uitgevoerde gate niet geslaagd. Canonieke uitleg, optiehulp, handoff, privacy/structuur, SG-opdrachtgrens, upstreamreview, Python- en JavaScript-syntax blijven afzonderlijke controles.

Alle vijf Validate-gates moeten op de exacte PR-HEAD groen zijn vóór samenvoegen: repository/full-suite, HACS, Hassfest, echte Chromium-interacties en echte Home Assistant-startup. Main herhaalt de gates vóór de automatische versie-tag en vier release-assets. Daarna worden beide ZIPs en beide releasedocumenten opnieuw tegen de exacte tag en bron-SHA vergeleken. Een eerdere groene commit is geen vervanging; geen handmatige publicatie-omweg of verplaatste bestaande tag.

Geen fysieke batterij-, SG-, warmtepomp- of laadproef uitgevoerd. Softwarepublicatie bewijst geen lokale installatie, fysieke bronkalibratie, COP/SCOP of levensduurwinst.
