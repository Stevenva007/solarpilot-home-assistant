# Lokale validatie beta.24

SolarPilot 1.0.0-beta.24 — lokale validatie

Basis: volledige SolarPilot 1.0.0-beta.23 source-archive.
Python: 3.13.5 (Linux).

Volledige suite: 494 passed (laatste uitvoering 2.21 s).
Actuele uitleg: OK, 1.0.0-beta.24, hash 4fc5ed99ad717f03.
Repositorystructuur: OK.
Public repository preflight: OK.
77 Python-bestanden: AST-syntaxcontrole geslaagd.
JSON-bestanden: parse geslaagd; manifest-sleutelvolgorde gecontroleerd.
JavaScript: node --check geslaagd.

Browsercontrole: echte solar-pilot-card.js in Chromium met fictieve gegevens.
7 navigatietabs, kosten dag versus horizon, geen dubbele PV-aftrek,
open details behouden bij nieuwe telemetrie, leesbare mobiele kostenkaart,
Wallbox-paneel zonder fysieke bedienknoppen, HTML-escaping en actierouting.
Responsieve controles voor 320, 390, 768, 1280 en/of 1440 px volgens teststappen.

Nieuwe tests behandelen onder meer:
- kabelaanwezigheid versus actieve laadvraag;
- minimum zonnelaadvermogen, klein-overschotfallback, stabiele vrijgave;
- geen overschrijven van compressor-minimumlooptijd of beschermde cycli;
- geen ongecontroleerde EV-vermogensovername door lagere lasten;
- begrensde wachttijd als de auto niet start;
- import/export apart integreren, directe PV niet dubbel aftrekken;
- negatieve tarieven, lokale middernacht, zomertijd, ontbrekende metingen;
- herstartbehoud en duidelijk gemarkeerde oude dagtotalen;
- gecachete monetary/total-sensors met correcte dagreset;
- geen permanente forecastblokkering voor een toestel zonder dagdoel.

Grenzen: de Python-tests gebruiken Home Assistant-doubles, niet een draaiende
Home Assistant Core-installatie. De browser gebruikt fictieve waarden. Geen
live hardwaretest op de woning, auto, Wallbox, compressor of warmtepomp gedaan.
Geen GitHub-push, remote Actions/hassfest/HACS-validatie of HA-installatie gedaan.
Die checks moeten op de nieuwe commit en installatie nog worden uitgevoerd.

Het archief is cumulatief; beta.22 en beta.23 hoeven niet eerst geïnstalleerd.
Nieuwe voorrang is opt-in; configuratie/leerdata/userfiles worden niet meegeleverd.
