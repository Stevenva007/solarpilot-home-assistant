# SolarPilot 1.0.0-beta.87 — negatieve warmtepompverbruikswaarden als nul

Beta.87 gebruikt verse, verder volledig geldige negatieve W/kW-waarden van de toegewezen **warmtepompverbruiksmeters als 0 W**. Dit geldt voor een exclusieve totaalmeter of toegewezen deelvoeding, binnen het bestaande plausibele bereik en pas na de gewone broncontroles. De oorspronkelijke bronwaarde, ruwe watts en normalisatiemarkering blijven inspecteerbaar.

Deze nul is de gekozen gebruikersinterpretatie, **geen bewezen meterkalibratie, correcte aansluiting of compressorstilstand**. De meter zelf, sensorbinding en tekeninstelling worden niet gewijzigd. Oude historie en eerdere exports worden niet opnieuw geïnterpreteerd.

## Wat als nul wordt behandeld

| Gegevens | Beta.87 |
|---|---|
| Verse eindige negatieve HP-verbruikswaarde met geldige bron, eenheid, bereik en dekking | 0 W als bruikbare interpretatie; ruwe waarde en markering blijven beschikbaar. |
| Werkelijk gemeten geldige nul | Blijft nul. |
| Ontbrekend, oud, toekomstig, NaN/oneindig, geschat, hersteld, verkeerde eenheid, overlap of anders onbruikbaar | Blijft onbekend. |
| Eén geldige deelvoeding en een ontbrekende/ongeldige andere | Bekende deelwaarde blijft zichtbaar; totaal blijft onbekend. |
| Net/P1, export, PV, batterij en fasen | Bestaande betekenis en tekens blijven behouden; geen negatieve-naar-nulbeleid. |

De regel maakt een onbekend totaal niet compleet en keert geen teken om. De SG-startbegroting krijgt geen extra warmtepompcredit uit nul. De volledige conservatieve extra-vraagraming, essentiële bronkwaliteit en harde voorwaarden blijven gelden. Een terugkerende bron wordt met haar volgende actuele kwaliteit beoordeeld; oude meetgaten worden niet ingevuld.

## Upgrade vanaf beta.86 of ouder

1. Maak een volledige privé HA-back-up met instellingen, opslag, modellen, APP-aanvragen, historie en userfiles. Bewaar gecontroleerde beta.86-code.
2. Geef een eigen SG-aanvraag veilig vrij waar betrouwbaar mogelijk en controleer contact/lokale afloop. Onderbreek geen beschermde cyclus en herhaal geen onzekere opdracht.
3. Update via HACS naar exact `1.0.0-beta.87` nadat releasegates en publicatie geslaagd zijn. Lokaal vervang je uitsluitend `custom_components/solar_pilot`, met behoud van userfiles en HA-opslag.
4. **Herstart Home Assistant volledig** en herlaad browser/app volledig. Controleer backend- en kaartversie afzonderlijk; bestanden vervangen bewijst geen geladen nieuwe Python-module.
5. Een bestaande interne foutpauze blijft beschermd: controleer de melding, kies **Controle afronden** en daarna bewust **Automatisch regelen**, zodra actuele controles dit toelaten. De update wist deze pauze niet automatisch.
6. Controleer HP-deelwaarden/totaaldekking, oorspronkelijke waarde en normalisatiemarkering, SG-contact/timer en overige apparaten. Behoud entry, bindings, volgorde en geldige bevestigingen; verwijder of hermaak niets.

Bij blijvende vragen over de echte meetkwaliteit blijft een nieuwe privé-export nodig. De software-interpretatie stelt geen fysieke oorzaak vast en herstelt geen meteraansluiting.

## Wat behouden blijft

De beta.86-herbeoordeling blijft uitsluitend voor lokaal bevestigd GENERAL met onbekende SG-reactie: na bestaande rust 300 s verse restzon met minstens twee originele rapporten, dan gewone startvertraging. Andere bewezen holds en DHW-only behouden hun voorwaarden. De actuele getypeerde Aquarea-weergave blijft display-only; native koelguards veranderen niet.

Beta.85-callbackfix, beta.84-tijdelijke Aan/Uit voor 30/60 min, absolute deadline/Auto-terugkeer, oorspronkelijke sessiegrenzen/importtimer, startbuffer en verse herstart blijven intact. Gewone SG behoudt minimum twintig minuten, 600 W gedurende vijf continue minuten en bestaande harde maximum. Lokale toestemming blijft standaard 300 s, vernieuwd iedere 60 s.

Panasonic blijft native eigenaar; SolarPilot bedient uitsluitend het toegewezen SG-contact. Wallbox blijft read-only; AEG krijgt maximaal één START per geldige nieuwe belading en mag afwerken. Geen gegevensreset, oude terugvulling, native Panasonic-write of automatische opheffing van foutpauze.

## Rollback naar beta.86

Geef de eigen SG-aanvraag veilig vrij en controleer contact/lokale afloop. Bewaar een actuele volledige privéback-up, stop beta.87 en herstel gecontroleerde beta.86-code met behoud van entry, opslag en userfiles. Herstart HA volledig en herlaad app/browser.

Beta.86 behoudt SG-herbeoordeling en eerdere fixes, maar behandelt negatieve HP-watts weer als onbruikbaar. Oude geschiedenis wordt niet opnieuw geïnterpreteerd. Exact herstel vraagt code én een passende privéback-up. Geen oude onverbruikte APP-aanvraag bij een gestart programma, tweede START, oude AAN-replay, twee runtimes tegelijk of entryverwijdering.

Actuele werking: [ACTUELE_WERKING.md](ACTUELE_WERKING.md). Eigen software-/CI-/pakketbewijs: [TESTRESULTATEN_BETA87.md](TESTRESULTATEN_BETA87.md). Privé-exports, entiteiten en woninggegevens horen niet op GitHub.
