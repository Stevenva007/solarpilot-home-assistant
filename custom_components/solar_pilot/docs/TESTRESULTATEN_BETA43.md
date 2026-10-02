# SolarPilot 1.0.0-beta.43 — testresultaten

Datum: **2026-10-02**

> **Definitieve lokale releasecontrole groen:** de gesynchroniseerde beta.43-bron leverde **1656 geslaagde tests in 9.95 s** en **veertien geslaagde browsercontroles** op. Actuele uitleg, handoff, repositorystructuur, publieke preflight, JavaScript-syntax en diffcontrole zijn groen. Dit verslag claimt geen nog niet uitgevoerde GitHub-workflow of fysieke beta.43-acceptatie.

## Bewezen live basis vóór beta.43

- Home Assistant Core **2026.9.4** had SolarPilot **1.0.0-beta.42** werkelijk geladen; backend en kaart zijn afzonderlijk gecontroleerd.
- Een volledige Home Assistant-back-up is vereist vóór de beta.43-upgrade.
- De Wallbox blijft read-only; beta.43 voegt waarneming en uitleg toe, geen actuatorrecht.
- Een echte actieve koelcyclus en een volledig nieuwe AEG-belading worden niet vooraf als beta.43-liveacceptatie geclaimd.
- Deze feiten bewijzen de beta.42-uitgangssituatie, niet dat beta.43 al gepubliceerd of geïnstalleerd is.

## Werkelijk uitgevoerde softwarecontroles tijdens ontwikkeling

- definitieve volledige Python-regressiesuite na versie-/documentensynchronisatie: **1656 geslaagd in 9.95 s**;
- alle veertien browsercontroles geslaagd, inclusief de nieuwe vermogensuitleg, actieve toestellen/voordeel/Wallbox-geschiedenis en veilige Terug/Vooruit-navigatie; uitsluitend fictieve gegevens en geen fysieke opdrachten;
- actuele-uitlegcontrole: beta.43, hash `2072294edfd69fb0`; handoff, repositoryvalidatie, publieke preflight, JavaScript-syntax en `git diff --check` groen;
- gerichte regressies voor de samengevoegde runtime-, Wallbox-activiteit-, waardeschattings-, afwasdeadline- en DHW/Wallbox-prioriteitswijzigingen: **271 geslaagd** na toevoeging van **29 nieuwe tests**;
- de tests zijn uitgevoerd met UTF-8, zonder bytecode en zonder pytest-cache.

De lokale resultaten hierboven zijn werkelijk uitgevoerd. De bestaande GitHub-workflow controleert daarna onafhankelijk repository/tests, HACS en Hassfest en maakt pas bij succes de nieuwe tag en releasepakketten. Publicatie en geladen versies zijn afzonderlijke controles, geen gevolgtrekking uit groene lokale tests.

## Gedrag dat gericht is afgedekt

- **Nu actief** vereist een werkelijk actieve status. Gemeten versus geschat vermogen blijft onderscheiden; een helper-, afgeleide of onbetrouwbare bron wordt niet als exclusieve meting voorgesteld.
- De Wallbox-wachtuitleg gebruikt de actuele bekende native status en verleent geen actuatorrecht.
- Maximaal dertig waargenomen laadperiodes blijven lokaal bewaard. Herstart, meetgat, corrupte/toekomstige tijd en oude native status maken geen fictieve start, stop of oorzaak.
- Een historische native stopoorzaak is alleen geldig wanneer de exacte status na het laatste laadrapport en binnen vijf seconden van het stop-vermogensrapport ligt.
- Browser Terug/Vooruit herstelt alleen eigen SolarPilot-UI op dezelfde URL, vraagt bevestiging bij niet-opgeslagen werk en onderbreekt geen busy/save-actie.
- De voorwaartse automatische-voordeeltelling bewaart maximaal negentig dagen, telt alleen werkelijk actieve door SolarPilot beheerde Auto-verbruikers en houdt ontbrekende data onbekend. Het resultaat blijft een niet-causale opportunity-value-schatting.
- De optionele maandagdeadline is leeg/gewone 13:00 voor bestaande installaties, kan alleen maandag bijvoorbeeld 10:00 maken en respecteert lokale tijd/DST.
- Een bestaand ticket wordt door een upgrade niet stil herberekend of opnieuw gewapend. Alleen expliciet toepassen op huidig verzoek herberekent dezelfde geplande dag, zonder ticket of START; een lopende cyclus blijft beschermd.
- De beschermde avondvoorraad blijft onder de ingestelde limiet en maximaal 55 °C. EV-krediet vereist een expliciet ingeschakelde, verbonden en vragende native Full Solar-sessie, minstens 50 W en maximaal 120 seconden oude status én vermogensrapportage.
- Handmatig, onbekend, strijdig of oud laden geeft geen EV-krediet. Extra 60 °C krijgt nooit EV-krediet; comfort-, koel-, fabrikant- en elektrische beveiligingen blijven hoger.

## Definitieve releasecontrole

Vóór publicatie worden op de definitieve bronboom opnieuw gecontroleerd:

- volledige Python-regressiesuite;
- alle browser-/UI-controles, inclusief mobiel, navigatie, busy/dirty-formulieren, actieve lasten, waardeschatting, AEG-planning en DHW/Wallbox-prioriteit;
- `tools/check_current_explanation.py`, `tools/check_handoff.py`, `tools/validate_repository.py` en `tools/check_public_repository.py`;
- JavaScript-syntax, `git diff --check` en bytegelijkheid van root- en embedded documentkopieën;
- versieconsistentie tussen manifest, backend, kaart, actuele uitleg en optiehulp;
- daarna de echte GitHub Validate-/HACS-/Hassfest-workflow.

## Acceptatieplan na installatie beta.43

1. Controleer na volledige herstart dat backend en kaart werkelijk `1.0.0-beta.43` tonen.
2. Controleer **Nu actief** met echte actieve en inactieve states en verifieer de bronkwaliteit van het vermogen.
3. Controleer de read-only Wallbox-wachtuitleg. Observeer later een echte laadstop en bevestig dat een meetgat of oude status geen stopoorzaak krijgt.
4. Controleer browser Terug/Vooruit met een ongewijzigd scherm, een dirty formulier en een lopende opslagactie.
5. Controleer dat de waardeschatting pas voorwaarts op bruikbare intervallen telt en niet als tweede aftrek op de elektriciteitskost wordt gepresenteerd.
6. Controleer leeg als gewone maandagdeadline 13:00; stel indien gewenst expliciet 10:00 in. Toepassen op het huidige verzoek mag alleen na bevestiging dezelfde dag herberekenen en mag geen START sturen.
7. Controleer dat een bestaand APP-ticket de update overleeft en APP dat bij startup al Enabled is geen nieuw ticket maakt. Voor een nieuwe belading is uit→exact Enabled nodig.
8. Controleer avondvoorraad afzonderlijk met actuele bevestigde Full Solar versus manueel, onbekend en oud laden. De voorraad blijft maximaal 55 °C en extra 60 °C krijgt geen EV-krediet; er mag geen Wallbox-servicecall plaatsvinden.
9. Controleer de bestaande koelroute en onmiddellijke DHW-terugval tijdens een echte actieve koelcyclus. Dit is nog niet fysiek bewezen.
10. Test een volledig nieuwe AEG-belading alleen gecontroleerd: APP uit→aan, geldige startvoorwaarden, maximaal één START en bescherming tot End Of Cycle. Dit is nog niet fysiek bewezen.

## Fysieke grenzen

Softwaretests met Home Assistant-testdubbels bewijzen geen echte cloud-, laadpaal-, compressor- of AEG-reactie. Zonder exclusieve AEG-meter wordt geen gemeten elektrisch faseprofiel geclaimd. Waargenomen Wallbox-status is geen bewijs dat SolarPilot een sessie veroorzaakte. De fysieke koelroute en nieuwe AEG-cyclus blijven afzonderlijke liveacceptatiepunten en zijn geen voorwaarde om softwaretests eerlijk als softwaretests te rapporteren.

## Releasepakketten

Release-ZIP's worden pas door de publicatieworkflow gemaakt. Inhoud, manifestversie, verboden private/cachebestanden, padveiligheid, bytes ten opzichte van de tag en SHA-256-checksums worden daarna werkelijk gecontroleerd; deze nog niet bestaande pakketten worden hier niet vooraf als geslaagd gemeld.

Zie `BETA43_INSTELLEN.md` voor installatie, bediening en rollback.
