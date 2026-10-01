# SolarPilot 1.0.0-beta.41 — testresultaten

Datum: 2026-10-02

> **Software- en bronrelease-gate: groen.** De volledige Python-regressiesuite, alle browsercontroles en alle niet-browser broncontroles zijn op de definitieve beta.41-bronboom geslaagd. Release-ZIP's worden pas door de publicatieworkflow gemaakt en daarna afzonderlijk inhoudelijk gecontroleerd.

## Geautomatiseerde regressiesuite

- Volledige suite met `PYTHONUTF8=1`: **1465 passed in 8.72s**.
- Gerichte runtime/startdiagnostiek-set: **47 passed**.
- Gerichte klimaat-runtime-set: **16 passed**.
- Gerichte DHW-set inclusief comfort/gentle-regressies: **229 passed**.
- Gerichte UI/live-config/live-options/geschiedenis-set: **157 passed**.
- Gerichte afwasmachine-/recoveryset: **245 passed**.

De gerichte sets zijn inhoudelijke deelcontroles en kunnen tests uit de volledige suite overlappen; hun aantallen worden daarom niet bij elkaar opgeteld als een tweede totaalcijfer.

De definitieve suite dekt de volgende beta.41-grenzen:

- de centrale prioriteitenlijst is leidend voor schema 2 en oude/open formulieren kunnen centrale waarden niet terugschrijven;
- per toestel blijft `result.reason` de beslissende samenvatting en worden bekende startvoorwaarden, vermogensmarge en stabiliteitstijd eerlijk weergegeven;
- onbekende externe start-/stopoorzaken worden niet ingevuld;
- een handmatige OFF-zone blijft behouden bij gewone AUTO, een eigen coast-zone kan worden vrijgegeven en hard comfort richt zich uitsluitend op de overschrijdende zone;
- DHW-overschothysterese vereist bevestigd SolarPilot-eigendom, echte import/actieve koeling geven directe terugval en `manual_hold` voorkomt servicecalls;
- Wallbox-sessies blijven fail-closed en read-only;
- beta.40-AEG-recovery blijft idempotent, same-device, begrensd en zonder fysieke migratieopdracht.

## Releasecontroles

Alle browsercontroles zijn geslaagd:

- `check_card`;
- `consumer_history`;
- `dhw_gentle`;
- `dishwasher_analysis`;
- `dishwasher_app`;
- `dishwasher_priority`;
- `learning_ui`;
- `live_options_ui34`;
- `options_ui`;
- `priority_ui35`;
- `pv_ui33`.

- `tools/check_current_explanation.py`: **geslaagd** voor beta.41, regel-hash `f37ff9c0c44f04a9`.
- `tools/check_handoff.py`: **geslaagd**.
- `tools/validate_repository.py`: **geslaagd**.
- `tools/check_public_repository.py`: **geslaagd** nadat uitsluitend gegenereerde testcaches waren verwijderd.
- Python compileall met bytecodecache buiten de bronboom: **geslaagd**.
- Node-syntaxcontrole voor `solar-pilot-card.js` en `option-help.js`: **geslaagd**.
- `git diff --check`: **geslaagd**.
- Root- en embedded kopie van dit testverslag: **identiek** na deze update; root herbevestigt dit vóór publicatie.

De release-ZIP's, hun werkelijke inhoud en checksums worden na de releaseworkflow gecontroleerd en niet vooraf als geslaagd gemeld.

## Bevestigde live uitgangssituatie vóór beta.41

- Home Assistant draaide werkelijk **2026.9.4** met SolarPilot **1.0.0-beta.40** geladen.
- De beta.40 post-start recovery vond de complete AEG same-device mapping en maakte het profiel zichtbaar onder Toestellen en Voorrang zonder START tijdens migratie.
- De installatie beschikt over een effectieve Wallbox-sessiebron met volledige waarden voor zonne-auto, manueel laden en gestopt. Zij was nog niet als `session_mode_entity` gekoppeld; de Full Solar-select alleen bleef terecht onvoldoende bewijs.
- Klimaat stond live met één zone OFF en één zone AUTO; beide `hvac_action`-waarden waren idle. De gewone winterbeslissing was AUTO, de modelzekerheid was 0% en de zichtbare reactievertraging gebruikte nog de fallback. Dit bewees dat AUTO niet hetzelfde is als actief verwarmen en motiveerde de per-zone eigendomsfix.
- DHW stond met automatische functie aan maar `control_allowed=false`, `manual_hold=true` en `owns_target=false`. Dit is een bewuste schrijfblokkering. Oude boilerautomatiseringen bestonden nog en moeten pas bij een gecontroleerde overname worden uitgeschakeld.
- Fase- en batterijstatus leverden geen nieuw actuatorrecht op: fasecontrole vereist echte bron-/limietvalidatie en zonder batterijhardware blijft batterijwerking adviserend.

## Acceptatieplan na installatie beta.41

De software-gate vereist geen fysieke AEG-start. Na installatie worden de volgende punten gecontroleerd op de echte installatie:

1. Home Assistant toont backendversie `1.0.0-beta.41`; na geforceerd vernieuwen toont ook de kaart beta.41.
2. Voorrang toont één volledige stapel, geen dubbele toestelvelden en correcte positie/toestemming rond Auto laden.
3. Een nog niet gestart toestel toont de doorslaggevende reden, eerlijke startvoorwaarden, vereiste vermogensmarge en stabiliteitstijd.
4. Geschiedenis toont afzonderlijke Startreden en Stopreden zonder verzonnen externe oorzaak.
5. De effectieve Wallbox-sessiebron classificeert zonne-auto, manueel en gestopt correct; er wordt geen Wallbox-service aangeroepen.
6. Een handmatig OFF gezette klimaatzone blijft OFF bij een gewone AUTO-beslissing; alleen een echte harde comfortoverschrijding mag precies die zone naar AUTO zetten.
7. Een door SolarPilot beheerd 60 °C-doel valt bij actieve koeling of echte netafname zonder terugvalvertraging terug; tijdens manual hold volgt geen write.
8. Een nieuwe AEG-belading gebruikt een nieuwe overgang naar exact `Enabled`, verstuurt maximaal één START en blijft beschermd tot End Of Cycle.
9. Globale Automatisch regelen en per-toestel Auto worden pas na deze controles afzonderlijk vrijgegeven.

## Fysieke grenzen van deze test

Softwaretests gebruiken Home Assistant-testdubbels en bewijzen geen echte cloud-, relais-, compressor-, laadpaal- of vermogensrespons. Zonder exclusieve AEG-meter wordt geen gemeten elektrisch faseprofiel geclaimd. Zonder echte batterij wordt geen batterijregeling getest. De fysieke controle is een expliciete acceptatiestap na installatie en geen misleidende claim dat de echte afwasmachine al vanuit de bouwomgeving werd gestart.

Zie `BETA41_INSTELLEN.md` voor upgrade, controle en rollback.
