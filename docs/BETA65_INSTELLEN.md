# SolarPilot 1.0.0-beta.65 — instellen en controleren

Panasonic blijft zelfstandig eigenaar van warm water, ruimtebedrijf en alle fabrikantbeveiligingen. SolarPilot mag voor die warmtepomp uitsluitend het bestaande toegewezen SG-contact aanvragen/vrijgeven. Deze update herstelt de warmtepompweergave en toont de warmtepomp tussen de andere toestellen, met grafische activiteit en afzonderlijke SG-aanvraag, contactstand en ontvangen status. De bestaande SG-policy, het lokaal gekozen bereik en de meterroute blijven behouden. Zij schrijft geen Panasonic-doel, bedrijfsmodus, SG-percentage of heater-toestemming.

Volledige actuele werking: `ACTUELE_WERKING.md` en **SolarPilot → Uitleg** in Home Assistant. Werkelijk uitgevoerde software-/publicatiecontroles: `TESTRESULTATEN_BETA65.md`. Oudere verslagen zijn geen beta.65-testbewijs.

## 1. Upgrade met behoud van gegevens

Bouwbasis: de gecontroleerde gepubliceerde [beta.64](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.64), main-commit `103399152d45017c621ca9e6af528c090bb96dec`. Die tag en haar assets blijven onveranderd. Beta.65 behoudt de ondersteuning voor onveranderbare en geneste HA-opties uit beta.63.

1. Maak vóór de upgrade een volledige privé Home Assistant-back-up, inclusief configuratie, SolarPilot-opslag, modellen en lokale userfiles. Bewaar de passende beta.64-code voor rollback.
2. Controleer de huidige SG-aanvraag en contactstand; geef een eigen aanvraag vrij voordat je de programmabestanden vervangt. Onderbreek geen beschermde afwascyclus en maak geen nieuw APP-ticket als updateproef.
3. Update via HACS naar exact `1.0.0-beta.65` zodra de release gepubliceerd is en herstart Home Assistant volledig. Herlaad de browserpagina volledig of sluit de app volledig af en open haar opnieuw. Controleer de geladen backend- én kaartversie onderaan bij **Instellingen & controle**; beide moeten `1.0.0-beta.65` zijn. Een download of integratieherlading bewijst niet dat nieuwe browsercode geladen is.
4. Bij lokale installatie vervang je uitsluitend `custom_components/solar_pilot`. Bewaar `userfiles`, HA-configuratie en eigen opslag. Verwijder of herschep de bestaande integratie niet.
5. Controleer behouden andere toestellen, prioriteiten, APP-tickets, modellen en historie. Ongewijzigde geldige beta.64-SG-/profiel-/meter-/koelbevestigingen blijven behouden; deze codeupdate vraagt daarvoor geen nieuwe bevestiging. Nieuwe of werkelijk gewijzigde keuzes houden hun bestaande lokale bevestigingsvoorwaarden. Renderen en upgraden maken geen nieuwe fysieke toestemming.

Eerste installatie: voeg de repository in HACS toe als **Integration**, installeer, herstart HA en voeg SolarPilot toe onder **Instellingen → Apparaten & diensten**. Begin met betrouwbare P1/PV in **Alleen bekijken**. De frontend wordt automatisch geregistreerd; er is geen aparte Lovelace-resource, dashboard-YAML of www-kopie nodig.

## 2. Het juiste toepassingsbereik

Bij een ongewijzigde bestaande beta.64-installatie controleer je de behouden waarden. Je hoeft haar bewezen SG-ingebruikname niet over te doen wegens deze update. Voor een nieuwe installatie of werkelijk gewijzigde koppeling/profielkeuze gelden de onderstaande voorwaarden.

Open **Warmtepomp — Panasonic-regeling / SG-zonneboost** en de bestaande SG-instellingen.

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

De warmtepomp staat in **Overzicht** en **Toestellen** tussen de andere blokken. **Warmtepomp** toont de huidige Panasonic-/SG-uitleg, zonder foutmelding dat de verwijderde boiler- of klimaatregeling nog ontbreekt. Bekende meetwaarden en tankinformatie blijven zichtbaar; ontbrekende informatie verschijnt als onbekend.

De grafische activiteit verschijnt bij bevestigd bedrijf. De bedrijfsmelding onderscheidt actief, rust en onbekend; een gekozen modus is een afzonderlijke contextmelding. Een oude bron wordt niet als actuele activiteit weergegeven doordat een andere bron wel recent is.

| Bedrijfsbewijs | Wat de kaart ermee mag tonen |
| --- | --- |
| Gekoppelde echte compressorfrequentie, actueel en geldig | Positieve frequentie bevestigt bedrijf; gemeten nul bevestigt compressorstilstand. |
| Gekoppelde compressorfrequentie ontbreekt, is oud of ongeldig | Bedrijf blijft onbekend. Verse andere context vervangt een falende gekoppelde compressorbron niet. |
| Geen compressorbron gekoppeld; passende actuele native activiteitsmelding | Werkelijk gemelde heating/cooling kan bedrijf aangeven; gemelde idle/off kan rust aangeven. De kaart vermeldt deze andere bewijsbron. |
| Gemeten vermogen, WATER-/klepstand, gekozen HEAT/AUTO of tanktemperatuur | Meetwaarde of gekozen context; op zichzelf geen bewijs dat de warmtepomp actief produceert. |

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

Voor de ongewijzigde beta.64-upgrade volstaat de read-only weergavecontrole: controleer beide versievelden, behoud van je instellingen, de warmtepomp in Overzicht/Toestellen/Warmtepomp, gescheiden SG-lagen en de overeenkomst met de bestaande bronnen in HA. Een ontbrekende compressor- of ontvangen-SG-bron is geen fout: de kaart moet dan het juiste brononderscheid of onbekend tonen.

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
2. Stop beta.65 voordat een andere runtime terugkomt. Laat nooit twee versies hetzelfde contact beheren.
3. Herstel de gecontroleerde beta.64-code **en de passende volledige privéback-up van vóór deze upgrade**. Alleen de ZIP vormt geen volledige restore van instellingen, opgeslagen bewijs en modellen.
4. Herstart HA, herlaad de pagina volledig of sluit de app volledig af en open haar opnieuw, controleer backend- en kaartversie en kies de gewenste globale modus bewust. Bevestig oude SG-ingebruikname niet zonder haar eigen bewijs; behoud beschermde cycli.

Terugkeer naar de oude directe beta.61-regeling vereist nog steeds code én de volledige bijpassende back-up van vóór de beta.62-SG-migratie. De private herkomstregistratie is geen complete HA-restore en doet geen fysieke replay. Zie `TESTRESULTATEN_BETA65.md` voor software-/publicatiestatus; geladen HA en fysieke acceptatie blijven afzonderlijk bewijs.

## Primaire technische bronnen

- [Shelly Switch RPC: Set, status en timers](https://shelly-api-docs.shelly.cloud/gen2/ComponentsAndServices/Switch/).
- [Shelly 1 Gen4-documentatie](https://kb.shelly.cloud/knowledge-base/shelly-1-gen4).
- [Panasonic K-generatie, fabrikantbrochure](https://www.panasonicproclub.com/uploads/LT/catalogues/EU_20P_PRINT_AQ_K_GEN_23_LR.pdf).

Protocol- en fabrikantbeschrijvingen vervangen geen verificatie van de aanwezige firmware, contactmapping, meterdekking en lokale beveiligingen.
