# SolarPilot 1.0.0-beta.71 — SG-wachten en analysevenster

Beta.71 verduidelijkt twee bestaande processen: de afzonderlijke SG-wachtfasen en het warmtepompdeel van een privé-analyse-export. De regeling, wachttijden, native Panasonic-instellingen en dertig dagen bewaartermijn veranderen niet.

## Update met behoud van gegevens

1. Maak een volledige privé Home Assistant-back-up, inclusief instellingen, eigen opslag, modellen, tickets, gewone en warmtepompgeschiedenis en userfiles. Bewaar de gecontroleerde beta.70-code.
2. Geef vóór codevervanging een eigen SG-aanvraag vrij en controleer de gemelde contactstand/lokale afloop. Onderbreek geen beschermde apparaatcyclus.
3. Update via HACS naar exact `1.0.0-beta.71` zodra deze release is gepubliceerd. Bij lokale installatie vervang je uitsluitend `custom_components/solar_pilot`; behoud lokale userfiles en HA-opslag.
4. Herstart Home Assistant volledig. Herlaad de browser volledig, of sluit de app volledig af en open haar opnieuw. Controleer backend- en kaartversie apart.
5. Behoud de bestaande entry en alle geldige bindings, prioriteiten, SG-/profiel-/split-/koelbevestigingen en gebruikerswaarden. Controleer de wachtweergave en bestaande geschiedenis. Geen nieuwe verplichte entiteiten of algemene herbevestiging bij een ongewijzigde upgrade.

## Afzonderlijke SG-wachtfasen

| Fase | Betekenis |
| --- | --- |
| Nieuwe aanleiding bevestigen | De bestaande 300 seconden met echte nieuwe bronrapporten voor een nieuwe zonneperiode of passende verse native aanleiding. Reset- en native bewijsfasen houden hun eigen betekenis. |
| Wachten op actueel eindrapport | De bevestigingstijd is verstreken, maar het passende nieuwe eindrapport is nog nodig. Nul resterende seconden geeft geen starttoestemming. |
| Startvertraging | De ingestelde vertraging, standaard 120 seconden, na aanvaarde nieuwe aanleiding en zolang alle actuele startvoorwaarden gelden. |
| Geen lopende teller | Er is geen lopende bevestiging/startvertraging, of de brondata is te oud. Een voortlopende schermklok maakt brondata niet vers. |

Kaart en Details tonen deze fasen afzonderlijk. Ze voegen de timers niet samen en verkorten ze niet. Rust, hysterese, bronversheid, minimumtijden, sessielimiet, prioriteiten, lokale toestemming, koelbeveiliging en fysieke fase-/netgrenzen behouden hun bestaande werking. De uitleesweergave maakt geen opdracht of nieuw bedieningsrecht.

## Warmtepompgeschiedenis in het analysebestand

De bestaande warmtepompgeschiedenis bewaart maximaal dertig HA-lokale kalenderdagen. Het gevraagde analysevenster is afzonderlijk **1, 24 of 168 rollende uren**, met één vast eindtijdstip voor alle exportonderdelen. Bewaartermijn, gevraagde uren en aantal daadwerkelijk geëxporteerde datums zijn aparte gegevens.

Het warmtepompdeel bevat iedere lokale kalenderdag die met dat venster overlapt. Een venster van 168 uur kan acht datums omvatten en rond een tijdwissel soms negen. Exact op middernacht wordt geen lege einddag toegevoegd. Lokale 23/25-uursdagen houden hun werkelijke duur.

Geregistreerde dagtotalen, taakperioden en SG-lagen beschrijven de **volledige lokale kalenderdag**. Gedeeltelijke grensdatums en hun overlap met het venster worden expliciet benoemd, apart van ontbrekende meetdekking. Gegevens op een grensdag kunnen buiten het rollende venster liggen. Energie wordt niet naar rato geschat of kunstmatig afgeknipt. Dit is geen exact energieverbruik over alleen de gevraagde uren.

De bestaande dagpopup en zeven/dertig-dagenweergave blijven beschikbaar. Registratie sinds beta.70 blijft behouden; de update doet geen migratie, backfill, gegevensreset of wijziging van meetretentie.

## Grenzen en privacy

Totale elektrische warmtepompenergie vereist complete verse bevestigde niet-overlappende meters, met bijbehorende dekking. Een deelmeting, taaklabel of activiteit is geen totale energie- of compressorclaim. SG-aanvraag, contact en ontvangen status blijven afzonderlijk; geen causale extra SG-kWh, COP of besparingsclaim.

Panasonic blijft uitsluitend via de bestaande toegewezen SG-uitgang gekoppeld voor extra vraag. Lokaal gekozen percentages, koelwaarden, programma's, overige instellingen en zelfstandige native beveiligingen blijven behouden. Warmtepomp-zonnecredit geeft geen extra elektrische capaciteit of EV-overnamerecht.

Analyse-export is een bewuste lokale download voor een ingelogde HA-beheerder. Controleer het bestand vóór delen; publiceer geen huishoudelijke exports, bindings, back-ups of persoonlijke instellingen op GitHub. De read-only geschiedenis-API behoudt READ-controles op actuele en bewaarde bronnen. Interne ACL-/bindingidentiteiten worden niet als geschiedenisdata geëxporteerd.

## Rollback naar beta.70

Geef de eigen SG-aanvraag vrij, controleer contact/lokale afloop en stop beta.71. Herstel de gecontroleerde beta.70-code met behoud van dezelfde entry, aparte warmtepompgeschiedenis, overige opslag en userfiles. Beta.70 leest dezelfde geschiedenis; alleen de verbeterde wachtweergave en exportvensteruitleg vallen terug.

Voor exact herstel van de pre-upgradetoestand herstel je code én de volledige passende privéback-up. Dit kan daarna geregistreerde data vervangen; bewaar gewenste nieuwe historie eerst. Een ZIP alleen herstelt geen eerder tijdstip van alle data. Verwijder de entry niet en laat nooit twee runtimes tegelijk werken.

Terugkeer naar de oude directe beta.61-regeling vereist nog steeds de volledige back-up van vóór de beta.62-migratie. Zie [TESTRESULTATEN_BETA71.md](TESTRESULTATEN_BETA71.md) voor het actuele software-/publicatiebewijs en [ACTUELE_WERKING.md](ACTUELE_WERKING.md) voor de volledige werking.
