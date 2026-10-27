# SolarPilot

**Actuele bronversie: 1.0.0-beta.108.** SolarPilot verdeelt lokaal zonnestroom tussen je toestellen in Home Assistant.

De Wallbox staat standaard achteraan en gebruikt zelfstandig het resterende overschot. Voorwaardelijk laadvermogen voor een SG-start moet bij de actuele P1/PV-balans passen; een nog recent maar fysiek tegenstrijdig cloudrapport levert geen laadbijdrage. De kaart benoemt de werkelijke voorrang en het verschil tussen wolkenbuffer en directe netgrens. Snelle diagnose bevat oorspronkelijke bronrapporten om een volgende laad-/netreactie te beoordelen.

[Actuele werking](docs/ACTUELE_WERKING.md) · [Installatie en rollback](docs/BETA108_INSTELLEN.md) · [Testverslag](docs/TESTRESULTATEN_BETA108.md) · [Changelog](CHANGELOG.md)

Panasonic regelt de warmtepomp zelfstandig; SolarPilot bedient uitsluitend de bevestigde SG-uitgang. De afwasmachine behoudt haar beschermde cyclus. Net-, fase- en kwartiergrenzen blijven gelden.

## Installatie via HACS

1. Voeg `https://github.com/Stevenva007/solarpilot-home-assistant` toe aan **HACS → Custom repositories** als **Integration**.
2. Download SolarPilot en herstart Home Assistant.
3. Voeg **SolarPilot** toe onder **Instellingen → Apparaten & diensten**.
4. Selecteer betrouwbare P1-/PV-bronnen en begin bij nieuwe installatie met **Alleen bekijken**.

De frontend wordt meegeleverd en automatisch geregistreerd. Geen aparte Lovelace-resource, dashboard-YAML of www-kopie is nodig. De warmtepomp staat tussen de andere toestellen in Overzicht en Toestellen en heeft een eigen tabblad Warmtepomp. De kaart toont afzonderlijk **Taak van de warmtepomp**, **Elektrische bijverwarming**, elektrische activiteit en de werkelijk gemelde SG-contactstand. De aanvraag staat in Details; ontvangen SG verschijnt alleen met een passende actuele bevestigde bron. Een bekende afwijking tussen aanvraag en contact krijgt een waarschuwing. Verse native taakmeldingen en afleidingen blijven afzonderlijk. Een verse native actie benoemt de taak rechtstreeks; verse ontdooimelding heeft voorrang. Een verse exact herkende tankroute met actieve toegewezen hoofd- of ondersteuningsvoeding kan Boiler opwarmen afleiden. Een gekozen verwarmings-/koelstand vraagt daarnaast een verse actieve hoofdvoeding en afzonderlijke verse expliciete tankrust voordat Verwarmen of Koelen wordt afgeleid. Deze read-only presentatie kan een bruikbare deelmeting gebruiken; het totale vermogen blijft onbekend bij ontbrekende dekking. Watts of gekozen stand alleen, expliciete globale UIT en oude/conflicterende context geven geen afgeleide functie. Elektrische ondersteuning is aanvullend en vervangt de taak niet. De kaart houdt de taak en waarden compact; ruwe meldingen, bronuitleg en profielaannamen staan in Details/export. Het bestaande verschillende meterpaar gebruikt automatisch de in Details benoemde aanname voeding 1 = warmtepomp inclusief regeling/pompen en voeding 2 = elektrische bijverwarming; eerdere expliciete afwijkingen blijven behouden. De gewone taakherkenning gebruikt bestaande koppelingen. Voor het berekende tapwater-SG-doel kies je eenmaal de bestaande geregistreerde native tankbron voor de vergelijking en bevestig je het lokaal ingestelde percentage onder Warmtepomp — uitleesbronnen. Alleen complete actuele bevestigde dekking vormt het totaal. De ventilatoranimatie toont verse elektrische hoofdactiviteit en bewijst geen compressorbeweging; bij alleen ondersteuning beweegt het verwarmingssymbool. Verminderde beweging onderdrukt animaties. Zonder bruikbaar taakbewijs blijft het taakvak weg; verse actieve meting kan Warmtepomp werkt tonen. Metingen, SG, reden en technische broninformatie in Details blijven beschikbaar. Backend- en geladen kaartversie staan onder Instellingen & controle. Herlaad na update de pagina volledig of sluit de app volledig af en open haar opnieuw; de backendversie alleen bewijst geen actuele kaart.

Bij **Analyse nodig** maakt één klik een export van de beschikbare zeven dagen; onder **Meetkwaliteit** zie je bevindingen en dekking zonder leervragen of beleidkeuzeknoppen. Onder **Export** download je een lokaal JSON.GZ-bestand met gerichte warmtepomp-/SolarPilot-analysevraag, meet-/beslisgeschiedenis en bronkwaliteit. Voeg het hier bewust toe; de meegeleverde analysevraag bevat insteltips en onderbouwde verbetervoorstellen als onderwerpen. Een teruggegeven JSON-antwoord-/adviezenrapport kun je optioneel lokaal uploaden en bekijken. Exact bron-/bevindingrevisiegebonden antwoorden verwerken alleen de reviewstatus: beoordeeld afgehandeld, meer data nodig open. Het rapport blijft bij een gewone update bewaard. Logische voorstellen met een stabiele identiteit worden alleen als uitgevoerd getoond als het vertrouwde register van de geïnstalleerde release dat bevestigt; de upload werkt de integratie niet bij. Het rapport wordt nooit automatisch als instelling, codewijziging of apparaatopdracht toegepast; elke gewenste wijziging houdt haar eigen bewuste actie en voorwaarden.

## Herstel van de beta.62-opstartfout

Update via HACS naar beta.96 na geslaagde publicatie en herstart Home Assistant volledig. Verwijder SolarPilot niet en wis geen configuratie, modellen of opslag. De herstelupdate ondersteunt de onveranderbare opties die Home Assistant zelf aanbiedt en houdt geneste instellingen intact. In een lokale proef met de onveranderbare mappingvorm van HA-opties ontstond de beta.62-fout vóór migratie en opslag; de toestand van jouw eigen installatie is niet uitgelezen. De beta.63-opstartfix blijft behouden. Nieuwe algemene profiel- en meetkeuzes vereisen hun eigen bewuste lokale bevestiging. Ongewijzigde geldige SG-bevestigingen uit beta.69 blijven behouden; beta.91 vraagt geen herbevestiging alleen door de codeupdate.

## Upgrade vanaf beta.61

Maak eerst een volledige privé Home Assistant-back-up inclusief configuratie en SolarPilot-opslag. De sinds beta.62 gebruikte migratie archiveert oude warmtepompgegevens buiten de actieve runtime en verwijdert de uitvoerende tank-/klimaatregeling. De migratie zelf geeft geen fysieke opdracht. Controleer eenmalig de gewenste native basisinstellingen op Panasonic; deze versie zet een mogelijk eerder achtergelaten doel of zone niet terug.

Geldige andere toestellen, prioriteiten, APP-tickets, geschiedenis, leerdata en bestaande retentie blijven behouden. SG wordt niet geactiveerd door een oude boilerkeuze of globale Auto-modus. Rollback vereist beta.61-code **en de passende pre-migratie privé-opslag/back-up**; alleen de oudere ZIP terugzetten is geen volledig herstel. Zie de releasehandleiding.

## Ontwerpgrenzen

- P1/PV, fysieke grenzen en fabrikantbeveiligingen gaan vóór forecasts en plannen. De gezamenlijke planner is geen nieuwe actuator of thermische Panasonic-regelaar.
- Panasonic bezit comfort, verwarmen/koelen, warm water, elektrische ondersteuning en sterilisatie.
- SG is een optionele extra flexibele vraag en neemt geen Wallbox-, afwas- of noodzakelijk comfortvermogen af.
- Aanvraag/eigenaar, gemelde contactstand/lokale timer, compressor/native context en ontvangen SG-status zijn afzonderlijke bewijslagen. Compressorbedrijf bewijst geen extra SG-effect.
- Eén totaalmeter of twee complete bevestigde niet-overlappende voedingen; ontbrekend totaal blijft onbekend en inbegrepen heater wordt niet nogmaals opgeteld.
- Een SG-sessie is standaard begrensd tot één uur. Tapwater-only behoudt tankafkoeling; het lokaal bevestigde algemene profiel vraagt na rust betekenisvol nieuw zon-/native bewijs. Tijd, reload of dezelfde samples geeft geen eindeloze herstarts. Extra koeling heeft afzonderlijke bestaande condensbeveiliging nodig tenzij betrouwbare native context koeling uitsluit.
- De Wallbox blijft read-only; een afwasbeurt krijgt maximaal één native START en wordt nooit onderbroken. De vastgelegde APP-startdeadline staat netstroom toe zonder zonnevoorwaarde, binnen de bestaande fysieke en apparaatgrenzen.
- Batterijbediening houdt haar eigen expliciete toestemming/eigenaarschap en commandobevestiging.
- Een EMS en lokale timer vervangen geen elektrische beveiliging.

## Privacy en gegevens

Configuratie, modellen, migratiearchief en onderzoeksdata blijven lokaal. Een normale update vervangt programmabestanden, geen privé HA-opslag. De bewaarde optionele `userfiles/private_bundle.json` hoort nooit in GitHub of release-assets. De analyse-export wordt door een ingelogde beheerder bewust lokaal gemaakt; geen automatische upload.

Geen back-ups, access tokens, huisadressen, persoonlijke entitybindings of ruwe huishouddatasets committen. Publieke voorbeelden en tests gebruiken fictieve bronnen. Grote actuele leerattributen/eigen opslag blijven behouden; alleen herhaalde zware Recorder-kopieën worden uitgesloten. Bestaande perioden/aantallimieten blijven gelden, geen onbeperkt archief.

## Verwijderen

Kies **Verwijderen voorbereiden**, wacht op gerichte veilige vrijgave, verwijder de SolarPilot-entry en vervolgens de HACS-integratie. Dit verwijdert geen oorspronkelijke Shelly-, warmtepomp-, Wallbox-, AEG- of meterintegratie. Bewaar vooraf de gewenste privégegevens en back-up. Onzekere SG-status wordt niet als bevestigd UIT voorgesteld.

De SG-startdrempel gebruikt vanaf beta.69 de gemeten gezamenlijke zonnebijdrage inclusief de complete actuele warmtepompmeting. Restinjectie en mogelijke extra SG-vraag blijven apart; net-/fasegrenzen en Wallboxvoorrang gelden volledig. Details tonen de gebruikte bijdrage, bronkwaliteit en concrete blokkering. Native en afgeleide taakvoorbeelden blijven afzonderlijk in leren/export.


Het openbare [upstream-bronregister](docs/UPSTREAM_BRONNEN.md) houdt vaste bronversies en relevante PR-status bij. Een afzonderlijke geautoriseerde wekelijkse ChatGPT-taak kan relevante geteste SolarPilot-correcties onderzoeken en publiceren. Dit is externe ontwikkeling; SolarPilot voert geen achtergrond-AI, automatische providerupdate of wijziging van lokale apparaten uit.
