# SolarPilot 1.0.0-beta.44 — testresultaten

Datum: **2026-10-02**

> **Beta.44 gepubliceerd en geladen, met later aangetoonde ACK-beperking:** 1760 Python-tests, veertien browsercontroles, Validate, pakketten, HACS-installatie en geladen backend/kaart zijn bevestigd. De werkelijke adapter heet `aquarea` 1.0.61 en viel buiten de `panasonic_cc`-only ACK-herkenning. De vroege live `ha_state` is geen tienseconden-guardbewijs. SolarPilot staat opnieuw op Pauze voor de aparte beta.45-correctie.

## Definitieve lokale softwarecontrole

De volledige Python-regressiesuite behaalde op **2 oktober 2026** **1760 geslaagde tests in 11.68 s**. Alle **veertien browsercontroles** zijn groen, inclusief het nieuwe boileroverzicht met gerapporteerd doel, voorgesteld doel en beschermende pauze. De browserproeven gebruikten fictieve gegevens en registreerden **nul actuatoroproepen**.

Ook de overige lokale releasecontroles zijn uitgevoerd en groen:

- actuele-uitlegcontrole: hash `65b54c9797e55bb4`;
- overdrachtscontrole, repositoryvalidatie en publieke preflight;
- syntaxcontrole van beide meegeleverde frontend-JavaScriptbestanden;
- `git diff --check`, documentspiegels en versieconsistentie tussen manifest, backend, kaart, actuele uitleg en optiehulp.

Drie gecontroleerde cachemappen zijn opgeruimd. De definitieve lokale softwaregate omvat de aanvullende Panasonic-bevestiging, native taakbron en nieuwe boilerweergave; zij vervangt het eerdere testtotaal als actuele softwarestatus.

## Eerdere volledige run

Op **2 oktober 2026** zijn **1729 Python-tests** en **veertien browsercontroles** geslaagd op de toenmalige beta.44-bron. De browserproeven gebruikten fictieve gegevens en voerden geen fysieke opdrachten uit.

Daarna zijn aanvullende wijzigingen toegevoegd: uitsluiten van de onmiddellijke optimistische Panasonic-doelterugmelding als opdrachtbevestiging, gemeld versus voorgesteld doel op het boilerdashboard en een expliciete read-only bron voor de native ruimte-/tapwatertaak. Het eerdere totaal is uitsluitend historische testinformatie. De hierboven vastgelegde definitieve run omvat de aanvullende wijzigingen.

## Werkelijk uitgevoerde gerichte controles

- Wallbox-guard, huis-eerstregel, verbruikersprioriteit, runtime-uitleg en automatische waarderegistratie rond expliciet **geen laadvraag**: **105 geslaagd in 0.81 s**.
- Wallbox-sessiebeleid met **Zonne-auto · wacht op auto**, native Full Solar, migratie van exact oude standaardlijsten en behoud van eigen waardelijsten: **56 geslaagd in 0.67 s**.
- De testopdrachten gebruikten UTF-8, schreven geen bytecode en maakten geen pytest-cache.

Deze twee aantallen zijn afzonderlijke, mogelijk overlappende gerichte suites en worden niet tot één totaal opgeteld.

## Gericht afgedekt gedrag

- Geen EV-reservering bij verse geldige lage laadkracht plus expliciet `demand=false`, een niet-verbonden auto of een bekende inactieve status.
- Lage laadkracht alleen is onvoldoende; oude, ongeldige, onbekende en strijdige bronnen blijven fail-closed.
- Actief manueel laden, verse gemeten laadactiviteit en externe stopvoorwaarden behouden hun bestaande bescherming.
- De standaard zonnelaadlijst herkent **Zonne-auto · wacht op auto** alleen samen met native Full Solar.
- Exact oude standaardlijsten worden case-, volgorde- en eenvoudig scheidingsteken-onafhankelijk compatibel uitgebreid; een werkelijk aangepaste lijst niet.
- De Wallbox-routes blijven read-only en verkrijgen geen start-, stop-, modus-, fase- of laadstroomrecht.

## Aanvullende controles op de definitieve bron

De definitieve regressies en browsercontroles dekken ook af dat:

- alleen de geregistreerde Panasonic-adapter de minimale wachttijd voor latere doelwaarneming gebruikt; een onmiddellijk optimistisch echo-bericht mag geen eigendom of opdrachtbevestiging opleveren;
- timeout, mismatch, herstart en een bestaande beschermende pauze niet leiden tot blinde herhaalopdrachten of automatisch wissen van handmatige overname;
- de dashboarduitleg het gerapporteerde doel en een beschermende pauze vóór een voorgesteld doel toont;
- een expliciet gekoppelde native taakbron vers, geldig en eenduidig moet zijn, en ruimtebedrijf of tegenstrijdige informatie de extra zonnebuffer blokkeert;
- Panasonic AUTO met een inactieve klimaatactie zonder betrouwbare taakbron niet als bewezen afwezig ruimtebedrijf geldt;
- `PUMP` en `WATER` niet als HEAT/COOL- of compressor-/elektrisch meetbewijs worden gebruikt, en de nieuwe bron read-only blijft;
- een nieuwe koppeling niet automatisch wordt ontdekt of uit private installatie-identiteiten wordt samengesteld.

Deze softwarecontrole bewijst niet dat een latere HA-waarneming rechtstreekse LIVE cloud-/apparaatrapportage is of dat de nieuwe regels fysiek zijn uitgevoerd.

## Later aangetoonde beperking en resterende acceptatie

- Beta.45 corrigeert de exact gemiste `aquarea`-adapterherkenning en is afzonderlijk softwaregetest: 1773 Python-tests en veertien browsercontroles. Publicatie, installatie en geladen versie blijven open.
- Een passende latere doelrapportage na minstens tien seconden is nog niet live bewezen. De vroege beta.44-`ha_state` vóór deze grens was geen bewijs.
- fysieke observatie van de nieuwe verdelingsregels tijdens een natuurlijk passend venster.

## Bewezen live uitgangspunt

- HACS-installatie van **1.0.0-beta.44**, groene Home Assistant-configuratiecontrole, volledige herstart en geladen backend/vernieuwde kaart zijn afzonderlijk bevestigd op Core **2026.9.4**.
- De beta.44-herstart behield de bestaande beschermende pauze en scheidde gemeld en voorgesteld doel. De normale wizard en gerichte review zijn gecontroleerd. Een vroege `ha_state` vóór tien seconden toonde de exacte ACK-adaptermismatch; de installatie is voor beta.45-controle gepauzeerd. Persoonlijke temperaturen en bedientijden worden niet gepubliceerd.
- Er is geen AEG-START of STOP voor de update verstuurd. Een actuele inactieve status bewijst op zichzelf geen historische stopreden.
- Gerichte DHW-review en hervatten zijn gecontroleerd zonder fysieke proefstart; gerapporteerd doel en tankmeting zijn afzonderlijke gegevens.
- Een afwijking tussen gemeld en laatst bevestigd doel veroorzaakte een beschermende pauze. Een optimistische echo met oude cloudinformatie is een softwarematige mogelijkheid, geen bewezen historische oorzaak of bewuste gebruikerswijziging.
- De werkelijk geïnstalleerde Aquarea Smart Cloud 1.0.61 heeft domein `aquarea`; haar water-heater schrijft optimistisch en doet na tien seconden force-fetch. Beta.44 herkende alleen `panasonic_cc`. De gepatchte Aquarea-klimaatbron gebruikt `current_action` correct; de oudere panasonic_cc-AUTO-beperking wordt niet zonder bewijs aan haar toegeschreven.
- De native taakbron is gekoppeld: verse WATER met ruimtebusy false en later PUMP met ruimtebusy true. Dit bewijst de read-only taakguard, geen HEAT/COOL of compressorvermogen.
- De private Wallbox-helper onderscheidt inmiddels wachten op de auto van wachten op overschot; de native Wallbox-modus bleef Full Solar en werd niet door SolarPilot gewijzigd.
- Een verse native Wallbox-bron zonder laadvraag toonde dat een afgeleide sessietekst kon achterlopen. Beta.44 maakt vrijgave en uitleg onafhankelijk van zo'n aantoonbaar achterlopende tekst, zonder de versheids- of geldigheidseisen te versoepelen.
- De live vermogensanalyse liet zien dat een conservatieve DHW-reserve plus een geschatte lopende AEG-reserve vrijwel alle ruwe vrije injectie kon verbruiken. Dat motiveert de nieuwe zichtbare effectieve toewijzing en proportionele 60 °C-regel, maar bewijst niet dat beta.44 die regels al live heeft uitgevoerd.
- Een versleutelde volledige Home Assistant-back-up op de toegestane NAS is gereed bevestigd. Dit is geen uitgevoerde herstelproef.
- Het SolarPilot-logo is werkelijk zichtbaar bevestigd in het Home Assistant/HACS-updatevenster met een semantisch versienummer. De ondersteunde `entity_picture`-customisatie gebruikt de lokale Home Assistant-brandsproxy; daarna is uitsluitend de update-entiteit opnieuw opgevraagd. Er is geen HACS-codepatch of warmtepompcommando voor uitgevoerd.
- Opslaan en teruglezen van de afzonderlijke maandagdeadline zijn via de normale wizard getest, zonder APP-ticket/herarming/START of publicatie van een persoonlijk schema. Gemeten afwascyclusleren blijft terecht uit zonder exclusieve W-meter. Gerichte review is getest; de latere ACK-guard zelf is niet live bewezen.

## Geen fysieke claim

Beta.44 is gepubliceerd, door HACS geïnstalleerd en als backend/nieuwe kaart geladen bevestigd. Dat bewijst niet alle fysieke regelroutes. Er is geen fysieke AEG-START, Wallbox-opdracht, geforceerde 60 °C-opwarming, Powerful-activering of nieuwe laadcyclus uitgevoerd om de softwaretest te laten slagen. Een echte AEG-/60 °C-samenloop mag alleen in een natuurlijk passend overschotvenster worden geobserveerd; onbekende broninformatie blijft fail-closed. Een doelwaarneming na wachttijd bewijst niet dat de tank het doel heeft bereikt of dat het cloudbericht een rechtstreekse fysieke meting was.

## Releasepakketten

De [Validate-workflow 37022762657](https://github.com/Stevenva007/solarpilot-home-assistant/actions/runs/37022762657) is geslaagd. De [beta.44-prerelease](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.44) is gepubliceerd op **2 oktober 2026**, onder onveranderlijke tag `v1.0.0-beta.44` op commit `5bbfa16cbc9453a818fb825fe16c447792ed63a2`.

De gedownloade pakketten zijn werkelijk gecontroleerd: verifier `errors=[]`, **250 repositorybestanden** in de GitHub/HACS-ZIP en **98 integratiebestanden** in de lokale ZIP, met integratie-inhoud bytegelijk aan de tag. Manifestversie, padveiligheid en afwezigheid van private/cachebestanden zijn gecontroleerd. Werkelijk berekende SHA-256:

- `SolarPilot-v1.0.0-beta.44-GitHub-HACS.zip`: `bee258bb280656be6797a559fdfeb228a8b6850eb9f16a2a6f7f43a066e4c7d1`.
- `SolarPilot-v1.0.0-beta.44-local.zip`: `480aa06fe65555314c2ffee204db7ce441407077fa385048adfbd8da650ba60f`.

De bestaande tag, ZIP-assets en release-documentassets blijven onveranderd. Deze bijgewerkte documentatie registreert de latere controles en vervangt geen reeds gepubliceerd releasebestand.

Zie `BETA44_INSTELLEN.md` voor installatie, liveacceptatie en rollback.
