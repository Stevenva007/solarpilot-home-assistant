# SolarPilot 1.0.0-beta.55 — testresultaten

Datum: **2026-10-05**

## Bronbasis en bewijsgrenzen

De codebasis is de gepubliceerde beta.54 op commit `8047742cf3fbb376792bb0730d7c0638923c03aa`, tree `b904876c53c8d136581ab1f12a0a1f17f7f5ef7f`, met annotated tag `c16bbde374ee09939e4e7ca28fb540dce17a1e72`. Release `403127618`, workflow `37220469340` en alle vier workflowjobs zijn gecontroleerd. Alle vier release-assets zijn gedownload en hun hashes gecontroleerd; beide ZIP-pakketten zijn inhoudelijk tegen de exacte bron vergeleken.

De beta.54-softwaregate behaalde lokaal 2877 geslaagde tests in 30.62 s en in CI 2877 in 24.49 s. Deze eerdere resultaten, hashes en publicatiecontrole zijn uitsluitend beta.54-bewijs. Zij worden niet als beta.55-test- of publicatieresultaat gebruikt.

Gebruikershistoriek bevat geen sample-per-versiestempel. Na meerdere updates kunnen oudere boilerdoel- en timerwaarnemingen niet zonder nieuw passend bewijs aan de huidige versie worden toegeschreven. Een analysebestand is geen bewijs dat alle historische samples met de daarin getoonde versie zijn gemaakt. Publieke regressies en voorbeelden gebruiken fictieve bronnen; privé-exportdata, installatie-identiteiten en echte entity_ids worden niet gepubliceerd.

## Softwaregate

**Volledige suite: 3064 tests geslaagd in 21.08 s**, Python 3.12.14, pytest 9.1.1. Uitgevoerd na de finale codewijzigingen met `PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider`. De suite behoudt de 2877 eerdere gevallen en voegt 187 synthetische regressiegevallen toe. Een tweede lezer controleerde de gewijzigde routes en vond geen blokkerende regressies.

| Onderdeel | Gecontroleerd gedrag | Resultaat |
| --- | --- | --- |
| Volledige samengestelde regressiesuite | Behouden en nieuwe regressies; geen actuator of live HA-contact | 3064 geslaagd |
| Uurlijkse weersforecast | Actuele temperatuur apart; geldige toekomstcurve tussen uurupdates; oorspronkelijke cacheleeftijd; begrensde minuutretry | Geslaagd |
| Forecastbescherming | Onbeschikbaar/restored, verkeerde eenheid, rebind, cacheverloop, mislukte opvraag en ontbrekende toekomstcurve | Geslaagd |
| DHW-koeladviescache | Geen hergebruik zonder nog geldige gekoppelde weersforecast | Geslaagd |
| Native PV-dag- en uurbronnen | Oude rapportage niet herlabelen; frisse nieuwe waarden opnieuw lezen; gelijke waarde met nieuwe rapportage; beide zomertijdwissels; gedateerde curves behouden | Geslaagd |
| Leerbronnen en afwijsredenen | Ongeldige, verouderde en restored acties; ontbrekende zone naast UIT; echte actieve context; afgewezen vermogensmeting behoudt eigen reden | Geslaagd |
| AEG nieuwe belading | Oude running-status met huidige READY; nieuwe APP-overgang; maandagaanvraag 08:30 met deadline 10:00; eenmaal START; geen herarming bij oude Enabled, deurannulering of onzekere START | Geslaagd |
| Syntax en publieke repositorychecks | 65 Pythonbestanden via AST; 4 JSONbestanden; beide frontendmodules via Node; publieke preflight, handoff, actuele uitleg, repository en diff | Geslaagd |
| Actuele uitleg, hulp en voorbeeld | Backend en beide frontendversies beta.55; beide uitlegmirrors; 437 hulpvelden; fictief offline voorbeeld opnieuw opgebouwd | Geslaagd |

De actuele regel-hash is `0e41b3f32ae816e2`. De algemene DHW-testfixture gebruikt geen kalenderafhankelijke sterilisatieplanning; de specifieke kalender-/herstarttest schakelt die planning expliciet in. Daarmee hangen gewone klimaat-/batterijtests niet af van een toevallige maandagmiddag. De echte sterilisatiebeveiliging is niet afgezwakt.

De AEG-regressie reproduceerde vóór de wijziging dat een bewaarde oude `running`-status een nieuwe APP-vrijgave blokkeerde ondanks actuele READY. READY wordt nu als einde niet bevestigd verwerkt, zonder fictief voltooiingsbewijs en zonder oude aanvraag terug te zetten. Een reeds geprobeerd onzekere START blijft geblokkeerd. Dit verklaart een mogelijke oorzaak van de getoonde tegenspraak, maar bewijst niet de precieze gebeurtenissen van een nieuwe ochtendbelading: de beschikbare eerdere export eindigt vóór die aanvraag. Een actuele export moet laten zien of die nieuwe aanvraag is geaccepteerd, geweigerd of later door een echte Running-melding verbruikt.

Wallbox-bronsemantiek en echte bronheartbeat zijn een afzonderlijk installatiepunt. SolarPilot verruimt hiervoor geen versheidsgrens en vertrouwt geen opgeslagen zonne-instelling als bewijs van een actuele autonome sessie. De bestaande read-only en conservatieve voorwaarden blijven onderdeel van de behouden regressies; herstel van een externe effectieve-sessiesensor wordt niet als door deze softwaregate bewezen voorgesteld.

De kalendercorrectie voor ongedateerde PV-bronnen bewijst geen nieuwe gekalibreerde voorspelnauwkeurigheid. Nachtelijke nulproductie en leerkwaliteit per tijdvak blijven afzonderlijk van een echte dagfout. Geldige PV-/thermische leerdata en configuratie worden niet algemeen gewist of aangepast.

Geen live Home Assistant-/hardwaretest is in deze werksessie uitgevoerd. HA-API-/DOM-doubles bewijzen softwaregedrag, geen fysieke thermische respons, compressoractie, echte browser-HTTP-levering of nieuwe installatieacceptatie. Eventuele browseruitvoering wordt alleen met haar werkelijk uitgevoerde resultaat toegevoegd.

## Publicatie en installatie

Dit verslag legt de lokale gate vóór het uploaden vast. De CI- en publicatieresultaten ontstaan vervolgens op de gepubliceerde commit en zijn te controleren bij de onveranderlijke [beta.55-release](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.55) en de [Validate-workflow](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml). Vereist zijn geslaagde repositorychecks, HACS, Hassfest en publicatie; een annotated tag op de geteste commit; beide ZIP-pakketten en beide beta.55-documenten. De afsluitende publicatiecontrole vergelijkt alle vier gedownloade assets met hun opgegeven SHA-256 en beide ZIP-inhouden met de exacte tagbron. De lokale suite is op zichzelf geen bewijs van die latere CI-run. Bestaande beta.54-assets blijven onveranderd.

Bestaande instellingen, geldige leerdata, dashboardoverrides, boilerbeleid, beschermde programma's en volledig read-only Wallbox blijven behouden. Publicatie is geen bewijs van geïnstalleerde of geladen nieuwe appcode en geen fysieke acceptatietest. Installatie en rollback staan in `BETA55_INSTELLEN.md`; rollbackbasis is de gecontroleerde gepubliceerde beta.54.
