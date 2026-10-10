# SolarPilot 1.0.0-beta.63 — instellen en controleren

Panasonic regelt voortaan zelfstandig comfort en beveiligingen. SolarPilot mag voor de warmtepomp alleen één bestaande Shelly-uitgang voor extra SG-zonneboost bedienen. Het schrijft geen temperatuur, AUTO/UIT, heaterkeuze of fabrikantprogramma. Oude actieve tank-/klimaatsturing is verwijderd; nuttige metingen, historie en overige SolarPilot-apparaten blijven behouden.

De enige volledige actuele werking staat in `ACTUELE_WERKING.md` en binnen Home Assistant op **SolarPilot → Uitleg**. Werkelijke software- en publicatiestatus: `TESTRESULTATEN_BETA63.md`.

## Herstellen van de beta.62-opstartfout

Krijg je na beta.62 **Error setting up entry SolarPilot**? Update via HACS naar **1.0.0-beta.63**, herstart Home Assistant volledig en open de app/webpagina opnieuw. Verwijder de bestaande integratie niet en wis geen configuratie, modellen, archief of Home Assistant-opslag. Deze update maakt geen nieuwe SG-toestemming en vereist geen nieuwe APP-aanvraag voor de afwasmachine.

De bekende fout is met de echte Home Assistant Core 2026.10.0 lokaal geïsoleerd gereproduceerd op de ongewijzigde beta.62-bron: HA biedt opgeslagen opties als een onveranderbare mapping aan, terwijl beta.62 die direct probeerde te deepcopyen. Dat gaf in die proef `TypeError: cannot pickle 'mappingproxy' object` en `SETUP_ERROR` vóór de SolarPilot-migratiearchivering, opslag en runtime-start. Opties en Store bleven exact ongewijzigd; er waren 0 fysieke servicecalls. Beta.63 maakt eerst een lokale dictionarykopie en laat ook de migratie de HA-mapping accepteren, zodat bestaande geneste instellingen behouden blijven. De nieuwe versie slaagde in dezelfde echte Core bij productie-entry setup, zes platforms, reload en unload, met exact archiefbehoud en 0 fysieke servicecalls. Dit gebruikt uitsluitend fictieve lokale configuratie, met HTTP-netwerkstart uitgeschakeld. De eigen installatie is hiermee niet geïnspecteerd; een afzonderlijke andere fout kan een andere oorzaak hebben.

Controleer na herstart of SolarPilot geladen is en backend- én kaartversie beta.63 aangeven. Blijft laden mislukken, open de volledige fout in **Home Assistant → Instellingen → Systeem → Logboeken** en bewaar de traceback privé. Publiceer geen complete thuisconfiguratie of analyse-export.

## 1. Eerst een herstelbare privéback-up

De bouwbasis van deze herstelupdate is [beta.62](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.62), commit `8e49c21ee03d3bd70a7d3460c2104628a43772f2`, tree `7314c163b156f4df18dfe5ab31b88aae6a188865`. Terugzetten naar beta.62 lost de beschreven opstartfout niet op. Terugkeer naar de oude beta.61-regeling vereist de passende volledige privéback-up van vóór de SG-migratie, zoals hieronder beschreven.

1. Maak **vóór de upgrade** een volledige Home Assistant-back-up met configuratie, SolarPilot-opslag, modellen, userfiles en benodigde herstelgegevens. Bewaar haar privé.
2. Bewaar beta.61 en noteer bij welke pre-upgrade-opslag/back-up die code hoort.
3. Controleer de gewenste normale native Panasonic-instellingen: tankdoel, zones, programma, normaal comfort, elektrische ondersteuning en sterilisatie. Een oudere directe SolarPilot-regelaar kan iets hebben achtergelaten; beta.63 zet dat niet via een herstelwrite terug.
4. Onderbreek geen draaiende beschermde afwascyclus. Een upgrade maakt geen APP-aanvraag of extra START.
5. Controleer de bewaarde keuze **Na herstart automatisch hervatten**. Aan kan een gewone Pauze na herstart weer laten beoordelen; zij activeert geen SG en passeert geen echte fouten.

De migratie bewaart een versiegebonden read-only privéarchief van oude configuratie/opslag en relevante fout-/opdrachtgegevens. Zij doet geen fysieke opdracht, herhaalt geen oud pending doel en neemt geen oude AUTO/OFF-eigendom over. Aantoonbaar uitsluitend vervallen opdrachtfouten worden als vervallen functie beoordeeld; onbekende/mengfouten en echte gebruikers-/toestel-/batterijkeuzes blijven beschermd. Het archief is geen vervanging voor een complete HA-back-up.

## 2. Installatie via HACS of lokaal

Bij eerste gebruik voeg je `https://github.com/Stevenva007/solarpilot-home-assistant` toe aan **HACS → Custom repositories** als **Integration**. Installeer/update exact `1.0.0-beta.63` zodra die release is gepubliceerd, herstart Home Assistant volledig en heropen browser/app. Controleer backendversie en geladen kaartversie afzonderlijk.

Een lokaal pakket vervangt uitsluitend `custom_components/solar_pilot`. Bewaar lokale `userfiles` en Home Assistant-opslag. Geen aparte Lovelace-resource, dashboard-YAML of www-kopie nodig. Voeg bij nieuwe installatie SolarPilot toe via **Instellingen → Apparaten & diensten** en controleer P1/PV eerst in **Alleen bekijken**.

Geldige andere toestellen, prioriteiten, bestaande APP-tickets, geschiedenis, modellen en bewaartermijnen blijven behouden. Automatische SG staat na deze migratie uit; er wordt geen Shelly-entiteit gegokt of een tweede fysieke uitgang aangemaakt.

## 3. Compacte warmtepompconfiguratie

Open de bestaande warmtepompinstellingen. Het onderdeel heet **Warmtepomp — Panasonic-regeling**.

| Onderdeel | Wat je vastlegt |
| --- | --- |
| Automatische zonneboost | Eén bestaande fysieke Shelly-switch, bewuste activering en echte ingebruikname-/timerbevestiging. |
| Alleen-lezen bronnen | Tanktemperatuur, normaal native tankdoel, activiteit, zones en een geschikte W/kW-meter. |
| Meterdekking | Hele warmtepomp, alleen voeding 1, alleen voeding 2 of onbevestigd. Een deelmeting is geen totaal. |
| Geavanceerd | Start/stop/rust/sessietijden, vermogensraming en lokale toestemming; standaardwaarden zijn voorzichtige policy, geen bewezen apparaatvermogen. |

Selecteer geen interne Shelly-temperatuur als tankbron, energieteller in kWh als actuele W-meter of P1/PV als exclusieve warmtepompmeter. Een inbegrepen heater wordt niet apart opgeteld. Normaal native warmtepompverbruik is niet volledig terugwinbaar door het SG-contact vrij te geven.

Nieuwe standaardwaarden: startdrempel **3000 W**, afzonderlijke raming **3200 W**, startvertraging **120 s**, stopvertraging **60 s**, rust **900 s**, sessie maximaal **3600 s**. De lokale toestemming duurt standaard **300 s** en wordt iedere **60 s** vernieuwd, binnen de resterende maximale sessieduur. Tegen het sessie-einde wordt geen nieuwe volle lease geplaatst; de ingestelde bevestigingsmarge kan de aanvraag iets eerder laten eindigen. Kleine gewone import heeft een afzonderlijke buffer, standaard **300 W**; harde limieten en onbetrouwbare noodzakelijke bronnen gaan vóór de wachttijden. Een actieve boost hoeft de oorspronkelijke restinjectiedrempel niet te blijven halen: de warmtepomp gebruikt die zon. Netafname boven de buffer gedurende de stopvertraging geeft de eigen SG-aanvraag vrij. Tijdens die tekortcontrole wordt de lokale toestemming niet vernieuwd. Native verbruik kan vervolgens doorgaan.

Een oude startdrempel of tankopwarmraming krijgt niet stilzwijgend een nieuwe betekenis. De migratie bewaart oude effectieve waarden als privébeoordelingskandidaten. Controleer en bevestig de SG-startdrempel en raming afzonderlijk. De waargenomen heaterbelasting is geen totaalvermogen, heatermaximum of startdrempel.

## 4. Eén eigenaar en native basis controleren

De SG-uitgang mag niet ook als gewone flexlast, batterijactuator of tweede SolarPilot-profiel worden gebruikt. Backendvalidatie voorkomt interne dubbeltelling/eigenaarschap. Controleer daarnaast inspecteerbare externe automatiseringen/scripts die het tankdoel, zones of dezelfde uitgang nog schrijven. Schakel ze niet blind op naam uit: bepaal de echte koppeling en vraag expliciete toestemming voor het uitschakelen van aantoonbaar oude writers.

Deze bronrelease heeft geen live huisautomatiseringen geïnspecteerd. Zij levert de controle, geen claim dat dubbele externe sturing al verdwenen is. Houd automatische SG uit zolang het eigenaarschap of de native basis onduidelijk is.

## 5. Lokale ingebruiknameproef — alleen na expliciete toestemming

Deze proef vereist geen elektrische meting op geopende apparatuur en wijzigt geen bedrading, DIP-schakelaars of heater-toestemming. Laat een installateur de fysieke aansluiting controleren als die niet eerder betrouwbaar is bevestigd. Noteer lokaal wat werkelijk is waargenomen; publiceer geen IP’s of privébindings.

1. Laat automatische SG voorlopig uit. Controleer dat de warmtepomp zonder SolarPilot normale comfort- en fabrikantprogramma’s kan uitvoeren en dat de relevante native tank-/zonestanden gewenst zijn.
2. Controleer op de bestaande Shelly de juiste fysieke uitgang, geschikte firmware/lokale toegang en uitgangsconfiguratie. Opstartstand UIT is alleen een power-onvoorkeur; zij bewijst geen terugval bij wifi- of HA-uitval.
3. Test het **tijdelijk aangevraagde** SG-contact via de ondersteunde lokale Shelly-timerfunctie, met expliciete toestemming en begrensde duur. Controleer werkelijk gemelde `output`, `timer_started_at` en `timer_duration`; een RPC-antwoord `was_on` is slechts de vorige toestand.
4. Controleer de juiste SG-trap op de Panasonic-bediening en het effect op tank én ruimtes. Dezelfde SG-trap kan meer dan tapwater beïnvloeden; bevestig dat geen ongewenste extra ruimteverwarming of vloerkoeling wordt gevraagd. Een normaal blijvend app-tankdoel is geen testmislukking en geen bewijs van het effectieve SG-doel.
5. Controleer dat een tijdige vernieuwing dezelfde uitgang AAN houdt en de lokale afloopdeadline opschuift, zonder fysieke UIT/AAN-cyclus. Een geaccepteerde vernieuwing alleen bewijst dat niet.
6. Laat vervolgens de vernieuwing bewust uitblijven en controleer dat het contact door de lokale timer opent, ook zonder Home Assistant-vernieuwing. Controleer opnieuw de echte uitgang. De timer beëindigt alleen de SG-aanvraag; een lopende Panasonic-cyclus kan blijven doorgaan.
7. Geef het contact vrij, bevestig de normale native situatie en leg pas dan ingebruikname en terugval als geslaagd vast. Ontbreekt een ondersteund/testbaar lokaal pad of een echte waarneming, laat automatische SG uit en corrigeer de gemelde configuratievoorwaarde.
8. Activeer daarna **Automatische zonneboost** en gebruik de globale Auto-modus alleen wanneer de gewone SolarPilot-bronnen/veiligheidscontroles betrouwbaar zijn. Observeer een natuurlijke voldoende stabiele zonnestart; forceer geen tanktemperatuur of klimaatmodus als proef.

De softwareadapter gebruikt de ondersteunde native Shelly-RPC met `Switch.Set` en een lokaal `toggle_after` in seconden, gevolgd door echte status-/timeruitlezing. De fysieke proef wordt hier niet uitgevoerd. Gebruik voor een lokale test de werkelijk ondersteunde geauthenticeerde toegang van de gekoppelde Shelly; geen publiek voorbeeldadres, token of verzonnen HA-service. Zonder deze proef geeft een checkbox geen onafhankelijke garantie.

## 6. Wat de kaart bewijst

| Status | Betekenis |
| --- | --- |
| SolarPilot vraagt boost | De huidige policy heeft een extra aanvraag gekozen. |
| SG-contact bevestigd actief | De Shelly meldt werkelijk AAN en haar lokale toestemming. |
| Panasonic-reactie bevestigd | Alleen als een afzonderlijke passende bron die reactie werkelijk meldt. |
| Panasonic-reactie onbekend | Het contact kan bevestigd zijn zonder afzonderlijk bewijs van warmwateropwarming. |
| Vrijgegeven, native verbruik blijft | Normaal Panasonic-bedrijf kan doorgaan; deze stroom wordt niet opnieuw als vrije ruimte uitgegeven. |

Uitklapbare Details houdt de volledige actuele reden en bekende watts/dekking bij elkaar. Een voorstel of serviceacceptatie is geen fysieke bevestiging. Actuele PV/netkleuren en blauwe activiteit blijven apart; onbekende bron blijft onbekend.

Na de maximale sessieduur blijft een afzonderlijke wachtstand bewaard. Een verse betrouwbare tankmeting bij het einde vormt de referentie. Na rust kan SolarPilot opnieuw zon beoordelen als dezelfde tank minstens **2 °C** is afgekoeld, bevestigd door minimaal twee latere echte rapporten gedurende **vijf minuten**. Dit toont nieuwe opslagruimte, geen comfortvraag, bewezen eerdere SG-opwarming of effectief SG-tankdoel. Alle huidige zon-, bron-, fase- en voorrangsvoorwaarden en de volledige startvertraging gelden opnieuw. Na herstart moet de vijfminutenbevestiging met nieuwe echte rapporten opnieuw plaatsvinden. Zonder eindmeting, na bronwisseling of bij onbetrouwbare data blijft de wachtstand staan; **Automatisering hervatten** blijft mogelijk na bewuste controle. Alleen herstart of rusttijd begint geen nieuwe sessie. Een gewone vrijgave wegens netafname kan na rust en verse geldige zon wel opnieuw worden beoordeeld.

Een echte handmatige SG-wijziging wordt behouden. **Automatisering hervatten** geeft een bewuste nieuwe beoordeling, geen ongecontroleerde AAN. Na herstart wordt een oude eigen aanvraag niet blind hervat; bronnen en contact worden eerst opnieuw beoordeeld. Een oude late AAN of verlopen toestemming verleent geen nieuwe toestemming.

## 7. Andere toestellen en meldingen

De ontvochtiger houdt zijn bestaande minimumlooptijd/rust en deelname. Extra SG kan alleen veilige lagere eigen onderbreekbare lasten laten wijken; na bevestigde UIT zijn nieuwe net-/PV-metingen nodig. Wallbox blijft read-only en SG krijgt geen autolaadvermogenskrediet. De afwas behoudt haar APP-edge, kalenderdag/deadline, netoptie en één native START per belading; AirDry is geen einde en een draaiend programma wordt nooit gestopt.

Gerichte resterende problemen staan in **Home Assistant → Meldingen → SolarPilot: controle nodig**. Een fout in de SG-uitgang/terugval is lokaal voor SG en hoeft gezonde andere lasten niet te pauzeren. Gewone zonnestabiliteit/rust/bronwacht geeft geen meldingenspam. Oude boilerreview-/klimaatknoppen bestaan niet meer; de nieuwe runtime herstelt geen native doel via een verborgen opdracht.

Bestaande model-/historiegegevens blijven privé bewaard. Grote Recorderdetailkopieën zijn uitgesloten, actuele attributen/eigen opslag/export blijven beschikbaar. De geauthenticeerde JSON.GZ-route kan de werkelijk beschikbare zeven dagen exporteren zonder de oude uitgepakte 16 MB-grens; bestaande retentie/aantallimieten en privacyfilters blijven gelden.

## 8. Rollback met passende opslag

1. Trek de eigen SG-aanvraag in, controleer contactstand/lokale terugval en voorkom nieuwe leasevernieuwing.
2. Stop de nieuwe SG-runtime voordat de oude beta.61-writers terugkomen. Laat nooit beide versies/regelpaden tegelijk beheren.
3. Herstel de gecontroleerde beta.61-code **én de volledige passende privé HA-back-up van vóór de beta.62-migratie**. Alleen de oudere ZIP herstelt niet de gewijzigde opslag/schema’s.
4. Kies de gewenste globale gebruikersmodus en hervatvoorkeur bewust; controleer native Panasonic-basis en mogelijke externe writers vóór eventuele oude directe sturing opnieuw toestemming krijgt.
5. Herstart HA, heropen browser/app en controleer backend-/kaartversie. Behoud beschermde cycli en maak geen nieuwe APP-aanvraag of warmtepompwrite om rollback te bewijzen.

De nieuwe read-only migratiesnapshot helpt beoordeling, maar doet nooit fysieke replay en is geen complete restore van alle HA-integraties. Zie `TESTRESULTATEN_BETA63.md` voor werkelijk uitgevoerde software-/publicatiecontrole. Shelly-/Panasonic-proef, geladen HA en woningacceptatie blijven afzonderlijke lokale bewijsstappen.

## Primaire technische bronnen

- [Shelly 1 Gen4-documentatie](https://kb.shelly.cloud/knowledge-base/shelly-1-gen4) en [Gen4 RPC-apparaat](https://shelly-api-docs.shelly.cloud/gen2/Devices/Gen4/Shelly1G4/).
- [Shelly Switch RPC: Set, status en timers](https://shelly-api-docs.shelly.cloud/gen2/ComponentsAndServices/Switch/).
- [Panasonic K-generatie, fabrikantbrochure](https://www.panasonicproclub.com/uploads/LT/catalogues/EU_20P_PRINT_AQ_K_GEN_23_LR.pdf): SG kan tapwater en ruimtebedrijf beïnvloeden; lokale configuratie is bepalend.

Bronbeschrijvingen en softwaretests vervangen geen verificatie van de aanwezige firmware, contactmapping en native instellingen.
