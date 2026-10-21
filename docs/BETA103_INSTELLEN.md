# SolarPilot beta.103 — warmtepompstatus op de kaart

Versie: **1.0.0-beta.103** · 21 oktober 2026

Bouwbasis: gepubliceerde beta.102 `637032107a71798b3a181076e531d5eeb76c238f`, tree `7d27bd7d346031aebecb3cd8d567f239da8571c0`.

## Wat verandert

De kaart kon bij het ondersteunde nieuwe Aquarea-broncontract een geldige door de backend afgeleide taak toch als onbekend tonen. De frontend accepteerde op die route alleen het oudere special_status-contract. Beta.103 laat beide bestaande exacte broncontracten toe, met behoud van hun eigen betekenis en de oorspronkelijke controles op provider, binding, actualiteit, cachedata en metingen.

Een afgeleide taak blijft **Afgeleid**. Nieuwe ontbrekende of oude brongegevens worden niet aangevuld. Details en historische bronbijschriften volgen het vastgelegde contract: de nieuwe operation_status-route krijgt geen oude special-status- of globale-UIT-uitleg.

De backend leverde deze samenhangende afleiding al. Backendregels, leren, SG- en andere controllers, instellingen, timers, modellen en geschiedenis blijven behouden. De update verandert uitsluitend de weergave en de releasegebonden documentatie-/implementatieregistratie; zij voegt geen toestelopdracht of extra bronrecht toe.

## Bijwerken

1. Maak een volledige privé Home Assistant-back-up, inclusief instellingen, opslag, modellen, historie en userfiles. Behoud de bestaande integratie-entry.
2. Werk via HACS bij naar exact **beta.103**, zodra de geteste release is gepubliceerd. Bij lokale installatie vervang je uitsluitend `custom_components/solar_pilot`, met behoud van userfiles en opslag.
3. Herstart Home Assistant volledig en herlaad de app/browser volledig. Controleer backend- en kaartversie afzonderlijk; een oude geladen kaart kan de eerdere fout blijven tonen.
4. Controleer bij een werkelijk actief meetmoment de taak, het label **Afgeleid** en de bronuitleg in Details. Bij onvoldoende of verlopen bewijs blijft de taak onbekend.

Er is geen instellingenmigratie, reset, nieuwe bronkoppeling, SG-herbevestiging of extra dependency nodig. Laat bestaande beschermde toestelcycli en geldige SG-/timerregels intact.

## Rollback naar beta.102

Beta.102 gebruikt dezelfde instellingen en opslag. Terugzetten behoeft geen migratie, maar brengt de oude frontendfilter en bijbehorende weergavefout terug. Bewaar dezelfde entry, modellen, historie en userfiles; verwijder of hermaak de integratie niet. Herstart Home Assistant en herlaad de browser/app volledig.

[Actuele werking](ACTUELE_WERKING.md) · [Testresultaten en publicatiestatus](TESTRESULTATEN_BETA103.md)
