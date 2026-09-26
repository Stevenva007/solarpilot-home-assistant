# SolarPilot · Configuratiestructuur

**Geldig voor 1.0.0-beta.21.** Dit document beschrijft waar instellingen staan. Voor de inhoudelijke EMS-regels geldt uitsluitend `ACTUELE_WERKING.md`.

## Configuratiecentrum

Open **Instellingen → Apparaten & diensten → SolarPilot → Configureren**.

### Overzicht & controle

Toont modus, gekoppelde bronnen, actieve onderdelen, waarschuwingen en concurrerende regelingen. Gebruik dit als eerste controlepunt als iets onverwacht werkt.

### Energie & net

Hier staan de P1-/PV-bronnen, tekenrichting, injectiereserve, maximale softwarematige netafname, kwartierpiek, L1/L2/L3 en energieprijzen.

### Verbruikers & prioriteiten

Flexibele lasten worden via vier stappen beheerd: **Basis → Koppeling → Gedrag & bescherming → Planning & energie**. Nieuwe apparaten blijven standaard **Uitgesloten** totdat je ze bewust op Auto zet.

### Comfort & warmtepomp

**Sanitair warm water** bevat de Panasonic-bronnen en de actuele 43/49/50/60 °C-regels, nachtvenster, koelblokkering en sterilisatiebescherming.

**Ruimteklimaat · basis** koppelt de Panasonic-zones, weather-entiteit, actuele buitentemperatuur en de belangrijkste comfortbanden. SolarPilot stuurt nooit HEAT of COOL; Panasonic AUTO beslist dat zelf.

**Ruimteklimaat · geavanceerd** blijft beschikbaar als fallback-configuratie, maar de normale plaats om het klimaat te begrijpen en fijn af te stellen is voortaan het **dashboard → Comfort → Ruimteklimaat**.

Daar vind je in één samenhangend blok:

- **Status & advies** — binnentemperatuur, Panasonic-doel, AUTO/coast-advies en voorspelde comfortband;
- **Meldingen** — blokkeringen, lage modelzekerheid, ontbrekende PV/forecast en adviesmodus;
- **Bevindingen & leren** — warmteverlies, reactie op verwarmen/koelen, vloerreactievertraging, aangeleerde zonnewinst, lokale weerscorrectie en coast-resultaten;
- **Instellingen** — **iedere** `SMART_CLIMATE`-instelling, gegroepeerd per onderwerp;
- **Uitleg** — in gewone taal wat de klimaatregeling wel en niet doet.

Bij iedere dashboardinstelling staat:

1. een korte betekenis;
2. een aanbevolen startwaarde of keuze;
3. voor getallen: wat lager/hoger praktisch betekent;
4. voor schakelaars: wat Aan/Uit praktisch betekent;
5. bij bronwijziging: welk model daardoor opnieuw moet leren;
6. vóór opslaan: een bevestiging met huidige waarde, nieuwe waarde, advies en gevolg.

Er zijn dus geen verborgen klimaat-tuningwaarden zonder gebruikersuitleg. De fysieke Panasonic-doeltemperatuur blijft je thermostaatinstelling en is bewust **geen** SolarPilot-tuningwaarde.

### Klimaatleerlagen

**Zonnewinst in de woning**

Werkelijk PV-vermogen dient als lokale instralingsproxy. SolarPilot leert per zone hoeveel extra natuurlijke opwarming daarmee samenhangt. Dit is begrensd en wordt alleen bij voldoende leerkwaliteit gebruikt.

**Lokale weerscorrectie**

SolarPilot bewaart de fout tussen de eerdere uurforecast en de later werkelijk gemeten buitentemperatuur. Correctie wordt afzonderlijk geleerd rond 6, 12, 24 en 48 uur vooruit, met minimumsamples, minimum verschillende dagen, confidence en een maximumcorrectie.

**Coast-evaluatie**

Een door SolarPilot gestarte OFF/coastperiode wordt achteraf als **correct**, **te lang** of **te voorzichtig** beoordeeld. Alleen het minimum nuttige coastvenster mag daarna stap voor stap binnen jouw ingestelde onder-/bovengrens verschuiven. Comfortbanden, Panasonic-doel en HEAT/COOL worden nooit door deze feedback aangepast.

**Niet geïmplementeerd:** raam- en deurcontacten hebben geen invloed op het klimaatmodel of AUTO/coast-beslissingen.

### Opslag & laden

Wallbox blijft alleen-lezen. Toekomstige thuisbatterijen kunnen read-only of expliciet bestuurbaar worden gekoppeld; fysieke batterijbediening vereist meerdere toestemmingen. Batterij-what-if blijft adviserend zonder hardware.

### Voorspellen & optimaliseren

Forecast.Solar, lokaal PV-/schaduwmodel en planner. Actuele meters blijven altijd belangrijker dan forecast of historische patronen.

### Geavanceerd & systeem

Technische engine-timing, meetkwaliteit, faseherkenning, Wallbox-herkenning, privéprofiel/historiek en systeeminformatie. Dit zijn geen dagelijkse instellingen. **Privéprofiel & historiek** leest uitsluitend het lokale `userfiles/private_bundle.json`, toont welke bron-groepen ontbreken en kan de bundel opnieuw conservatief toepassen zonder fysieke regeltoestemmingen te activeren.

## Dashboardstructuur

De gewone kaart heeft zeven hoofdtabs:

- **Overzicht** — beslisinformatie en belangrijkste KPI's;
- **Verbruikers** — flexibele lasten en prioriteiten;
- **Comfort** — boiler én het volledige klimaat-Control Center;
- **Planning** — gezamenlijke 24–48-uursplanning, dagdoelen, beschermde cyclusprofielen, planfouten, what-if-replay, tijdlijn en plannerinstellingen;
- **Energie** — kwartierpiek, fasen, forecast en lokaal PV-model;
- **Opslag** — batterijvloot en batterijscenario's;
- **Uitleg** — de release-gebonden actuele werking.

Moduskeuze en kritieke waarschuwingen blijven bovenaan zichtbaar.

## Ontwerpregel

Nieuwe functies horen in een bestaande logische categorie tenzij dat echt niet kan. Bij iedere gedragswijziging worden code, Home Assistant-uitleg en `ACTUELE_WERKING.md` in dezelfde release bijgewerkt.


## Planning-tab

De Planning-tab hoort bij **Voorspellen & optimaliseren → Unified Planner**. Hier staan horizon, planblokken, dagdoelen, beschermde cycli, voorspelde import/export/kost, 7/30-dagen plannerkwaliteit, recente what-if-replay en alle actieve plannerinstellingen. Wijzigingen vanuit het dashboard tonen eerst een korte uitleg, advies en de gevolgen. Beschermde cycli worden per programma geconfigureerd bij **Verbruikers & prioriteiten → Planning & energie**.
