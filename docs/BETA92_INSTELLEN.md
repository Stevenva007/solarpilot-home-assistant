# SolarPilot beta.92 — alleen gerichte urgente meldingen

Versie: **1.0.0-beta.92** · 15 oktober 2026

De algemene melding **Analyse nodig** wordt niet meer aangemaakt. Een gewijzigde bevinding, een nieuwe revisie of een verstreken dag maakt een analysepunt niet dringend. De bevindingen blijven bij Meetkwaliteit en Export; onderzoek, modellen en gegevensverzameling blijven werken.

Dringende regelingsfouten en bewezen Aquarea-incompatibiliteit behouden hun bestaande gerichte meldingen, inclusief afhandeling na herstel. Een tijdelijke onbereikbaarheid blijft de bestaande vijfminuten-herstelroute volgen.

## Installeren

1. Bewaar een actuele volledige privé Home Assistant-back-up, inclusief SolarPilot-opslag en userfiles.
2. Geef een eigen SG-aanvraag veilig vrij waar betrouwbaar mogelijk; onderbreek geen beschermde apparaatcyclus.
3. Installeer **1.0.0-beta.92** via HACS na geslaagde publicatie. Lokaal vervang je uitsluitend `custom_components/solar_pilot`; behoud userfiles, entry, instellingen en opslag.
4. Herstart Home Assistant volledig en herlaad browser/app. Controleer backend- en kaartversie.
5. Bij de eerste geslaagde leercontrole wordt uitsluitend de oude SolarPilot-analysemelding opgeruimd. Bij tijdelijk ontbrekende meldingsservice volgt later een nieuwe poging. De melding kan tot die geslaagde controle blijven staan.

Er is geen nieuwe instelling nodig. Ook een eerder opgeslagen ingeschakelde analysemeldingsvoorkeur maakt geen algemene melding meer. Bestaande instellingen, modellen, historie, deadlineaanvragen en SG-bevestigingen blijven behouden. De normale regeling wordt door deze meldingscorrectie niet gewijzigd.

## Aquarea-broncontrole

Beide actuele defaultbranches en laatste stabiele releasecommits zijn opnieuw gecontroleerd. Aquarea **1.5.4** en aioaquarea-ng **1.3.1** zijn ongewijzigd tegenover het bestaande beoordeelde broncheckpoint. De beta.91-capabilitycontrole en alle bron-/bedieningsgrenzen blijven behouden. Zie [UPSTREAM_BRONNEN.md](UPSTREAM_BRONNEN.md).

## Rollback

Herstel zo nodig beta.91 met behoud van entry, opslag en userfiles en herstart HA volledig. Geef een eigen SG-aanvraag veilig vrij waar betrouwbaar mogelijk en gebruik geen twee runtimes tegelijk. Beta.91 kan bij de oude ingeschakelde meldingsvoorkeur weer algemene analysemeldingen maken.

[Actuele werking](ACTUELE_WERKING.md) · [Testverslag](TESTRESULTATEN_BETA92.md) · [Overdracht](../OVERDRACHT.md)
