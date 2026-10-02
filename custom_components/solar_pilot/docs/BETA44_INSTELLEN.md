# SolarPilot 1.0.0-beta.44 — instellen, controleren en rollback

Beta.44 is een cumulatieve transparantie- en vermogensverdelingsrelease. Zij laat een verse, expliciet afwezige Wallbox-laadvraag geen vermogen reserveren, maakt de werkelijke starttoewijzing per toestel zichtbaar en vervangt het algemene 60 °C-blok bij een voorkeurs-afwasmachine door een conservatieve, proportionele reservering. De aanvullende boilerbewaking negeert een onmiddellijke optimistische doelterugmelding als opdrachtbevestiging, toont gemeld en voorgesteld doel afzonderlijk en ondersteunt een expliciet gekoppelde native warmtepomptaak. De Wallbox blijft volledig read-only en alle APP-, boiler-, klimaat- en elektrische beveiligingen blijven vereist.

## Bewezen uitgangspunt

**1.0.0-beta.44** is op 2 oktober 2026 gepubliceerd onder de onveranderlijke tag `v1.0.0-beta.44`, commit `5bbfa16cbc9453a818fb825fe16c447792ed63a2`. Validate-workflow `37022762657` is geslaagd; beide ZIP-pakketten zijn gecontroleerd tegen die tag. HACS-installatie, groene Home Assistant-configuratiecontrole, volledige herstart en geladen backend/vernieuwde kaart zijn afzonderlijk bevestigd op Core 2026.9.4.

Na herstart zijn de nieuwe doelweergave en behouden bescherming bevestigd. Native taakbron, afzonderlijke maandagdeadline en gerichte review zijn via de normale bediening gecontroleerd, zonder nieuwe APP-aanvraag of fysieke proefstart. Een vroege bevestiging vóór tien seconden gebruikte echter `ha_state`: de gecontroleerde Aquarea Smart Cloud 1.0.61-adapter heet `aquarea`, terwijl beta.44 alleen `panasonic_cc` herkent. De installatie is daarom voor beta.45-controle gepauzeerd. Dit is geen livebewijs van de tienseconden-guard; een geladen interface bewijst geen fysieke regelacceptatie.

De beta.44-softwarecontrole behaalde **1760 Python-tests in 11.68 s** en **veertien browsercontroles**. GitHub-CI, tag, releasepakketten, publicatie, HACS-installatie en geladen backend/kaart zijn afzonderlijk bevestigd. De aangetoonde ACK-adaptermismatch vraagt beta.45; haar afzonderlijke softwaregate is groen met 1773 tests en veertien browsercontroles, maar publicatie, installatie en latere live-doelrapportage blijven open. Pakketchecks/SHA-256 staan in `TESTRESULTATEN_BETA44.md`; beta.44-tags en release-assets worden niet vervangen.

Het SolarPilot-logo is in het Home Assistant/HACS-updatevenster bevestigd via ondersteunde lokale brandsproxy-customisatie en uitsluitend een update-entiteit-opvraag; geen HACS-codepatch of warmtepompcommando. Opslaan en teruglezen van de afzonderlijke maandagdeadline zijn getest, zonder hier een persoonlijk schema te publiceren. Gemeten afwascyclusleren blijft uit zonder geschikte exclusieve W-meter.

Een versleutelde volledige Home Assistant-back-up op de toegestane NAS is gereed bevestigd. Er is geen herstelproef uitgevoerd; maak voor een volgende installatie een actuele back-up.

## Vooraf

1. Wacht tot beta.44 werkelijk als SolarPilot-release beschikbaar is; installeer geen lokale conceptbron over de live installatie.
2. Maak een volledige Home Assistant-back-up.
3. Kies bij voorkeur een moment zonder actieve beschermde cyclus. Laat een lopende AEG-beurt normaal afwerken en gebruik geen STOPRESET om voor de update ruimte te maken.
4. Noteer de globale modus, per-toestelmodus, actuele APP-aanvraag, boilerstatus en Wallbox-status.
5. Laat de installatie-specifieke afgeleide Wallbox-bron alleen waarden publiceren die door verse fysieke status-, vermogens- en rapportagebronnen zijn gedekt. Houd private entity-id's buiten publieke bestanden.

## Upgrade naar de gepubliceerde beta.44

1. Installeer exact `1.0.0-beta.44` via de bestaande HACS-repository.
2. Herstart Home Assistant volledig.
3. Controleer in SolarPilot dat de werkelijk geladen backendversie `1.0.0-beta.44` is.
4. Vernieuw de browser geforceerd en controleer afzonderlijk dat ook de kaart beta.44 toont.
5. Begin de nieuwe controles in **Alleen bekijken** of **Pauze**. Herstel **Automatisch regelen** pas nadat de actuele boiler-, klimaat-, AEG- en Wallbox-toestand klopt.
6. Staat de boilerregeling beschermd stil, controleer eerst tankmeting, gerapporteerd doel, native hygiëne-/krachtige-/handmatige functies en eventuele wachtende opdracht. Gebruik pas daarna buiten **Automatisch regelen** de bestaande knop **Automatische boilerregeling hervatten**. De knop schrijft zelf geen temperatuur en start geen regelcyclus; de update mag deze review niet automatisch vervangen.

## Boilerdoel en warmtepomptaak

Beta.44 past de latere doelbevestiging uitsluitend op exact geregistreerd `panasonic_cc` toe. De gecontroleerde adapter `aquarea` 1.0.61 publiceert ook optimistisch, maar viel buiten deze herkenning en kreeg een vroege generieke `ha_state`. Beta.45 corrigeert dit exacte domein; beschouw een bevestiging vóór tien seconden niet als guardbewijs. Ook een latere HA-waarneming kan cloudcache zijn en bewijst geen onafhankelijk apparaatbericht, compressoractiviteit of bereikte tanktemperatuur.

Het dashboard toont het **gemelde doel** vóór een eventueel **voorgesteld doel**. Wanneer de regeling stil staat, staat die pauze zichtbaar bij de boiler. Een gewenst doel van 55 °C betekent niet dat de tank al 55 °C is of dat SolarPilot het doel werkelijk heeft toegepast.

Voor adapters waarbij Panasonic AUTO een inactieve `hvac_action` kan tonen ondanks mogelijk ruimtebedrijf, koppel je optioneel **Gemelde warmtepomptaak/richting (alleen lezen)** van dezelfde warmtepomp. De generieke configuratiesleutel is `space_activity_entity`; de afzonderlijke waardelijsten zijn `space_activity_active_states` en `space_activity_inactive_states`. Voor de gecontroleerde native richting betekenen `PUMP` gemeld ruimtebedrijf en `IDLE;WATER` geen gemeld ruimtebedrijf. Controleer deze semantiek bij de werkelijk gebruikte bron; lijsten moeten niet-leeg zijn en mogen niet overlappen. De koppeling wordt niet automatisch ontdekt of hardgecodeerd.

Een verse `PUMP`-rapportage houdt de extra zonnebuffer tegen, zonder HEAT of COOL te kiezen. `WATER` is een gemelde tapwatertaak, geen bewijs van exclusief compressorvermogen. Een gekoppelde bron die ontbreekt, oud, hersteld, onbekend of tegenstrijdig is, verleent geen buffertoestemming. Zonder zo'n bron blijft de bekende Panasonic-AUTO-blinde vlek beschermd. De bestaande koel-, comfort-, eigendoms-, hygiëne- en elektrische grenzen blijven daarnaast gelden.

Powerful wordt in beta.44 niet automatisch als boilerboost ingezet. De Panasonic K T-CAP-servicehandleiding beschrijft deze functie voor ruimteverwarming, niet als bewezen tapwaterboost; ook de afzonderlijke installateursinstelling DHW capacity blijft ongewijzigd. Zie [Panasonic-servicehandleiding PAPAMY2310071CE §14.11](https://paltaja.lt/wp-content/uploads/panasonic-k-t-cap-manual.pdf).

## Wallbox zonder actuele laadvraag

SolarPilot reserveert geen EV-vermogen wanneer alle volgende informatie vers en geldig is:

- het gemeten laadvermogen ligt onder de ingestelde laaddrempel; en
- de bron meldt expliciet geen laadvraag, geen verbonden auto of een bekende inactieve status.

Alleen nul of laag vermogen is onvoldoende. Een oude, onbekende, herstelde of strijdige bron blijft fail-closed. Een actieve gemeten laadvraag blijft leidend. Deze regel verandert uitsluitend SolarPilots vermogensbegroting en uitleg; SolarPilot verstuurt geen start-, stop-, modus-, fase- of laadstroomopdracht naar de Wallbox.

De standaard zonnelaadstatussen bevatten nu ook **Zonne-auto · wacht op auto**. Een opgeslagen lijst die exact de oude standaardwaarden bevat, wordt bij het lezen compatibel met die nieuwe waarde. Een eigen aangepaste lijst wordt niet stil uitgebreid. Een herkende tekst verleent bovendien alleen zonneclassificatie wanneer de native laadmodus werkelijk Full Solar is.

## Werkelijke toewijzing per toestel

De startuitleg toont twee verschillende grootheden:

- de actuele vrije zonnestroom na de algemene huis- en batterijreserve; en
- het vermogen dat na hogere prioriteiten, comfort- en cyclusreserves en nog niet verbruikte toezeggingen werkelijk voor dit toestel is toegewezen.

Die tweede waarde komt uit dezelfde engineberekening als het startbesluit. **Benodigd**, **beschikbaar voor dit toestel** en **voldoende/onvoldoende** moeten dus bij elkaar passen. Een groene algemene checklist is geen startgarantie wanneer de effectieve toewijzing te klein is; de actuele beslisreden blijft leidend.

## AEG en extra 60 °C

Een startklare APP-aanvraag die aantoonbaar in de veilige startpool past, krijgt één startkans vóór de optionele 60 °C-buffer. De bestaande voorwaarden blijven verplicht: een nieuwe fysieke overgang naar exact `Enabled`, gesloten deur, Ready To Start, geldig programma, actuele verbinding, bruikbare alarmcontrole indien gekoppeld, één START per belading en voldoende elektrische ruimte.

Een al lopende AEG-beurt blokkeert 60 °C niet meer categorisch. Zonder exclusieve afwasmachinemeter reserveert SolarPilot het ingestelde nominale AEG-vermogen conservatief. Daarnaast worden huisreserve, batterijontlading en nog niet verbruikte toesteltoezeggingen afgetrokken. De bruikbare ruimte wordt begrensd door de actuele én gefilterde netmeting en door de werkelijke PV-productie. Alleen wanneer daarna nog meer dan de ingestelde 60 °C-overschotdrempel overblijft, mag die buffer naast de lopende beurt werken. Bij actieve kwartierpiekbewaking moet een nieuwe of onbevestigde native boilerherstart ook het geschatte boilervermogen in de geldige piekruimte passen; een bewezen reeds actieve, door SolarPilot beheerde 60 °C-verwarming wordt niet dubbel gereserveerd.

Wallboxvermogen telt nooit mee voor extra 60 °C. Gewoon warmwatercomfort, avondvoorraad binnen de ingestelde limiet en maximaal 55 °C, koeling, fabrikantsterilisatie en overige beveiligingen blijven afzonderlijk leidend. Een lopende afwasbeurt wordt nooit onderbroken.

## Geïntegreerde optieswizard

De geïntegreerde wizard leest bij opslaan alleen de benoemde invoervelden in het actuele formulier. Daardoor blijft opslaan werken in Home Assistant-frontends waarin de algemene `form.elements`-verzameling niet is geïmplementeerd. Browservalidatie, de native Home Assistant-optiesflow, live/deferred toestelbeveiliging en servervalidatie blijven ongewijzigd. Een leesfout geeft zichtbare feedback en bewaart niets.

## Maandagdeadline en APP-ticket

Beta.44 verandert de bestaande keuze niet automatisch. Een lege maandagdeadline gebruikt de gewone deadline, standaard 13:00. Alleen een bewust opgeslagen 10:00 geldt op maandag; de andere dagen blijven ongewijzigd. Bestaande APP-tickets worden door upgrade of herstart niet herberekend of opnieuw gewapend. Alleen een expliciete keuze om dezelfde geplande dag aan te passen mag een bestaand verzoek herberekenen, zonder nieuw ticket of START.

## Liveacceptatie na installatie

- Backend en kaart tonen werkelijk `1.0.0-beta.44` na volledige herstart en cache-refresh.
- Een verse native toestand zonder laadvraag en met laag vermogen toont geen EV-reservering; oud of onbekend blijft fail-closed.
- **Zonne-auto · wacht op auto** wordt alleen als zonne-autosessie herkend samen met native Full Solar. Een bewust aangepaste waardelijst blijft ongewijzigd.
- De startuitleg toont dezelfde effectieve toewijzing als de engine en houdt ruwe vrije injectie daarvan gescheiden.
- Een lopende AEG-beurt reserveert conservatief vermogen, maar is geen algemeen 60 °C-verbod. Forceer geen fysieke 60 °C- of afwasproef; observeer een natuurlijk passend venster.
- Opslaan via **Configureren met uitleg ?** rondt de native optiesflow af of geeft een duidelijke fout; het mag geen directe toestelopdracht uitvoeren.
- Het boileroverzicht scheidt tankmeting, gerapporteerd doel, voorgesteld doel en eventuele beschermende pauze. Een onmiddellijke optimistische doelterugmelding geldt niet als opdrachtbevestiging.
- De gekoppelde native taakbron wordt uitsluitend gelezen. Gemeld ruimtebedrijf of onbruikbare/tegenstrijdige informatie blokkeert de extra zonnebuffer; `WATER` wordt niet als elektrisch meetbewijs getoond. Forceer geen klimaat- of boileropdracht om deze uitleg te testen.
- Een bestaande beschermende boilerpauze wordt niet door installatie of herstart stil opgeheven. Een gerichte review blijft een afzonderlijke, gecontroleerde handeling.
- Maandag 10:00 blijft een bewuste, afzonderlijke installatiekeuze en wordt niet door de update toegepast.

Deze punten zijn acceptatiestappen, geen claims dat zij al op de echte beta.44-installatie zijn uitgevoerd.

## Rollback

1. Zet SolarPilot op **Pauze**.
2. Laat een lopende beschermde cyclus afwerken; verstuur geen STOPRESET vanuit SolarPilot.
3. Herstel de volledige back-up of installeer de onveranderlijke beta.43-release opnieuw.
4. Herstart Home Assistant en controleer de werkelijk geladen backend- en kaartversie.
5. Controleer APP-ticket, centrale Voorrang, maandagdeadline, DHW-/klimaateigendom en Wallbox fail-closed gedrag voordat je **Automatisch regelen** opnieuw gebruikt.

Zie `TESTRESULTATEN_BETA44.md` voor de werkelijk uitgevoerde en nog open controles.
