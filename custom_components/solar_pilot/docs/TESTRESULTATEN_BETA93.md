# SolarPilot beta.93 — test- en publicatieverslag

Versie: **1.0.0-beta.93** · 16 oktober 2026

Bouwbasis: gepubliceerde beta.92-commit `6eb4c49c743bcc5ca0e5aff2f3f7d15d0de55386`. De correcties betreffen de read-only bronmetadatahercontrole in `native_program.py` en de gewone/SG-vrijgave bij ontbrekende Wallbox-telemetrie in drie Wallboxguards en de finale SG-check. Er worden geen privé-exports, woningidentiteiten of echte apparaatopdrachten opgenomen.

## Oorzaak en correctie

De metadatahercontrole na 300 seconden maakte de eerdere metadata onmiddellijk onbruikbaar en leverde tijdelijk een onbekend broncontract op. Dat veroorzaakte korte onbekende taaksegmenten ondanks verse consistente echte bronrapporten. De hercontroletermijn wordt nu apart behandeld van de identiteit van de werkelijk geladen module en semantische implementatie.

Eerder geverifieerde metadata blijft uitsluitend bij dezelfde geladen identiteit en een lopende inspectie maximaal 30 seconden na de normale metadatahercontroletermijn beschikbaar. Een identiteitswisseling, afgeronde mislukte/onbekende/incompatibele inspectie of vastgelopen langere inspectie trekt het bewijs in. Dit verlengt geen echte poll-/meteractualiteit en wijzigt geen rapporttijd, bronbinding, leerclassificatie of actuatorrecht.

## Werkelijke restzon zonder Wallbox-afhankelijkheid

Drie Wallboxguards behandelden ontbrekende telemetrie als een algemene startblokkering, 0 W-cap of latere gedwongen gewone lastvrijgave. Zij laten nu uitsluitend werkelijk gemeten P1-restinjectie aan de gewone engine over. Een onbekende EV-meting wordt geen nul of EV-reclaimcredit. De per-toestelguard behoudt afzonderlijk haar blokkering bij onbruikbare actuele ruwe/gefilterde netmetingen. SG herleest de actuele Wallboxcontext vóór de finale capcontrole en kan geen oude nulcap blijven gebruiken.

Werkelijke bewezen laadvraag behoudt de gekozen voorrang. Een pending/overdracht/journal wordt niet afgerond door ontbrekende EV-data. Actuele bron-, batterij-, fase-, kwartier-, koel-, actuator- en toestelvoorwaarden blijven gelden. Eerdere beleidsasserties zijn gericht aan het nieuwe gebruikersbeleid aangepast; er zijn geen fysieke grenzen weggehaald.

## Gerichte verificatie

De nieuwe metadata-/broncontract-/historieroute behaalde **235 geslaagde tests**. De onafhankelijke bron-/leer-/bedieningsisolatiegroep behaalde **8 geslaagde tests**. Beide groepen zijn werkelijk uitgevoerd; eerdere releasetotalen gelden niet als beta.93-testbewijs.

De duurtest registreert 950 seconden met echte synthetische providerupdates en drie metadatahercontroles die elk tien seconden wachten. Het resultaat is één ononderbroken verwarmingssegment van 950 seconden, zonder onbekend segment en met oorspronkelijke rapporttijden en deadlines. Er ontstaan geen service- of provider-API-aanroepen.

Randgevallen omvatten de normale hercontrolegrens, de harde begrenzing van de achtergrondinspectie, slechts één lopende inspectie, module-/SDK-identiteitswisseling, gewijzigde registerbinding, mislukte/oude poll, oude of onbeschikbare entiteit, bronconflict, ontbrekende/oude passende meter en afgeronde onbruikbare inspectie. De leerclassificatie en eigen control-watchers blijven afzonderlijk en onveranderd.

De flexloadgroep behaalde **228 geslaagde tests**, waaronder 35 nieuwe gevallen met werkelijke runtime-starts bij ontbrekend/stale/ongeldig Wallboxvermogen in globale, huis- en per-toestelvoorrang. Nettoetsen, batterij, fase, kwartier, minimumlooptijd, beschermd programma, tekortstop en herstel van EV-data zijn afzonderlijk gedekt. De volledige gerichte SG-groep behaalde **1398 geslaagde tests**, inclusief de nieuwe 14 Wallbox-onafhankelijkheidstests. Deze groepen overlappen met oudere suites en worden niet tot een onafhankelijke totaalscore opgeteld.

De actuele Aquarea- en SDK-defaultbranches en laatste stabiele releasecommits zijn opnieuw online gecontroleerd: geen nieuwe relevante wijzigingen tegenover Aquarea 1.5.4 en aioaquarea-ng 1.3.1. Beide releasedocumenten hebben een bytegelijke componentmirror.

## Definitieve releasegates

De volledige Python-suite, repository-/privacy-/documentatiecontroles, HACS, Hassfest, echte Home Assistant-startup en Chromium draaien op de definitieve bron. Alle vijf verplichte CI-jobs moeten slagen voordat de main-publicatie begint. De [Validate-workflow](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml) bevat het brongebonden uitvoeringsbewijs; eerdere releases of gerichte aantallen vervangen dat niet.

Na die gates maakt de publicatiejob de nieuwe annotated tag en vier assets, downloadt ze terug en controleert bronbytes, grootte en SHA-256:

- `SolarPilot-v1.0.0-beta.93-GitHub-HACS.zip`
- `SolarPilot-v1.0.0-beta.93-local.zip`
- `BETA93_INSTELLEN.md`
- `TESTRESULTATEN_BETA93.md`

Er wordt geen bestaande tag of releaseasset overschreven. Softwaretests en pakketcontrole bevestigen geen installatie in de woning. Eerdere onbekende historie wordt niet herschreven; een echt ontbrekende taak blijft onbekend.
