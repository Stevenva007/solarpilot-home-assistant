# SolarPilot beta.102 — analysecorrecties en waterbronactualiteit

Versie: **1.0.0-beta.102** · 20 oktober 2026

Deze update stemt de PV-samenvatting af op de bestaande daglichtmetingen, voorkomt dat Aquarea-enablement bevestigd leerbewijs wordt en vergelijkt kleine opeenvolgende boilerdalingen binnen een begrensd watervenster. De optionele **Water**-weergave toont afzonderlijk de actualiteit van debiet- en lekbronnen. Tellerintervallen, meetgaten en bronrollen blijven herkenbaar; gedeeld huishoudelijk water wordt niet aan een toestel toegewezen.

De watermonitor staat standaard **uit**. Kies zelf onder **Watermeter** ten minste één passende bestaande bron; de drie rollen zijn afzonderlijk optioneel. Standaard vraagt het eigen vermoeden **0,1 L/min gedurende 60 minuten** met nieuwe actuele rapporten. Een metermelding of dit vermoeden bewijst geen fysiek lek. De functie leest uitsluitend en bedient geen kraan of toestel.

De lichte SG-bediening, klikbare toestel-/boilerhistorie en bestaande instellingen, timers, modellen, historie, opslag en userfiles blijven behouden. Geen SG- of plannerbeleid verandert. SolarPilot configureert MQTT of force_update niet automatisch; echte nieuwe HA-ontvangsten zijn geen bewijs van een fysiek meettijdstip.

## Bijwerken

1. Bewaar een volledige privé Home Assistant-back-up.
2. Werk via HACS bij naar beta.102 na geslaagde controles en publicatie. Behoud dezelfde entry, instellingen, modellen, historie, opslag en userfiles.
3. Herstart Home Assistant volledig en herlaad de app/browser. Controleer backend- en kaartversie apart.
4. Laat Water uit als je de functie niet gebruikt. Controleer na bewuste bronkeuze de eenheden, echte bronrapporttijden, registratie en ontbrekende dekking. Een herstart of oude vaste bronwaarde geeft geen nieuw uur aan bevestiging of volledig dagtotaal.

Er is geen nieuwe SG-bevestiging, fysieke proef of waterhardware verplicht. De optionele waterfunctie heeft uitsluitend expliciet gekozen uitleesbronnen nodig. Historie omvat maximaal dertig lokale dagen en vaste aantalsgrenzen; meetgaten blijven onbekend. De actuele validatie en nog openstaande publicatiecontroles staan in het testverslag.

Rollback naar beta.101 kan de versie-1-wateropslag lezen, maar laat de nieuwe optionele meetgatrol bij een volgende opslag weg. Bewaar de volledige privéback-up om die aanvullende herkomst bij terugkeer naar beta.102 te behouden. Verwijder de entry niet en reset geen opslag.

[Installatie, instellingen en rollback](docs/BETA102_INSTELLEN.md) · [Actuele werking](docs/ACTUELE_WERKING.md) · [Testverslag](docs/TESTRESULTATEN_BETA102.md) · [Waterbronnen](docs/WATER_BRONNEN_BETA101.md) · [Overdracht](OVERDRACHT.md)
