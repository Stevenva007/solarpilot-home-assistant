> **Actuele bron: beta.53** — een tijdelijk onbeschikbaar eerder beheerd toestel wordt afzonderlijk opzijgezet, zodat de andere beschikbare toestellen veilig kunnen worden geregeld. Betrouwbare bronterugkeer laat het toestel automatisch opnieuw deelnemen; deelname, prioriteit en bescherming blijven behouden. Test-/publicatiestatus: `docs/TESTRESULTATEN_BETA53.md`.

# SolarPilot

SolarPilot is a local Home Assistant Energy Management System (EMS) for PV surplus, flexible loads, Panasonic Aquarea hot-water policy, Wallbox Full Solar coexistence, phase analysis, capacity-tariff awareness, local PV/shade learning, slow thermal-climate learning, future home batteries and a unified rolling-horizon planner.

De absolute codebasis is de gepubliceerde beta.52 op commit `80402cd03b213334608d4ca0956ce662c5021216`, tree `d1cb08369429a66773ad226c2642baac86aecf46`. De onveranderlijke [beta.52-release](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.52), haar geslaagde publicatieworkflow en gecontroleerde pakketten vormen de rollbackbasis. Een softwaretest of publicatie bewijst geen geladen Home Assistant-versie of fysieke toestelactie.

> **Updates zijn cumulatief.** Je hoeft tussenliggende beta-versies niet één voor één te installeren of publiceren. Installeer de nieuwste release over je bestaande SolarPilot-installatie; Home Assistant-configuratie en lokale leerdata blijven behouden.

## Nieuw in beta.53

- Een onbeschikbaar eerder beheerd toestel wacht afzonderlijk op bruikbare status. De overige beschikbare toestellen kunnen de opgeslagen automatische modus hervatten zodra de globale net- en veiligheidsbronnen geldig zijn. Er volgt geen blinde uitschakeling van het ontbrekende toestel.
- Het ontbrekende toestel blijft automatisch gecontroleerd worden en keert na echte betrouwbare terugmelding vanzelf terug. Eerdere beheerinformatie, deelname, prioriteit, minimumlooptijden en bescherming van lopende programma’s blijven behouden. Een later gekozen Alleen bekijken of Pauze wordt gerespecteerd.
- Mogelijk huidig en later verbruik blijft conservatief gereserveerd. Werkelijk verbruik zit al in de P1-meting; onbekende lasten leveren geen gratis vermogen op. Echte opdrachtfouten en onzekere START-opdrachten behouden hun afzonderlijke blokkering.
- Actieve fasebewaking behoudt de algemene elektrische begrenzing bij ontbrekende of ongeldige actuele fasemetingen, ook met een aangeleerde fasekaart. Instellingen, leerdata, boilerbeleid en volledig read-only Wallbox blijven behouden.

Zie `docs/BETA53_INSTELLEN.md`, `docs/TESTRESULTATEN_BETA53.md` en het actuele `OVERDRACHT.md`. Deze softwarewijziging repareert geen fysieke toestelverbinding.

## Behouden uit beta.52

- Tijdelijke oude, ontbrekende of onbeschikbare toesteldata toont **Automatische broncontrole** en wordt opnieuw uitgelezen bij gewone regelrondes. De kaart biedt hiervoor geen misleidende **Controle afronden** aan. Bronherstel geeft geen recht om een oude opdracht te herhalen.
- Verkeerde vereiste koppelingen en echte opdrachtfouten krijgen hun eigen melding. Echte fouten, handmatige overname, minimumlooptijden, bronversheid en beschermde cycli behouden hun bestaande voorwaarden.
- Analyse-export leest read-only configuratiemappings en hun expliciet gekoppelde bronnen volledig. Privacyfilters, consistente pseudoniemen, maximale bronlijsten en ontbrekende-bronlabels blijven behouden.

De gebruikersbeelden tonen dat de paneelinterface van beta.51 inmiddels opent. De eerdere export bevat een brononderbreking zonder vastgelegde pending opdracht of opdrachtfout; zij bewijst geen specifieke fysieke verbindingsstoring of de oorzaak van een later screenshot. Zie `docs/BETA52_INSTELLEN.md`, `docs/TESTRESULTATEN_BETA52.md` en het actuele `OVERDRACHT.md`.

## Behouden uit beta.51

- Het zijbalkpaneel gebruikt dezelfde JavaScript-module-URL als de automatisch beschikbare kaart. De eerdere combinatie van klassieke scriptlading en modulelading vervalt; er is geen extra dashboardresource nodig.
- Opnieuw geladen release-URL's maken geen dubbele eigen kaartcatalogusitems. Alleen SolarPilot-duplicaten worden opgeruimd; de gedeelde catalogus en kaarten van andere integraties blijven behouden.
- Na installeren: Home Assistant volledig herstarten en de webpagina of appweergave opnieuw openen/verversen. Behoud instellingen en leerdata; geen algemene reset of wijziging van boilerwachttijden.

De aangeleverde melding **Unable to load custom panel** bewijst niet op zichzelf of bestandslevering, browser of WebView de specifieke live oorzaak is. De bewezen loader-/registratiefouten worden met softwaretests hersteld; live laden blijft een afzonderlijke controle. Zie `docs/BETA51_INSTELLEN.md`, `docs/TESTRESULTATEN_BETA51.md` en het actuele `OVERDRACHT.md`.

## Behouden uit beta.50

- Een voltooide boilerstabiliteitscontrole blijft voltooid zolang de actuele zonnevoorwaarden geldig blijven. Wachten op de minimumtijd sinds de vorige doelopdracht start die controle niet opnieuw. Ongeldig zonnebewijs, koeling en meetgaten behouden hun bestaande bescherming.
- De standaard rust van 1800 seconden blijft gerekend vanaf de laatste werkelijk verstuurde doelopdracht, ook een normale herstelopdracht of verlaging. Het verstrijken van deze rust geeft een wachtend voorstel geen eerdere hysterese- of eigendomsrechten.
- Het overzicht en de warmwaterdetailkaart tonen de actuele uitvoeringswachtreden, waaronder de rust tussen doelopdrachten. Een gunstig zonneadvies verbergt die wachtreden niet meer. Voorstel, gemeld Panasonic-doel en gemeten tanktemperatuur blijven apart zichtbaar.
- Instellingen, geldige leerdata, centrale prioriteiten, doelbevestiging en beschermde afwascycli blijven behouden. Geen Force DHW, Powerful, extra APP-aanvraag, Wallbox-opdracht of algemene leerreset.

Zie `docs/BETA50_INSTELLEN.md`, `docs/TESTRESULTATEN_BETA50.md` en het actuele `OVERDRACHT.md`.

## Behouden uit beta.49

- Alleen bekijken kan tijdens actief beheer eerst Pauze en veilige vrijgave vereisen; handmatige OFF en overgenomen doelen blijven beschermd. Vervangende batterijdoelen verrekenen echte eigen flow en respecteren native actuatorgrenzen.
- Een pending batterijopdracht blokkeert nieuwe gewone lastopdrachten, AEG-deadline-START en nieuwe vermogensoverdracht. Na batterijactie is nieuw P1-bewijs nodig; een oude meting wordt niet als vrije ruimte hergebruikt. Beschermde cycli en veilige reductie behouden hun bestaande regels.
- Batterijbevestiging vereist nieuw passend gemeten vermogen van ná de opdracht; voorbereiding op verwijderen vereist ook werkelijk neutrale aansturing. Ontbrekende bronnen of fouten geven geen blinde retry of onterechte vrijgave.
- Ontbrekende forecasturen, gaten en een ontbrekende staart blijven onbekend. Geen fictieve nulforecast of mooier gemaakte kwaliteitsscore; tijdroosters volgen verstreken UTC-tijd met correcte lokale zomer-/wintertijdlabels.
- Dagreplay gebruikt alleen volledig gedekte lokale dagen van 92, 96 of 100 kwartieren. Een nulprijs blijft een echte nulprijs.
- Export pseudonimiseert namen en verwijzingen samen, met behoud van schema-sleutels, eenheden en statuswaarden. Herladen/startafbreking en ongeldige afzonderlijke opgeslagen records behouden geldige andere gegevens.
- Klimaat deactiveren of zonekoppelingen wijzigen wacht op veilig afronden van eigen OFF/coast en pending opdrachten, ook wanneer een beheerde zone tijdelijk onbereikbaar is. Geen algemene leerreset of verruiming van actuator-, comfort- of prioriteitsrechten.

Zie `docs/BETA49_INSTELLEN.md`, `docs/TESTRESULTATEN_BETA49.md` en het actuele `OVERDRACHT.md`.

## Behouden uit beta.48

- Handmatig of extern OFF blijft onbeperkt OFF tot de gebruiker zelf AUTO kiest. Dit vervangt bewust de oudere uitzondering waarbij een harde comfortgrens een handmatige zone kon activeren. Alleen aantoonbaar eigen OFF/coast-zones mogen automatisch worden vrijgegeven.
- Pending of onzekere klimaatopdrachten worden niet opnieuw verstuurd. Nieuwe betrouwbare terugmelding en persistent eigendom/bescherming per zone blijven leidend.
- De coastbeoordeling gebruikt passieve respons en zonnewinst waar gebruikt, plus verwarm-/koelrespons en reactievertraging wanneer de voorspelde comfortgrens die richting nodig heeft. Ontbrekende ongebruikte koelervaring blokkeert een voldoende geleerd verwarmingspad niet.
- Modelstatus, werkelijk opgeslagen bewijs-/sample-/dag-/episodeaantallen en de zekerheid voor de huidige beslissing zijn zichtbaar. De oude complete score blijft aparte vergelijkingsinformatie; weercontext is geen actuele verwarm-/koelvraag.
- Versterkt broncontrole voor vermogen, Wallbox en boiler, houdt een onzekere AEG-START beschermd zonder nieuwe fase-terugmelding en laat handmatige toestelvraag nooit een fout of interlock overrulen. Bestaande minimumlooptijden en beschermde cycli blijven gelden.
- Dynamische prijsbronnen vallen bij ontbrekende, restored, toekomstige of te oude gegevens terug op het ingestelde vaste tarief. Ontbrekende prijsrijen verschuiven het tijdrooster niet.
- Instellingen en geldige leerdata blijven behouden; er is geen algemene leerreset of nieuw actuatorrecht. Alleen oude gecontroleerde fasewaarnemingen zonder bewijs dat andere meters stabiel waren worden niet opnieuw vertrouwd; geldige passieve fasewaarnemingen en handmatige fasekeuzes blijven behouden.

Zie `docs/BETA48_INSTELLEN.md`, `docs/TESTRESULTATEN_BETA48.md` en het actuele `OVERDRACHT.md`.

## Behouden uit beta.47

- Een gewone herstart blijft automatisch echte toestelstatussen controleren zonder handmatige bevestiging. De actuele individuele bescherming van een tijdelijk onbeschikbaar toestel staat bij beta.53; opgeslagen gebruikersintentie en betrouwbare status blijven leidend.
- De oorspronkelijke hervatkeuze blijft bewaard over tussentijdse opslag of een volgende herstart. Een bewuste latere keuze voor Alleen bekijken of Pauze vervangt die keuze. Minimum aan-/uittijden starten bij de nieuwe echte waarneming.
- De boiler controleert temperatuur, doel en beschermingsbronnen automatisch zonder oude doelopdracht te herhalen. Een routinecontrole wacht modulelokaal; echte fout, handmatige overname of gewijzigd doel blijft beschermd. Een pending boileropdracht vereist een nieuwe rapportage ná herstart en de bestaande adapterwachttijd.
- Een afwasmachine met onzekere eerdere START krijgt nooit een tweede START. Alleen een nieuwe betrouwbare lopende of voltooide fase-terugmelding van ná die START kan de specifieke herstartonzekerheid automatisch oplossen; een oude Washing/Finished-stand niet. Andere fouten blijven behouden.

Eenmalig kan oude Alleen bekijken-opslag zonder hervatmarker haar verloren Auto-keuze herstellen: uitsluitend zonder echte fout/handmatige boilerbescherming en met een onderbroken lease van een bekend Auto-toestel of schoon routine-boilerjournal. Nieuwe expliciete Alleen bekijken-/Pauze-keuzes blijven beschermd door de opgeslagen marker.

Zie `docs/BETA47_INSTELLEN.md`, `docs/TESTRESULTATEN_BETA47.md` en het actuele `OVERDRACHT.md`.

## Behouden uit beta.46

- Een actuele native `hvac_action=idle/off` van exact geregistreerde `aquarea` houdt ook in AUTO/HEAT_COOL voorrang op een algemene `PUMP`-taak. Oude of niet herkende optionele taakdata maakt deze betrouwbare klimaatactie niet onbruikbaar.
- Echte `cooling` blokkeert extra warmte; actieve `heating/preheating/defrosting` behoudt de ingestelde ruimtecomfortvoorrang. Ontbrekende, oude, restored of onbeschikbare klimaatbronnen blijven beschermd. De oudere `panasonic_cc`-AUTO-ambiguïteit blijft een actuele expliciete `IDLE/WATER`-taak vereisen.
- Alleen bewezen koeling verlengt de ingestelde koelrusttijd. Onbekende gegevens blokkeren zolang ze ontbreken, maar veroorzaken bij betrouwbaar bronherstel geen nieuw verzonnen halfuur wachttijd.
- Ruwe taakdiagnostiek en conservatief leren blijven apart; `PUMP` wordt niet als een normale rustsample aangeleerd. Alle beta.45-doelbevestiging, temperaturen, hygiëne, AEG-reserves, prioriteiten en Wallboxgrenzen blijven behouden.

Zie `docs/BETA46_INSTELLEN.md`, `docs/TESTRESULTATEN_BETA46.md` en het actuele `OVERDRACHT.md`.

## Behouden uit beta.44

- Bij een verse geldige Wallbox-meting onder de laaddrempel wordt alleen dan geen EV-vermogen meer gereserveerd wanneer de native bron ook expliciet geen laadvraag, geen verbonden auto of een bekende inactieve status meldt. Oude en onduidelijke bronnen blijven fail-closed; SolarPilot bedient de Wallbox niet.
- De canonieke sessiewaarde **Zonne-auto · wacht op auto** hoort bij de standaard zonne-autostatussen. Een exact oude standaardlijst wordt compatibel uitgebreid; eigen waardelijsten blijven ongewijzigd en native Full Solar blijft verplicht.
- Een lopende AEG-beurt blokkeert extra 60 °C niet meer categorisch. Zonder exclusieve meter blijft het nominale AEG-vermogen conservatief gereserveerd. Alleen wanneer na die en alle andere reserves nog voldoende werkelijk net- én PV-overschot resteert, mag de 60 °C-buffer daarnaast werken; Wallboxvermogen telt nooit mee.
- De startuitleg toont de effectieve toewijzing uit dezelfde engineberekening als het startbesluit, naast de ruwe vrije injectie. Zo wordt zichtbaar wanneer hogere prioriteiten, comfort, een lopende cyclus of toezeggingen het voor dit toestel beschikbare vermogen beperken.
- De geïntegreerde optieswizard leest bij opslaan alleen de benoemde velden van het actuele formulier. Een niet-ondersteunde algemene formulierverzameling veroorzaakt daardoor geen stille mislukking; validatie en de Home Assistant-optiesflow blijven leidend.
- Bij de geregistreerde Panasonic-koppeling telt de onmiddellijke, optimistische doelterugmelding niet meer als bevestiging van een boileropdracht. Een latere Home Assistant-waarneming blijft vereist en is geen bewijs van rechtstreekse apparaatrapportage of opwarming. Een bestaande beschermende wachtstand wordt niet automatisch opgeheven.
- Het warmwateroverzicht toont eerst het gerapporteerde doel en een eventuele beschermende pauze; een voorgesteld SolarPilot-doel is afzonderlijk herkenbaar en wordt niet als reeds toegepast getoond.
- Een afzonderlijk gekoppelde native taakbron maakt gemeld ruimtebedrijf en een gemelde tapwatertaak zichtbaar. Beta.46 laat actuele native `aquarea`-actie voor deze extra-DHW-guard voorgaan op een algemene `PUMP`-taak; de oude `panasonic_cc`-AUTO-beperking en werkelijk onbetrouwbare klimaatbronnen blijven beschermd. Taakinformatie bewijst geen HEAT/COOL of compressorvermogen.

Beta.44-publicatie, pakketcontrole en geladen versie staan in `docs/BETA44_INSTELLEN.md` en `docs/TESTRESULTATEN_BETA44.md`; uitleg-hash `65b54c9797e55bb4` hoort bij die historische softwaregate. [Beta.44-release](https://github.com/Stevenva007/solarpilot-home-assistant/releases/tag/v1.0.0-beta.44). Bestaande tags en release-assets blijven onveranderlijk.

## Current DHW policy (beta.53)

For Panasonic K T-CAP models, Powerful is **not automatically used as a tank boost**: Panasonic service manual PAPAMY2310071CE §14.11 describes space-heating water-target shifts, not a DHW boost. The separate installer setting DHW capacity is not changed. [Panasonic-original service manual](https://paltaja.lt/wp-content/uploads/panasonic-k-t-cap-manual.pdf).

The exact registered water-heater adapters `aquarea` and `panasonic_cc` retain the beta.45 delayed target acknowledgement: an immediate optimistic target echo is ignored and a matching new Home Assistant report after at least ten seconds is required. A delayed cloud report is not independent physical proof. Reported target, proposed target and protective pause remain separate; an existing manual hold requires the guarded explicit review.

For the exact native `aquarea` climate adapter, fresh `hvac_action=idle/off` is trustworthy in AUTO/HEAT_COOL. Generic task information such as `PUMP`, stale optional task data or an unmapped optional task cannot override that reliable climate action. Actual cooling always wins and actual heating/preheating/defrosting retains the configured space-climate priority. Missing, restored, stale or unavailable climate information still blocks optional heating.

The older `panasonic_cc` AUTO mapping can expose idle/off despite a possible space task. It remains ambiguous without a fresh explicit `IDLE/WATER` task. The raw task remains diagnostic and learning information; `PUMP` is never relabelled as proven normal operation. Only confirmed cooling updates the cooling wait timer. Unknown data blocks while unknown and does not invent an extra wait once reliable evidence returns. The configured stricter COOL-mode detection option retains its existing meaning. Persisted pre-beta.46 cooling/uncertainty timestamps remain conservatively protected because their original cause cannot be reconstructed; an existing cooldown or native-DHW hold may therefore temporarily remain.

Normal tank setpoint and monitored comfort floor are independent (new defaults 50/46 °C). No deadband-compensating 52 °C boost or Force DHW. A 50 °C target with a -5 °C native differential can reheat around 45 °C: 46 °C is monitored, not guaranteed and not a hygiene standard. Optional bounded evening solar storage waits for space climate; see `docs/BETA28_INSTELLEN.md`. Existing setpoints and permissions migrate without silent profile activation.

Solar stability and the minimum interval since the last issued target command remain independent. A completed solar check is retained while an optional rise waits for that interval, provided current source and guard conditions remain valid. A waiting proposal does not gain ownership or start-hysteresis rights. The dashboard shows the actual runtime wait separately from the policy's energy advice; a proposed 60 °C while the native target remains 50 °C is no proof of dispatch, acknowledgement or physical heating.


## Nieuw in beta.43

- **Nu actief** gebruikt de werkelijk waargenomen toestelstatus en maakt gemeten versus geschat vermogen zichtbaar. Activiteit bewijst niet dat alle energie op dat moment van PV komt of dat SolarPilot de start veroorzaakte.
- De Wallbox blijft read-only, maar toont nu de actuele bekende wachtstatus en maximaal dertig lokaal waargenomen laadperiodes. Een historische native stopreden wordt alleen gekoppeld bij een aantoonbaar nieuwe status uit dezelfde rapportagebatch; gaten, herstarts of oude/onlogische tijden blijven onbekend.
- Browser **Terug** en **Vooruit** herstellen uitsluitend SolarPilot-schermen op dezelfde Home Assistant-URL. Niet-opgeslagen formulieren vragen bevestiging en opslaan of een lopende actie wordt niet onderbroken.
- De aparte automatische-voordeelweergave bewaart maximaal negentig dagen vanaf activering. Het is een opportunity-value-schatting op bruikbare meetintervallen, geen bewezen extra besparing en geen bedrag dat nogmaals van de elektriciteitskost mag worden afgetrokken.
- De AEG-afwasmachine krijgt een optionele afzonderlijke maandagdeadline. Leeg houdt ook maandag de gewone 13:00; bijvoorbeeld 10:00 geldt alleen op maandag. Bestaande tickets blijven bevroren tenzij je expliciet dezelfde geplande dag laat herberekenen; dat maakt geen ticket en verstuurt geen START.
- De beschermde avondvoorraad tot de ingestelde limiet en maximaal 55 °C mag alleen actuele, expliciet bevestigde Full Solar-lading als vrijmaakbaar zonnevermogen meewegen: verbonden en vragend, minstens 50 W, sessiestatus én vermogen hoogstens 120 seconden oud. Handmatig/onbekend/oud laden telt niet; extra 60 °C krijgt nooit EV-krediet en comfort-, koel- en fabrikantbeveiliging blijven hoger.
- Alle beta.42-veiligheidsgrenzen blijven cumulatief behouden: gerichte DHW-Hervat, eerlijke effectieve Voorrang, begrensde leerreset, handmatig OFF gezette klimaatzones, extra boilerwarmte alleen onder eigendom en een volledig read-only Wallbox.
- De definitieve softwaregate voor beta.43 is groen met **1656 geslaagde Python-tests** en **veertien geslaagde browsercontroles**. Publicatie en installatie veranderen die softwarecontrole niet in een fysieke acceptatietest.
- Een beschermde AEG-cyclus bleef bij de goedgekeurde herstart behouden, zonder nieuwe APP-aanvraag, START of STOP. Gerichte DHW-herstartcontrole en hervatten zijn gecontroleerd; dit bewijst niet dat alle latere beta.44-regels fysiek zijn uitgevoerd.
- Het SolarPilot-logo is werkelijk zichtbaar bevestigd in het Home Assistant/HACS-updatevenster naast een semantisch versienummer. Ondersteunde Home Assistant-`entity_picture`-customisatie gebruikt de lokale brandsproxy; daarna is alleen de update-entiteit opnieuw opgevraagd. Er is geen HACS-codepatch, warmtepompcommando of extra SolarPilot-installatie voor nodig geweest. Dit bewijst niet dat ook het afzonderlijke HACS-repositoryoverzicht is aangepast. Zie de [ondersteunde Home Assistant-customisatie](https://www.home-assistant.io/integrations/homeassistant/#editing-entity-settings-in-yaml).

Zie `docs/BETA43_INSTELLEN.md` en `docs/TESTRESULTATEN_BETA43.md`.

## Behouden uit beta.40: gericht AEG-herstel

- De live diagnose bewees dat beta.39 tijdens zijn enige setupcontrole nog geen legacy-marker zag, terwijl beide markers en alle verplichte AEG-rollen kort daarna volledig op hetzelfde Home Assistant-apparaat aanwezig waren.
- De bestaande legacy-recovery blijft daarom na SolarPilot-start maximaal tien minuten gericht actief, reageert op relevante states en controleert begrensd opnieuw. Na succes, timeout of unload worden de tijdelijke listeners verwijderd.
- Alleen één complete, eenduidige same-device mapping kan een profiel opleveren. Ontbrekende of ambigue verplichte rollen geven geen fysiek recht; `dishwasher_setup` maakt de rolstatus zichtbaar zonder private device-id.
- Een laat hersteld profiel wordt persistent en live toegepast, verschijnt onder Toestellen en volgens de bestaande voorkeursregel onder Voorrang. Alleen de exacte eenmalige legacy-recovery kan Auto herstellen wanneer geen eerdere gebruikersmodus bestaat.
- De migratie maakt geen APP-aanvraag, verandert geen programma en verstuurt geen START. Exacte nieuwe `Enabled`-overgang, deur, programma, Ready To Start, actuele verbinding, elektrische ruimte en alle overige veiligheidslocks blijven verplicht.
- Een later bewust verwijderd herstelprofiel wordt niet stil opnieuw gemaakt. Handmatige profielen en bestaande gebruikerskeuzes worden niet overschreven.
- De beta.39-fixes voor ConnectivityState als heartbeat, volledige beschermde cyclusfasen en de onbewezen automatische alarmbron blijven cumulatief behouden, evenals centrale prioriteiten, Wallbox-read-onlybeleid, Panasonic/DHW, fasebewaking, planner, analyse en leerdata.
- De beta.40-bron werd met haar toenmalige regressiesuite vrijgegeven. Zie `docs/BETA40_INSTELLEN.md` en `docs/TESTRESULTATEN_BETA40.md` voor die historische releasecontrole.

## Install via HACS

This repository is intended to be added as a **HACS Custom Repository** of type **Integration**.

1. In HACS, open **Custom repositories**.
2. Add this repository URL and choose **Integration**.
3. Download **SolarPilot**.
4. Restart Home Assistant.
5. Go to **Settings → Devices & services → Add integration → SolarPilot**.
6. Select your grid-power source and optional PV source, then keep the integration in **Alleen bekijken** during the first checks.

The SolarPilot frontend is shipped inside the integration. No `/config/www` file, Lovelace resource or manual dashboard YAML is required for normal use.

## Updates

HACS manages the integration files. A normal update is:

**HACS → SolarPilot → Update → Restart Home Assistant**

SolarPilot configuration and learned runtime data are stored in Home Assistant, not in the program files replaced by HACS. The optional `userfiles` directory is marked persistent so a local private bundle survives ordinary HACS updates.


## Optional private profile + history

A private bundle is optional. Place exactly one local file at:

```text
/config/custom_components/solar_pilot/userfiles/private_bundle.json
```

Then open **SolarPilot → Configure → Advanced & system → Private profile & history** and apply/reload it. The importer only fills still-empty links to Home Assistant entities that actually exist. Monitoring/advisory modules may be enabled with safe defaults, but physical climate control, phase shedding and DHW control remain explicitly protected. A first setup starts in **Alleen bekijken**. On ordinary restart actual-state reconciliation protects each unresolved device separately; valid global measurements and all remaining guards are still required before the stored automatic mode can regulate the other devices. See `IMPORT_PRIVATE_BUNDLE.md`.

## Safe removal

1. In SolarPilot choose **Verwijderen voorbereiden** and wait for **Verwijderen gereed**.
2. Remove the SolarPilot config entry under **Settings → Devices & services**.
3. Remove SolarPilot in HACS.
4. Restart Home Assistant.

SolarPilot does not remove the underlying grid meter, heat-pump, wallbox, inverter, smart-plug or other integrations/devices.

## Current behaviour

The canonical current explanation is [docs/ACTUELE_WERKING.md](docs/ACTUELE_WERKING.md). The same explanation is available inside the SolarPilot Home Assistant panel.

## Important fixed design rules

- Current P1/PV measurements and device protection override forecasts and plans.
- Wallbox Pulsar Max remains read-only and controls its own Full Solar mode.
- Panasonic chooses HEAT versus COOL; SolarPilot never chooses those modes.
- Panasonic sterilisation remains autonomous.
- Battery control is disabled by default and requires explicit ownership/permission.
- An EMS decision is not an electrical safety device.

## Repository privacy

This repository may be public because HACS requires public GitHub repositories. Do not commit Home Assistant backups, access tokens, raw energy-history exports, addresses or other private files. The public repository contains no household-specific entity IDs. SolarPilot can learn live without private data. For a faster installation-specific start, one local `custom_components/solar_pilot/userfiles/private_bundle.json` may contain entity mappings plus an aggregated historical bootstrap. HACS preserves `userfiles` across ordinary upgrades, and the private bundle must never be committed to GitHub.

## Inbegrepen: dagkosten en Wallbox-voorrang

Afzonderlijke elektriciteitskost vandaag met netto afname/injectie en directe PV, naast de behouden 36-uurskostprognose. Wallbox-voorrang is per verbruiker instelbaar, met klein-overschotfallback en behoud van minimumlooptijden. De generieke Wallbox-voorrang per verbruiker wordt bewust gekozen; de nieuwe AEG-voorkeurgroep is in beta.32 standaard aan, zonder fysieke startrechten te activeren. Lees `docs/KOSTEN_EN_WALLBOXVOORRANG.md`. Deze cumulatieve release behoudt ook de eerdere stabiliteits- en interfacecorrecties.

## Geschiedenis per toestel

Open **SolarPilot → Toestellen → Geschiedenis**. De popup toont geregistreerde draaitijd per dag, start-/stoptijden, sessieduur en altijd afzonderlijk Startreden en Stopreden. Kies een datum of vergelijk de laatste 7/30 dagen. De popup blijft open tijdens live telemetrie.

Draaitijd volgt de gekoppelde aan-/actiefstatus: een ingeschakelde slimme stekker bewijst niet dat een compressor continu draait. Externe bediening, onbekende begintijd, meetgaten en herstarts worden apart gemarkeerd. De historiekfunctie registreert sinds beta.25; bestaande opgeslagen sessies blijven behouden. Eerdere niet-geregistreerde redenen worden niet verzonnen. De opslag blijft lokaal, is begrensd en overleeft gewone updates. De volledige historie wordt alleen opgevraagd wanneer de popup wordt gebruikt.

Deze release is cumulatief en bevat ook alle correcties en uitbreidingen uit beta.22, beta.23 en beta.24. Tussenliggende releases hoeven niet apart gepubliceerd of geïnstalleerd te worden. De volledige actuele uitleg staat in `docs/ACTUELE_WERKING.md` en in het Home Assistant-tabblad **Uitleg**.

## Nieuw in beta.28

- Vraagtekens met uitgebreide Nederlandse optie-uitleg via **Configureren met uitleg ?**; dezelfde HA-optiesflow en serverbeveiligingen, geen globale HA-DOM-patch.
- Automatisch alleen-lezen Wallbox-laadprofiel, met expliciete bron-/terugvalstatus, huidige 1-fase/25-A-terugval en toekomstige 3-fasenondersteuning.
- Optionele nacht-/ochtendbewaking: om 09:00 de gewenste gemeten voorraad controleren (standaard 46 °C). Het normale doel blijft 50 °C; geen verhoogde hersteltemperatuur of vaste klokstart. Panasonic mag volgens zijn eigen regeling ook netstroom gebruiken.
- Optionele avondvoorraad op laatste bruikbare zon, begrensd tot standaard 55 °C en gebaseerd op voorzichtig tankleren.
- Normaal warmtepompcomfort vóór Wallbox; extra 60 °C uitsluitend uit echte restinjectie. Recente en optioneel voorspelde koeling begrenzen extra tankopwarming.

Nieuwe comfortfuncties staan na upgrade niet ongemerkt aan. Bestaande instellingen, gebruikersbestanden en lokale leerdata blijven behouden. De fabrikant-hygiëne en verbrandingsbeveiliging blijven onafhankelijk vereist; een ochtendtemperatuur is een doel, geen garantie na waterafname of storingen. Zie **docs/ACTUELE_WERKING.md** en **docs/BETA28_INSTELLEN.md**.

## Nieuw in beta.29: AEG en analyse

Afwasmachine-start met eenmalige klaarzettoestemming en native AEG-START, nooit via de netstekker. Een gestart programma blijft beschermd. De knop **Analyse-export** onderaan het dashboard maakt een lokaal JSON-bestand voor handmatige probleem- en modelanalyse. Zie [instellen en beperkingen](docs/AFWASMACHINE_EN_ANALYSE.md). Nieuwe fysieke koppelingen worden niet automatisch geactiveerd.


## Nieuw in beta.30: Leren & vragen

De meetbasis, ontbrekende gegevens en gerichte beslisvragen staan in een aparte
popup. Basislastleren kan nu doorgaan tijdens EV/eigen lasten wanneer aparte,
actuele meters een betrouwbare restbalans geven. Geen nul voor onbekende data.
Een recente voorspelling wordt in de achtergrond getoetst en alleen na jouw
toestemming en voldoende bewijs begrensd toegepast; veiligheids-/comfortregels
worden niet door leren herschreven. Nieuwe daglichtfouten en meetdekking maken de
kwaliteit begrijpelijker.

Zie [beta.30 instellen](docs/BETA30_INSTELLEN.md) en de release-gebonden actuele
uitleg. De APP-knopgestuurde AEG-start en 13:00-deadline zijn sinds beta.31 inbegrepen;
zie [APP instellen](docs/BETA31_INSTELLEN.md). De huidige cumulatieve release
bevat zowel die startlogica als de leerupdate.

## Afwasmachinevoorrang in beta.32

Zie [de actuele beta.32-instelhandleiding](docs/BETA32_INSTELLEN.md).
Normaal warmtepompcomfort gaat voor, vervolgens de afwasmachine en daarna de
lagere automatische lasten, Wallbox en extra 60 °C-zonnebuffer. De twee nieuwe
voorkeuren staan standaard aan voor AEG-profielen; fysieke rechten blijven staan.
Programmafaseplanning volgt pas met de afzonderlijke latere Shelly-update.
