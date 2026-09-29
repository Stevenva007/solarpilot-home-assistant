# SolarPilot 1.0.0-beta.32 — lokaal testverslag

Datum: 29 september 2026. Bronbasis: de werkelijk aangeleverde volledige beta.31-ZIP.
Oorspronkelijke SHA-256: e7546dde60e98d6ea27f3505ab7c549f31112feed4b4afcd167a2f49a533f867.
Reikwijdte: cumulatieve lokale bronwijziging, geen publicatie of fysieke bediening.

## Uitgevoerd

- Python 3.13.5, pytest 9.0.2.
- Ongewijzigde bronbasis: 1027 tests geslaagd.
- Huidige volledige suite: **1094 tests geslaagd**, inclusief **67 nieuwe**
  voorrangs-, engine-, runtime-, reserverings- en terugmeldingstests.
- Uitlegcontrole: versie **1.0.0-beta.32**, regel-hash **9fb7599a6daa9332**.
- 391 help-items gegenereerd, inclusief de twee nieuwe afzonderlijke AEG-opties.
- Repositorystructuur en public repository preflight: OK.
- 115 Pythonbestanden geparseerd; alle vier component-JSONbestanden geldig.
- node --check op de daadwerkelijke kaart en optie-uitleg-JavaScript: OK.
- git diff --check tegenover de oorspronkelijke beta.31-boom: geen fouten.
- De uiteindelijke ZIP wordt apart uitgepakt en dezelfde volledige pytest-suite,
  versie-/uitleg-, structuur- en privacychecks worden vóór aflevering opnieuw uitgevoerd.

## Nieuwe gedragscontroles

- De voorkeurgroep staat standaard aan voor het afwasmachinetype, niet voor alle toestellen.
- Geen automatische mappingbevestiging, Auto-vrijgave of fysieke bronkoppeling.
- Voorrang boven lagere numerieke prioriteiten van gewone lasten.
- Klein overschot laat de ontvochtiger ongemoeid; geen onnodig stopzetten als beide passen.
- Alleen benodigde eigen, met een exclusieve echte meter gemeten lasten veilig vrijgeven.
- Minimumlooptijd, handmatige overname, boost, dagdeadline en beschermde cycli behouden.
- Reductie komt vóór de afwasstart; geen voorspeld vrijgekomen elektrisch vermogen gebruiken.
- Alleen verse geldige Full Solar-data met actuele PV voor de aparte beschermde EV-zonnestart.
- Geen aanvullende net-/kwartierpiek-/faseruimte uit EV-vermogen, ook niet bij de laatste dispatchcontrole.
- Gewone niet-onderbreekbare scripts kunnen geen afwas-specifiek krediet gebruiken.
- Geen tweede toewijzing van dezelfde voorwaardelijke EV-pool aan meerdere nieuwe afwasbeurten.
- Wijziging van de EV-modus tussen plan en verzenden blokkeert de start.
- Ontbrekende/beschadigde/oneindige metingen, Pause/Observe en expliciete uitkeuzes gerespecteerd.
- Normale 50 °C-opdracht wordt eerst afgehandeld; geen 52 °C-herstelopdracht toegevoegd.
- Aankomende gewone tankvraag en benodigde avondvoorraad worden gereserveerd; extra 60 °C niet.
- Een `heating`-bedrijfsmodus is niet hetzelfde als bevestigde compressoractiviteit.
- Sterilisatie wordt niet verlaagd en is niet afhankelijk van zon; bij genoeg ruimte kan afwas erbij.
- Bestaande vloerverwarming wordt niet uitgeschakeld; bij voldoende restvermogen kan afwas tegelijk.
- De 13:00-nettoestemming omzeilt geen comfortreserveringen of onbekende gekoppelde boilerstatus.
- Morgen klaargezet blokkeert vandaag geen extra zonnebuffer en reserveert geen aankomende tanklast.
- Conservatieve extra piekruimte voor een lopende afwas zonder exclusieve vermogensmeter.
- Startintentie en nieuwe netto-balansbewaking worden opgeslagen vóór de fysieke button-call.
- Geen STOP/PAUSE/RESUME/relais/Wallbox-opdrachten of generieke terugneembare handover voor afwas.
- Mislukte nettobalans geeft eenmalig aandacht en blokkeert nieuwe EV-gebaseerde starts;
  een lopende beurt blijft afwerken. Werkelijk restoverschot blijft een aparte startmogelijkheid.
- Nieuwe actieve AEG-status en meerdere nieuwe netrapporten vereist voor balansbevestiging.
- Bevestigde voltooiing verwijdert de actieve voorkeur, ook na het korte einde-event gevolgd door Off.
- De bestaande 1027 regressies voor alle eerdere functies blijven geslaagd.

## Browsercontroles — echte code, fictieve data

Uitgevoerd in headless Chromium/Playwright op de opnieuw gegenereerde voorbeeldpagina
met de daadwerkelijke frontendcode uit deze release:

- tools/check_dishwasher_priority_ui.py: nieuwe voorkeurgroep, twee standaardkeuzes,
  live waarschuwingen/reserveringen, afzonderlijke mogelijkheid EV-prioriteit uit te
  schakelen, vraagtekens/uitleg, 80 telemetrieupdates zonder invoerverlies, HTML-escaping,
  320/390/768/1440 px en geen actuatoraanroepen. Netwerk in deze proef geblokkeerd.
- tools/check_dishwasher_app_ui.py: datum/deadline, geen extra verplichte knop,
  AirDry/nadrogen, bewaard einde bij offline, onbekend einde en 80 updates.
- tools/check_dishwasher_analysis_ui.py: beschermd programma, eenmalige bevestiging,
  analyse-export/JSON-download, pseudoniemen, gemeten versus onbekend profiel.
- tools/check_consumer_history_ui.py: 7/30-dagenpopup, datums/scroll/details, races,
  Esc/focus/opruiming en 80 updates.
- tools/check_options_ui.py: werkelijke configuratiedialoog met nagebootste native-HA-
  formulieren en antwoorden; 80 updates, foutafhandeling en formulierpayloads.
- tools/check_dhw_gentle_ui.py: 50/46/45 afzonderlijk zichtbaar, waarschuwingen en
  geen verborgen basisbuffer-instelling.
- tools/check_learning_ui.py: vragen en begrensde toestemming, opslagfouten,
  revisies, 7 modules en behoud van invoer/details.
- tools/check_card.py: alle bestaande tabbladen, planning/klimaat, responsiviteit
  en bescherming tegen onveilige HTML.

De uitvoerteksten van oudere browserscripts noemen soms hun oorspronkelijke beta-
nummer. De geteste HTML is telkens opnieuw gebouwd uit de huidige beta.32-bron.

## Grenzen

Geen fysieke AEG-, Shelly-, Panasonic- of Wallboxtest. Geen draaiende echte Home
Assistant-server. Geen nieuwe GitHub Actions/hassfest/HACS-validatie; die volgt
na publicatie van de werkelijke commit. Geen gemeten CPU-impact op de installatie.

Voorwaardelijk aan EV onttrokken zonnestroom is geen gegarandeerde netvrije beurt.
De nettebalansproef bewijst zonder Shelly geen afzonderlijk gemeten afwasvermogen
of causale reactie van de laadpaal. Een gestart programma blijft beschermd, ook
als daarna bewolking, comfortvraag of een trage Wallbox netstroom nodig maakt.
De ingestelde vermogens zijn planningswaarden, geen elektrische beveiliging.

Volledige faseprofielgestuurde APP-startplanning is uitgesteld tot de latere
Shelly-update. De 13:00-deadline blijft afhankelijk van echte startvoorwaarden,
netruimte en beschikbaarheid. Normaal 50 °C met native −5 °C biedt geen gegarandeerd
minimum van 46 °C. Fabrikanthygiëne en fysieke beveiligingen blijven noodzakelijk.
