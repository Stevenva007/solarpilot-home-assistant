# SolarPilot 1.0.0-beta.64 — instellen en controleren

Panasonic blijft zelfstandig eigenaar van warm water, ruimtebedrijf en alle fabrikantbeveiligingen. SolarPilot mag voor die warmtepomp uitsluitend het bestaande toegewezen SG-contact aanvragen/vrijgeven. Deze update voegt een expliciet lokaal toepassingsbereik, betrouwbare observatie en een eenvoudige tweemeterroute toe. Zij schrijft geen Panasonic-doel, bedrijfsmodus, SG-percentage of heater-toestemming.

Volledige actuele werking: `ACTUELE_WERKING.md` en **SolarPilot → Uitleg** in Home Assistant. Werkelijk uitgevoerde software-/publicatiecontroles: `TESTRESULTATEN_BETA64.md`. Oudere verslagen zijn geen beta.64-testbewijs.

## 1. Upgrade met behoud van gegevens

Bouwbasis: de gecontroleerde gepubliceerde [beta.63](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.63), commit `977f2fe1eb19c4944be7ee7125b911a473ef7c29`. Die tag en haar assets blijven onveranderd. Beta.64 behoudt de ondersteuning voor onveranderbare en geneste HA-opties uit beta.63.

1. Maak vóór de upgrade een volledige privé Home Assistant-back-up, inclusief configuratie, SolarPilot-opslag, modellen en lokale userfiles. Bewaar de passende beta.63-code voor rollback.
2. Controleer de huidige SG-aanvraag en contactstand; geef een eigen aanvraag vrij voordat je de programmabestanden vervangt. Onderbreek geen beschermde afwascyclus en maak geen nieuw APP-ticket als updateproef.
3. Update via HACS naar exact `1.0.0-beta.64` zodra de release gepubliceerd is en herstart Home Assistant volledig. Heropen browser/app en controleer de geladen backend- én kaartversie afzonderlijk. Een download bewijst niet dat nieuwe code geladen is.
4. Bij lokale installatie vervang je uitsluitend `custom_components/solar_pilot`. Bewaar `userfiles`, HA-configuratie en eigen opslag. Verwijder of herschep de bestaande integratie niet.
5. Controleer behouden andere toestellen, prioriteiten, APP-tickets, modellen en historie. Een upgrade bevestigt geen nieuw algemeen SG-profiel, geen splitmeting en geen koelbeveiliging. Zij schrijft geen nieuwe fysieke migratieopdracht.

Eerste installatie: voeg de repository in HACS toe als **Integration**, installeer, herstart HA en voeg SolarPilot toe onder **Instellingen → Apparaten & diensten**. Begin met betrouwbare P1/PV in **Alleen bekijken**. De frontend wordt automatisch geregistreerd; er is geen aparte Lovelace-resource, dashboard-YAML of www-kopie nodig.

## 2. Het juiste toepassingsbereik

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

## 5. Wat de compacte kaart werkelijk bewijst

| Bewijslaag | Betekenis |
| --- | --- |
| SolarPilot-aanvraag, eigenaar en reden | Wat de huidige policy toestaat en wie de aanvraag beheert. |
| Shelly AAN/UIT/onbekend en resterende toestemming | Door Shelly gemelde uitgang en afzonderlijk bevestigde lokale timer. Een ACK bewijst geen fysiek gesloten contact. |
| Compressorstatus/-frequentie en native context | Werkelijk beschikbare actuele bedrijfsinformatie. WATER of een klepstand is geen compressorbewijs. |
| Metingen per voeding en totaal | De bekende bronwaarden en dekking. Onvolledig blijft onvolledig. |
| Ontvangen SG-status | Expliciet actief/inactief alleen bevestigd met een passende echte bron; anders onbekend. Numerieke standen worden niet gegokt. Ontvangen stand en compressorbedrijf bewijzen geen causaal extra SG-opname. |

Een gelijkblijvend normaal app-tankdoel bewijst geen mislukte SG-aanvraag. Na twintig minuten nieuwe actuele lage vermogensrapporten zonder bevestigde compressoractiviteit verschijnt eenmaal de diagnose “SG-contact actief; extra warmteopname nog niet aangetoond” in Details en op de tijdlijn. Dit is geen fout en geen vermogensvrijgave. Langdurig laag vermogen mag aanleiding zijn om waarnemingen te controleren; het is geen opdracht voor periodieke OFF/ON-pulsen, een hertrigger na twintig minuten, reboot, Force-opdracht of heaterwrite. Een buiten SolarPilot handmatig ingeschakeld contact heeft niet automatisch een bewezen lokale timer.

De eerdere stilstand en het later zichtbare compressorbedrijf hebben **geen vastgestelde oorzaak**. Nog te verduidelijken is of alleen het SG-contact of ook Panasonic is uit-/aangezet en of modus, menu of native vraag tussendoor veranderde. Verschillende meetmomenten zonder passende logs bewijzen geen contactflankprobleem, SolarPilot-fout of compressorstart door SG. Publiceer geen ruwe thuismetingen om die vraag te beantwoorden.

## 6. Korte lokale acceptatie, zonder geopende apparatuur

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
2. Stop beta.64 voordat een andere runtime terugkomt. Laat nooit twee versies hetzelfde contact beheren.
3. Herstel de gecontroleerde beta.63-code **en de passende volledige privéback-up van vóór deze upgrade**. Alleen de ZIP herstelt nieuwe schema-/bewijsvelden niet exact.
4. Herstart HA, heropen browser/app, controleer backend- en kaartversie en kies de gewenste globale modus bewust. Bevestig oude SG-ingebruikname niet zonder haar eigen bewijs; behoud beschermde cycli.

Terugkeer naar de oude directe beta.61-regeling vereist nog steeds code én de volledige bijpassende back-up van vóór de beta.62-SG-migratie. De private herkomstregistratie is geen complete HA-restore en doet geen fysieke replay. Zie `TESTRESULTATEN_BETA64.md` voor software-/publicatiestatus; geladen HA en fysieke acceptatie blijven afzonderlijk bewijs.

## Primaire technische bronnen

- [Shelly Switch RPC: Set, status en timers](https://shelly-api-docs.shelly.cloud/gen2/ComponentsAndServices/Switch/).
- [Shelly 1 Gen4-documentatie](https://kb.shelly.cloud/knowledge-base/shelly-1-gen4).
- [Panasonic K-generatie, fabrikantbrochure](https://www.panasonicproclub.com/uploads/LT/catalogues/EU_20P_PRINT_AQ_K_GEN_23_LR.pdf).

Protocol- en fabrikantbeschrijvingen vervangen geen verificatie van de aanwezige firmware, contactmapping, meterdekking en lokale beveiligingen.
