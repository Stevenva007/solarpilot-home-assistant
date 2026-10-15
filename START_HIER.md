# SolarPilot beta.92 — minder meldingen

Beta.92 verwijdert de terugkerende algemene melding **Analyse nodig**. Gewone analysebevindingen blijven bij Meetkwaliteit en Export, ook wanneer de vroegere meldingsvoorkeur nog aanstaat. Lokaal onderzoek en gegevensverzameling gaan door. Dringende regelingsfouten en bewezen Aquarea-incompatibiliteit behouden hun gerichte meldingen.

## Bijwerken

1. Bewaar een actuele volledige privé Home Assistant-back-up met SolarPilot-opslag en userfiles.
2. Geef een eigen SG-aanvraag veilig vrij waar betrouwbaar mogelijk; onderbreek geen beschermde apparaatcyclus.
3. Installeer exact **1.0.0-beta.92** via HACS zodra de release beschikbaar is. Behoud dezelfde integratie-entry, instellingen, opslag en userfiles.
4. Herstart Home Assistant volledig en herlaad browser/app. Controleer backend- en kaartversie afzonderlijk.
5. De eerste geslaagde leercontrole ruimt de oude algemene analysemelding op. Open bevindingen blijven beschikbaar bij Meetkwaliteit en Export. Andere meldingen worden niet verwijderd.

Alle Aquarea-, PV-, leer-, SG- en toestelherstelverbeteringen uit beta.91 blijven behouden. De actuele Aquarea- en SDK-bron zijn opnieuw gecontroleerd; hun gecontroleerde commits en releases zijn ongewijzigd.

Rollback naar beta.91 kan de algemene analysemelding opnieuw toelaten als de vroegere voorkeur aanstaat. Behoud entry, opslag en userfiles; herstart HA na codevervanging. Gebruik geen twee runtimes tegelijk.

[Installatie en rollback](docs/BETA92_INSTELLEN.md) · [Tests en publicatie](docs/TESTRESULTATEN_BETA92.md) · [Actuele werking](docs/ACTUELE_WERKING.md) · [Technische overdracht](OVERDRACHT.md)
