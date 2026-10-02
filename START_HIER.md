> **Actuele software-release: beta.43.** Deze release maakt actuele activiteit en waardeschattingen eerlijker, bewaart begrensde read-only Wallbox-waarnemingen, beveiligt browsernavigatie met open formulieren en voegt een optionele maandagdeadline voor de AEG-afwasmachine toe. De werkelijk geladen en gecontroleerde live basis blijft beta.42 totdat de upgrade hieronder is uitgevoerd.

# SolarPilot beta.43 — installatie en upgrade

Dit is de aanbevolen eerste installatie.


> **Updates zijn cumulatief.** Je hoeft tussenliggende beta-versies niet één voor één te installeren of publiceren. Installeer de nieuwste release over je bestaande SolarPilot-installatie; Home Assistant-configuratie en lokale leerdata blijven behouden.

## 1. Vooraf

- Maak een volledige Home Assistant-back-up.
- Installeer/configureer HACS als dat nog niet gebeurd is.
- Een nieuwe installatie blijft tijdens de eerste controle in **Alleen bekijken**.

## 2. SolarPilot via HACS toevoegen

1. Open **HACS → Custom repositories**.
2. Voeg de publieke SolarPilot GitHub-repository toe als type **Integration**.
3. Download **SolarPilot**.
4. Herstart Home Assistant.
5. Ga naar **Instellingen → Apparaten & diensten → Integratie toevoegen → SolarPilot**.
6. Selecteer je netvermogensbron en optionele PV-bron en bevestig.

Daarna verschijnt de SolarPilot-interface automatisch. Er is geen aparte Lovelace-resource nodig.


## 3. Optioneel: privéprofiel + historiek in één bestand

Heb je een installatie-specifieke privébundel, plaats dan `private_bundle.json` in:

```text
/config/custom_components/solar_pilot/userfiles/private_bundle.json
```

Ga daarna naar **SolarPilot → Configureren → Geavanceerd & systeem → Privéprofiel & historiek** en kies importeren/herladen. De bundel vult alleen lege koppelingen in en gebruikt uitsluitend entiteiten die op dat moment werkelijk bestaan. Historische aggregaten worden als bootstrap gebruikt. Fysieke klimaatbediening, fase-afbouw en boilerregeling worden niet automatisch vrijgegeven; SolarPilot blijft bij een nieuwe installatie in Alleen bekijken.

## 4. Eerste controle

Controleer in Alleen bekijken achtereenvolgens P1/PV, Forecast.Solar/lokale schaduw, L1/L2/L3, Panasonic warm water, slim klimaat, Wallbox read-only en de Planning-tab.

Zet PV Excess Control en de twee oude boilerautomatiseringen pas uit wanneer SolarPilot daadwerkelijk klaar is om over te nemen.

## 5. Eerste fysieke test

Activeer eerst één niet-kritieke, goed meetbare flexlast. Breid pas daarna toestel per toestel uit.

## 6. Uitleg

De enige actuele regelbeschrijving is `docs/ACTUELE_WERKING.md` en dezelfde inhoud staat in Home Assistant onder SolarPilot → Uitleg.

## Apparaatgeschiedenis bekijken

In **SolarPilot → Toestellen** staat bij ieder toestel **Geschiedenis**. De popup toont geregistreerde draaitijd per dag, begin/einde per sessie en altijd een afzonderlijke Startreden en Stopreden. Een niet bewezen externe oorzaak blijft expliciet onbekend. De registratie begint na installatie van deze functie; gewone updates behouden de gegevens. Een slimme stekker registreert ingeschakelde tijd, niet vanzelf afzonderlijke compressorcycli. Zie `docs/ACTUELE_WERKING.md` voor meetdekking, opslaggrenzen en details.

## Nieuw in beta.29: AEG en analyse

Afwasmachine-start met eenmalige klaarzettoestemming en native AEG-START, nooit via de netstekker. Een gestart programma blijft beschermd. De knop **Analyse-export** onderaan het dashboard maakt een lokaal JSON-bestand voor handmatige probleem- en modelanalyse. Zie [instellen en beperkingen](docs/AFWASMACHINE_EN_ANALYSE.md). Nieuwe fysieke koppelingen worden niet automatisch geactiveerd.

## Huidige AEG-voorrang en APP-start

[Beta.32 instellen](docs/BETA32_INSTELLEN.md) beschrijft de standaard AEG-voorkeur
onder warmtepompcomfort en boven Wallbox, lagere verbruikers en extra 60 °C.
[APP en deadline](docs/BETA31_INSTELLEN.md) zijn cumulatief inbegrepen.
Volledige faseprofielplanning blijft uitgesteld tot de latere Shelly-update.

## Beta.43-upgrade: back-up, rustig upgraden, daarna gericht controleren

1. Maak een volledige Home Assistant-back-up en kies een moment zonder actieve beschermde afwas- of andere cyclus. Laat een lopende cyclus veilig afwerken; gebruik geen STOPRESET om voor de update ruimte te maken.
2. Installeer beta.43 via HACS en herstart Home Assistant volledig.
3. Controleer dat de SolarPilot-status werkelijk `1.0.0-beta.43` toont. Vernieuw de browser geforceerd en controleer ook de kaartversie. De vóór-upgrade bewezen basis is beta.42 op Home Assistant Core `2026.9.4`; dat bewijst niet dat beta.43 al geladen is.
4. Controleer **Nu actief**: alleen werkelijk actieve bronnen horen erin en gemeten of geschat vermogen moet herkenbaar blijven. Activiteit is geen bewijs van SolarPilot-eigendom of uitsluitend PV-verbruik.
5. Controleer de read-only Wallbox-uitleg en historie. De huidige native status mag wachten verklaren; een historische stopoorzaak mag alleen bevestigd zijn bij aantoonbaar tijdgecorreleerde rapporten. Een meetgat of herstart blijft onbekend en SolarPilot verstuurt geen Wallbox-opdracht.
6. Test browser Terug/Vooruit eerst met een ongewijzigd SolarPilot-scherm en daarna met een gewijzigd formulier. Niet-opgeslagen werk moet bevestiging vragen; opslaan en lopende acties mogen niet worden onderbroken.
7. Stel bij de afwasmachine alleen indien gewenst **Maandag: afwijkende uiterste starttijd** expliciet op `10:00`. Leeg houdt de gewone `13:00`, ook op maandag; andere dagen blijven `13:00`. Pas dit alleen na bevestiging toe op het huidige verzoek. Dezelfde geplande dag blijft staan en er ontstaat geen START.
8. Een update of herstart behoudt bestaande APP-tickets. APP dat bij startup al exact `Enabled` is, maakt of heractiveert geen ticket. Voor een nieuwe belading is opnieuw de fysieke overgang uit → exact `Enabled` nodig; alle startvoorwaarden en maximaal één START blijven gelden.
9. Controleer de automatische-voordeelweergave als afzonderlijke opportunity-value-schatting vanaf haar eigen start. Ontbrekende data is niet nul; trek het resultaat niet nogmaals van de elektriciteitskost af.
10. Controleer bij avondvoorraad dat alleen een bevestigde native Full Solar-sessie krediet kan geven: ingeschakeld, verbonden, vragend, minstens 50 W en status plus vermogen maximaal 120 seconden oud. De voorraad blijft begrensd tot de ingestelde limiet en maximaal 55 °C; extra 60 °C, manueel, onbekend of oud laden krijgt geen EV-krediet.
11. Kies pas daarna globaal **Automatisch regelen** en zet uitsluitend gecontroleerde toestellen afzonderlijk op **Auto**. De oude 60/50-boilerautomatiseringen blijven uit zolang SolarPilot de regelaar is.

Zie `docs/BETA43_INSTELLEN.md` voor de volledige controle en rollback.


## Behouden uit beta.40: laat AEG-profiel veilig herstellen

Beta.40 houdt de bestaande legacy-recovery na SolarPilot-start maximaal tien minuten gericht actief wanneer Home Assistant de template-markers of AEG-entiteiten later laadt. Alleen één complete same-device mapping wordt opgeslagen; de migratie zelf maakt geen APP-aanvraag en verstuurt geen START. Voor de echte controle:

1. Controleer dat de SolarPilot-status werkelijk `1.0.0-beta.43` toont en wacht na de herstart maximaal tien minuten wanneer het AEG-profiel nog door de behouden herstelroute moet worden aangemaakt.
2. Controleer **SolarPilot → Toestellen**, **Voorrang** en de rolstatus in `dishwasher_setup`.
3. Kies het AEG-programma, sluit de deur en zet APP/remote-start uit en opnieuw aan zodat exact `Enabled` als nieuwe overgang wordt gezien.
4. Controleer geplande dag/deadline en wachtrede. Een onveranderde Ready To Start/deur/programmakeuze mag niet alleen door ouderdom afvallen zolang ConnectivityState actueel blijft.
5. Er mag maximaal één native START worden verstuurd. Een lopende Washing/Rinsing/Drying/Ado Drying-fase blijft beschermd tot het echte End Of Cycle.

Zie `docs/BETA40_INSTELLEN.md` voor de oorspronkelijke herstelachtergrond en `docs/BETA43_INSTELLEN.md` voor de actuele upgrade- en rollbackprocedure. Een echte nieuwe AEG-belading wordt niet vooraf als beta.43-liveacceptatie geclaimd.
