# SolarPilot beta.33 — Wallbox-sessie, PV-kalibratie en duidelijke diagnose

**Volledig cumulatief vanaf het gecontroleerde beta.32-pakket.** Tussenliggende
versies hoeven niet apart geïnstalleerd te worden. Deze download wijzigt niets
op GitHub of je live Home Assistant. De volledige actuele uitleg is
`docs/ACTUELE_WERKING.md` en staat identiek in Home Assistant onder Uitleg.

## 1. Wat behouden blijft

De AEG-APP-vrijgave geeft één belading toestemming, met 13:00 als startdeadline
en na 13:00 standaard de volgende kalenderdag. De expliciete deadline-nettoestemming,
het eventgestuurde korte `End Of Cycle`, de blijvende eindtijd en AirDry blijven.
Geen PAUSE/RESET of Shelly-relaisbediening voor een lopende beurt. Prioriteit blijft
gewoon warmtepompcomfort → afwas → bestaande lagere functies.

Het normale boilerdoel blijft bij het afgesproken profiel 50 °C en 46 °C is een
bewakingsgrens. Geen herstelboost naar 52 °C, geen Force DHW en geen wijziging van
de fysieke −5 °C differentie. De nominale fabrikant-herstart rond 45 °C betekent
nog altijd dat 46 °C niet fysiek gegarandeerd kan worden. Een berekende zonne-
avondvoorraad boven 50 °C (begrensd op het gekozen plafond) is een aparte functie.
Fabrikantsterilisatie, Powerful en Force DHW blijven beschermd.

Bestaande zon-, woning-, tank-, fase-, toestel-, kosten- en batterijgegevens,
startaanvragen, historie, Leren & vragen en analyse-export blijven behouden.
Geen nieuwe Auto-deelname of fysieke toestemming wordt automatisch aangezet.

## 2. Bijwerken

Maak een volledige Home Assistant-back-up. Werk bij voorkeur bij wanneer een
beschermd programma klaar is. Zet SolarPilot op Pauze en laat eigen onderbreekbare
lasten hun minimumtijden respecteren; Pauze is geen noodstop.

Kopieer de **inhoud** van het nieuwe project over je bestaande Git-repository,
niet een extra versiemap als submap. Bewaar `.git` en privébestanden. Publiceer
nooit je HA-configuratie, `.storage`, privébundel of analyse-exporten.

Controleer lokaal in PowerShell, één opdracht per keer:

```powershell
$env:PYTHONUTF8="1"
$env:PYTHONDONTWRITEBYTECODE="1"
py -m pytest -q -p no:cacheprovider
py tools\check_current_explanation.py
py tools\validate_repository.py
py tools\check_public_repository.py
git -c core.autocrlf=false diff --check
```

Push eerst de gewijzigde commit naar `main`. Maak pas na een geslaagde GitHub-
validatie van diezelfde commit de nieuwe tag `v1.0.0-beta.33`; verplaats geen
bestaande tag. Werk vervolgens via HACS bij en herstart Home Assistant. Er is
geen nieuwe losse dashboardresource of configuratieherimport nodig.

## 3. Wallbox — onderscheid de echte sessie van de ingestelde optie

Open **Configureren met uitleg ? → Opslag & laden → Wallbox**.

| Optie | Uitgangspunt |
|---|---|
| Oorspronkelijke zonnelaadmodus | Bestaande select-/sensorbron behouden |
| Effectieve laadsessie | Een door jou gecontroleerde bron koppelen |
| Alleen Full Solar-instelling vertrouwen zonder sessiebron | **UIT** |
| Extra 60 °C uitstellen bij manueel/onzeker laden | **AAN** |
| Bestaande maximale stroom/fasen | Behouden; geen fysieke wijziging |

**Belangrijk:** de Full Solar-instelling kan aan blijven wanneer je in de
Wallbox-app manueel start. Daarom is die instelling alleen standaard geen
bewijs van autonome zonneregeling. Een bestaande dashboardhelper voor de reële
laadmodus is een *kandidaat*, geen automatisch betrouwbare bron. Controleer dat
hij ook een handmatige start in de Wallbox-app zelf correct weergeeft. Een helper
die uitsluitend netafname als "manueel" interpreteert is hiervoor niet geschikt.

Onder **Geavanceerd → Wallbox statusherkenning/timing** zijn de volledige waarden
instelbaar (puntkomma-gescheiden, niet zoeken op een deel van de tekst):

| Soort sessie | Voorgestelde waarden |
|---|---|
| Autonoom zonne-auto | `Zonne-auto · laden;Zonne-auto · wacht op overschot` |
| Manueel | `Manueel laden;Manueel laden · klaar;Manueel / solar uit` |
| Gestopt | `Laden gestopt` |

Kies de waarden die de werkelijk gekoppelde bron terugmeldt. Onbekende of verouderde
bron: **geen EV-vermogensovername**, maar wel gewone regeling op echte injectie.
Daarom kan een verbruiker na deze update wachten terwijl dat vroeger niet gebeurde:
het dashboard vermeldt dan welke sessiebevestiging ontbreekt. Geef niet blind
vertrouwen aan Full Solar om die melding weg te drukken.

Tijdens manueel laden blijft gewoon sanitair water en vloercomfort volgens de
bestaande regels werken. Extra 60 °C kan na de ingestelde terugvalvertraging naar
het gewone doel gaan. Dit is geen directe compressorstop en koelt geen water af.
Sterilisatie/handmatige Panasonic-programma's worden niet overschreven. Een
bewezen losgekoppelde of voltooide auto blokkeert deze extra buffer niet.

Een lopende afwas blijft afwerken. De expliciet toegestane 13:00-start met netstroom
blijft mogelijk binnen de machine-, net-, fase- en piekvoorwaarden. SolarPilot
stuurt de Wallbox zelf niet aan, ook niet tijdens manueel laden.

## 4. Gewone verbruikers — instelbare standaardovername

Open het verbruikersprofiel en **Planning & energie**.

| Zonnevermogen dat de Wallbox al gebruikt | Betekenis |
|---|---|
| **Voorrang volgen** (standaard) | Geschikte verbruiker vóór Wallbox mag bevestigd Full Solar-vermogen gebruiken. |
| **Alleen echt overschot** | Geen EV-vermogen gebruiken; wachten op echte resterende injectie. |
| **Oude expliciete keuze** | Het eerdere overnamevinkje en korte minimumlooptijdvoorwaarde blijven gelden. |

Gewone aan/uit- en numerieke lasten hebben een eigen exclusieve, actuele
W/kW-meting nodig. Bekende schattingen worden geweigerd. Een beschermde generieke
scriptcyclus krijgt geen nieuwe overnamerechten. De AEG gebruikt zijn bestaande
aparte beschermde route en eigen voorkeursoptie, ook zonder Shelly.

De complete nieuwe last moet elektrisch passen **alsof de Wallbox nog even niet
terugregelt**. De overnamestap, net-/fase-/kwartierlimieten, terugmelding en
minimumlooptijden blijven gelden. Een mislukte overdracht kan bij een lange
compressor-minimumlooptijd tijdelijk netstroom vragen. De software knipt die
bescherming niet weg. Geen twee nieuwe fysieke opdrachten tegelijk.

Een verbruiker onder de Wallbox krijgt geen EV-vermogen omdat deze standaard
bestaat. Je bestaande ontvochtiger kan dus onder de Wallbox blijven; een expliciet
hoger geplaatste verbruiker krijgt de nieuwe passende overnamekeuze.

## 5. Forecast.Solar en lokale PV-kalibratie

Open **Configureren met uitleg ? → Voorspellen & optimaliseren →
PV-voorspelling & lokale kalibratie**.

| Optie | Opgegeven installatie / voorstel |
|---|---:|
| Forecast.Solar gebruiken | AAN, automatisch als één bron gevonden |
| Automatisch bron vinden | AAN |
| Lokale kalibratie / schaduwprofiel | AAN / AAN |
| Stabiliteit | **Normaal** |
| Panelen | **13.800 Wp** |
| AC-omvormerlimiet | **10.000 W** |
| Helling / paneelazimut | **25° / 180°** |
| Minimum vergelijkbare dagen | **5** |
| Diagnosehistoriek | **30 dagen** |
| Forecast te oud na | **7200 seconden** |
| Ruw en gecorrigeerd tonen | AAN |

Een eerder expliciet uitgeschakelde forecast of lokale-PV-module wordt niet bij
migratie ingeschakeld. Kies dit hier bewust. De nieuwe laag UIT laat afzonderlijk
geconfigureerde oude fallbackbronnen bestaan; die staan als geavanceerde terugval
in hetzelfde configuratiecentrum. Er worden geen dubbele factoren toegepast op
uren die door de nieuwe curve gedekt zijn.

**Forecast.Solar zelf behoudt jouw 13,8 kWp, 10 kW, 25°, zuid en 0,00/0,00 damping.**
Er is geen API-key nodig voor deze lokale koppeling. SolarPilot wijzigt die
bronnen niet. Bij meerdere Forecast.Solar-configuraties: kies één ID uit
PV-diagnose → Bronnen, of koppel selectors. Er worden geen huishoudspecifieke
entity-ID's hardcoded gekozen en geen verschillende installaties opgeteld.

Waar ondersteund leest de adapter de reeds geladen Forecast.Solar-vermogenscurve.
Dat is bewust een afgeschermde compatibiliteitsadapter: als HA die interne vorm
verandert, vallen we terug op de echte gekoppelde sensoren, zonder de realtime
regeling te laten crashen. Geen aparte HTTP-polling, geen vaker opvragen van de
cloud en geen gebruik van een actuele productiemeter als forecastbron.

## 6. Wat je na installatie ziet

**Planning** begint met een compact blok Zon & voorspelling. Onderaan staat
**Onderzoek & instellingen** met PV-diagnose, Leren & vragen, Analyse-export en
de bestaande configuratie. Verbruikers tonen hun Wallbox-overnamevoorwaarden.
De zeven bestaande hoofdtabbladen blijven herkenbaar.

**PV-diagnose** toont ruw → gecorrigeerd nu en +1/+2/+3 uur, resterende kWh,
vergelijkbare dagen, factor, confidence, omvormergrens, grafiek en dagtabel. Per
kwartier: ruwe forecast, correctie, echte productie, fout W/% en leerreden.
Historiek wordt alleen op aanvraag opgehaald; vijfsecondenupdates sluiten niets.
Een reset vraagt expliciet bevestiging en wist alleen de live PV-profielen plus
PV-diagnose, geen woning-/tank-/afwasleerdata of apparaatstanden.

De ruwe curve is lineair tussen bronpunten geïnterpoleerd; de native nu-sensor
kan trapsgewijs afwijken. Die native waarde staat ter controle apart. Zonder
voldoende curvegegevens zijn +2/+3 of lokale energiecorrecties onbekend. Een
beschikbaar dagtotaal blijft dan als **ruw, niet lokaal gecorrigeerd** gemarkeerd.
Er wordt geen huidige schaduwfactor op heel morgen toegepast.

Nieuwe sensoren (de exacte entity-ID kiest HA op basis van de namen/unique-ID):

- **8 vermogenssensoren (W):** Forecast.Solar ruw en lokaal gecorrigeerd voor nu,
  +1, +2 en +3 uur.
- **3 energiesensoren (kWh):** resterend vandaag ruw/gecorrigeerd; morgen gecorrigeerd.
- **3 modelwaarden:** correctiefactor, kalibratiezekerheid (%) en gemiddelde
  gecorrigeerde afwijking bij zon (W).

Deze voorspellingen zijn geen oplopende gemeten energietellers. Gebruik voor het
gewone HA-energiedashboard je bestaande echte productie-/netenergiesensoren.

## 7. Leren en beperkingen

De eerste tien minuten na starten wordt niet geleerd. Daarna zijn volledige
kwartieren met minstens 12 verse waarnemingen nodig. Eén minuut telt niet als
nieuw kwartier en 100 metingen op één dag zijn geen 100 leerdagen.

Vanaf 9800 W bij deze 10kW-omvormer wordt mogelijke clipping niet als schaduw
geleerd. Snelle wolken, hiaten, bevroren rapporten, extreme verhoudingen en waarden
boven 11kW worden apart geweigerd. Een rustig, volledig kwartier telt pas mee in
een herhaald profiel per zonnestand/seizoen. Minstens vijf vergelijkbare dagen,
voldoende consistentie en geleidelijke factorwijziging zijn vereist.

De eerste 30 dagen kwartierdiagnose beginnen na deze installatie. Bestaande
historische PV-startprofielen blijven behouden als terugval; ongedateerde of
niet met toenmalige forecast gepaarde HomeWizard-data worden niet als betrouwbare
nieuwe kalibratie uitgevonden. Het model bewaart maximaal 45 dagen per vak,
gebruikt geen bewijs ouder dan 120 dagen en overleeft normale herstarts/updates.

De gecorrigeerde curve voedt de bestaande vooruitplanner en thermische/boiler-
vooruitblik. Actuele metingen, comfort, piek/fasegrenzen en deadlines blijven
leidend. **Fasegewijze optimalisatie van jouw afwasprogramma wacht nog op de
Shelly en de daarvoor afgesproken latere update.** Die functie wordt hier niet
stilzwijgend als af beschouwd.

Een gedeelde meter, stabiele bewolking of onjuiste broninstelling is niet volledig
uit een ratio te herkennen. Een geleerde lokale afwijking is niet automatisch
bewezen schaduw. Controleer de eerste bruikbare dagen in PV-diagnose en exporteer
bij vragen de analyse: de nieuwe PV- en Wallbox-gegevens zitten daarin.

## 8. Verificatie na installatie

Controleer de versie **1.0.0-beta.33**, de oorspronkelijke bronkoppelingen en
fysieke vrijgaven. Kijk of PV-diagnose de juiste bron/omvormergrens toont en of
ruwe/verwerkte waarden plausibel zijn. Geen gedekte bron: echte regeling blijft
werken; configureer niet zomaar een willekeurige vermogenssensor als forecast.

Controleer de effectieve Wallboxbron in zowel zonne-auto als een gewone manuele
sessie. Manueel moet als manueel verschijnen terwijl het normale warmtepompdoel
onveranderd blijft. Bewaak vervolgens één gewone toegestane verbruiksstart en de
netbalans, zonder een beschermd programma te onderbreken.

Alle meegeleverde tests zijn lokale software-/browserproeven met fictieve bronnen.
Geen fysieke AEG-/Wallbox-/Panasonic-test, geen actuele HA-serverproef en geen
nieuwe GitHub Actions-run zijn door het maken van deze download uitgevoerd.
