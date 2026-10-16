# SolarPilot beta.94 — installatie en upgrade

Versie: **1.0.0-beta.94** · 16 oktober 2026

Beta.94 voorkomt dat een Home Assistant-herstart of integratieherlaad de minimale rusttijd van een al uitgeschakeld toestel opnieuw laat beginnen. SolarPilot bewaart de bevestigde UIT-tijd en gebruikt na een passende actuele UIT-controle alleen de resterende tijd. De tijd tijdens de herstart telt mee.

Voorbeeld: bij 30 minuten minimale rust, 10 minuten al verstreken en 2 minuten herstart blijven **18 minuten** over. Was de rusttijd al verstreken, dan begint er geen nieuwe rusttijd alleen door het herstarten. De overige actuele startvoorwaarden blijven gelden.

## Bijwerken

1. Bewaar een actuele volledige privé Home Assistant-back-up, inclusief SolarPilot-opslag en userfiles.
2. Geef een eigen SG-aanvraag veilig vrij waar betrouwbaar mogelijk; onderbreek geen beschermde apparaatcyclus.
3. Installeer **1.0.0-beta.94** via HACS nadat de release gepubliceerd is. Behoud dezelfde integratie-entry, instellingen en opslag.
4. Herstart Home Assistant volledig en herlaad browser/app. Controleer backend- en kaartversie afzonderlijk.
5. Controleer bij een volgende herstart dat de resterende rusttijd verder afloopt zodra de toestelgegevens betrouwbaar zijn.

Er is geen nieuwe instelling of sensor nodig. Wijzig de ingestelde rusttijd niet om deze softwarefout te omzeilen.

## Eerste upgrade en ontbrekend bewijs

Beta.93 en ouder bewaarden de oorspronkelijke UIT-tijd niet. Bij de eerste upgrade kan daarom nog eenmaal de volledige rusttijd nodig zijn. Beta.94 bewaart vervolgens de bevestigde tijd voor volgende herstarts. Een oude tijd wordt niet gegokt of achteraf uit een screenshot afgeleid.

Een echte nieuwe AAN-naar-UIT-overgang begint een nieuwe rusttijd. Een onbekende of herstelde placeholderstatus, onzekere opdracht, gewijzigde toestel-/bronkoppeling of onbruikbare tijdregistratie geeft geen verkorting. Een onbereikbaar toestel mag niet starten door alleen een opgeslagen tijd. Lopende minimumlooptijden en alle bestaande toestel-, bron- en elektrische voorwaarden blijven gelden.

De vijfminutenbuffer voor stabiel zonneoverschot is een andere voorwaarde dan de minimale rusttijd. Die buffer wordt na een herstart opnieuw op echte actuele metingen beoordeeld. Voldoende overschot alleen maakt een toestel met resterende rusttijd niet startklaar.

## Rollback

Herstel zo nodig beta.93 met behoud van entry, instellingen, opslag en userfiles en herstart Home Assistant volledig. Gebruik geen twee runtimes tegelijk. Beta.93 kan de rusttijd bij een herstart opnieuw laten beginnen. De taakherkennings-, Wallbox- en meldingscorrecties uit die versie blijven daarin beschikbaar.

[Actuele werking](docs/ACTUELE_WERKING.md) · [Testverslag](docs/TESTRESULTATEN_BETA94.md) · [Overdracht](OVERDRACHT.md)
