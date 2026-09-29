# SolarPilot beta.31 — AEG APP-vrijgave en startdeadline

Volledige cumulatieve update op beta.30. Behoudt Leren & vragen, alle analyse-exporten,
het rustige boilerprofiel, Wallbox-prioriteit en de dagoverzichten. Er wordt niets
op GitHub of Home Assistant gepubliceerd of bediend door het downloaden van dit pakket.

## Wat is nu nieuw?

De fysieke Delay Start/APP-knop mag één belading aanvragen, zonder zelf een timer te
kiezen en zonder extra klaarzetknop in SolarPilot. Kies dit bewust in de wizard.
De toestemming is uitsluitend de volledige Remote control-waarde `Enabled`.
`Not Safety Relevant Enabled` telt niet als volledige toestemming.

Standaard is de startdeadline **13:00**. Vóór die tijd klaargezet: dezelfde dag.
Op of na die tijd klaargezet: **de volgende kalenderdag**. Op die geplande dag
wordt eerst bruikbaar zonneoverschot afgewacht; bij de deadline mag netstroom
bijvullen wanneer die optie aanstaat. Geen onbeperkt uitstel tot er ooit weer zon is.

De keuze bij te laat klaarzetten is instelbaar. Alternatief `Nog dezelfde dag`
betekent na de deadline: starten zodra de apparaat- en netvoorwaarden kloppen,
zo nodig meteen met netstroom. Bij een nieuwe aanvraag wordt de datum vastgelegd;
een herstart of nieuwe cloudmelding verschuift die datum niet.

## Installeren

1. Maak een volledige Home Assistant-back-up. Zet SolarPilot op Pauze en laat
   eigen lasten veilig vrijgeven. Een lopende afwascyclus wordt niet onderbroken.
2. Kopieer de volledige projectinhoud over de bestaande Git-repository, behoud
   `.git` en privébestanden. Publiceer geen eigen analyse-exporten of HA-configuratie.
3. Draai `py -m pytest -q -p no:cacheprovider`, de repository- en uitlegcontroles.
4. Push de commit eerst naar `main`. Maak pas na geslaagde GitHub-validatie van
   die commit de nieuwe tag `v1.0.0-beta.31`. Verplaats nooit een bestaande tag.
5. Installeer via HACS en herstart Home Assistant. Tussenliggende beta's mogen
   worden overgeslagen. Geen aparte dashboardresource nodig.

Bestaande handmatige AEG-profielen blijven handmatig. De update schakelt niet
stilzwijgend nieuwe fysieke rechten in. Bij een nieuw AEG-profiel wordt APP als
optie voorgesteld, maar mappingbevestiging en deelname Auto blijven vereist.

## Koppelingen en instellingen

Open **Configureren met uitleg ? → Verbruikers & prioriteiten**. Voeg het type
**AEG/Electrolux afwasmachine — alleen starten** toe, of wijzig het bestaande profiel.

Koppel oorspronkelijke bronnen van hetzelfde apparaat voor START, Appliance state,
Remote control, Door state, Connectivity state en het gekozen programma. De
Cycle phase-bron is aanvullend; de Shelly-vermogensmeter is optioneel.

| Optie | Geadviseerd voor de aangetoonde APP-bediening |
|---|---|
| Gereedstatus | `Ready To Start` |
| Werkelijk bezig | `Running` |
| Bevestigd einde | `End Of Cycle` |
| Verbonden | `Connected` |
| Remote-vrijgave | Exact `Enabled` |
| Deur gesloten | `off` voor een HA door-binary-sensor |
| Toestemming | Fysieke Delay Start / APP-knop |
| Uiterlijk starten | **13:00** |
| Na de deadline klaargezet | **Volgende dag, eerst zon** (standaard) |
| Netstroom bij deadline | **Aan**, bewust bevestigen |
| Herstelvenster na een blokkering | 120 minuten |
| Voldoende overschot gedurende | 300 seconden |
| Wachten op START-terugmelding | 300 seconden |
| Alarmherkenning bij AEG Alerts-sensor | AEG DISH_ALARM-attributen |

Bevestig de bronkoppelingen en stel de nominale planningswaarde conservatief in.
De voorgestelde 2000 W is geen geverifieerde modelspecificatie. Een fasegemiddelde
van 1171/1335 W bewijst niet het maximale elektrische vermogen. Laat Shelly/cyclusleren
uit zolang er geen echte exclusieve W/kW-meting bestaat. Vul geen geschatte
vermogenshelper in als echte meter. Schakel het programma nooit met een stekkerrelais.

AEG-alarmvlagmodus vereist beschikbare technische DISH_ALARM-vlaggen die allemaal
OFF zijn. De twee benoemde zout-/glansmiddelwaarschuwingen zijn geen startblok.
Onbekende technische vlaggen worden niet genegeerd. Het cijfer `Alerts=2` wordt
niet op zichzelf veilig of onveilig verklaard. Er wordt geen alarm gewist.

Doorloop de volledige wizard en sla op. Kies vervolgens voor deze verbruiker
**Auto** en globaal **Zonnestroom**. Alleen bekijken/configureren start niets.
Staat APP al aan bij de eerste installatie, schakel de APP-vrijgave eenmaal uit
én weer in op de machine. Een reeds actieve status bij opstart wordt niet als
nieuwe fysieke knopdruk aangenomen. Een eerder opgeslagen aanvraag wordt wel hervat.

## Voorbeelden van de standaardplanning

| Klaargezet | Gedrag |
|---|---|
| Dinsdag 09:00 | Dinsdag zon proberen; startdeadline dinsdag 13:00. |
| Dinsdag 15:00 | Dinsdag niet meer starten; woensdag zon proberen; deadline woensdag 13:00. |
| Dinsdag 22:00 | Woensdag zon proberen; deadline woensdag 13:00. |
| Woensdag 01:00 | Woensdag zon proberen; deadline woensdag 13:00. |

De status toont geplande datum en tijd. De 13:00-deadline is een gewenste uiterste
start, geen tijdstip waarop het 4,5-uurprogramma klaar moet zijn. De opdracht wordt
op de eerstvolgende regelcyclus bij de deadline gegeven; fysieke terugmelding kan
cloudvertraging hebben. Er is geen garantie bij uitval, storingen, open deur,
ontbrekende APP-vrijgave, Pauze/Observatie of onvoldoende elektrische ruimte.

Bij zo'n blokkering volgt na 30 seconden overschrijding eenmaal een HA-melding.
Een nog niet verstuurde start mag na herstel binnen het ingestelde venster alsnog
gebeuren. Daarna vervalt de aanvraag. Een onzekere of mislukte START wordt nooit
blind herhaald, ook niet binnen dat venster. De aanvraag wordt niet naar nog een
dag doorgeschoven. Handmatig starten verbruikt dezelfde aanvraag.

De nettoestemming vervangt bij de deadline uitsluitend de zonnevoorwaarde en haar
stabilisatietijd. De globale importlimiet, kwartierpiek, fasebewaking, gereserveerd
vermogen van andere eigen lasten, sensoractualiteit en alle machinevoorwaarden
blijven gelden. Er wordt geen Wallbox-vermogen als extra elektrische capaciteit
geteld en geen Wallbox-opdracht verstuurd.

## Eindeherkenning en AirDry

- `End Of Cycle` wordt direct bij het HA-status-event verwerkt, ook als het maar
  enkele seconden bestaat. Er is geen wachttijd of vijfsecondenpolling voor dit signaal.
- Het eindtijdstip blijft lokaal bewaard na `Off`, `Unavailable`, `Disconnected`
  en een herstart. Het dashboard toont **klaar met tijdstip**, niet leeggemaakt.
- `Ado Drying` is nadrogen. De geopende AirDry-deur is dan geen klaar-/leegmelding.
- Alleen `Off` of een verbroken verbinding is geen bewijs van voltooiing. Bij
  ontbreken van een geregistreerd eindesignaal wordt geen succesvol einde verzonnen.
- Een nieuwe APP-aanvraag vraagt opnieuw geldige startvoorwaarden. Dezelfde
  Enabled-status, een herstart of opnieuw verbinden kan geen tweede beurt maken.

De START-intentie wordt vóór de opdracht in lokale opslag bewaard. Echte Running-
terugmelding bevestigt de start. SolarPilot stuurt voor dit toestel geen PAUSE,
RESUME, STOPRESET, native uitsteltimer, programmaselectie of relaisopdracht.
Een eenmaal gestart programma mag daardoor later netstroom gebruiken bij wolken.

## Diagnose, historie en grenzen

Analyse-export bevat nu ook de APP-aanvraag, geplande datum/deadline, uitkomst,
bronbinding, de laatste cyclus en de bevestigde eindtijd. Bestaande model-, energie-,
leer- en foutinformatie blijft behouden. Geen automatisch versturen naar ChatGPT.
Een export blijft privé; pseudoniemen maken huishoudelijke patronen niet anoniem.

Alle meegeleverde software- en browserproeven gebruiken fictieve HA-antwoorden.
Er is geen nieuwe fysieke AEG-test, echte HA-servertest of GitHub Actions-run
uitgevoerd tijdens het bouwen. Beoordeel na installatie één normale belading.
Bewaar de fabrikantbeveiligingen en gebruik nooit een tweede automatische START-
regelaar voor dezelfde machine naast dit profiel.
