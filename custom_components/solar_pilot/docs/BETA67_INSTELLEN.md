# SolarPilot 1.0.0-beta.67 — instellen en controleren

Panasonic blijft zelfstandig eigenaar van warm water, ruimtebedrijf en alle fabrikantbeveiligingen. SolarPilot mag voor die warmtepomp uitsluitend het bestaande toegewezen SG-contact aanvragen/vrijgeven. Deze update toont automatisch de actuele warmtepomptaak, elektrische activiteit en elektrische bijverwarming als afzonderlijke informatie. Verse native meldingen en afleidingen uit meting/context hebben hun eigen uitleg. Het bestaande meterpaar krijgt een expliciet benoemd Panasonic-voedingsprofiel als presentatie-aanname. Bevestigde activiteit/rust, metingen, SG-lagen, beslisreden en Details blijven beschikbaar. Zonder bruikbaar bewijs verschijnt geen prominente Werking onbekend-indicator. De bestaande SG-policy, het lokaal gekozen bereik en de meterroute blijven behouden. Zij schrijft geen Panasonic-doel, bedrijfsmodus, SG-percentage of heater-toestemming.

Volledige actuele werking: `ACTUELE_WERKING.md` en **SolarPilot → Uitleg** in Home Assistant. Werkelijk uitgevoerde software-/publicatiecontroles: `TESTRESULTATEN_BETA67.md`. Oudere verslagen zijn geen beta.67-testbewijs.

## 1. Upgrade met behoud van gegevens

Bouwbasis: de gecontroleerde gepubliceerde [beta.66](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.66), main-commit `16d78d94cd95063211d86ef6524dee43156188eb`. Die tag en haar assets blijven onveranderd. Beta.67 behoudt de ondersteuning voor onveranderbare en geneste HA-opties uit beta.63.

1. Maak vóór de upgrade een volledige privé Home Assistant-back-up, inclusief configuratie, SolarPilot-opslag, modellen en lokale userfiles. Bewaar de passende beta.66-code voor rollback.
2. Controleer de huidige SG-aanvraag en contactstand; geef een eigen aanvraag vrij voordat je de programmabestanden vervangt. Onderbreek geen beschermde afwascyclus en maak geen nieuw APP-ticket als updateproef.
3. Update via HACS naar exact `1.0.0-beta.67` zodra de release gepubliceerd is en herstart Home Assistant volledig. Herlaad de browserpagina volledig of sluit de app volledig af en open haar opnieuw. Controleer de geladen backend- én kaartversie onderaan bij **Instellingen & controle**; beide moeten `1.0.0-beta.67` zijn. Een download of integratieherlading bewijst niet dat nieuwe browsercode geladen is.
4. Bij lokale installatie vervang je uitsluitend `custom_components/solar_pilot`. Bewaar `userfiles`, HA-configuratie en eigen opslag. Verwijder of herschep de bestaande integratie niet.
5. Controleer behouden andere toestellen, prioriteiten, APP-tickets, modellen en historie. Ongewijzigde geldige beta.66-SG-/profiel-/meter-/koelbevestigingen blijven behouden; deze codeupdate vraagt daarvoor geen nieuwe bevestiging. De nieuwe weergave gebruikt bestaande bronkoppelingen en standaard 200 W; nieuwe instellingen of entiteiten invullen is niet nodig. Het bestaande paar verschillende sensoren gebruikt automatisch de aanname voeding 1 = warmtepomp inclusief regeling/pompen, voeding 2 = elektrische bijverwarming; eerdere expliciete afwijkende rollen blijven behouden. Verfijning blijft optioneel. Nieuwe of werkelijk gewijzigde keuzes houden hun bestaande lokale bevestigingsvoorwaarden. Renderen en upgraden maken geen nieuwe fysieke toestemming.

Eerste installatie: voeg de repository in HACS toe als **Integration**, installeer, herstart HA en voeg SolarPilot toe onder **Instellingen → Apparaten & diensten**. Begin met betrouwbare P1/PV in **Alleen bekijken**. De frontend wordt automatisch geregistreerd; er is geen aparte Lovelace-resource, dashboard-YAML of www-kopie nodig.

## 2. Het juiste toepassingsbereik

Bij een ongewijzigde bestaande beta.66-installatie controleer je de behouden waarden. Je hoeft haar bewezen SG-ingebruikname niet over te doen wegens deze update. Voor een nieuwe installatie of werkelijk gewijzigde koppeling/profielkeuze gelden de onderstaande voorwaarden.

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

Een actuele 0 W is gemeten nul. Is één deelmeter ontbrekend, oud, negatief of anders ongeldig, dan blijft het totaal onvolledig/onbekend en de bekende deelwaarde zichtbaar. De weergave gebruikt op het bestaande verschillende sensorpaar automatisch het Panasonic-profiel: voeding 1 voor warmtepomp inclusief regeling/pompen, voeding 2 voor elektrische bijverwarming. De kaart benoemt deze aanname; een aangenomen rol bewijst geen bedrading en maakt een onvolledig totaal niet compleet. De meters moeten afzonderlijk actueel, geldig en W/kW zijn voordat activiteit wordt getoond. Een enkelvoudige meter krijgt geen automatisch rollenpaar. Een eerdere bewuste afwijkende rol blijft staan.

Panasonic-documentatie toont modelverschillen. In de beschreven standaardopstelling omvat voeding 1 compressor, regelprinten, ventilator en circulatiepomp; voeding 2 kan interne backupverwarming en een door Panasonic bestuurde externe tapwaterbooster omvatten. Bij sommige oudere varianten ligt backupverwarming juist op voeding 1. Daarom is de automatische rol een herkenbare presentatie-aanname, geen universele modelclaim. De opgenomen watts onderscheiden backup- en boosterelementen niet. SG is een apart contactsignaal, geen vermogensvoeding: compressorbedrijf terwijl de ondersteuningsmeter 0 W meet, is mogelijk en bewijst geen SG-effect. Eén gunstig werkpunt verlaagt geen elektrische marges en is geen gegarandeerd maximum.

## 4. Begrenste aanvraag en nieuwe aanleiding

Bestaande defaults blijven: startdrempel **3000 W**, aparte raming **3200 W**, startvertraging **120 s**, stopvertraging **60 s**, rust **900 s**, sessie maximaal **3600 s**, kleine-importbuffer **300 W**. Dit zijn voorzichtige beleidswaarden, geen bewezen toestelvermogen. De lokale toestemming blijft **300 s**, met vernieuwing iedere **60 s** en steeds begrensd door de resterende sessieduur.

Vernieuwing verlengt dezelfde AAN-toestand, zonder fysieke UIT/AAN-cyclus. Netafname boven de buffer gedurende de stopvertraging geeft alleen de eigen SG-aanvraag vrij; tijdens die tekortcontrole wordt geen nieuwe toestemming geplaatst. P1/PV, fase-/netgrenzen, actuele bronnen en voorrang blijven beslissend. Native warmtepompverbruik kan na SG-UIT doorgaan en is niet ineens vrijgemaakt flexvermogen.

De maximale sessieduur betekent **sessielimiet**, geen volle tank. Onbekende reactie betekent geen werkelijk voltooide cyclus. De algemene beleidswachtstand onderscheidt sessielimiet, native voltooid, geen aangetoonde opname en onbekende reactie. Zij blijft ook na onderbreking, lokale timerafloop, bronverlies, netvrijgave of reload gelden. Handmatige overname, transportonzekerheid en veiligheidsblokkeringen blijven afzonderlijk.

- **Uitsluitend tapwater:** na rust kan dezelfde tankbron minstens 2 °C afkoeling ten opzichte van de verse eindmeting aantonen, bevestigd met minstens twee nieuwe echte rapporten over vijf minuten. Zonder bruikbaar eindbewijs, na bronwisseling of bij onbetrouwbare data blijft deze wachtstand staan. Na reload begint de vijfminutenbevestiging opnieuw.
- **Algemeen profiel:** een warme, onveranderde of ontbrekende tank blokkeert niet zelfstandig ieder volgend algemeen gebruik. Na iedere beëindigde of onderbroken algemene sessie zijn na rust minstens twee nieuwe echte rapporten over vijf minuten nodig voor een gewijzigde betrouwbare relevante native context, of een nieuwe relevante actieve episode na eveneens bevestigde rust. Een nieuwe zonneperiode kan ook gelden: eerst minstens vijf minuten restoverschot hoogstens de kleine-importbuffer en vervolgens minstens vijf minuten vanaf de startdrempel, telkens met minstens twee nieuwe rapporten.
- **Iedere nieuwe sessie:** de volledige startvertraging en actuele zon-, bron-, elektrische-, koel- en voorrangsvoorwaarden gelden opnieuw. Vastgelegde bewijslagen blijven bij reload bewaard; lopende vensters vragen nieuwe rapporten. Dezelfde samples, constante zon, rusttijd of herstart alleen geeft geen eindeloze hertriggerlus.

Bij bevestigde omschakeling van een oude tankgebonden hold naar algemeen bereik blijft de herkomst privé bewaard. Nieuw betrouwbaar relevant native bewijs of een aantoonbaar nieuwe zonneperiode is nodig; omschakelen alleen start niets. Echte handmatige, communicatie- en veiligheidsblokkeringen verdwijnen hierdoor niet. Een gewijzigde native uitleesbron bewijst geen nieuwe vraag: de eerste verse rapportage stelt alleen een referentie vast. Daarna blijft werkelijk gewijzigde context of een nieuwe zonneperiode nodig. Bij relevante native bronwijziging moet ook de koelbeveiligingsbevestiging opnieuw worden beoordeeld. **Automatisering hervatten** vraagt een nieuwe actuele beoordeling en is geen gedwongen AAN.

## 5. Wat je op de warmtepompkaart ziet

De warmtepomp staat in **Overzicht** en **Toestellen** tussen de andere blokken. **Warmtepomp** toont dezelfde actuele Panasonic-/SG-uitleg. Twee vaste onderdelen tonen **Taak van de warmtepomp** en **Elektrische bijverwarming**. Tankinformatie, meetwaarden, SG-lagen, beslisreden en Details blijven beschikbaar.

Alles gebruikt automatisch bestaande bronkoppelingen en standaard **200 W** voor elektrische activiteit; een nieuwe sensor kiezen of formulier invullen is niet nodig. De taak die Panasonic daadwerkelijk meldt, de elektrische activiteit en een gekozen stand hebben een verschillende betekenis. Alleen complete bevestigde actuele meterdekking vormt een totaal.

| Bronbewijs | Weergave en betekenis |
| --- | --- |
| Verse passende werkelijke native taakmelding | **Panasonic meldt** sanitair water opwarmen, ruimte verwarmen of ruimte koelen. Deze hoofdtaak blijft apart leesbaar bij lage/nul/partiële of ontbrekende meting. Zij bewijst geen afzonderlijke compressorbeweging of hoeveelheid warmte. |
| Exact gekoppelde verse Aquarea-poll | De bestaande binding kan automatisch HEATING (2), COOLING (3) of HEATING_WATER (4) melden. Geen extra entiteit of invoer; actualiteit en passend apparaat blijven vereist. |
| Verse actieve hoofdvoeding én compleet actueel totaal met passende tankroute | **Sanitair water opwarmen**, expliciet als afgeleid, met uitleg dat hoofdmeting en tankroute worden gecombineerd. Watts of tankroute alleen onderscheiden geen werkelijke thermische taak. |
| Compleet actief totaal door ondersteuningsvoeding, hoofdvoeding op nul/basis | **Elektrische bijverwarming actief**; geen afgeleide warmwater-/ruimtefunctie alleen uit heaterverbruik. |
| Alleen een verse gekozen tank-/programmastand | **Tankroute** of **Gekozen stand**, als context. Alleen heating of WATER is geen werkelijk gemelde opwarmactie. |
| Verse passende rustmelding | **Panasonic meldt rust**; deze eigen bronmelding wordt niet door alleen watts of tankroute tot warmwater-/ruimteactie gemaakt. |
| Verse geverifieerde ontdooimelding | **Ontdooien**, vóór de gewone warmte-/koelrichting. Geen SG-effect of compressorbeweging uit afleiden. |
| Oude, ontbrekende of tegenstrijdige taakcontext | Geen actuele functieclaim; **Geen actuele taakmelding** wanneer er geen bruikbare taakmelding is. Verse geldige vermogenswaarden houden hun eigen betekenis. |
| Verse actieve hoofdvoeding vanaf de weergavegrens | Elektrische warmtepompactiviteit; het hoofdcircuit kan regeling en pompen omvatten. Geen zuivere compressor- of warmteproductiemeting. |
| Verse ondersteuningsvoeding vanaf de weergavegrens | **Bijverwarming aan · afgeleid**, uit het opgenomen vermogen en de aangenomen of expliciete voedingsrol. Geen afzonderlijke heaterterugmelding. |
| Actuele ondersteuningsvoeding gelijk aan 0 W | **Geen verbruik** op die voeding; geen totale inactiviteit bij ontbrekende andere meting. |
| Actuele lage positieve ondersteuningsvoeding | **Basisverbruik**. |
| Geen gekoppelde ondersteuningsmeter | **Geen heaterdeelmeting**; er is geen aparte voedingswaarneming om te interpreteren. |
| Gekoppelde maar ontbrekende of oude ondersteuningsmeter | **Geen actuele meting**; een laatst bekende stand levert geen actief/uit-bewijs. |
| Complete actuele totale meting | Totaal en complete nul/lage/actieve elektrische activiteit; een deelmeting wordt nooit stil een volledig totaal. |
| Verse geldige compressorfrequentie | Afzonderlijk werkelijk compressorbewijs. Dit blijft onderscheiden van taakmelding, meting en activiteitssymbool. |

Werkelijke verse native actie heeft haar eigen bronbetekenis; zij hoeft niet te wachten totdat de hele warmtepomp elektrisch boven 200 W wordt gemeten. Een afgeleid functielabel houdt de gebruikte verse meting/context als herkenbare uitleg. Tegenstrijdige werkelijke native taken geven geen eenduidige functieclaim. Een gekozen koelprogramma met tankmogelijkheid is op zichzelf geen conflict met werkelijk gemelde tankopwarming. Een geverifieerde verse ontdooimelding onderdrukt de gewone warmwater-/ruimtefunctie; zij wordt niet uit watts of temperatuur gegokt. Alleen een gekozen heating-tankstand geeft geen werkelijk gemelde tapwateropwarming. De displayreader verandert geen controllerprogrammalezing, SG-vrijgave of bediening.

De ventilatoranimatie toont **bevestigde activiteit of actuele elektrische activiteit van de hoofdvoeding** en mag bij een verse actieve hoofdmeting draaien, ook als een afzonderlijke bron 0 Hz meldt. Zij beweert geen echte compressor- of ventilatorbeweging. Bij uitsluitend actieve elektrische bijverwarming en niet actieve hoofdvoeding blijft de ventilator stil en beweegt het verwarmingssymbool. De kaart houdt eventueel afwijkend compressorbewijs afzonderlijk leesbaar. Oude/ongeldige bronnen geven geen lopende animatie. Met de systeemvoorkeur **Verminderde beweging** staan animaties stil, terwijl labels en waarden zichtbaar blijven.

Een gekoppelde maar oude of ongeldige compressorbron blijft technisch onbekend; verse meting vervangt haar niet als compressorbewijs. Alleen zonder gekoppelde compressorbron kan passende verse native activiteit afzonderlijk bedrijf/rust bevestigen. Zonder bruikbaar bewijs verschijnt geen prominente Werking onbekend-badge; metingen, SG, reden, Details en export blijven beschikbaar.

De volgende opties zijn uitsluitend voor wie zelf wil verfijnen; ze zijn geen stap om de update te gebruiken.

| Optionele weergaveoptie | Betekenis en grens |
| --- | --- |
| **Actief verbruik vanaf (W) — alleen weergave** | Standaard **200 W**, instelbaar van **10 tot 2000 W**. Alleen elektrische uitleg/animatie; geen SG-start-/stopdrempel, timer, koelvrijgave of toestemming. |
| **Functie voeding 1/2 — automatische weergave**: **Automatisch volgens Panasonic-voedingen** | Het bestaande verschillende sensorpaar gebruikt voeding 1 als warmtepomp inclusief regeling/pompen en voeding 2 als elektrische bijverwarming, zichtbaar als profielaanname. Een enkele meter krijgt geen automatisch rollenpaar. |
| Dezelfde functieoptie: **Hoofdvoeding: warmtepomp, regeling en pompen** | Expliciete uitleesrol voor de lokaal bekende hoofdvoeding; geen zuivere compressormeter. |
| Dezelfde functieoptie: **Elektrische ondersteuning** | Expliciete uitleesrol voor het opgenomen vermogen van die ondersteuning; geen afzonderlijke native heaterstatus of bediening. |

Bestaande bewust gekozen afwijkende rollen blijven behouden. Niet-overlapdekking, voedingsrol en SG-rechten blijven afzonderlijk. De automatische rol geeft geen dekkings-/veiligheidsbevestiging en geen nieuwe bediening. Bij een werkelijk gewijzigd meterpaar blijft herbeoordeling van de totale dekking nodig; een afwijkende eerdere rol hoort bij haar oorspronkelijke meter. De update vraagt geen nieuwe SG-ingebruikname voor ongewijzigde geldige koppelingen.

De **gemelde SG-contactstand** staat prominent. De **SolarPilot-aanvraag** staat in Details, samen met eigenaar en beslisreden. Een bekende afwijking tussen aanvraag en contact krijgt een expliciete waarschuwing. **Ontvangen SG** verschijnt alleen als een echte passende actuele bron de ontvangen stand bevestigt. Zonder die bron staat geen permanente onbekende ontvangen-status op de kaart; technisch blijft zij onbekend in bronbewijs/Details/export. Contact AAN is geen bewijs dat SG daadwerkelijk ontvangen is of dat extra warmte wordt geproduceerd. Native taak, watts, compressor en animatie leveren daarvoor evenmin een ACK. De lokale timer en bronactualiteit blijven apart.

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

Voor de ongewijzigde beta.66-upgrade volstaat de read-only weergavecontrole: controleer beide versievelden, behoud van je instellingen, de warmtepomp in Overzicht/Toestellen/Warmtepomp, beide vaste onderdelen, de prominente contactstand, aanvraag in Details, eventuele bevestigde ontvangen-SG en bekende mismatchwaarschuwing, plus overeenkomst met de bestaande bronnen in HA. Vergelijk voedingswaarden en de verse native taakmelding met HA. Bekijk of hoofdvoeding en elektrische bijverwarming hun eigen actuele activiteit tonen en of de automatische Panasonic-profielaanname herkenbaar blijft. Het totaal mag alleen verschijnen bij complete actuele bevestigde dekking. Een gekozen tankstand is context; een werkelijke native taakmelding blijft als zodanig herkenbaar. Controleer de ventilatoranimatie bij verse hoofdactiviteit, apart verwarmingssymbool bij alleen ondersteuning en stilstaande animaties bij Verminderde beweging. Compressorfrequentie blijft afzonderlijk bewijs, ook bij 0 Hz. Hiervoor hoef je geen configuratieformulier te openen. Een ontvangen-SG-bron heeft haar eigen betekenis: zonder passende actuele bevestigde bron wordt geen ontvangen-status op de kaart getoond en blijft het bronbewijs technisch onbekend.

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

## 8. Export hier laten analyseren en advies optioneel teruglezen

1. Kies bij **Analyse nodig** **Maak analysebestand**: één klik stelt de beschikbare **zeven dagen** met open bevindingen samen, zonder extra vragen of nieuw configuratieformulier. Onder **Meetkwaliteit** staan dekking en bevindingen als waarnemingen. Je kunt ook rechtstreeks **Export** openen. Download het **JSON.GZ**-bestand. Het pakket bevat een gerichte `analysis_request`, bronherkomst en het adviesrapportformaat. Na de export is **Adviesrapport-sjabloon downloaden** apart beschikbaar met de exacte bronhash; downloaden daarvan is optioneel. Hiervoor hoef je geen extra entiteit of nieuw configuratieformulier te kiezen.
2. Voeg het bestand hier bewust toe. De meegeleverde analysevraag betreft onderbouwde warmtepompinsteltips, SolarPilot-keuzes en logische codeverbeteringen, met bronbewijs, vertrouwen en beperkingen; je hoeft die onderwerpen niet opnieuw in een formulier in te vullen. Deel privégegevens alleen bewust; er is geen automatische upload.
3. Vraag desgewenst een **JSON-antwoord-/adviezenrapport** volgens het meegeleverde template. Het advies kan native warmtepompinstellingen, SolarPilot-instellingen, logische verbeteringen of waarnemingen betreffen. Het rapport bevat tekst, bewijs, vertrouwen en beperkingen, geen uitvoerbare opdrachten. Antwoorden op bevindingen vragen de bijbehorende **zevendagenexport**; korte exports kunnen wel een adviesrapport zonder bevindingantwoorden opleveren. `question_answers` kan maximaal honderd geëxporteerde bevindingen met `question_id`, `revision`, `answer` en `outcome` beantwoorden: `reviewed` of `needs_more_data`.
4. Upload het rapport optioneel bij **Export** en lees de bevindingen/tips. Alleen een HA-beheerder kan uploaden, bekijken of verwijderen. Ondersteund is UTF-8 JSON van maximaal **1 MiB** en **honderd adviezen**; dubbele of onbekende velden/ongeschikte schema-inhoud worden geweigerd.
5. Controleer de bronbinding. Exportidentiteit, SHA-256, release en aanmaakdatum moeten exact passen bij een van maximaal **vijftig** bewaarde succesvolle exportidentiteiten voor een gekoppelde herkomst. Een niet gekoppeld rapport blijft zichtbaar als **ongeverifieerd**; een versieverschil wordt duidelijk gemeld. Een bronmatch bevestigt herkomst, niet dat iedere aanbeveling inhoudelijk juist of geschikt is.
6. Bekijk welke bevindingen zijn verwerkt. Alleen exact bij deze export én nog actuele identiteit/revisie passende antwoorden veranderen reviewstatus. `reviewed` handelt de bevinding af; `needs_more_data` blijft open. Oud/onbekend/gewijzigd bewijs wordt niet als actueel afgehandeld. Een gekoppeld rapport met antwoorden op niet uit die export afkomstige bevindingen wordt geweigerd. Sampling-/aanpassingsbeleid en modeltoestemming blijven behouden. Beoordeel daarna de tips. De upload verandert **geen instellingen, code of apparaat** en verstuurt geen servicecall. Voer een gewenste instellingenwijziging alleen als afzonderlijke bewuste actie uit volgens haar bestaande voorwaarden. Een codevoorstel vraagt een afzonderlijke geteste release; Panasonic blijft eigenaar van zijn normale regeling.

Een logisch codevoorstel kan een optionele stabiele `proposal_id` hebben. De status daarvan wordt alleen uit het vertrouwde meegeleverde implementatieregister, exact dezelfde voorstelidentiteit én inhoud en de geïnstalleerde release bepaald; geüploade tekst kan zichzelf niet als uitgevoerd verklaren. Het rapport blijft bij gewone updates behouden en toont bron-/huidige versie apart. Nog open logische voorstellen kunnen in een volgende analyse meegaan. Uploaden werkt de integratie niet bij: daarvoor is een afzonderlijke geteste release met de normale HACS-/herstartprocedure nodig.

Bij zo'n volgende analyse behoudt een open logisch voorstel dezelfde `proposal_id` en ongewijzigde abstracte tekst. Privé-entiteiten, tijdstippen en onderbouwing staan apart in `evidence`; zo verandert nieuwe pseudonimisering de voorstelinhoud niet. Alleen een passend vertrouwd register kan het voorstel later als opgenomen tonen.

| Softwarevoorstelstatus | Betekenis |
| --- | --- |
| **Opgenomen in de geïnstalleerde versie** | Identiteit en inhoud passen exact bij het vertrouwde register en de geïnstalleerde versie is minstens de geteste introductierelease. |
| **Nog niet in deze versie opgenomen** | Het voorstel is bekend, maar de tekst is gewijzigd of de geïnstalleerde versie is ouder/onherkend. Geen uitvoering claimen. |
| **Nog niet gekoppeld aan een softwarewijziging** | Geen passende vertrouwde voorstelidentiteit. Een advies is daarmee nog geen uitgevoerde codewijziging. |

Alleen het laatste rapport per integratie-entry wordt lokaal bewaard. Verwijderen wist het adviesrapport, geen oorspronkelijke metingen, exporthistorie, instellingen of modellen. Bevindingen die uitsluitend door dat rapport als beoordeeld golden, kunnen daardoor weer open verschijnen. Succesvolle exportidentiteiten zijn bronverwijzingen; de gewone tijdelijke downloadbestanden houden hun eigen opruiming en limieten.

De analyse gebruikt beschikbare voedingshistorie, native taak/stand/tankroute, ontdooimeldingen, SG-aanvraag/contact/beslisreden, bronkwaliteit, wijzigingen van instellingen en Aquarea-versie. De automatische registratie gebruikt standaard **zeven dagen** met **vijfminutenmeetpunten**, onder de behouden bestaande instellingen/aantallimieten. Zij ziet niet iedere korte piek of compressor-/heaterwisseling. Veranderde taak-/SG-/instellingswaarnemingen krijgen aparte gebeurtenissen waar beschikbaar. Een interval tussen overeenkomstige betrouwbare eindpunten is geen bewijs van ononderbroken fysiek bedrijf; cloudontvangsttijd is geen bewezen fysieke meettijd. Zonder gevalideerde warmtemeting volgt geen COP/SCOP of thermische opbrengst en temperatuur-/wattsnapshots certificeren geen comfort of hygiëne. Meetgaten, gedeeltelijke dekking, stale bronnen en resolutie beperken conclusies; voeding-2-profiel is een aanname, geen bewijs van model, bedrading, interne backupheater versus tankbooster, warmteproductie of extra SG-opname. Niet bewaarde oude data worden niet achteraf aangevuld.

## 9. Rollback

1. Trek de eigen SG-aanvraag in, controleer de contactstand/lokale afloop en voorkom nieuwe vernieuwing.
2. Stop beta.67 voordat een andere runtime terugkomt. De automatische taak-/voedingsuitleg en animaties veranderen geen SG-regel; rollback herstelt de beta.66-weergave en de passende opgeslagen configuratie. Laat nooit twee versies hetzelfde contact beheren.
3. Herstel de gecontroleerde beta.66-code **en de passende volledige privéback-up van vóór deze upgrade**. Alleen de ZIP vormt geen volledige restore van instellingen, opgeslagen bewijs en modellen.
4. Herstart HA, herlaad de pagina volledig of sluit de app volledig af en open haar opnieuw, controleer backend- en kaartversie en kies de gewenste globale modus bewust. Bevestig oude SG-ingebruikname niet zonder haar eigen bewijs; behoud beschermde cycli.

Terugkeer naar de oude directe beta.61-regeling vereist nog steeds code én de volledige bijpassende back-up van vóór de beta.62-SG-migratie. De private herkomstregistratie is geen complete HA-restore en doet geen fysieke replay. Zie `TESTRESULTATEN_BETA67.md` voor software-/publicatiestatus; geladen HA en fysieke acceptatie blijven afzonderlijk bewijs.

## Primaire technische bronnen

- [Shelly Switch RPC: Set, status en timers](https://shelly-api-docs.shelly.cloud/gen2/ComponentsAndServices/Switch/).
- [Shelly 1 Gen4-documentatie](https://kb.shelly.cloud/knowledge-base/shelly-1-gen4).
- [Panasonic Aquarea-installatiehandleiding 2023](https://www.panasonicproclub.com/uploads/GB/catalogues/2023/UK_INSTALLATION_MANUAL_H%202023v3.pdf), p. 7: de beschreven hoofdvoeding en backup-/boostervoeding.
- [Panasonic F-generatie servicehandleiding](https://www.panasonicproclub.com/uploads/CZ/catalogues/aquarea/service-manual/SXC9,12_F_E8_service%20manual_PAPAMY1311028CE.pdf), p. 43: modelverschillen in de voedingsverdeling.
- [Aquarea-provider: DeviceAction-definitie](https://github.com/wpatrik14/aioaquarea/blob/main/aioaquarea/data.py) en [native warmwaterentiteit](https://github.com/wpatrik14/home-assistant-aquarea/blob/main/custom_components/aquarea/water_heater.py): programmastand, tankroute en actuele melding hebben afzonderlijke betekenis.

Protocol- en fabrikantbeschrijvingen vervangen geen verificatie van de aanwezige firmware, contactmapping, meterdekking en lokale beveiligingen.
