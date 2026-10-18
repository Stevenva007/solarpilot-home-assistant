# SolarPilot beta.99 — leesbare warmtepompsessies

Versie: **1.0.0-beta.99** · 18 oktober 2026

Open Geschiedenis bij het gewenste toestel. Tijdlijnen, sessies en gebeurtenissen zijn aanklikbaar. Bronhistorie opent de bewaarde metingen van een toegestane gekoppelde bron in Home Assistant; beschikbaarheid en bewaartermijn volgen de eigen Recorder. Bij de warmtepomp: Lange sessies tonen eerst de geregistreerde duur per taak en bewijsniveau. Klap de taakperioden open voor de oorspronkelijke chronologie met seconden en korte duur. Onbekende perioden blijven herkenbaar. Een los meetpunt is geen bewezen looptijd.

De aanraakbare tijdmarkering blijft vermogen, temperaturen, doelen, taak en SG-contact op echte meetpunten tonen. Er wordt geen oude historie ingevuld of kWh aan een taak toegeschreven. Een bronvolgordecorrectie voorkomt dat een tussentijdse Aquarea-uitlezing een geldig nieuw bericht mist. Cachedata en echte ongeldige bronnen blijven onbekend.

## Bijwerken

1. Bewaar een volledige privé Home Assistant-back-up.
2. Werk via HACS bij naar beta.99 na geslaagde controles en publicatie. Behoud entry, instellingen, modellen, historie, opslag en userfiles.
3. Herstart Home Assistant volledig en herlaad de app/browser. Controleer backend- en kaartversie apart.
4. Controleer een lange sessie, de uitgeklapte korte perioden en schuiven over de balken. Alleen bekijken schakelt niets.

Aquarea 1.8.0 en SDK 1.4.0 zijn opnieuw gecontroleerd en ongewijzigd. SG-regels, Panasonic-bevoegdheden en oorspronkelijke gegevens blijven behouden.

[Installatie en rollback](docs/BETA99_INSTELLEN.md) · [Actuele werking](docs/ACTUELE_WERKING.md) · [Testverslag](docs/TESTRESULTATEN_BETA99.md) · [Overdracht](OVERDRACHT.md)
