# SolarPilot beta.97 — test- en publicatieverslag

Versie: **1.0.0-beta.97** · 18 oktober 2026

Bouwbasis: gepubliceerde beta.96-commit `1b8e436caf69c3c59c754acc2bde1977239453d5`. Regressies gebruiken uitsluitend fictieve apparaten, bronnen en waarnemingen.

## Correctie

De vaste SG-herhaalwacht werd bij een onbekende eerdere reactie opgeteld vóór vijf minuten verse restoverschotbevestiging en de gewone startvertraging. De nieuwe route kan de resterende herhaalwacht vervangen wanneer vijf minuten werkelijk voldoende vers restoverschot zijn bewezen, de vorige eigen beëindigde aanvraag aantoonbaar bij de huidige uitgang past, het contact opnieuw betrouwbaar UIT is en alle actuele voorwaarden passen. De gewone startvertraging blijft apart.

Oude of niet passende opdrachtherkomst geeft geen verkorting. Het profiel Uitsluitend tapwater, andere voltooiingsredenen, harde maximumduur, lokale lease, handmatige overname en actuele bron-/koel-/elektrische guards behouden hun afzonderlijke bescherming. De configuratie- en opslagschema's veranderen niet. Een nieuwe bevestiging wordt na reload opnieuw uit oorspronkelijke actuele bronrapporten opgebouwd; geschiedenis wordt niet herschreven.

## Verificatie

De gerichte regressies toetsen de kortere eigen-aanvraagroute en de afwijzing bij onvoldoende of onderbroken restoverschot, ontbrekende of veranderde herkomst, onbetrouwbaar of handmatig gewijzigd contact, andere voltooiingsreden, gewijzigde binding en actuele blokkeringen. De bestaande SG-regressies blijven onderdeel van de volledige suite. De UI toont de herhaalwacht als SG-beleid en geeft verkorting uitsluitend weer op basis van expliciet backendbewijs.

De definitieve volledige lokale suite slaagde met **7.265 tests in 149,53 seconden** (`PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider`). De 81 nieuwe gevallen zijn daarin opgenomen: 26 gerichte SG-regressies, 21 afzonderlijk ontwikkelde adversarial SG-proeven, 28 UI-gevallen en zes Aquarea-contractgevallen. De brede SG-selectie slaagde met 1.556 tests en de gerichte UI-selectie met 211; dit zijn overlappende deelverzamelingen, geen extra tests boven het volledige totaal.

Python-syntaxis, repository/privacy, overdrachtsdossier, gegenereerde uitleg, bytegelijke documentmirrors en Panasonic/SG-grenscontrole slaagden. De online upstreamgate bevestigde beide actuele defaultbranches en stabiele releasetags tegen de gepinde broncommits. De echte Chromium-proef is uitgebreid met de overlappende herhaalwacht en blijft samen met echte Home Assistant, HACS, Hassfest en PowerShell een verplichte GitHub-gate. De lokale browserdownload was niet beschikbaar; daarvoor wordt geen lokaal geslaagd resultaat geclaimd. Eerdere versies leveren geen testresultaten voor beta.97.

## Upstream

Aquarea v1.7.0 `3151d7f196e45b671f3136c9220244fb8c10f2df` en aioaquarea-ng v1.3.1 `d859f3727556c8a07964affd61a038edfd2d353a` zijn online gecontroleerd. Sinds beta.96 is alleen het presentatie-attribuut `auto_mode` toegevoegd; de SDK, bestaande status-/actiebetekenis en consumptieroute veranderen niet. Zes nieuwe regressies bewaken compatibiliteit zonder actief bedrijf, verse poll of actuatorrecht uit dat attribuut af te leiden. De gecombineerde Aquarea-contract- en upstreamgate-selectie slaagde met **112 tests**. Details: `docs/AQUAREA_UPSTREAM_REVIEW_BETA97.md`; machineleesbaar checkpoint: `docs/upstream_review.json`.

## Publicatievoorwaarden

De definitieve GitHub-bron moet alle vijf Validate-gates doorlopen: repository/privacy/documentatie, PowerShell en volledige suite; HACS; Hassfest; echte Home Assistant setup/reload/unload; Chromium. Pas na geslaagde gates op `main` publiceert de bestaande job de immutable tag met vier assets:

- `SolarPilot-v1.0.0-beta.97-GitHub-HACS.zip`
- `SolarPilot-v1.0.0-beta.97-local.zip`
- `BETA97_INSTELLEN.md`
- `TESTRESULTATEN_BETA97.md`

De job verifieert beide ZIPs en beide documentassets vóór publicatie en na opnieuw downloaden tegen de exacte broncommit, met grootte en SHA-256. Bestaande tags en assets worden niet overschreven. Er wordt geen privé Home Assistant-configuratie gepubliceerd of automatische lokale installatie uitgevoerd. Softwaretests zijn geen fysieke Panasonic-/Shelly-acceptatie.
