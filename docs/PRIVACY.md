# Privacy bij HACS/GitHub

HACS werkt met een publieke GitHub-repository. Persoonlijke historische gegevens horen daarom niet in de repository.

Niet committen: Home Assistant-back-ups, tokens, wachtwoorden, exacte adressen, raw History/HomeWizard CSV-bestanden of persoonlijke exports.

De publieke SolarPilot-repository bevat geen persoonlijke historische bootstrap. Configuratie en live leerdata worden lokaal in Home Assistant opgeslagen. Voor deze installatie kan optioneel een privé `historical_seed.json` in `custom_components/solar_pilot/userfiles/` worden geplaatst; `hacs.json` markeert die map als persistent zodat HACS-updates haar behouden. Bij volledige SolarPilot-verwijdering verwijdert de integratie dit eigen seedbestand.

De publieke release bevat geen woning-specifieke entity-ID-defaults. Bronentiteiten worden lokaal door de gebruiker gekozen en blijven in Home Assistant-configuratie.
