# SolarPilot beta.103 — warmtepompstatus op de kaart

Versie: **1.0.0-beta.103** · 21 oktober 2026

De kaart kon een geldige door de backend afgeleide warmtepomptaak bij het nieuwe Aquarea-broncontract toch onbekend tonen. Beta.103 herstelt die frontendfilter en geeft de bronuitleg volgens het werkelijke contract. De taak blijft **Afgeleid**; oude, ontbrekende of ongeldige bronnen leveren geen extra bewijs.

Backendregels, leren, SG/controllers, timers, instellingen, modellen, historie, opslag en userfiles blijven behouden. De correctie bedient geen toestel en verandert geen bronkoppeling of regelbeleid.

## Bijwerken

1. Bewaar een volledige privé Home Assistant-back-up.
2. Werk via HACS bij naar beta.103 na geslaagde controles en publicatie. Behoud dezelfde entry, instellingen, modellen, historie, opslag en userfiles.
3. Herstart Home Assistant volledig en herlaad de app/browser. Controleer backend- en kaartversie apart.
4. Controleer de taak, het label Afgeleid en de bronuitleg tijdens een werkelijk actief meetmoment. Onvoldoende of verlopen bewijs blijft onbekend. Een oude geladen kaart kan de eerdere fout blijven tonen.

Er is geen instellingenmigratie, reset, nieuwe SG-bevestiging of extra dependency nodig. De actuele validatie en nog openstaande publicatiecontroles staan in het testverslag.

Rollback naar beta.102 gebruikt dezelfde opslag en instellingen, maar brengt de oude frontendfout terug. Verwijder de entry niet, reset geen opslag en herstart Home Assistant plus de app/browser volledig.

[Installatie, instellingen en rollback](docs/BETA103_INSTELLEN.md) · [Actuele werking](docs/ACTUELE_WERKING.md) · [Testverslag](docs/TESTRESULTATEN_BETA103.md) · [Waterbronnen](docs/WATER_BRONNEN_BETA101.md) · [Overdracht](OVERDRACHT.md)
