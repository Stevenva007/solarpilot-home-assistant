# SolarPilot beta.95 — test- en publicatieverslag

Versie: **1.0.0-beta.95** · 17 oktober 2026

Bouwbasis: gepubliceerde beta.94-commit `913cd2ae98466576ad2a017d356199c13fffcedf`. Publieke regressies gebruiken uitsluitend fictieve bronnen en opdrachten. De privé-analyse is niet in bron of pakketten opgenomen.

## Gereproduceerde problemen

1. Een opgeslagen ouder SG-configuratieblok mist latere standaardvelden. Vergelijken met een volledig genormaliseerd formulier meldt daardoor stuurwijzigingen, ook als effectief alleen een weergavepercentage wijzigt. De actieve SG-sessie blokkeert dan onterecht de weergavewijziging. Een andere volgorde van dezelfde ruimtebronnen versterkt dit probleem.
2. Een oude afwasvoltooiing kan een huidige onbekende status overschrijven naar UIT. De export noemt die toestand geldig met rapporttijd 0. Historische voltooiing en actuele bereikbaarheid worden daardoor vermengd.
3. Een algemene afgewezen SG-hercontrole verliest de concrete voorwaarde; een tekstcategorie schrijft vervolgens ten onrechte een handmatige/configuratiewijziging toe. Een bestaande expliciete onbereikbaarheidsmelding wordt juist niet herkend.
4. Dagelijkse EMS-registratie behandelt ontbrekend PV als 0 W en telt het interval als algemene meettijd. Het zelfverbruikspercentage mist een afzonderlijke aanwijzing voor onvolledige PV-dekking.

## Correcties en bewijsgrenzen

Effectieve SG-wijzigingen worden vóór de blokkeerbeslissing vergeleken. Alleen visuele wijzigingen krijgen de bestaande directe route; echte bron-, regel- en toestemmingswijzigingen houden hun wachtgrens. Bestaande wachtende voorstellen en gelijktijdige wijzigingen blijven gevalideerd. Een update verleent geen ontbrekende lokale profielbevestiging.

De actuele afwaswaarneming gebruikt het oorspronkelijke bruikbare bronbewijs. Historische voltooiing en een eenmalig nieuw waargenomen einde houden hun eigen tijd. Onbereikbaarheid wordt geen actuele UIT-status, geen nulmeting en geen nieuwe START-toestemming.

Nieuwe SG-stopdetails leggen alleen werkelijk bekende afgewezen voorwaarden vast. Oude generieke meldingen behouden een onbekende specifieke oorzaak; een tekstmatch mag geen handmatige ingreep bewijzen. De finale stuurcontrole, lokale timer, minimumduur en harde grenzen behouden hun betekenis.

PV-meettijd, ontbrekende tijd en legacy-onbekende dekking worden afzonderlijk bewaard. Geldige nulmetingen blijven geldig; onbruikbare PV-waarden leveren geen zonne-energie of dekking op. Oude totalen krijgen geen verzonnen huidige dekking. Onbekende toekomstige kwaliteitsvelden blijven behouden zonder ze als huidig bewijs te gebruiken.

## Verificatie

De volledige lokale suite op de afgeronde functionele bron is geslaagd: **7.178 tests in 141,61 seconden** (Python 3.12). Een eerdere tussenstand had 7.153 geslaagde tests; die wordt niet als extra onafhankelijke score opgeteld. De nieuwe eindgrensregressies zijn vervolgens ook in de volledige eindrun opgenomen.

Gerichte routes zijn afzonderlijk geslaagd: 269 SG-liveconfiguratietests, 382 afwas-/herstel-/exporttests, 156 EMS-/kosten-/export-/kaarttests en 1.505 SG-/grensbewakingstests. Deze groepen overlappen elkaar en de volledige suite. Een onafhankelijke reviewer behaalde daarnaast 186 gerichte controles en vond geen verruiming van bron- of actuatorrechten.

Publieke-inhoudcontrole, overdrachtscontrole, canonieke gids-/mirror-/optiehulpcontrole, SG-bevoegdheidsgrens, Python-syntax en diffcontrole zijn geslaagd. De gids heeft regel-hash `d14d83b9ffc8a816`. De gewijzigde kaart is in Node getest, inclusief ontbrekend SG-doel en gedeeltelijke PV-dekking. De volledige Chromium-acceptatie, PowerShell-publisherproeven en echte Home Assistant Core-startup/reload/unload worden door de verplichte GitHub-gates op de exacte commit uitgevoerd vóór samenvoegen en publicatie.

Dit zijn softwareproeven met fictieve brongegevens; er zijn geen live toestelopdrachten gegeven. Het oude herstart-/Wallboxgedrag en oorspronkelijke opdracht-/tijdsbescherming blijven in de regressies opgenomen.

## Upstream en publicatie

Op 17 oktober 2026 zijn de defaultbranches, laatste stabiele releasetags/commits en SDK PR12 opnieuw gecontroleerd. Aquarea 1.5.4 en aioaquarea-ng 1.3.1 zijn ongewijzigd; PR12 blijft open en ongepubliceerd. Het actuele broncheckpoint wordt door CI opnieuw online gecontroleerd.

Alle vijf verplichte gates moeten op dezelfde definitieve bron slagen: repository/privacy/documentatie met de volledige testsuite en PowerShell-regressies, HACS, Hassfest, echte Home Assistant-startup/reload/unload en Chromium. De [Validate-workflow](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml) bewaart het brongebonden bewijs. Pas daarna worden de annotated tag en vier assets gepubliceerd:

- `SolarPilot-v1.0.0-beta.95-GitHub-HACS.zip`
- `SolarPilot-v1.0.0-beta.95-local.zip`
- `BETA95_INSTELLEN.md`
- `TESTRESULTATEN_BETA95.md`

De publicatiejob downloadt alle vier assets opnieuw en controleert bronbytes, grootte en SHA-256 tegen de exacte tag. Bestaande tags en assets worden niet overschreven. Softwaretests en pakketcontrole bewijzen geen installatie of fysieke Panasonic-/Shelly-/AEG-acceptatie. Er wordt geen live apparaatproef uitgevoerd.
