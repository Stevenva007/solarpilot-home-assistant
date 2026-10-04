# SolarPilot 1.0.0-beta.54 — instellen en controleren

Beta.54 regelt vrijgegeven Panasonic-ruimtezones afzonderlijk tussen AUTO en UIT. SolarPilot kan de woning zonder onnodig ruimtebedrijf op temperatuur laten blijven en AUTO weer beschikbaar stellen wanneer actuele of verantwoord voorspelde behoefte dit vraagt. Een native UIT-stand hoeft niet eerst handmatig op AUTO te worden gezet. Panasonic blijft eigenaar van verwarmen/koelen en het thermostaatdoel blijft behouden.

## Bronbasis en gegevensbehoud

De codebasis is de gepubliceerde beta.53 op commit `de4e7f364789ec486447b2c6ee5dce4cbabcbdb3`, tree `ea793e13fa35b8327c269f6754a76ef4c561ed72`. Haar onveranderlijke release, workflow `37215861144` en gecontroleerde pakketten zijn de rollbackbasis. Updates zijn cumulatief: geldige instellingen, koppelingen, centrale prioriteit, modellen, historiek en APP-aanvragen blijven behouden. De beta.53-isolatie van onbeschikbare toestellen en conservatieve vermogensreserves blijven gelden.

## Upgrade

1. Maak een actuele volledige Home Assistant-back-up en bewaar de gecontroleerde beta.53-release.
2. Laat beschermde afwas- of andere cycli afwerken. Gebruik geen STOPRESET voor de update.
3. Installeer exact `1.0.0-beta.54` via HACS zodra de release beschikbaar is, of vervang uitsluitend `custom_components/solar_pilot` met het lokale pakket. Behoud bestaande `userfiles` en Home Assistant-opslag.
4. Herstart Home Assistant volledig. Herlaad de webpagina; op Android stop je de Home Assistant-app volledig en open je haar opnieuw, op iOS kun je de weergave naar beneden trekken om te verversen.
5. Controleer backendversie en geladen kaart afzonderlijk. Open **Uitleg** en controleer beta.54 en de bijbehorende actuele regel-hash. Een download of manifestnummer bewijst geen geladen kaartcode.

SolarPilot registreert de frontend zelf. Een extra Lovelace-resource, www-bestand of dashboard-YAML is niet nodig. De definitieve regel-hash en softwaregate worden vastgelegd in `TESTRESULTATEN_BETA54.md`.

## Automatische ruimtebediening

De klimaatmodule moet ingeschakeld zijn, fysieke klimaatbediening moet vrijgegeven zijn en de globale modus moet **Automatisch regelen** zijn. **Ruimtes automatisch AUTO of UIT** staat standaard aan binnen die bestaande voorwaarden; deze instelling verleent geen rechten aan een niet vrijgegeven module. Een geldige actuele UIT-zone doet vanzelf mee. Er is geen terugkerende handmatige AUTO-actie nodig.

| Dashboardkeuze per zone | Werking |
| --- | --- |
| **Handmatig bedienen: Uit** | SolarPilot beoordeelt deze zone zelf en kiest AUTO of UIT onder de normale bron-, opdracht- en comfortvoorwaarden. |
| **Handmatig bedienen: Aan**, **AUTO / UIT: AUTO** | Deze zone blijft handmatig op AUTO tot je Handmatig bedienen weer uit zet. Panasonic kiest zelf of er werkelijk verwarmd/gekoeld wordt. |
| **Handmatig bedienen: Aan**, **AUTO / UIT: UIT** | Deze zone blijft handmatig UIT tot je Handmatig bedienen weer uit zet. Een comfortwaarschuwing heft deze keuze niet op. |
| **Handmatig bedienen weer Uit** | De bewaarde dashboardoverride wordt opgeheven. De volgende gewone regelbeoordeling bepaalt de gewenste stand; dit reset geen echte fout en verstuurt zelf geen opdracht. |

Deze schakelaars staan onder **Warmte & comfort** bij iedere ruimte. Handmatige AUTO/UIT-bediening loopt via het SolarPilot-dashboard. Een buiten dit dashboard gewijzigde native AUTO/UIT-stand krijgt de ingestelde tijdelijke gebruikersrust, standaard twaalf uur. Een vaste Panasonic HEAT- of COOL-stand wordt niet automatisch gewijzigd. Wie expliciet automatische zonebediening uitschakelt, behoudt de oudere werkwijze met handmatige native vrijgave.

Een expliciete dashboardoverride blijft bewaard over herstarts. Een onbeschikbare zone, pending opdracht of echte fout geeft geen recht om toch een nieuwe moduswrite te sturen. Terugkeren naar automatisch blijft mogelijk als instelling, maar wist de bestaande fout of onzekere opdracht niet.

## Wat doet SolarPilot zonder een volledig geleerd model?

**Comfortbewaking tijdens leren** gebruikt de verse werkelijke temperatuur en passende comfortvraag. De regeling hoeft niet op een volledig geleerd koelmodel te wachten om echte verwarmingsbehoefte te herkennen. AUTO blijft niet permanent aan alleen omdat de voorspelling winter-/zomercontext aangeeft. Een warme ruimte die zonder bedrijf veilig naar haar doel afkoelt krijgt niet uitsluitend wegens koud toekomstig buitenweer een koelvraag.

**Voorspellend geregeld** gebruikt voldoende relevant leerbewijs voor passieve temperatuurontwikkeling, zon waar toegepast, de benodigde verwarm-/koelrespons en reactievertraging. Per zone wordt bepaald of UIT veilig is en wanneer AUTO weer beschikbaar moet zijn. Een behoefte in een tweede ruimte laat een veilige woonkamer niet automatisch mee inschakelen.

Gewone veranderingen respecteren de minimum aan-/uittijd, standaard één uur, en opdrachtfrequentie. Een echte of verantwoord voorspelde urgente comfortbehoefte kan gewone wachttijd voor automatisch herstel doorbreken. Handmatige keuze, tijdelijke gebruikersrust, bron-/fabrikantbescherming en pending/onzekere opdrachten blijven leidend. Nieuwe passende Home Assistant-rapportage bevestigt een opdracht; een lokale echo of het verstrijken van een timer bewijst geen fysieke stand.

Bij een onzekere klimaatopdracht kun je op het dashboard **Gemelde stand behouden** kiezen zodra de bron weer betrouwbaar is. Dit neemt de gemelde AUTO/UIT-stand over als vaste handmatige keuze en beoordeelt uitsluitend die fout; het verstuurt geen modeopdracht. Keer daarna bewust terug naar automatische regeling of gebruik de handmatige AUTO/UIT-schakelaar. Ontbrekende bronnen en pending opdrachten kunnen niet zo worden omzeild.

## Praktisch leren en voorspellen

1. Controleer per zone actuele ruimtetemperatuur, native doel en bruikbare `hvac_action`; controleer daarnaast de geselecteerde °C-buitenbron en uurforecast. Bij ingeschakelde zonnewinst moet actuele PV-data bruikbaar zijn.
2. Laat gewone comfortabele AUTO- en UIT-perioden ontstaan. Extreme proefstanden, onnodig koelen en leerdata wissen verhogen de modelzekerheid niet.
3. Bekijk de afzonderlijke leergegevens voor passief, verwarmen, koelen en vertraging. Samples en relevante dagen/episodes tonen waarnemingsdekking; verwarmen en koelen vragen eigen consistente metingen en eigen dagen. Zij zijn geen procent voorspelnauwkeurigheid.
4. Vergelijk aangekondigde temperaturen tijdens UIT met latere echte metingen en de afzonderlijke voorspelfout. Gemiddelde absolute fout in °C wordt per passief-/verwarm-/koelpad op de volgende echte meting over vijftien tot negentig minuten gecontroleerd. Dit bewijst geen 48-uursnauwkeurigheid of bouwschilmassa; ontbrekende foutmetingen blijven onbekend.
5. Laat werkelijke koelervaring pas meetellen als Panasonic echt koelt. Passieve of verwarmingsmetingen bewijzen geen koelrespons. Echte uiteenlopende meetdagen en bevestigde UIT-feedback maken de regeling bruikbaarder.

De ingestelde horizon is standaard maximaal 48 uur. Alleen werkelijke opeenvolgende beschikbare forecasturen worden beoordeeld; een gat of ontbrekende staart blijft onbekend. Vijf uur data wordt niet voorgesteld als twee dagen vooruitkijken.

Bij een voorspelde hittegolf gebruikt een geleerd langzaam koelpad meer voorbereidingstijd dan een snel pad. Maar 40 °C buiten over twee dagen bewijst niet dat de bouwschil nu twee dagen moet worden gekoeld. AUTO met ongewijzigd doel kan idle blijven of door Panasonic anders worden ingevuld. Doelbewuste bouwschilvoorconditionering vraagt afzonderlijk bewijs van opgeslagen warmte en nawerking over meerdere warme dagen; deze update claimt die fysieke garantie niet en verandert geen ruimte-doeltemperatuur of HEAT/COOL-keuze.

## Behouden veiligheid en diagnose

Onbeschikbare gewone toestellen worden afzonderlijk beschermd en bij betrouwbare terugkeer automatisch opnieuw beoordeeld; onbekend huidig/toekomstig verbruik levert geen vrije vermogenscredit op. Bronversheid, echte P1/PV, fase-/piekgrenzen, beschermde afwascycli, boilerdoelbevestiging, hygiëne en volledig read-only Wallbox blijven behouden. Er wordt geen Force DHW, Powerful, extra APP-aanvraag of algemene datareset toegevoegd.

Zonnestabiliteit en rust sinds de laatste werkelijk verstuurde boilerdoelopdracht blijven afzonderlijk lopen. Warmwateradvies, native doel en tanktemperatuur blijven afzonderlijk zichtbaar. De nieuwe ruimtebediening schrijft geen tankdoel buiten het bestaande boilerbeleid.

Gebruik bij onduidelijk gedrag **Export → Export samenstellen** voor een nieuwe actuele analyse. Controleer per zone de bediening, actuele bronnen, voorstel, wachtreden, leerbewijs en werkelijke forecastdekking. Privacyfilters en pseudoniemen blijven behouden; publiceer privé-analyses niet op GitHub.

## Teststatus en rollback

De definitieve softwaregate staat in `TESTRESULTATEN_BETA54.md`. HA-API-/DOM-doubles bewijzen softwaregedrag, geen fysieke respons of live installatie. In deze werksessie is geen live Home Assistant-toegang of fysieke toestelactie uitgevoerd.

Rollback: **Pauze → beschermde cycli afwerken → onveranderlijke beta.53-release of gecontroleerde volledige back-up herstellen → Home Assistant herstarten → webpagina/app opnieuw openen → backend/kaart, bronnen, eigendom en beveiligingen controleren**. Beta.53 behoudt toestelisolatie en reserves, maar kent de nieuwe dashboardoverride en autonome per-zone AUTO/UIT-regelaar niet. Controleer daarom na rollback de native ruimtestanden en oudere handmatige vrijgave. Oude releasedocumenten blijven onveranderd; `OVERDRACHT.md` beschrijft de huidige bron.
