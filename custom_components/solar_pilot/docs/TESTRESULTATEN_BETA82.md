# SolarPilot beta.82 — brongebonden test- en releaseverslag

Versie: **1.0.0-beta.82** · 14 oktober 2026

Bouwbasis: gepubliceerde beta.81-commit `8083e3647e7bb0e09620da8194dd2ca9e157afe6`, tree `46d3f51af9b1d3dcdb6bcccbfac47a874aa6c92f`. Die eerdere release is herkomstbewijs en geen beta.82-validatie.

## Concrete wijzigingen en bewijsgrenzen

Een afzonderlijke read-only bedrijfsweergave combineert uitsluitend de bestaande actuele native acties, exact herkende tankroute, gekozen ruimtestand, tankrust en toegewezen voedingsmetingen. Ontdooien houdt voorrang; gekozen HEAT/COOL zonder verse tankrust bewijst geen ruimtebedrijf. De oudste noodzakelijke bron begrenst een afgeleide taak. Gekoppelde ontbrekende of ongeldige metingen blijven onbekend; een bruikbare deelmeting kan alleen presentatie ondersteunen en maakt geen totaal of leerbewijs compleet.

De warmtepompgeschiedenis registreert elektrische ondersteuning als een aanvullende lijn naast de primaire thermische taak. Ondersteuning vervangt Boiler opwarmen, Verwarmen of Koelen niet en wordt niet dubbel bij totale activiteit opgeteld. Historische taakperioden worden niet herlabeld of teruggevuld. De bestaande volledige-vermogenintegraal en energiedekking blijven afzonderlijk.

Het SG-contact heeft een eigen brongebonden AAN/UIT/ONBEKEND-balk. Een aanvraag of warmtepompactiviteit kan een ontbrekend of oud contact niet bevestigen. Actuele en historische boilerwaarden tonen het gewone gemelde doel met oorspronkelijke brontijd; meetgaten, verouderde waarden en onbekend effectief SG-/hygiënedoel blijven onbekend. Nieuwe aanvullende gegevens behouden de bestaande opslagversie en private bronleesrechten.

Alle publieke fixtures zijn fictief. Privé-exports, analysefeedback, woninglabels, persoonlijke bronidentiteiten en schermafbeeldingen maken geen deel uit van repository, testdata of pakketten. De regeling en conservatieve modelvoorwaarden veranderen niet.

## Lokale uitvoering

De definitieve lokale volledige regressiesuite is geslaagd: **5482 tests in 99,78 seconden**, Python 3.12.14 / pytest 9.1.1. Daarnaast zijn **131 gerichte tests** voor de laatste versiegebonden dialogs, taakweergave en historie geslaagd. Deze gerichte groep overlapt de volledige suite en wordt niet bij het totaalaantal opgeteld.

| Controle | Lokaal resultaat |
|---|---|
| Volledige regressiesuite op de definitieve beta.82-bron | 5482 geslaagd; 0 mislukt |
| Laatste gerichte taak-, historie-, UI- en versiegebonden dialogcontroles | 131 geslaagd; overlapt volledige suite |
| Nieuwe regressies ten opzichte van beta.81 | 82: 40 taak-/brongevallen, 31 historiegevallen en 11 UI-gevallen |
| Guide, optiehulp en embedded mirrors | Actueel beta.82; 345 optievelden; checks geslaagd |
| Overdracht, privacy-preflight, repository en SG-opdrachtgrens | Geslaagd |
| Beide meegeleverde frontendmodules | Node-syntax geslaagd |
| Python en component-JSON | 83 Python-bestanden en 4 JSON-bestanden parsebaar |
| Diffcontrole | Geslaagd |

De nieuwe regressies toetsen native voorrang, echte actieconflicten, scopebewust UIT, ontdooien, afzonderlijke verse hoofd-/heaterfeeds, oude/negatieve/boolean-metingen, vereiste verse tankrust, oorspronkelijke afzonderlijke afloop en volledige splitmeting. Ondersteuningsactiviteit en opgeteld ondersteuningsvermogen houden hun eigen bewijsgrenzen: een actieve feed kan activiteit bevestigen terwijl een ontbrekende of verlopen benodigde feed geen volledig opgeteld vermogen geeft. Een positieve actuele compressorfrequentie kan activiteit ondersteunen zonder een onbekende thermische richting in te vullen.

Historiegevallen bewaken afzonderlijke supportduur, behoud van oude taakperioden en energie, historische ACL, retentie/restore, onbekende opslag, brongebonden contactafloop en gescheiden temperatuur-/doelpunten zonder backfill. De UI-gevallen toetsen taak-/supportweergave, contact AAN/UIT/ONBEKEND, temperatuurpunten, escape en behoud van open popup. Alleen fictieve fixtures zijn gebruikt; er is geen opdracht naar een fysiek apparaat verstuurd.

De lokale review en broncontroles zijn geslaagd. **Echte Chromium, Home Assistant Core 2026.10.0 en PowerShell zijn in deze lokale ronde niet uitgevoerd**; hun afzonderlijke CI-gates moeten op dezelfde exacte bron slagen. Software-uitvoering blijft afzonderlijk van fysieke Panasonic-/Shelly-acceptatie, compressorlooptijd, werkelijk effectief SG-doel en causale warmteopname.

## CI en publicatie op dezelfde exacte bron

Alle vijf gates van [Validate](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml) moeten op dezelfde exacte releasebron slagen:

1. Repositorycontroles, volledige suite, syntax en native PowerShell-publisherproeven.
2. HACS-validatie.
3. Hassfest.
4. Echte Home Assistant Core 2026.10.0: setup, platforms, reload, unload, immutable configuratie en optionele bronselectoren.
5. Echte Chromium: alle behouden browserproeven en de nieuwe taak-/contact-/temperatuurweergave op mobiele en brede schermen, met escape, onbekende waarden en behoud van open popup.

Chromium, PowerShell en de echte Core-uitvoering zijn afzonderlijke CI-proeven; lokale doubles vervangen die niet. Niet uitgevoerde gates blijven open. Oudere CI-resultaten vormen geen nieuw beta.82-bewijs. De bestaande workflow publiceert pas na de vijf gates en maakt daarna een nieuwe immutable annotated tag.

## Pakketbewijs

De workflow vergelijkt vóór upload en na terugdownload alle vier assets bytegelijk met dezelfde bron-SHA:

- `SolarPilot-v1.0.0-beta.82-GitHub-HACS.zip`
- `SolarPilot-v1.0.0-beta.82-local.zip`
- `BETA82_INSTELLEN.md`
- `TESTRESULTATEN_BETA82.md`

Publicatie is pas bevestigd wanneer **Download and verify published four assets against the exact tag** slaagt met `download_verified: true`. Dit bronverslag bevat geen vooraf verzonnen toekomstig run-ID. Bekijk na publicatie de exacte tagcommit en gekoppelde push-run bij [release beta.82](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.82).

Instellingen, bronbindings, prioriteiten, modellen, historie en APP-aanvragen blijven behouden. Panasonic blijft SG-only, Wallbox read-only en AEG start-only. De gekozen 600 W/300 s/minimum 1200 s en alle harde guards veranderen niet. Upgrade en rollback naar beta.81 staan in [BETA82_INSTELLEN.md](BETA82_INSTELLEN.md).
