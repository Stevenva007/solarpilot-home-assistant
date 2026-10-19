# SolarPilot beta.101 — watermonitor en gedeelde waterhistorie

Versie: **1.0.0-beta.101** · 19 oktober 2026

Het nieuwe tabblad **Water** toont gekozen bestaande waterbronnen: cumulatieve meterstand, actueel debiet, gedeeltelijk geregistreerde liters van vandaag en een afzonderlijke lekindicatie of vermoeden van langdurige stroming. **Watergeschiedenis** vergelijkt werkelijke meetpunten met beschikbare boiler-/afwascontext. Gedeeld huishoudelijk water wordt niet aan een toestel toegewezen.

De watermonitor staat standaard **uit**. Kies zelf onder **Watermeter** ten minste één passende bestaande bron; de drie rollen zijn afzonderlijk optioneel. Standaard vraagt het eigen vermoeden **0,1 L/min gedurende 60 minuten** met nieuwe actuele rapporten. Een metermelding of dit vermoeden bewijst geen fysiek lek. De functie leest uitsluitend en bedient geen kraan of toestel.

De lichte SG-bediening uit beta.100, klikbare toestel-/boilerhistorie en Aquarea-bronverwerking blijven behouden. Bestaande instellingen, timers, modellen, historie, opslag en userfiles blijven behouden.

## Bijwerken

1. Bewaar een volledige privé Home Assistant-back-up.
2. Werk via HACS bij naar beta.101 na geslaagde controles en publicatie. Behoud dezelfde entry, instellingen, modellen, historie, opslag en userfiles.
3. Herstart Home Assistant volledig en herlaad de app/browser. Controleer backend- en kaartversie apart.
4. Laat Water uit als je de functie niet gebruikt. Controleer na bewuste bronkeuze de eenheden, echte bronrapporttijden, registratie en ontbrekende dekking. Een herstart of oude vaste bronwaarde geeft geen nieuw uur aan bevestiging of volledig dagtotaal.

Er is geen nieuwe SG-bevestiging, fysieke proef of waterhardware verplicht. De optionele waterfunctie heeft uitsluitend expliciet gekozen uitleesbronnen nodig. Historie omvat maximaal dertig lokale dagen en vaste aantalsgrenzen; meetgaten blijven onbekend. De actuele validatie en nog openstaande publicatiecontroles staan in het testverslag.

[Installatie, instellingen en rollback](docs/BETA101_INSTELLEN.md) · [Actuele werking](docs/ACTUELE_WERKING.md) · [Testverslag](docs/TESTRESULTATEN_BETA101.md) · [Waterbronnen](docs/WATER_BRONNEN_BETA101.md) · [Overdracht](OVERDRACHT.md)
