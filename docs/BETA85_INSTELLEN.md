# SolarPilot 1.0.0-beta.85 — herstel van SG-dispatchopruiming

Beta.85 herstelt een gerichte fout: een vroege terugkeer bij een begrensde lokale SG-toestemming kon een bestaande finale controle verwijderen, waarna latere regelrondes stopten. Alleen een daadwerkelijk door dezelfde aanroep geplaatste tijdelijke controle wordt nu opgeruimd; de oorspronkelijke controle blijft intact.

De tijdelijke SG-keuzes **Aan/Uit voor 30/60 minuten**, absolute eindtijd, terugkeer naar Automatisch, oorspronkelijke sessiegrenzen, vijfminutenbuffer van de inschakelklok, verse herstartcontrole en alle harde voorwaarden uit beta.84 blijven behouden. De lokale toestemming blijft standaard 300 seconden met vernieuwing iedere 60 seconden. Geen native Panasonic-write of gegevensreset.

## Upgrade en herstellen uit foutpauze

1. Maak een volledige privé Home Assistant-back-up met instellingen, eigen opslag, modellen, APP-aanvragen, historie en userfiles. Bewaar gecontroleerde beta.84-code.
2. Geef een eigen SG-aanvraag veilig vrij waar betrouwbaar mogelijk en controleer contact/lokale afloop. Onderbreek geen beschermde apparaatcyclus. Een onbekende stand blijft onbekend; herhaal geen onzekere opdracht.
3. Update via HACS naar exact `1.0.0-beta.85` nadat de releasegates en publicatie zijn geslaagd. Lokaal vervang je uitsluitend `custom_components/solar_pilot`, met behoud van userfiles en HA-opslag.
4. **Herstart Home Assistant volledig.** Alleen bestanden vervangen, de kaart herladen of een browsercache verversen vervangt geen geladen Python-module. Herlaad ook browser/app volledig en controleer backend- en kaartversie afzonderlijk.
5. Staat SolarPilot door een eerdere interne fout nog in **Pauze**, controleer de concrete melding, kies **Controle afronden** en daarna bewust **Automatisch regelen**, zodra actuele controles dit toelaten. Een bestaande interne foutpauze blijft beschermd; deze update wist haar niet automatisch. Een gewone opgeslagen gebruikerspauze houdt haar bestaande hervatvoorkeur.
6. Controleer actuele SG-contactstand, lokale timer en beslisreden, tijdelijke keuze/deadline en overige toestellen. Bestaande bronnen, prioriteiten, bevestigingen, modellen, geschiedenis en APP-tickets blijven behouden. Verwijder of hermaak de entry niet.

Blijft een concrete fout terugkomen, bewaar de melding en maak een nieuwe privé-analyse-export met de geladen versie. Wis geen opslag en stuur geen native temperatuur-, programma- of heateropdracht als herstelroute. De loaded backend-/kaartversie en de versie van programmabestanden zijn afzonderlijk bewijs; een verschil bewijst op zichzelf geen oorzaak.

## Behoud

Panasonic regelt zelfstandig comfort, warm water, verwarmen/koelen, ondersteuning, ontdooien en sterilisatie. SolarPilot bedient uitsluitend het toegewezen SG-contact. Wallbox blijft read-only; AEG krijgt maximaal één START per geldige nieuwe belading en mag afwerken. Gewone automatische SG behoudt 600 W gedurende vijf continue minuten, minimum twintig minuten, bestaande harde maximum en expliciete geldige gebruikerswaarden. De korte startonderbrekingsbuffer geeft geen AAN op oude of ontbrekende gegevens.

De tijdelijke SG-bediening en herstartvoorwaarden staan volledig in [ACTUELE_WERKING.md](ACTUELE_WERKING.md). Deze hotfix verandert die policy niet.

## Rollback naar beta.84

Geef de eigen SG-aanvraag veilig vrij en controleer contact/lokale afloop. Bewaar een actuele volledige privéback-up, stop beta.85 en herstel gecontroleerde beta.84-code met behoud van entry, opslag en userfiles. Herstart HA volledig en herlaad app/browser.

Beta.84 behoudt dezelfde tijdelijke bediening en timers, maar **herintroduceert de gerepareerde dispatchfout**; rollback naar die versie is geen oplossing voor deze fout. Laat nooit twee runtimes tegelijk werken. Code terugzetten mag geen tweede START, oude AAN-replay of automatisch opgeheven foutpauze vrijgeven. Exact herstel vraagt code én een passende volledige privéback-up; herstel geen oude onverbruikte APP-aanvraag bij een inmiddels gestart programma.

Brongebonden software-/CI-/pakketbewijs: [TESTRESULTATEN_BETA85.md](TESTRESULTATEN_BETA85.md). Privé-exports, entiteiten, woninggegevens en fouten uit de eigen installatie horen niet op GitHub.
