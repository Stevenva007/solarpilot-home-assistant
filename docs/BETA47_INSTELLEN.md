# SolarPilot 1.0.0-beta.47 — instellen en controleren

Beta.47 bouwt voort op de huidige beta.46-bron en werkt het automatische herstel na Home Assistant-herstart uit. De herstart is geen nieuwe toestelopdracht: SolarPilot controleert de echte toestanden en behoudt bestaande gebruikerskeuzes, prioriteiten en veiligheidsgrenzen.

## Bronbasis

De absolute codebasis is beta.46 op commit `c9ea80de746d0f0f25f5b127bcafaaf88f624b65`. De beta.46-tag en releasebestanden blijven onveranderd en zijn de rollbackbasis. De actuele volledige regelbeschrijving staat in `ACTUELE_WERKING.md` en in Home Assistant onder **SolarPilot → Uitleg**.

## Upgrade

1. Maak een actuele volledige Home Assistant-back-up en bewaar de gecontroleerde beta.46-release.
2. Laat beschermde afwas- of andere cycli afwerken. Gebruik geen STOPRESET voor de update.
3. Installeer exact `1.0.0-beta.47` via HACS zodra de release beschikbaar is of vervang uitsluitend `custom_components/solar_pilot` met het lokale pakket. Behoud bestaande `userfiles` en Home Assistant-opslag.
4. Herstart Home Assistant volledig en controleer backendversie en vernieuwde kaart afzonderlijk.
5. Controleer de herstelreden en actuele bronnen. Een niet geladen bron is geen fysieke OFF-toestand en een herstart geeft geen recht om een oude opdracht te herhalen.

## Automatisch herstartherstel

| Situatie | Gedrag |
| --- | --- |
| Eerder beheerd toestel heeft betrouwbare aan-/uitstatus | Werkelijke toestand wordt herkend zonder oude schakelopdracht. Minimumlooptijden starten conservatief bij die waarneming; daarna blijven gewone zon-/piek-/veiligheidsbesluiten gelden. |
| Numerieke toestelinstelling is tijdens herstart veranderd | Huidige bediening blijft vrij: SolarPilot laat eigendom los en respecteert de bestaande handmatige rusttijd zonder herstelwrite. |
| Toestelbron is nog niet geladen of tijdelijk onbeschikbaar | SolarPilot wacht en controleert opnieuw tijdens volgende gewone regelrondes. Na herstel hervat de bewaarde gebruikersmodus. |
| Gebruiker kiest ondertussen Alleen bekijken of Pauze | Die bewuste nieuwe keuze vervangt de bewaarde hervatkeuze. |
| Boiler heeft passend eerder beheerd doel en betrouwbare bronnen | Gewone herstartcontrole rondt automatisch af zonder doelopdracht. |
| Boilerbronnen ontbreken tijdelijk | Alleen de boilerherstelcontrole wacht; gewone andere regeling krijgt hierdoor geen blijvende globale herstartblokkering. |
| Boileropdracht was vóór herstart nog pending | Geen retry. Een nieuwe rapportage ná herstart en ná de bestaande adapterwachttijd moet de uitkomst bevestigen. |
| Boilerdoel wijkt af of echte handmatige/foutstatus bestaat | Bestaande bediening krijgt voorrang; de echte bescherming wordt niet automatisch gewist. |
| Fabrikanthygiëne/Powerful of native OFF heeft voorrang | Huidige fabrikantinstelling blijft behouden; SolarPilot verzendt geen hersteldoel of inschakelopdracht. |
| Eerdere AEG-START is onzeker | Geen tweede START. Alleen betrouwbaar lopend of voltooid bewijs kan de specifieke herstartonzekerheid automatisch oplossen; Idle of onduidelijke START-uitkomst geeft geen tweede START. |

Oude beta.46-opslag kon de tijdelijke Alleen bekijken-modus bewaren en de oorspronkelijke hervatkeuze verliezen. De éénmalige reparatie geldt uitsluitend zonder nieuwe hervatmarker, in Alleen bekijken, zonder echte toestel-/boilerfout of handmatige boilerbescherming, en met een onderbroken lease van een bekend Auto-toestel of een schoon routine-boilerhersteljournal. Een nieuwe expliciet opgeslagen marker, ook wanneer zij leeg is, voorkomt dat latere bewuste Alleen bekijken- of Pauze-keuzes worden overschreven.

Tijdens gewone bronwacht toont het overzicht **Automatische herstartcontrole** en de automatische wachtrede, zonder **Controle afronden** te vragen. Bij echte fout of onduidelijke START-uitkomst blijven controlebediening en waarschuwing beschikbaar.

Een bevestigde lopende of voltooide AEG-cyclus verbruikt ook de bestaande APP-aanvraag; later Idle maakt die oude belading niet opnieuw startklaar. Een open boilerhersteljournal telt mee als bezig bij veilig verwijderen, totdat de toestand betrouwbaar is vastgesteld.

De hervatkeuze en read-only herstelgegevens blijven bewaard wanneer tijdens het wachten opnieuw wordt opgeslagen of herstart. Een nieuwe beta.47-routineherstelmelding wordt na geslaagd herstel vanzelf opgeruimd; een al bestaande oude beta.46-melding kan cosmetisch blijven staan en mag na afgerond herstel gesloten worden. Die oude melding is zelf geen regelblokkering; andere foutmeldingen worden niet als routineherstel weggeveegd.

## Behouden regels

- De beta.46-hiërarchie tussen native `aquarea`-actie en algemene taakinfo blijft behouden, inclusief echte koel-/verwarmvoorrang en conservatieve bronversheid.
- Normaal warmwaterdoel standaard 50 °C, bewaakte comfortgrens 46 °C en extra restoverschot maximaal 60 °C; geen automatisch force-profiel of 55 °C-tussenstap.
- Vertraagde doelbevestiging voor exact `aquarea`/`panasonic_cc` blijft gelden; een onmiddellijke optimistische doelweergave is geen ACK.
- Handmatige/fabrikantbescherming, sterilisatie, elektrische grenzen, minimumlooptijden en beschermde cycli blijven leidend.
- AEG-startveiligheid en maximaal één START per belading blijven behouden. Herstart/reconnect maakt geen nieuwe APP-aanvraag.
- Wallbox blijft read-only en extra 60 °C krijgt geen Wallboxkrediet.
- Bestaande instellingen, leerdata, globale gebruikersmodus en afzonderlijke toesteldeelname blijven bewaard.

## Test- en installatiestatus

De definitieve softwaregate staat in `TESTRESULTATEN_BETA47.md`. In deze werksessie is geen live Home Assistant-verbinding beschikbaar; beta.47-installatie, fysieke toestelactie en tankopwarming zijn niet bevestigd.

## Rollback

Kies **Pauze**, laat beschermde cycli afwerken, herstel de onveranderlijke beta.46-release of een gecontroleerde volledige back-up en herstart Home Assistant. Controleer backend/kaart en alle relevante bronnen en beveiligingen. Beta.46 bevat de DHW-zonnebufferherstelling; het uitgebreidere automatische herstartherstel is onderdeel van beta.47.
