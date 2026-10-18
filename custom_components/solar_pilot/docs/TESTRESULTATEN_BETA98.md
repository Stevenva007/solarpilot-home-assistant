# SolarPilot beta.98 — test- en publicatieverslag

Versie: **1.0.0-beta.98** · 18 oktober 2026

Bouwbasis: gepubliceerde beta.97-commit `9265310616f5ec7cdc122659ef167f47123171a1`. Regressies gebruiken fictieve apparaten, bronnen, historische meetpunten en gebruikersrechten.

## Aanraakbare geschiedenis

De gezamenlijke tijdmarkering leest historische meetpunten en bestaande taak-/SG-intervallen. Numerieke waarden worden niet naar een andere tijd verplaatst: bij een nabijgelegen werkelijk meetpunt verandert ook de aangegeven markeringstijd naar die vastlegging. Buiten de begrensde afstand blijven numerieke waarden onbekend. De actuele boilerkaart levert geen historische terugval. Nieuwe totaalwatts worden alleen uit bestaande volledige metervalidatie vastgelegd; oude ontbrekende totalen en onvolledige voedingen blijven onbekend.

De opnamecadans, dertig lokale kalenderdagen, begrensde aantallen, oorspronkelijke rapporttijden, bestaande bron-ACL en afzonderlijke dagelijkse kWh-dekking blijven behouden. Er komt geen nieuwe fysieke opdracht of besturingsrecht. UTC-daggrenzen houden 23/25-uursdagen en dubbele lokale uren uit elkaar.

## Nieuwe Aquarea-bronvorm

Aquarea v1.8.0 `8722cf22e5a5752406aea1ba79b2cf48d4deedf3` vereist SDK 1.4.0 `893065a81c014cb9aa1d3350446d61c01bccf3b9`. De parser en werkelijke statusbetekenis veranderen. Het afzonderlijke nieuwe contract bewaart de oudere historische semantiek. Een getypeerde CACHED-status geeft geen nieuwe actualiteit, ook wanneer de coordinator zijn poll als geslaagd meldt. Dezelfde controle geldt voor native HA-temperaturen, doelwaarden, acties en regelcontext. Het achteraf wijzigen van dezelfde afgekeurde status naar LIVE vernieuwt dat bewijs niet. De nieuwe afgeleide apparaatinschakeling levert op zichzelf geen bewijs van fysieke globale stilstand; de oudere historische interpretatie blijft herkenbaar. De bestaande inbedrijfstelling, SG-/koelvoorwaarden en Panasonic-read-only-grens blijven behouden.

De Aquarea-energiesensoren, oorspronkelijke UTC-periode en interval-/maandwaarden veranderen in deze upstreamvergelijking niet. De SDK levert de bestaande Consumption-lijst via een nieuw rijker rapport; SolarPilot gebruikt de geregistreerde HA-bronroute en neemt de extra metadata niet als nieuw energie- of stuurrecht over. Bronbeoordeling: `docs/AQUAREA_UPSTREAM_REVIEW_BETA98.md`; machineleesbaar checkpoint: `docs/upstream_review.json`.

## Validatie

Uitgevoerde gerichte controles op de beta.98-bron:

- 76 nieuwe en behouden UI-regressies; daarnaast 44 onafhankelijke geschiedenis-, opslag-, API-, UI- en cachegrensgevallen. De groepen overlappen met bredere suites en worden niet bij elkaar opgeteld.
- Volledige Chromium-geschiedeniscontrole op vier schermbreedtes, inclusief 320/390 px, horizontale vingerbediening, behouden verticale scroll, stabiele balkpositie onder de vinger, pointercapture tijdens hertekenen, alle zes balken, toetsenbord, vernieuwen/dagwissels, meetgaten en nul stuuracties. De actieve mobiele detailweergaven zijn visueel gecontroleerd.
- De daadwerkelijke geïnstalleerde PyPI-SDK `aioaquarea-ng==1.4.0` is onder Python 3.12.14, 3.13.16 en 3.14.2 rechtstreeks door de meegeleverde geladen-code-inspector geaccepteerd onder `aquarea_operation_status_action_v1`; de vingerafdruk is `118e26322d23606c3c5343fcf751a5a7ada96d430592b744b9d5340f0b7b6deb`.
- 31 nieuwe SDK-statusgevallen en 13 afzonderlijke native-monitorgevallen; de laatste gecombineerde gerichte bronrun behaalde 476 geslaagde tests.
- Alle negen canonieke bronfuncties onafhankelijk met de officiële vastgepinde SDK vergeleken; energie-/sensorroute en alle acht actuele upstreamrecords gecontroleerd.
- Actuele uitleg, overdracht, publieke repositorystructuur en Panasonic-/SG-commandogrens geslaagd.

De volledige lokale suite op de definitieve productiebron is geslaagd: **7396 tests** onder Python 3.13.16, zonder mislukte of overgeslagen gevallen, in 152,44 seconden. JavaScript-syntax en alle 93 Python-bronbestanden zijn gecontroleerd. De definitieve GitHub-gates en pakketverificatie blijven afzonderlijke publicatievoorwaarden; hun brongebonden resultaat staat bij de workflowrun en release. Oudere releases leveren geen testresultaten voor beta.98.

De regressies moeten selectie, actuele versus historische waarden, oude ontbrekende totalen, onvolledige splitmeters, meetgaten, grenzen/tijdwissels, navigatie, vernieuwen, pointercapture, sluiten en late antwoorden toetsen. De browsertests voeren de daadwerkelijk meegeleverde kaart uit met fictieve gegevens en controleren mobiele bediening en uitsluitend leesbare aanvragen.

De nieuwe SDK-regressies moeten de daadwerkelijk gecontroleerde parser-/actiebetekenis, LIVE/CACHED, gewijzigde geladen code, oorspronkelijke pollgeneratie, bronconflict, oudere contracten, oorspronkelijke historie en ongewijzigde actuatorgrenzen afdekken.

De eerste GitHub-run wees twee concrete verschillen aan: Python 3.13 veranderde de standaardweergave van lege AST-velden, en de oude Core-discoveryfixture bevatte wel native registraties maar geen coordinator. De bronvergelijking gebruikt nu expliciet dezelfde volledige canonieke vorm op alle drie Python-versies; alle negen oorspronkelijke hashes blijven gelijk en gewijzigde code blijft geweigerd. De Core-fixture toetst eerst het afwijzen van losse native registraties, voegt daarna een exact gekoppelde offline legacy-coordinator toe en behoudt de bestaande controles. De herziene fixture is met echte Core 2026.10.0 / Python 3.14.2 geslaagd voor setup, reload, unload, geschiedenis en rechten, met nul fysieke serviceaanroepen.

## Publicatievoorwaarden

Alle vijf Validate-gates moeten op de definitieve bron slagen: repository/privacy/documentatie, PowerShell en volledige suite; HACS; Hassfest; echte Home Assistant setup/reload/unload; Chromium. Pas na geslaagde gates op `main` publiceert de bestaande job de immutable tag met vier assets:

- `SolarPilot-v1.0.0-beta.98-GitHub-HACS.zip`
- `SolarPilot-v1.0.0-beta.98-local.zip`
- `BETA98_INSTELLEN.md`
- `TESTRESULTATEN_BETA98.md`

De job vergelijkt beide ZIPs en beide documentassets vóór publicatie en na opnieuw downloaden met de exacte broncommit, inclusief grootte en SHA-256. Bestaande tags en assets worden niet overschreven. Privé Home Assistant-gegevens worden niet gepubliceerd en er volgt geen automatische lokale installatie. Softwaretests zijn geen fysieke Panasonic-/Shelly-acceptatie.
