# Testresultaten SolarPilot 1.0.0-beta.71

Dit verslag onderscheidt de bewezen gepubliceerde bouwbasis van de nieuwe beta.71-uitvoeringen. Resultaten van een eerdere release zijn geen nieuwe testuitslag.

## Bewezen bouwbasis beta.70

Main en annotated tag staan op commit `630b0f3d260b0af91fbbcb81392eb903485f82e9`, tree `c310e354c55d3c8a7226d449cb4f72bc1aca4f81`. Actions-run `38140817189` slaagde met alle vijf CI-gates plus publicatie. Alle vier werkelijk gedownloade release-assets zijn exact met deze bron vergeleken. De volledige beta.70-suite slaagde lokaal met **3974 cases in 61,19 s** en in CI met **3974 in 71,31 s**. Oude tags/assets blijven ongewijzigd.

## Actuele beta.71-status

| Controle | Beta.71-uitvoeringsbewijs |
| --- | --- |
| Volledige lokale suite | **4049 geslaagde cases in 66,04 s**; geen fouten, skips of xfails. |
| Nieuwe gerichte regressies | **75 extra cases** tegenover beta.70: 35 export/API, 17 backend-wachtvoortgang, 21 UI en 2 catalogusgevallen; inbegrepen in 4049, geen tweede optelling. |
| Actuele guide/help, mirrors, handoff en syntax | Geslaagd; canonieke guide-hash `9ebc3824b1eeee4d`, 342 helpentries, Python-AST/Node-syntax en diffcontrole. |
| Privacy-, repository- en SG-grenscontrole | Geslaagd; openbare bron bevat geen private exports of cachebestanden, repositorystructuur en SG-bevoegdheidsgrens gecontroleerd. |
| Vijf CI-gates op exact dezelfde commit | Brongebonden uitvoering in [Actions](https://github.com/Stevenva007/solarpilot-home-assistant/actions/workflows/validate.yml). Controleer de exacte commit van de PR/tag; de workflow blokkeert publicatie tot alle vijf gates slagen. |
| Nieuwe tag, publicatie en vier teruggedownloade assets | Brongebonden bewijs in de Publish-job bij de exacte tagged commit: vier assets worden vóór upload en na geïsoleerde download met de Git-bron vergeleken. |

Geen voorafgaande beta.70-uitslag of tussentijdse beta.71-run wordt als definitief beta.71-bewijs gebruikt.

## Regressiescope

- SG-weergave: bestaande 300 seconden bevestiging en ingestelde startvertraging afzonderlijk; nul tijdens herbevestiging wacht op een passend nieuw eindrapport; nul startvertraging wacht op de bestaande actuele beoordeling. Echte rapporten, oude brondata, reset/native fasen en reload blijven herkenbaar. Uitlezen schept geen bedieningstoestemming.
- Exportvenster: 1/24/168 uur, alle strikt overlappende lokale datums, exacte middernacht en lokale 23/25-uursdagen. Dertig dagen retentie, gevraagde uren en werkelijk geëxporteerde datums zijn apart; één exporteindtijdstip voor alle onderdelen.
- Geregistreerde kalenderdagtotalen blijven intact. Grensdatums en meetdekking blijven apart. Geen evenredige energieknip, backfill of private ACL-/bindingidentiteiten in het geschiedenisdeel.
- Behoud van beta.70-geschiedenismodellen, aparte HA Store, API/READ-controles en popup, en van alle SG-only bevoegdheden, bron-/koel-/fase-/net-/voorrangsgrenzen en overige apparaten. Fixtures blijven fictief.

## CI en publicatie

De vijf bestaande CI-gates zijn repositorytests, HACS, Hassfest, echte Home Assistant Core 2026.10 setup/reload/unload en browser-UI op 320/390/768/1280 px. De bestaande warmtepomp-, warmtepompgeschiedenis- en verbruikerhistorieproeven blijven in de browsergate. Alleen dezelfde exacte commit met vijf geslaagde gates mag worden gepubliceerd.

De bestaande workflow maakt een nieuwe immutable annotated tag, bouwt beide ZIPs en vergelijkt alle vier assets vóór upload en na een geïsoleerde download bytegelijk met de commit. Naam, grootte, SHA-256 en broninhoud zijn afzonderlijk te controleren. De daadwerkelijke CI-uitslag en publicatiestappen staan bij de exacte broncommit in Actions; deze immutable bronbijlage voorspelt geen toekomstige run-ID of uitslag.

## Beperkingen

Software-/Core-/browser-/pakketbewijs is geen fysieke SG-, meter-, bedrading- of Panasonicacceptatie. Taaklabels en voedingsprofielen bewijzen geen heater- of klepfout. Volledige kalenderdagtotalen op gedeeltelijke grensdatums zijn geen exact energieverbruik over alleen de gevraagde rollende uren. Gemeten elektrische kWh geven geen thermische opbrengst, COP, compressorlooptijd of causale SG-besparing.

De bestaande `via_device`-deprecatiewaarschuwing richting Home Assistant 2027.8 blijft een afzonderlijk open punt; beta.71 verandert dat pad niet. Installatie, gegevensbehoud en rollback naar beta.70 staan in [BETA71_INSTELLEN.md](BETA71_INSTELLEN.md).
