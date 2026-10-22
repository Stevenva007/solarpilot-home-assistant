from pathlib import Path
import re
r=Path.cwd()
old='1.0.0-beta.103'; new='1.0.0-beta.104'
for rel in ('custom_components/solar_pilot/manifest.json','custom_components/solar_pilot/const.py','custom_components/solar_pilot/frontend/solar-pilot-card.js','custom_components/solar_pilot/frontend/option-help.js','custom_components/solar_pilot/current_guide.py'):
 p=r/rel;s=p.read_text();s=s.replace(old,new)
 if rel.endswith('current_guide.py'):
  s=s.replace("GUIDE_UPDATED = '2026-10-21'", "GUIDE_UPDATED = '2026-10-22'").replace("'updated': '2026-10-21'", "'updated': '2026-10-22'")
  s=re.sub(r" 'intro': .*?\n", " 'intro': 'Beta.104 scheidt gewone tijdelijke onbereikbaarheid van echte opdrachtfouten. Controle afronden vraagt geen UIT-bevestiging meer aan een niet-betrokken offline toestel en wist diens herstelgegevens niet. Een ontbrekende Wallbox-uitlezing wordt informatief getoond zonder nutteloze resetknop. Andere toestellen blijven actuele P1-restzon gebruiken volgens hun eigen voorwaarden. Onzekere verzonden opdrachten, harde elektrische grenzen, instellingen en historie blijven beschermd.',\n",s,count=1)
  marker='\ndef render_markdown('
  at=s.index(marker)
  s=s[:at]+'''
# Release-specific recovery boundary: no global OFF prerequisite for source waits.
CURRENT_GUIDE['sections'][0]['paragraphs'].append(
    'Controle afronden beoordeelt echte fouten, niet gewone tijdelijke onbereikbaarheid. '
    'Een offline afwasmachine of andere bronwachter hoeft niet eerst UIT te bevestigen '
    'om een onafhankelijke fout af te ronden. De eigen wachttijd, onbekende toestand, '
    'lease en eenmalige aanvraag blijven bewaard. Een verouderde knop zonder echte '
    'fout doet niets en verstuurt geen toestelopdracht. Onzekere verzonden opdrachten '
    'vereisen passende nieuwe terugmelding; een oude of restored UIT is geen bewijs. '
    'Wallbox-telemetriewacht wordt informatief getoond zonder foutkleur of resetknop. '
    'Een dubbele koppeling blijft een zichtbare configuratiemelding. Actuele '
    'P1-restzon en alle bestaande toestel-, net-, fase- en kwartiergrenzen blijven leidend.'
)
''' +s[at:]
 p.write_text(s)
p=r/'OVERDRACHT.md';s=p.read_text().replace('<!-- solarpilot-handoff-version: '+old+' -->','<!-- solarpilot-handoff-version: '+new+' -->')
s=re.sub(r'Laatst bijgewerkt:.*?\n', 'Laatst bijgewerkt: **22 oktober 2026**. Actuele bron: **v1.0.0-beta.104**. Gewone bronwachters blokkeren geen onafhankelijke foutcontrole meer. Wallbox-telemetriewacht krijgt geen algemene resetknop. Echte onzekere opdrachten blijven beschermd. Bouwbasis: gepubliceerde beta.103 `8a81fc0ab5134d99d56da9941cbc5cfe0a8b7ecd`. Installatie/rollback: `docs/BETA104_INSTELLEN.md`; tests/publicatie: `docs/TESTRESULTATEN_BETA104.md`.\n',s,count=1)
start=s.index('## 2. Actuele basis');end=s.index('\nDe canonieke gebruikersuitleg',start)
s=s[:start]+'''## 2. Actuele basis

Bouwbasis: gepubliceerde beta.103 `8a81fc0ab5134d99d56da9941cbc5cfe0a8b7ecd`. Beta.104 wijzigt alleen foutcontrole en de typering/presentatie van Wallbox-onbereikbaarheid. De bestaande gewone P1-restzonverdeling is behouden en opnieuw getoetst met gelijktijdig offline Wallbox en afwasmachine. Geen opslag- of instellingenmigratie. Aquarea- en SDK-bronpins zijn ongewijzigd; de online releasegate blijft vereist. Actueel bewijs: `docs/TESTRESULTATEN_BETA104.md`; oudere resultaten zijn historische herkomst.
''' +s[end:]
s=s.replace('## 3. Absolute ontwerpregels\n', '''## 3. Absolute ontwerpregels

- `source_wait` is geen UIT-reviewvoorwaarde: nooit een onafhankelijk toestel laten wachten of een bronwachter wissen bij `reset()`. Onbekende source-only herstartleases blijven afzonderlijk onder reconciliatie. Alleen betrokken bewezen UIT-fouten worden afgehandeld. Een onzekere verzonden opdracht vraagt echte terugmelding na de opdracht; restored/oud UIT volstaat niet. Een lopende batterijopdracht mag door deze knop niet worden gewist. Zonder echte fout is een oude/directe resetaanroep een idempotente no-op zonder opslag of dispatch. Wallbox-telemetriewacht is `wallbox_wait`, dubbele koppeling `wallbox_configuration`; geen algemene resetknop voor beide. Dit verruimt geen elektrische of fysieke bevoegdheden.
''')
p.write_text(s)
p=r/'CHANGELOG.md';s=p.read_text();s=s.replace('# Changelog\n','# Changelog\n\n## 1.0.0-beta.104 — niet-blokkerende bronwachttijden en gerichte foutcontrole\n\n- Gewone offline bronwachters en onbekende source-only herstartleases zijn geen algemene UIT-voorwaarde voor Controle afronden. Hun status, eigendom, wachttijden en tickets blijven bewaard.\n- Alleen betrokken echte fouten worden afgewikkeld. Een onzekere verzonden opdracht vereist actuele niet-restored UIT-terugmelding na de opdracht; lopende batterijopdrachten worden niet gewist.\n- Verouderde of directe reset zonder echte fout is een no-op, zonder foutmelding, opslag of toestelopdracht.\n- Ontbrekende Wallbox-telemetrie is een informatieve wachtstatus zonder foutkleur of resetknop; dubbele koppeling blijft zichtbaar als configuratieprobleem.\n- Behoudt gewone P1-restzonverdeling, harde net-/fase-/kwartiergrenzen, beschermde cycli en alle gegevens. Geen nulaanname voor onbekend vermogen.\n- Zestien nieuwe synthetische regressies; installatie/rollback en bewijsgrenzen staan in `docs/BETA104_INSTELLEN.md` en `docs/TESTRESULTATEN_BETA104.md`.\n',1);p.write_text(s)
p=r/'README.md';s=p.read_text();idx=s.index('\n\n',s.index('\n\n')+2)
s=s[:idx]+'''\n\nBeta.104 herstelt de onterechte koppeling tussen **Controle afronden** en een gewone offline afwasmachine. Tijdelijke bronwachters houden hun automatische hercontrole en blokkeren geen onafhankelijke foutcontrole. Een ontbrekende Wallbox-uitlezing is informatief, zonder nutteloze resetknop. Andere toestellen mogen echte P1-restzon gebruiken zodra hun eigen voorwaarden gelden; echte opdrachtfouten en elektrische grenzen blijven beschermd. [Installatie en rollback](docs/BETA104_INSTELLEN.md) · [Testverslag](docs/TESTRESULTATEN_BETA104.md).''' +s[idx:]
s=s.replace('**'+old+'**','**'+new+'**').replace('[Beta.103 instellen](docs/BETA103_INSTELLEN.md)','[Beta.104 instellen](docs/BETA104_INSTELLEN.md)')
p.write_text(s)
install='''# SolarPilot beta.104 — gerichte foutcontrole zonder offline blokkering

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
'''
test='''# SolarPilot beta.104 — test- en publicatieverslag

Versie: **1.0.0-beta.104** · 22 oktober 2026

Bouwbasis: beta.103 `8a81fc0ab5134d99d56da9941cbc5cfe0a8b7ecd`. Alle fixtures zijn synthetisch. Privé-exportgegevens zijn niet opgenomen.

## Uitgevoerd vóór definitieve CI

- **203 bestaande gerichte regressies geslaagd**: toestelhercontrole, source waits, isolatie-UI, runtime en herstartmodus.
- **16 nieuwe regressies geslaagd** in `tests/test_nonblocking_review104.py`: gelijktijdige afwas-/Wallbox-onbereikbaarheid, gezonde restzonstart, geen start bij onvoldoende overschot, bewaarde eigendoms-/herstartgegevens, gerichte echte foutreview, oude/restored UIT na onzekere opdracht, bescherming lopende batterijopdracht, automatische Wallbox-herstelweergave en kaartteksten zonder resetknop.
- De volledige lokale suite kon niet als voltooid worden beoordeeld: drie modules vereisen de lokaal ontbrekende dependency voluptuous; een bredere proef zonder die modules is vóór voltooiing afgebroken. Dit is geen volledige-suite-pass.

## Vereiste definitieve validatie

De ongewijzigde Validate-workflow moet op de definitieve bron alle vijf gates laten slagen: repository/privacy/documentatie/upstream en volledige pytest-suite, HACS, Hassfest, echte Home Assistant-start en Chromium. De status van de bijbehorende GitHub-run is het actuele bewijs; dit bestand claimt geen al voltooide toekomstige run, merge, release of gebruikersinstallatie.

De online upstreamgate controleert opnieuw defaultbranches, HEADs, laatste stabiele releases en tagcommits. De inhoudelijk beoordeelde Aquarea 1.8.1- en SDK 1.4.0-pins zijn behouden; nieuwe upstreamwijzigingen blokkeren publicatie tot beoordeling.

## Grenzen

Geen opslagmigratie, nulaanname bij onbekend vermogen of uitbreiding van actuatorrechten. Echte opdrachten en elektrische guards blijven beschermd. Een gewone bronwachter wordt nooit door een onafhankelijke foutreview gewist; herstel kan alleen door passende echte brongegevens worden vastgesteld. Softwaretests bewijzen geen fysieke toestelwerking of uitgevoerde Home Assistant-installatie.

## Releasebestanden

Na alle vereiste gates publiceert de bestaande workflow exact `v1.0.0-beta.104` met de volledige GitHub-HACS-ZIP, lokale component-ZIP en beide beta.104-documenten. Voor en na upload worden de vier assets vergeleken met dezelfde bron. Geen bestaande tag of asset overschrijven. Dit verslag en de installatiehandleiding hebben bytegelijke componentmirrors.
'''
for name,body in [('BETA104_INSTELLEN.md',install),('TESTRESULTATEN_BETA104.md',test)]:
 for prefix in ['docs','custom_components/solar_pilot/docs']:
  (r/prefix/name).write_text(body)
