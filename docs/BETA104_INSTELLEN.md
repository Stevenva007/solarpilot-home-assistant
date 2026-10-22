# SolarPilot beta.104 — gerichte foutcontrole zonder offline blokkering

Versie: **1.0.0-beta.104** · 22 oktober 2026

Bouwbasis: beta.103 `8a81fc0ab5134d99d56da9941cbc5cfe0a8b7ecd`.

## Wat is hersteld

De algemene foutcontrole nam ook gewone tijdelijke bronwachters op in de lijst van toestellen die eerst UIT moesten bevestigen. Een offline afwasmachine kon dat niet. Bovendien verscheen bij een ontbrekende Wallbox-uitlezing ten onrechte de knop Controle afronden.

Beta.104 laat gewone bronwachttijden en onbekende source-only herstartleases bij hun eigen automatische hercontrole. Zij blokkeren geen onafhankelijke foutcontrole en worden daarbij niet gewist. Een oude knop zonder echte fout is een veilige no-op. Wallbox-telemetriewacht krijgt een informatieve melding zonder resetknop; een dubbele koppeling blijft een configuratiemelding.

Andere gezonde toestellen kunnen de actueel gemeten resterende zon blijven benutten volgens hun eigen voorwaarden. Onbekend laadvermogen is geen 0 W en geeft geen vermogenskrediet. Zonder echt overschot blijft een gewone zonnegestuurde last terecht wachten. Een onzekere verzonden opdracht, lopende batterijopdracht, ontbrekende essentiële netmeting, echte fout of elektrische grens blijft beschermd. Geen garantie op nulimport of foutloze fysieke apparatuur.

## Bijwerken

1. Maak een volledige privé Home Assistant-back-up, inclusief opslag, modellen, historie en userfiles. Behoud de bestaande integratie-entry.
2. Werk via HACS bij naar **1.0.0-beta.104** zodra die geteste release is gepubliceerd. Bij lokale installatie vervang je alleen de bestanden onder `custom_components/solar_pilot`; behoud userfiles en opslag.
3. Herstart Home Assistant volledig en herlaad de app/browser. Controleer dat backend én kaart beta.104 tonen.
4. Een niet-vrijgegeven/offline afwasmachine mag blijven wachten. Er is geen algemene UIT-controle nodig. De bestaande hercontrole beoordeelt haar opnieuw op actuele gegevens; een oude aanvraag of onzekere START wordt niet blind herhaald.

Geen nieuwe instelling, reset van historie, integratieherinstallatie, SG-herbevestiging of bronkoppeling is nodig. Een echte bestaande interne foutpauze moet nog gericht worden beoordeeld; deze update zet die niet blind op Automatisch.

## Rollback

Beta.103 gebruikt dezelfde opslag en instellingen. Terugzetten vraagt geen migratie, maar brengt de foutcontrole-/weergavefout terug. Behoud dezelfde entry, modellen, historie en userfiles. Herstart Home Assistant en herlaad de app/browser.

[Testresultaten en beperkingen](TESTRESULTATEN_BETA104.md) · [Actuele werking](ACTUELE_WERKING.md)
