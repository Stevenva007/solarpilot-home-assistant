# SolarPilot beta.37 — gebruiksvriendelijke bediening en centrale voorrang

Deze release bouwt cumulatief voort op beta.36. Bestaande koppelingen, prioriteiten, leerdata, APP-aanvragen en expliciete fysieke rechten blijven behouden.

## Wat verandert meteen na de update?

Bij de eerste start van beta.37 wordt éénmalig een veilig startprofiel toegepast:

- analyse-export, planner, basislastleren, lokaal PV-leren, Forecast.Solar-kalibratie en batterij-what-if worden actief;
- fasebewaking en fase-leren worden actief wanneer L1/L2/L3 al gekoppeld zijn;
- Wallbox-monitoring wordt actief wanneer een laadvermogensbron al gekoppeld is;
- klimaatmodel en AUTO/OFF-regeling worden alleen actief wanneer de gekoppelde zones werkelijk AUTO en OFF ondersteunen;
- warmwaterregeling wordt alleen actief wanneer doel- en temperatuursensor én de bestaande veiligheidsbevestiging aanwezig zijn;
- een toestel met een afzonderlijke eigen vermogensmeter mag zijn cyclusprofiel leren;
- Leren & vragen gebruikt gemeten gegevens, begrensde automatische adaptatie en Home Assistant-meldingen.

SolarPilot maakt geen ontbrekende entiteit, veiligheidsbevestiging, toestelvrijgave of batterij-eigenaarschap aan. De activering gebeurt maar één keer; latere handmatige keuzes worden niet opnieuw overschreven.

## Nieuwe dagelijkse indeling

De belangrijkste dashboardonderdelen zijn:

- **Alleen bekijken** — meten, plannen en leren zonder gewone flexibele toestellen te schakelen;
- **Automatisch regelen** — de reeds toegestane regels mogen fysiek sturen;
- **Voorrang** — één lijst voor flexibele zonne-energie;
- **Toestellen** — apparaten toevoegen, koppelen, plannen, historiek bekijken en vervangen;
- **Warmte & comfort** — Panasonic warm water en ruimteklimaat;
- **Auto & batterij** — Wallbox en batterijfuncties;
- **Export** — één compleet analysebestand;
- **Uitleg** — de actuele releasegebonden werking.

## Voorrang instellen

Open **Voorrang → Wie krijgt eerst zonne-energie?**.

Vaste beschermde functies staan bovenaan en zijn niet verplaatsbaar:

1. veiligheid en Panasonic-beveiligingen;
2. benodigde verwarming/koeling van de woning;
3. normaal warm water en noodzakelijke ochtendvoorraad.

Daaronder staat de verschuifbare volgorde. De bestaande beta.36-volgorde wordt bij de update behouden. Voor de bekende installatie hoort de gewenste volgorde, wanneer de AEG-afwasmachine als profiel aanwezig is, te zijn:

1. **AEG-afwasmachine**;
2. **Auto laden (Wallbox)**;
3. **Ontvochtiger kelder**;
4. **Extra warm water tot 60 °C**.

Een nieuw gewoon flexibel toestel komt standaard onderaan. Gebruik slepen of de pijltjes om het hoger/lager te zetten.

Per toestel staat daarnaast:

**Mag dit toestel zonnevermogen gebruiken dat de auto al gebruikt?**

- **Ja · Wallbox mag terugregelen** — alleen actief wanneer het toestel óók boven de Wallbox staat en een actuele autonome zonnelaadsessie betrouwbaar bevestigd is.
- **Nee · alleen nog vrij overschot** — het toestel gebruikt alleen zonnevermogen dat na de Wallbox werkelijk overblijft.

De Wallbox blijft read-only. SolarPilot verstuurt geen laadstroom-, pauze-, start- of laadmodusopdrachten.

## Toestellen beheren

Onder **Toestellen** kun je apparaten toevoegen en later vervangen. Nieuwe toestellen starten Uitgesloten en krijgen geen fysieke starttoestemming door alleen hun categorie of naam.

Een vervangend toestel krijgt een eigen ID en eigen leerprofiel. Oude metingen, APP-aanvragen en fysieke koppelingen worden niet als waarheid naar de opvolger gekopieerd.

## Export voor controle in ChatGPT

Open **Export** en kies **Analysebestand downloaden**.

De standaardexport gebruikt zeven dagen en pseudonimiseert namen. Het bestand bevat onder meer:

- effectieve instellingen en centrale voorrang;
- relevante bronmetingen en meetdekking;
- start-/stopredenen en opdrachten;
- Wallbox-, Panasonic- en toestelstatus;
- planning en forecast;
- leerprofielen en vertrouwen;
- fouten, blokkeringen en herstarts;
- beschikbare apparaat- en cyclusinformatie.

Ontbrekende historie wordt niet verzonnen. SolarPilot uploadt niets automatisch. Deel het bestand zelf in ChatGPT wanneer je een periodieke controle of verdere verbetering wilt.

## Eerste controle na installatie

1. Installeer beta.37 via HACS en herstart Home Assistant.
2. Controleer **Voorrang** en bevestig dat de bestaande volgorde behouden is.
3. Controleer bij relevante toestellen de kolom/keuze over Wallbox-zonnevermogen.
4. Open **Leren & vragen** en bekijk welke modellen actief zijn, leren of nog op een bron wachten.
5. Download na enkele dagen via **Export** een analysebestand om de werking te controleren.
6. Zet geen nieuw fysiek toestel op Auto voordat de koppelingen en veilig gedrag zijn gecontroleerd.

Een software-update verandert geen fabrikantbeveiliging en is geen elektrische of hygiënische keuring.
