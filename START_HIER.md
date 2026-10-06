# SolarPilot beta.58 — installatie en upgrade

Beta.58 hervat een gewone opgeslagen Pauze na herstart automatisch zodra de bestaande controles dit toelaten. **Na herstart automatisch hervatten** staat standaard Aan bij de modusknoppen. Alleen bekijken, echte fouten en voorbereiden van verwijderen blijven beschermd. De kaart toont automatisch wachten of een vereiste echte controle.

Alle beta.57-regelingen blijven behouden: één gezamenlijke warmtepompbegroting, extra 60 °C vóór veilige gewone lasten, AUTO vanaf 2500 W restzon, informatie-only sterilisatieplanning en blauwe activiteitsranden. Geldige leerdata, bronkoppelingen, dashboardkeuzes, APP-aanvragen en veiligheid blijven behouden. Er is geen nieuwe rangordemigratie; de bestaande éénmalige beta.57-migratie blijft bij upgrades van oudere versies gelden. Test-/publicatiestatus: [docs/TESTRESULTATEN_BETA58.md](docs/TESTRESULTATEN_BETA58.md).

## 1. Vooraf

- Maak een actuele volledige Home Assistant-back-up en bewaar de gecontroleerde beta.57-release voor rollback.
- Laat een lopende beschermde afwas- of andere cyclus afwerken.
- Gebruik bij een nieuwe installatie **Alleen bekijken** voor de eerste broncontrole. Bij bestaand actief beheer kan die modus eerst **Pauze** en veilige vrijgave vereisen. Alleen bewezen eigen coast en passende bevestigde numerieke batterijdoelen mogen worden vrijgegeven; handmatige bediening blijft beschermd.
- Voor een gewone upgrade is Pauze niet verplicht. Wil je bewust gepauzeerd blijven na de herstart, zet **Na herstart automatisch hervatten Uit**; de standaard Aan vraagt dan juist automatische terugkeer. Deze schakelaar verandert de huidige modus niet.
- Updates zijn cumulatief: bestaande Home Assistant-configuratie en lokale leerdata blijven behouden; tussenliggende beta-versies hoeven niet afzonderlijk geïnstalleerd te worden.

## 2. Via HACS installeren of upgraden

1. Voeg bij een nieuwe installatie in **HACS → Custom repositories** `https://github.com/Stevenva007/solarpilot-home-assistant` toe als type **Integration**.
2. Download of update naar exact `1.0.0-beta.58` zodra die release beschikbaar is.
3. Herstart Home Assistant volledig.
4. Herlaad de webpagina. Stop op Android de Home Assistant-app volledig en open haar opnieuw; op iOS kun je de weergave naar beneden trekken om te verversen. Controleer backendversie en geladen kaart afzonderlijk. Een download of manifestnummer bewijst geen geladen kaartcode.
5. Voeg bij een nieuwe installatie **SolarPilot** toe via **Instellingen → Apparaten & diensten** en kies je P1/netbron en optionele PV-bron.

De interface verschijnt automatisch. Er is geen aparte Lovelace-resource of dashboard-YAML nodig. Bij een lokaal pakket vervang je uitsluitend `custom_components/solar_pilot`; bewaar bestaande `userfiles` en Home Assistant-opslag.

Controleer bij een waarschuwing de genoemde toestelbron. **Automatische broncontrole** wacht op betrouwbaar nieuwe data en vraagt geen reset. Bij een verkeerde vereiste bronkoppeling corrigeer je die koppeling; een echte **Opdrachtfout** behoudt de bestaande gerichte controle. Controleer bij de modusknoppen **Na herstart automatisch hervatten Aan** voor automatische terugkeer. Zie [docs/BETA58_INSTELLEN.md](docs/BETA58_INSTELLEN.md); verwijder geen configuratie of leerdata.

## 3. Optioneel privéprofiel

Plaats een bestaande installatie-specifieke `private_bundle.json` alleen lokaal in:

```text
/config/custom_components/solar_pilot/userfiles/private_bundle.json
```

Importeer via **SolarPilot → Configureren → Geavanceerd & systeem → Privéprofiel & historiek**. De bundel vult alleen lege, werkelijk bestaande entiteiten in. Fysieke klimaatbediening, fase-afbouw en boilerregeling krijgen hierdoor geen automatische vrijgave. Deel dit bestand niet publiek.

## 4. Boilerwachttijden en gegevensbehoud

Controleer bij extra warm water de twee afzonderlijke wachttijden. **Stabiliteitscontrole** vraagt voortdurend geldig zonnebewijs; **rust tussen doelopdrachten** wacht op de ingestelde minimumtijd sinds de laatste werkelijk verstuurde doelopdracht. Die laatste opdracht kan ook een verlaging of herstel naar het normale doel zijn. Standaard zijn dat respectievelijk 300 en 1800 seconden; bestaande eigen instellingen blijven behouden.

Als de zonnevoorwaarden geldig blijven, mag de stabiliteitscontrole niet telkens opnieuw beginnen alleen omdat de opdrachtrust nog loopt. De kaart toont die echte uitvoeringswachtreden. Zodra beide voorwaarden en alle andere guards voldaan zijn, kan de volgende gewone regelronde de verhoging vragen. Werkelijk verlies van geldig zonnebewijs, koeling of een te groot meetgat kan een nieuwe stabiliteitscontrole vereisen.

Houd **gemeten tanktemperatuur**, **SolarPilot-voorstel** en **gemeld Panasonic-doel** apart. Een voorstel is nog geen uitgevoerde verhoging. Een echt gemeld hoger doel krijgt een gestippelde blauwe rand; alleen passend verse opwarmactiviteit krijgt doorlopend blauw. De bekende maandagsterilisatie 12:00/62 °C kan intern blijven zonder doelwijziging; de planning blokkeert geen gewone 60 °C-vraag. Echte gekoppelde hygiene/manual/native-onzekerheid en pending behouden hun afzonderlijke guard.

### Behouden opdracht- en forecastcontrole

Een pending batterijopdracht laat nieuwe gewone lasten, AEG-deadline-START en vermogensoverdracht wachten. Nieuw passend batterijvermogen van ná de opdracht en daarna nieuw P1-bewijs blijven nodig; ontbrekende rapportage is geen klaarstatus of reden voor een blinde retry. Een verwijderen-voorbereiding vereist werkelijk neutraal batterijvermogen en bij numerieke aansturing een neutraal doel.

Ontbrekende forecasturen of staart blijven onbekend. Controleer tijdzone-/dekkinglabels; een onvolledige dag is geen volledige dagreplay en een werkelijk nultarief blijft nul. Export behoudt schema-sleutels, eenheden en statuswaarden bij consistente pseudoniemen. Een afgebroken start of ongeldige afzonderlijke opslagrij mag geldige andere gegevens niet wissen.

Op **Warmte & comfort** staat per zone **Handmatig bedienen**. Uit laat SolarPilot zelf AUTO/UIT kiezen; Aan toont de vaste **AUTO / UIT**-keuze. Die expliciete dashboardoverride blijft bewaard over herstarts tot je Handmatig bedienen weer uit zet. Een native wijziging buiten het dashboard krijgt tijdelijke gebruikersrust, standaard twaalf uur; vaste HEAT/COOL en pending/onzekere opdrachten blijven beschermd. Een geldige oorspronkelijke UIT-stand vraagt onder automatische zonebediening geen handmatige AUTO-fiets.

Gewone comfortvraag controleert **Werkelijk Panasonic-programma**: geen warmtevraagstart bij COOL/AUTO_COOL of koelvraagstart bij HEAT/AUTO_HEAT. Daarnaast mag zonne-AUTO bij 2500 W bruikbaar restoverschot na 60 s en nieuwe P1/PV zonder thermische vraag of modelscore. Het programma moet bekend en vers zijn; UIT is bekende context. Alleen bevestigd eigen zonne-AUTO houdt vanaf 2000 W met eenmaal verse gedeelde warmtepompstroom, begrensd door echte PV. Dashboardkeuze, externe rust, minimumtijden en bron-/opdrachtbescherming blijven leidend. HA AUTO/UIT kan door de integratie globaal worden vertaald; geen ongewijzigd programma garanderen.

Een passieve UIT-trend mag geen actief verwarm-/koelverloop gebruiken; actueel buitenbewijs bepaalt de huidige richting. Zachte nieuwe AUTO-vraag vanuit UIT moet standaard tien minuten aanhouden. Harde of onderbouwd dringende comfortvraag behoudt haar bestaande herstelpad. Het overzicht noemt **Comfortbewaking tijdens leren** of **Voorspellend geregeld**, per-zone reden en echte forecastdekking. Actuele passende comfortvraag werkt zonder volledig geleerd model. Leerbewijs, relevante dagen/episodes en gemeten voorspelfout blijven afzonderlijk; samples bewijzen geen 98% nauwkeurigheid. Winter-/zomerweer houdt AUTO niet alleen wegens die context aan. Een toekomstige hittegolf vraagt relevant koelbewijs en echte forecasturen; AUTO met ongewijzigd doel garandeert geen bouwschilvoorkoeling.

Behoud je huidige instellingen en leerdata. Deze update vraagt geen algemene leerreset. De eerdere bescherming van gecontroleerde fasewaarnemingen zonder bewijs van stabiele andere meters blijft gelden; geldige passieve waarnemingen, nieuwe geïsoleerde fasewaarnemingen en handmatige fasekeuzes blijven behouden. Zie [docs/BETA58_INSTELLEN.md](docs/BETA58_INSTELLEN.md) voor de volledige controle.

## 5. Automatisch herstel na herstart

Een gewone opgeslagen **Pauze** vraagt met **Na herstart automatisch hervatten Aan** bij de volgende Home Assistant-herstart of integratieherlading automatisch **Automatisch regelen** via de bestaande controles. Met Uit blijft Pauze staan; een al opgeslagen automatische modus houdt haar normale herstelroute. Alleen bekijken en een eerste installatie blijven Alleen bekijken. De schakelaar verandert de huidige modus niet. Opnieuw Pauze kiezen annuleert een nu wachtende hervatting; bij de volgende herstart geldt de voorkeur weer.

Interne fouten en voorbereiden van verwijderen bewaren een afzonderlijke pauzeoorzaak en reden en hervatten niet automatisch. Bekende opdrachtfouten, onzekere eerdere opdrachten en vereiste boilerbeoordeling blijven beschermd. Een gezonde volgende meetronde wist een interne foutreden niet. Oudere beta.57-Pauze heeft geen opgeslagen oorzaak; daar kan SolarPilot uitsluitend een gewone beveiligde hervatting proberen, geen vroegere handmatige/foutoorzaak bewijzen.

SolarPilot controleert eerder beheerde toestellen afzonderlijk. Bij ontbrekende, restored of onbeschikbare bediening wordt alleen dat toestel tijdelijk opzijgezet. Er volgt geen blinde OFF en onbekend verbruik wordt niet als nul gerekend. De overige beschikbare toestellen kunnen in de opgeslagen automatische modus verder zodra betrouwbare globale P1- en veiligheidsmetingen en hun eigen voorwaarden dit toelaten. Een eerste installatie zonder opgeslagen Auto-keuze blijft Alleen bekijken.

Het ontbrekende toestel wordt bij volgende gewone regelrondes automatisch opnieuw gecontroleerd. Zodra echte bruikbare status terugkomt, volgt de gewone herbeoordeling: eigen ON wordt zonder nieuwe start herkend; OFF laat het oude eigendom los; een gewijzigd numeriek doel blijft handmatig beschermd. Minimum aan-/uittijden starten conservatief bij de nieuwe waarneming. Deelname en prioriteit worden niet aangepast. Alleen bekijken blijft gelden; Pauze stopt de actuele hervatting en volgt bij een volgende herstart de zichtbare voorkeur.

Een onbeschikbaar toestel kan nog steeds stroom gebruiken of later opnieuw gaan vragen. De P1-meting bevat werkelijk huidig verbruik al; SolarPilot houdt daarnaast een conservatieve reserve voor mogelijk niet gemeten of later toenemend verbruik. Daardoor kunnen andere lasten soms nog wachten op echte vermogensruimte. Dat is een veiligheidsbeperking, geen globale opstartblokkering door het ontbreken van één status. Echte opdrachtfouten, een onzekere START, ongeldige globale bronnen en elektrische begrenzing houden hun bestaande bescherming.

Een bronwacht kan ook ontstaan na de herstart. De kaart toont een gerichte automatische controle zonder resetknop. Betrouwbaar bronherstel ruimt de wachtreden automatisch op; **Controle afronden** blijft bedoeld voor een echte fout of vereiste handmatige controle.

De boilercontrole werkt afzonderlijk. Een passend eerder beheerd tankdoel wordt zonder doelwrite herkend; een routinecontrole wacht op verse temperatuur-/doel-/beschermingsbronnen. Een vóór herstart pending opdracht wordt nooit herhaald en vereist voor bevestiging een nieuwe rapportage ná herstart en de bestaande adapterwachttijd. Echte fouten, bewuste handmatige overname of gewijzigd doel blijven beschermd. Een hygiëne-/krachtige fabrikantcyclus behoudt haar doel.

Een onzekere eerdere AEG-START krijgt geen nieuwe START. Alleen een nieuwe betrouwbare fase-terugmelding van ná START voor een lopende of voltooide cyclus kan de specifieke herstartonzekerheid oplossen; een oude Washing/Finished-stand niet. Idle of onduidelijke START-uitkomst leidt niet tot een tweede START. Een tijdelijk ontbrekende bron wordt automatisch opnieuw geprobeerd; een blijvend ontbrekende bron blijft als wachtreden zichtbaar.

Voor oude Alleen bekijken-opslag zonder hervatmarker kan de verloren Auto-keuze éénmalig worden hersteld, uitsluitend zonder echte fout/handmatige boilerbescherming en met een onderbroken lease van een bekend Auto-toestel of schoon routine-boilerjournal. Nieuwe expliciete Alleen bekijken-keuzes blijven beschermd. De Pauze-regel staat hierboven.

## 6. Bronnen en warm water controleren

Controleer in **Alleen bekijken** of **Pauze** de echte adapterherkomst, bronversheid, ruwe klimaat- en taakstatus, gemeld tankdoel, tankmeting, P1/PV, handmatige functies, hygiëne en pending opdrachten.

- Exact geregistreerde `aquarea` met actuele native `idle/off` kan de klimaatguard vrijgeven, ook in AUTO/HEAT_COOL en bij algemene `PUMP`-taakinfo.
- Werkelijke `cooling` blijft extra warmte begrenzen. Werkelijke `heating/preheating/defrosting` houdt de ingestelde ruimtecomfortvoorrang.
- Ontbrekende, oude, restored of onbeschikbare klimaatdata blijft blokkeren. Een taakmelding vervangt geen ontbrekende betrouwbare klimaatbron.
- Oudere `panasonic_cc` in AUTO/HEAT_COOL blijft zonder actuele expliciete `IDLE/WATER`-taak onduidelijk.
- Alleen bewezen koeling verlengt de ingestelde koelrusttijd. Onbekende data maakt geen nieuwe halfuurwachttijd na bronherstel.

Een vóór beta.46 opgeslagen koel-/onzekerheidstijd blijft conservatief behouden. Een bestaande uitloop of bescherming tijdens een native warmwatertaak kan daarom nog tijdelijk gelden; de upgrade wist geen mogelijk echte koeling.

Extra warm water start standaard vanaf 3000 W bruikbaar overschot; exacte grens telt. De vroegere drempelmigratie blijft éénmalig, eigen waarden blijven. Veilige lager geplaatste eigen onderbreekbare lasten mogen wijken na stabiliteit, echte UIT-bevestiging, nieuwe P1 en verse PV. Afwas, ruimteklimaat en Wallbox worden hiervoor niet gestopt. De raming van 3200 W wordt niet verlaagd. Controleer de W/kW-bron en **Wat meet deze vermogensmeter?**: standaard hele warmtepomp, exclusieve boiler alleen bij echte tankmeter. P1 bevat gezamenlijke stroom al eenmaal; een gedeelde meter bewijst geen specifieke tankopwarming. Stabiliteit, opdrachtrust, reserves, koeling, eigendom en elektrische/fabrikantgrenzen blijven afzonderlijk gelden.

## 7. Hervatten en doelbevestiging

Gebruik alleen waar nodig de bestaande gerichte boilerreview buiten **Automatisch regelen** en zonder pending opdracht. Zij schrijft zelf geen temperatuur. Een gewone herstartcontrole wordt automatisch afgewerkt; een echte fout of bewuste handmatige overname wordt hierdoor niet gewist.

Hervat gewone regeling na bron- en beveiligingscontrole en observeer een natuurlijke toegestane doelopdracht. Voor exact geregistreerde `aquarea` en `panasonic_cc` blijft minstens tien seconden nodig vóór een passende nieuwe Home Assistant-doelrapportage telt. Ook die rapportage bewijst geen compressorstart of bereikte tanktemperatuur.

Laat concurrerende boilerautomatiseringen uit zolang SolarPilot regelt. AEG-APP-aanvragen en beschermde cycli blijven behouden; maak geen nieuwe APP-aanvraag of START om updateacceptatie af te dwingen. De Wallbox blijft read-only. Nieuwe toestellen blijven afzonderlijk gecontroleerd en vrijgegeven.

## 8. Analyse, uitleg en rollback

Kies **Export → Export samenstellen → 7 dagen** voor de volledige beschikbare analyse als **JSON.GZ**. Alleen dezelfde ingelogde beheerder kan de lokale gecomprimeerde download tien minuten ophalen. De nieuwe route verkort de periode niet wegens de vroegere 16 MB-berichtgrens. Nieuwe punten bewaren de geladen versie; oudere ongestempelde punten blijven versie onbekend. Privacyfilters blijven behouden; publiceer analyses niet op GitHub.

De enige actuele regelbeschrijving staat in [docs/ACTUELE_WERKING.md](docs/ACTUELE_WERKING.md) en in Home Assistant onder **SolarPilot → Uitleg**. De volledige upgradecontrole staat in [docs/BETA58_INSTELLEN.md](docs/BETA58_INSTELLEN.md).

Voor rollback die bewust gepauzeerd blijft: **Na herstart automatisch hervatten Uit → Pauze → beschermde cycli afwerken → onveranderlijke beta.57-release of passende volledige back-up herstellen → Home Assistant herstarten → webpagina/app opnieuw openen → backend/kaart en beveiligingen controleren**. Beta.57 bewaart Pauze over herstarts en gebruikt de nieuwe hervatvoorkeur/pauzereden niet. Bij later opnieuw installeren van beta.58 kan de opgeslagen voorkeur weer gelden. Programmabestanden herstellen eerdere opslag niet vanzelf; herstel voor exact herstel de volledige bijbehorende back-up. Oude releasedocumenten blijven historie; `OVERDRACHT.md` beschrijft de huidige bron.
