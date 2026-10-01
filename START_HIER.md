> **Actuele release: beta.40.** Deze release herstelt de bewezen Home Assistant-opstartvolgordefout waardoor beta.39 de legacy-markers te vroeg controleerde en het later complete AEG-profiel niet meer aanmaakte. Een begrensde post-start recovery kan het profiel nu veilig onder Toestellen en Voorrang opnemen. Zij verstuurt geen START; APP-vrijgave en alle veiligheidslocks blijven verplicht.

# SolarPilot beta.40 — installatie en upgrade

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

## Dagoverzicht bekijken

In **SolarPilot → Verbruikers** staat bij ieder toestel **Dagoverzicht**. De popup toont geregistreerde draaitijd per dag, begin/einde per sessie en de bevestigde SolarPilot-redenen of een expliciete melding van externe/onbekende bediening. De registratie begint na installatie van deze functie; gewone updates behouden de gegevens. Een slimme stekker registreert ingeschakelde tijd, niet vanzelf afzonderlijke compressorcycli. Zie `docs/ACTUELE_WERKING.md` voor meetdekking, opslaggrenzen en details.

## Nieuw in beta.29: AEG en analyse

Afwasmachine-start met eenmalige klaarzettoestemming en native AEG-START, nooit via de netstekker. Een gestart programma blijft beschermd. De knop **Analyse-export** onderaan het dashboard maakt een lokaal JSON-bestand voor handmatige probleem- en modelanalyse. Zie [instellen en beperkingen](docs/AFWASMACHINE_EN_ANALYSE.md). Nieuwe fysieke koppelingen worden niet automatisch geactiveerd.

## Huidige AEG-voorrang en APP-start

[Beta.32 instellen](docs/BETA32_INSTELLEN.md) beschrijft de standaard AEG-voorkeur
onder warmtepompcomfort en boven Wallbox, lagere verbruikers en extra 60 °C.
[APP en deadline](docs/BETA31_INSTELLEN.md) zijn cumulatief inbegrepen.
Volledige faseprofielplanning blijft uitgesteld tot de latere Shelly-update.


## Beta.40-upgrade: laat AEG-profiel veilig herstellen

Beta.40 houdt de bestaande legacy-recovery na SolarPilot-start maximaal tien minuten gericht actief wanneer Home Assistant de template-markers of AEG-entiteiten later laadt. Alleen één complete same-device mapping wordt opgeslagen; de migratie zelf maakt geen APP-aanvraag en verstuurt geen START. Voor de echte controle:

1. Controleer dat de SolarPilot-status werkelijk `1.0.0-beta.40` toont en wacht na de herstart maximaal tien minuten.
2. Controleer **SolarPilot → Toestellen**, **Voorrang** en de rolstatus in `dishwasher_setup`.
3. Kies het AEG-programma, sluit de deur en zet APP/remote-start uit en opnieuw aan zodat exact `Enabled` als nieuwe overgang wordt gezien.
4. Controleer geplande dag/deadline en wachtrede. Een onveranderde Ready To Start/deur/programmakeuze mag niet alleen door ouderdom afvallen zolang ConnectivityState actueel blijft.
5. Er mag maximaal één native START worden verstuurd. Een lopende Washing/Rinsing/Drying/Ado Drying-fase blijft beschermd tot het echte End Of Cycle.

Zie `docs/BETA40_INSTELLEN.md` voor de volledige upgrade- en rollbackprocedure.
