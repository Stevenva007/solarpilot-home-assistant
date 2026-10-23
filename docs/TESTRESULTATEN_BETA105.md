# Beta.105 — validatie en bewijsgrenzen

Bouwbasis: gepubliceerde beta.104, commit `f014edaf205f9e0cf7c95cc899fa30499e3cf091`.

## Lokaal uitgevoerd

55 nieuwe gerichte tests geslaagd (synthetische bronnen; geen huishouddata):

- meterclassificatie, handmatige/externe activiteit en onbekend begin;
- geen echte start-/stopopdracht of bevestiging van een onzekere SolarPilot-opdracht;
- korte pieken, bevestigingsduur, stille fasen en native activiteit/einde;
- originele rapporttijden, dubbele uitlezingen, stale/unknown/restored/estimated, verkeerde eenheden en ongeldige getallen;
- cumulatieve tellerstappen, reset, onmogelijke sprongen, meetgaten, daggrens en ontbrekende energiemeter;
- echte ConsumerHistoryRecorder met inerte opslag: externe sessie, onbekende meetgaten, onbevestigd einde, bronrechten, rebind en gewijzigde drempels;
- echte JavaScript-methoden in Node met inert DOM: cloud-onbereikbaar plus actuele meter, geen vrijgave van startknop, verlopen/ongeldige meterweergave.

Python-syntax van het component en Node-syntax van de kaart en optiehulp zijn gecontroleerd. De lokale omgeving bevat geen volledige Home Assistant-installatie; deze 53 tests zijn niet de volledige repositoriesuite of een praktijktest op een echt afwasprogramma.

## Verplichte publicatiecontroles

De bestaande GitHub Validate-workflow moet voor de exacte kandidaatcommit slagen: volledige testsuite, actuele upstreambronreview, HACS, Hassfest, browserregressies, echte Home Assistant-start en overige repository-/publicatiecontroles. Dit document claimt niet dat die controles al afgerond zijn. Hun werkelijke commitgebonden resultaten zijn leidend. Niet publiceren bij een mislukte of niet-afgeronde verplichte controle.

## Grenzen

Geen live koppeling of praktijkkalibratie op de installatie van een gebruiker uitgevoerd. Het kiezen van de lokale entiteiten is nog vereist. De voorlopige drempels zijn instelbaar en kunnen geen native programmafase bewijzen. Gemeten deelenergie is geen gegarandeerd volledig dag-/cyclusverbruik of toerekening aan zonne-energie. Geen eerdere ontbrekende beurt gereconstrueerd; geen fysieke actuator of cloudinstelling gewijzigd.
