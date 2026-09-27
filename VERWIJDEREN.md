# SolarPilot volledig verwijderen

1. Open SolarPilot en kies **Verwijderen voorbereiden**.
2. Wacht tot SolarPilot **Verwijderen gereed** meldt. Beschermde cycli/minimumlooptijden kunnen dit vertragen.
3. Verwijder de SolarPilot-configuratie-entry via **Instellingen → Apparaten & diensten**.
4. Verwijder SolarPilot daarna in HACS.
5. Herstart Home Assistant.

De verwijdering wist SolarPilot-eigen runtime-/leerdata en programmabestanden, maar verwijdert of ontkoppelt geen onderliggende apparaten/integraties zoals netmeter-, warmtepomp-, laadpaal-, omvormer- of smart-plug-integraties.

Bij het definitief verwijderen van de configuratie-entry wordt ook de eigen, afzonderlijke dag-/sessiehistoriek gewist. Een gewone herstart of HACS-update wist die historiek niet.
