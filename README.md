# SolarPilot

SolarPilot is een lokale Home Assistant-integratie voor zonnestroomverdeling, flexibele verbruikers, een beschermde AEG-afwasmachine, read-only Wallbox-informatie, voorspellingen, kosten, lokaal leren en batterijfuncties.

**Actuele versie: 1.0.0-beta.64.** Panasonic regelt de warmtepomp zelfstandig. SolarPilot kan voor die warmtepomp alleen een extra SG-zonneboost aanvragen via één bewust gekoppelde bestaande Shelly-uitgang, met bewezen lokale aflooptimer. Het schrijft geen tank-/kamertemperatuur, AUTO/UIT, heaterkeuze of fabrikantprogramma. Nieuwe SG-sturing staat standaard uit tot gecontroleerde ingebruikname.

[Installatie en veilige upgrade](START_HIER.md) · [Volledige actuele werking](docs/ACTUELE_WERKING.md) · [Beta.64 instellen](docs/BETA64_INSTELLEN.md) · [Testresultaten](docs/TESTRESULTATEN_BETA64.md) · [Technische overdracht](OVERDRACHT.md)

Dezelfde actuele uitleg staat binnen Home Assistant onder **SolarPilot → Uitleg**. Historische veranderingen staan in [CHANGELOG.md](CHANGELOG.md); oudere instelbestanden beschrijven hun eigen release.

## Installatie via HACS

1. Voeg `https://github.com/Stevenva007/solarpilot-home-assistant` toe aan **HACS → Custom repositories** als **Integration**.
2. Download SolarPilot en herstart Home Assistant.
3. Voeg **SolarPilot** toe onder **Instellingen → Apparaten & diensten**.
4. Selecteer betrouwbare P1-/PV-bronnen en begin bij nieuwe installatie met **Alleen bekijken**.

De frontend wordt meegeleverd en automatisch geregistreerd. Geen aparte Lovelace-resource, dashboard-YAML of www-kopie is nodig. Backend- en geladen kaartversie worden afzonderlijk gecontroleerd na heropenen van browser/app.

## Herstel van de beta.62-opstartfout

Update via HACS naar de actuele beta.64 en herstart Home Assistant volledig. Verwijder SolarPilot niet en wis geen configuratie, modellen of opslag. De herstelupdate ondersteunt de onveranderbare opties die Home Assistant zelf aanbiedt en houdt geneste instellingen intact. In een lokale proef met de onveranderbare mappingvorm van HA-opties ontstond de beta.62-fout vóór migratie en opslag; de toestand van jouw eigen installatie is niet uitgelezen. De beta.63-opstartfix blijft behouden. Nieuwe algemene profiel- en meetkeuzes vereisen hun eigen bewuste lokale bevestiging.

## Upgrade vanaf beta.61

Maak eerst een volledige privé Home Assistant-back-up inclusief configuratie en SolarPilot-opslag. De sinds beta.62 gebruikte migratie archiveert oude warmtepompgegevens buiten de actieve runtime en verwijdert de uitvoerende tank-/klimaatregeling. De migratie zelf geeft geen fysieke opdracht. Controleer eenmalig de gewenste native basisinstellingen op Panasonic; deze versie zet een mogelijk eerder achtergelaten doel of zone niet terug.

Geldige andere toestellen, prioriteiten, APP-tickets, geschiedenis, leerdata en bestaande retentie blijven behouden. SG wordt niet geactiveerd door een oude boilerkeuze of globale Auto-modus. Rollback vereist beta.61-code **en de passende pre-migratie privé-opslag/back-up**; alleen de oudere ZIP terugzetten is geen volledig herstel. Zie de releasehandleiding.

## Ontwerpgrenzen

- P1/PV, fysieke grenzen en fabrikantbeveiligingen gaan vóór forecasts en plannen.
- Panasonic bezit comfort, verwarmen/koelen, warm water, elektrische ondersteuning en sterilisatie.
- SG is een optionele extra flexibele vraag en neemt geen Wallbox-, afwas- of noodzakelijk comfortvermogen af.
- Aanvraag/eigenaar, gemelde contactstand/lokale timer, compressor/native context en ontvangen SG-status zijn afzonderlijke bewijslagen. Compressorbedrijf bewijst geen extra SG-effect.
- Eén totaalmeter of twee complete bevestigde niet-overlappende voedingen; ontbrekend totaal blijft onbekend en inbegrepen heater wordt niet nogmaals opgeteld.
- Een SG-sessie is standaard begrensd tot één uur. Tapwater-only behoudt tankafkoeling; het lokaal bevestigde algemene profiel vraagt na rust betekenisvol nieuw zon-/native bewijs. Tijd, reload of dezelfde samples geeft geen eindeloze herstarts. Extra koeling heeft afzonderlijke bestaande condensbeveiliging nodig tenzij betrouwbare native context koeling uitsluit.
- De Wallbox blijft read-only; een afwasbeurt krijgt maximaal één native START en wordt nooit onderbroken.
- Batterijbediening houdt haar eigen expliciete toestemming/eigenaarschap en commandobevestiging.
- Een EMS en lokale timer vervangen geen elektrische beveiliging.

## Privacy en gegevens

Configuratie, modellen, migratiearchief en onderzoeksdata blijven lokaal. Een normale update vervangt programmabestanden, geen privé HA-opslag. De bewaarde optionele `userfiles/private_bundle.json` hoort nooit in GitHub of release-assets. De analyse-export wordt door een ingelogde beheerder bewust lokaal gemaakt; geen automatische upload.

Geen back-ups, access tokens, huisadressen, persoonlijke entitybindings of ruwe huishouddatasets committen. Publieke voorbeelden en tests gebruiken fictieve bronnen. Grote actuele leerattributen/eigen opslag blijven behouden; alleen herhaalde zware Recorder-kopieën worden uitgesloten. Bestaande perioden/aantallimieten blijven gelden, geen onbeperkt archief.

## Verwijderen

Kies **Verwijderen voorbereiden**, wacht op gerichte veilige vrijgave, verwijder de SolarPilot-entry en vervolgens de HACS-integratie. Dit verwijdert geen oorspronkelijke Shelly-, warmtepomp-, Wallbox-, AEG- of meterintegratie. Bewaar vooraf de gewenste privégegevens en back-up. Onzekere SG-status wordt niet als bevestigd UIT voorgesteld.
