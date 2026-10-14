# SolarPilot beta.83 — brongebonden test- en releaseverslag

Versie: **1.0.0-beta.83** · 14 oktober 2026

Bouwbasis: gepubliceerde beta.82-commit `a1b051d9c780ba1027ee48c261c9fafa2388f561`, tree `6e5205c1d3acc800b60551e68d8bd78f63e797b0`. Die eerdere release is herkomstbewijs en geen beta.83-validatie.

## Concrete wijzigingen en bewijsgrenzen

De uitsluitend voor presentatie bedoelde Aquarea-interpretatie gebruikt gecontroleerde semantiek van de bekende provider-/librarycombinatie. De library koppelt globale bedrijfstoestand aan `specialStatus`; een hierdoor ontstane OFF krijgt geen universele betekenis. Actuele afzonderlijke pomp-, richting-, ingeschakelde zone- en tankvelden ondersteunen alleen een passende expliciete afleiding. Defrost houdt voorrang. Nieuwe historische provider-evidence bewaart uitsluitend een gesloten generieke projectie van getypeerde rollen en oorspronkelijke tijden; apparaat-/entiteitsidentiteiten worden verwijderd. Restore mag geen onbekend contract, extra velden of vervalste actualiteit als geverifieerd bewijs laden. Dit verandert geen upstream-object, directe programmaopdracht, conservatieve leerclassificatie of SG-veiligheidsvrijgave.

Het tapwater-SG-doel is een read-only berekening van een verse gewone doelbron en een lokaal bevestigd percentage. De afzonderlijke displayselector kiest de geregistreerde native doelbron zonder de bestaande regelbron te wijzigen. Een opaque bronbinding voorkomt hergebruik van bevestiging na een vervangen, hergebruikte, onbekende of niet-overeenkomende entiteit. Bevestiging en bronactualiteit blijven afzonderlijk; een standaardpercentage is geen gecontroleerde lokale instelling. Gemeld contact AAN/UIT/ONBEKEND blijft apart van aanvraag en SG-ontvangst. Historische doelpunten gebruiken uitsluitend de destijds vastgelegde metadata, geen huidig percentage op oude data. Ongeldige doelen, percentages, tijden of tegenstrijdige historische waarden blijven onbekend of worden als ongeldig afgewezen.

De onderzoeksweergave scheidt eerder beoordeelde context van actuele bronwaarneming en houdt verklaring, getallen en tijdstippen coherent. Oorspronkelijke forecastuitgifte moet een bruikbare tijd zijn; ontbrekende, nul- of ongeldige waarden worden geen 1970-datum. Vooruit vastgelegde PV-vergelijkingen tonen daglicht en nacht als aparte populaties met hun eigen aantal en foutmaten, uitsluitend met passend vers oorspronkelijk zonnestandbewijs. Overige 0/0-vergelijkingen en onbekende daglichtcontext blijven apart. Unieke doelen en UTC-brondagen zijn geen bewezen onafhankelijke statistische proeven. De bestaande kalibratie, realtime regeling en onbekende oorspronkelijke gegevens blijven behouden.

Het nieuwe [UPSTREAM_BRONNEN.md](UPSTREAM_BRONNEN.md) gebruikt uitsluitend opnieuw gecontroleerde publieke vaste bronnen. Op 14 oktober is Aquarea v1.5.3 gepubliceerd; PR 129/130 zijn gemerged, aioaquarea PR 12 en Aquarea PR 125 zijn nog open. Open code of een upstream-versienummer certificeert geen lokale installatie, hardwareoorzaak of geïmplementeerde SolarPilot-correctie.

Alle publieke fixtures zijn fictief. Privé-exports, analysefeedback, woninglabels, persoonlijke bronidentiteiten en schermafbeeldingen maken geen deel uit van repository, testdata of pakketten. Alleen daadwerkelijk geïmplementeerde en geteste generieke voorstelbetekenissen mogen aan het vertrouwde release-/digestregister worden gekoppeld.

## Lokale uitvoering

De definitieve lokale volledige regressiesuite is geslaagd: **5694 tests in 105,06 seconden**, Python 3.12.14 / pytest 9.1.1, **0 mislukt**. De onafhankelijke review is akkoord. Oudere releaseaantallen worden niet als beta.83-bewijs overgenomen.

| Controle | Lokaal resultaat |
|---|---|
| Volledige regressiesuite op de definitieve beta.83-bron | 5694 geslaagd; 0 mislukt |
| Bekende Aquarea-semantiek, verse afzonderlijke velden en defrostvoorrang | Geslaagd binnen de volledige suite |
| Lokaal bevestigd SG-percentage, gesloten bronbinding en historische herkomst | Geslaagd binnen de volledige suite |
| Samenhangend onderzoeksbewijs, forecasttijdvalidatie en gescheiden vooruit-PV-populaties | Geslaagd binnen de volledige suite |
| Kaart-/geschiedenisweergave, escape, bronverval en open-popupbehoud | Geslaagd binnen de volledige suite |
| Vertrouwd generiek voorstelregister | Alle 7 nieuwe en 9 behouden betekenissen exact herkend; 16 softwarestatussen |
| Guide, optiehulp en embedded mirrors | Actueel beta.83; 348 optievelden; guidehash `656c78051c1faf08` |
| Overdracht, privacy-preflight, repository en SG-opdrachtgrens | Geslaagd |
| Beide meegeleverde frontendmodules | Node-syntax geslaagd |
| Python en component-JSON | 85 component-Python-bestanden en 4 JSON-bestanden parsebaar |
| Diffcontrole en onafhankelijke review | Geslaagd |

De regressies onderscheiden bekende en onbekende providercontracten, echte OFF/conflicten, actuele getypeerde pomp/richting/zone/tank, gefaalde polls, cached startup en optimistische mutaties. Native veldcontext wordt als dezelfde oorspronkelijke poll beoordeeld; afzonderlijke vermogensmetingen behouden hun eigen actualiteit en afloop zonder timestamps te vernieuwen. De correctie verleent uitsluitend presentatiebewijs.

Doelregressies bewaken lokale percentagebevestiging en de aparte geregistreerde displaybron, opaque bronbinding, oorspronkelijke doel- en contacttijden, toekomstige/ongeldige metadata, onbekende waarden, historische ACL en restore zonder terugvullen. Diagnose-/PV-regressies bewaken samenhangende eerdere beoordeling, afzonderlijk actuele bron, echte bronwijziging, sentinel-/tijdeenheden, oorspronkelijke zonnestand en foutmaten binnen dezelfde populatie. Alleen fictieve fixtures zijn gebruikt; er is geen fysieke apparaatopdracht verstuurd.

De zeven nieuwe generieke voorstelbetekenissen zijn volledig geïmplementeerd, getest en aan beta.83 gekoppeld. Samen met negen behouden betekenissen leveren zij zestien exacte softwarestatussen. Dit register is geen bewijs van een fysieke meterreparatie, toegepast Panasonic-doel, SG-ontvangst of praktijkbesparing; een adviesupload maakt geen nieuwe implementatie.

**Echte Chromium, Home Assistant Core 2026.10.0 en PowerShell zijn in deze lokale ronde niet uitgevoerd**. Hun afzonderlijke CI-gates moeten op dezelfde exacte bron slagen. Software-uitvoering blijft afzonderlijk van fysieke Panasonic-/Shelly-acceptatie, compressorlooptijd, werkelijk effectief SG-doel en causale warmteopname.

## CI en publicatie op dezelfde exacte bron

Alle vijf gates van [Validate](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml) moeten op dezelfde exacte releasebron slagen:

1. Repositorycontroles, volledige suite, syntax en native PowerShell-publisherproeven.
2. HACS-validatie.
3. Hassfest.
4. Echte Home Assistant Core 2026.10.0: setup, platforms, reload, unload, immutable configuratie en optionele bronselectoren.
5. Echte Chromium: alle behouden browserproeven en de nieuwe bron-/doel-/diagnoseweergave op mobiele en brede schermen, met escape, onbekende waarden en behoud van open popup.

Chromium, PowerShell en de echte Core-uitvoering zijn afzonderlijke CI-proeven; lokale doubles vervangen die niet. Niet uitgevoerde gates blijven open. Oudere CI-resultaten vormen geen nieuw beta.83-bewijs. De bestaande workflow publiceert pas na de vijf gates en maakt daarna een nieuwe immutable annotated tag.

## Pakketbewijs

De workflow vergelijkt vóór upload en na terugdownload alle vier assets bytegelijk met dezelfde bron-SHA:

- `SolarPilot-v1.0.0-beta.83-GitHub-HACS.zip`
- `SolarPilot-v1.0.0-beta.83-local.zip`
- `BETA83_INSTELLEN.md`
- `TESTRESULTATEN_BETA83.md`

Publicatie is pas bevestigd wanneer **Download and verify published four assets against the exact tag** slaagt met `download_verified: true`. Dit bronverslag bevat geen vooraf verzonnen toekomstig run-ID. Bekijk na publicatie de exacte tagcommit en gekoppelde push-run bij [release beta.83](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.83).

Instellingen, bronbindings, prioriteiten, modellen, historie en APP-aanvragen blijven behouden. Panasonic blijft SG-only, Wallbox read-only en AEG start-only. De gekozen 600 W/300 s/minimum 1200 s en alle harde guards veranderen niet. Upgrade en rollback naar beta.82 staan in [BETA83_INSTELLEN.md](BETA83_INSTELLEN.md).
