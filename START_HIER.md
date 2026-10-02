> **Actuele software-release: beta.42.** Deze release voegt een veilige hervatroute na handmatige boilerbediening toe, toont de effectieve Voorrang-uitkomst onder Auto laden, corrigeert uitleg/labels en begrenst het wissen van leergegevens. De beta.40-AEG-recovery en beta.41-klimaat-/DHW-grenzen blijven ongewijzigd behouden. De werkelijk geladen live versie blijft beta.41 totdat de upgrade hieronder is uitgevoerd en gecontroleerd.

# SolarPilot beta.42 — installatie en upgrade

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

## Beta.42-upgrade: controleer eerst, activeer daarna gericht

1. Installeer beta.42 via HACS en herstart Home Assistant.
2. Controleer dat de SolarPilot-status werkelijk `1.0.0-beta.42` toont. Vernieuw de browser geforceerd wanneer alleen de kaart nog een oudere versie toont. De vóór-upgrade bewezen basis was beta.41 op Home Assistant Core `2026.9.4`; dat bewijst niet dat beta.42 al geladen is.
3. Open **Warmte & comfort** in **Pauze** of **Alleen bekijken**. Bij een herkende handmatige boilerpauze mag **Hervat** alleen de SolarPilot-rust beëindigen: geen directe temperatuurwrite en niet tijdens Automatisch regelen of een wachtende opdracht.
4. Open **Voorrang**. Controleer de opgeslagen keuze én de effectieve uitkomst. Een toestel met opgeslagen **Ja** onder **Auto laden** moet zichtbaar effectief **Nee** melden totdat je het erboven plaatst. Opslaan stuurt op zichzelf geen toestel.
5. Open **Leren & modelkwaliteit**. Gebruik **Apparaat-, lokale PV-, fase- en klimaatleerdata wissen** alleen bewust: lokale afgeleide Wallbox-, toestelvermogen-, PV-, fase- en klimaatleerlagen worden gewist, maar instellingen en operationele klimaatveiligheid blijven staan. De knop mag geen regelcyclus of fysieke opdracht uitvoeren.
6. Controleer onder **Configureren → Auto & batterij → Wallbox → Koppeling** de werkelijke sessiebron. Gebruik een actuele bron die zonne-auto, manueel laden en gestopt onderscheidt; de Full Solar-instelling alleen is geen bewijs. De live bron is met fysieke bronversheid en heartbeat als actueel gestopt geval gecontroleerd; bevestig na upgrade ook de andere werkelijke sessietoestanden. Onbekend of oud blijft fail-closed.
7. Controleer **Warmte & comfort** eerst zonder fysieke uitbreiding. Handmatig OFF blijft beschermd. De koelroute en onmiddellijke DHW-terugval tijdens een echte koelcyclus zijn nog een expliciete liveacceptatiestap.
8. Kies daarna pas globaal **Automatisch regelen** en zet uitsluitend de gecontroleerde toestellen afzonderlijk op **Auto**. Laat andere toestellen **Uitgesloten**. De oude 60/50-boilerautomatiseringen zijn in de bewezen live basis uitgeschakeld en mogen niet parallel opnieuw worden aangezet.

Zie `docs/BETA42_INSTELLEN.md` voor de volledige controle en rollback.


## Behouden uit beta.40: laat AEG-profiel veilig herstellen

Beta.40 houdt de bestaande legacy-recovery na SolarPilot-start maximaal tien minuten gericht actief wanneer Home Assistant de template-markers of AEG-entiteiten later laadt. Alleen één complete same-device mapping wordt opgeslagen; de migratie zelf maakt geen APP-aanvraag en verstuurt geen START. Voor de echte controle:

1. Controleer dat de SolarPilot-status werkelijk `1.0.0-beta.42` toont en wacht na de herstart maximaal tien minuten wanneer het AEG-profiel nog door de behouden herstelroute moet worden aangemaakt.
2. Controleer **SolarPilot → Toestellen**, **Voorrang** en de rolstatus in `dishwasher_setup`.
3. Kies het AEG-programma, sluit de deur en zet APP/remote-start uit en opnieuw aan zodat exact `Enabled` als nieuwe overgang wordt gezien.
4. Controleer geplande dag/deadline en wachtrede. Een onveranderde Ready To Start/deur/programmakeuze mag niet alleen door ouderdom afvallen zolang ConnectivityState actueel blijft.
5. Er mag maximaal één native START worden verstuurd. Een lopende Washing/Rinsing/Drying/Ado Drying-fase blijft beschermd tot het echte End Of Cycle.

Zie `docs/BETA40_INSTELLEN.md` voor de oorspronkelijke herstelachtergrond en `docs/BETA42_INSTELLEN.md` voor de actuele upgrade- en rollbackprocedure. Een echte AEG-belading is nog niet als beta.42-liveacceptatie uitgevoerd.
