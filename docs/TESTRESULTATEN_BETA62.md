# SolarPilot 1.0.0-beta.62 — testresultaten

Datum: **2026-10-10**.

## Vastgelegde bronbasis

Geverifieerde bouw- en rollbackbasis: [beta.61](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.61), commit `6c7e77b75e09b1c8bc9c4b24e7b9ce693b4a974d`, tree `7aecb76027e3c1c5cd3de6d22d10b4cd9a3b6a04`. Bij de start waren main en tag gelijk; beta.62 was vrij. De bron wordt op een aparte branch ontwikkeld zonder vorige tags/assets te vervangen.

De beta.61-bronbasis is afzonderlijk opnieuw getest: **3814 tests geslaagd in 49,76 seconden**. Dit is de verse baseline, los van de historische releasevermelding en de nieuwe toepasselijke beta.62-suite. Uit deze baseline wordt geen nieuw publicatie- of CI-succes afgeleid.

## Softwaregate en contractmapping

**Definitieve lokale softwaregate: 2809 tests geslaagd in 31,45 seconden.**

Uitvoering: `PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider`. De mapping in `SG_TEST_MAPPING.md` onderscheidt behouden contracttests, vervanging door SG-/migratietests en bewust vervallen directe tank-/klimaatregeltests. Minder tests na verwijdering is geen doel; dekking van behouden functies blijft vereist.

| Controle | Vastlegging |
| --- | --- |
| Opnieuw uitgevoerde beta.61-baseline | 3814 geslaagd in 49,76 s. |
| Volledige toepasselijke beta.62-suite | **2809 geslaagd in 31,45 s**, na de laatste sessie-/atomicity- en publicatieworkflowregressies. |
| SG-status/lease/bron-/vermogensgrenzen | Geslaagd in de volledige suite, inclusief lokale timerreadback, actuele bronbewijzen en verse tankafkoeling voor een nieuwe sessie. |
| Migratie en single-owner/nul Panasonic-writes | Geslaagd in de volledige suite, inclusief duurzame opslag vóór actuatie en centrale dispatchgrens. |
| Bestaande AEG/Wallbox/batterij/ordinary/Recorder/export | Toepasselijke behouden contracten geslaagd in de volledige suite. |
| Gerichte SG-/overige HA-meldingen en echte restart | 17 SG-/meldingsregressies en de behouden overige meldingsgevallen geslaagd in de volledige suite. |
| Publieke preflight/handoff/guide/mirrors | Geslaagd; guidehash `22d95cd9bbdeeab5`, versie beta.62 en beide documentmirrors gelijk. |
| SG-grens, repository, Python-/JS-/JSON-syntax en diff | Geslaagd; 68 Python-productiemodules en beide JavaScript-bestanden gecontroleerd, `git diff --check` schoon. |
| Publicatie-/pakketvalidator | Regressies geslaagd in de volledige suite, inclusief bestaande-tagretry, exacte Git-bytes en weigering van ontbrekende of afwijkende assets. Werkelijke publicatie wordt afzonderlijk hieronder geverifieerd. |

Geen oude actieve writer wordt behouden om historische tank-/AUTO-tests te laten slagen. Alleen specifiek bewust geschrapte contracten worden vervangen of retired; behouden apparaatbevoegdheden en privacy/data/retentie krijgen regressiecontrole.

## Wat de geslaagde regressies bewijzen

- Alle actieve runtime-/planner-/herstel-/gebruikerpaden doen nul Panasonic-writes; één toegewezen SG-uitgang is de enige warmtepompactuator.
- SG vraagt alleen met bevestigde ingebruikname, echte lokale timerreadback, stabiele betrouwbare huidige net-/PV-/fasemetingen en passende rang/toewijzing.
- Vernieuwing schuift de lokale deadline op zonder fysieke uit/aan-cyclus; wifi-/HA-uitval is niet hetzelfde als power-on. Timerbewijs blijft afzonderlijk van de serviceacceptatie.
- Max-sessionherhaling vraagt een verse same-binding eindtankmeting plus minstens 2 °C afkoeling na rust, met twee latere echte rapporten over vijf minuten; onbekend, restored, veranderd of oud bewijs heft de wachtstand niet op. Herstart vraagt nieuwe vijfminutenbevestiging en volledige actuele startvoorwaarden. Dit bewijst opslagruimte, geen comfortvraag/SG-respons.
- Bronuitval/verkeerde units/faseoverschrijding, Shelly-onbereikbaarheid, late ACK/callback, manual hold, session/rest/lease en herstart/rebind/unload mogen geen onbeperkte ON-replay of fictieve OFF veroorzaken.
- Totaal/deelvoeding, heater-inclusie en blijvend native verbruik na SG-UIT geven geen dubbeltelling of onbewezen terugwinbaar vermogen.
- Idempotente migratie archiveert relevante oude opties/opslag, journal/fouten en modellen zonder oude doel-/AUTO-write of afwasstart. Onbekende/mengfouten, gebruikersmodus en andere commandobescherming blijven behouden.
- AEG behoudt exact nieuwe APP-vrijgave, ticketkalender/deadline, één native START, beschermd nadrogen, eventgestuurd einde en geen stroomonderbreking. Wallbox blijft read-only.
- Recorderuitsluiting, bestaande overige live attributen, presentatiecache, gebruikersvolgorde, lokale historie, geauthenticeerde export en echte herstartmeldingen blijven intact. Het Panasonic-migratiearchief wordt live uitsluitend compact samengevat; de exacte volledige inhoud blijft in private eigen opslag en privacygefilterde export. Synthetische regressies bewaren ook 50.001 modelrijen, diepte 30 en een tekst van 9000 tekens bij die export. De compacte livepresentatie kapt de opgeslagen archiefbron niet af.
- De UI toont aanvraag/contact/reactie afzonderlijk, kent geen oude tank-/heater-/klimaatknoppen en bewaart open details op vaste ids.

## Bewijsgrenzen

Softwareproeven gebruiken fictieve Home Assistant-/Shelly-antwoorden, gesimuleerde tijd en service-recording. Zij bewijzen codegedrag, geen echt relais, lokale firmwaretimer, Panasonic-reactie of fysieke vat-/vloeropwarming. Er is geen live woning-/Home Assistant-acceptatie uitgevoerd in deze codewerkrondes. De volledige browser-/renderproef kon niet worden uitgevoerd: Chromium ontbrak en de browserdownload werd afgebroken. JavaScript-/UI-regressies geven daarom geen claim over een werkelijk geladen appkaart. Externe automatiseringen zijn zonder live inzage niet geïnspecteerd.

Nieuwe SG blijft standaard uit tot de gebruiker juiste uitgang, native basis/contactmapping, afwezigheid dubbele schrijvers en lokale aflooptimer echt heeft gecontroleerd. Fysieke proefdraaiactie uitsluitend na expliciete toestemming. Een gelijkblijvend app-tankdoel is geen temperatuuropdracht-ACK-fout; relaisbevestiging alleen is geen bewezen tapwaterrespons.

Bestaande retentie en datalimieten blijven behouden. Een niet verwerkbaar of extreem diep genest archief geeft een expliciete exportfout, zonder stille afkapping of wijziging van de private bronopslag. De migratie bewijst geen complete HA-back-up en een nieuwe ZIP herstelt geen oude privé-opslag. Rollback vereist passende beta.61-code en pre-upgrade-back-up; geen oude en nieuwe writer tegelijk.

## Publicatie-/pakketgate

De lokale softwaregate hierboven is voltooid. De volgende afzonderlijke publicatiegate gebruikt nieuwe PR-/main-workflowruns, een annotated tag op de exacte geteste broncommit en een prerelease met vier assets. De publicatieworkflow controleert beide ZIPs vóór upload tegen de Git-bron en controleert daarna de vier werkelijk gedownloade assets. Dat geldt ook bij opnieuw uitvoeren voor een bestaande tag; een afwijkende tag, ontbrekende release/asset of afwijkende bytes geven een fout en worden niet stil overschreven.

`tools/check_release_packages.py` vergelijkt de volledige ledenlijst en bytes van beide ZIPs, versies, broncommit, standalone installatie-/testdocumenten en hun ingebedde mirrors. Het registreert de werkelijke bron-SHA, assetgroottes en SHA-256. De publieke bewijsplaats is de nieuwe [Actions-run](https://github.com/Stevenva007/solarpilot-home-assistant/actions) voor [tag v1.0.0-beta.62](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.62), aangevuld met het download-/hashbewijs bij publicatie. Deze brongebonden testtekst claimt geen al uitgevoerde upload of geslaagde toekomstige workflow. Vorige tags/assets blijven ongewijzigd.

Installatie, lokale ingebruikname en rollback: `BETA62_INSTELLEN.md`. De volledige actuele gebruiksuitleg komt uitsluitend uit `current_guide.py` en haar gegenereerde `ACTUELE_WERKING.md`-mirrors.
