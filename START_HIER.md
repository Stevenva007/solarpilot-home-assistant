# SolarPilot beta.46 — installatie en upgrade

Beta.46 herstelt de onnodige extra-warmwaterblokkering bij een betrouwbare native `aquarea`-actie `idle/off`. Een algemene `PUMP`-taak of AUTO-modus mag die actie niet als actieve koeling of verwarming behandelen. Echte koeling, ruimtecomfort, hygiëne en alle andere voorwaarden blijven gelden.

De definitieve test- en publicatiestatus staat in [docs/TESTRESULTATEN_BETA46.md](docs/TESTRESULTATEN_BETA46.md). In deze werksessie is geen live beta.46-installatie of fysieke opwarming bevestigd.

## 1. Vooraf

- Maak een actuele volledige Home Assistant-back-up en bewaar de gecontroleerde beta.45-release voor rollback.
- Laat een lopende beschermde afwas- of andere cyclus afwerken.
- Gebruik bij een nieuwe installatie **Alleen bekijken** voor de eerste broncontrole.
- Updates zijn cumulatief: bestaande Home Assistant-configuratie en lokale leerdata blijven behouden; tussenliggende beta-versies hoeven niet afzonderlijk geïnstalleerd te worden.

## 2. Via HACS installeren of upgraden

1. Voeg bij een nieuwe installatie in **HACS → Custom repositories** `https://github.com/Stevenva007/solarpilot-home-assistant` toe als type **Integration**.
2. Download of update naar exact `1.0.0-beta.46` zodra die release beschikbaar is.
3. Herstart Home Assistant volledig.
4. Controleer backendversie en vernieuwde kaart afzonderlijk. Een download of manifestnummer bewijst geen geladen code.
5. Voeg bij een nieuwe installatie **SolarPilot** toe via **Instellingen → Apparaten & diensten** en kies je P1/netbron en optionele PV-bron.

De interface verschijnt automatisch. Er is geen aparte Lovelace-resource of dashboard-YAML nodig. Bij een lokaal pakket vervang je uitsluitend `custom_components/solar_pilot`; bewaar bestaande `userfiles` en Home Assistant-opslag.

## 3. Optioneel privéprofiel

Plaats een bestaande installatie-specifieke `private_bundle.json` alleen lokaal in:

```text
/config/custom_components/solar_pilot/userfiles/private_bundle.json
```

Importeer via **SolarPilot → Configureren → Geavanceerd & systeem → Privéprofiel & historiek**. De bundel vult alleen lege, werkelijk bestaande entiteiten in. Fysieke klimaatbediening, fase-afbouw en boilerregeling krijgen hierdoor geen automatische vrijgave. Deel dit bestand niet publiek.

## 4. Warm water controleren

Controleer in **Alleen bekijken** of **Pauze** de echte adapterherkomst, bronversheid, ruwe klimaat- en taakstatus, gemeld tankdoel, tankmeting, P1/PV, handmatige functies, hygiëne en pending opdrachten.

- Exact geregistreerde `aquarea` met actuele native `idle/off` kan de klimaatguard vrijgeven, ook in AUTO/HEAT_COOL en bij algemene `PUMP`-taakinfo.
- Werkelijke `cooling` blijft extra warmte begrenzen. Werkelijke `heating/preheating/defrosting` houdt de ingestelde ruimtecomfortvoorrang.
- Ontbrekende, oude, restored of onbeschikbare klimaatdata blijft blokkeren. Een taakmelding vervangt geen ontbrekende betrouwbare klimaatbron.
- Oudere `panasonic_cc` in AUTO/HEAT_COOL blijft zonder actuele expliciete `IDLE/WATER`-taak onduidelijk.
- Alleen bewezen koeling verlengt de ingestelde koelrusttijd. Onbekende data maakt geen nieuwe halfuurwachttijd na bronherstel.

Een vóór beta.46 opgeslagen koel-/onzekerheidstijd blijft conservatief behouden. Een bestaande uitloop of bescherming tijdens een native warmwatertaak kan daarom nog tijdelijk gelden; de upgrade wist geen mogelijk echte koeling.

Een grote vrije injectie geeft nog geen startgarantie: zonnestabiliteit, rust tussen doelopdrachten, reserves, eigendom, hygiëne, koeluitloop en elektrische grenzen worden afzonderlijk beoordeeld. Het normale doel blijft standaard 50 °C, de bewaakte comfortgrens 46 °C en extra overschot maximaal 60 °C. Extra 60 °C krijgt nooit Wallboxkrediet.

## 5. Hervatten en doelbevestiging

Gebruik alleen waar nodig de bestaande gerichte boilerreview buiten **Automatisch regelen** en zonder pending opdracht. Zij schrijft zelf geen temperatuur. De update hervat een beschermende pauze niet automatisch.

Hervat gewone regeling na bron- en beveiligingscontrole en observeer een natuurlijke toegestane doelopdracht. Voor exact geregistreerde `aquarea` en `panasonic_cc` blijft minstens tien seconden nodig vóór een passende nieuwe Home Assistant-doelrapportage telt. Ook die rapportage bewijst geen compressorstart of bereikte tanktemperatuur.

Laat concurrerende boilerautomatiseringen uit zolang SolarPilot regelt. AEG-APP-aanvragen en beschermde cycli blijven behouden; maak geen nieuwe APP-aanvraag of START om updateacceptatie af te dwingen. De Wallbox blijft read-only. Nieuwe toestellen blijven afzonderlijk gecontroleerd en vrijgegeven.

## 6. Uitleg en rollback

De enige actuele regelbeschrijving staat in [docs/ACTUELE_WERKING.md](docs/ACTUELE_WERKING.md) en in Home Assistant onder **SolarPilot → Uitleg**. De volledige upgradecontrole staat in [docs/BETA46_INSTELLEN.md](docs/BETA46_INSTELLEN.md).

Voor rollback: **Pauze → beschermde cycli afwerken → onveranderlijke beta.45-release of gecontroleerde back-up herstellen → Home Assistant herstarten → backend/kaart en beveiligingen controleren**. Beta.45 behoudt de vertraagde `aquarea`-doelbevestiging maar heeft nog de te brede taak-/AUTO-blokkering. Oude release-documenten zijn historische informatie; het actuele `OVERDRACHT.md` beschrijft de huidige bron.
