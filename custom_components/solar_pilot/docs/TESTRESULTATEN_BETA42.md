# SolarPilot 1.0.0-beta.42 — testresultaten

Datum: **2026-10-02**

> **Software- en bronrelease-gate: groen.** De definitieve samengevoegde beta.42-bronboom leverde **1472 geslaagde tests in 8.88 s** op met UTF-8 en zonder pytest-cache. Alle elf browsercontroles en de vereiste bron-/documentcontroles zijn eveneens geslaagd. Releasepakketten bestaan pas na publicatie en worden daarna afzonderlijk inhoudelijk gecontroleerd.

## Bewezen live basis vóór beta.42

- Home Assistant Core **2026.9.4** had SolarPilot **1.0.0-beta.41** werkelijk geladen; backend en kaart zijn daarbij gecontroleerd.
- De geregistreerde beta.41-bron had **1465 geslaagde Python-tests** en **elf geslaagde browsercontroles**; publicatieworkflow en release-assets zijn daarna onafhankelijk geverifieerd.
- Veilige modules waren gericht geactiveerd.
- De oude afzonderlijke warmtepompboilerautomatiseringen voor 60/50 °C stonden uit, zodat zij niet parallel met SolarPilot regelden.
- Home Assistant-configuratiecontrole en template-reload voor de fail-closed Wallbox-bron zijn geslaagd. De bron meldde daarna actueel gestopt, de fysieke rapportage was ongeveer tien seconden oud en SolarPilot gaf terecht geen EV-vermogenskrediet.
- Deze feiten bewijzen de beta.41-uitgangssituatie. Zij bewijzen niet dat beta.42 al geïnstalleerd is of dat onderstaande fysieke acceptatiepunten al zijn uitgevoerd.

## Software-gate beta.42

Werkelijk uitgevoerd:

- volledige Python-regressiesuite: **1472 geslaagd in 8.88 s** (`PYTHONUTF8=1`, `-p no:cacheprovider`);
- de suite omvat de gerichte runtime-, thermal-, DHW-, interface-, dishwasher- en leerresetregressies.

Alle elf browsercontroles zijn geslaagd: `check_card`, `consumer_history`, `dhw_gentle`, `dishwasher_analysis`, `dishwasher_app`, `dishwasher_priority`, `learning_ui`, `live_options_ui34`, `options_ui`, `priority_ui35` en `pv_ui33`. Dit omvat desktop/mobiele snapshots, slepen en pijlen in Voorrang, de manual-hold-Hervatvoorwaarden, annuleren vóór leerreset en afzonderlijke historie-redenen.

De bronreleasecontroles zijn groen:

- `tools/check_current_explanation.py`: **geslaagd**, beta.42-regel-hash `813423dab59557a1`;
- `tools/check_handoff.py`: **geslaagd**;
- `tools/validate_repository.py`: **geslaagd**;
- `tools/check_public_repository.py`: **geslaagd** nadat uitsluitend door tests aangemaakte cachemappen waren verwijderd;
- Node-syntaxcontrole van de frontend en `git diff --check`: **geslaagd**;
- root- en embedded kopieën van de actuele uitleg, beta.42-installatie, dit verslag en de configuratiestructuur: **bytegelijk**.

## Gedrag dat de gerichte regressies moeten bewijzen

- DHW-Hervat is alleen beschikbaar buiten Automatisch regelen, weigert tijdens een wachtende opdracht, beëindigt alleen manual hold en stuurt geen temperatuur of andere fysieke service.
- Voorrang bewaart de gebruikerskeuze maar toont onder Auto laden eerlijk effectief Nee; boven Auto laden zijn positie én toestemming nodig.
- De verbeterde DHW-/Wallboxlabels en hulptekst staan in beide talen en in de gegenereerde optiehulp.
- **Apparaat-, lokale PV-, fase- en klimaatleerdata wissen** wist de bedoelde lokale afgeleide leerlagen, behoudt instellingen/historische bootstrap/operationele klimaatstaat en andere modellen, publiceert alleen status en voert geen tick of actuatoropdracht uit.
- De bestaande beta.41-klimaat-/DHW-eigendomsgrenzen en beta.40-AEG-recovery blijven groen.

## Acceptatieplan na installatie beta.42

1. Controleer dat Home Assistant werkelijk backendversie `1.0.0-beta.42` toont; vernieuw de browser geforceerd en controleer ook de kaartversie.
2. Controleer in Pauze of Alleen bekijken dat DHW-Hervat manual hold opheft zonder onmiddellijke doeltemperatuurwrite. Controleer tevens dat Automatisch regelen en een wachtende opdracht de actie blokkeren.
3. Controleer bij een toestel met bewaarde toestemming Ja de effectieve melding onder en boven Auto laden. Opslaan of verplaatsen mag geen fysieke opdracht veroorzaken.
4. Maak vóór de begrensde leerreset een analyse-export, voer de reset alleen bewust uit en vergelijk daarna instellingen, operationele klimaatstaat en afzonderlijke modellen met de gewiste lokale leerlagen.
5. Herbevestig de effectieve Wallbox-sessiebron na de upgrade. De gestopte toestand en actuele bronversheid zijn live bewezen; doorloop nog zonne-auto en manueel. Onbekend, oud of strijdig moet fail-closed blijven; geen Wallbox-servicecall is toegestaan.
6. Controleer de bestaande koelroute en onmiddellijke DHW-terugval tijdens een echte actieve koelcyclus. Dit is nog niet fysiek bewezen.
7. Test een nieuwe AEG-belading alleen gecontroleerd: APP uit→aan, geldige startvoorwaarden, maximaal één START en bescherming tot End Of Cycle. Dit is nog niet fysiek bewezen.
8. Breid fysieke activering pas uit nadat elke relevante stap afzonderlijk is bevestigd.

## Fysieke grenzen

Softwaretests met Home Assistant-testdubbels bewijzen geen echte cloud-, laadpaal-, compressor- of AEG-reactie. Zonder exclusieve AEG-meter wordt geen gemeten elektrisch faseprofiel geclaimd. De fysieke koelroute en een echte beta.42-AEG-cyclus blijven expliciete liveacceptatiepunten. Voor de Wallbox zijn actuele gestopte bronversheid en geen EV-krediet bewezen; zonne-auto- en manuele overgangen blijven nog te doorlopen. Deze fysieke punten zijn geen voorwaarde om softwaretests eerlijk als softwaretests te rapporteren.

## Releasepakketten

Release-ZIP's worden pas door de publicatieworkflow gemaakt. Inhoud, manifestversie, verboden private/cachebestanden en SHA-256-checksums worden daarna werkelijk gecontroleerd; deze nog niet bestaande pakketten worden hier niet vooraf als geslaagd gemeld.

Zie `BETA42_INSTELLEN.md` voor installatie, bediening en rollback.
