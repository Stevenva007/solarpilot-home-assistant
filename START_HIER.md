# SolarPilot beta.53 — installatie en upgrade

Beta.53 voorkomt dat één onbeschikbaar eerder beheerd toestel de gewone opstartcontrole voor alle toestellen laat wachten. SolarPilot zet alleen dat toestel tijdelijk opzij, houdt rekening met mogelijk verbruik en hervat de overige beschikbare toestellen als de globale bronnen en veiligheidsvoorwaarden geldig zijn. Het ontbrekende toestel wordt automatisch opnieuw gecontroleerd en keert bij echte betrouwbare status terug, met behoud van deelname, prioriteit en bescherming.

De test-/publicatiestatus staat in [docs/TESTRESULTATEN_BETA53.md](docs/TESTRESULTATEN_BETA53.md). Een fysieke verbindingsstoring blijft bij de gekoppelde HA-integratie te onderzoeken; deze update verandert de softwareafhandeling van die uitval.

## 1. Vooraf

- Maak een actuele volledige Home Assistant-back-up en bewaar de gecontroleerde beta.52-release voor rollback.
- Laat een lopende beschermde afwas- of andere cyclus afwerken.
- Gebruik bij een nieuwe installatie **Alleen bekijken** voor de eerste broncontrole. Bij bestaand actief beheer kan die modus eerst **Pauze** en veilige vrijgave vereisen. Alleen bewezen eigen coast en passende bevestigde numerieke batterijdoelen mogen worden vrijgegeven; handmatige bediening blijft beschermd.
- Updates zijn cumulatief: bestaande Home Assistant-configuratie en lokale leerdata blijven behouden; tussenliggende beta-versies hoeven niet afzonderlijk geïnstalleerd te worden.

## 2. Via HACS installeren of upgraden

1. Voeg bij een nieuwe installatie in **HACS → Custom repositories** `https://github.com/Stevenva007/solarpilot-home-assistant` toe als type **Integration**.
2. Download of update naar exact `1.0.0-beta.53` zodra die release beschikbaar is.
3. Herstart Home Assistant volledig.
4. Herlaad de webpagina. Stop op Android de Home Assistant-app volledig en open haar opnieuw; op iOS kun je de weergave naar beneden trekken om te verversen. Controleer backendversie en geladen kaart afzonderlijk. Een download of manifestnummer bewijst geen geladen kaartcode.
5. Voeg bij een nieuwe installatie **SolarPilot** toe via **Instellingen → Apparaten & diensten** en kies je P1/netbron en optionele PV-bron.

De interface verschijnt automatisch. Er is geen aparte Lovelace-resource of dashboard-YAML nodig. Bij een lokaal pakket vervang je uitsluitend `custom_components/solar_pilot`; bewaar bestaande `userfiles` en Home Assistant-opslag.

Controleer bij een waarschuwing de genoemde toestelbron. **Automatische broncontrole** wacht op betrouwbaar nieuwe data en vraagt geen reset. Bij een verkeerde vereiste bronkoppeling corrigeer je die koppeling; een echte **Opdrachtfout** behoudt de bestaande gerichte controle. Zie [docs/BETA53_INSTELLEN.md](docs/BETA53_INSTELLEN.md); verwijder geen configuratie of leerdata.

## 3. Optioneel privéprofiel

Plaats een bestaande installatie-specifieke `private_bundle.json` alleen lokaal in:

```text
/config/custom_components/solar_pilot/userfiles/private_bundle.json
```

Importeer via **SolarPilot → Configureren → Geavanceerd & systeem → Privéprofiel & historiek**. De bundel vult alleen lege, werkelijk bestaande entiteiten in. Fysieke klimaatbediening, fase-afbouw en boilerregeling krijgen hierdoor geen automatische vrijgave. Deel dit bestand niet publiek.

## 4. Boilerwachttijden en gegevensbehoud

Controleer bij extra warm water de twee afzonderlijke wachttijden. **Stabiliteitscontrole** vraagt voortdurend geldig zonnebewijs; **rust tussen doelopdrachten** wacht op de ingestelde minimumtijd sinds de laatste werkelijk verstuurde doelopdracht. Die laatste opdracht kan ook een verlaging of herstel naar het normale doel zijn. Standaard zijn dat respectievelijk 300 en 1800 seconden; bestaande eigen instellingen blijven behouden.

Als de zonnevoorwaarden geldig blijven, mag de stabiliteitscontrole niet telkens opnieuw beginnen alleen omdat de opdrachtrust nog loopt. De kaart toont die echte uitvoeringswachtreden. Zodra beide voorwaarden en alle andere guards voldaan zijn, kan de volgende gewone regelronde de verhoging vragen. Werkelijk verlies van geldig zonnebewijs, koeling of een te groot meetgat kan een nieuwe stabiliteitscontrole vereisen.

Houd **gemeten tanktemperatuur**, **SolarPilot-voorstel** en **gemeld Panasonic-doel** apart. Een voorstel van 60 °C terwijl Panasonic nog 50 °C meldt is geen toegepaste verhoging of fysieke opwarming. Een lopende doelopdracht wacht op haar bestaande nieuwe passende terugmelding; verstuur geen extra proefopdracht om een teller te doen verdwijnen.

### Behouden opdracht- en forecastcontrole

Een pending batterijopdracht laat nieuwe gewone lasten, AEG-deadline-START en vermogensoverdracht wachten. Nieuw passend batterijvermogen van ná de opdracht en daarna nieuw P1-bewijs blijven nodig; ontbrekende rapportage is geen klaarstatus of reden voor een blinde retry. Een verwijderen-voorbereiding vereist werkelijk neutraal batterijvermogen en bij numerieke aansturing een neutraal doel.

Ontbrekende forecasturen of staart blijven onbekend. Controleer tijdzone-/dekkinglabels; een onvolledige dag is geen volledige dagreplay en een werkelijk nultarief blijft nul. Export behoudt schema-sleutels, eenheden en statuswaarden bij consistente pseudoniemen. Een afgebroken start of ongeldige afzonderlijke opslagrij mag geldige andere gegevens niet wissen.

Een handmatig/extern OFF gezette zone blijft OFF tot je zelf AUTO kiest. Ook een harde comfortoverschrijding of verlopen rusttijd mag haar niet automatisch inschakelen. Controleer dat alleen eigen SolarPilot-coast-zones automatisch naar AUTO kunnen terugkeren. Een wachtende of onzekere klimaatopdracht wordt niet opnieuw verstuurd.

Het overzicht moet de huidige benodigde respons, relevante modelzekerheid, modelstatus en werkelijk opgeslagen leeraantallen laten zien. Ontbrekende ongebruikte koelervaring mag een voldoende geleerd verwarmingspad niet blokkeren; een voorspelde behoefte aan koelrespons blijft wel echt bewijs vragen. Winter-/zomercoast blijft standaard uit en weerscontext bewijst geen actieve vraag.

Behoud je huidige instellingen en leerdata. Deze update vraagt geen algemene leerreset. De eerdere bescherming van gecontroleerde fasewaarnemingen zonder bewijs van stabiele andere meters blijft gelden; geldige passieve waarnemingen, nieuwe geïsoleerde fasewaarnemingen en handmatige fasekeuzes blijven behouden. Zie [docs/BETA53_INSTELLEN.md](docs/BETA53_INSTELLEN.md) voor de volledige controle.

## 5. Automatisch herstel na herstart

SolarPilot controleert eerder beheerde toestellen afzonderlijk. Bij ontbrekende, restored of onbeschikbare bediening wordt alleen dat toestel tijdelijk opzijgezet. Er volgt geen blinde OFF en onbekend verbruik wordt niet als nul gerekend. De overige beschikbare toestellen kunnen in de opgeslagen automatische modus verder zodra betrouwbare globale P1- en veiligheidsmetingen en hun eigen voorwaarden dit toelaten. Een eerste installatie zonder opgeslagen Auto-keuze blijft Alleen bekijken.

Het ontbrekende toestel wordt bij volgende gewone regelrondes automatisch opnieuw gecontroleerd. Zodra echte bruikbare status terugkomt, volgt de gewone herbeoordeling: eigen ON wordt zonder nieuwe start herkend; OFF laat het oude eigendom los; een gewijzigd numeriek doel blijft handmatig beschermd. Minimum aan-/uittijden starten conservatief bij de nieuwe waarneming. Deelname en prioriteit worden niet aangepast. Een later bewust gekozen Alleen bekijken of Pauze blijft gelden.

Een onbeschikbaar toestel kan nog steeds stroom gebruiken of later opnieuw gaan vragen. De P1-meting bevat werkelijk huidig verbruik al; SolarPilot houdt daarnaast een conservatieve reserve voor mogelijk niet gemeten of later toenemend verbruik. Daardoor kunnen andere lasten soms nog wachten op echte vermogensruimte. Dat is een veiligheidsbeperking, geen globale opstartblokkering door het ontbreken van één status. Echte opdrachtfouten, een onzekere START, ongeldige globale bronnen en elektrische begrenzing houden hun bestaande bescherming.

Een bronwacht kan ook ontstaan na de herstart. De kaart toont een gerichte automatische controle zonder resetknop. Betrouwbaar bronherstel ruimt de wachtreden automatisch op; **Controle afronden** blijft bedoeld voor een echte fout of vereiste handmatige controle.

De boilercontrole werkt afzonderlijk. Een passend eerder beheerd tankdoel wordt zonder doelwrite herkend; een routinecontrole wacht op verse temperatuur-/doel-/beschermingsbronnen. Een vóór herstart pending opdracht wordt nooit herhaald en vereist voor bevestiging een nieuwe rapportage ná herstart en de bestaande adapterwachttijd. Echte fouten, bewuste handmatige overname of gewijzigd doel blijven beschermd. Een hygiëne-/krachtige fabrikantcyclus behoudt haar doel.

Een onzekere eerdere AEG-START krijgt geen nieuwe START. Alleen een nieuwe betrouwbare fase-terugmelding van ná START voor een lopende of voltooide cyclus kan de specifieke herstartonzekerheid oplossen; een oude Washing/Finished-stand niet. Idle of onduidelijke START-uitkomst leidt niet tot een tweede START. Een tijdelijk ontbrekende bron wordt automatisch opnieuw geprobeerd; een blijvend ontbrekende bron blijft als wachtreden zichtbaar.

Voor oude Alleen bekijken-opslag zonder hervatmarker kan de verloren Auto-keuze éénmalig worden hersteld, uitsluitend zonder echte fout/handmatige boilerbescherming en met een onderbroken lease van een bekend Auto-toestel of schoon routine-boilerjournal. Nieuwe expliciete Alleen bekijken- en Pauze-keuzes blijven beschermd.

## 6. Bronnen en warm water controleren

Controleer in **Alleen bekijken** of **Pauze** de echte adapterherkomst, bronversheid, ruwe klimaat- en taakstatus, gemeld tankdoel, tankmeting, P1/PV, handmatige functies, hygiëne en pending opdrachten.

- Exact geregistreerde `aquarea` met actuele native `idle/off` kan de klimaatguard vrijgeven, ook in AUTO/HEAT_COOL en bij algemene `PUMP`-taakinfo.
- Werkelijke `cooling` blijft extra warmte begrenzen. Werkelijke `heating/preheating/defrosting` houdt de ingestelde ruimtecomfortvoorrang.
- Ontbrekende, oude, restored of onbeschikbare klimaatdata blijft blokkeren. Een taakmelding vervangt geen ontbrekende betrouwbare klimaatbron.
- Oudere `panasonic_cc` in AUTO/HEAT_COOL blijft zonder actuele expliciete `IDLE/WATER`-taak onduidelijk.
- Alleen bewezen koeling verlengt de ingestelde koelrusttijd. Onbekende data maakt geen nieuwe halfuurwachttijd na bronherstel.

Een vóór beta.46 opgeslagen koel-/onzekerheidstijd blijft conservatief behouden. Een bestaande uitloop of bescherming tijdens een native warmwatertaak kan daarom nog tijdelijk gelden; de upgrade wist geen mogelijk echte koeling.

Een grote vrije injectie geeft nog geen startgarantie: zonnestabiliteit, rust tussen doelopdrachten, reserves, eigendom, hygiëne, koeluitloop en elektrische grenzen worden afzonderlijk beoordeeld. Het normale doel blijft standaard 50 °C, de bewaakte comfortgrens 46 °C en extra overschot maximaal 60 °C. Extra 60 °C krijgt nooit Wallboxkrediet.

## 7. Hervatten en doelbevestiging

Gebruik alleen waar nodig de bestaande gerichte boilerreview buiten **Automatisch regelen** en zonder pending opdracht. Zij schrijft zelf geen temperatuur. Een gewone herstartcontrole wordt automatisch afgewerkt; een echte fout of bewuste handmatige overname wordt hierdoor niet gewist.

Hervat gewone regeling na bron- en beveiligingscontrole en observeer een natuurlijke toegestane doelopdracht. Voor exact geregistreerde `aquarea` en `panasonic_cc` blijft minstens tien seconden nodig vóór een passende nieuwe Home Assistant-doelrapportage telt. Ook die rapportage bewijst geen compressorstart of bereikte tanktemperatuur.

Laat concurrerende boilerautomatiseringen uit zolang SolarPilot regelt. AEG-APP-aanvragen en beschermde cycli blijven behouden; maak geen nieuwe APP-aanvraag of START om updateacceptatie af te dwingen. De Wallbox blijft read-only. Nieuwe toestellen blijven afzonderlijk gecontroleerd en vrijgegeven.

## 8. Uitleg en rollback

De enige actuele regelbeschrijving staat in [docs/ACTUELE_WERKING.md](docs/ACTUELE_WERKING.md) en in Home Assistant onder **SolarPilot → Uitleg**. De volledige upgradecontrole staat in [docs/BETA53_INSTELLEN.md](docs/BETA53_INSTELLEN.md).

Voor rollback: **Pauze → beschermde cycli afwerken → onveranderlijke beta.52-release of gecontroleerde back-up herstellen → Home Assistant herstarten → webpagina/app opnieuw openen → backend/kaart en beveiligingen controleren**. Beta.52 behoudt de bronclassificatie en volledige export, maar kan bij een ontbrekende eerder beheerde status nog globaal op de herstartcontrole wachten. Oude release-documenten zijn historische informatie; het actuele `OVERDRACHT.md` beschrijft de huidige bron.
