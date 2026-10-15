# SolarPilot 1.0.0-beta.88 — Wallbox voorrang geven

**Wallbox voorrang geven** is een algemene en individuele voorkeur voor autonoom autoladen. Zij verandert de verdeling van flexibele SolarPilot-last via de bestaande voorrangsregels. De opgeslagen rangorde blijft behouden; **Automatisch** gebruikt die huidige rangorde opnieuw.

## Keuzes en aftelklok

| Keuze | Weergave en afloop |
|---|---|
| 30 min | Aftelklok tot de oorspronkelijke eindtijd, daarna Automatisch. |
| 1 uur | Aftelklok tot de oorspronkelijke eindtijd, daarna Automatisch. |
| 2 uur | Aftelklok tot de oorspronkelijke eindtijd, daarna Automatisch. |
| 3 uur | Aftelklok tot de oorspronkelijke eindtijd, daarna Automatisch. |
| 4 uur | Aftelklok tot de oorspronkelijke eindtijd, daarna Automatisch. |
| 5 uur | Aftelklok tot de oorspronkelijke eindtijd, daarna Automatisch. |
| Tot terugschakelen | **tot ik terug op automatisch zet**; geen aftelklok. |
| Automatisch | De huidige opgeslagen rangorde geldt weer. |

Op de SolarPilot-kaart kies je een duur vóór activering. In Home Assistant zijn ook een schakelaar en keuzelijst beschikbaar. Een gewone schakelaar AAN kiest standaard **30 minuten**. UIT kiest **Automatisch**. De voorkeur start of versnelt de auto niet rechtstreeks: SolarPilot stuurt geen Wallbox-opdracht.

## Algemeen en individueel

- Algemeen activeren kopieert de gekozen duur en dezelfde eindtijd naar de op dat moment aanwezige ondersteunde flexibele toestellen en optionele SG-zonneboost.
- Daarna blijft ieder toestel apart bedienbaar. Je kunt een toestel terug op Automatisch zetten, een andere tijdelijke duur kiezen of de blijvende keuze gebruiken. Een eigen tijdelijke wijziging krijgt haar eigen eindtijd; de algemene aftelklok blijft gelijk.
- Een nieuwe algemene keuze wordt opnieuw naar de betrokken individuele keuzes gekopieerd.
- **Algemeen terug naar Automatisch wist alle individuele uitzonderingen**, handmatig én wanneer de algemene tijd afloopt. Dat geldt ook voor tussentijds afwijkende of blijvende toestelkeuzes.
- Is algemeen al Automatisch maar staat nog een toestel anders? **Alle toestellen terug op Automatisch** wist alle individuele uitzonderingen samen.
- Wanneer alleen een individuele tijd afloopt, blijven de andere toestelkeuzes staan.

Voorbeeld: algemeen 1 uur, daarna één toestel op 3 uur. Bij afloop van het algemene uur keert ook dat toestel terug naar Automatisch. Wil je één toestel langer laten afwijken, kies die individuele uitzondering nadat de algemene keuze weer Automatisch is.

## Welke toestellen meedoen

De voorkeur geldt alleen voor ondersteunde flexibele SolarPilot-verbruikers en, waar beschikbaar, de optionele SG-zonneboost. De afwasmachine heeft deze keuze niet. Algemeen inschakelen voegt daar geen nieuwe startblokkering toe: haar bestaande APP-toestemming, deur-/apparaatvoorwaarden, deadline, elektrische ruimte en regelmodus blijven gelden. Een lopende beurt blijft beschermd.

Bij de warmtepomp betreft deze keuze uitsluitend extra SG-zonneboost. Panasonic blijft zelfstandig comfort, tank, verwarmen/koelen, compressor, ondersteuning en sterilisatie verzorgen. Gewone SG staat al achter de Wallbox; deze keuze geeft nooit toestemming om EV-vermogen voor SG over te nemen. De afzonderlijke tijdelijke SG-Aan/Uit-keuze blijft haar eigen voorwaarden houden. De nieuwe tijdelijke voorkeur blokkeert een nieuwe SG-start en respecteert bij een lopende aanvraag de oorspronkelijke bevestigde minimumduur. Bestaande vrijgavegronden blijven gelden: bestaande Wallbox-/EV-, elektrische, koel-, bron-, handmatig Uit- en communicatieregels kunnen eerder vrijgeven. Panasonic-comfort wordt hierdoor niet uitgeschakeld. Native comfort, read-only apparaten en batterijen krijgen hiermee geen nieuwe bediening.

## Rustig en veilig wijken

De actuele laadvraag, betrouwbare Wallbox-bronnen, bestaande hysterese, klein-overschotregel en veilige overdracht blijven bepalend. Een lager toestel kan klein niet door de auto bruikbaar overschot volgens de bestaande regels benutten. Minimumlooptijden en beschermde cycli worden niet verkort; een stopverzoek is nog geen vrijgekomen vermogen. Nieuwe net-/PV-metingen en bestaande terugmelding blijven nodig.

De voorkeur geeft geen ruimere net-, fase- of kwartiergrens. Alleen bekijken en Pauze geven geen nieuwe fysieke opdracht; de bewaarde voorkeur en haar eindtijd kunnen wel doorlopen. Handmatige SolarPilot-bediening, echte externe overname, fouten en onzekere opdrachten houden hun eigen bescherming.

## Herstart en tijd

Elke tijdelijke keuze bewaart een absolute eindtijd. Herladen, browser sluiten of Home Assistant-herstart begint de duur niet opnieuw. Is een algemene keuze tijdens afwezigheid afgelopen, dan wordt zij bij herstel Automatisch en vervallen ook de individuele uitzonderingen. Een blijvende keuze blijft herkenbaar staan met **tot ik terug op automatisch zet**. De aftelklok is een voorkeurstimer, geen bewijs dat de auto werkelijk laadt.

## Upgrade vanaf beta.87 of ouder

1. Maak een volledige privé HA-back-up met instellingen, SolarPilot-opslag, modellen, APP-aanvragen, historie en userfiles. Bewaar gecontroleerde beta.87-code.
2. Geef vóór codevervanging een eigen SG-aanvraag veilig vrij waar betrouwbaar mogelijk en controleer contact of lokale afloop. Onderbreek geen beschermde cyclus; herhaal geen onzekere opdracht.
3. Update via HACS naar exact `1.0.0-beta.88` nadat releasegates en publicatie geslaagd zijn. Lokaal vervang je uitsluitend `custom_components/solar_pilot`, met behoud van userfiles en HA-opslag.
4. **Herstart Home Assistant volledig** en herlaad browser/app volledig. Controleer backend- en kaartversie afzonderlijk.
5. Controleer de nieuwe algemene/individuele voorkeur, tijdelijke aftelklok en Auto-terugkeer. Een bestaande opgeslagen rangorde, toestelbinding of geldige toestemming wordt niet door deze update herschreven. De update activeert geen nieuwe voorkeur.
6. Controleer SG-contact/timers, AEG-aanvraag/deadline, andere toestellen en geschiedenis. Verwijder of hermaak geen entry. Een bestaande interne foutpauze blijft beschermd; rond na controle de melding af en kies bewust Automatisch regelen zodra de voorwaarden dat toelaten.

## Behoud

Beta.87-HP-negatief-naar-nulinterpretatie met bronbewijs, beta.86-restzonherbeoordeling en Aquarea-presentatie, beta.85-callbackfix en eerdere SG-bediening blijven behouden. Gewone SG houdt twintig minuten minimum voor zachte importvrijgave en de nieuwe tijdelijke voorkeursvrijgave, 600 W gedurende vijf continue minuten, bestaande maximumduur, korte lokale lease, startbuffer, actuele herstartcontrole en alle harde guards. Geen nieuwe Panasonic- of Wallbox-write, instellingenreset, oude historieaanvulling, compressorlooptijd- of besparingsgarantie.

## Rollback naar beta.87

Zet algemeen en alle individuele uitzonderingen terug op **Automatisch**. Geef een eigen SG-aanvraag veilig vrij waar betrouwbaar mogelijk en controleer contact of lokale afloop. Bewaar een actuele volledige privéback-up, stop beta.88 en herstel gecontroleerde beta.87-code met behoud van entry, opslag en userfiles. Herstart HA volledig en herlaad app/browser.

Beta.87 voert deze nieuwe tijdelijke Wallbox-voorkeuren niet uit en gebruikt haar bestaande rangorde. Zij behoudt de HP-nulinterpretatie en eerdere SG-/Aquarea-fixes. Nieuwe opslagvelden kunnen bij een oudere opslagwrite wegvallen; een volledige privéback-up blijft nodig voor exact herstel. Geen oude onverbruikte APP-aanvraag bij een gestart programma, tweede START, oude AAN-replay, twee runtimes tegelijk of entryverwijdering.

Actuele werking: [ACTUELE_WERKING.md](ACTUELE_WERKING.md). Eigen software-/CI-/pakketbewijs: [TESTRESULTATEN_BETA88.md](TESTRESULTATEN_BETA88.md). Privé-exports, entiteiten en woninggegevens horen niet op GitHub.
