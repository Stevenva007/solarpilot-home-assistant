# SolarPilot 1.0.0-beta.66 — instellen en controleren

Panasonic blijft zelfstandig eigenaar van warm water, ruimtebedrijf en alle fabrikantbeveiligingen. SolarPilot mag voor die warmtepomp uitsluitend het bestaande toegewezen SG-contact aanvragen/vrijgeven. Deze update toont automatisch afzonderlijk gemeten elektrische activiteit, de betekenis van beide voedingsmetingen en met passende verse native context een afgeleide warmwater-/ruimtefunctie. Bevestigde activiteit/rust, metingen, SG-lagen, beslisreden en Details blijven beschikbaar. Zonder bruikbaar bewijs verschijnt geen prominente Werking onbekend-indicator. De bestaande SG-policy, het lokaal gekozen bereik en de meterroute blijven behouden. Zij schrijft geen Panasonic-doel, bedrijfsmodus, SG-percentage of heater-toestemming.

Volledige actuele werking: `ACTUELE_WERKING.md` en **SolarPilot → Uitleg** in Home Assistant. Werkelijk uitgevoerde software-/publicatiecontroles: `TESTRESULTATEN_BETA66.md`. Oudere verslagen zijn geen beta.66-testbewijs.

## 1. Upgrade met behoud van gegevens

Bouwbasis: de gecontroleerde gepubliceerde [beta.65](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.65), main-commit `e5bff1f81a1ba9e50da060fc961bbe7722d7da63`. Die tag en haar assets blijven onveranderd. Beta.66 behoudt de ondersteuning voor onveranderbare en geneste HA-opties uit beta.63.

1. Maak vóór de upgrade een volledige privé Home Assistant-back-up, inclusief configuratie, SolarPilot-opslag, modellen en lokale userfiles. Bewaar de passende beta.65-code voor rollback.
2. Controleer de huidige SG-aanvraag en contactstand; geef een eigen aanvraag vrij voordat je de programmabestanden vervangt. Onderbreek geen beschermde afwascyclus en maak geen nieuw APP-ticket als updateproef.
3. Update via HACS naar exact `1.0.0-beta.66` zodra de release gepubliceerd is en herstart Home Assistant volledig. Herlaad de browserpagina volledig of sluit de app volledig af en open haar opnieuw. Controleer de geladen backend- én kaartversie onderaan bij **Instellingen & controle**; beide moeten `1.0.0-beta.66` zijn. Een download of integratieherlading bewijst niet dat nieuwe browsercode geladen is.
4. Bij lokale installatie vervang je uitsluitend `custom_components/solar_pilot`. Bewaar `userfiles`, HA-configuratie en eigen opslag. Verwijder of herschep de bestaande integratie niet.
5. Controleer behouden andere toestellen, prioriteiten, APP-tickets, modellen en historie. Ongewijzigde geldige beta.65-SG-/profiel-/meter-/koelbevestigingen blijven behouden; deze codeupdate vraagt daarvoor geen nieuwe bevestiging. De nieuwe weergave gebruikt bestaande bronkoppelingen en standaard 200 W; nieuwe instellingen of entiteiten invullen is niet nodig. Voedingsrollen en weergaveverfijning blijven optioneel. Nieuwe of werkelijk gewijzigde keuzes houden hun bestaande lokale bevestigingsvoorwaarden. Renderen en upgraden maken geen nieuwe fysieke toestemming.

Eerste installatie: voeg de repository in HACS toe als **Integration**, installeer, herstart HA en voeg SolarPilot toe onder **Instellingen → Apparaten & diensten**. Begin met betrouwbare P1/PV in **Alleen bekijken**. De frontend wordt automatisch geregistreerd; er is geen aparte Lovelace-resource, dashboard-YAML of www-kopie nodig.

## 2. Het juiste toepassingsbereik

Bij een ongewijzigde bestaande beta.65-installatie controleer je de behouden waarden. Je hoeft haar bewezen SG-ingebruikname niet over te doen wegens deze update. Voor een nieuwe installatie of werkelijk gewijzigde koppeling/profielkeuze gelden de onderstaande voorwaarden.

Voor de bestaande installatie is het openen van een configuratieformulier niet nodig voor deze nieuwe weergave. De onderstaande oorspronkelijke SG-instellingen zijn alleen relevant voor een nieuwe ingebruikname of werkelijk gewijzigde koppeling/profielkeuze.

| Instelling | Betekenis en lokale controle |
| --- | --- |
| SG-zonneboost warmtepomp | Eén bestaande toegewezen Shelly-uitgang, met echte contactmapping, één eigenaar en bewezen lokale aflooptimer. |
| Uitsluitend tapwater | Bewust gekozen bereik met behoud van de tankgebonden anti-herhaalregel. Het fysieke Panasonic-profiel moet dat bereik werkelijk ondersteunen. |
| Algemene SG-boost volgens Panasonic-bedrijf | Eén aanvraag voor extra opname volgens actuele native modus en het lokaal ingestelde SG-profiel: tapwater, verwarmen of koelen. Geen gelijktijdige productieopdracht en geen tweede controller. |
| Toepassingsbereik lokaal bevestigd | Afzonderlijke bewuste bevestiging van de gekozen werking. Een profielwijziging neemt die toestemming niet automatisch over. |
| Bestaande condens-/dauwpuntbeveiliging voor extra koeling bevestigd | Losse beveiligingscontrole. Een gewenst algemeen profiel alleen bewijst geen veilige extra koeling. |

Behoud gewenste lokale Panasonic-SG-waarden. SolarPilot wijzigt ze niet, zet extra koeling niet stil op nul en maakt van SG-percentages geen universele temperatuur- of vermogensformule. Panasonic blijft eigenaar van thermostaten, zones, stooklijnen, omschakeling, compressor, pompen, kleppen, ontdooien, normaal comfort, elektrische ondersteuning en sterilisatie. Deze update vraagt geen tweede Shelly, extra hardware, Swiss mode, DIP-wijziging of externe compressorfunctie.

Voor het algemene profiel zonder bevestigde bestaande condensbeveiliging moet verse native context koeling betrouwbaar uitsluiten. Werkelijke koeling, AUTO of onbekende context kan die extra SG-aanvraag blokkeren. De normale Panasonic-koeling blijft onaangeroerd. Een vaste minimumtemperatuur of alleen een luchtvochtigheidssensor vormt geen volledige beveiligingsbevestiging. Laat een installateur bestaande beveiliging en contactmapping beoordelen wanneer betrouwbare lokale documentatie ontbreekt; open geen elektrische apparatuur voor deze acceptatieproef.

## 3. Eén totaalmeter of twee afzonderlijke voedingen

Selecteer lokale entiteiten via de bestaande HA-selectors; een naam is geen bewijs van elektrische dekking.

| Route of bron | Gebruik |
| --- | --- |
| Bestaande single-meterbron | Behouden bij upgrade. Kies het echte dekkingslabel: totaal, voeding 1, voeding 2 of onbevestigd. Een deelmeter is geen totaal. |
| Voeding 1 en voeding 2 | Twee echte afzonderlijke W/kW-bronnen die samen de volledige warmtepomp dekken. Bevestig lokaal dat de dekking volledig en niet-overlappend is. |
| Compressorfrequentie | Optionele echte actuele Hz-bron. Een handmatig getoond getal wordt geen sensor. |
| Ontvangen SG-status | Optionele passende native bron die daadwerkelijk de ontvangen SG-status meldt. |
| Tank, native tankdoel, activiteit en zones | Uitsluitend uitlezen. Controleer de betekenis en actualiteit van de echte bronnen. |

Bij twee complete actuele gevalideerde deelmeters is totaal = voeding 1 + voeding 2. Gelijke bronnen, totaal plus deelmeter en bekende inspecteerbare template-overlap worden geweigerd. Verborgen overlap blijft een lokale controle. Een reeds inbegrepen heater wordt nooit nogmaals opgeteld. Koppel geen P1/PV, gedeelde andere toestelmeter, kWh-teller of interne Shelly-temperatuur als exclusief warmtepompvermogen.

Een actuele 0 W is gemeten nul. Is één deelmeter ontbrekend, oud, negatief of anders ongeldig, dan blijft het totaal onvolledig/onbekend en de bekende deelwaarde zichtbaar. Bij een bevestigde Panasonic-installatie met een hoofdvoeding en apart elektrisch ondersteuningscircuit omvat het hoofdcircuit de compressor en, afhankelijk van het model, ook regeling/pompen. De tweede voeding hoort dan bij de bedoelde booster-/back-upverwarming. Bevestig de werkelijke lokale dekking; voeding 1 is geen zuivere compressormeter en voeding 2 mag alleen bij bewezen dekking als heaterverbruik worden geïnterpreteerd. SG is een apart contactsignaal, geen vermogensvoeding: compressorbedrijf terwijl de heatermeter 0 W meet, is mogelijk en bewijst geen SG-effect. Eén gunstig werkpunt verlaagt geen elektrische marges en is geen gegarandeerd maximum.

## 4. Begrenste aanvraag en nieuwe aanleiding

Bestaande defaults blijven: startdrempel **3000 W**, aparte raming **3200 W**, startvertraging **120 s**, stopvertraging **60 s**, rust **900 s**, sessie maximaal **3600 s**, kleine-importbuffer **300 W**. Dit zijn voorzichtige beleidswaarden, geen bewezen toestelvermogen. De lokale toestemming blijft **300 s**, met vernieuwing iedere **60 s** en steeds begrensd door de resterende sessieduur.

Vernieuwing verlengt dezelfde AAN-toestand, zonder fysieke UIT/AAN-cyclus. Netafname boven de buffer gedurende de stopvertraging geeft alleen de eigen SG-aanvraag vrij; tijdens die tekortcontrole wordt geen nieuwe toestemming geplaatst. P1/PV, fase-/netgrenzen, actuele bronnen en voorrang blijven beslissend. Native warmtepompverbruik kan na SG-UIT doorgaan en is niet ineens vrijgemaakt flexvermogen.

De maximale sessieduur betekent **sessielimiet**, geen volle tank. Onbekende reactie betekent geen werkelijk voltooide cyclus. De algemene beleidswachtstand onderscheidt sessielimiet, native voltooid, geen aangetoonde opname en onbekende reactie. Zij blijft ook na onderbreking, lokale timerafloop, bronverlies, netvrijgave of reload gelden. Handmatige overname, transportonzekerheid en veiligheidsblokkeringen blijven afzonderlijk.

- **Uitsluitend tapwater:** na rust kan dezelfde tankbron minstens 2 °C afkoeling ten opzichte van de verse eindmeting aantonen, bevestigd met minstens twee nieuwe echte rapporten over vijf minuten. Zonder bruikbaar eindbewijs, na bronwisseling of bij onbetrouwbare data blijft deze wachtstand staan. Na reload begint de vijfminutenbevestiging opnieuw.
- **Algemeen profiel:** een warme, onveranderde of ontbrekende tank blokkeert niet zelfstandig ieder volgend algemeen gebruik. Na iedere beëindigde of onderbroken algemene sessie zijn na rust minstens twee nieuwe echte rapporten over vijf minuten nodig voor een gewijzigde betrouwbare relevante native context, of een nieuwe relevante actieve episode na eveneens bevestigde rust. Een nieuwe zonneperiode kan ook gelden: eerst minstens vijf minuten restoverschot hoogstens de kleine-importbuffer en vervolgens minstens vijf minuten vanaf de startdrempel, telkens met minstens twee nieuwe rapporten.
- **Iedere nieuwe sessie:** de volledige startvertraging en actuele zon-, bron-, elektrische-, koel- en voorrangsvoorwaarden gelden opnieuw. Vastgelegde bewijslagen blijven bij reload bewaard; lopende vensters vragen nieuwe rapporten. Dezelfde samples, constante zon, rusttijd of herstart alleen geeft geen eindeloze hertriggerlus.

Bij bevestigde omschakeling van een oude tankgebonden hold naar algemeen bereik blijft de herkomst privé bewaard. Nieuw betrouwbaar relevant native bewijs of een aantoonbaar nieuwe zonneperiode is nodig; omschakelen alleen start niets. Echte handmatige, communicatie- en veiligheidsblokkeringen verdwijnen hierdoor niet. Een gewijzigde native uitleesbron bewijst geen nieuwe vraag: de eerste verse rapportage stelt alleen een referentie vast. Daarna blijft werkelijk gewijzigde context of een nieuwe zonneperiode nodig. Bij relevante native bronwijziging moet ook de koelbeveiligingsbevestiging opnieuw worden beoordeeld. **Automatisering hervatten** vraagt een nieuwe actuele beoordeling en is geen gedwongen AAN.

## 5. Wat je op de warmtepompkaart ziet

De warmtepomp staat in **Overzicht** en **Toestellen** tussen de andere blokken. **Warmtepomp** toont de huidige Panasonic-/SG-uitleg, zonder foutmelding dat de verwijderde boiler- of klimaatregeling nog ontbreekt. Bekende meetwaarden en tankinformatie blijven zichtbaar; ontbrekende meet-/SG-informatie behoudt haar eigen onbekend-label. Alleen de onbewezen bedrijfsindicatie wordt weggelaten.

De kaart werkt automatisch met bestaande bronkoppelingen en standaard 200 W; een nieuwe sensor kiezen of instelling invullen is niet nodig. Zij gebruikt twee afzonderlijke bewijssoorten: daadwerkelijk gemelde native/compressoractiviteit en uit de meter(s) afgeleide elektrische activiteit. Gemeten watts bewijzen niet apart dat de compressor draait of hoeveel warmte wordt geproduceerd. Afgeleide activiteit krijgt de uitleg **Afgeleid uit gemeten verbruik; compressorbedrijf/warmteproductie niet afzonderlijk gemeten.**.

| Meetbewijs en actuele context | Weergave en betekenis |
| --- | --- |
| Compleet actueel totaal vanaf de ingestelde weergavegrens | **Warmtepomp werkt**: actief elektrisch verbruik, herkenbaar als afgeleid. |
| Compleet actueel totaal gelijk aan 0 W | **Geen elektrisch verbruik**. Geen claim over een nog warme tank of eerdere productie. |
| Compleet actueel positief totaal onder de weergavegrens | **Basisverbruik**. Geen aparte compressor-/warmteproductieclaim. |
| Compleet actief totaal plus expliciete verse tankactiviteit of geverifieerde verse Aquarea-opwarmmelding | **Sanitair water opwarmen** als afgeleide functie. De echte tankactie of HEATING_WATER uit de recente poll van het exact gekoppelde apparaat wordt automatisch met de meting gecombineerd. |
| Alleen de gekozen tankstand heating, zonder echte actuele actie | Algemene gemeten activiteit; de gekozen stand is context en bewijst geen sanitairwateropwarming. |
| Compleet actief totaal plus passende verse native ruimteactie of exact gebonden recente Aquarea-poll | **Ruimte verwarmen** of **Ruimte koelen** als afgeleide functie. De bestaande warmwaterbinding kan automatisch HEATING (2), COOLING (3) en HEATING_WATER (4) leveren; geen extra instelling of entiteit nodig. |
| Complete actuele actieve meting, maar oude/ontbrekende/conflicterende native context | Algemeen actief verbruik blijft zichtbaar; geen afgeleide warmwater-/ruimtefunctie. |
| Onvolledige splitmeting met een bekende actuele voeding vanaf de grens | **Actief verbruik op voeding 1/2**. Geen compleet totaal, totale inactiviteit of afgeleide warmwater-/ruimtefunctie. Een bekende nul op de andere/ene voeding bewijst geen totale rust. |
| Verse geldige compressorfrequentie | Afzonderlijk werkelijk compressorbewijs. Ventilatorrotatie vereist dit bewijs; watts of gekozen programma geven geen rotatiebewijs. |
| Geen bruikbaar bedrijfs- of verbruiksbewijs | Geen prominente Werking onbekend-badge of apart onbekend-bedrijfsblok. Bekende meet-/SG-informatie, beslisreden en Details blijven beschikbaar; technische onzekerheid blijft behouden. |

De automatische functie-afleiding via de native binding vereist een complete verse actieve vermogensmeting, een verse beschikbare gebonden warmwaterentiteit en geverifieerd actueel pollbewijs. Tegenstrijdige werkelijke native acties geven geen functieclaim. Een gemeten actieve kaart houdt haar verbruikslabel ook bij native rust of 0 Hz; de compressor-/rustwaarheid blijft zichtbaar in de uitleg en de ventilator draait dan niet.

Een gekoppelde maar oude of ongeldige compressorbron blijft technisch onbekend; verse vermogensmeting vervangt haar niet als compressorbewijs. Alleen zonder gekoppelde compressorbron kan passende verse native activiteit afzonderlijk bedrijf/rust bevestigen. Programma, WATER-/klepstand of temperatuur alleen bewijst geen productie. Blauwe grafische activiteit mag herkenbare afgeleide elektrische activiteit tonen; dit onderscheidt de kaart van een werkelijk draaiende compressorventilator.

De volgende opties zijn uitsluitend voor wie zelf wil verfijnen; ze zijn geen stap om de update te gebruiken.

| Optionele weergaveoptie | Betekenis en grens |
| --- | --- |
| **Actief verbruik vanaf (W) — alleen weergave** | Standaard **200 W**, instelbaar van **10 tot 2000 W**. Bepaalt alleen het meetactiviteitslabel, niet de SG-start-/stopdrempel, timer, koelvrijgave of toestemming. |
| **Functie voeding 1/2 — alleen weergave**: **Functie nog niet bevestigd** | Neutraal **Voeding 1/2**. Er wordt geen compressor-/heaterrol uit de naam of het nummer gegokt. |
| Dezelfde functieoptie: **Hoofdvoeding: warmtepomp, regeling en pompen** | Uitleg voor de bevestigde voeding met compressor en mogelijk regeling/pompen. Geen zuivere compressormeter. |
| Dezelfde functieoptie: **Elektrische ondersteuning** | Uitleg voor het opgenomen vermogen van de bevestigde elektrische backup-/ondersteuningsvoeding. Geen nieuwe native heaterstatus of bediening. |

Meterdekking en onderdeelrol zijn verschillende bevestigingen: twee volledig niet-overlappende metingen bewijzen niet automatisch welke voeding compressor/regeling of elektrische ondersteuning dekt. Zonder rolkeuze werkt de activiteitweergave met neutrale Voeding 1/2-labels. Wie later zelf een rol kiest, doet dat op basis van de werkelijke aansluiting, niet alleen een naam. De nieuwe opties gebruiken bestaande gekoppelde bronnen; er is geen extra leesentiteit nodig en bestaande geldige SG-bevestigingen blijven behouden.

De drie SG-lagen krijgen afzonderlijke aanduidingen. **SG aangevraagd** zegt wat SolarPilot vraagt. **SG-contact AAN** zegt wat de Shelly terugmeldt. **SG ontvangen** kan alleen een echte passende actuele bron op de warmtepomp bevestigen. Zij mogen verschillend zijn; bijvoorbeeld contact AAN met ontvangen status onbekend. De lokale timer en de bronactualiteit blijven afzonderlijk zichtbaar in Details.

| Bewijslaag | Betekenis |
| --- | --- |
| SolarPilot-aanvraag, eigenaar en reden | Wat de huidige policy toestaat en wie de aanvraag beheert. |
| Shelly AAN/UIT/onbekend en resterende toestemming | Door Shelly gemelde uitgang en afzonderlijk bevestigde lokale timer. Een ACK bewijst geen fysiek gesloten contact. |
| Compressorstatus/-frequentie en native context | Werkelijk beschikbare actuele bedrijfsinformatie volgens het bronbewijs hierboven. WATER of een klepstand is geen compressorbewijs. |
| Metingen per voeding en totaal | De bekende bronwaarden en dekking. Onvolledig blijft onvolledig. |
| Ontvangen SG-status | Expliciet actief/inactief alleen bevestigd met een passende echte bron; anders onbekend. Numerieke standen worden niet gegokt. Ontvangen stand en compressorbedrijf bewijzen geen causaal extra SG-opname. |

Een gelijkblijvend normaal app-tankdoel bewijst geen mislukte SG-aanvraag. Na twintig minuten nieuwe actuele lage vermogensrapporten zonder bevestigde compressoractiviteit verschijnt eenmaal de diagnose “SG-contact actief; extra warmteopname nog niet aangetoond” in Details en op de tijdlijn. Dit is geen fout en geen vermogensvrijgave. Langdurig laag vermogen mag aanleiding zijn om waarnemingen te controleren; het is geen opdracht voor periodieke OFF/ON-pulsen, een hertrigger na twintig minuten, reboot, Force-opdracht of heaterwrite. Een buiten SolarPilot handmatig ingeschakeld contact heeft niet automatisch een bewezen lokale timer.

De eerdere stilstand en het later zichtbare compressorbedrijf hebben **geen vastgestelde oorzaak**. Nog te verduidelijken is of alleen het SG-contact of ook Panasonic is uit-/aangezet en of modus, menu of native vraag tussendoor veranderde. Verschillende meetmomenten zonder passende logs bewijzen geen contactflankprobleem, SolarPilot-fout of compressorstart door SG. Publiceer geen ruwe thuismetingen om die vraag te beantwoorden.

## 6. Korte lokale controle

Voor de ongewijzigde beta.65-upgrade volstaat de read-only weergavecontrole: controleer beide versievelden, behoud van je instellingen, de warmtepomp in Overzicht/Toestellen/Warmtepomp, gescheiden SG-lagen en de overeenkomst met de bestaande bronnen in HA. Vergelijk beide voedingswaarden met HA. Controleer complete actieve/nul/lage meting met de automatische standaard van 200 W en neutrale voedingsrollen; daarvoor hoef je geen configuratieformulier te openen. Een complete actieve meting mag met expliciete verse tankactie of een verse exact gebonden Aquarea-opwarmmelding Sanitair water opwarmen afleiden. Alleen een gekozen tankstand heating mag dat niet. Passende verse ruimtecontext kan Ruimte verwarmen/koelen afleiden; oude/conflicterende context mag dat niet. Een deelmeting blijft activiteit op de bekende voeding. Controleer herkenbare afleidingsuitleg, ventilatorrotatie uitsluitend bij bevestigde Hz, en behoud van metingen, SG-lagen, beslisreden en Details. Zonder bruikbaar bewijs geen prominente Werking onbekend-indicator. Een ontvangen-SG-bron heeft haar eigen betekenis: zonder passende actuele bron blijft ontvangen status onbekend.

Het zijbalkpaneel laadt de kaart van deze release. Een al geopende gewone Lovelace-kaart kan echter haar eerdere weergavecode blijven gebruiken tot een volledige browser/app-herlading. Een oude kaart kon de nieuwe backendversie tonen zonder zelf bijgewerkt te zijn en kan de nieuwe versieverschilwaarschuwing nog niet tonen. Herlaad de pagina volledig of sluit de app volledig af en open haar opnieuw; controleer daarna beide versievelden. Voeg geen extra Lovelace-resource of www-kopie toe om dit te herstellen.

De onderstaande oorspronkelijke ingebruiknamecontrole is bedoeld voor een nieuwe SG-installatie of daadwerkelijk gewijzigde relevante koppeling. Een ongewijzigde codeupgrade vraagt geen extra SG-proef.

De softwareproeven hebben geen fysieke apparaten bediend. Deze lokale controle verandert geen bedrading, DIP-schakelaars, heater-toestemming, Panasonic-doelen of bedrijfsmodus. Alleen de read-only punten kunnen zonder fysieke proefdraaiautorisatie worden uitgevoerd. Een tijdelijke SG-/timerproef en natuurlijke automatische sessie worden uitsluitend na expliciete toestemming uitgevoerd.

1. Controleer versie, behouden gegevens en **Alleen bekijken**. Verifieer de gewenste native Panasonic-basis en inspecteer bekende externe writers; schakel automatiseringen niet blind op naam uit. Zonder live inzage is er geen bewezen conflictvrijheid.
2. Controleer geselecteerd toepassingsbereik en passende lokale bevestiging. Bevestig condens-/dauwpuntbeveiliging afzonderlijk wanneer extra koeling mogelijk is.
3. Controleer met bestaande documentatie en gesloten apparatuur wat de meter(s) dekken. Vergelijk actuele waarden en eenheden in HA en de kaart; bekende nul en ontbrekende waarde moeten verschillend verschijnen. Verifieer optionele compressor-/SG-bronsemantiek.
4. Na expliciete toestemming: vraag via de bestaande ondersteunde Shelly-route kort en begrensd SG aan. Controleer echte `output`, `timer_started_at` en `timer_duration`. `was_on` is alleen de vorige uitgangsstand. Controleer de ontvangen SG-trap op Panasonic indien beschikbaar; een normaal gelijkblijvend tankdoel is geen mislukking.
5. Controleer dat een tijdige timervernieuwing dezelfde uitgang AAN houdt en de deadline opschuift, zonder UIT/AAN-cyclus. Laat daarna vernieuwing uitblijven en controleer daadwerkelijk lokale afloop, ook zonder HA-vernieuwing. Power-on UIT alleen bewijst geen wifi-terugval.
6. Geef de aanvraag vrij en bevestig normale native werking. Leg alleen daadwerkelijk waargenomen aansluiting, reactie en lokale terugval als geslaagd vast. Bij ontbrekend bewijs blijft automatische SG uit; gezonde andere toestellen houden hun eigen voorwaarden.
7. Na expliciete toestemming en complete ingebruikname: observeer een natuurlijke stabiele zonnestart. Controleer begrenzing, echte wachtreden en gescheiden bewijs op de kaart. Forceer geen warmte-/koelvraag om opname te bewijzen.

De bestaande native HA Shelly-route gebruikt `Switch.Set(on=true, toggle_after=...)` en leest uitgang/timer terug. Geen tweede transport, cloudfallback of nieuwe generieke servicewriter. Bij onbereikbaarheid blijft contactstand onbekend; er komt geen fictieve UIT-bevestiging. Een lokale timer vervangt geen elektrische beveiliging.

## 7. Andere toestellen en privacy

Wallbox blijft read-only. AEG behoudt één START per belading, APP-ticket, kalenderdag/deadlines en AirDry-bescherming. Ontvochtiger-minimumtijden, batterijen, kosten, historie, leren, eigen opslaglimieten, Recorder-begrenzing en stabiele pop-ups blijven behouden. Geen ongevraagde herprioritering of algemene gegevensreset.

Bewaar bindings, netwerkgegevens, tokens, ruwe exports en back-ups privé. De migratie bewaart relevante herkomst read-only; geen oude aanvraag replayen. Gerichte echte problemen staan bij **Home Assistant → Meldingen → SolarPilot: controle nodig**. Gewone rust, zonwacht of beleidswachtstand bewijst geen fout en hoort geen meldingenspam te geven.

## 8. Rollback

1. Trek de eigen SG-aanvraag in, controleer de contactstand/lokale afloop en voorkom nieuwe vernieuwing.
2. Stop beta.66 voordat een andere runtime terugkomt. De nieuwe uitleesopties veranderen geen SG-regel; rollback herstelt de beta.65-weergave en de passende opgeslagen configuratie. Laat nooit twee versies hetzelfde contact beheren.
3. Herstel de gecontroleerde beta.65-code **en de passende volledige privéback-up van vóór deze upgrade**. Alleen de ZIP vormt geen volledige restore van instellingen, opgeslagen bewijs en modellen.
4. Herstart HA, herlaad de pagina volledig of sluit de app volledig af en open haar opnieuw, controleer backend- en kaartversie en kies de gewenste globale modus bewust. Bevestig oude SG-ingebruikname niet zonder haar eigen bewijs; behoud beschermde cycli.

Terugkeer naar de oude directe beta.61-regeling vereist nog steeds code én de volledige bijpassende back-up van vóór de beta.62-SG-migratie. De private herkomstregistratie is geen complete HA-restore en doet geen fysieke replay. Zie `TESTRESULTATEN_BETA66.md` voor software-/publicatiestatus; geladen HA en fysieke acceptatie blijven afzonderlijk bewijs.

## Primaire technische bronnen

- [Shelly Switch RPC: Set, status en timers](https://shelly-api-docs.shelly.cloud/gen2/ComponentsAndServices/Switch/).
- [Shelly 1 Gen4-documentatie](https://kb.shelly.cloud/knowledge-base/shelly-1-gen4).
- [Panasonic K-generatie, fabrikantbrochure](https://www.panasonicproclub.com/uploads/LT/catalogues/EU_20P_PRINT_AQ_K_GEN_23_LR.pdf).

Protocol- en fabrikantbeschrijvingen vervangen geen verificatie van de aanwezige firmware, contactmapping, meterdekking en lokale beveiligingen.
