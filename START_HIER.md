# SolarPilot beta.70 — installatie en upgrade

Beta.70 voegt lokale warmtepompgeschiedenis toe: gekozen dag, geregistreerde activiteit/starts/stops, taken, gemeten totale elektrische energie, meetdekking en afzonderlijke SG-lagen. De popup geeft geen bediening. Panasonic blijft zelfstandig regelen; de bestaande SG-startbijdrage, elektrische grenzen, instellingen en overige apparaten blijven behouden.

**Begin met [BETA70_INSTELLEN.md](docs/BETA70_INSTELLEN.md).** Daar staan behoud, back-up, controle, geschiedenis en rollback naar beta.69. De volledige actuele werking staat in [ACTUELE_WERKING.md](docs/ACTUELE_WERKING.md) en **SolarPilot → Uitleg**. Actuele software-/publicatiestatus: [TESTRESULTATEN_BETA70.md](docs/TESTRESULTATEN_BETA70.md).

## Update

1. Maak vooraf een volledige privé HA-back-up, inclusief instellingen, SolarPilot-opslag, modellen, tickets, geschiedenis en userfiles. Bewaar beta.69-code.
2. Geef een eigen SG-aanvraag vrij en controleer contactstand/lokale afloop vóór codevervanging. Behoud beschermde cycli.
3. Update via HACS naar exact `1.0.0-beta.70` na publicatie, herstart HA volledig en herlaad de pagina volledig of sluit de app volledig af en open haar opnieuw.
4. Controleer backend- en geladen kaartversie apart. Bewaar de bestaande entry, instellingen, userfiles en opslag; geen reset of herbevestiging van ongewijzigde geldige koppelingen.

Lokaal vervangen: uitsluitend `custom_components/solar_pilot` uit het local-ZIP. Eerste installatie: GitHub-repository in HACS als **Integration**, volledige HA-herstart en toevoegen onder **Instellingen → Apparaten & diensten**. Controleer P1/PV eerst in **Alleen bekijken**. De frontend wordt automatisch geregistreerd; een aparte Lovelace-resource is niet nodig.

## Geschiedenis gebruiken

Open **Geschiedenis** bij de warmtepomp in Overzicht, Toestellen of Warmtepomp. Kies een dag, Vandaag of zeven/dertig dagen. Ontbrekende data blijft zichtbaar als geen registratie. De registratie begint na deze installatie en bewaart maximaal dertig lokale kalenderdagen in aparte HA-opslag. Bestaande verbruikerhistorie, modellen en analyse worden niet teruggevuld of vervangen.

Starts/stops en geregistreerde draaitijd zijn waargenomen activiteit, geen bewezen compressorlooptijd. Elektrische kWh gelden alleen voor bruikbare complete actuele bevestigde totale meting en hebben een eigen meetdekking. SG-aanvraag, gemeld contact en ontvangen SG blijven apart. Gelijktijdig verbruik bewijst geen extra SG-kWh of causale besparing.

De bestaande SG-only bevoegdheid blijft: één toegewezen bestaande uitgang, Panasonic verder read-only. De gewone start-/stop-/leasevoorwaarden en fysieke grenzen blijven behouden. Controleer werkelijke hardware of gewijzigde koppelingen alleen volgens de bestaande lokale ingebruiknamevoorwaarden.

## Rollback

Geef de eigen SG-aanvraag vrij, controleer contact/lokale afloop, stop beta.70 en herstel gecontroleerde beta.69-code. Behoud de afzonderlijke nieuwe geschiedenis als je later weer wilt upgraden; beta.69 gebruikt haar niet. Voor exact herstel van de pre-upgradetoestand gebruik je de volledige passende privéback-up naast de code. Verwijder de entry niet en laat nooit twee runtimes tegelijk werken. De volledige procedure staat in [BETA70_INSTELLEN.md](docs/BETA70_INSTELLEN.md).
