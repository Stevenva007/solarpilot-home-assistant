> **Actuele release: beta.41.** Deze release maakt Voorrang en toestelbeslissingen begrijpelijker, bewaart handmatig uitgeschakelde klimaatzones en laat extra boilerwarmte veilig en direct terugvallen bij echte netafname of koeling. De beta.40-AEG-recovery blijft ongewijzigd behouden: geen START tijdens migratie, één complete same-device mapping en APP-vrijgave per belading.

# SolarPilot beta.41 — installatie en upgrade

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

## Beta.41-upgrade: controleer eerst, activeer daarna gericht

1. Installeer beta.41 via HACS en herstart Home Assistant.
2. Controleer dat de SolarPilot-status werkelijk `1.0.0-beta.41` toont. Vernieuw de browser geforceerd wanneer alleen de kaart nog een oudere versie toont.
3. Open **Voorrang**. Beschermde regels staan vast bovenaan; toestellen, **Auto laden** en extra warm water staan in één flexibele lijst. Controleer per toestel de keuze **Mag de auto minder laden?**. Opslaan stuurt op zichzelf geen toestel.
4. Open **Toestellen**. Controleer bij een nog niet gestart toestel de beslisreden, startvoorwaarden, benodigd vermogen en stabiliteitstijd. De samenvatting van de regelaar blijft doorslaggevend; een groen lijstje alleen is geen startgarantie.
5. Controleer onder **Auto & batterij → Wallbox** de werkelijke sessiebron. Gebruik de bron die volledige waarden onderscheidt voor zonne-auto, manueel laden en gestopt; de Full Solar-instelling alleen is geen bewijs van de actieve sessie. SolarPilot blijft read-only.
6. Controleer **Warmte & comfort** eerst in **Alleen bekijken**. Een handmatig OFF gezette zone hoort bij een gewone AUTO-beslissing OFF te blijven. Alleen een echte harde comfortoverschrijding mag die ene zone naar Panasonic AUTO vrijgeven.
7. Controleer bij warm water dat een door SolarPilot beheerd extra doel bij actieve koeling of echte netafname zonder terugvalvertraging naar het gewone/koelbegrensde doel terugvalt. Bij een handmatige Panasonic-override schrijft SolarPilot niets.
8. Kies daarna pas globaal **Automatisch regelen** en zet uitsluitend de gecontroleerde toestellen afzonderlijk op **Auto**. Laat andere toestellen **Uitgesloten**.

Zie `docs/BETA41_INSTELLEN.md` voor de volledige controle en rollback.


## Behouden uit beta.40: laat AEG-profiel veilig herstellen

Beta.40 houdt de bestaande legacy-recovery na SolarPilot-start maximaal tien minuten gericht actief wanneer Home Assistant de template-markers of AEG-entiteiten later laadt. Alleen één complete same-device mapping wordt opgeslagen; de migratie zelf maakt geen APP-aanvraag en verstuurt geen START. Voor de echte controle:

1. Controleer dat de SolarPilot-status werkelijk `1.0.0-beta.41` toont en wacht na de herstart maximaal tien minuten wanneer het AEG-profiel nog door de behouden herstelroute moet worden aangemaakt.
2. Controleer **SolarPilot → Toestellen**, **Voorrang** en de rolstatus in `dishwasher_setup`.
3. Kies het AEG-programma, sluit de deur en zet APP/remote-start uit en opnieuw aan zodat exact `Enabled` als nieuwe overgang wordt gezien.
4. Controleer geplande dag/deadline en wachtrede. Een onveranderde Ready To Start/deur/programmakeuze mag niet alleen door ouderdom afvallen zolang ConnectivityState actueel blijft.
5. Er mag maximaal één native START worden verstuurd. Een lopende Washing/Rinsing/Drying/Ado Drying-fase blijft beschermd tot het echte End Of Cycle.

Zie `docs/BETA40_INSTELLEN.md` voor de oorspronkelijke herstelachtergrond en `docs/BETA41_INSTELLEN.md` voor de actuele upgrade- en rollbackprocedure.
