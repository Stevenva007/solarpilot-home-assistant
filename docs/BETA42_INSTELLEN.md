# SolarPilot 1.0.0-beta.42 — instellen, controleren en rollback

Beta.42 is een cumulatieve veiligheids- en uitlegrelease. Zij vervangt niets aan de bestaande AEG-startvoorwaarden, Panasonic-fabrikantbeveiliging of Wallbox-read-onlygrens.

## Bewezen uitgangspunt

Vóór deze upgrade is op de echte installatie gecontroleerd dat Home Assistant Core **2026.9.4** SolarPilot **1.0.0-beta.41** werkelijk had geladen. De veilige modules waren gericht geactiveerd en de oude afzonderlijke warmtepompboilerautomatiseringen voor 60/50 °C stonden uit. Dat is de bewezen basis; het is geen bewijs dat beta.42 al geladen of fysiek geaccepteerd is.

## Upgrade

1. Maak een volledige Home Assistant-back-up.
2. Installeer `1.0.0-beta.42` via de bestaande HACS-repository.
3. Herstart Home Assistant volledig.
4. Controleer in de SolarPilot-status dat de geladen backendversie exact `1.0.0-beta.42` is.
5. Vernieuw de browser geforceerd en controleer dat ook de kaart beta.42 toont.
6. Begin de controles in **Alleen bekijken** of **Pauze**. Geef niet meerdere nieuwe fysieke rechten tegelijk vrij.

## Boiler na handmatige bediening hervatten

Wanneer SolarPilot een handmatige Panasonic-wijziging herkent, blijft `manual_hold` een bewuste schrijfblokkering. Beta.42 toont dan een gerichte **Hervat**-actie.

- Gebruik Hervat uitsluitend in **Alleen bekijken** of **Pauze**.
- Hervatten is geblokkeerd tijdens **Automatisch regelen** en zolang een opdracht nog op bevestiging wacht.
- De actie beëindigt alleen de SolarPilot-rust. Zij schrijft niet direct een doeltemperatuur en start geen DHW-cyclus.
- Een latere gewone regelcyclus mag pas handelen nadat bronstatus, toestemming, eigendom, koeling, sterilisatie en alle overige locks opnieuw zijn beoordeeld.

Controleer na Hervat dat de handmatige blokkering verdwijnt, de doeltemperatuur op dat moment niet verandert en er geen fysieke servicecall ontstaat.

## Voorrang eerlijk lezen

De keuze om een toestel zonnevermogen te laten gebruiken dat de auto al gebruikt heeft twee afzonderlijke kanten:

- **Bewaarde keuze:** wat de gebruiker heeft opgeslagen.
- **Effectief nu:** alleen Ja wanneer het toestel boven **Auto laden** staat én de bewaarde keuze Ja is.

Een opgeslagen Ja onder Auto laden blijft bewust bewaard, maar beta.42 toont daar effectief **Nee · Auto laden staat hoger**. Verplaatsen of opslaan stuurt geen toestel en verleent geen nieuw actuatorrecht. Alle gewone startvoorwaarden, meters, minimumtijden en veiligheidslocks blijven daarnaast verplicht.

## Leergegevens veilig wissen

**Apparaat-, lokale PV-, fase- en klimaatleerdata wissen** is in beta.42 begrensd tot de lokale afgeleide leerlagen:

- Wallbox-respons en overdrachtsstatistiek;
- toestelvermogenssamples en overdrachttellers;
- lokale live-PV-bins en -samples;
- faseprofielen en tellers;
- klimaat-zoneprofielen, weersbias en coast-feedback.

De actie behoudt de instelling dat lokaal leren aan of uit staat, historische PV-bootstrap/configuratie en de operationele klimaatstaat: een actieve of wachtende coastepisode, handmatige rust, commandolimiet/teller van vandaag, verwacht modus-/OFF-eigendom, laatste commando, beslissing, guard, sample- en forecasttiming, actuele forecast en foutstatus. Zij wist ook geen afzonderlijke cyclus-, DHW-, planner- of andere modellen. Na reset wordt alleen de nieuwe leerstatus gepubliceerd; er start geen regelcyclus en er wordt geen apparaat bediend.

## Labels en hulptekst

Controleer na een geforceerde browservernieuwing minstens:

- DHW gebruikt **Automatisch regelen** voor de automatische functie;
- de Wallbox toont een duidelijke statusomschrijving in plaats van het technische Engelse label;
- de DHW-importuitleg zegt dat echte netafname boven de ingestelde grens het extra hoge doel onmiddellijk laat terugvallen.

## Wallbox blijft read-only en fail-closed

Een Full Solar-instelling is geen bewijs van de actuele laadsessie. De effectieve sessiebron moet zonne-auto laden/wachten, manueel laden/klaar/solar uit en gestopt betrouwbaar onderscheiden. De afgeleide live bron controleert de onderliggende fysieke status-, vermogen- en ruwe rapportagebronnen gezamenlijk: bruikbaar, niet restored en hoogstens vijf minuten oud. Een minuutheartbeat in het controle-attribuut houdt de actuele broncontrole zichtbaar. Home Assistant-configuratiecontrole en template-reload zijn geslaagd; daarna werd een actuele gestopte sessie met een ongeveer tien seconden oude fysieke rapportage en zonder EV-vermogenskrediet gezien.

Tot die controle rond is:

- leidt SolarPilot geen sessie af uit alleen de Full Solar-select;
- blijft een oude, onbekende of strijdige status fail-closed;
- verstuurt SolarPilot geen start-, stop-, laadstroom-, fase- of modusopdracht naar de Wallbox.

## Veilige activering

Behoud de bestaande lagen:

1. globaal **Alleen bekijken**;
2. daarna alleen indien gecontroleerd globaal **Automatisch regelen**;
3. per toestel afzonderlijk **Uitgesloten** of **Auto**;
4. afzonderlijke bron-, meter-, eigenaarschap- en veiligheidsbevestiging.

Laat de oude 60/50-boilerautomatiseringen uit zolang SolarPilot de gecontroleerde regelaar is; twee gelijktijdige regelaars zijn geen geldige test. Een update, reset, Hervat-actie of opgeslagen Voorrang geeft op zichzelf geen fysiek recht.

## Nog live te accepteren

- Werkelijk geladen beta.42-backend en beta.42-kaart na herstart/cache-refresh.
- Hervat na manual hold zonder directe temperatuurwrite.
- Effectieve Voorrang-uitkomst boven en onder Auto laden.
- Begrensde leerreset zonder wijziging van operationele klimaatveiligheid of apparaatopdracht.
- Wallbox-sessieclassificatie en versheid opnieuw na upgrade, inclusief de nog niet live doorlopen zonne-auto- en manuele toestanden.
- De bestaande koelroute en DHW-terugval tijdens een echte actieve koelcyclus.
- Eén echte nieuwe AEG-belading met APP uit→aan, maximaal één START en bescherming tot End Of Cycle.

Er wordt in deze releasehandleiding niet beweerd dat de laatste twee fysieke scenario's al zijn uitgevoerd.

## Rollback

1. Zet SolarPilot op **Pauze**.
2. Laat een lopende beschermde cyclus veilig afwerken; verstuur geen STOPRESET vanuit SolarPilot.
3. Herstel de back-up of installeer de geregistreerde beta.41 opnieuw.
4. Herstart Home Assistant en controleer de werkelijk geladen backend- en kaartversie.
5. Controleer Voorrang, boiler-manual-hold, klimaat-OFF-eigendom en Wallbox fail-closed gedrag opnieuw voordat je Automatisch regelen gebruikt.

Zie `TESTRESULTATEN_BETA42.md` voor de werkelijke software-gate en het liveacceptatieplan.
