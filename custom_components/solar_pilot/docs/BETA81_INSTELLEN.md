# SolarPilot 1.0.0-beta.81 — SG-onderzoek en controleerbaar bronbewijs

Beta.81 herstelt de concrete tijdtypefout waardoor de bestaande SG-onderzoeksfunctie geen runtime-metingen ontving. De recorder gebruikte een datumobject; de onderzoeksfunctie vereiste numerieke seconden. De omzetting gebeurt uitsluitend op de onderzoeksgrens. Warmtepompgeschiedenis en apparaatbesturing behouden hun eigen werking.

Nieuwe begrensde onderzoeks- en historiegegevens maken onderbrekingen, controllerstop, contactbewijs, transportfase, tankcontext en oorspronkelijke meter-/forecasttijden beter te beoordelen. Een onderbroken SG-onderzoek wordt als onvolledig historisch record bewaard, zonder een actieve aanvraag, lease, tijdcontinuïteit of apparaatopdracht te herstellen. Historische ontbrekende metingen worden niet achteraf ingevuld.

## Upgrade

1. Maak een volledige privé Home Assistant-back-up met instellingen, eigen opslag, PV-factoren, modellen, APP-aanvragen, historie en userfiles. Bewaar gecontroleerde beta.80-code.
2. Geef vóór codevervanging een eigen SG-aanvraag veilig vrij en controleer contact en lokale afloop. Onderbreek geen beschermde apparaatcyclus.
3. Update via HACS naar exact `1.0.0-beta.81` nadat releasegates en publicatie geslaagd zijn. Lokaal vervang je uitsluitend `custom_components/solar_pilot`, met behoud van userfiles en HA-opslag.
4. Herstart Home Assistant volledig, herlaad app/browser volledig en controleer backend- en kaartversie afzonderlijk onder **Instellingen & controle**.
5. Bekijk **Meetkwaliteit → Automatisch onderzoek**, de PV-diagnose en **Warmtepomp → Geschiedenis**. Nieuw SG-onderzoek begint bij nieuwe waarnemingen; een oude lege registratie krijgt geen verzonnen complete sessie.

Verwijder of hermaak de integratie niet. Geldige instellingen, bronbindings, prioriteiten, lokale Panasonic SG-percentages/koelwaarde, APP-deadlines en verbruikte beladingen blijven staan. Geen extra package, sensor, add-on of nieuwe hardware is verplicht. Een software-update maakt geen nieuwe AEG-START beschikbaar.

## Wat de aanvullende gegevens betekenen

| Gegevens | Betekenis en noodzakelijke controle |
|---|---|
| SG-onderzoek | Release, policy, oorspronkelijk bronbewijs en meetdekking horen bij dezelfde nieuwe sessie. Een onderbreking blijft onvolledig en niet vergelijkbaar; controllerafsluiting, gemeld contact en transportbewijs zijn afzonderlijk. |
| Negatieve warmtepompmeter | De ruwe waarde blijft diagnostisch zichtbaar en ongeldig voor een verbruikstotaal. Werkelijk gemeten nul blijft nul. Vergelijk lage en bekende positieve belasting met passend onafhankelijk bewijs voordat een meteraanpassing wordt overwogen. |
| Wallbox-brondossier | Oorspronkelijke rapporttijden en de werkelijk beschikbare bronrelatie helpen een oude template onderscheiden van verse oorspronkelijke bronnen. Onbewezen afhankelijkheden blijven onbekend; geen heartbeat, automatische koppeling of ruimere stale-grens. |
| Net/PV-coherentie | Ongelijk getimede rapporten en onbekende aanvullende productie/opslag verhinderen een zekere energiebalans. Een opvallend moment is een controlespoor, geen tekencorrectie of nieuwe regelblokkering. |
| PV-kwartieren | Geldige en afgekeurde onderdelen verklaren de samenvatting. Een eindige mediaan maakt een onvolledig kwartier niet geschikt om te leren. De bestaande leercriteria blijven gelden. |
| Forecastvergelijking | Oorspronkelijke uitgiftetijd, lokale ontvangst en voorspellingstermijn blijven afzonderlijk. Een later ontvangen bijstelling bewijst geen eerdere voorspelkwaliteit. Onbekende uitgifte blijft onbekend. |
| Tank-/programmatijdlijn | Verse native taak, tanktemperatuur, gewoon doel, eventueel effectief doel, afzonderlijke voedingen en native voltooiing hebben ieder eigen bewijs. Temperatuur of watts boven het gewone doel bewijzen geen geslaagde sterilisatie. |
| Korte elektrische activiteit | Presentatie naast de ruwe historie verklaart korte metermomenten. Ruwe starts, stops, perioden en meetgaten blijven behouden; elektrische activiteit is geen bewezen compressorstart. |

## Behouden regeling

De standaard SG-importbuffer blijft **600 W gedurende vijf continue minuten**, met **twintig minuten minimum SG-aanvraag**. Beide zachte tijden moeten verstreken zijn; de tekorttijd reset op of onder de importgrens. Harde bron-, net-, fase-, kwartier-, batterij-, lease-, handmatige en voorrangsvoorwaarden kunnen eerder vrijgeven. Dit is geen minimum compressorlooptijd. De lokale lease blijft kort, standaard 300 s met vernieuwing om de 60 s.

Panasonic blijft read-only behalve het expliciet toegewezen bestaande SG-contact. Wallbox blijft read-only. AEG behoudt maximaal één native START per geldige nieuwe belading en de zonne-onafhankelijke deadline binnen alle echte apparaat- en elektrische grenzen. SG-onderzoek, geschiedenis en forecastbewijs verlenen geen actuatorrecht of nieuwe modeltoestemming.

## Rollback naar beta.80

Geef de eigen SG-aanvraag vrij, controleer contact/lokale afloop, stop beta.81 en herstel gecontroleerde beta.80-code met behoud van entry, actuele opslag en userfiles. De beta.80-providerherkenning en koelguards blijven beschikbaar. De beta.81-onderzoeksinnamefix en aanvullende bewijsgegevens vervallen; beta.80 kan daardoor opnieuw geen nieuwe SG-onderzoeksrecords verzamelen.

Exact herstel vraagt de passende volledige privéback-up. Bewaar gewenste nieuwe historie eerst. Herstel geen oude onverbruikte APP-aanvraag nadat dezelfde belading gestart of afgerond is. Laat nooit twee runtimes tegelijk werken en verwijder de entry niet.

Volledige werking: [ACTUELE_WERKING.md](ACTUELE_WERKING.md). Brongebonden tests en pakket/publicatiebewijs: [TESTRESULTATEN_BETA81.md](TESTRESULTATEN_BETA81.md). Softwareproeven bewijzen geen fysieke meterreparatie, compressorbedrijf, levensduurwinst, COP of causale SG-besparing.
