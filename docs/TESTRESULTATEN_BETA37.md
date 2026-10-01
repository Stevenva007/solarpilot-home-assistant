# SolarPilot 1.0.0-beta.37 — testresultaten

Datum: 2026-10-01  
Codebasis: cumulatief op SolarPilot 1.0.0-beta.36.

## Geautomatiseerde GitHub-controle

De volledige Validate-workflow is groen op de beta.37-werkbranch voor de functionele code, releasegebonden uitleg en repositorycontroles.

- **Volledige Python-suite:** 1425 tests geslaagd.
- **Public repository privacy/structure:** geslaagd.
- **Overdrachtsdossier:** 1.0.0-beta.37 geslaagd.
- **Actuele release-uitleg:** 1.0.0-beta.37 geslaagd.
- **Python-syntax / compileall:** geslaagd.
- **HACS validation:** geslaagd.
- **Hassfest:** geslaagd.

## Belangrijke regressies in beta.37

Gecontroleerd wordt onder meer dat:

- de bestaande beta.36-prioriteitsvolgorde bij migratie behouden blijft;
- nieuwe gewone flexibele toestellen standaard onderaan de centrale lijst komen;
- een toestel alleen Wallbox-zonnevermogen mag benutten als het zowel boven de Wallbox staat als expliciete toestemming heeft;
- een toestel onder de Wallbox geen laadvermogen terugneemt, ook niet als een oude toestemming nog opgeslagen is;
- lopende cycli, minimumlooptijden en veiligheidsgrenzen niet door herordening worden opgeheven;
- de centrale prioriteitenlijst dezelfde rangorde aan realtime dispatch en planner doorgeeft;
- de beta.37-activering maar één keer wordt toegepast en latere keuzes niet opnieuw overschrijft;
- ontbrekende klimaat-, DHW-, fase- of Wallbox-bronnen niet door aannames worden vervangen;
- DHW niet automatisch wordt ingeschakeld zonder bestaande veiligheidsbevestiging;
- nieuwe toestellen niet automatisch van Uitgesloten naar Auto worden gezet;
- analyse-registratie live kan worden ingeschakeld zonder integratieherlaad;
- eenvoudige dashboardlabels en de centrale Export-/Voorrangstructuur aanwezig blijven.

## Grenzen

Dit zijn software-, repository- en integratievalidaties. Ze zijn geen fysieke acceptatietest van:

- de Panasonic Aquarea;
- de Wallbox;
- de AEG-afwasmachine;
- toekomstige Shelly-vermogensmetingen;
- de elektrische installatie of beveiligingen.

Na installatie hoort de eerste controle te bestaan uit het bekijken van de centrale voorrang, het controleren van de actieve/wachtende leermodules en het downloaden van een analyse-export na enkele dagen normaal gebruik.


## GitHub Actions en meldingen

De functionele beta.37-code is op de werkbranch volledig gevalideerd voordat de workflow-scope
werd aangescherpt. Om onnodige GitHub Actions-mails tijdens ontwikkeling te vermijden, start
`Validate` voortaan automatisch alleen bij een push naar `main` en bij pull requests naar
`main`. De vroegere dagelijkse schedule is verwijderd en een release-tag start niet nogmaals
`Validate`; de tag gebruikt alleen de bestaande `Release`-workflow.

Voor publicatie blijft daarom één finale groene `Validate`-run op de exacte beta.37-commit op
`main` verplicht, gevolgd door de `Release`-run voor `v1.0.0-beta.37`.
